# W023 发布并读回第 0 版初始状态

## 任务要求（PM）

**阶段为可执行，归属 M1 的 Stage 2。** 执行分支为 `codex/w023-atomic-baseline-publication`。以前置 [W021 候选](W021-proposed-initial-state.md#pm2-integration) 和 [W022 已验收的逐层校验](W022-layer-initialization-checks.md#pm2-integration) 为输入。执行 session 交付运行代码，独立 reviewer 复核方案与实现，PM 负责集成和阶段回归。

本次要让后续阶段能凭仓库里的版本号和引用，重新读到这次运行的起始版图。在已有的单进程仓库中完成。运行模式沿用当前支持的 `dummy_fixture / whole_intent`。架构依据为 [§2.3、§2.6、§3.8、§9.2、§11.8](../architecture.md)，样本与验收输入见 [W020 发布清单](W020/readiness.md)。本轮交付 `sealed_open` 的 Stage 2 交接。后续 M1 工作负责约束、目标闭合和导出。当前仓库只提供进程内原子性，样本覆盖 synthetic 范围。

| 验收项 | 输入、动作和可观察结果 |
| --- | --- |
| A1 同一次捕获能发布并读回 | 从正常 W003/W004 真实文件副本显式选择 [W022 完整 synthetic 坐标](W022/layer-discretization.synthetic.yaml)，重绑 query header，经 W006 → W020 → W021 → W022 走新入口。在空 lineage 首次发布后，由仓库引用读回不可变的第 0 版快照、一条 `InitializationEvent`、指向该快照的 head，以及已封存上下文的 attempt。正常输入由 revision 1 推进到 2，ECO 提交数为 0。消费者释放原候选后仍能按引用读取。 |
| A2 起始事实与保证范围 | 快照具备 §3.8 所列内容，按 §2.3 分清当前电路、独立目标及证据。读回实际 M1 线端 130 DBU²（GDS 偏移 2352）、LI 格片到物理分量和 R04/VSS 的来源、未知区域及外部 body 的证据范围。沿用实际坐标格号。另以 C13 核对 MN0 当前长度 4n、独立目标 5n，保留待处理差异。合成外部 body 背书及 LVS 状态维持原级别。 |
| A3 发布前置与拒绝 | 只接受与同一仓库、run、checkpoint 及候选绑定、在所声明能力下充分的依据。必投层缺声明、几何越界、混入另一捕获、引用不能解析或摘要不符时，保留可定位的原因。验证本次发布前后的 head、attempt 和初始化记录。已存在的输入审计可回查。POLY 声明二维且完整重建时允许普通占用通过，一维操作继续读取其单独的可用性。 |
| A4 原子性、并发和重放 | 在同一原子切换中创建快照/事件/head、封存上下文、推进 attempt 并登记幂等回执。核验预期 head、phase、revision 和模式。切换前注入故障，观察发布前状态。切换后丢失响应，同键同请求重放返回原引用。同键内容变更、陈旧 revision/head 有可区分的冲突。让两个已读取空 head 的 run 竞争同一 lineage，确认只产生一个第 0 版，落败方状态一致。 |
| A5 已有版本与阶段交接 | 新 run 请求已有 head 时，按 §2.3 加载该版并对封存的绑定做相容性校验。相容时经 `seal_context` 仅封存该 run 的上下文，head、快照和初始化事件数保持原值。用实际改变且重新绑定的工艺坐标或 evidence 验证不相容会被拒绝、原版仍可读。保留旧读入/失败终结和单 cell 只读分析行为。交一条实际文件示例，列出复跑命令、身份、影响范围和资源实测。 |

### 实施与验证约定

1. 先核对 [现有仓库](../../layauto_v2/repository/publication.py)、[中立发布类型](../../layauto_v2/domain/publication.py)、[候选](../../layauto_v2/state/mutation.py) 和 [逐层校验](../../layauto_v2/state/layer_checks.py)。以一个新 lineage 和一个已有 lineage 画出写入前后可见的对象与引用。说明哪些内容参与 snapshot binding 相容性、哪些仅用于追溯该次 run，并给出两次独立运行的正反例。准备回读、拒绝、故障及并发的观察方法。先交独立方案 review，再实施。
2. 遵守既有所有权。Pipeline 调用初始化事务。事务消费中立候选并构建 baseline 发布数据，repository 通过 `initialize` 在一个原子步骤中登记内容、head 和 attempt。检查新记录的版本、不可变性、来源和 digest，兼容已有 W006 记录。逐项核对现有证据，避免另建一份占用或物理图作为事实源。
3. 正常输入沿用 [W022 临时准备步骤](W022-layer-initialization-checks.md)，保留正常 target。W022 合同辅助函数 `sample(..., complete=True)` 另选了 C13，适合验证目标有差异的情形。固定 fixture、既有答案和历史证据均保留。
4. 开发、交付和独立复核按[验证分工](../collaboration/rules.md#verification-reuse)跑新增与受影响检查，包括仓库/codec、原 pre-context、模块边界和安装后的公开切片。首次走完整读回时测量新增耗时、内存和持有内容的体积，区分既有组装成本和发布增量。不同断言可共享同次真实捕获。重型检查串行。由独立 reviewer 从仓库读者的视角核验至少一项故障/并发及一项物理或来源见证，并复核发现的必须修正项。
5. **阶段验收由 PM 在实际合入 main 的 W023 版本上执行 Python 3.10、3.12 两次全量及发布组合检查。** 若实现触及无法划定的共享基础，按协作规则单列原因与追加检查。发布证据及限制一同推回执行分支。

## 执行 session 启动指令

> 在 `codex/w023-atomic-baseline-publication` 执行 W023 A1–A5。先用新建和复用已有第 0 版的两个例子说明哪些数据同时写入、失败后还能读到什么，交独立 reviewer 核对后实施。从实际文件跑通发布及回读，验证同请求重试、并发竞争、切换前后故障和绑定不相容。开发与交付跑新增及受影响检查。将实现、复现命令和独立复核结论推回原分支并报告完整 SHA，交 PM 集成及阶段全量。

## 方案与决定（执行准备，PM 接收）

1. **空 lineage。** A 用正常 target、W022 坐标和重绑 header 从 W006 取得 revision 1 的 checkpoint。Pipeline 从本仓库实际回读组装 W020/W021。初始化事务消费该候选，在同一对象上运行 W022；不足时返回层、原因与位置。事务冻结中立的版本化发布材料。仓库锁内先查该 operation/run/key 的完整请求摘要，再核对起始 head、phase、revision、模式、同一 checkpoint 及其可解析的审计和来源摘要。一次 root 切换发布 snapshot 0、InitializationEvent、head、context 及其回执，attempt 变为 sealed_open/revision 2，ECO 链为空。读者凭 head 和内容引用读回，原候选退出作用域。切换前中断所有新对象均不可见，切换后响应丢失按原请求读同一回执。
2. **已有 lineage。** B 请求 A 的 head。对 B 独立捕获的 URI 与实际 SHA-256（GDS、CDL、query/header/raw、body、全部 tech、配置与 policy）、版本化能力和模式做相容性核对。当前 synthetic header 本身绑定 target；同输入的新 run 可复用原版的不可变目标。run ID、创建键、绝对根路径、attempt/checkpoint/tool/parse/evidence 等 run 专属引用只用于本次追溯。加载原版并通过 seal_context 登记 B 的上下文、回执及 revision 2。B 不创建候选快照或再次初始化。改变有效坐标或 query 后重新绑定 header，拒绝 B 并保留其 revision 1、原审计、A 的 head/快照/事件。
3. **所有权与观测。** snapshot 只冻结 §3.8 各权威组件及来源 ID，原格号、精确片段、region/node/component 与 annotation/evidence 引用贯通。目标与差异在独立不可变上下文中。新记录用封闭版本和内容摘要；旧 W006 字节与引用保留。重放先于 guard；比较故障前后完整仓库观测。两个 run 都读到空 head 后分别完成准备，从屏障同时提交，核对唯一版、落败方 checkpoint 及 revision。另用 C13、缺声明、越界和二维 POLY；串行对重型组装和发布/读回分别计时、记录 RSS 与持有体积。独立 reviewer 先核方案，再从仓库读者视角实查故障或并发及物理来源。

方案在实现前由独立 reviewer 核对并接收。[方案复核](W023/plan-review.md)

## 执行结果（执行）

受测产品提交为 `9f6fa09ce79c2b9c731c909b5a2e526a06e66c47`，执行分支为 `codex/w023-atomic-baseline-publication`。[复现命令、环境和验证分工](W023/verification.md) · [正常文件示例](W023/example.py)

| 验收项 | 结果 |
| --- | --- |
| A1 | W003/W004 正常文件副本选择显式 W022 坐标并重绑。空 lineage 只发布一次 version 0；读者可释放候选，从 sealed_open/revision 2 的 attempt 读回 context、head、快照、独立目标与 InitializationEvent，ECO 提交数为 0。 |
| A2 | 40 条原图、220 个 drawn 片和 92 个 effective 片。M1 (2,2) 读回 130 DBU²、GDS 偏移 2352。LI (1,3) 经 region/node 查物理分量，并由覆盖该片的 R04 追到 VSS。未知导体保留 suspect 标记，外部 body 保留 synthetic 范围，LVS 为 not_run。C13 读回当前 MN0 为 4n、目标 5n，并保留待处理差异。 |
| A3 | 缺必投层声明、MARKER 越框、外来候选、预算不符、损坏或缺失的引用均被定位。失败后核对原审计和仓库观测。完整二维 POLY 允许占用通过，同时读出一维轨号不可用。 |
| A4 | 切换前故障无新增记录。切换后丢失响应，用原请求重放取回原引用。变更同键内容、陈旧 revision 或 head 分别收到相应冲突。两个已读空 head 的 run 同时发布，只增加一版；落败方保留 revision 1 及 checkpoint。 |
| A5 | 新 run 在另一绝对目录捕获相同文件，经 seal_context 复用原 head、快照与事件。实际更改 M1 坐标或 R04 query 后重绑，拒绝封存，原版可读。复用前也逐项解析初始运行的证据链。 |

新增检查 12 项、受影响检查 129 项全部通过，mypy 检查 88 个源文件通过。独立 wheel 中测得组装 44.6967 秒、校验冻结 1.2269 秒、发布 1.3107 秒、完整读回 0.3983 秒；仓库新增持有 547,137 字节。[实测数据与输入身份](W023/evidence/readback.json)

交付范围为单进程仓库、synthetic 输入、`dummy_fixture / whole_intent` 的 Stage 2。阶段双解释器全量和实际合并版发布组合由 PM 验收。

## Review 结论（reviewer）

独立复核通过。受测实现 `9f6fa09ce79c2b9c731c909b5a2e526a06e66c47` 已修复候选预算与请求不一致、已有版本的原捕获链断裂仍可封存两项问题。独立探针逐项验证拒绝且无部分写入，确认切换后中断可重放；从 GDS 原字节独立核对全部 4 条 M1 原图和 10 个格片。剩余必须修正项为 0。[独立复核、版本及复跑命令](W023/code-review.md)

## PM 验收与交接（PM）

当前派发执行。首次发布和阶段全量尚待实施、集成及实跑。
