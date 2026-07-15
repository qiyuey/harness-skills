"""harness-skills 评估主入口。

用法：
  python3 evals/scripts/run_evals.py                 # 全部三层
  python3 evals/scripts/run_evals.py --layer l1      # 只跑 L1（零 LLM，CI 默认）
  python3 evals/scripts/run_evals.py --layer l3
  python3 evals/scripts/run_evals.py --strict        # L2/L3 失败也返回非零

退出码：L1 失败始终返回 1（CI 阻塞）；L2/L3 默认只 warning，加 --strict 才阻塞。
"""
import argparse, subprocess, sys
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent
LAYERS = {
    "l1": ("run_l1_lint.py", "L1 Lint（SKILL.md 自洽合规，零 LLM）"),
    "l2": ("run_l2_behavioral.py", "L2 Behavioral（review 检出植入缺陷，需 claude CLI）"),
    "l3": ("run_l3_trigger.py", "L3 Trigger（显式路由+普通开发近邻误触发，需 claude CLI）"),
}


def run_layer(key: str, strict: bool) -> int:
    script, label = LAYERS[key]
    print(f"\n{'#'*60}\n# {label}\n{'#'*60}")
    cmd = [sys.executable, str(SCRIPTS / script)]
    if key in ("l2", "l3") and strict:
        cmd.append("--strict")
    return subprocess.run(cmd).returncode


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layer", choices=["l1", "l2", "l3"], help="只跑指定层（默认全部）")
    ap.add_argument("--strict", action="store_true", help="L2/L3 失败也阻塞")
    args = ap.parse_args()

    keys = [args.layer] if args.layer else ["l1", "l2", "l3"]
    exit_code = 0
    for k in keys:
        rc = run_layer(k, args.strict)
        if k == "l1" and rc != 0:
            exit_code = 1  # L1 始终阻塞
        elif k in ("l2", "l3") and rc != 0 and args.strict:
            exit_code = rc
    print(f"\n{'='*60}\n汇总：退出码 {exit_code}")
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
