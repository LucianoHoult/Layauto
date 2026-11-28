# W027 核对全部目标，在受检版本上记录无修改结果

## 任务要求（PM）

**阶段为可执行。** 在 `codex/w027-no-change-closure` 承接 M1 的 Stage 4 和 Stage 5 无修改路径。用户交给程序正常样本后，应能读到本次运行为什么无需改图、实际在哪一版上查过哪十条规则，以及最终的 Stage 5 记录。若目标不符或规则违规，应能定位到对应器件、图形和输入。

Stage 4 消费已封存的当前电路、独立目标、全部归一化差异及所需版图提取事实，绑定判定所使用的版本。证实目标已满足才返回 `NoChangePlanningResult`。Stage 5 在同一版本正式调用 [W026 的整包检查](W026-connector-enclosure.md#pm2-integration)。十条必需规则均通过、该运行的 ECO 链为空，且关闭时仓库 head 仍匹配受检 head，才冻结 `no_change`。Stage 6 随后从关闭记录读出受检版本，在后续任务实现导出、回读和 terminal。当前范围为进程内仓库、synthetic 单 cell、whole-intent。[架构 §2.5–2.7、§7.1](../architecture.md#stage5-rule-invocation) · [W003 记录合同](W003/contracts.md)

### 从实际文件验证的样本

用 W003/W004 原文件、W022 完整坐标及现有 header 重绑步骤建立第 0 版。[原始失败案例及预期](../../tests/fixtures/w003_m1/failures/cases.json) · [Stage 2 发布与复用](W023-atomic-baseline-publication.md#pm2-integration)

| 输入 | 要验证的结果 |
| --- | --- |
| 正常 source/target CDL 的空白及参数顺序不同，几何实测 MN0/MP0 为 5/7 | Stage 4 按规范化语义与实际提取事实确认全部目标已满足；Stage 5 在绑定快照上实算 T01–T10，关闭后从仓库引用读回本次结果、十条状态、原快照与空 ECO 链。 |
| C13 `unsupported_target`，FIN 相同，MN0 长度从 4n 变为 5n | 全部目标准入能找到这一项不支持的变化，保留 `UnsupportedTargetAxis` 和双方 CDL 位置，记录失败。再用同一输入包含多项差异的对照核对完整性。 |
| C16 `extraction_mismatch`，MN0 几何只计 4，source 仍写 5 | 保留 `ExtractionCountMismatch`、几何与 CDL 来源。即使 source 和 target 声明相符，实际计量差异也阻止无修改结果。按实际到达阶段记录失败。 |
| C14 与 C15，以及 W026 已有的双违规组合 | 电路目标满足，仍须在 Stage 5 执行必需规则。C14 报 T07 的 4/5 nm；C15 报 T05 的 −3 nm 包围余量；组合版从同一次正式检查中读回两项独立原因。原 head、快照及空 ECO 链可读。 |
| 删除 T07 声明并重绑工艺的已知可发布对照 | 从 W026 的合同取样。Stage 5 记录缺少 T07、规则目录位置和阻止成功关闭的策略；其他可求值规则保留独立结论。[已有公开检查](../../tests/contracts/test_w026_policy.py) |

PM 在 W026 合并版 `176326e` 以 Python 3.12.14 实跑 C16。该输入能发布第 0 版，源与目标之间有 0 项归一化差异，MN0 从实际版图提取到 4 条 FIN，两份 CDL 第 3 行均要求 5 条。这个输入可直接检验 Stage 4 是否同时使用语义和提取证据。复跑命令为 `PYTHONPATH=.:tests/contracts python -B docs/tasks/W027/pm_c16.py`。[输入准备和读回](W027/pm_c16.py)

### 验收项

| 项 | 可观察结果 |
| --- | --- |
| A1 方案与独立复核 | 先画清从已发布输入、目标与原始证据到判定、规则报告和仓库关闭记录的路径。逐项注明已有生产者、事实不足或冲突时的处理、进入成功分支的条件。审阅现有 W006 失败记录与 W023 身份/重放合同，先独立复核再实施。 |
| A2 Stage 4 | 从真实发布入口接入；选定 cell 全部规范化目标及其有依据的物理量须得到明确判断。空 diff、单独的 FIN 计数或旧规则报告均不足以证明全部满足。返回绑定本次 run/context、目标和基础快照的只读判定；无需修改时，候选与修改操作均为空。未支持、已有提取矛盾或缺少必需事实分别保留原因。 |
| A3 Stage 5 | 用现有整包入口在同一受检版本显式求值，冻结可定位的逐条结果及来源。违规、必需项缺失、待求值、不确定或执行错误都阻止成功；保留可独立取得的原因。用组合违规和至少一个无法判定或出错的对照验收。Stage 4 已拒绝时，记录实际完成的工作。 |
| A4 关闭与重试 | 按架构的 `close_stage5` 由仓库在同一原子操作中冻结 RunRecord、Stage5Closure 和 attempt 更新，`sealed_open → stage5_closed`；成功与失败均保持已发布版图，成功记录指向实际受检快照。测试过期 head/attempt、跨 run 或错配引用、重复请求、同键改内容及关闭前后中断；丢失响应时同一请求可读回原结果。RunRecord 冻结失败沿用规定的独立失败分支。验证已有 W006/W023 记录可读和单进程边界。 |
| A5 交付 | 用公开入口交付正常与失败样本的可运行示例，从仓库读回状态和证据；记录目标判定、规则求值、关闭的耗时。复用已绑定输入与已有算子，避免每条规则重新发布。独立代码复核、修正后定向复验；开发及交付运行新增和受影响测试、typing 及必要的安装入口 smoke。PM 在本节点实际集成版本上运行 Python 3.10/3.12 双全量和组合验收。[验证分工](../collaboration/rules.md#verification-reuse) |

## 执行指令

> 沿用独立执行 session，在 `codex/w027-no-change-closure` 按 A1–A5 交付正常无修改和对应失败路径。先独立复核方案，复用已发布事实和 W026 十条检查，按绑定版本原子关闭本次运行，并独立复核实现。把实现、复现命令、实测范围、证据及完整 SHA 推回原分支，交 PM 集成。真实修改及候选传播在 M2；导出产物与运行终态在 Stage 6。

## 执行交付

分支从 `b94c03e83fe16b7037a103e1c76e24e14a5a2f56` 开始。A1 的独立复核在实施前完成。A2–A4 的最终实现与测试提交为 `86cafe8f06b622d22f80b4b8f35d4ec50beb7579`。正常样本从仓库读回 `stage5_closed`、受检的第 0 版、十条通过及空 ECO 链。目标拒绝和规则拒绝各自保留实际到达阶段的审计。PM 可依照交接中的命令在实际合并版验收。

| 验收项 | 分支内材料 |
| --- | --- |
| A1 | [方案](W027/plan.md) · [实施前独立复核](W027/plan-review.md) |
| A2、A3 | [正常和失败样例](W027/example.py) · [按原始 CDL 和 GDS 独立核值的合同](../../tests/contracts/test_w027_cases.py) · [规划边界](../../tests/contracts/test_w027_planning.py) |
| A4 | [版本、竞争、存储、冻结与重放合同](../../tests/contracts/test_w027_boundaries.py) · [旧记录内容地址](../../tests/unit/test_w027_wire_compatibility.py) |
| A5 | [复现命令、检查范围及耗时](W027/handoff.md) · [仓库读回证据](W027/sample-results.jsonl) · [独立代码复核与问题复验](W027/code-review.md) |
