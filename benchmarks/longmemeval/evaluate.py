"""Stage 3: LLM-judge evaluation of LongMemEval search results.

Follows the official LongMemEval evaluation protocol (xiaowu0162/longmemeval).
Uses OpenAI directly (not memv's LLMClient) to match the official setup:
  - gpt-4o as judge (official asserts gpt-4o-2024-08-06)
  - temperature=0, max_tokens=10
  - No system prompt (user message only)
  - Type-specific prompts + abstention prompt for _abs questions
  - Task-averaged accuracy as primary metric
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
from datetime import datetime, timezone

from openai import AsyncOpenAI

from ._checkpoint import RESULTS_DIR, append_jsonl, load_all_results, load_completed

logger = logging.getLogger(__name__)

JUDGE_MODEL = "gpt-4o"

# --- Judge prompts matching official LongMemEval evaluate_qa.py (xiaowu0162/longmemeval) ---

TEMPORAL_REASONING_PROMPT = """I will give you a question, a correct answer, and a response from a model. \
Please answer yes if the response contains the correct answer. Otherwise, answer no. \
If the response is equivalent to the correct answer or contains all the intermediate steps \
to get the correct answer, you should also answer yes. \
If the response only contains a subset of the information required by the answer, answer no. \
In addition, do not penalize off-by-one errors for the number of days. \
If the question asks for the number of days/weeks/months, etc., and the model makes off-by-one errors \
(e.g., predicting 19 days when the answer is 18), the model's response is still correct.

Question: {question}

Correct Answer: {gold_answer}

Model Response: {response}"""

KNOWLEDGE_UPDATE_PROMPT = """I will give you a question, a correct answer, and a response from a model. \
Please answer yes if the response contains the correct answer. Otherwise, answer no. \
If the response contains some previous information along with an updated answer, \
the response should be considered as correct as long as the updated answer is the required answer.

Question: {question}

Correct Answer: {gold_answer}

Model Response: {response}"""

SINGLE_SESSION_PREFERENCE_PROMPT = """I will give you a question, a rubric for desired personalized response, \
and a response from a model. Please answer yes if the response satisfies the desired response. Otherwise, answer no. \
The model does not need to reflect all the points in the rubric. \
The response is correct as long as it recalls and utilizes the user's personal information correctly.

Question: {question}

Rubric: {gold_answer}

Model Response: {response}"""

DEFAULT_PROMPT = """I will give you a question, a correct answer, and a response from a model. \
Please answer yes if the response contains the correct answer. Otherwise, answer no. \
If the response is equivalent to the correct answer or contains all the intermediate steps \
to get the correct answer, you should also answer yes. \
If the response only contains a subset of the information required by the answer, answer no.

Question: {question}

Correct Answer: {gold_answer}

Model Response: {response}"""

ABSTENTION_PROMPT = """I will give you an unanswerable question, an explanation, and a response from a model. \
Please answer yes if the model correctly identifies the question as unanswerable. \
The model could say that the information is incomplete, or some other information is given \
but the asked information is not.

Question: {question}

Explanation: {gold_answer}

Model Response: {response}"""

PROMPTS_BY_TYPE = {
    "temporal-reasoning": TEMPORAL_REASONING_PROMPT,
    "knowledge-update": KNOWLEDGE_UPDATE_PROMPT,
    "single-session-preference": SINGLE_SESSION_PREFERENCE_PROMPT,
}


async def evaluate_single(
    client: AsyncOpenAI,
    question: str,
    gold_answer: str,
    response: str,
    question_type: str,
    question_id: str = "",
) -> bool:
    """Evaluate a single question-response pair using LLM judge.

    Uses OpenAI directly (not memv's LLMClient) to match the official
    LongMemEval evaluation protocol: gpt-4o, temperature=0, no system prompt.
    """
    if question_id.endswith("_abs"):
        template = ABSTENTION_PROMPT
    else:
        template = PROMPTS_BY_TYPE.get(question_type, DEFAULT_PROMPT)
    prompt = template.format(question=question, gold_answer=gold_answer, response=response)
    prompt += "\n\nIs the model response correct? Answer yes or no only."

    completion = await client.chat.completions.create(
        model=JUDGE_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=10,
    )
    result = completion.choices[0].message.content or ""
    return result.strip().lower().startswith("yes")


async def run(
    run_name: str = "baseline",
    max_concurrent: int = 10,
    resume: bool = True,
):
    """Run evaluation on search results.

    Args:
        run_name: Name for this benchmark run (must match search stage).
        max_concurrent: Max concurrent LLM calls.
        resume: Resume from checkpoint if prior results exist.
    """
    client = AsyncOpenAI()

    run_dir = RESULTS_DIR / run_name
    search_path = run_dir / "search.json"
    if not search_path.exists():
        raise FileNotFoundError(f"No search results at {search_path}. Run search stage first.")

    data = json.loads(search_path.read_text(encoding="utf-8"))

    jsonl_path = run_dir / "evaluate.jsonl"

    completed_ids = load_completed(jsonl_path) if resume else set()
    if not resume and jsonl_path.exists():
        jsonl_path.unlink()

    remaining = [item for item in data if item["question_id"] not in completed_ids]

    print(f"LongMemEval Evaluate | run={run_name} questions={len(data)} remaining={len(remaining)}")
    if completed_ids:
        print(f"  Resuming: {len(completed_ids)} already completed")

    semaphore = asyncio.Semaphore(max_concurrent)

    async def eval_with_semaphore(item: dict) -> None:
        async with semaphore:
            # Skip items that errored in search stage
            if item.get("error"):
                scored = {
                    "question_id": item["question_id"],
                    "question_type": item.get("question_type"),
                    "is_correct": None,
                    "error": item["error"],
                    "question": item.get("question", ""),
                    "gold_answer": item.get("answer", ""),
                    "response": item.get("response", ""),
                }
            else:
                try:
                    is_correct = await evaluate_single(
                        client,
                        item["question"],
                        item["answer"],
                        item["response"],
                        item.get("question_type", "default"),
                        question_id=item["question_id"],
                    )
                    scored = {
                        "question_id": item["question_id"],
                        "question_type": item.get("question_type"),
                        "is_correct": is_correct,
                        "question": item["question"],
                        "gold_answer": item["answer"],
                        "response": item["response"],
                    }
                except Exception as e:
                    logger.error("Evaluation failed for %s: %s", item["question_id"], e)
                    scored = {
                        "question_id": item["question_id"],
                        "question_type": item.get("question_type"),
                        "is_correct": None,
                        "error": f"eval_failed: {e}",
                        "question": item.get("question", ""),
                        "gold_answer": item.get("answer", ""),
                        "response": item.get("response", ""),
                    }
            append_jsonl(jsonl_path, scored)

    tasks = [eval_with_semaphore(item) for item in remaining]
    await asyncio.gather(*tasks)

    all_scored = load_all_results(jsonl_path)

    type_stats: dict[str, dict[str, int]] = {}
    abstention_correct = 0
    abstention_total = 0
    total_correct = 0
    total_scored = 0
    total_errors = 0

    for scored in all_scored:
        qtype = scored.get("question_type", "unknown")
        if qtype not in type_stats:
            type_stats[qtype] = {"correct": 0, "total": 0}

        if scored.get("is_correct") is None:
            total_errors += 1
            continue

        type_stats[qtype]["total"] += 1
        total_scored += 1

        is_abstention = scored.get("question_id", "").endswith("_abs")
        if is_abstention:
            abstention_total += 1

        if scored["is_correct"]:
            type_stats[qtype]["correct"] += 1
            total_correct += 1
            if is_abstention:
                abstention_correct += 1

    overall_accuracy = total_correct / total_scored if total_scored > 0 else 0
    abstention_accuracy = abstention_correct / abstention_total if abstention_total > 0 else 0
    accuracy_by_type = {}
    for qtype, stats in sorted(type_stats.items()):
        acc = stats["correct"] / stats["total"] if stats["total"] > 0 else 0
        accuracy_by_type[qtype] = {
            "correct": stats["correct"],
            "total": stats["total"],
            "accuracy": round(acc, 4),
        }

    # Task-averaged accuracy: mean of per-type means (official LongMemEval metric).
    # Prevents type imbalance from skewing results.
    type_accuracies = [s["accuracy"] for s in accuracy_by_type.values()]
    task_averaged_accuracy = sum(type_accuracies) / len(type_accuracies) if type_accuracies else 0

    scores = {
        "run_name": run_name,
        "total_questions": len(all_scored),
        "scored_questions": total_scored,
        "errors": total_errors,
        "correct_answers": total_correct,
        "task_averaged_accuracy": round(task_averaged_accuracy, 4),
        "overall_accuracy": round(overall_accuracy, 4),
        "abstention_accuracy": round(abstention_accuracy, 4),
        "abstention_total": abstention_total,
        "accuracy_by_type": accuracy_by_type,
        "evaluation_timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "scored_items": all_scored,
    }

    print(f"\n{'=' * 50}")
    print(f"Task-averaged: {task_averaged_accuracy:.1%}")
    print(f"Overall: {total_correct}/{total_scored} = {overall_accuracy:.1%}")
    if abstention_total:
        print(f"Abstention: {abstention_correct}/{abstention_total} = {abstention_accuracy:.1%}")
    if total_errors:
        print(f"Errors (excluded from scoring): {total_errors}")
    print(f"{'=' * 50}")
    for qtype, stats in sorted(accuracy_by_type.items()):
        print(f"  {qtype}: {stats['correct']}/{stats['total']} = {stats['accuracy']:.1%}")
    print(f"{'=' * 50}")

    output_path = run_dir / "scores.json"
    output_path.write_text(json.dumps(scores, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nScores saved to {output_path}")

    return scores


def main():
    parser = argparse.ArgumentParser(description="LongMemEval Stage 3: Evaluation")
    parser.add_argument("--run-name", default="baseline", help="Name for this run")
    parser.add_argument("--max-concurrent", type=int, default=10, help="Max concurrent LLM calls")
    parser.add_argument("--no-resume", action="store_true", help="Start fresh, ignore prior checkpoint")
    args = parser.parse_args()

    asyncio.run(run(run_name=args.run_name, max_concurrent=args.max_concurrent, resume=not args.no_resume))


if __name__ == "__main__":
    main()
