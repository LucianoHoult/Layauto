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

待执行 session 填写方案、样张与 review 位置。

## 执行结果（执行）

待记录受测提交、实际输入、命令、资源实测及结果。

## Review 结论（reviewer）

待独立 reviewer 记录范围、发现及复核结论。

## PM 验收与交接（PM）

当前派发执行。首次发布和阶段全量尚待实施、集成及实跑。
