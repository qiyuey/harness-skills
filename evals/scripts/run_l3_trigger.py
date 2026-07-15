"""L3 Trigger: 显式调用路由 + 普通开发近邻误触发评测（Claude CLI）。

每条 query 默认独立运行 3 次，避免单次随机结果制造虚假 PASS。这里评估的是
description 的跨客户端降级边界；Codex/Claude 的禁止隐式调用策略由 L1 静态阻塞。
"""
import argparse
import json
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = EVALS_DIR.parent
SKILLS_DIR = REPO_ROOT / "skills"
WORKSPACE = EVALS_DIR / "workspace"
SKILLS = ["review", "fix", "build"]
LABELS = SKILLS + ["none"]


def claude(prompt: str) -> str:
    result = subprocess.run(
        ["claude", "-p", prompt, "--output-format", "json"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
    )
    if result.returncode != 0:
        raise RuntimeError(f"claude CLI exit {result.returncode}: {result.stderr[:200]}")
    return json.loads(result.stdout).get("result", "")


def load_descriptions() -> dict:
    descriptions = {}
    for skill in SKILLS:
        text = (SKILLS_DIR / f"harness-{skill}" / "SKILL.md").read_text(encoding="utf-8")
        match = re.search(r"^description:\s*(.*?)(?=\n[a-z][a-z0-9_-]*:|\n---)", text, re.S | re.M)
        descriptions[skill] = re.sub(r"\s+", " ", (match.group(1) if match else "").lstrip(">").strip())
    return descriptions


def judge(query: str, descriptions: dict) -> str:
    block = "\n\n".join(f"[{skill}] harness-{skill}:\n{descriptions[skill]}" for skill in SKILLS)
    prompt = f"""你是 skill 路由器。下面是三个候选 skill 的 description：

{block}

用户消息：
{query}

哪个 skill 应被调用？只回答一个词：review / fix / build / none。显式调用是必要条件；none 表示都不应调用。"""
    answer = claude(prompt).strip().lower()
    match = re.fullmatch(r"(?:harness-)?(review|fix|build|none)[.!。]?", answer)
    return match.group(1) if match else "none"


def run_attempt(case_index: int, run_index: int, case: dict, descriptions: dict) -> dict:
    try:
        predicted = judge(case["query"], descriptions)
        error = None
    except Exception as exc:
        predicted = "none"
        error = str(exc)
    return {
        "case_index": case_index,
        "run_index": run_index,
        "query": case["query"],
        "expected": case["expected_skill"],
        "predicted": predicted,
        "correct": predicted == case["expected_skill"],
        "error": error,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--runs", type=int, default=3)
    parser.add_argument("--workers", type=int, default=6)
    args = parser.parse_args()

    cases = json.loads((EVALS_DIR / "fixtures" / "trigger-evals.json").read_text(encoding="utf-8"))
    descriptions = load_descriptions()

    if args.dry_run:
        from collections import Counter
        print("cases:", dict(Counter(case["expected_skill"] for case in cases)), "total", len(cases))
        print("runs per case:", args.runs)
        for skill in SKILLS:
            print(f"  harness-{skill} desc: {descriptions[skill][:100]}...")
        return

    attempts = []
    print(f"评测 {len(cases)} 条 query × {args.runs} 次独立运行...")
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        futures = [
            pool.submit(run_attempt, case_index, run_index, case, descriptions)
            for case_index, case in enumerate(cases)
            for run_index in range(args.runs)
        ]
        for future in as_completed(futures):
            attempts.append(future.result())

    attempts.sort(key=lambda item: (item["case_index"], item["run_index"]))
    results = []
    for case_index, case in enumerate(cases):
        case_attempts = [item for item in attempts if item["case_index"] == case_index]
        predictions = [item["predicted"] for item in case_attempts]
        all_correct = all(item["correct"] for item in case_attempts)
        print(f"  {'✅' if all_correct else '❌'} exp={case['expected_skill']:6} pred={','.join(predictions):17} | {case['query'][:48]}")
        results.append({
            "query": case["query"],
            "expected": case["expected_skill"],
            "predictions": predictions,
            "all_runs_correct": all_correct,
        })

    total_attempts = len(attempts)
    attempt_accuracy = sum(item["correct"] for item in attempts) / total_attempts if total_attempts else 0
    case_accuracy = sum(item["all_runs_correct"] for item in results) / len(results) if results else 0
    cross_attempts = sum(
        1 for item in attempts
        if item["expected"] in SKILLS and item["predicted"] in SKILLS and not item["correct"]
    )
    missed_attempts = sum(
        1 for item in attempts if item["expected"] in SKILLS and item["predicted"] == "none"
    )
    false_fire_attempts = sum(
        1 for item in attempts if item["expected"] == "none" and item["predicted"] != "none"
    )
    error_attempts = sum(1 for item in attempts if item["error"])
    metrics = {
        "attempt_accuracy": round(attempt_accuracy, 3),
        "case_accuracy": round(case_accuracy, 3),
        "cross_skill_attempts": cross_attempts,
        "missed_attempts": missed_attempts,
        "false_fire_attempts": false_fire_attempts,
        "error_attempts": error_attempts,
        "cases": len(cases),
        "runs_per_case": args.runs,
    }

    WORKSPACE.mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "trigger-baseline.json").write_text(json.dumps(
        {"timestamp": datetime.now(timezone.utc).isoformat(), "metrics": metrics,
         "results": results, "attempts": attempts},
        ensure_ascii=False,
        indent=2,
    ), encoding="utf-8")

    if args.json:
        print(json.dumps(metrics, ensure_ascii=False))
    print("=" * 72)
    print(
        f"Attempt accuracy {attempt_accuracy:.1%} | Case accuracy {case_accuracy:.1%} | "
        f"串触发 {cross_attempts} | 漏触发 {missed_attempts} | 误触发 {false_fire_attempts}"
    )
    print("=" * 72)
    passed = (
        attempt_accuracy >= 0.95
        and cross_attempts == 0
        and missed_attempts == 0
        and false_fire_attempts == 0
        and error_attempts == 0
    )
    print("✅ L3 PASS" if passed else "⚠️  L3 FAIL")
    sys.exit(0 if passed or not args.strict else 2)


if __name__ == "__main__":
    main()
