---
name: harness-fix
description: 对 LLM 工作流（skill/pipeline）中发现的具体 bug 或异常，执行系统化的「根因溯源 → 前置检测 → 修复」三层闭环。触发词：harness-fix、系统化修复、根因分析、前置发现、避免复现、harness问题。与 harness-review 的区别：review 是全量审计（七维度评分），harness-fix 是针对**已知症状**的单点深挖与修复。**不适用场景**：功能空缺/schema 扩展/新功能发现的改进建议，应使用 harness-build。
---

# harness-fix

针对在 skill/pipeline 运行过程中**已发现的具体 bug 或异常**，执行「根因溯源 → 前置检测 → 修复」三层闭环，确保问题不在未来复现。

> **与 `harness-review` 的区别**：
> - `harness-review`：全量审计，无症状也能运行，输出七维评分报告
> - `harness-fix`：有症状驱动，深挖单点，输出可落地的代码级修复
>
> **重要**：本 skill 是排障框架，不是任何具体 repo 状态的权威说明。遇到路径、Step 编号、QC 名称、产物结构时，必须先用工具验证；如果本文示例与 repo 不一致，以 repo 为准。
>
> **项目失败案例**：本文的失败模式分类表是**抽象 taxonomy**。具体项目的真实失败案例（字段名、路径、QC 名称）应放在该项目的 harness adapter skill 里；执行时若存在 adapter，先 Read adapter 的案例库再溯源。

---

## 核心框架：三层修复原则

每个问题原则上要在三个层次同时修复；若某层在当前问题中不存在（例如纯文档误导、一次性数据产物修正、无生成端代码），必须在最终说明中明确"该层不适用"的理由，而不是为了凑三层制造无意义改动：

```
层1 契约（Contract）   ─── 字段/接口定义是否有歧义或遗漏？
        ↓
层2 前置检测（Guard）  ─── QC/脚本能否在问题到达用户前自动检出？
        ↓
层3 生成端（Source）   ─── 产生错误的代码是否直接修复，而非加 workaround？
```

**STOP 规则**：
- ❌ 只修层3（治标）：下次换个字段名还会复现
- ❌ 只加层2（打补丁）：根因仍在，QC 脚本会越来越臃肿
- ❌ 只改层1（写文档）：文档和实现仍然脱节
- ✅ 三层同时修复，每层都有可验证的产出
- ✅ 或明确标注某层 N/A，并用证据说明为什么不需要改

---

## 失败模式分类表（抽象 taxonomy）

按**根因位置**归类，用于快速定位问题属于哪一类。具体项目的真实案例见该项目 adapter。

| 类型 | 抽象症状 | 根因位置 |
|------|---------|---------|
| **字段名不一致** | 下游消费字段全为 null / 断线 | 生产方与消费方对同一字段的命名约定不同 |
| **分支提前 return 绕过通用检查** | 某类型分支的产物通过 QC，但下游消费崩溃 | 类型分支内部 return 之前未执行通用字段检查；专项分支必须在 return 前补齐共用校验 |
| **QC 覆盖盲区** | 某类错误通过了所有 QC，用户肉眼发现 | QC 脚本只检查"结构合规"，不检查"数值合理性" |
| **联合 QC 导致时机错误** | Task N 结束时跑 QC 报 FAIL，因依赖 Task M 的产物 | 将多个 Task 的检查项合并进同一脚本，违反"尽早失败"原则 |
| **枚举约束缺口** | 某输入既不满足分类 A 也不满足分类 B，无合法归属 | Schema 规则的边界区间未对齐，存在无法打出合规结果的空白区 |
| **Skill 调用中断主流程** | Skill() 调用返回后主任务停止，需用户催促 | Skill 工具调用会切换活跃任务上下文；错误地用 Skill() 做前置刷新 |
| **文档-实现脱节** | SKILL.md 描述了某规则，但对应脚本没实现；README schema 字段不全 | 文档与代码各自演化，没有机制强制同步 |
| **结构/位置不合理** | 某内容块放在错误的逻辑分组里 | 产物架构设计未严格区分不同职责层 |
| **LLM 完整透传缺乏约束** | LLM 自由填充的结构（如整个 dict 透传）出现非法 type / 数值不平衡 | 整块由 LLM 提供且无 type 校验、无数值平衡校验 |
| **跨字段内部不一致** | 同一产物内多个字段不满足应有的恒等关系 | 各字段来自不同代码路径，未做跨字段一致性验证 |
| **内容越界** | 某 section 包含了应属于另一 section 的内容 | 撰写指引只定义"写什么"，未定义"禁止写什么"；无内容边界 QC |
| **透传字段名偏离 schema** | 数据点缺失 / 轴空白 / key 与 data 不匹配 | LLM 写入时字段名与脚本约定不一致；脚本透传不校验字段名，QC 无法前置拦截 |
| **调用参数文档缺失** | 示例命令缺必填参数直接 exit；或枚举值直觉与实际不符 | 脚本 argparse 定义了 required 参数，但 SKILL.md 示例只写部分；枚举白名单只在 schema 里，文档无内联 |
| **helper 语义与 QC 不一致** | 同一业务概念在 helper 与 QC 中实现不同，导致 QC FAIL | 同一概念在 helper 和 QC 中有不同实现，根因是某一侧逻辑缺业务依据 |
| **schema-script-QC 三角不对齐** | schema 新增字段后 QC 没跟上，或 script 写入字段名与 schema 不一致 | schema（唯一真理来源）、生成脚本、QC 脚本三者独立演化，无强制同步机制 |

---

## 执行流程

### Step 0.A：自动收集失败证据（在用户描述症状之前先跑）

默认先执行本步骤；但如果用户明确指出某个具体文件/函数/症状，或上一轮已经收集过证据，可直接从该症状进入 Step 1，避免被过期评分牵偏。

目的：从结构化数据中提取失败模式，替代（或补充）用户口述，让后续溯源更精准。

**0.A.1 读最近一次运行的评分/状态文件**

```bash
# 通用：先定位当前目标 workflow 的评分/状态文件
find . -maxdepth 4 \( -name skill_score.json -o -name "*manifest*.json" -o -name "*status*.json" \) 2>/dev/null | sort
# 若用户给定运行目录，则优先在该目录及其父目录下找
```

- `hard=0`（或等价的硬失败标志）→ 从 `failures[]` 字段提取症状清单，每项作为独立症状进入 Step 1
- 有跳过项但无硬失败 → 记录但不作为主要症状
- 文件不存在 → 跳过此子步骤

**0.A.2 读最新 postmortem / review 的结构化失败列表**

```bash
find . -maxdepth 5 \( -name postmortem.md -o -name postmortem.json -o -name monitoring.json -o -name review.md -o -name "*manifest*.json" \) 2>/dev/null | sort
```

提取满足以下条件的项：
- `root_cause` 含 "schema" / "QC" / "harness" / "脚本" 关键词（工程类缺陷）
- 或 `fix` 字段提到了具体文件或脚本
- 或 review/postmortem 明确指出"QC 未检出 / skill 误导 / 字段漂移 / 产物路径错误"

**过滤原则**：只提取**工程类缺陷**（schema 设计、QC 缺口、脚本 bug），跳过**判断类问题**（叙事重心、概率分配、视角选择）——后者是业务问题，不是 harness-fix 的修复范围。

**0.A.3 汇总失败证据表**，输出格式：

```
失败证据汇总（自动提取）：
┌─────────────────────────────────────────────────────┐
│ #  来源            症状                             │
│ 1  skill_score     step QC: required field missing │
│ 2  postmortem      某字段缺失（schema gap）           │
└─────────────────────────────────────────────────────┘
工程类缺陷：N 条（进 Step 1）
判断类问题：N 条（跳过，记录供参考）
```

**0.A.4 与用户症状合并**：优先级 用户描述 > 评分失败 > postmortem 工程缺陷。

---

### Step 0.B：症状接收与分类

接收用户描述的症状（或从 review 报告中提取失败项），快速归类到上表的失败模式。

**从 harness-review 报告提取症状的方法**：
1. 找「建议修复优先级」表，按 P0 → P1 → P2 顺序处理
2. 对每个 FAIL 项，提取：维度（A-G）+ 缺口描述 + 改进建议
3. 将每项映射到本文「失败模式分类表」：
   - 维度 D FAIL（QC 脚本）→ 通常对应「QC 覆盖盲区」
   - 维度 D FAIL（依赖边界）→ 对应「联合 QC 导致时机错误」
   - 维度 G FAIL（行为/风格类）→ 对应「文档-实现脱节」（指令层面）
   - 维度 G FAIL（内容边界无 QC）→ 对应「内容越界」
   - 维度 F FAIL → 通常对应「Skill 调用中断主流程」或失败契约缺失
4. 每项作为独立症状进入 Step 1 溯源

若用户描述模糊且无法从 repo 证据推断，才问一个精确问题：**"这个问题是用户肉眼发现的，还是 QC 脚本已经报告了？"**

在 Default mode 下，优先从现有文件和日志做合理判断，不要因为可问可不问的问题阻塞修复。

- 用户肉眼发现 → 先做层2修复（补 QC），再做层1+3
- QC 已报告但未修复 → 直接做层1+3

---

### Step 1：根因溯源（Root Cause Analysis）

**不允许把猜测当根因**，必须通过工具验证；但允许先提出候选根因，再用 grep / 最小复现 / py_compile / QC 注入测试证伪或确认。

**1.1 失败链路追踪** — 画出问题的完整传递路径：

```
[产生源] → [中间环节] → [消费端] → [症状表现] → [检测点]
```

**1.2 关键溯源工具**

```bash
# 定位字段名来源（所有读取点）
grep -rn 'get("<field>' <scripts-dirs>

# 定位字段名定义（所有写入点）
grep -rn '"<field>' . | grep -v ".pyc"

# 比对文档与实现
grep -n "<field>" SKILL.md          # 文档侧
grep -n "<field>" <scripts>/qc_*.py # 实现侧
```

**1.3 schema-script-QC 三角 coverage 检查**（适用于"三角不对齐"失败模式）

```bash
# Step A：提取 schema 中所有必填字段名
python3 -c "import json,sys; s=json.load(open(sys.argv[1])); print(list(s.get('required',[])))" <schema.json>
# Step B：检查 script 写入了哪些字段名
grep -n '"<field>"' <scripts>/*.py
# Step C：检查 QC 覆盖了哪些字段名
grep -n '"<field>"' <scripts>/qc_*.py
# Step D：三角对比——schema 定义的字段，在 script 和 QC 中是否都出现？
```

**判定规则**：
- schema 定义了字段 X，但 QC 脚本中 0 行命中 → **QC 覆盖盲区**，进层2修复
- QC 检查字段 X，但 script 写入的是字段 Y → **字段名不一致**，进层1+3修复
- schema 定义 X、script 写 Y、QC 检查 Z → **三者全漂移**，从层1（schema）开始重新对齐

**1.4 失败链路完整记录格式**

```
产生点：[文件:行号] [字段名/行为]
传递路径：A → B → C
消费点：[文件:行号] [期望字段名]
QC 盲区：[哪个 QC 脚本应当拦截但没有]
用户暴露点：[用户如何发现]
```

---

### Step 2：三层修复

#### 层1：修复契约文档（先做，为后续修复提供正确的参考规范）

契约文档是**唯一真理来源**，修复后所有实现必须向它看齐：
- **字段 schema**：README / task reference 中的 JSON 结构示例——确保生产方写入、消费方读取的字段都在 schema 中明确列出
- **规则边界**：SKILL.md / schema 中的枚举约束、阈值——枚举规则不允许存在"空白区"；阈值来源必须有逻辑根据
- **时序约定**：QC 触发时机——联合 QC 是反模式，一个 QC 脚本只检查一个 Task 的产物

**检验标准**：任何一个新加入项目的人，只读契约文档，应能正确实现所有接口。

#### 层2：修复前置检测（QC 脚本）

| 时机 | 脚本 | 应覆盖的检查项 |
|------|------|--------------|
| 单 step 完成后 | 该 step 对应 QC | 只读当前 step 产物，做字段/数值/来源检查 |
| 跨 step 消费后 | 消费点 QC | 检查上游产物存在、已消费标记、关键字段被带入下游 |
| 终态产物完成后 | 终态 validator | 检查结构、引用完整性、跨层一致性 |
| 回填/复盘完成后 | 回填 QC | 检查状态确实变化、幂等覆盖、下一轮可消费字段 |

**QC 检查项编写规范**：每项必须有明确的权威来源、被检方、量化偏差阈值或布尔条件，退出码语义清晰（通常 0=PASS / 1=可修复失败 / 2=缺文件或 schema 错误；若脚本已有约定，以脚本现状为准）。

**QC 不允许做的事**：
- ❌ 在 QC 里"修复"数据（QC 是检测器，不是修复器）
- ❌ 吞掉异常（`except: pass`）
- ❌ 对已知问题写 `try/except` 绕过

#### 层3：修复生成端（代码直接修复）

**找到最初产生错误的代码行**，直接修复，不在下游加转换层：

```python
# ❌ 错误：在消费端加兼容（别名越来越多）
val = d.get("field_v1") or d.get("field_v2") or d.get("field")

# ✅ 正确：在生产端统一字段名，消费端只读一个（与 schema 对齐）
```

**访问方式**：`dict["key"]` → `dict.get("key")`（字段缺失返回 None 而非 KeyError，方便 QC 检出）；但 None 最终必须被 QC 拦截，不得静默传播到产出物。

---

### Step 3：回归验证

**3.1 正向验证**（修复有效）
```bash
python3 path/to/relevant_qc.py path/to/target_artifact_or_run_dir
```

**3.2 注入测试**（QC 能检出"坏数据"）——每次层2修复原则上都要做；若目标 QC 依赖外部行情/网络/大型真实产物，至少做隔离 smoke test 并在最终说明限制。

```python
# 标准注入测试模板：tempfile 隔离环境，注入坏数据，断言 QC FAIL，不污染真实产物
import json, tempfile, subprocess
from pathlib import Path

tmp = Path(tempfile.mkdtemp())
# 注入触发 bug 的最小坏数据（故意缺某必填字段）
(tmp / "artifact.json").write_text(json.dumps({"...": "..."}))

result = subprocess.run(
    ["python3", "path/to/relevant_qc.py", str(tmp) + "/"],
    capture_output=True, text=True
)
assert result.returncode != 0, "QC 应当 FAIL 但返回了 PASS"
print("✅ 注入测试通过")
```

注入测试失败（QC 没检出）说明层2修复不完整，必须加强 QC 再重测。

**3.3 反向验证**（修复不过度）：正常输入仍 PASS；不引入新的 FAIL 情形（尤其是层1枚举规则变更时）。

**3.4 全量回归**：如目标 workflow 有 eval/golden fixture 则运行；否则记录 N/A。

---

### Step 4：沉淀复用

| 沉淀类型 | 触发条件 | 产出形式 |
|---------|---------|---------|
| **更新契约文档** | schema/接口/时序规则变化 | README / task reference / 被修复 skill 的 SKILL.md |
| **更新 QC 脚本** | 发现新的 QC 盲区 | `qc_N.py` 新增检查项 |
| **更新 memory** | 行为约束（非代码）需在未来会话生效 | 项目的 agent memory 目录（路径以当前环境为准，先用工具确认） |
| **添加回归测试** | 高频失败模式（已出现 2 次以上）| `tests/` 或 `evals/` 新增 golden fixture |
| **更新项目 adapter 案例库** | 出现该项目特有的新失败案例 | 该项目 harness adapter skill 的失败案例小节 |

> ⚠️ 默认不要在普通业务修复中修改本文件（harness-fix/SKILL.md）。只有当用户明确要求优化 harness skill，或本文件本身的过期说明正在误导修复流程时，才可小范围修订。

### Step 5：最终汇报

最终回复必须区分：
- 已修复的工程问题（文件 + 行为变化）
- 生成/回填的业务产物
- 验证命令和结果
- 未处理的既有工作区改动（不要混入本次结论）

---

## 触发模式与输入格式

```
harness-fix                                   # 通用触发，后接症状或裸调用（分析最近的 bug）
harness-fix --symptom "<某产物字段全为 null>"
harness-fix --file <path/to/script>           # 针对特定文件做三层审查
```

| 输入形式 | 处理方式 |
|---------|---------|
| 具体症状描述 | Step 0 分类 → Step 1 溯源 → Step 2 三层修复 |
| QC 脚本 FAIL 报告 | 直接进入 Step 1（症状已明确）|
| review 报告（harness-review 输出）| 按 P0/P1 优先级逐项执行 Step 2 |
| 无参数（裸调用）| 从当前会话对话中提取最近一次 bug 描述，进入 Step 0.B |
| 评分 + postmortem（自动读取）| Step 0.A 自动提取工程类缺陷，与用户症状合并后进 Step 1 |

---

## 与其他 skill 的关系

| skill | 关系 |
|-------|------|
| `harness-review` | 输入端：harness-review 输出的 P0/P1 修复项可直接作为 harness-fix 的输入 |
| `harness-build` | 互斥：build 落地新功能，fix 修已知 bug；若需求其实是新增能力，改用 harness-build |
| 项目 harness adapter | 提供该项目的真实失败案例、路径与 QC 名称；溯源前先 Read adapter 案例库 |
| 域质量 review skill | 负责内容/业务判断；harness-fix 只处理工程稳定性、契约、QC、恢复能力 |
