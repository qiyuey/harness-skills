"""L2 Behavioral: 把"植入已知缺陷的 workflow skill"喂给 harness-review，
断言它检出了这些缺陷（用 claude CLI；先生成审计报告，再用 LLM judge 逐断言打分）。

用法：
  python3 evals/scripts/run_l2_behavioral.py
  python3 evals/scripts/run_l2_behavioral.py --strict   # 失败返回非零
"""
import argparse, json, subprocess, sys
from datetime import datetime, timezone
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = EVALS_DIR.parent
SKILLS_DIR = REPO_ROOT / "skills"
WORKSPACE = EVALS_DIR / "workspace"


def claude(prompt: str, timeout=240) -> str:
    r = subprocess.run(["claude", "-p", prompt, "--output-format", "json"],
                       capture_output=True, text=True, cwd=REPO_ROOT, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"claude CLI exit {r.returncode}: {r.stderr[:200]}")
    return json.loads(r.stdout).get("result", "")


def run_review(fixture_text: str, review_skill: str, prompt: str) -> str:
    """注入 harness-review 的 SKILL.md + references 作为方法论，让模型对 fixture 出报告。"""
    full = (
        "你将扮演 harness-review skill。下面是它的完整方法论：\n\n"
        f"=== harness-review/SKILL.md ===\n{review_skill}\n\n"
        f"=== 任务 ===\n{prompt}\n\n"
        f"=== 被审计的 workflow skill ===\n{fixture_text}\n"
    )
    return claude(full)


def judge_assertions(report: str, assertions: list[dict]) -> list[dict]:
    items = "\n".join(f"{i+1}. (维度{a['dim']}) {a['expect']}" for i, a in enumerate(assertions))
    prompt = f"""下面是一份 harness 审计报告，以及一组断言。逐条判断报告是否满足该断言（命中=YES/未命中=NO）。

审计报告：
{report[:6000]}

断言：
{items}

只输出 JSON 数组，每元素 {{"n":序号,"hit":true/false}}，不要解释。"""
    raw = claude(prompt)
    try:
        start = raw.find("["); end = raw.rfind("]") + 1
        arr = json.loads(raw[start:end])
        return arr
    except Exception:
        return [{"n": i + 1, "hit": False} for i in range(len(assertions))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    cfg = json.loads((EVALS_DIR / "evals.json").read_text(encoding="utf-8"))
    review_skill = (SKILLS_DIR / "harness-review" / "SKILL.md").read_text(encoding="utf-8")
    seven = (SKILLS_DIR / "harness-review" / "references" / "seven-dimensions.md").read_text(encoding="utf-8")
    review_skill += "\n\n=== references/seven-dimensions.md ===\n" + seven

    all_pass = True
    out = []
    for ev in cfg["l2_behavioral"]["evals"]:
        fixture = (REPO_ROOT / ev["fixture"]).read_text(encoding="utf-8")
        print(f"\n[{ev['name']}] 生成审计报告中（~1-2min）...")
        try:
            report = run_review(fixture, review_skill, ev["prompt"])
        except Exception as e:
            print("  ❌ review 失败:", e); all_pass = False; continue
        verdicts = judge_assertions(report, ev["assertions"])
        hits = sum(1 for v in verdicts if v.get("hit"))
        total = len(ev["assertions"])
        for i, a in enumerate(ev["assertions"]):
            v = next((x for x in verdicts if x.get("n") == i + 1), {"hit": False})
            print(f"  {'✅' if v.get('hit') else '❌'} 维度{a['dim']}: {a['expect'][:50]}")
        passed = hits >= 5  # pass_rule: >=5/6
        print(f"  命中 {hits}/{total} → {'PASS' if passed else 'FAIL'}")
        all_pass = all_pass and passed
        out.append({"name": ev["name"], "hits": hits, "total": total, "passed": passed})

    WORKSPACE.mkdir(parents=True, exist_ok=True)
    (WORKSPACE / f"l2_{datetime.now().strftime('%Y%m%d-%H%M%S')}.json").write_text(
        json.dumps({"timestamp": datetime.now(timezone.utc).isoformat(), "results": out},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print("✅ L2 PASS" if all_pass else "⚠️  L2 有 FAIL")
    if args.strict and not all_pass:
        sys.exit(2)


if __name__ == "__main__":
    main()
