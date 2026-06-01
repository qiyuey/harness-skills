"""L3 Trigger: 三个 harness skill 的路由准确率 + 互斥性（用 claude CLI，无需 API key）。

与单 skill 触发评测不同：本评测给判官**三个 skill 的 description**，让它从
{review, fix, build, none} 选一个最该触发的。这同时检验：
  - 召回：该触发某 skill 的 query 是否选中它
  - 互斥：fix 的样本不串到 build（description 边界是否清晰）

用法：
  python3 evals/scripts/run_l3_trigger.py
  python3 evals/scripts/run_l3_trigger.py --dry-run
"""
import argparse, json, re, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = EVALS_DIR.parent
SKILLS_DIR = REPO_ROOT / "skills"
WORKSPACE = EVALS_DIR / "workspace"
SKILLS = ["review", "fix", "build"]


def claude(prompt: str) -> str:
    r = subprocess.run(["claude", "-p", prompt, "--output-format", "json"],
                       capture_output=True, text=True, cwd=REPO_ROOT)
    if r.returncode != 0:
        raise RuntimeError(f"claude CLI exit {r.returncode}: {r.stderr[:200]}")
    return json.loads(r.stdout).get("result", "")


def load_descriptions() -> dict:
    out = {}
    for s in SKILLS:
        fm = (SKILLS_DIR / f"harness-{s}" / "SKILL.md").read_text(encoding="utf-8")
        m = re.search(r"^description:\s*(.*?)(?=\n[a-z][a-z0-9_-]*:|\n---)", fm, re.S | re.M)
        out[s] = re.sub(r"\s+", " ", (m.group(1) if m else "").lstrip(">").strip())
    return out


def judge(query: str, descs: dict) -> str:
    block = "\n\n".join(f"[{s}] harness-{s}:\n{descs[s]}" for s in SKILLS)
    prompt = f"""你是 Claude Code 的 skill 路由器。下面是三个候选 skill 的描述：

{block}

用户消息：
{query}

哪个 skill 最该被触发？只回答一个词：review / fix / build / none（none 表示三个都不该触发）。不要解释。"""
    ans = claude(prompt).strip().lower()
    for s in SKILLS + ["none"]:
        if s in ans:
            return s
    return "none"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    cases = json.loads((EVALS_DIR / "fixtures" / "trigger-evals.json").read_text(encoding="utf-8"))
    descs = load_descriptions()

    if args.dry_run:
        from collections import Counter
        print("cases:", dict(Counter(c["expected_skill"] for c in cases)), "total", len(cases))
        for s in SKILLS:
            print(f"  harness-{s} desc: {descs[s][:80]}...")
        return

    results = []
    print(f"评测 {len(cases)} 条路由 query（每条约 3-5s）...")
    for c in cases:
        exp = c["expected_skill"]
        try:
            pred = judge(c["query"], descs)
        except Exception as e:
            print("  ❌", e); pred = "none"
        ok = pred == exp
        print(f"  {'✅' if ok else '❌'} exp={exp:6} pred={pred:6} | {c['query'][:50]}")
        results.append({"query": c["query"], "expected": exp, "predicted": pred, "correct": ok})

    n = len(results)
    acc = sum(r["correct"] for r in results) / n if n else 0
    # 互斥错误：在三个真 skill 之间串触发（exp 与 pred 都是真 skill 但不同）
    cross = sum(1 for r in results if r["expected"] in SKILLS and r["predicted"] in SKILLS and not r["correct"])
    # 漏触发：该触发真 skill 却答 none
    miss = sum(1 for r in results if r["expected"] in SKILLS and r["predicted"] == "none")
    # 误触发：none 样本却选了某 skill
    false_fire = sum(1 for r in results if r["expected"] == "none" and r["predicted"] != "none")

    metrics = {"accuracy": round(acc, 3), "cross_skill_errors": cross,
               "missed": miss, "false_fire": false_fire, "n": n}

    WORKSPACE.mkdir(parents=True, exist_ok=True)
    (WORKSPACE / "trigger-baseline.json").write_text(json.dumps(
        {"timestamp": datetime.now(timezone.utc).isoformat(), "metrics": metrics, "results": results},
        ensure_ascii=False, indent=2), encoding="utf-8")

    if args.json:
        print(json.dumps(metrics, ensure_ascii=False)); 
    print("=" * 60)
    print(f"Accuracy {acc:.1%} | 串触发 {cross} | 漏触发 {miss} | 误触发 {false_fire}")
    print("=" * 60)
    target = 0.85
    ok = acc >= target and cross == 0
    print(f"{'✅' if ok else '⚠️ '} accuracy {acc:.1%} (目标 {target:.0%})，串触发 {cross}（目标 0）")
    sys.exit(0 if ok else (2 if "--strict" in sys.argv else 0))


if __name__ == "__main__":
    main()
