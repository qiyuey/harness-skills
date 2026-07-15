"""L1 Lint: SKILL.md 自洽合规检查（零 LLM，确定性，<2s）。

对纯方法论 skill 而言这是最关键的一层：全部价值在 SKILL.md 文本，没有脚本可回归。
本检查把"一个 harness skill 应有的品质"机械化。

用法：
  python3 evals/scripts/run_l1_lint.py
  python3 evals/scripts/run_l1_lint.py --json   # 机读输出
退出码：0=全过，1=有 FAIL
"""
import argparse
import json
import re
import sys
from pathlib import Path

EVALS_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = EVALS_DIR.parent
SKILLS_DIR = REPO_ROOT / "skills"

ALLOWED_FM_KEYS = {
    "name", "description", "license", "allowed-tools", "metadata", "compatibility",
    # Claude Code 官方平台扩展；与 agents/openai.yaml 的 Codex policy 配对。
    "disable-model-invocation",
}

# 领域残留黑名单：通用库不得出现任何金融/项目专属词或绝对用户路径
FORBIDDEN_TERMS = [
    "ebitda", "financial_snapshot", "akshare", "yfinance", "rs_competition",
    "rs_tam", "vs_comps", "football_field", "initiating-coverage", "港交所",
    "/users/yuchuan", "/home/", "中芯国际", "valuation_output",
]

# 语言中立：skill 本体不得耦合具体编程语言（方法论必须语言无关）。
# 用正则避免误伤（如 "policy" 含 "py"）。命中即 FAIL。
LANGUAGE_COUPLING_PATTERNS = [
    r"\bpython3?\b", r"\bpy_compile\b", r"\bargparse\b", r"\bsubprocess\b",
    r"\btempfile\b", r"\bimport json\b", r"\bjson\.load\b", r"\bsys\.argv\b",
    r"\.pyc?\b", r"```python\b", r"```(?:js|javascript|typescript|go|rust|java)\b",
    r"\bnpm\b", r"\bpip install\b",
]

# 行为/风格类负向指令模式（指令正向性自审，dogfooding 维度 D3 指令极性）。
# 仅匹配"行为/风格"类；内容边界类（带 QC 配套的）由人工豁免，见 ALLOWLIST。
NEGATIVE_PATTERNS = [
    r"禁止使用.{0,8}语言", r"don't\b", r"\bdo not\b", r"\bnever\b", r"must not",
]
# 已知合理的负向指令（结构性约束 / 引用反模式名 / STOP 规则），豁免不计 FAIL
POLARITY_ALLOWLIST_SUBSTR = [
    "禁止在 x 时机运行",  # 这是被引用来批判的反模式名，不是 skill 自身指令
    "禁止补丁式",          # 强制纪律，无正向等价（且属内容边界）
    "不允许把猜测当根因",  # 方法论硬规则
    "stop 规则",
]


def parse_frontmatter(text: str):
    m = re.match(r"^---\n(.*?)\n---", text, re.S)
    if not m:
        return None, "无 frontmatter"
    return m.group(1), None


def lint_skill(skill_md: Path) -> list[dict]:
    """返回 finding 列表，每项 {check, level, msg}。level: FAIL / WARN / PASS"""
    findings = []
    text = skill_md.read_text(encoding="utf-8")

    # ---- frontmatter 合规 ----
    fm, err = parse_frontmatter(text)
    if err:
        findings.append({"check": "frontmatter", "level": "FAIL", "msg": err})
        return findings
    topkeys = set(re.findall(r"^([a-z][a-z0-9_-]*):", fm, re.M))
    bad = topkeys - ALLOWED_FM_KEYS
    if bad:
        findings.append({"check": "frontmatter.keys", "level": "FAIL",
                         "msg": f"非法 frontmatter key: {sorted(bad)}"})
    name_m = re.search(r"^name:\s*(.+)$", fm, re.M)
    name = name_m.group(1).strip().strip("'\"") if name_m else ""
    if not re.match(r"^[a-z0-9-]+$", name):
        findings.append({"check": "frontmatter.name", "level": "FAIL", "msg": f"name 非 kebab-case: {name!r}"})
    if len(name) > 64:
        findings.append({"check": "frontmatter.name", "level": "FAIL", "msg": f"name >64 字符"})
    desc_m = re.search(r"^description:\s*(.*?)(?=\n[a-z][a-z0-9_-]*:|\Z)", fm, re.S | re.M)
    desc = re.sub(r"\s+", " ", (desc_m.group(1) if desc_m else "").lstrip(">").strip())
    if len(desc) > 1024:
        findings.append({"check": "frontmatter.description", "level": "FAIL", "msg": f"description {len(desc)}>1024 字符"})
    if "<" in desc or ">" in desc:
        findings.append({"check": "frontmatter.description", "level": "FAIL", "msg": "description 含尖括号 <>"})
    if not desc:
        findings.append({"check": "frontmatter.description", "level": "FAIL", "msg": "description 缺失"})

    # ---- 调用策略：harness workflow 必须由用户显式启动 ----
    claude_policy = re.search(r"^disable-model-invocation:\s*true\s*$", fm, re.M)
    if not claude_policy:
        findings.append({"check": "invocation-policy.claude", "level": "FAIL",
                         "msg": "缺少 disable-model-invocation: true"})
    openai_yaml = skill_md.parent / "agents" / "openai.yaml"
    if not openai_yaml.exists():
        findings.append({"check": "invocation-policy.codex", "level": "FAIL",
                         "msg": "缺少 agents/openai.yaml"})
    else:
        openai_text = openai_yaml.read_text(encoding="utf-8")
        if not re.search(r"^\s*allow_implicit_invocation:\s*false\s*$", openai_text, re.M):
            findings.append({"check": "invocation-policy.codex", "level": "FAIL",
                             "msg": "缺少 policy.allow_implicit_invocation: false"})

    # ---- 零领域残留 ----
    lower = text.lower()
    hits = [t for t in FORBIDDEN_TERMS if t in lower]
    if hits:
        findings.append({"check": "no-domain-residue", "level": "FAIL", "msg": f"领域残留: {hits}"})

    # ---- 语言中立（skill 本体不耦合具体编程语言）----
    lang_hits = []
    for i, line in enumerate(text.splitlines(), 1):
        for pat in LANGUAGE_COUPLING_PATTERNS:
            if re.search(pat, line, re.I):
                lang_hits.append(f"L{i}: {line.strip()[:60]}")
                break
    if lang_hits:
        findings.append({"check": "language-neutral", "level": "FAIL",
                         "msg": f"语言耦合 {len(lang_hits)} 处: " + " | ".join(lang_hits[:3])})

    # ---- 交叉引用完整 ----
    for ref in re.findall(r"references/([A-Za-z0-9_\-]+\.md)", text):
        if not (skill_md.parent / "references" / ref).exists():
            findings.append({"check": "cross-ref", "level": "FAIL", "msg": f"悬空引用 references/{ref}"})

    # ---- 指令正向性自审（dogfooding 维度 D3 指令极性）----
    polarity_hits = []
    for i, line in enumerate(text.splitlines(), 1):
        ll = line.lower()
        if any(sub in ll for sub in POLARITY_ALLOWLIST_SUBSTR):
            continue
        for pat in NEGATIVE_PATTERNS:
            if re.search(pat, ll):
                polarity_hits.append(f"L{i}: {line.strip()[:60]}")
                break
    if polarity_hits:
        findings.append({"check": "instruction-polarity", "level": "WARN",
                         "msg": f"行为/风格类负向指令 {len(polarity_hits)} 处（应正向改写）: " + " | ".join(polarity_hits[:3])})

    # ---- 渐进披露：body 行数 ----
    body = text[text.find("---", 3) + 3:] if text.count("---") >= 2 else text
    body_lines = len([l for l in body.splitlines()])
    if body_lines > 500:
        findings.append({"check": "progressive-disclosure", "level": "WARN",
                         "msg": f"SKILL.md body {body_lines} 行 >500，考虑拆 references/"})

    if not findings:
        findings.append({"check": "all", "level": "PASS", "msg": "全部检查通过"})
    return findings


def lint_references() -> list[dict]:
    """>300 行的 reference 应有目录（## 或 # 小标题即可视为目录骨架）"""
    findings = []
    for ref in SKILLS_DIR.glob("*/references/*.md"):
        text = ref.read_text(encoding="utf-8")
        n = len(text.splitlines())
        headers = len(re.findall(r"^#{1,3}\s", text, re.M))
        if n > 300 and headers < 3:
            findings.append({"check": "ref-toc", "level": "WARN",
                             "msg": f"{ref.relative_to(REPO_ROOT)} {n} 行但小标题 <3，建议加目录"})
    return findings


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    report = {}
    fail = 0
    warn = 0
    for skill_md in sorted(SKILLS_DIR.glob("*/SKILL.md")):
        name = skill_md.parent.name
        findings = lint_skill(skill_md)
        report[name] = findings
        fail += sum(1 for f in findings if f["level"] == "FAIL")
        warn += sum(1 for f in findings if f["level"] == "WARN")
    ref_findings = lint_references()
    if ref_findings:
        report["_references"] = ref_findings
        warn += sum(1 for f in ref_findings if f["level"] == "WARN")

    if args.json:
        print(json.dumps({"fail": fail, "warn": warn, "report": report}, ensure_ascii=False, indent=2))
    else:
        print("=" * 60)
        print(f"L1 Lint — {len(report)} 个检查单元")
        print("=" * 60)
        for unit, findings in report.items():
            for f in findings:
                icon = {"FAIL": "❌", "WARN": "⚠️ ", "PASS": "✅"}[f["level"]]
                print(f"  {icon} [{unit}] {f['check']}: {f['msg']}")
        print("=" * 60)
        print(f"FAIL={fail}  WARN={warn}")
        print("✅ L1 PASS" if fail == 0 else f"❌ L1 FAIL ({fail} 项)")

    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
