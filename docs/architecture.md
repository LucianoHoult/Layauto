# Layauto architecture

> **文档定位。** 本文描述 Layauto v2 的目标架构：它以 backlog 中已经识别的关键问题为约束，重新定义事实源、状态所有权、修改语义、约束检查、事务提交、导出与验证边界。现有实现下文统一称为 **legacy MVP**，只作为 legacy/reference implementation 与可复用代码来源；它跑通过端到端链路，但不作为目标架构的正确实现基线。本文中的 **v2 MVP** 则指目标架构的首个实现范围。具体开发顺序、任务拆分与 agentic coding 执行计划应另行维护。
>
> **仓库定位。** `docs/architecture.md` 是当前 docs 下唯一 active v2 architecture source of truth。原 backlog 与 correctness audit 的要求已吸收到本文第 13 节及相关主体章节；旧版 MVP flow 已删除；历史 changelog 已归档到 `docs/archive/changelog.md`。legacy MVP 实现已整体移入 `legacy_mvp/`，只作参考与选择性代码复用来源；新的 v2 实现应落入 `layauto_v2/`。

## 1. 项目定位与目标边界

### 1.1 Layauto 要解决的问题

Layauto 是面向 FinFET 标准单元的**增量式版图自动修改框架**。它不从零 placement / routing，也不试图替代 foundry PCell 或完整 signoff flow；它在已有 GDS 几何、CDL 电路语义、LVS/Calibre annotation、工艺规则与工程约束的共同基础上，对 target intent 所描述的局部变化进行受约束、可追踪、可验证的版图修改。Target intent 通常来自 source/target CDL diff，也可以来自显式 ECO command、用户 intent 或经归一化的上一轮 signoff feedback。

核心问题可以概括为：

> 当目标 intent 要求某个标准单元发生局部变化时，系统应如何从真实工程事实出发，规划合法修改，提交到唯一权威状态，并导出可验证产物。

这里的“真实工程事实”包括四类：

- GDS / lossless normalized geometry 提供的几何事实；`bbox_by_layer` 只用于已声明的 flat-rectilinear subset。
- CDL / target intent 提供的电路语义事实。
- Calibre / LVS query 提供的 annotation 与 identity join 事实。
- Tech bundle 提供的 layer、坐标、规则、连通与派生 policy 等技术事实。

`site_config`、tool mode、export / validation policy 只选择一次 run 如何读取、执行和验收，不是 design truth 或 tech truth；它们不能覆盖上述事实。

### 1.2 v2 架构目标

v2 的目标不是把 legacy MVP 局部修补到“能继续跑”，而是重新收敛到以下架构原则：

- **事实源清晰。** 几何、语义、annotation、派生视图各有明确来源，不互相伪装。
- **状态所有权单一。** 版图几何和 occupancy 不应在 parser、grid、engine、decoder、output JSON 中形成多个互相漂移的权威副本。
- **修改语义基于物理实体。** 例如 `nfin` resize 不是删除 FIN，而是改变 OD active coverage，并触发相关 routing / via / derived marking 修复。
- **规划先于提交。** macro / planner 产生 candidate；constraint engine 判断可行性；transaction commit 成功后才更新权威状态。
- **导出不是修补。** Stage 6 只从 committed snapshot 导出 GDS / CDL / JSON / SKILL / report / validation result，不再作为 canonical writeback 阶段。
- **面向 agentic coding。** 模块边界、接口合同、失败条件和 backlog highlights 应足够明确，使后续开发任务可以被拆分、验证和审计。

### 1.3 Legacy MVP 的角色：reference / reusable code source

legacy MVP 以单级 inverter fixture 跑通了从 CDL diff 到输出 GDS / CDL / JSON / report 的端到端链路：输入版图中 NMOS / PMOS 的 `nfin = 5 / 7`，目标 CDL 要求 `nfin = 4 / 6`。这个 fixture 仍有价值，但它有三种限定角色：

1. **Legacy implementation.** 当前路径包含已知架构债，例如 FIN 可编辑、Stage 6 writeback、shape_pool 漂移、legacy JSON 输入、fixture correctness gap 等，不应作为目标设计参考。
2. **Reference behaviour.** 它可以帮助定位哪些已有代码逻辑可复用，例如 CDL parser、Calibre query parser、tech config loader、部分 GDS IO 和测试 harness。
3. **Regression seed.** 它可继续作为 v2 初期合成测试来源，但 fixture 应逐步改为基于真实 Calibre query 事实构建，而不是保留 legacy convenience JSON 作为主路径。

因此，architecture 主体描述 v2 目标状态；legacy MVP 与目标状态的差异只在必要处作为 warning 或 backlog highlight 出现。架构义务以本文前 12 节及第 13 节覆盖矩阵为准；后续 plan 只维护开发顺序、任务拆分和验收安排，不能覆盖本文合同。

### 1.4 支持范围与暂不覆盖范围

**v2 优先支持范围：**

- 单个标准单元内的增量 ECO。v2 MVP 的最低 acceptance capability 是 fixed-frame `nfin` shrink：更新 current semantic / OD active coverage，并对 candidate 实际触及的 LI / VIA0 / M1 / cut 提供 concrete repair；任一必要 repair capability 缺失则该 intent typed-unsupported。Grow 与其它 action 只有在 capability registry 显式声明时才支持，否则 typed-fail。
- 固定 standard-cell frame：cell boundary、VSS/VDD rails、FIN backdrop、rail-side gate endpoints、NWELL / BOUNDARY 与 M1 rail topology 原则上保持稳定；LI / VIA / local routing 只在受影响局部、经 constraint 检查后修复。
- 以 GDS 几何 + Calibre query bundle + CDL 语义构建 layout state。
- 在 planner / constraint / transaction 边界内完成候选修改、可行性判断和提交。
- v2 MVP 从 committed snapshot 导出 GDS / CDL / JSON / report / machine-readable validation result；SKILL / Virtuoso mirror 与真实 Calibre signoff 通过 policy-enabled Stage 6 扩展点接入，可以明确 defer 到 post-MVP。

**暂不作为 v2 初始目标：**

- 跨 cell / multi-cell routing 与全局优化。
- 从零 placement / routing 或由 netlist 合成完整新版图。
- 完整 device add / device remove / buffer insertion / arbitrary net reroute 的生产级实现。
- M2 及以上完整金属栈、多重图形化、cut-mask、coloring 的完整 signoff 语义。
- 完整 foundry DRC / LVS signoff 自动闭环；v2 先定义可接入边界。

### 1.5 架构核心闭环

目标闭环是：

```text
target intent
  → evidence acquisition
  → fact normalization / annotation overlay
  → authoritative layout state + derived views
  → candidate planning
  → transaction-private base materialization
  → constraint feasibility check
  → annotation / derived finalization
  → atomic CommitEvent + immutable snapshot publication
  → export + validation
```

Validation / tool feedback 若要触发下一次修复，只能作为**下一轮 run** 的 Stage 1 evidence，再经 Stage 2 归一化为 typed intent；Stage 6 不得在当前 run 内据此 patch committed snapshot。

这个闭环中有两个关键断点：

- **commit 之前**只有候选和事务上下文，不能把几何修改提前写成事实。
- **commit 之后**exporter 只能读取 committed snapshot，不能再修补内部状态。

## 2. 总体数据流与阶段边界

### 2.1 Stage 编号约定

v2 采用连续的 Stage 1–6，不再使用 legacy MVP 中的 “Stage 1.5”。Calibre / LVS query bundle 是输入证据获取的一部分，归入 Stage 1；annotation refresh / invalidation delta、derived markings finalization 与 read-view invalidation 是 Stage 5 原子发布的一部分；导出和验证统一归入 Stage 6。

| Stage | 名称 | 目标职责 | 不应承担的职责 |
|-------|------|----------|----------------|
| Stage 1 | 输入证据获取 | 读取 CDL、GDS/geometry、Calibre/LVS query bundle、tech bundle 与 site/run config，形成 raw captures + schema-canonical evidence records | 不构建工作状态，不做 identity/spatial overlay，不做几何修改 |
| Stage 2 | 语义/空间归一化与状态构建 | 构建 current semantic state、immutable TargetCircuit / TargetIntent、几何 store、坐标系统、annotation state、occupancy / connectivity 与初始 views | 不做 ECO 修改，不复制多个权威几何源 |
| Stage 3 | 约束上下文初始化 | 基于 Stage 2 的坐标系统、occupancy 与 connectivity 初始化 constraint engine、rule context、domain / trail | 不重新拥有 layout state，不规划修改，不提交状态 |
| Stage 4 | 修改意图与候选规划 | 把 Stage 2 归一化后的 typed target intent 转换为 candidate plans | 不直接消费 raw diff / raw command，不绕过 state / grid 手工拼最终 bbox，不提前 side-effect |
| Stage 5 | 可行性检查、事务提交与派生刷新 | 在 transaction-private overlay 中检查并 finalise base / annotation / derived state，再原子发布权威状态、CommitEvent 与 snapshot | 不暴露半提交状态，不导出文件，不把 output 当状态源 |
| Stage 6 | 导出、生产工具交互与验证 | 从 committed snapshot 导出 MVP artifacts，并按 policy 运行可选 production integration / signoff / report | 不 mutate Layauto AuthoritativeState，不把工具输出反向 patch 成事实 |

### 2.2 Stage 1：输入证据获取

Stage 1 的输出是 raw captures、schema-canonical evidence records、已校验的 tech models 与 run config，而不是 layout model。这里的 canonicalization 只做格式/schema 解析、显式单位解码及 provenance 保留；identity join、空间投影、annotation overlay 和 current/target state construction 属于 Stage 2。Source evidence → schema-canonical unit decode 只能发生一次，并必须保留 original value / unit / precision backlink；Stage 6 canonical → artifact unit / DBU serialization 是独立的纯输出变换。

输入包括：

- Source CDL，以及 target CDL / ECO command / 用户指定 intent / 未来 signoff feedback raw input 中至少一种 target-intent source；多种并存时 Stage 2 必须验证一致性。
- 原始 GDS / lossless normalized geometry；只有通过 flat-rectilinear capability check 时才可使用 round-trip `bbox_by_layer`。
- Calibre / LVS query bundle：`ixref`、`net_xref`、`device_info`、`net_shapes`。
- 技术配置：site config、layer map、Calibre layer map、DRC rules。

Stage 1 应做的事：

- 解析 source CDL；若提供 target CDL 则提取 target circuit / raw diff，若提供其它 raw intent 则保留为待 Stage 2 归一化的 evidence。
- 运行真实 Calibre query 或读取 dummy fixture raw captures，保存可审计的 raw query output 与 schema-canonical evidence YAML/对象；这些对象仍不是 domain/layout facts。Dummy fixture 必须以 raw captures 为源并走同一 parser / schema，不得绕回 legacy `calibre_device_query.json` / `calibre_net_query.json` 主路径，也不得用 normalized-only input 绕过 parser。
- 从 GDS 读取 lossless geometry；仅对通过 capability check 的 flat-rectilinear subset 归一为 `bbox_by_layer`，并保留未 annotation 的几何。
- 校验 evidence 的基本格式一致性，例如 cell-name / identity 字段、单位与 layer name 是否存在且可解析；跨 evidence 的 canonical identity join 由 Stage 2 执行。

Stage 1 不应做的事：

- 不应把 legacy `calibre_device_query.json` / `calibre_net_query.json` 当作 v2 主输入。
- 不应根据 query 结果直接生成 `Device.fin_track_indices` 或 `Net.segments` 等工作状态。
- 不应进行 resize 或任何几何写回。

### 2.3 Stage 2：事实归一化与 layout state 构建

Stage 2 的核心不是创建某个固定 package tree，而是把 Stage 1 的 schema-canonical evidence 做 semantic / identity / spatial normalization，形成几类**来源清楚、生命周期不同、后续消费者明确**的事实对象；raw CDL diff、raw ECO command 或 raw signoff feedback 也在这里归一化为 typed target intent。Current circuit state 从 source CDL 初始化、可由 Stage 5 commit 更新；target circuit / target intent 是 immutable reference，不被 commit 改写。下面出现的 `domain.*` / `state.*` / `annotation.*` 名称是建议实现落点，用于表达职责边界；真正的架构要求是数据所有权和依赖方向，而不是这些目录名本身。

Stage 2 产生的六类主要事实对象如下：

| 归一化产物 | 主要来源 | 建议实现落点 | 后续消费者 | 不应承担的职责 |
|------------|----------|--------------|------------|----------------|
| Current semantic state | Source CDL | `domain.circuit` 定义 value types；`state.semantic` 持有 current state | planner、transaction、CDL exporter、report / validation | canonical `DeviceId` / `NetId` 使用 cell/schematic scope；只由 commit 更新，不拥有 LVS join 或 layout anchor |
| Immutable target reference | Target CDL / raw intent 经 Stage 2 归一化后的 `TargetCircuit` / `TargetIntent` | `domain.circuit`、`domain.intent`；由 RunRecord / snapshot context 引用 | planner、whole-intent closure validation、report | 不属于 `AuthoritativeState` 的 mutable current semantic component，不被 commit 改写 |
| Geometry store | GDS / lossless normalized geometry；capability-scoped `bbox_by_layer` | `state.layout_store` | annotation overlay、occupancy projection、planner、transaction、exporter | 不直接解释 schematic identity，不丢弃所声明 capability 内的 unannotated geometry |
| Annotation state（由 overlay 产生） | Calibre query bundle：`ixref`、`net_xref`、`device_info`、`net_shapes` | `annotation.layer_overlay` 产生 `CellId`-keyed state；`state.annotation` 受事务管理 | planner、constraints、DRC/LVS localization、coverage report | 不替代 GDS 几何事实；shape/component 只保存可重算 summary |
| Occupancy store | geometry store + layer tier + Stage 2 coordinate system | `state.occupancy` | constraint engine、planner、transaction、connectivity、read / export views | canonical discrete geometry abstraction；不是 raw geometry source，但作为候选修改、CSP 检查和 commit 的主要工作基底 |
| Connectivity state | occupancy + via edges + cut barriers + diffusion sharing / split policy + annotation refs | `state.connectivity` | constraint engine、router、transaction、validation / report | occupancy 上的 topology interpretation；不等同于 `net_id` label，不承担 semantic netlist ownership |

这些对象的产生顺序是有依赖关系的：source CDL 形成 current semantic state；target CDL / raw intent 单独形成 immutable target reference；GDS evidence 先形成 geometry store；tech layer map / rule deck 先形成 Stage 2 coordinate system（layer grid、track coordinate、B-tier axes）；geometry store 再结合 coordinate system 和 layer policy 投影为 base occupancy；Calibre evidence 通过 layer mapping 和 tolerance policy 形成 `CellId`-keyed annotation state，occupancy record 只引用该 state；enriched occupancy 再结合 annotation / conservative policy，连同 via / cut / diffusion sharing 语义形成 connectivity state。Read / export views（routing spans、gate tracks、fin attribution、annotation coverage、artifact edit view 等）只从这些权威对象重算或缓存，不作为新的事实源。

Stage 2 的关键原则：

- GDS / lossless normalized geometry 是几何事实源；bbox 只覆盖已声明 subset；LVS shapes 是 annotation 与 identity evidence，不是完整几何替代品。
- `Device` / `Net` 是语义 IR，不应长期保存可从 layout store 推导的几何副本。
- Annotation overlay 是 evidence-to-identity 的解释过程；其权威结果进入 AuthoritativeState 内 `CellId`-keyed annotation state，occupancy / shape / component 只持有 reference 或可重算 summary。Overlay 算法本身不拥有 layout state。
- Grid / coordinate system 在 Stage 2 建立，用于 geometry-to-cell projection；它是坐标系统，不能成为 layout occupancy 的长期 owner。
- Constraint engine 可以建立检查用 cache / trail，但不能成为 occupancy 或 connectivity 的另一份权威副本。
- Unannotated shapes 必须保留，并按保守策略作为 blockage / suspect geometry 进入后续判断。

Stage 2 的退出合同是一次只用于 baseline construction 的 `InitializationTransaction`：它不能应用 target ECO，只能从 evidence 构建 state、按同一 annotation / connectivity / C1 derivator 合同完成一致性检查，并原子发布 `state_version = 0`、baseline snapshot 与 `InitializationEvent`。Input GDS 中的 C1 shape 只能按 tech policy 与 derivator 结果比较：`recompute` 模式以重算结果为权威，`validate_and_adopt` 模式必须先证明在声明 tolerance 内等价；缺少所需 derivator 或比较失败时不得发布 baseline。Stage 4 必须持有该 versioned baseline snapshot / `base_snapshot_id` 才能开始。Initialization 不是 ECO CommitEvent，也不能绕过 Stage 5 对后续 mutation 的唯一门。

### 2.4 Stage 3：约束上下文初始化

Stage 3 初始化“判断候选是否合法”所需的约束上下文。它读取 Stage 2 已经建立的 coordinate system、layout state、occupancy 与 connectivity，但不重新构建或拥有这些状态。

主要内容：

- 读取 Stage 2 已建立的 layer grid、track coordinate、B-tier axes 等坐标系统。
- 加载 DRC rule records 与 rule predicates。
- 建立 constraint engine 的 domain / trail / propagation context。
- 接入 Stage 2 的 occupancy store 与 connectivity index。
- 标记固定几何、blockage、cut barrier、via edge、diffusion sharing 等约束语义。

v2 的目标合同是：constraint engine 不拥有 layout state，也不维护一份可与 layout store 漂移的 occupancy copy；它只在 Stage 2 的 coordinate system、occupancy 与 connectivity 之上叠加 rule predicates、domain、trail、propagation context 和 candidate feasibility API。

允许为了性能建立检查用 cache / index，但这些 cache 必须可由 Stage 2 state 重建，有明确 invalidation 规则，不作为 authoritative occupancy / connectivity，也不能被 planner、transaction 或 exporter 当作 layout truth。

### 2.5 Stage 4：修改意图与候选规划

Stage 4 将 Stage 2 归一化后的 typed target intent 转换为 candidate plans；它不直接消费 raw CDL diff、raw command 或 raw signoff log。

以 `nfin` resize 为例，planner 应解释：

- 目标设备是谁。
- semantic delta 是什么，例如 `MN0.nfin: 5 → 4`。
- 该 delta 对物理实体的正确作用是什么，例如 OD active coverage 改变，而不是 FIN 删除。
- 可能受影响的 LI / VIA / M1 / C1 derived markings 是哪些。
- 是否需要 LI / VIA / M1 / cut / derived marking 局部 repair 或候选排序。

Stage 4 的候选是“待检查计划”，不是已提交修改。它可以包含 grid cells、shape ids、semantic ids、repair requirement、old/new coverage、预期 derived refresh region、provenance seed 等，但不能把候选直接写成 committed geometry。

Unsupported intent 应在 Stage 4 显式失败。失败结果应说明：哪个 intent 无法被当前 planner 覆盖、是否有部分候选被拒绝、系统是否已经保持无副作用状态。

一个 executable `PlanningResult` 只绑定一个 `base_snapshot_id`，并且至多对应下一次 publication group。默认 `whole_intent` 时，该 group 覆盖全部 target delta。Explicit partial policy 则由 pipeline 执行受控的 Stage 4 → Stage 5 迭代：每个 CommitEnvelope 发布后，以它的新 snapshot 和同一 immutable TargetIntent 重新计算 remaining delta、重新做 capability admission，并生成下一份 PlanningResult；上一轮 candidate / precondition 不得复用。Stage 5 只接受匹配当前 parent snapshot 的结果，不负责 rebase 或 replan。若后续 replan 失败，按 partial-policy terminal failure 记录已提交、失败与未应用 delta。

### 2.6 Stage 5：可行性检查、事务提交与派生刷新

Stage 5 是唯一可以把候选变成权威状态的阶段。

流程：

1. 接收带 `base_snapshot_id`、old-state preconditions 与 `apply_atomicity` 的 selected plan group，并打开 transaction-private overlay / checkpoint。
2. 将 Stage 4 已具体化的 proposed base mutations 应用到 transaction-private overlay，并把 planner 的 annotation refresh / invalidation request 交给 `annotation/` 生成 tentative `AnnotationState`，再更新 tentative connectivity；未具体化的 required repair 不可执行。Planner 不得直接给出任意 annotation value delta。
3. Constraint engine 根据 tech / layer / action policy 独立补全 mandatory checks，并从 staged delta 重算、扩张 affected scope；candidate 自报的 checks / region 只能增加检查，不能缩小检查范围。
4. 在 overlay 中运行 DRC / connectivity / blockage / intent-invariant / rule feasibility check；任何 stale precondition 或检查失败都丢弃 overlay，并生成结构化失败结果。
5. 检查通过后，在同一 overlay 中 finalise annotation attribution / validity；若结果影响 diffusion split / sharing 等 annotation-dependent topology，必须更新 connectivity、扩张 affected scope 并重跑相关 mandatory checks。随后 finalize C1 derived markings，并刷新或 invalidate component summaries 与其它 non-geometry read views；任一 finalization / post-finalization check 失败都必须整体回滚。
6. 按 `apply_atomicity = whole_intent | dependency_group | candidate` 原子发布 `CommitEnvelope`：新的 AuthoritativeState version、immutable snapshot、ChangeSet、CommitEvent 与 per-publication `CommitAuditRecord`。默认是 `whole_intent`；该单-envelope 路径必须把 final RunRecord 与 CommitEnvelope 放在同一 Stage5CompletionEnvelope 原子 batch，RunRecord freeze 失败即不发布 commit。更细粒度发布必须由 explicit partial-apply policy 启用并进入 report；它在所有 plan groups 结束后冻结唯一 run-level RunRecord，引用 ordered commit ids 与 final snapshot。若该 final freeze 失败，earlier envelopes 不伪装回滚，但 PipelineResult 必须 fail / requires-review 并阻止正常 Stage 6 export。

Stage 5 的合同：

- 失败的 plan group 不得留下 partial edit；whole-intent / dependency-group policy 下，组内后续 candidate 只能读取同一 overlay 中的 tentative state，直到整组一次发布。
- Candidate-level policy 下，已发布 candidate 通过新 snapshot 对下一轮 Stage 4 可见；下一个 candidate 必须基于该 snapshot 重新生成。该 partial-apply 语义必须显式启用、可审计，且不需要等 Stage 6 decoder 回放。
- Commit 的目标是 authoritative layout state，而不是 output JSON、legacy edit stream 或 exporter-side patch。
- Derived markings finalization 位于 Stage 5 transaction 内、tentative base materialization 之后、CommitEvent / snapshot 原子发布之前；它不是 Stage 6 side effect。
- v2 不把 legacy L1 EditOp / ShapeEditRecord 作为核心状态模型；Stage 5 产生的是 ChangeSet / CommitEvent，Stage 6 如需 SKILL 或 diff visualization，可从 ChangeSet 派生 artifact-specific ExportEdit。任何 edit event 都不是 authoritative geometry。
- v2 不定义 legacy `EditOp` / decoder writeback / output replay / `engine → shape_pool` writeback 等过渡路径。正确目标是 Stage 5 transaction 直接提交到唯一 authoritative layout state；不符合该边界的 legacy 实现应作为错误状态流删除或重构，而不是进入 v2 architecture。

`AuthoritativeState` 是唯一权威聚合；各 component table 有各自明确 owner，但只能通过同一 transaction gate 一致发布，不能成为彼此竞争或漂移的副本。它至少包括：

- current semantic state：从 source CDL 初始化、已提交的 `Device` / `Net` / pins / params；immutable target circuit / intent 单独保留。
- geometry store：单一 shape table，包含 committed drawn partition 与 C1 pre-publication-derived partition、shape ids、layer / bbox / purpose、origin / edit / derivation policy、annotation summary 与 shape provenance；C1 不是第二份 geometry store。
- occupancy state：A-tier / B-tier occupancy、blockage、via、cut、OD / diffusion sharing。
- annotation state：`CellId`-keyed identity / pin-role attribution、source-evidence backlink、validity 与 conflict metadata。
- connectivity state：component membership、same-layer / via edges、cut barriers 与 diffusion sharing / split topology；不拥有 semantic / annotation summary。`ComponentId` 是 snapshot-scoped stable id，topology mutation 的完整 snapshot-to-snapshot lineage（unchanged / merge / split / removed / created-without-predecessor）必须进入 ChangeSet，调用方不得假定 id 跨 snapshot 自动延续。
- C1 derived layout geometry：geometry store 内 `partition = c1_derived` 的权威部分，例如 NWELL / BOUNDARY / VT / PP / NP / DNW；shape `origin` 单独记录 `source_evidence | transaction | derivator`，不能用 origin 混代 partition。
- read-view version / invalidation metadata；segments、vias、fin attribution、gate tracks、annotation coverage、net-to-component summary 等 materialized views 是 non-authoritative cache，可删除并从 snapshot 重建。
- immutable context / state linkage：`coordinate_system_id`、`tech_bundle_id` / hash、`state_version`、`snapshot_id`、`parent_snapshot_id`、`last_commit_id`、`last_change_set_id` 等中立 ids。Coordinate / tech binding 在 baseline 后不可由 ECO transaction 改写。Full ChangeSet、CommitEvent、CommitAuditRecord 是与 snapshot 同时发布的 append-only siblings；final RunRecord 在 Stage 5 结束后引用 ordered envelopes。它们都不存入 `state/`。

Immutable snapshot 是上述 committed state 的只读冻结视图，供后续 Stage 4 planning、Stage 5 transaction 以及 Stage 6 export / validation 使用。实现上它可以是 deep copy、copy-on-write view、persistent data structure 或 immutable wrapper；architecture 只要求所有消费者看到稳定、版本化、只读、可重跑的状态。

### 2.7 Stage 6：artifact export 与 validation

成功 run 的 Stage 6 只读取 final committed snapshot、该 run 的 ordered ChangeSet / CommitEvent chain、immutable `RunRecord` / diagnostic provenance、site/tool config、export policy、validation policy，以及可选的 fixture golden target。Stage 5 orchestration 完成后冻结唯一 RunRecord：它包含 input summary（含 tech / coordinate ids 与 hashes）、neutral PlanningAuditRecord / ConstraintAuditRecord、Stage 1–5 audit records、ordered commit ids、final snapshot id 与 provenance，不嵌入 planning / constraint implementation objects。Stage 6 必须按该 ordered chain 汇总 validation expectations、ExportEdit 与 report delta，不能只读取最后一个 commit。Stage 6 产出的 ArtifactManifest、ToolRunResult、ValidationResult、ReportingResult 分别引用同一 run id / final commit-snapshot ids，不反向修改 RunRecord。Stage 6 不读取 live planner / mutable transaction object，也不把 Stage 1 raw evidence 或 target diff globals 当作输出事实源。

Stage 6 输入包括：

- immutable committed snapshot。
- Ordered ChangeSet / CommitEvent chain（默认 whole-intent 只有一项）。
- immutable RunRecord / diagnostic provenance。
- site/tool config。
- export policy。
- validation policy。
- optional golden target。

输出包括：

- Required v2 MVP core artifacts：GDS、JSON / machine-readable layout snapshot、CDL；以及 policy-enabled optional integration artifacts，例如 SKILL / Virtuoso script。
- Immutable export `ArtifactManifest`；每个 published required / optional export artifact 均有 path / hash / type / requiredness。Validation result、report、visualization 与 pipeline terminal record 分别由后续 record 持有，不能在 manifest 冻结后回填。
- Stage 6 `ToolRunResult` / `ParseResult`、`ValidationResult`。
- Human / machine-readable report、optional visualization / debug artifacts 与 `ReportingResult`。

成功路径的 Stage 6 子顺序是：exporter 先把全部 required core artifacts 写到 staging 位置，完成 hash / schema checks 后一次性发布 immutable `ArtifactManifest`；随后 validation 对 snapshot / manifest / tool outputs 形成 final `ValidationResult`；最后 `reporting/` 读取 success inputs 生成 report / visualization 与 `ReportingResult`。Export failure 产生 `StageFailure(stage=6, subphase=export)`，partial temp files 只作为 diagnostic refs，不进入 success manifest，也不运行正常 validation；failed `ValidationResult` 或 `ReportingResult` 不回滚 Stage 5 commit / manifest。

无论失败发生在 Stage 1–5、Stage 6 或 success path 结束后，pipeline 都产生 terminal immutable `PipelineResult`，所以它不是仅属于 Stage 6 的输出。它引用 optional RunRecord（仅 `run_record_freeze` failure 时可缺省）、optional commit / snapshot、optional ArtifactManifest、optional ValidationResult / ReportingResult，并直接携带或引用 terminal `StageFailure`；它分别记录 commit / export / validation / reporting status 与最终 deployment-policy outcome，不反向修改任何前置 record。

Failure path 按 publication state 区分两类；除下段 `run_record_freeze` 唯一例外外，两类都必须冻结 RunRecord。**No-publication failure** 表示本 run 尚无 CommitEnvelope（默认 whole-intent failure 属此类）：failure RunRecord 只强制包含 run id、已完成的 neutral stage audit records 与 typed StageFailure，last-stable-snapshot / planning / constraint audit refs 按到达阶段可选；只能生成 diagnostic report，不得生成“修改后”geometry artifact。**Partial-policy terminal failure** 表示 explicit candidate / dependency-group policy 下已有 earlier CommitEnvelopes：已发布 commits 不伪装回滚，failure RunRecord 必须列出 applied / failed / skipped deltas、ordered commit ids 与 final stable snapshot；在 RunRecord 成功冻结后，是否允许导出由 policy 决定，任何输出必须标为 non-production / requires-review。Failure reporting 对 ChangeSet / ArtifactManifest / ValidationResult 使用 optional refs，绝不能把 failed delta 伪装成 committed artifact。

`run_record_freeze` 是上述两类中唯一允许缺少 RunRecord 的 record-construction failure：只发布/保留 typed StageFailure、已完成的 neutral audit refs、optional ordered CommitEnvelope ids，并产生引用它们的 failed `PipelineResult`。该 variant 不进入正常 Stage 6 export 或 `ValidationResult`；diagnostic reporting 直接消费这些 refs，不能虚构 success / failure RunRecord。

Stage 6 的验证模型分为四类：

1. **Golden regression。** fixture 有目标 GDS/JSON 时，可作为回归门禁；生产场景不一定有唯一 golden layout。
2. **Self-consistency。** 已生成、已启用的 GDS/JSON/CDL 及 optional SKILL 必须与 committed snapshot 和 commit log 一致；reporting input 的一致性由 audit-readiness check 覆盖。
3. **Signoff/tool validation。** 按 policy 接入 Calibre DRC / LVS、Virtuoso dry-run、shape locate 等生产检查；v2 MVP 可以明确 deferred。
4. **Audit-readiness validation。** 在生成 report 前确认 frozen provenance、localized references 与 policy disclosure 足以说明改了什么、为什么改、谁产生、哪些检查通过、哪些检查降级或跳过。

Stage 6 不应 mutate Layauto `AuthoritativeState`、transaction state 或 snapshot。重复运行纯 artifact generation 应产生相同 artifact 或可解释的时间戳/路径差异。Stage 6 发现 snapshot 缺少可导出或可验证的 final state 时，应返回 typed export / validation failure；不能临时运行 derivator、decoder 或 parser 逻辑来补齐状态。显式启用的外部 Virtuoso/SKILL apply 是有外部副作用的 production-integration subphase，必须有 assertion、idempotency / undo policy 和结构化结果，但仍不得 backpatch Layauto snapshot。

### 2.8 Legacy MVP 与 v2 阶段边界的关系

Legacy MVP 的 Stage 1.5、Stage 6 writeback、legacy JSON parser、decoder-as-state-updater 等做法都属于迁移时期的实现细节。v2 不再把这些边界作为目标架构：

- Calibre query bundle 归入 Stage 1 evidence。
- Legacy JSON 不进入 v2 主路径。
- Stage 2 从 evidence 构建统一 layout state，而不是从 net JSON 和 bbox JSON 交叉构建多个几何副本。
- Stage 5 提交权威状态。
- Stage 6 只导出和验证。

可复用代码应按职责重新归位，而不是保留 MVP 的 stage 编号和状态流。仓库中 legacy MVP 已整体隔离到 `legacy_mvp/`；从仓库根目录不再维护 legacy import / test 兼容性，如需考古运行旧流程，应进入 `legacy_mvp/` 目录内部执行。

## 3. 事实源、状态所有权与派生视图

第 3 节定义 v2 中哪些对象是事实源，哪些对象拥有可变状态，哪些对象只是可重算查询或导出视图。这里的 “state” 不只表示内存对象所有权，也表示 v2 修改流程中的工作事实层级。

v2 区分四类对象：

1. **Raw / normalized facts。** 来自 GDS、CDL、LVS query 和 tech bundle 的事实，例如 drawn geometry、semantic IR、layer map、coordinate system；site/run config 不是事实源。
2. **Canonical working abstraction。** 由 drawn geometry 投影得到的 occupancy store。它不是原始几何事实源，但它是 candidate planning、CSP checking、transaction commit 和 connectivity update 的主要操作对象。
3. **Interpretation layers。** 作用在 occupancy 上的 annotation overlay 与 connectivity state。前者解决 identity association，后者解决 topological association。
4. **Read / export views。** 从 committed state 派生的查询、缓存、报告和 artifact view。

因此，v2 的目标不是把所有事实压缩成一个 table，而是让每一层的来源、可变性、transaction 责任和重算路径清楚。`AuthoritativeState` 是单一聚合，受控包含 current semantic、single geometry store（drawn / C1-derived partitions）、occupancy、annotation、connectivity 与 view-version / linkage metadata；各 component 有明确 owner，但只能一起发布。legacy MVP 中同一物理对象同时存在于 `shape_pool`、`TrackSegment`、`ViaInstance`、`CellOccupancy`、CSP engine cells、output JSON 等多个可独立变化表示的问题，在 v2 中必须收敛为该聚合内的一致 component 与若干只读视图。

v2 的基本原则是：

- GDS / lossless normalized evidence 是 drawn geometry 的事实源；bbox evidence 受 flat-rectilinear capability 限定。
- Source CDL 初始化 current semantic truth；target CDL / intent 是独立 immutable desired reference，不进入 mutable current state。
- LVS / Calibre query 是 geometry ↔ schematic identity 的 annotation evidence。
- `AuthoritativeState` 是 committed state 的唯一聚合 owner；layout store 权威持有 `drawn` 与 `c1_derived` partitions，occupancy / annotation / connectivity / current semantic 各自持有其明确维度；C1 不另设第二 geometry owner。
- Occupancy store 是后续候选规划、约束检查与事务提交使用的离散几何工作基底。
- Connectivity state 是 occupancy 上的拓扑解释层，是 same-conductor / split / sharing 判断的权威结构。
- Grid / coordinate system、constraint engine、exporter、reporter 只能读取或派生视图，不能成为第二套 layout truth。
- Read / export views 必须可从 authoritative state 重算；它们不能反向成为事实源。

### 3.1 几何事实源

几何事实来自 GDS / lossless normalized geometry；只有通过 flat-rectilinear capability check 的 v2 MVP subset 才能用等价的 `bbox_by_layer` evidence。该 capability 内的每个 drawn shape 应进入 layout store，携带：

- stable `shape_id`。
- layer / purpose / optional `drawn_mask_color`；纯 UI 属性使用独立 `display_color`。
- bbox / polygon geometry。
- source evidence backlink。
- annotation summary。
- provenance / derived 标记。

几何事实源必须覆盖 unannotated shapes。LVS-only sourcing 会丢失 filler、dummy、ESD、marker、手工几何等生产版图中常见对象，因此不能作为唯一几何源。

layout store 中的 geometry record 是 drawn geometry 的权威入口。对于同一个 physical occupant，不应再创建另一套可独立变更的长期工作表示。例如：

- `TrackSegment` 不能成为 LI / M1 geometry 的独立事实源。
- `ViaInstance` 不能成为 VIA0 geometry 或跨层连通的独立事实源。
- CSP engine cell assignment 不能成为 occupancy 的独立事实源。
- output JSON / SKILL edit 不能成为 commit 后几何的事实源。

迁移期可以取用 legacy MVP 中职责已经匹配的代码，但不应通过过渡包装固化错误状态模型。任何保留的数据结构都必须重新归位为只读查询、性能缓存、报告/导出视图或待删除的过渡实现，并且有明确 owner、invalidation 规则和重算路径。

### 3.2 语义事实源

语义事实来自 CDL 与 target intent。`domain/` 定义 immutable value types；`CurrentCircuitState` 从 source CDL 初始化并随 commit 更新，`TargetCircuit` / `TargetIntent` 保持 immutable。Canonical `DeviceId` / `NetId` 使用 cell/schematic scope，包括：

- cell / subckt identity。
- `Device`：instance name、device type、parameters、pins。
- `Net`：net name、net type、pin membership。
- target delta / intent：resize、add/remove、reroute、cut/share/split 等。

`Device` / `Net` 是 semantic IR，不应长期保存可从 layout store + annotation + occupancy 推导出的几何副本。`ixref` / `net_xref` join、LVS index/layout name 以及来自 `device_info` 的 device bbox / gate seed bbox 属于 annotation state / `DeviceAnnotationSeed`，以 canonical semantic id 为 key；它们是 run-scoped evidence backlink 或 stamping seed，不是 semantic field 或 geometry owner。

以下内容在 v2 中不属于 `Device` / `Net` 的权威语义状态：

- `Device.fin_track_indices`。
- `Device.gate_track_idx`。
- `Net.segments`。
- `Net.vias`。
- routing bbox 列表。
- via bbox 列表。
- 可由 `FIN ∩ OD ∩ device attribution` 重算的 active-fin attribution。

如果迁移期继续暴露这些字段，它们只能是从 authoritative layout state 重算的查询结果或短期缓存。任何 planner 或 transaction 都不应只依赖这些缓存来决定物理修改。

### 3.3 LVS annotation overlay

LVS / Calibre query 的角色是 annotation，不是完整几何事实。它负责把 layout-side geometry 和 schematic-side identity 连接起来：

- `ixref`：layout instance ↔ schematic instance，包含 S/D swap 等信息。
- `net_xref`：layout net / LVS index ↔ schematic net。
- `device_info`：per-device derived-layer seed shapes。
- `net_shapes`：per-net routing-layer shape evidence。

annotation 可以不完整，也可能有 sub-nm drift、layer-name difference、effective-region trimming difference。因此 overlay 需要 tolerance、layer mapping、coverage report 和 conflict policy。

v2 的 annotation home 应是 `state.annotation` 中以 occupancy `CellId` 为 key 的 table；occupancy 只持有 reference，而不是 identity fields。它不能退化为仅 shape-level summary，因为一个 GDS rectangle 可能：

- 被 cut 分成多个连通区域。
- 跨越多个 device 的 diffusion sharing 区域。
- 一部分有 LVS annotation，一部分没有。
- 在不同 cells 上携带不同 net / device / pin role。
- 因 effective-region trimming 与 drawn bbox 不完全一致。

因此 overlay 的目标是把 `device_id`、`net_id`、`pin_role`、LVS-derived `annotated_mask_color`、coverage/conflict marker 等 identity references 写入以 occupancy `CellId` 为 key 的 authoritative annotation table。Shape-level `net_id` / `device_id` 与 connectivity component summary 只能作为可重算 consensus：当覆盖 cells 完全一致时可以汇总；一旦不一致，应保持 unknown / ambiguous，并把细节留在 per-cell annotation 与 coverage report 中。未定义的 “store cell” 或 mutable connectivity component 不得成为 annotation owner。

Annotation overlay 只负责 identity association；via / cut / diffusion sharing 带来的 topological association 由 connectivity state 负责。Connectivity component 读取 per-cell annotation 并产生可重算 summary，二者共同形成 localization 与 DRC/LVS 判断所需的完整解释。

### 3.4 Grid 作为坐标系统

Grid 的职责是坐标转换和合法离散空间定义：

- physical bbox ↔ track / cell coordinates。
- layer orientation、pitch、offset。
- B-tier axes definition。
- routing preferred direction。
- bbox / polygon 到 occupancy cell 的 projection 规则。

因为 occupancy projection 依赖这些坐标定义，coordinate system 必须在 Stage 2 的事实归一化期间建立；Stage 3 只读取它来初始化约束上下文。

Grid 不应长期拥有 occupancy。否则 A-tier、B-tier、engine cells、shape_pool 会形成多个状态副本，导致 commit 后漂移。目标形态是：Grid / coordinate system 提供纯坐标服务；occupancy store 使用这些坐标服务建立和维护 cell occupancy；constraint engine、planner、router、read view builder 都读取同一份 occupancy store。

### 3.5 Layout store / occupancy 作为离散几何工作基底

Layout store 保存 drawn geometry，是 GDS / lossless normalized evidence（或 capability-scoped bbox）归一化后的几何事实承载者。Occupancy store 则是 drawn geometry 经 coordinate system 投影后的离散几何抽象。

二者关系是：

- layout store 记录 shape / bbox / polygon / layer / purpose，以及 source-evidence 或 commit / derivator provenance。
- coordinate system 定义 track、cell、pitch、offset、orientation、B-tier axes。
- occupancy store 记录 `(layer, cell)` 上是否被某个 shape / physical occupant 占据，以及该占据的 kind、shape reference、annotation-state reference 和 blockage / barrier / via / OD 等语义标记。

Occupancy 不是原始事实源：base cell projection 可由 layout store + coordinate system + layer policy 重建；包含 annotation reference、blockage / conservative classification 等语义的 enriched occupancy 还需要 annotation state 与 conservative policy，connectivity 则另行重建。Occupancy 也不是普通 cache，因为 v2 的 candidate planning、CSP-frontline rule checking、transaction commit、connectivity update 都以它为主要工作对象。一次 transaction 中被 staged、检查、提交或 rollback 的，首先是 occupancy 及其关联的 semantic / annotation / connectivity / derived changes。

目标状态容器应统一管理：

- drawn geometry records。
- A-tier / B-tier occupancy。
- shape-to-cell projection。
- cell-level device / net / pin annotation references。
- blockage / unknown / suspect geometry。
- cut / via / diffusion sharing state。
- commit-visible current state。

实现可以分层存储，例如 current-semantic table、geometry table、occupancy table、annotation table、connectivity table，但 architecture 要求它们是同一 `AuthoritativeState` 的受控 components，由一个 transaction gate 原子发布。其它对象必须是 read view、cache、transaction overlay 或 export artifact。

一个 physical occupant 在 working state 中只能有一个权威 occupancy 表达。例如 VIA0 的目标表示不应同时是 `ViaInstance`、B-tier occupancy、LI WIRE cells、M1 WIRE cells 和 CSP assignment。正确做法是：VIA0 drawn geometry 进入 layout store；其 occupied cells 进入 occupancy store；其跨层导通作用由 connectivity state 的 via edge 表达；任何 `ViaInstance` 只是查询或导出视图。

同理，OD active region、LI/M1 routing segment、CUT barrier、blockage 都应由同一 store substrate 表达，再由不同 read view 暴露给 planner、constraint、report 和 exporter。

### 3.6 Connectivity state 作为拓扑解释层

Connectivity state 基于 occupancy 构建，用于解释哪些 occupied cells 属于同一个 topological conductor / component。它不是 CDL net label 的副本，也不是普通 derived view；它是 DRC same-conductor reasoning、routing feasibility、via connectivity、cut barrier、diffusion sharing / split 判断的权威拓扑结构。

Connectivity state 应覆盖：

- same-layer adjacency。
- via edges。
- cut barriers。
- diffusion sharing / split。
- blockage 与 unknown geometry 的保守处理。
- component membership / stable component id；component-to-annotation / net summary 是 versioned read view，不属于 ConnectivityState truth。

Annotation overlay 和 connectivity state 都作用在 occupancy 上，但解决的问题不同：

- annotation overlay 解决 identity association：某个 occupancy cell 与哪个 schematic/layout device、net、pin role 相关。
- connectivity state 解决 topological association：多个 occupancy cells 是否物理连通，是否被 via 连接，是否被 cut 切断，是否因 diffusion sharing 形成共同 active region。

二者共同形成更完整的 id association：

```text
occupancy cell
  + annotation identity references
  + connectivity component
  + derived component-to-net/device summary
  → localization / DRC / LVS / report 使用的完整解释
```

Net label 是 semantic / annotation 属性，可用于报告、localization、LVS feedback 和 target intent 对齐；是否属于同一导体则应由 connectivity component 判断。

目标合同是：

- DRC spacing / same-conductor exemption 查询 connectivity component，而不是比较 scalar `net_id`。
- `CellState` / CSP domain 不携带长期 `net_id` / `device_id` ownership。
- `net_id=None` 不表示“与所有 named nets 兼容”；unknown / unannotated geometry 默认按 blockage、suspect conductor 或 conservative conflict 处理。
- VIA 是跨层 connectivity edge，不需要用 LI/M1 上额外的 via-as-wire double stamp 伪造连通。
- CUT 是 connectivity barrier，会改变 component relation，也会影响 rule checking 和 routing feasibility。
- diffusion sharing / split 是 topology 与 physical attribution 的共同问题，不能写入 current semantic `Device.shared_with[]` 作为孤立 truth；如需展示，只能从 occupancy / connectivity / annotation 派生 view。

Connectivity state 必须纳入 transaction checkpoint / restore / commit。任何 occupancy change、via add/remove、cut add/remove、OD split/share 都必须在 overlay 中增量更新；如果先标 invalid，则必须在 publication 前重建受影响 components。只有 non-authoritative index / cache 可以跨 commit 保持 invalid。`ComponentId` 在一个 snapshot 内稳定；跨 topology mutation 时，ChangeSet 必须记录 old→new component lineage（unchanged / merge / split / removed / created-without-predecessor），调用方只能经 lineage 追踪，不能把旧 id 静默沿用到新 snapshot。

### 3.7 Read views、localization queries 与 artifact views

v2 仍然需要从 committed state 派生的读取面，但它们的必要性来自查询便利、性能、导出、报告和 debug，而不是状态所有权。Planner 可以调用带 `snapshot_id`、freshness check 和确定性重算合同的 view query API；它不得依赖 stale materialized cache，也不得把 view 当作独立可变 truth。Transaction 或 exporter 同样不能让 view 反向成为事实源。

更准确地说，v2 有三类读取面。

**第一类：occupancy queries。**

这些是对 occupancy store 的不同读取方式，例如：

- 某 layer 上的连续 occupied cells。
- 某 net / component 对应的 routing span。
- 某 via layer 上的 occupied via cells。
- 某 device 附近的 OD / LI / M1 cells。
- 某 component 的 bounding envelope。

Legacy MVP 中的 `Net.segments`、`Net.vias`、routing read views 等概念应在 v2 中降级为 occupancy query 或导出/报告读取面，而不是独立 state。

**第二类：identity localization queries。**

这些查询用于把 semantic IR 与 geometry / occupancy 定位起来，例如：

- 某 `Device` 对应哪些 OD cells。
- 某 `Device` 覆盖哪些 active FIN tracks。
- 某 `Device` 的 gate anchor / gate track 在哪里。
- 某 pin role 对应哪些 LI / M1 access cells。
- 某 schematic net 对应哪些 connectivity components。

Legacy MVP 中的 `Device.fin_track_indices`、`Device.gate_track_idx` 不应作为 v2 `Device` 的 canonical fields。它们应由 semantic identity、annotation anchor、FIN/POLY/OD occupancy、connectivity component 和 tech coordinate system 动态求得；如需缓存，也必须可重算并有 invalidation 规则。

对于 `nfin` resize，active fin count 不应来自 stored `fin_track_indices`，而应来自：

```text
static FIN occupancy
  ∩ OD active occupancy
  ∩ device attribution / gate footprint
  → active fin attribution
```

**第三类：artifact / report views。**

这些视图服务 Stage 6 输出与人工审计，例如：

- GDS / JSON serialization view。
- CDL export view。
- SKILL edit sequence。
- human report section。
- diff visualization。
- validation result summary。
- L1 `EditOp` 风格的变更展示。

artifact views 从 final immutable snapshot、ordered ChangeSet / CommitEvent chain、export policy 和 validation policy 派生。它们不能反向修改 layout store、occupancy、connectivity 或 current semantic state，也不能通过 replay edit stream 才把 geometry 变成真实状态。

**Pre-publication derived layout geometry 单独处理。**

NWELL、BOUNDARY、VT、PP、NP、DNW 等 C1 derived markings 不是普通 read view。它们是在 Stage 5 transaction 内，由 tentative A/B-tier state、device metadata 和 tech rules 派生出来的 layout geometry；finalization 位于 base materialization 之后、CommitEvent / snapshot 原子发布之前。Stage 6 只序列化已经 final 的结果，不再临时修改它们。

这里的 C1 derived layout geometry 指 transaction-private refresh 完成后随同一 atomic publication 进入 snapshot 的 derived markings；FIN static backdrop 虽然也禁止普通 macro 直接编辑，但不是 C1 derivator 输出。实现层如果短期复用 `derived` 标记作为 direct-edit rejection seam，必须把它理解为 edit guard 的过渡承载方式，而不是把 FIN 归入 C1。

### 3.8 Snapshot、commit log 与 provenance

每次成功 commit 应产生：

- committed layout snapshot。
- semantic delta。
- geometry / occupancy delta。
- annotation delta。
- connectivity delta。
- derived refresh delta。
- constraint result。
- commit provenance：target intent → planner → candidate → constraint result → transaction-private base materialization → annotation / derived finalization → atomic commit publication。

Stage 6 生成 artifact / validation record 后，以 `commit_id` / `snapshot_id` 继续扩展 provenance 链；尚未发生的 exported artifact 不能预先写入 Stage 5 CommitEvent。

成功 commit 后，authoritative layout state 必须立即反映修改，并且后续 candidate 必须读取这个已提交状态。不能等 Stage 6 decoder 或 output JSON replay 才让修改“变成真实”。

失败 candidate 必须 restore 到 checkpoint，且不得留下 partial edit。无论失败发生在 occupancy feasibility、annotation / connectivity update、derived refresh 还是 semantic update 期间，都不能让 layout store、occupancy、annotation、connectivity、semantic IR、derived state 之间出现漂移。

ChangeSet / CommitEvent 是 provenance、debug、report、SKILL、diff visualization 和 validation 的输入，但不是唯一几何事实。几何事实已经在 committed layout snapshot 中存在；Stage 6 只能读取 snapshot、commit log、frozen RunRecord 与显式 policy / config 来导出或验证 artifact。

Immutable snapshot 是 committed state 的只读冻结视图，至少覆盖：

- current semantic state；associated `RunRecord` / snapshot context 可以引用 immutable target circuit / intent，但 target 不是 `AuthoritativeState` 的可变 component。
- geometry store 的 drawn 与 C1 pre-publication-derived partitions。
- occupancy。
- authoritative annotation state / references / validity metadata。
- connectivity components。
- blockage / unknown / suspect markers。
- `coordinate_system_id`、`tech_bundle_id` / hash 与 neutral state-linkage metadata；full tech objects、ChangeSet / CommitEvent / RunRecord 不嵌入 snapshot。

实现上可以是 deep copy、copy-on-write view、persistent data structure 或 immutable wrapper；architecture 只要求 Stage 4–6 消费者视角下它稳定、版本化、只读、可重跑。

## 4. Layer tier 与物理实体抽象

第 4 节定义 layer tier、物理实体、编辑策略与 connectivity 语义之间的关系。v2 中，**tier 是粗粒度 representation / lifecycle class**：A/B 描述参与 occupancy 的 1D/2D 离散化，C1/C2 描述不进入同一主 occupancy 的 derived / auxiliary geometry 生命周期。Tier 不能单独决定是否可编辑；一个 layer 的完整架构属性至少包括：

- **tier**：A/B 的 coordinate / occupancy projection，或 C1/C2 的非主-occupancy geometry lifecycle class。
- **role**：物理或工艺角色，例如 fin、gate、interconnect、via、cut、diffusion、well、boundary、text、marker。
- **edit policy**：layer map 提供默认值，例如 static backdrop、entity-constrained edit、routing-editable、derived-refresh-only、auxiliary-policy-controlled；shape / region / physical-entity record 可以施加更严格的 `fixed_frame` / `no_direct_edit` override，限制优先。
- **connectivity / annotation policy**：是否形成 conductor、via edge、cut barrier、diffusion sharing / split、blockage，以及哪些 occupancy cells 可引用 annotation state。
- **derivation policy**：是否由 transaction-private tentative A/B-tier state 和 tech rules 在 publication 前刷新，或是否只是静态 PCell / foundry backdrop，不随 resize 直接改变。

因此，v2 不应把 “Tier A” 理解为“都用 TrackSegment 独立存储并可由 macro 直接改”，也不应把 “derived” 只理解为 C1 derivator 输出。FIN 是 A-tier coordinate layer，但在 resize 语义下是 static backdrop；NWELL / BOUNDARY / VT / PP / NP / DNW 是 C1 derived markings；二者都不可被普通 macro 直接 patch，但原因和刷新方式不同。

### 4.1 Tier A：1D coordinate / backdrop / routing layers

Tier A 表示主要可投影到一维 track coordinate 的层，例如 FIN、POLY、LI、M1。Tier A 的共同点是 coordinate abstraction，而不是相同的可编辑性或相同的工作表示。

v2 中 Tier A 至少分三类：

- **Static backdrop layer：FIN。**
  - FIN 由 foundry / PCell / cell architecture 给出固定 pitch 的连续 backdrop。
  - `nfin` resize 不删除、不新增 FIN geometry。
  - Active fin attribution 由 `FIN occupancy ∩ OD active occupancy ∩ device attribution / gate footprint` 推导。
  - 为了防止 legacy macro 再发出 FIN edit，FIN 应具备明确的 `no_direct_edit` / `static_backdrop` 标记；迁移期可以复用 `derived` rejection seam，但架构上应区分“静态 backdrop”与“C1 derived marking”。
- **Entity-constrained gate layer：POLY / gate。**
  - POLY 是 device topology、gate recognition、pin access、cut / contact 语义的一部分。
  - 不能把 POLY 当作普通 rectangle 通过局部 bbox arithmetic 任意修改。
  - Gate 相关变更必须通过 physical entity model、device recognition、cut / contact policy、connectivity 和 DRC constraints 处理。
  - 对 v2 初始 `nfin` resize，POLY 通常保持不变；若端点或 pin access 受影响，也必须作为候选计划的一部分经过 Stage 5 检查和提交。
- **Routing / local interconnect layer：LI / M1。**
  - LI / M1 可以作为候选 routing 修改的一部分。
  - `routing_editable` 是 layer default；VSS/VDD rails、fixed frame 或其它 shape/region override 仍为 `no_direct_edit`，不能因与 signal stub 同属 M1 而被候选修改。
  - 修改入口是 planner / router 生成 candidate path 或 candidate shape change，再由 Stage 5 transaction 检查并提交。
  - LI / M1 drawn geometry 仍归 layout store；其离散占用归 occupancy store；连续 segment、span、net view 只是 read view / export view，不是独立状态 owner。

Tier A projection 的目标是服务 occupancy、connectivity 与 constraints。Legacy MVP 中 `TrackSegment`、CSP cell assignment、output JSON 等不能继续作为 LI / M1 的独立几何事实源；它们在 v2 中只能是 occupancy query、transaction overlay、constraint cache 或 artifact view。

### 4.2 Tier B：2D occupancy layers

Tier B 表示需要二维 cell occupancy 的层，例如 OD、VIA0、CPO、M0_CUT、FIN_CUT。Tier B 是 v2 物理实体抽象的关键层，因为它直接承载 active region、via edge、cut barrier 和 diffusion sharing / split 等语义。

- **OD / diffusion。**
  - OD 表示 active diffusion coverage，是 `nfin` resize 的核心作用对象。
  - 对 `nfin` resize，目标是调整 device active OD coverage，使被 OD 覆盖并归属该 device 的 active fin 数量变化，而不是删除 FIN。
  - OD occupancy 必须携带或可定位 device attribution、pin role、sharing / split、blockage / suspect 标记。
  - 多 device 共享 diffusion 时，sharing 不应只保存在 `Device.shared_with[]` 之类 metadata 中，而应体现在 occupancy、connectivity component 与 semantic attribution 的一致关系中。
- **VIA layer：VIA0。**
  - VIA0 drawn shape 进入 layout store。
  - VIA0 occupied cell 进入 occupancy store。
  - VIA0 的电学作用由 connectivity state 中的跨层 via edge 表达。
  - 不应同时用 `ViaInstance`、B-tier cell、LI wire cell、M1 wire cell、CSP assignment 等多个可漂移工作表示来表达同一个 physical via。
  - 如保留 `ViaInstance` 类型，只能作为只读查询 / API 兼容 shim / export view，不能拥有独立状态。
- **CUT layers：CPO、M0_CUT、FIN_CUT。**
  - CUT 是 connectivity barrier，而不是普通 blockage。
  - CUT 会改变 component relation，并影响 rule checking、routing feasibility、device recognition 与 diffusion split / sharing 判断。
  - CUT occupancy 必须纳入 transaction checkpoint / restore / commit，并在 overlay 中触发 connectivity 增量更新或 publication 前 affected-component rebuild。

Tier B 的 projection 应写入唯一 occupancy store。Grid 只提供 B-tier axes 和 bbox-to-cell projection，不拥有 `b_tier_cells` 这类 layout content。Constraint engine 可以缓存检查结果，但不能成为 Tier B occupancy 的第二份权威副本。

### 4.3 Tier C1：pre-publication derived layout geometry

Tier C1 包括 NWELL、BOUNDARY、VT、PP、NP、DNW 等由 tentative base state 和 tech rules finalise、随同一 CommitEvent 发布的 layout geometry。它们不是 planner / macro 的直接编辑目标。

C1 的合同是：

- 输入来自 transaction-private tentative A/B-tier state、semantic device metadata、tech rules 和 derivation policy。
- Finalization 在 Stage 5 base materialization 之后、atomic commit publication 之前完成；失败则整体回滚。
- 刷新结果进入 committed snapshot，成为 Stage 6 可序列化的 layout geometry。
- Stage 6 只读取并导出 C1 state，不临时修补 C1。
- 普通 candidate / macro 不得直接 patch C1 shape；如果确实需要影响 C1，应先修改其上游 A/B-tier 或 semantic state，再通过 derived refresh 得到结果。
- 对 fixed-frame `nfin` resize，BOUNDARY、frame-level NWELL 及其它声明为 frame invariant 的 geometry 必须与 parent snapshot 相同；任何 delta 都是 failure，除非存在显式 frame-edit intent / capability。其它真正依赖 delta 的 marking family 才进入 dirty scope。

需要注意，C1 的 “derived” 与 FIN 的 “static backdrop / no-direct-edit” 不是同一概念。二者都可以触发 direct-edit rejection，但一个是 pre-publication refresh geometry，另一个是 cell architecture / PCell backdrop。

### 4.4 Tier C2：auxiliary / marker / policy-controlled geometry

Tier C2 包括 TEXT、marker、DIODE / ESD marker layer 或其它不进入主 CSP / routing occupancy 的辅助几何。真实参与导电、device recognition 或 DRC 的 DIODE / ESD active / routing shapes 仍按对应 A/B layer role 建模，不能因器件类别被整体降为 C2。C2 不应简单理解为 LVS annotation overlay；它们仍可能是 GDS 中真实存在的 drawn geometry或生产工具需要保留的 marker / waiver carrier。

C2 的合同是：

- C2 shape 必须进入 layout store，保留 source evidence、layer / purpose、bbox / polygon、provenance 与 annotation summary。
- 默认情况下，C2 不参与主 routing / diffusion / via occupancy，也不作为 planner 修改的直接目标。
- 如果某类 C2 对象允许编辑，必须有显式 edit policy、validation policy 和 provenance，并通过 Stage 5 transaction / commit log，而不能由 exporter 或脚本绕过权威状态。
- 如果某类 C2 对象影响 DRC/LVS、ESD、diode recognition 或 tool waiver，其语义应通过 policy / validation hook 暴露，而不是混入 LVS annotation overlay 的 identity stamping 逻辑。

因此，C2 更准确的定位是 “auxiliary / marker / policy-controlled geometry”，而不是普通 “editable annotation”。

### 4.5 Static FIN / gate backdrop

FinFET 标准单元中的 FIN 应建模为固定 pitch、跨 cell frame 的连续 backdrop。`nfin` 的变化表示 active device coverage 变化，而不是 physical FIN track 的消失。

正确的 active fin attribution 是：

```text
static FIN occupancy
  ∩ OD active occupancy
  ∩ device attribution / gate footprint
  → active fin attribution
```

这意味着：

- `Device.fin_track_indices` 不应作为长期存储字段驱动 resize。
- FIN stripe 不应按每个 device 局部生成或删除。
- 同一 fin track 可以跨多个 device x-range 存在，具体归属由 device bbox / gate footprint / OD overlap 判断。
- 多 device 沿 X 方向复用同一批 FIN track 时，active fin attribution 必须同时考虑 X 与 Y，不能只按 fin Y 坐标归属。

Gate / POLY backdrop 也不应被简化为普通 rectangle patch。POLY 与 gate pitch、device recognition、CPO / cut、pin access、source/drain attribution 和 routing topology 相关。v2 初始 `nfin` resize 可以把大部分 gate geometry 视为稳定背景，但如果某个 intent 需要移动、截断或重建 gate，必须由专门 planner 生成 physical-entity-aware candidate，并由 Stage 5 统一检查和提交。

### 4.6 OD active region、diffusion sharing 与 device attribution

OD 是 `nfin` resize 的主要编辑对象。对一个 device 从 `nfin = old` 改到 `nfin = new`，planner 应提出 OD active coverage 的候选变化，并声明受影响的：

- OD occupancy cells。
- device attribution。
- S/D pin role attribution。
- diffusion sharing / split relation。
- nearby LI / VIA / M1 access region。
- 需要刷新的 derived markings 与 read views。

OD change 不能只更新 drawn bbox，也不能只更新 semantic `Device.nfin`。成功 commit 后，current semantic state、layout store、occupancy、annotation attribution / validity、connectivity state、derived geometry 与 provenance 必须一致。

Diffusion sharing / split 应作为 occupancy + connectivity + semantic attribution 的共同关系：

- occupancy 表示哪些 OD cells 被 active diffusion 占据。
- connectivity state 表示哪些 OD cells 属于同一 diffusion component，是否被 cut / split 断开。
- annotation / semantic attribution 表示 component 或 cell 与哪些 device、pin role、net identity 相关。
- report / validation 可以从上述结构派生 `shared_with` 之类展示字段，但它们不是权威事实源。

### 4.7 VIA / CUT / routing connectivity

VIA、CUT 与 routing layers 的核心语义应由 connectivity state 统一解释。

- VIA 是跨层 connectivity edge。
  - VIA0 connects policy 来自 layer map / tech bundle，例如 `connects: [LI, M1]`。
  - Connectivity state 根据 VIA0 occupancy 和上下层 conductor occupancy 建立 via edge。
  - Rule checking 使用 via geometry、enclosure、spacing 和 component relation，而不是依赖 via-as-wire double stamp。
- CUT 是 connectivity barrier。
  - CPO / M0_CUT / FIN_CUT 会切断或限制相应 layer / entity 的连通。
  - CUT 变化必须触发 connectivity component 更新，并进入 transaction checkpoint / restore / commit。
- Routing layers 的修改必须从 candidate path / candidate shape change 开始。
  - Router / planner 只产生 plan。
  - Constraint engine 判断 occupancy、spacing、enclosure、blockage、same-conductor exception、via legality 等。
  - Transaction commit 成功后才更新 layout store、occupancy 与 connectivity。
  - Exporter 不能通过修改 output JSON 的 shape bbox 来补齐 routing state。

对于 unknown / unannotated geometry，不能把 `net_id=None` 当作“与所有 net 兼容”。未解释几何应按 blockage、suspect conductor 或 conservative conflict 进入 routing / DRC 判断，直到 annotation overlay 或人工 policy 明确其语义。

### 4.8 Layer map 与 tech bundle

Layer map 和 tech bundle 是 v2 的工艺参数化边界，但不承载 cell-specific intent 或 target delta。

Layer map 应描述：

- layer name、GDS layer/datatype、purpose、allowed drawn-patterning policy / optional `drawn_mask_color` interpretation 与独立的 `display_color`。
- tier：A / B / C1 / C2。
- role：fin、poly、interconnect、via、cut、diffusion、well、boundary、text、marker 等。
- orientation / preferred direction。
- connectivity policy，例如 via `connects`、cut barrier target、conductor role。
- default edit policy，例如 `static_backdrop`、`routing_editable`、`entity_constrained`、`derived_refresh_only`、`auxiliary_policy_controlled`；shape / entity 的 stricter override 优先。
- derivation / refresh policy，例如 C1 derived markings 的 derivator rule，或 FIN static backdrop 的 no-direct-edit guard。
- canonical GDS alias / purpose mapping，以及对 `calibre_layer_map.yaml` stable names 的 `derived_layer_refs`；不重复 derived `carries`、tolerance、trim 或 alias / dialect metadata。

Tech bundle 应描述：

- pitch、width、spacing、enclosure、extension、minimum area 等 rule records。
- coordinate system 参数，例如 track pitch / offset、B-tier axes。
- rule predicate 的参数化输入。
- signoff 所需 rule-deck / layer-map 的逻辑 identity、version 与 compatibility metadata；具体 filesystem path / binary path 属于 site/tool config。

Layer map / rule deck 不应包含：

- cell-specific intent。
- device instance name。
- target `nfin`。
- 某次 ECO 的 candidate choice。
- fixture-only convenience field。

如果实现层继续使用 `derived: true` 作为 direct-edit rejection seam，应在 schema 注释中说明它是 “non-direct-edit guard” 的过渡承载方式；长期应拆成更明确的 `edit_policy` / `derivation_policy`，避免把 FIN static backdrop 与 C1 derived refresh 混为一类。

需要注意，Layer map / tech bundle 只定义 layer 的工艺语义、映射规则和 policy；它不保存某次 Calibre query 的 annotation 结果。`layer_map.yaml` 拥有 canonical GDS layer 的 drawn-patterning policy，并解释 GDS geometry 上的 `drawn_mask_color`；`calibre_layer_map.yaml` 独占 derived evidence 的 `annotated_mask_color` / carries / tolerance / trim mapping。Stage 2 必须按 tech reconciliation policy 比较两者：一致时形成 rule-facing color view，冲突时标记 suspect / conflict 并按 policy typed-fail 或 requires-review。`device_id`、`net_id`、`pin_role`、coverage / conflict marker 等属于 per-run annotation result。`display_color` 仅服务 UI，不得与任一工艺颜色共用无类型 `color` 字段。

## 5. LVS / Calibre annotation boundary

第 5 节定义 v2 如何把 Calibre / LVS query 结果作为 annotation evidence 接入 Stage 1–2。核心原则是：**GDS / lossless normalized geometry 提供 drawn geometry；`bbox_by_layer` 只覆盖已声明的 flat-rectilinear subset；CDL 提供 schematic semantic intent；Calibre / LVS query 提供 geometry ↔ schematic identity 的证据。** LVS shape 不是 GDS geometry 的替代物，legacy JSON 也不是 v2 的事实主路径。

Annotation boundary 需要同时解决四个问题：

1. 哪些输入是原始证据，哪些是必须丢弃的 legacy convenience path。
2. 如何把 LVS 侧 instance / net identity 归一到 schematic identity。
3. 如何通过 GDS↔LVS layer mapping 把 derived-layer evidence stamp 到 occupancy。
4. 如何报告 coverage gap、conflict、ambiguity，并把 unknown geometry 保守地交给后续约束系统。

### 5.1 v2 输入事实组成

v2 fixture 与生产输入应由以下事实组成：

- **Source CDL + target-intent source。** Source CDL 提供 current circuit；target CDL 或声明的 raw ECO / user / prior-feedback intent 至少提供一种，并在 Stage 2 归一化为独立 immutable TargetCircuit / TargetIntent。
- **GDS / lossless normalized geometry，或 capability-scoped bbox-by-layer。** 提供所声明 geometry capability 内的完整 drawn geometry，包括未被 LVS annotation 覆盖的 shape；超出 flat-rectilinear subset 时不得以 bbox 包络替代。
- **Calibre query bundle。** 至少包括 `ixref`、`net_xref`、`device_info`、`net_shapes` 四类 evidence。
- **Tech bundle。** 提供 layer map、Calibre layer registry、rule records、coordinate / derivation policy 等技术事实。
- **Site/run config。** 选择 tool path、query mode、输入输出路径与 validation / tolerance policy；它不是 design 或 tech fact。

Stage 1 负责读取或生成上述 evidence，并保存 raw output 与 schema-canonical middle files。Stage 2 才负责 semantic / identity / spatial normalization，并构建 current semantic state、immutable TargetCircuit / TargetIntent、layout store、occupancy、annotation state 与 connectivity state。

Fixture 应尽量模拟真实 Calibre query bundle。允许使用 dummy / synthetic middle files，但它们必须使用与生产路径一致的 schema 与 identity 语义；不应再发明只服务当前 parser 的 convenience JSON 作为 v2 主输入。Dummy / synthetic query fixture 模拟的是 Stage 1 Calibre query evidence，不是 legacy MVP parser input；它必须保存 raw captures 与 normalized YAML，并由同一 parser 生成或校验。

### 5.2 GDS geometry：bbox_by_layer

`bbox_by_layer` 是 v2 MVP **已声明 flat rectilinear subset** 的 GDS drawn geometry 结构化表示。它必须保留该 subset 内所有 drawn geometry，包括没有 LVS annotation 的 shape，例如 filler、dummy、marker、ESD、waiver carrier、unannotated routing fragment 或 cell-level wrapper。对 polygon、path、hierarchy/reference、array 或 transform，系统必须使用 lossless `geometry_by_layer` / direct-GDS representation，或在 Stage 1 typed-fail；不能用 bbox 包络冒充 round-trip geometry。

生产路径中，`bbox_by_layer` 只在输入已通过 flat-rectilinear capability check 时可由 GDS reader 生成并支持 round-trip。测试路径中也应使用同一 capability/schema，使 parser、layout store construction、annotation overlay 和 exporter regression 共享同一入口。

`bbox_by_layer` 的合同是：

- 记录 layer / purpose / optional `drawn_mask_color`、bbox；支持 polygon 时必须进入可保真的 normalized geometry schema，而不是塞入 bbox-only contract。
- 记录或引用 unit / DBU / rounding / snap policy；off-grid、半 DBU 漂移或由生成器取整造成的非对称 bbox 必须进入 evidence issue 或 validation issue，不能被 byte-golden 静默吸收。
- 不附带 schematic identity 的臆测。
- 不因为 LVS query 没有覆盖某个 shape 就丢弃该 shape。
- 不从 `device_info` / `net_shapes` 反向补造 drawn geometry。

GDS geometry 进入 layout store 后，后续 overlay 只能把 `device_id`、`net_id`、`pin_role`、`annotated_mask_color`、coverage marker、conflict marker 等写入 `CellId`-keyed annotation state；shape 仅保留 consensus summary。`drawn_mask_color` 仍属于 geometry evidence，两者按第 4.8 节 reconciliation policy 对齐；不能把 LVS shape 当作新的 geometry truth。

### 5.3 LVS identity：ixref / net_xref

`ixref` 负责 layout instance identity 与 canonical schematic `DeviceId` 的 join。Calibre query 中的 layout instance name 可能是 `M0` / `M1` 这类 LVS 侧命名，而 semantic IR 与 target intent 通常使用 schematic instance name，例如 `MN0` / `MP0`。因此，任何来自 `device_info` 的 layout instance name 都必须先通过 `ixref` 翻译到 canonical `DeviceId`，再进入 annotation state 或 report；join table 不写回 `DeviceIR`。

`net_xref` 负责 layout net / LVS index 与 canonical schematic `NetId` 的 join。内部 net可能被 Calibre renumber 或重命名，因此 LVS index / normalized layout-net identity 只作为 **run-scoped stable evidence key** 和 debug backlink；跨 run / commit 的 canonical key 仍是 cell-scoped schematic `NetId`。

Identity join 的目标合同是：

- `Device.inst_name` 等 semantic IR 字段使用 schematic identity。
- `state.annotation` entry 可以同时保留 layout/LVS identity 与 schematic identity，但必须标明来源；occupancy record 只引用该 entry。
- report 面向工程师时应显示 schematic name，同时保留 LVS index / layout name 作为 debug backlink。
- artifact 文件名、fixture 目录名、tool entry name 或 legacy label 不能覆盖 CDL / LVS evidence 中的 cell、subckt、device、net identity；命名不一致应进入 validation / report，而不是反向改写 semantic IR。
- 如果 `ixref` / `net_xref` 缺失、冲突或无法解释，Stage 2 应产生结构化 annotation error / coverage warning，而不是静默 fallback 到字符串相等或 legacy fixture naming assumption。
- S/D swap、pin role swap、body tie 等 LVS identity 细节应保留为 annotation/provenance，不应在 Stage 2 被丢弃。

### 5.4 LVS geometry annotation：device_info / net_shapes

`device_info` 和 `net_shapes` 提供的是 annotation geometry evidence，而不是 drawn geometry source。

`device_info` 的主要用途是：

- 提供 per-device derived-layer seed shape。
- 提供 gate / device bbox anchor，作为 device attribution 与 gate footprint localization 的输入。
- 帮助把 DRC/LVS error localize 到 device、pin role 或 candidate provenance。
- 作为打破 annotation stamping 循环依赖的 `DeviceAnnotationSeed`；anchor keyed by canonical `DeviceId` 并保存在 annotation state，不进入 `DeviceIR`，也不是 layout geometry owner。

`net_shapes` 的主要用途是：

- 提供 per-net routing / conducting derived-layer shape evidence。
- 把 LI / M1 / VIA / local interconnect occupancy cells 与 layout/LVS net identity 关联。
- 支持 DRC/LVS feedback localization、coverage report 和 report traceability。

这些 shapes 需要经过 layer mapping、Stage 2 canonical coordinate snap、annotation-match tolerance、containment / overlap policy 和 optional effective-region trimming 才能 stamp 到 occupancy。它们不替代 GDS geometry，也不能直接生成 `Net.segments`、`Net.vias`、`Device.fin_track_indices` 等工作状态。

对于 `nfin` resize，`device_info` 可以帮助定位 device gate / bbox anchor；但 active fin attribution 仍应由：

```text
static FIN occupancy
  ∩ OD active occupancy
  ∩ device attribution / gate footprint
  → active fin attribution
```

推导，而不是由 `device_info` 或 legacy JSON 中的 per-device fin list 直接决定。

### 5.5 GDS↔LVS layer mapping

生产 Calibre query 的 layer name 往往不是 GDS layer name。例如 gate recognition layer、S/D derived layer、SADP color layer、effective conducting region layer、cut-shadow-trimmed region 都可能有独立名称。

因此 v2 需要显式的 GDS↔LVS layer mapping，且每个维度只能有一个 authority：`calibre_layer_map.yaml` 是 derived-layer registry，权威声明 `name`、`associates_with`、`carries`、`annotated_mask_color` / patterning、tolerance 与 trim policy；`layer_map.yaml` 的 canonical GDS layer 按 stable name 声明 `derived_layer_refs`，并独占 GDS layer/datatype、drawn-patterning policy、via `connects`、cut target、tier 与 edit policy。Loader 必须验证每个 reference 唯一解析，重复或冲突声明 fatal。

- 某个 GDS layer 可接受哪些 LVS / Calibre derived layers 作为 annotation source。
- 每个 derived layer carries 哪些 annotation，例如 `device_id`、`net_id`、`pin_role`、`annotated_mask_color`、well / implant flavour 等。
- via layer 的 `connects` 关系，例如 `VIA0` connects `[LI, M1]`。
- cut layer 的 target / barrier policy。
- SADP / multi-patterning `annotated_mask_color` metadata；纯显示颜色不参与该 mapping。
- unit / DBU / layer-purpose translation。
- containment、overlap、sub-nm drift tolerance。
- cut shadow、extension、effective-region trimming policy。
- conflict policy：哪些 overlap 表示 diffusion sharing，哪些表示 short、ambiguous annotation 或 unsupported production case。

推荐 schema 方向是：在 GDS layer 侧只声明可接受的 `derived_layer_refs`；所有 `carries` / mapping / patterning / tolerance / trim metadata 在 Calibre layer registry 定义一次。

示意：

```yaml
- name: POLY
  derived_layer_refs: [ngate_lvt, pgate_lvt, POLY]

- name: OD
  derived_layer_refs: [nsd, psd]

- name: M1
  derived_layer_refs: [M1a, M1b]
```

Layer mapping 只是解释 annotation evidence 的配置；它不拥有 annotation 结果，也不承载 cell-specific intent、device instance name、target `nfin` 或某次 ECO 的 candidate choice。

### 5.6 Per-cell annotation overlay

目标 annotation home 是 **`state.annotation` 中以 occupancy `CellId` 为 key 的 table**；occupancy 只引用它，不拥有 identity fields。它不是仅 shape-level summary，因为一个 GDS rectangle 可能：

- 被 cut 分成多个连通区域。
- 跨越多个 device 的 diffusion sharing 区域。
- 一部分有 LVS annotation，一部分没有。
- 在不同 cells 上携带不同 net / device / pin role。
- 因 effective-region trimming 与 drawn bbox 不完全一致。

因此，v2 annotation overlay 的 authoritative result 应写到 `CellId`-keyed annotation table，并由 occupancy record 引用。`ShapeRecord.net_id`、`ShapeRecord.device_id`、`ShapeRecord.pin_role` 或 connectivity-local summary 如果保留，只能是 per-cell annotation 的可重算 consensus：

- 如果 shape 覆盖的 cells 对某个 annotation field 完全一致，可以汇总到 shape summary。
- 如果 cells 不一致，应保持 unknown / ambiguous，并把细节留在 per-cell annotation 与 coverage report 中。
- Planner、constraint、transaction 不应只依赖 shape-level summary 判断物理修改是否合法。

Overlay 流程应至少包括：

1. 读取 GDS geometry，构建 layout store 与 occupancy projection。
2. 读取 `ixref` / `net_xref`，建立 layout/LVS identity 到 schematic identity 的 join table。
3. 使用 GDS↔LVS layer mapping 找到每个 GDS layer 对应的 derived-layer evidence。
4. 对 A-tier occupancy 使用 cell-center / interval-overlap / tolerance 规则 stamp annotation。
5. 对 B-tier occupancy 使用 cell-area overlap / containment / tolerance 规则 stamp annotation。
6. 对 device identity 先执行 LVS layout instance → schematic instance 翻译，再 stamp `device_id`。
7. 对 net identity 保留 LVS index / layout name，并映射到 schematic net name。
8. 处理 conflict / sharing / ambiguity，并生成结构化 coverage report 与 conflict report。
9. 从 per-cell annotation 生成 shape-level consensus summary，无法 consensus 时保持 unknown / ambiguous。

Stage 2 的 refs 描述 **source evidence**。ECO 改变 geometry / occupancy 后，Stage 5 必须在同一 transaction 中提交 candidate-derived attribution，或 invalidate 受影响 refs 并标记 `unverified_after_edit`；旧 `device_info` / `net_shapes` 不得静默投影到新 cells。Annotation delta / validity / provenance 进入 checkpoint、ChangeSet 与 snapshot；新的 Calibre output 只有作为下一轮 Stage 1 evidence 重新摄入后，才能替换 source-evidence annotation。

Annotation overlay 只解决 identity association；via / cut / diffusion sharing 带来的 topology association 由 connectivity state 解决。二者共同作用于 occupancy，但职责不同：

```text
occupancy cell
  + annotation identity references
  + connectivity component
  + component-to-net/device summary
  → localization / DRC / LVS / report 使用的完整解释
```

### 5.7 Conflict、sharing 与 ambiguity policy

Annotation conflict 不能简单按“后写覆盖前写”处理。v2 应区分至少以下情况：

- **正常 co-occurrence。** 例如 gate cell 同时带有 `device_id` 与 gate-net `net_id`，这是正常 gate attribution。
- **Diffusion sharing。** OD / S/D derived layer 上多个 device attribution 可能表示共享 diffusion，应进入 occupancy sharing / connectivity component / pin-role attribution，而不是直接报错。
- **Same-conductor merge。** 多个 annotated cells 可能经 connectivity state 属于同一 conductor；是否允许同网相邻、same-conductor spacing exemption，应由 connectivity component 与 net annotation summary 判断。
- **Net collision / short。** 同一 conductor component 或同一 occupancy region 出现不可解释的多个 schematic net，应报 conflict。
- **Device collision。** 非 sharing policy 覆盖的 device overlap，应报 ambiguous / unsupported。
- **Layer-map ambiguity。** 一个 derived layer 无法映射到唯一 GDS target，或多个 mapping 同时命中且无 precedence，应报配置错误。
- **Tolerance ambiguity。** LVS shape 与多个 GDS occupant 在 tolerance 内均可匹配但无法消歧，应报 ambiguous annotation，而不是随机选择。

Conflict policy 的输出应结构化，包括 affected layer / cells / shape ids / schematic ids / LVS ids / source evidence backlink / severity / recommended action。Stage 4–5 可基于 severity 决定 fail-fast、保守 blockage、人工 review 或允许继续。

### 5.8 Unannotated geometry 与 conservative policy

LVS annotation 不完整是常态。v2 对 unannotated geometry 的默认策略是保守处理：

- 保留 drawn geometry。
- 对参与 occupancy 的 A/B layers 投影到 occupancy；C1/C2 仍保留在 layout store，只有 policy 明确时才生成 blockage shadow。
- 按 layer role 与 policy 标记为 blockage、unknown conductor、suspect geometry、marker 或 auxiliary geometry。
- 对 boundary dummy gate、dummy device、filler、ESD、marker、waiver carrier 或 LVS deck 暂未识别的寄生 device，必须通过 coverage / conflict / fixture limitation 暴露其语义缺口；不能因为 CDL 未列出就静默丢弃或自动归并。
- 不自动 traverse、merge、delete。
- 不把 `net_id=None` 当作“与所有 named nets 兼容”。
- 与 annotated geometry 冲突时保守失败或标记 suspect。
- 在 coverage report 中暴露 coverage gap。

Coverage report 应至少能回答：

- 每个 layer 有多少 GDS cells / shapes。
- 其中多少被 LVS annotation 覆盖。
- 多少成为 blockage / unknown / suspect。
- 哪些 annotation evidence 没有匹配到 GDS occupant。
- 哪些 GDS occupant 没有 annotation evidence。
- 哪些 conflict 被降级、跳过或需要人工确认。

对于 production flow，coverage gap 不是自动错误；但任何继续执行的 policy 都必须显式、可审计，并进入 report / validation result。

### 5.9 Stage 边界与消费方式

Calibre query bundle 属于 Stage 1 evidence acquisition。Stage 1 可以运行 Calibre query、读取 raw output、生成 schema-canonical YAML / object，并做基本格式一致性检查。

Stage 2 消费这些 evidence，完成：

- canonical semantic ids 与 run-scoped LVS/layout identity join table。
- layout store construction。
- occupancy projection。
- annotation overlay。
- coverage / conflict report。
- connectivity state 初始化所需的 identity reference。

Stage 3 以后不应重新读取 raw query output 来构建另一套状态。Planner、constraint、transaction、exporter 应读取 Stage 2 后的 authoritative state、annotation references、connectivity state 和 derived views，而不是直接依赖 Calibre query globals。

### 5.10 Legacy JSON 的非目标定位

`calibre_device_query.json` 和 `calibre_net_query.json` 属于 legacy MVP convenience format，不是 v2 主路径。它们的问题不是“格式是 JSON”，而是它们把 production 中应由 GDS、CDL、Calibre query bundle、layer mapping 和 overlay 共同决定的事实提前揉成 parser-friendly 工作状态。

v2 不需要为这条 legacy JSON path 设计 compatibility adapter。符合 v2 架构要求的 parser、GDS IO、Calibre query parser、tech config loader、测试 harness 等代码可以按职责复用；把 legacy JSON 当作工作状态来源的路径应重构或删除，而不是在 v2 中继续适配。

目标合同是：

- architecture、fixture 和 pipeline plan 不依赖 legacy JSON 字段构建正确状态。
- `Device.fin_track_indices`、`Net.segments`、`Net.vias` 等长期工作状态不再由 legacy JSON 派生。
- 新测试 fixture 使用真实或拟真的 `ixref`、`net_xref`、`device_info`、`net_shapes` middle files。
- Stage 1 / Stage 2 的主路径只接受 v2 evidence bundle 与 normalized objects；任何 legacy-only convenience field 都不能进入目标 architecture。
- 删除 legacy path 时不需要保证与 legacy MVP 行为兼容；只需保留并迁移其中符合 v2 架构要求、且职责边界清晰的可复用实现。

## 6. 基于物理事实的修改语义

第 6 节定义“一个 target intent 在物理版图中到底意味着什么”。它不是 planner API 的完整说明，也不是 transaction 实现细节；它给后续第 7–9 节提供语义基线：planner 只能规划这些语义允许的候选，constraint engine 只检查候选是否可行，transaction 只提交已经通过检查的状态变化。

### 6.1 修改对象：semantic intent、物理实体与 candidate delta

版图修改不能从“目标参数变化”直接跳到“手写 bbox patch”。正确过程是：

1. 解释 target intent 的电路语义，例如 `MN0.nfin: 5 → 4`。
2. 找到受影响的物理实体，例如 device active region、S/D access、gate anchor、routing stubs、vias、derived markings。
3. 在 layout store / occupancy / connectivity 的坐标和 cell 表示中构造 candidate delta。
4. 在 transaction checkpoint 内把 proposed delta materialize 为 tentative base / annotation / connectivity state；该 overlay 对外不可见。
5. 由 constraint engine 检查 tentative state；可行后在同一 overlay finalise annotation / derived state，再按 apply_atomicity 发布 CommitEnvelope。

这里的 candidate delta 是“待检查的状态变化描述”，不是事实本身。它可以引用 shape id、cell id、device id、net/component id、old/new coverage、受影响区域和 provenance seed；但在 feasibility 成功之前，不得永久修改 `AuthoritativeState` 的任何 component 或 exporter artifact。

这个边界是 v2 相比 legacy MVP 的关键修正：宏不能先改 `shape_pool`、`grid.b_tier_cells` 或 output JSON，再依赖后续步骤补救；宏只能先提出候选，事务提交成功后才把候选写入唯一权威状态。

### 6.2 `nfin` resize 的物理含义：OD active coverage 变化

在 FinFET standard-cell 中，FIN 是静态 grating / backdrop；`nfin` 表示 device active region 覆盖了多少条 FIN track，而不是版图中实际存在多少条 FIN shape。因此，`nfin` resize 的物理含义是：

- FIN stripe 集合保持不变。
- device 的 OD active coverage 发生 shrink / grow。
- active fin count 由 `FIN stripe ∩ OD coverage ∩ device region` 的几何关系派生。
- device 的 semantic `nfin` 参数在 commit 后更新，用于 CDL/export/report；它不直接拥有 FIN 几何。
- FIN attribution、gate track、routing spans、vias 等都是从 committed state 派生的 read views，而不是 resize macro 私有维护的长期几何副本。

因此，`nfin: 5 → 4` 的目标行为不是删除一条 FIN，而是把该 device 的 OD active coverage 调整到只覆盖 4 条 active FIN track。输出 GDS 中 FIN 层应与输入 FIN backdrop 保持一致；如果 FIN layer 被标记为 derived / static / non-editable，任何 resize candidate 中出现 `add FIN` / `remove FIN` 都应被拒绝。

### 6.3 固定 cell frame 下的 resize placement model

v2 对 standard-cell 内 `nfin` resize 采用固定 frame 模型：

- cell boundary 不因一次局部 drive-strength ECO 改变。
- VSS / VDD rails、M1 rail locations、rail-side gate endpoints、FIN backdrop、NWELL / BOUNDARY 等 frame-level geometry 原则上保持稳定。
- `nfin` shrink / grow 通过调整 device OD active coverage 完成。
- shrink / grow 的默认方向是 device 面向 N/P gap 的一侧，而不是任意删除顶部或底部 FIN。
- anchor direction 应从几何关系推导，例如 device 与 rail / gap 的相对位置；不应仅依赖 `nmos` / `pmos` 字符串硬编码。
- POLY / gate 在 MVP `nfin` shrink 中通常作为 attribution anchor 保持不动；只有当候选明确证明 gate endpoint、pin access 或 design rule 需要调整时，才规划局部 gate / access 修复。

在当前 inverter fixture 的典型 `MN0: 5 → 4` / `MP0: 7 → 6` shrink 中，语义上应分别减少靠近 N/P gap 的 active OD coverage：NMOS 去掉 gap-side 的上侧 active fin，PMOS 去掉 gap-side 的下侧 active fin。FIN 本身不变；cell height、rails、M1 rail、NWELL / BOUNDARY 不应被 shrink-to-fit 地重新解释。

这个 placement model 只定义初始 v2 的 deterministic policy。将来可以由 search / RL / LLM 或更复杂 router 选择不同合法候选，但这些候选仍必须满足同一事实模型：先规划 OD / access / routing 的 state delta，再经 constraint 检查后提交。

### 6.4 Static FIN / gate backdrop 下的 resize candidate 内容

Resize planner 至少应显式处理以下问题：

- 哪些 FIN track 在 cell 中存在，且作为 static backdrop 保持不变。
- 哪些 FIN track 被旧 OD 覆盖，哪些会被新 OD 覆盖。
- 新旧 OD coverage 对 `Device.nfin`、device attribution、diffusion sharing、split diffusion 的影响。
- 被 OD shrink / grow 影响的 S/D LI bars、via coverage、M1 stubs 与 local net connectivity。
- 受影响区域内是否存在 unannotated blockage、cut barrier、derived marking 或 signoff-only risk。
- atomic publication 前需要 finalise 的 Tier C1 layout geometry，例如 NWELL / BOUNDARY / VT / PP / NP / DNW。
- publication 前需要刷新或 invalidate 的 read views，例如 fin attribution、gate tracks、segments、vias、annotation coverage、net-to-component summary。

任何 resize candidate 都不应包含 `add FIN` / `remove FIN` 这类操作。若某个 target delta 只能通过编辑 FIN 才能实现，v2 应将其判定为 unsupported 或需要更高层 cell regeneration，而不是在局部 ECO 中修改 FIN grating。

### 6.5 Routing、via、cut 与 derived markings 的局部修复

OD active coverage 改变可能连带影响多类局部对象：

- S/D LI bars 的长度、端点或覆盖关系。
- VIA0 / local via 的 enclosure、连接关系与可保留性。
- M1 stubs 或更高 routing 的局部连接。
- cut / barrier 对 connectivity component 的切分。
- Tier C1 derived markings，例如 NWELL、BOUNDARY、VT、PP、NP 等。
- DRC / LVS localization 所需的 annotation summary 与 provenance。

这些修复应遵循同一个边界：

1. planner 从 candidate 的 old/new state delta 中计算受影响区域。
2. constraint engine 基于 occupancy、connectivity、blockage 与 rule predicates 判断局部修复是否可行。
3. transaction 在 private overlay 中 materialize concrete repair，通过 annotation refresh / invalidation request 生成 tentative annotation，并更新 connectivity effect。
4. derived finalization / view invalidation 完成后，再随同一 CommitEvent 原子发布 authoritative state。
5. Stage 6 只从 committed snapshot 导出 artifacts，不临时补 bbox，也不把 L1 EditOp replay 当作事实落点。

Routing / via 修复不应依赖“同名 net label 就等价”的 shortcut。DRC 的 same-conductor 判断应最终基于 connectivity component；semantic net label 只作为 annotation / export / localization 信息。尚未完成统一 connectivity substrate 时，应优先落地目标 substrate 或缩小支持范围并显式失败；不为 per-cell `net_id` label 设计兼容层。

### 6.6 Unsupported intent 与失败语义

Target-intent input 中的每个 target delta 都必须被 planner 明确处理：

- 已支持的 intent 生成一个或多个 candidate。
- 不支持的 intent 返回 typed unsupported result。
- 多个 intent 中只要存在无法覆盖且会影响输出正确性的项，默认必须在任何 partial commit 之前 typed-fail。只有 explicit waiver / partial-apply policy 才能继续，且结果必须标为 non-production / requires-review，不能算 clean pass。
- 不允许静默过滤未知参数、未知 device 操作、device add/remove、net reroute、VT/L/W 变化等目标差异。

这条规则防止 legacy MVP 中“只处理 `nfin`，其它 diff 被过滤后继续输出”的行为进入 v2 主路径。v2 可以分阶段只支持 `nfin` resize，但 unsupported 的内容必须成为结构化失败结果，而不是被当作无事发生。

### 6.7 Legacy MVP resize path 的偏差与可复用边界

legacy MVP 的 resize path 只能作为 legacy/reference，不作为第 6 节语义的正确基线。与目标语义相关的主要偏差包括：

- FIN 被当作可编辑层，resize 会产生 FIN add/remove 或删除 FIN `ShapeRecord`。
- OD 修改、FIN 删除、LI reshape 等 side effects 可能在 constraint feasibility 完成前写入不同状态对象。
- B-tier occupancy、CSP engine cells、`shape_pool` 和 output JSON 之间存在多份可能漂移的几何表示。
- 成功 macro 不一定让下一次 macro 立即看到 committed geometry / semantic state。
- Stage 6 replay / decoder patch 曾承担事实落点角色，而 v2 要求 Stage 5 commit 后 state 已经权威。
- 当前 shrink 位置选择是硬编码策略，不是显式 candidate planning seam。
- legacy fixture 里存在 shrink-to-fit、FIN 局部绘制、enclosure / spacing 等 correctness gaps，不能反推为目标架构允许的物理模型。

可以复用的部分仅限于符合 v2 边界的实现片段，例如解析、单位转换、部分 GDS IO、部分 Calibre query 读取、测试 harness、部分 rule predicate 或 geometry helper。涉及 FIN edit、pre-commit state mutation、legacy JSON 主路径、Stage 6 canonical writeback、silent unsupported filtering 的逻辑应作为重构对象，而不是兼容目标。

## 7. 修改意图与候选规划

第 7 节定义 Stage 4 的职责：把 target intent 转换为可检查、可排序、可回滚的 candidate plan。第 6 节已经定义了 `nfin` resize 的物理语义；第 7 节不重新解释这些语义，而是规定 planner 如何在这些语义边界内生成候选。

Stage 4 的核心边界是：

- 输入是 Stage 2/3 已归一化的 immutable target intent、current semantic state、versioned snapshot、occupancy、connectivity、annotation references 与 constraint context。
- 输出是 planning result：candidate plans、unsupported intent failures、planning warnings、required checks、affected regions 和 provenance seeds。
- Candidate 是待检查计划，不是 committed geometry。
- Macro 是特定 intent 的 planner implementation，不是 transaction commit owner。
- Stage 4 不修改 authoritative state，不导出 artifact，不把 legacy edit stream 当作修改事实源。
- 所有 persistent mutation 只能发生在 Stage 5 transaction commit 中。

### 7.1 Target intent / diff model

Target intent 的 raw source 在 Stage 1 获取，例如 source/target CDL、ECO command、用户指定 intent 或未来 signoff feedback；它在 Stage 2 被归一化为独立 immutable `TargetIntent`，引用 canonical semantic ids 但不成为 mutable current semantic IR 的一部分。第 7 节不定义 raw input file format，而定义 Stage 4 planner-facing intent contract。Stage 4 不直接消费 raw CDL diff、raw command 或 raw signoff log。

每个 target delta 至少应包含：

- `delta_id`：稳定标识，用于 report、failure、provenance 和 validation。
- `source`：例如 CDL diff、ECO command、DRC feedback、user command。
- `op_type`：resize、device add/remove、net reroute、cut/share/split、pin access repair、derived refresh request 等。
- `operand_ref`：目标 device、net、pin、region、component 或 shape reference。
- `semantic_before` / `semantic_after`：参数变化、topology 变化或 connectivity intent。
- `scope`：single device、single net、single cell、bounded region 等。
- `hard_constraints`：必须满足的约束，例如固定 rail、固定 boundary、不可移动 shape、avoid region。
- `preferences`：可排序偏好，例如 gap-side shrink、少改动、低 via count、保持 pin access。
- `required_capability`：该 delta 需要哪个 planner / macro capability 覆盖。
- `provenance`：从哪些 evidence、annotation 或 diff 规则产生。

Stage 4 必须先对全部 target delta 做 **all-delta capability admission**：只要存在 unsupported delta，整个 planning result 默认失败，不进入 Stage 5；不能像 legacy MVP 那样在 dispatch 表中把无 macro 覆盖的 diff 静默过滤。执行原子性由独立的 `apply_atomicity = whole_intent | dependency_group | candidate` 决定，默认 `whole_intent`。未来如果需要 partial apply，必须由显式 policy 打开，并在 report / validation result 中标记 skipped / already-applied delta、风险与 non-production / requires-review outcome。

### 7.2 Planner / macro interface

Planner 的输出是 `PlanningResult`，而不是 edit stream。每份 planning result 绑定一个 base snapshot、包含一个 publication group 的候选 alternatives；partial chain 中每个新 snapshot 都对应一份新的 PlanningResult。一个 planning result 应包含：

- candidate plan 列表，通常按 delta 或 dependency group 组织。
- `base_snapshot_id`、candidate read-set / old-state preconditions 与 `apply_atomicity`。
- unsupported delta 列表。
- planning warnings，例如 evidence 不完整、annotation coverage 降级、候选空间被 policy 缩小。
- required checks，例如 DRC、connectivity、blockage、same-component、pin access、derived refresh。
- affected regions，例如需要重算 occupancy、connectivity、derived marking 或 annotation coverage 的区域。
- expected validation assertions，例如 “FIN layer invariant”、“Device.nfin committed to target”、“affected net remains connected”。
- provenance seeds，用于 Stage 5 commit log 和 Stage 6 report。

Stage 4 推荐使用以下层次表达规划过程：

```text
TargetIntent / TargetDelta
  → PlanningTask
  → MacroPlanner
  → CandidatePlan
  → RepairRequirement / SubCandidate
  → ProposedMutationSpec
  → Stage 5 transaction
```

这些层次的职责是：

- `TargetIntent` / `TargetDelta`：描述目标语义变化，例如某个 device 参数、net topology 或 repair request。
- `PlanningTask`：planner 对一个或多个 delta 做 grouping、ordering 和 dependency 分析后的规划任务。
- `MacroPlanner`：某类 task 的候选生成器，例如 resize planner。
- `CandidatePlan`：一个待检查的候选方案，引用 semantic object、shape、occupancy cell、connectivity component、affected region 和 required checks。
- `RepairRequirement` / `SubCandidate`：候选内部的局部修复需求，或已经具体化的修复子候选。
- `ProposedMutationSpec`：Stage 4 完成规划后、Stage 5 transaction 可消费的 proposed mutation 描述；真正的 `StagedMutation` / `StagedStateView` 只在 Stage 5 overlay 中创建。
- Stage 5 transaction：唯一可以把 staged changes 提交为 authoritative state 的阶段。

这个结构只借鉴 legacy MVP 自顶向下拆解的思路，不继承 legacy L1–L4 edit-op pipeline。v2 中 `EditOp`、SKILL edit 和 report diff 是 post-commit artifact-specific representation，不能作为 Stage 4 的主输出。

Candidate plan 应尽量以 domain / state 层对象表达，而不是以 artifact bbox 表达：

- semantic object references：`device_id`、`net_id`、`pin_id`、intent delta id。
- version / preconditions：`base_snapshot_id`、`semantic_before`、shape / cell / component old-state assertions；stale candidate 必须 replan / rebase 或 typed-fail。
- geometry references：`shape_id`、layer、purpose、old/new coverage region。
- occupancy references：A-tier / B-tier cell ids、old/new occupancy、release/assign intent。
- connectivity effects：可能新增或删除的 component edge、via edge、cut barrier、diffusion sharing relation。
- repair requirements：受 resize 影响的 LI / VIA / M1 / cut / derived marking 修复需求；可执行 candidate 必须已解析成 concrete sub-candidate。
- finalization scope：Tier C1 markings、annotation attribution / validity、read/export views 的刷新或 invalidation 范围。
- required rule checks：候选需要第 8 节约束系统检查，并在第 9 节事务边界内提交 / 回滚的 rule predicates 与 validation expectations。
- candidate policy metadata：ranking score、tie-breaker、chosen anchor、rejected alternatives。
- provenance seed：产生该候选所用的 evidence、policy 和 planner version。

Candidate plan 不是 committed state，也不是 L1 `EditOp`。`EditOp`、SKILL edit、diff visualization 或 report item 可以在 Stage 5 commit 后由 `ChangeSet` / `CommitEvent` 派生，但不能作为 Stage 4 的唯一修改事实。

Planner 是 Stage 4 的协调层；macro 是某一类 intent 的 planner implementation。两者都不能绕过 state / constraint / transaction 边界直接输出最终 GDS bbox。

推荐接口边界如下：

1. Planner 接收 typed target intent、planning context、policy 和 capability registry。
2. Planner 对所有 delta 做 coverage check，形成 supported / unsupported 列表。
3. 对 supported delta，Planner 调用对应 macro 生成一个或多个 candidate plan。
4. Macro 可以读取 semantic IR、layout store、occupancy、connectivity、annotation references 和 constraint context 的只读 planning view。
5. Macro 不直接调用 persistent mutation API，不导出 artifact，不提交 transaction。
6. Planner 返回完整 `PlanningResult`，交由 Stage 5 做 feasibility staging、constraint check 和 commit。

为了支持后续 agentic coding，macro 的失败也应结构化表达：例如 evidence 缺失、operand 不存在、候选空间为空、policy 禁止、capability 未实现。失败必须发生在任何事务 side effect 之前。

### 7.3 v2 MVP 的 resize planning 特例

第 7.3 是第 7.2 通用 planner contract 在 v2 MVP `nfin` resize 上的特例化。Resize planner 不重新定义物理语义；它必须遵守第 6.2–6.5 定义的 static FIN、OD-driven resize、fixed frame、gap-side placement 和局部 repair 边界。

对于一个 `Device.nfin: old → new` delta，推荐映射为：

- `TargetDelta`：device parameter resize，operand 是目标 `device_id`，semantic delta 是 `nfin old → new`。
- `PlanningTask`：single-device resize task，记录 policy、scope、dependency 和 required capability。
- `MacroPlanner`：resize planner，根据 semantic IR、layout state、occupancy、connectivity 和 annotation references 生成候选。
- `CandidatePlan`：一个或多个 old/new OD coverage candidate，附带 affected occupancy、connectivity effects、repair requirements、required checks、candidate ranking metadata 和 provenance。
- `RepairRequirement` / `SubCandidate`：LI / VIA0 / M1 / cut / derived marking 的局部修复需求，或已经具体化的 repair sub-candidate。
- `ProposedMutationSpec`：Stage 5 可消费的 current-semantic update、geometry / occupancy delta、connectivity effect expectation、annotation refresh / invalidation request 与 derived dirty-scope hint；planner 不能直接指定 authoritative annotation value 或 C1 shape。

Resize candidate 不应包含 `add FIN` / `remove FIN` 操作。FIN attribution、gate tracks、segments、vias、annotation coverage 等应作为 committed state 的 derived views 重算；planner 不应把这些派生视图作为长期可变字段直接改写。

Shrink-only 是 v2 MVP 的最低 capability，同时必须表达为 capability / candidate-selection policy，而不是散落在 bbox arithmetic 中。Grow 或更多候选策略通过同一 planning seam 接入并显式声明；未声明时返回 typed unsupported。

### 7.4 Resize repair planning

`nfin` resize 可能连带要求局部 repair。第 6.5 已经定义这些 repair 的语义边界；第 7.4 只规定 planner 如何表达它们。

Resize repair planning 应覆盖：

- S/D LI bars 的长度、端点或覆盖关系是否需要调整。
- VIA0 / local via 是否仍满足 enclosure 和 connectivity。
- M1 stubs 或局部 access 是否仍连接到目标 component。
- cut / barrier 是否影响 component 切分。
- derived markings 是否需要刷新。
- annotation summary、provenance、validation expectation 是否需要更新。

Planner 可以在诊断与候选形成过程中使用两种 repair 表达：

1. **Repair requirement**：说明尚待 planner / router 具体化的必要 repair；含有此未解析 requirement 的 candidate 是 incomplete / non-executable，Stage 5 必须拒绝。
2. **Concrete repair candidate**：planner 已经给出具体 old/new occupancy 或 geometry coverage，由 Stage 5 检查后提交。

无论哪种表达，repair 都不能在 Stage 4 直接写入 layout store、occupancy、connectivity 或 output artifact。Stage 4 必须先把所有 required repair 解析为 concrete sub-candidate / `ProposedMutationSpec`；Stage 5 只机械 staging、检查与原子发布，不承担 routing / repair planning。

通用 routing subsystem，例如 device add/remove、arbitrary net reroute、buffer insert、rip-up and reroute、multi-net search，不属于 v2 初始 resize MVP 的第 7 节主线。它们应作为长期目标另行定义；当前第 7 节只要求 resize 相关的局部 repair 能被 candidate 显式表达并交给后续阶段检查。

### 7.5 Unsupported intent handling

Unsupported intent 必须显式失败，不得静默跳过。

Stage 4 应在生成任何可执行候选之前完成全量 coverage check。失败结果应包含：

- unsupported delta id。
- op type。
- operand reference。
- required capability。
- unsupported reason。
- 是否有候选被生成但未执行。
- 建议的后续 capability，例如需要 device add macro、需要 general router、需要 signoff feedback ingestion。
- 状态副作用保证：**本次** Stage 4 attempt 未新增 Stage 2/3/5 side effect；若处于 explicit partial chain，earlier published CommitEnvelopes 必须另列且不伪装回滚。

默认情况下，任何 unsupported delta 都使整个 planning result 失败，并阻止 Stage 5 commit。未来如果允许 partial apply，必须由 explicit policy 打开；Stage 6 report / validation result 必须清楚记录哪些 delta 被应用、哪些被跳过、为什么跳过，以及由此产生的工程风险。

### 7.6 Stage 4 与后续阶段的接口

Stage 4 输出的 `PlanningResult` 是下一次 Stage 5 feasibility / transaction 的输入；partial policy 每发布一个 envelope 就返回 Stage 4 生成新结果。Pipeline 在 Stage 4↔5 迭代结束时把各轮中立 planning / constraint audit records 按序冻结到唯一 RunRecord；Stage 6 不直接读取 live PlanningResult。

接口关系如下：

- Constraint system 消费 proposed delta / context，并独立从 tech / layer / action policy 推导 mandatory checks 与 expanded affected scope；candidate 的 required checks / region 只是附加 assertion / hint。
- Transaction system 把 `ProposedMutationSpec` 映射为 staged changes；检查和 finalization 成功后按 `apply_atomicity` 原子发布 authoritative state。
- Commit 后产生 `ChangeSet` / `CommitEvent`，而不是把 Stage 4 candidate 本身当作 committed geometry。
- Export / validation / reporting 从 final immutable snapshot、ordered ChangeSet / CommitEvent chain 与 frozen RunRecord 中的 planning provenance 生成 artifacts、report 和 validation result。
- Candidate、ChangeSet、ExportEdit 三者必须分层：candidate 是计划，ChangeSet 是已提交事实，ExportEdit 是 artifact-specific 派生产物。

这个边界保证：规划可以产生多个候选和失败解释；约束系统可以拒绝候选且无副作用；成功提交会更新权威状态；导出阶段只读取 committed snapshot，不再补写 architecture state。

## 8. 约束系统与可行性检查

第 8 节定义 Stage 3 / Stage 5 中“候选是否合法”的判断模型。这里的重点不是沿用 legacy MVP 的 `ConstraintEngine.cells + CellState(net_id)` 实现，而是把 backlog 已经指出的问题吸收到 v2 目标架构中：occupancy 是离散几何工作基底，connectivity 是 same-conductor 判断依据，constraint engine 只叠加 domain / trail / rule predicates，不再拥有另一份可漂移的版图状态。

### 8.1 Constraint engine

Constraint engine 的职责是判断 candidate 是否可行，并在 neutral `StagedStateView` / trail protocol 上提供局部传播与 rule result。它不拥有完整 transaction，也不应成为另一个长期 occupancy owner，或把 semantic `net_id` / `device_id` 复制成 DRC 判断的权威身份。

它读取：

- Stage 2 建立的 coordinate system。
- authoritative occupancy store。
- connectivity index。
- rule records / rule predicates。
- candidate staged changes。
- blockage / fixed / cut / via context。
- annotation / identity references 的只读摘要，仅用于定位、报告或 policy 判断。

输出：

- feasible / infeasible。
- violation list。
- affected cells / neighborhoods。
- propagated domain changes。
- connectivity delta / refresh request。
- transaction trail entries。

有效检查集必须是 `tech/layer/action policy` 推导的 mandatory checks 与 candidate intent-specific assertions 的并集；affected scope 必须由 proposed mutations 重新计算，并按 rule halo、via / cut relation 与 connectivity-component closure 扩张。Candidate 自报字段不得关闭 mandatory predicate 或缩小检查范围。

v2 目标合同是：constraint engine 可以维护 domain、trail、propagation queue、局部 rule cache 和 checkpoint metadata，但不能维护一份独立的 layout occupancy truth。legacy MVP 中 `engine.cells` 保存 `CellState(occ_type, net_id)`、再由 `load_existing_layout` / `load_b_tier_cells_into_engine` 从 model 拷贝状态的做法，只能作为迁移期实现；v2 应收敛为“engine over store”：engine 以 occupancy `CellId` 为 key 叠加 domain / trail，候选提交直接作用于 authoritative occupancy / connectivity，并由同一 transaction 保护。

因此，constraint engine 的 cell state 应尽量缩小为候选检查需要的状态轴，例如 empty / occupied / barrier / fixed / candidate marker，以及必要的 rule-local width / line-end metadata。Occupant kind、shape reference、semantic net/device identity 属于 occupancy store 或 annotation / semantic IR，不应长期复制到 engine state。

### 8.2 Legacy CSP 中应吸收的 modeling / propagation 机制

Legacy MVP 的 CSP 实现虽然在状态所有权和 `net_id` 建模上不符合 v2 目标，但其中有几类机制是 v2 可以且应该吸收的。吸收方式不是复制当前对象结构，而是保留其算法合同并换到 v2 的 store / connectivity / transaction 边界上。

应吸收的部分：

- **规则模板化。** 现有 DRC rule 使用 stencil / trigger / forbidden 的模式：某个确定 cell 状态触发规则，然后在邻域 stencil 内剪掉非法状态。v2 可以保留这种 rule predicate 组织方式，但 forbidden 的判定应从 `CellState(net_id)` 集合剪枝，改为查询 occupancy / connectivity / geometry context。
- **只从 determined state 传播。** legacy `_propagate` 只在 cell domain 已经收敛到单值时触发邻域传播，避免把“可能成为某 net / 某状态”的 cell 提前当作事实传播。这一点应保留：v2 propagation 只应从 staged assignment、fixed occupancy、barrier 或已确定的 derived condition 出发。
- **队列式局部传播。** legacy 使用 queue 从 changed cell 做局部 cascade，并在邻居 domain 收敛后继续传播。v2 应继续采用局部增量传播，而不是每个 candidate 都全图重跑；传播范围由 rule stencil、affected region 和 connectivity delta 共同限定。
- **trail-based transaction。** legacy trail 同时记录 prior domain 和 prior assignment，使 checkpoint / restore 能精确回滚失败 proposal；union-find trail 也能随 checkpoint 回滚。v2 应把这个思想推广到 occupancy change、connectivity edge/component change、derived cache invalidation 和 rule-domain/cache change 的统一 transaction trail。
- **proposal API。** `propose_assign` / `propose_release` 的语义是“候选修改可能失败，调用方必须在 checkpoint 内提交或回滚”。v2 应保留这个 API 语义，但 proposal 的目标应是 authoritative occupancy / layout_store 的 staged change，而不是 engine 内部 occupancy copy。
- **deterministic commit delta。** legacy commit 根据 checkpoint 后的 trail 汇总 cell delta，并按 `(layer, track, ortho)` 稳定排序。v2 的 ChangeSet / CommitEvent 也应具备稳定排序、可审计 old/new state、以及可从 transaction trail 汇总的性质。
- **fixed blockage / cut barrier 语义。** legacy `mark_blockage` / `mark_cut` 把不可编辑障碍与 cut 固定为 singleton 状态，并在已有 annotated assignment 上拒绝覆盖。这种保守冲突策略应保留：unannotated geometry、blockage、cut、fixed frame 不能被候选静默覆盖。
- **可逆 connectivity trail。** legacy union-find 为 rollback 放弃 path compression，并用 union trail 记录 merge。v2 的 connectivity index 应支持同等事务语义；no-compression reversible union-find 只适用于 additive overlay / 回滚新增 merge。既有 edge removal、CUT insertion 或 OD split 导致的 component split 必须采用 affected-component rebuild 或真正支持 deletion 的 transactional connectivity 结构，并保证与 occupancy staging 同 checkpoint / restore。
- **传播统计。** legacy `propagate_stats` 记录按 seed layer 聚合的 calls / visited cells / time。v2 应保留类似 observability，用于发现 rule 或 layer 的传播热点，并把它纳入 validation / performance report。

不应吸收的部分：

- 不吸收 per-cell `CellState.net_id` 作为 same-conductor 判据。
- 不吸收 `occ_type × net_id` 的 domain 展开。
- 不吸收 engine 自己长期持有 occupancy copy 的所有权模型。
- 不吸收 VIA0 通过 LI/M1 wire double-stamp 伪造跨层连通的做法。
- 不吸收 `net_id=None` 彼此兼容的乐观 spacing 语义。

因此，v2 的 constraint engine 可以继承 legacy CSP 的“模板化局部规则 + determined-only propagation + reversible trail + proposal/commit delta”算法骨架；但状态身份、连通性身份和持久 occupancy ownership 必须按第 3、5、9 节的 v2 state model 重建。

### 8.3 Rule records 与 predicates

Rule deck 应使用结构化 rule records 表达 min width、spacing、pitch、enclosure、extension、exact size、coloring、cut / barrier、via relation 等规则。Constraint engine 消费其中可在 candidate 阶段判断的 subset。

Rule predicate 的输入应是明确的上下文对象，而不是散落读取 artifact 或 legacy working representation：

- coordinate context：layer、track axis、pitch、width、orientation、B-tier axes。
- occupancy context：某 cell / neighborhood 是否被占用、被何类物理对象占用、是否 fixed / blockage / barrier。
- geometry context：shape bbox、cell coverage、enclosure / overlap / extension。
- connectivity context：两个 occupant 是否属于同一 connected component，cut 是否切断 component，via 是否提供跨层 edge。
- annotation / semantic context：仅用于报告、localization、intent policy 或 rule 例外的显式输入，不作为 same-conductor 的默认判据。

对 capability 已声明支持、且 candidate 触及范围内可判定的基础局部规则，Stage 5 必须检查，而不能依赖输出 GDS 后的外部 DRC 才发现；这包括局部 spacing、via enclosure、cut barrier、OD sharing / spacing 与 blockage conflict。缺少必要 predicate 时 capability admission 必须失败。复杂 coloring、全芯片密度、foundry deck 中无法简化的派生层规则可以明确归为 signoff-only。

对 `nfin` resize，Stage 5 还必须执行 intent invariants，而不能把它们只留作 Stage 6 expectation：parent active-fin count 等于 `semantic_before`；candidate count 等于 `semantic_after`；FIN 与 fixed frame 不变；未受影响 device 的 count / topology 不变；touched pin/device 到目标 component 的 reachability 满足 intent；具有冲突 schematic-net annotation 的 components 不得被合并。DRC feasible 但 intent invariant 失败的 candidate 仍不可提交。

### 8.4 Occupancy-aware DRC

DRC 判断应基于 occupancy 和 shape geometry，而不是直接基于 legacy `Net.segments`、`Device.fin_track_indices` 或 output JSON。`Net.segments`、vias、fin attribution、gate tracks 等在 v2 中都是 derived views；它们可以帮助定位和展示，但不能成为 rule predicate 的事实源。

CSP-frontline 至少应覆盖这些局部规则族：

- same-layer spacing / adjacent-track spacing。
- min width / exact width / line-end 与 extension 检查。
- via enclosure、via-to-wire overlap、via stack relation。
- cut barrier 对连通性的影响。
- OD spacing、diffusion sharing、split diffusion 的局部合法性。
- blockage / fixed geometry conflict。
- derived layer refresh region 的基本一致性检查，例如 Tier C1 families（VT / well / boundary 等）的受影响范围。

Occupancy-aware DRC 的正确状态依赖第 3、5、9 节定义的单一状态所有权：candidate 在 Stage 5 transaction 中 staged 到 occupancy / layout store 后检查，成功后提交到同一个 authoritative state。不能出现“engine 接受了候选，但 shape_pool / layout_store 仍是旧 LI/M1 几何，导出靠 decoder patch”的状态漂移。

### 8.5 Connectivity-aware same-conductor reasoning

Same-net spacing exemption 不应简单比较 cell 上的 scalar `net_id`。更稳健、也更符合 DRC 语义的判断是：两个对象是否属于同一物理连通 component。

这样可以避免：

- same net label 但物理 disconnected 的对象被错误放宽。
- unknown / unannotated geometry 被乐观处理。
- via-as-wire 多重表示被用于伪造跨层连通。
- cut / barrier 已经切断几何，但 label 仍让 rule 误以为连通。

Connectivity index 应由 occupancy geometry 建立，至少包含：

- same-layer 相邻或重叠 conductor cell 的 edge。
- VIA / contact 形成的跨层 edge。
- CUT / barrier 对 edge 的删除或禁止。
- OD / diffusion sharing 与 split policy 对 component 的影响。

Net label 可作为 component 的属性用于报告、LVS localization、semantic consistency check 或未来的 policy 例外；但 rule 判断默认应以 connectivity 为准。对于 same-net-but-disconnected 的对象，v2 应采取保守策略：按不同 conductor 检查 spacing。若未来确有工艺或产品需要放宽，应显式引入“component → semantic net property”的 policy，而不是回到 per-cell `net_id` 比较。

这个修订与 backlog 中的 M11 方向一致：legacy union-find 不应只是测试覆盖的附属设施，而应成为 spacing / connectivity rule 的生产消费者；跨层连通必须通过 via edge 表达，而不是依赖 VIA0 被同时伪装成 LI/M1 wire。

### 8.6 Domain model 与 propagation 边界

Legacy MVP 的 domain 按 `occ_type × net_id` 展开，会制造大量不可达或无意义状态，例如 CUT 带 net 的组合，并使 domain 大小随 net 数增长。v2 不应继承这种 domain 设计。

v2 的 domain model 应遵守：

- domain 只表达候选检查真正会分支或传播的状态轴。
- semantic `net_id` / `device_id` 不进入 per-cell domain；它们属于 semantic / annotation / component summary。
- occupant kind 优先从 layer / occupancy record 得到；只有同层确实存在多种合法 occupant kind 时才进入 domain。
- CUT / barrier 是拓扑屏障或 occupancy record 属性，不是带 net fan-out 的可选状态。
- unknown / unannotated geometry 不应被乐观视为 compatible-with-everything；应投影为 blockage、suspect occupancy 或 disconnected component，并触发保守检查。

Propagation 的职责是对 staged candidate 做局部剪枝和冲突发现，不是进行全局搜索。只要当前架构仍以 macro / planner 提出候选、engine 检查候选为主，rule predicate 可以在 propose / stage 时结合 occupancy 与 connectivity 即时判断；不需要预先把所有 net-labeled 状态枚举进每个 cell domain。

### 8.7 CSP-frontline rules 与 signoff-only rules

v2 应区分：

- **CSP-frontline rules。** 修改候选必须立即满足，例如局部 spacing、via enclosure、blockage conflict、cut connectivity、OD sharing / split、fixed frame boundary、FIN static backdrop 不可编辑等。
- **Signoff-only rules。** 需要完整 foundry DRC/LVS 或复杂 coloring / density / full derived-layer deck 才能判断的规则。
- **Deferred rules。** 目标架构已留接口，但当前实现暂不覆盖，需要在 validation report 中说明风险。

Validation report 必须说明哪些规则在 CSP-frontline 检查，哪些交给 signoff，哪些被降级或跳过。对于被降级或跳过的规则，report 应记录原因：缺少 PDK deck、缺少 Calibre runtime、fixture 不覆盖、当前 planner scope 不支持，或该规则本身属于生产 signoff-only。

### 8.8 Rule gaps 与 correctness highlights

v2 开发应特别避免继承 backlog 已经指出的 correctness gaps。第 8 节相关的重点包括：

- FIN 是 static backdrop；任何 `add FIN` / `remove FIN` candidate 都应被 rule / edit policy 拒绝。
- VIA0 不应同时作为独立 via、B-tier occupancy、LI/M1 wire 多重表示；via enclosure 与跨层 connectivity 应从统一 occupancy + via edge 判断。
- LI / M1 的 committed 几何必须写回 authoritative state；不能只在 engine 或 EditOp stream 中存在。
- Raw `net_shapes` / `device_info` 是 annotation evidence，必须经过 layer mapping、effective-region tolerance 和 identity translation；不能直接当作完整几何事实或 rule truth。
- Per-cell `net_id=None` / unknown annotation 不能带来乐观 spacing 例外；应按 blockage / suspect / disconnected component 的保守语义处理。
- `Device.fin_track_indices`、`Net.segments`、`Net.vias` 等 derived views 不能被 rule predicate 当作长期事实源。
- 当前 fixture 中未覆盖的 VIA0 enclosure、LI spacing、cut / effective-region trimming、format verification 等问题，应进入 tests / validation plan，而不是被 architecture 默认视为已满足。

这些 highlights 不是独立需求池，而是第 3 节 state ownership、第 5 节 annotation、第 6–8 节修改/约束语义、第 9 节 transaction、第 10 节 export / validation 和第 11 节 module boundaries 的共同约束。后续实现不应把 legacy `ConstraintEngine.cells` 或 net-labeled domain 包装成目标架构的一部分；相关路径应按统一 occupancy / connectivity substrate 重构，未覆盖能力应显式失败。

## 9. 事务提交、派生状态与变更记录

第 9 节定义 Stage 5 如何把已经规划的 candidate materialize 到私有 overlay、完成约束与 finalization 检查，再变成 committed layout state。它要解决的核心问题是：所有持久状态必须在同一事务边界内一起成功或一起回滚；成功后，后续 planner、constraint engine、read-view recompute 和 exporter 都读取同一个 committed snapshot，下一次 transaction 的 derivator 也以它为 parent。

这个边界是 v2 对 legacy MVP 问题的直接修正。v2 不把 output JSON、L1 `EditOp` stream、临时 macro side effect 或导出阶段的补写结果当作 layout state。v2 architecture 只描述正确的目标状态模型；legacy MVP 中不符合这个模型的状态流应被重构或删除，而不是通过 adapter 继续保留。

### 9.1 Transaction scope

Stage 5 transaction 必须按 selected plan group 与 `apply_atomicity` 覆盖可能影响的全部持久状态：

- layout store geometry changes。
- occupancy changes。
- annotation attribution / reference / validity changes。
- connectivity changes。
- current semantic state changes；immutable target reference 不变。
- `coordinate_system_id` / `tech_bundle_id` 只作为 precondition binding，ECO transaction 不得修改。
- derived marking dirty scope 或 final derived delta。
- derived read-view / cache invalidation。
- commit log / ChangeSet / CommitEvent / per-publication CommitAuditRecord append；run-level RunRecord 由 Stage 5 orchestrator 在所有 plan groups 结束后冻结。

Transaction 的核心 staged object 是 `StagedStateView` 上的 state delta，transaction owner 不是 constraint engine 本身。Constraint engine 只消费 neutral staged-view / trail protocol并返回 propagation / rule result；真正的 commit 目标是整个 `AuthoritativeState`。Geometry、occupancy、annotation、current semantic、connectivity、derived finalization / view invalidation 与 commit log append 都必须围绕同一 plan group、同一 checkpoint 和同一 CommitEvent 保持一致。

OD shrink / grow、VIA / CUT 变化、diffusion sharing / split 等 B-tier change 也必须服从同一事务边界。它们不能只更新某个 bbox、某个 grid cell map、某个 helper-local object 或某个 output artifact；必须在同一 checkpoint 下 stage / validate / publish layout store geometry、occupancy release / assign、annotation attribution / invalidation、connectivity component / via edge / cut barrier、current semantic `Device` / `Net` state、derived dirty scope 与 ChangeSet。

标准顺序是：

1. 接收 Stage 4 selected plan group / `ProposedMutationSpec`，校验 `base_snapshot_id`、old-state preconditions 与 `apply_atomicity`。
2. 从 parent snapshot 打开 transaction-private overlay / checkpoint。
3. 在 overlay 中 materialize proposed geometry、occupancy、connectivity 与 current-semantic changes；annotation algorithm 根据 refresh / invalidation request 生成 tentative `AnnotationState`，形成对外不可见的 tentative base state。
4. 从 staged delta 独立推导 mandatory checks / affected scope，运行 constraint propagation、intent invariants、rule predicates 和 concrete repair checks。
5. 若任一检查失败，丢弃 overlay / restore checkpoint，并返回 typed failure。
6. 检查通过后，在同一 overlay 中 finalise annotation attribution / validity；若其变化影响 annotation-dependent topology，更新 connectivity、重算 affected scope 并重跑相关 mandatory checks，同时刷新或 invalidate rule-domain、component-summary 与 read-view cache；这些状态仍不可见。
7. 对需要进入 exported layout 的 Tier C1 markings 执行 final derivation，并运行 post-finalization invariants。
8. 比较 old/new base、annotation 与 derived state，生成完整 ChangeSet。
9. 若 finalization 或 post-check 失败，必须丢弃 overlay / restore parent snapshot，并返回 typed failure。
10. 按 `apply_atomicity` 将 AuthoritativeState version、immutable snapshot、ChangeSet、CommitEvent 与 CommitAuditRecord 封装为一次 `CommitEnvelope` 原子 publication；任一 per-commit sibling record 无法冻结都不得发布该 envelope。Explicit partial policy 发布后由 pipeline 返回 Stage 4，以新 snapshot 规划 remaining delta；Stage 5 不复用或 rebase 旧 candidate。Stage 4↔5 迭代结束后，orchestrator 冻结唯一 final RunRecord，Stage 6 只能在此后开始。

默认 whole-intent 只有一个 CommitEnvelope，final RunRecord 必须与它作为同一 `Stage5CompletionEnvelope` 原子发布。Explicit partial policy 可以先发布多个 CommitEnvelopes；此时 final RunRecord freeze failure 不回滚已发布 envelopes，但必须阻止正常 Stage 6 export，并由 final PipelineResult 标记 fail / requires-review。

Planner / macro 不能直接修改 committed layout store、`shape_pool`、B-tier occupancy、semantic device/net state 或 output artifact。它们只能产生 candidate / `ProposedMutationSpec`。任何需要持久修改的内容，都必须通过 Stage 5 transaction 发布到 authoritative state。

### 9.2 Commit to authoritative state

Commit 的目标是 authoritative layout state，不是 output JSON，也不是 legacy L1 `EditOp` stream。成功 commit 后，后续 planner、constraint engine、read-view recompute 和 exporter 都应读取同一个 committed state；C1 finalization 已在该 publication 前完成。

`AuthoritativeState` 是一组有明确 component ownership 的 committed state graph，至少包括 current semantic state、单一 geometry store（含 drawn 与 C1 derived partitions）、occupancy state、annotation state、connectivity state、read-view version / invalidation metadata，以及中立 state / snapshot / commit-link ids。Immutable target circuit / intent 属于 run input，由 `RunRecord` / snapshot context 引用而不进入可变 state graph。Full ChangeSet、CommitEvent、CommitAuditRecord 是 CommitEnvelope 中的 append-only sibling records；run-level RunRecord 在 Stage 5 结束后另行冻结。State/snapshot 不 import 或嵌入 transaction types。Materialized non-geometry views 不是 authoritative component。实现可以拆分 storage，但 atomic publication 必须保证所有 components 一致更新或一致回滚。

一次成功 commit 必须满足：

- geometry store 与 occupancy state 对同一物理对象给出一致 old/new。
- B-tier occupancy、A-tier occupancy、annotation 与 connectivity state 同步更新；rule-domain / cache 只需刷新或明确失效，不成为持久 truth。
- current semantic `Device` / `Net` state 只反映 target 明确要求的 circuit parameter / topology 结果，例如 `nfin` 与 schematic pin/net membership；physical pin-role attribution 留在 AnnotationState，diffusion sharing 留在 occupancy / connectivity，`shared_with` 等展示关系只是 view。Target reference 未被改写。
- C1 derived markings 已由 final derivation 刷新到与 base state 一致。
- derived read views 已刷新或明确失效，不能被后续阶段静默读取为 truth。
- 下一次 macro / planner 在同一 pipeline run 中读取到本次 commit 后的状态，不需要等待 Stage 6 decoder replay。
- ChangeSet / CommitEvent 已记录足够 old/new identity，使后续 ExportEdit、report、validation 和 debug 不需要把 L1 edit stream 当作几何事实源。

v2 可以复用 legacy MVP 中职责边界清楚、且不违背上述状态所有权的局部实现，例如稳定排序、纯 bbox 转换函数、可回滚 trail 的算法思想、纯导出 helper。凡是依赖 output replay、pre-commit side effect、独立漂移状态或 `EditOp` 作为唯一几何事实的实现，都不属于 v2 commit architecture。

### 9.3 Rollback consistency

失败回滚后必须保持一致：

- geometry 没有 partial bbox change。
- occupancy 没有 partial assign/release。
- annotation state 没有 partial attribution、stale-valid marker 或丢失的 invalidation。
- connectivity 没有残留 union、via edge、cut barrier 或 diffusion-share / split state。
- current semantic state 没有 partial parameter、device、pin 或 net update。
- derived markings 没有 partial bbox refresh 或 provenance stamp。
- derived read views / caches 没有 stale exposure。
- commit log 不记录 successful commit event。
- output artifact、ExportEdit、SKILL、report、validation result 不以失败 candidate 的 partial state 为输入。

Rollback 的判断基准是 `apply_atomicity` 对应的 parent plan-group snapshot，而不是某一个内部对象的 checkpoint。只恢复 constraint engine cells 不足以构成 rollback；layout store、occupancy store、annotation state、current semantic state、connectivity index 和 derived state 都必须恢复或未曾被持久修改。

失败 candidate / plan group 可以产生 diagnostic event，例如 `PlanningFailure`、`ConstraintFailure` 或 `TransactionRollbackEvent`，并在 Stage 5 终止时冻结到 failure RunRecord 用于 debug 和报告；但它们不是 CommitEvent，不能被 Stage 6 当成 committed delta 导出。若失败点正是 `run_record_freeze`，则按第 2.7 节唯一例外只保留 StageFailure + completed neutral audit refs。Partial-policy run 已有的 earlier CommitEvents 仍有效，必须与 failed delta 分列。

### 9.4 Derived markings finalization

Derived markings 的区分来自 layer tier 对物理实体的抽象。C1 derived markings 是会进入 exported layout 的几何层，例如 NWELL、BOUNDARY、VT、PP、NP、DNW；它们属于 layout state 的一部分，但其几何来源是 transaction-private tentative A/B-tier state、device metadata 与 tech rules，而不是 macro 手写 shape。

如果某类 C1 derived marking 不参与 planning、occupancy feasibility、connectivity 或 routing，它不需要在 candidate staging 的每一步都实时维护。v2 的默认模型是 final derivation：

1. Stage 5 在 transaction-private overlay 中 materialize 已通过约束检查的 tentative base state，包括 geometry、occupancy、annotation、connectivity 和 current semantic state；此时尚未 commit / publish。
2. 在发布对外可见的 committed snapshot 前，derivator 从 tentative base state、tech rules 和 affected scope 重新计算 C1 derived markings。
3. Derivator 产出的 derived geometry 与上一版 derived geometry 比较，形成 derived delta。
4. Base delta 与 derived delta 一起进入 ChangeSet / CommitEvent。
5. 只有 base state 与 derived markings 一致时，snapshot 才能发布给 Stage 6。

Final derivation 可以是全量 recompute，也可以是 affected-scope incremental recompute；这是实现策略，不改变 architecture contract。关键要求是 deterministic、可重算、可比较、可审计。

Derived finalization 失败时，不允许发布可导出的 committed snapshot。实现必须丢弃 overlay / 回滚到 parent snapshot，**并**返回 typed commit/finalization failure；不能暴露“base geometry 已变、C1 仍旧或半刷新”的 clean state。

Stage 6 不能临时运行 C1 derivator 来补几何。Stage 6 只能序列化 committed snapshot 中已经 final 的 derived markings。如果 Stage 6 发现 C1 derived markings 缺失、stale 或与 base state 不一致，应返回 validation failure；不得为了导出成功而在 Stage 6 补跑 derivator。

Planner / macro 不应直接覆写 C1 derived shape。对 C1 derived shape 的任何变化，都应来自 derivator 的 final result，并通过 derived delta 记录 provenance。

### 9.5 Derived views refresh

Read views 与 C1 derived markings 不同：它们通常不是单独的 exported physical layer，而是对 committed state 的查询视图或 materialized cache。Routing spans、vias、fin attribution、gate tracks、annotation coverage、device-owned active fins、net-to-component query summaries 等读取面必须从 committed state 重算或失效；权威 connectivity components 仍属于 ConnectivityState。

Read views 可以为了 planner、constraint、report 或 debug 被缓存，但不能被当作独立 truth；任何 cache 都必须能从 authoritative layout state 重建。

每个 commit 必须给出 view invalidation 所需的最小信息或保守信息：

- affected layers。
- affected bboxes / regions。
- affected occupancy cells。
- affected devices / nets。
- affected connectivity components。
- affected derived marking families。

当下游请求已失效 view 时，实现只能重算、读取已刷新 cache，或返回 typed stale-view failure；不能静默读取 stale cache。`Device.fin_track_indices`、`Net.segments`、`Net.vias`、routing read views 等只能是 read view / cache / export view，不能被 planner、transaction 或 exporter 当作长期事实源。

### 9.6 Commit log / ChangeSet / provenance

Commit log 应记录：

- target intent。
- planner / macro / candidate identity。
- candidate selection policy，例如 deterministic gap-side shrink、search result 或 human-selected plan。
- constraint result，包括 accepted checks、failed checks、warnings、degraded checks。
- committed geometry / occupancy / annotation / connectivity / current-semantic delta。
- apply atomicity、applied / skipped delta 与 waiver / non-production outcome。
- derived delta。
- invalidated / refreshed read views。
- validation expectations。
- responsible code path / agent / macro。
- parent snapshot id、new snapshot id、commit id、timestamp 或 run id。

ChangeSet 应具备稳定排序和可审计 old/new state。排序规则应与 layer、shape/store id、cell id、device id、net id 等稳定 identity 绑定，避免 report、golden regression 和 debug 因非确定性顺序漂移。

Commit log 中的 `validation expectations` 不是 validation result。它描述本次 commit 期望 Stage 6 / signoff 检查什么，例如 DRC clean、exported/extracted layout ↔ current-semantic CDL、whole-intent current ↔ target closure、SKILL dry-run locate exact shapes、fixture golden optional/required。Stage 6 必须按 RunRecord 的 ordered commit chain 聚合 expectations；实际 validation result 写入独立 artifact，并通过 run / commit ids 关联回来。

这使报告、debug、DRC/LVS feedback 和回归定位可以从 artifact 追溯到具体 intent：target intent → planner / candidate → constraint result → base materialization → annotation / derived finalization → atomic commit publication → exported artifact → validation result。

### 9.7 ChangeSet / CommitEvent / ExportEdit 的定位

v2 不把 legacy L1 `EditOp` / `ShapeEditRecord` 作为核心状态模型。Stage 5 commit 产生 ChangeSet / CommitEvent，用于描述 current-semantic、geometry、occupancy、annotation、connectivity 与 derived delta，并记录 provenance。

三者边界如下：

- **Candidate / ProposedMutationSpec**：Stage 4 / macro 产物，是计划，不是 staged 或 committed state。
- **ChangeSet**：Stage 5 成功 commit 后的事实 delta，记录 old/new state、identity、affected region、derived delta 和 invalidation metadata。
- **CommitEvent**：一次原子发布事件，只以 ids 绑定 `parent_snapshot_id`、`new_snapshot_id`、`change_set_id`、`run_id`、provenance 与 validation expectations；不嵌入 snapshot object，避免递归 ownership。
- **ExportEdit**：Stage 6 从 final immutable snapshot + ordered ChangeSet / CommitEvent chain 派生的 artifact-specific 指令，例如 SKILL command、diff visualization item 或 human report row。

ExportEdit 是 artifact 指令，不是 committed geometry。Stage 6 如需生成 SKILL、diff visualization 或 human report，可以从 ChangeSet 派生 ExportEdit；但下一轮 planner、constraint engine、read-view recompute、transaction derivator 和 exporter 的几何输入仍然是 committed snapshot，而不是 ExportEdit 或 legacy edit stream。

Legacy `EditOp` 不进入 v2 core architecture。若某些导出格式仍需要 edit-like 表达，应从 final committed snapshot 和 ordered ChangeSet chain 重新生成 artifact-specific ExportEdit，而不是保留 `EditOp` 作为状态或 commit 通道。

Derived-shape edit rejection 仍然重要：planner / macro 不应直接覆写 C1 derived shape。对 derived shape 的 artifact edit 也必须能追溯到 CommitEvent 中的 derived delta，而不是来自普通 macro edit。

## 10. Export、生产工具交互与验证

第 10 节定义 Stage 6 的职责边界。Stage 6 的目标是把已经提交并冻结的 layout snapshot 转换为 artifact，并对 artifact 与 snapshot、semantic intent、生产工具结果之间的一致性给出结构化判断。它不是修改阶段，也不是 legacy writeback 阶段。

Stage 6 的输入只能来自：

- immutable committed snapshot。
- ordered ChangeSet / CommitEvent chain / provenance。
- immutable RunRecord / diagnostic provenance；不得读取 live PlanningResult 或 mutable constraint / transaction object。
- export policy。
- validation policy。
- site/tool config。
- 可选 golden target 或 fixture expectation。

Stage 6 不能重新解释 raw target diff，不能读取 mutable transaction overlay，不能把 output artifact 当作 state source，也不能把生产工具输出直接 patch 回 layout state。No-publication failure（本 run 尚无 CommitEnvelope）只允许从 failure RunRecord + optional last-stable-snapshot ref 生成 diagnostic report，不允许 geometry export；已有 earlier envelopes 的 partial-policy terminal failure 仍按第 2.7 节 policy 处理。`run_record_freeze` exception 则直接从 StageFailure + completed neutral audit refs 生成 diagnostic report，同样不得进入正常 Stage 6。Legacy MVP 中符合 v2 边界的 GDS IO、CDL writer、Calibre query parser、可视化 helper 或测试 harness 可以按职责复用；不符合 v2 边界的 edit-stream writeback、output-side patch、placeholder SKILL、stdout-only validation 等路径应重构或删除，不设计兼容 adapter。

### 10.1 Stage 6 no-mutation boundary

Stage 6 是对 Layauto `AuthoritativeState` 的只读边界。它不允许修改 current semantic、geometry、occupancy、annotation、connectivity、derived markings 或 read-view version metadata。这个边界保证纯 artifact generation 可重跑、可比较、可审计；显式启用的外部 SKILL apply 另按 production-integration policy 管理其副作用、幂等与 undo，不改变该内部只读合同。

Stage 6 禁止：

- 修改 AuthoritativeState 的任何 component。
- 在 export 过程中运行或补跑 C1 derived refresh。
- replay legacy MVP edit stream 来生成 canonical geometry。
- 根据 Stage 1 target diff globals 临时修改 output params。
- 根据 output JSON / GDS / SKILL 反向修补 committed state。
- 把 validation mismatch 静默降级为 stdout。
- 把 skipped / deferred / degraded / environment-limited check 当作 pass。

如果 Stage 6 发现 snapshot 缺少 final C1 partition、authoritative AnnotationState 或 shape identity，frozen tech context 缺少 layer-purpose / unit mapping，或 ordered CommitEvent chain 缺少 validation expectations，应在对应 export / validation subphase 产生 typed failure。缺失 / stale 的 non-authoritative summary 应先由 versioned view builder 从 immutable snapshot 纯重算；只有无法确定性重建时才 typed-fail，且不得把结果写回 snapshot。

Legacy MVP 中 `DRCDerivator → WritebackDecoder.apply() → resized_data → GDS/JSON/CDL` 的路径属于要删除的错误边界，不是 v2 的过渡兼容目标。v2 中 C1 derived markings 已在 Stage 5 atomic publication 前 final，并随同一 commit / snapshot 发布；Stage 6 只序列化 snapshot 中已有的 geometry。

### 10.2 GDS / JSON / CDL export

Exporter 应从 immutable snapshot、由 snapshot / RunRecord ids 解析出的 frozen versioned tech context，以及 export policy 生成 artifact：

- **GDS。** Snapshot 提供 geometry store 的 drawn / C1 partitions；frozen tech context 提供 layer-purpose 与 unit / DBU mapping；export policy 提供 deterministic shape ordering。GDS export 不 replay ChangeSet 来“得到”最终几何；ChangeSet 只可用于 provenance、order hint、debug tag 或 diff reference。只有已声明 lossless capability 的 geometry subset 才能声称 round-trip。
- **JSON snapshot。** 输出 machine-readable snapshot / debug representation，包含 current semantic、geometry、occupancy、annotation validity、connectivity、C1 summary、commit / parent ids 和 change summary；optional target summary / ref 只能来自 frozen RunRecord / snapshot context，不冒充 AuthoritativeState component。JSON 是 artifact，不是下一轮 pipeline 的事实源。
- **CDL。** 从 current semantic state snapshot 输出 cell、device、net、pin、params；不得从 Stage 1 raw diff、immutable target object 或 hard-coded instance list 直接拼最终 params。
- **Optional debug / fixture JSON。** 可以为了回归测试保留简化格式，但必须标注为 artifact/debug view，不能成为 v2 parser 主输入。

输出顺序、canonical→artifact unit / DBU serialization、layer-purpose mapping、shape id / bbox serialization 必须可测试。Stage 1 的 source-evidence→schema-canonical unit decode 只发生一次；Stage 6 的反向 serialization 是纯输出变换，不写回任何事实。Byte-golden drift 不是天然错误，但必须能解释：是 shape order policy 改变、unit round-trip 改变、derived marking finalization 改变，还是实际几何语义改变。

Stage 6 artifact 的读取边界如下：

| Artifact | 从 snapshot 读取 | 从 commit sibling records 读取 | 其它 frozen inputs | 禁止事项 |
|----------|------------------|-------------------------------|--------------------|----------|
| GDS | geometry store 的 drawn / C1 partitions | provenance ref、optional deterministic-order hint | frozen tech layer-purpose / DBU mapping、export ordering policy | 不 replay legacy edit stream 修补 geometry |
| JSON snapshot | current semantic、geometry、occupancy、annotation、connectivity、C1 summary、linkage ids | ChangeSet summary、commit refs | RunRecord 中的 optional target ref、schema / export policy | 不重新计算 authoritative state，不把 target 写成 current state |
| CDL | current semantic state | semantic-delta provenance | format / naming policy | 不从 Stage 1 diff globals 或 target reference 硬编码 params |
| SKILL / Virtuoso script（post-MVP） | shape ids、bbox、snapshot geometry、identity anchors | ExportEdit、provenance | frozen tech layer-purpose mapping、tool config、assertion policy | v2 MVP 不依赖它完成 layout 修改；不把 SKILL 当作 state commit |
| Human / machine report | snapshot summary | ordered ChangeSet / CommitEvent chain | RunRecord、ArtifactManifest、ValidationResult、reporting policy | 不读取 live planner / transaction，不只统计 macro edit ops |
| Validation result | snapshot | commit id、validation expectations | ArtifactManifest、RunRecord、ToolRunResult / ParseResult、validation policy | 不只打印 stdout；不吞掉 skipped / deferred / degraded checks |
| Visualization | snapshot geometry / annotation / connectivity | committed delta、provenance | RunRecord、ValidationResult、reporting policy | 不从 pre-commit edit stream 拼图 |

### 10.3 SKILL / Virtuoso interaction

v2 MVP 的主输出路径是 Python-based exporter：从 committed snapshot 直接导出 GDS / JSON / CDL，并通过 self-consistency / fixture validation 检查这些 artifact。只要这条路径能产生可被下游工具读取、可回归、可审计的 layout artifact，SKILL / Virtuoso 交互就不是 v2 MVP 完成版图修改的必要步骤。

SKILL / Virtuoso 的定位应降级为 **post-MVP production integration / mirror-to-editor artifact**：当生产流程要求把 Layauto 已经 commit 的修改真实反映到 Virtuoso layout editor 中，或需要在 Virtuoso database 中保留可审计的人工复现脚本时，再从 final snapshot + ordered ChangeSet chain / ExportEdit 生成 SKILL。它的目的不是替代 Python exporter，也不是成为权威 commit 机制，而是把同一份已提交状态投射到 Virtuoso 环境。

因此 v2 MVP 对 SKILL 的要求是保留清晰边界，而不是实现完整生产脚本：

- Python exporter 生成的 GDS / JSON / CDL 是 MVP 的 primary artifact。
- SKILL emitter 可以暂不实现；若 v2 MVP contract 声明该 post-MVP check，则 validation policy 应把 SKILL dry-run 标记为 deferred；只有 policy disabled / not-applicable 才是 skipped。
- 如果后续实现 SKILL emitter，它必须只读 final snapshot + ordered ChangeSet chain / ExportEdit，并包含 lib/cell/view、layer-purpose mapping、Virtuoso shape-match tolerance、shape locate assertion、provenance comment、ambiguity / missing-shape failure、tool stdout/stderr / return code 等结构化记录。
- 占位式 `printf` helper 不能作为生产成功；也不需要为了保留 legacy `EditOp` list 而设计适配层。实现时应先形成符合 v2 的 ChangeSet / ExportEdit，再由 SKILL emitter 处理。

这里的 deferred 只表示 v2 core-state MVP 不被真实 Virtuoso 环境阻塞。当且仅当 run policy 启用 Virtuoso/SKILL integration 时，SKILL dry-run、shape locate、ambiguity check 和 tool return code 才是该 integration profile 的结构化 gate；placeholder、dummy、missing tool 或 skipped/deferred check 不能被计为该 profile 的 production pass。其它 production profile 不因未启用 Virtuoso mirror 而自动失败。

SKILL dry-run 通过并不等价于 layout state commit 成功。commit 已在 Stage 5 完成；SKILL dry-run / apply 的结果属于 Stage 6 validation result 或 production integration result。

### 10.4 Calibre DRC / LVS closure

Calibre DRC / LVS closure 是后续生产闭环能力，不是 v2 MVP 的必需完成项。v2 MVP 可以先只定义接入边界，并把真实 Calibre run、生产环境脚本、结果解析、violation localization、failure policy 等实现 defer 到 post-MVP。原因是这些工作依赖 PDK / rule deck / license / SVDB / tool command / report format，工程细节多，且不应阻塞核心 state / planner / transaction / exporter 架构收敛。

仍需区分两类 Calibre 消费：

1. **Stage 1 evidence acquisition。** `ixref`、`net_xref`、`device_info`、`net_shapes` 等 query bundle 用于构建 annotation overlay 和 layout state；这类 evidence 边界仍属于 v2 state construction 的输入约束。
2. **Stage 6 signoff validation（post-MVP）。** DRC / LVS run 先验证 exported / extracted layout 与 exported current-semantic CDL，再对默认 whole-intent run 验证 current semantic 与 immutable target closure，并同时检查 rule deck / tool environment；v2 MVP 可将其记录为 deferred check。

post-MVP 的 Calibre closure 应满足：

- DRC clean 是生产 fatal gate；但 v2 MVP 中已声明而暂缺生产 Calibre 环境的 post-MVP check 应标记为 deferred，只有 policy disabled / not-applicable 才是 skipped；两者都不能假装 pass。
- LVS 必须先比较 exported / extracted layout 与 exported current-semantic CDL snapshot；默认 `whole_intent` run 还必须证明 current semantic 等于 immutable target CDL / TargetIntent。Partial / waived run 的 target mismatch 必须显式报告为 non-production / requires-review，不能 clean-pass。内部 net renumber、S/D swap、layout instance rename 必须通过 Stage 2 annotation identity 解释，而不是在 Stage 6 临时猜测。
- DRC/LVS violation 应定位到 schematic net / device / connected component / candidate / commit provenance；无法定位时要给出 typed localization gap。
- Tool command failure、format drift、missing binary、timeout、license failure、SVDB missing、rule deck missing、layer map mismatch 都应成为结构化 validation result。
- Calibre output 不得直接 patch layout state；它只能产生 validation result、diagnostic artifact，或作为下一轮修复 intent 的 evidence 输入。

同样，deferred 只表示 v2 core MVP 可以先没有真实 Calibre 环境；一旦 run policy 声明启用 Calibre closure profile，DRC clean、LVS match、query-result parse 和 violation localization 就是该 profile 的结构化 fatal gate。dummy Calibre、缺失 license、缺失 rule deck 或 skipped/deferred signoff 不能作为该 profile 的 production pass。

第 10 节只定义边界。生产级 runner / dialect 位于 `tooling/`，格式 parser 分别位于 `importers/` / `validation/`，localization helper 位于 `validation/`；当前 v2 MVP 不需要实现完整 Calibre DRC / LVS closure。

### 10.5 Validation model

Validation 分层：

1. **Golden regression。** 用于 fixture / CI。检查输出是否与预期 golden 一致。适合 synthetic fixture，不应被当作生产 ECO 的唯一正确性标准。
2. **Self-consistency。** 检查 artifact 与 final snapshot / ordered ChangeSet chain / current semantic state / layer map / units / C1 markings 一致。
3. **Signoff validation。** 运行 DRC / LVS / SKILL dry-run / optional Virtuoso shape locate 等生产检查；v2 MVP 已声明但暂缓实现的检查标记为 deferred，policy disabled / not-applicable 才标记 skipped。
4. **Audit-readiness validation。** 在生成 report 前检查 frozen RunRecord、provenance、policy disclosure 与 localized references 是否足以解释修改；report / visualization artifact 本身由后续 reporting subphase 生成，避免 validation ↔ reporting 循环。

Self-consistency 至少应检查：

- 在声明的 geometry capability 内，GDS round-trip geometry 与 snapshot geometry 一致；bbox-only run 只有通过 flat-rectilinear capability check 才能声称 round-trip。
- JSON export 与 snapshot content 一致。
- CDL export 与 current-semantic state snapshot 一致。
- 对已生成的 SKILL / ExportEdit，self-consistency 只做静态 reference / bbox / layer-purpose / provenance 一致性检查；真实 Virtuoso dry-run / shape locate 仅归入 signoff/tool validation。已在 v2 contract 声明但 capability 暂缓实现时记为 deferred；run policy disabled / not-applicable 时记为 skipped。
- Frozen reporting input 中的 change counts、affected regions、target intent、candidate id、constraint result 与 ChangeSet 一致。
- C1 derived markings 已经包含在 snapshot 中，而不是 Stage 6 临时生成。
- FIN static backdrop、OD active coverage、routing/via/cut repair、connectivity component 等与 commit validation expectations 一致。
- Annotation coverage、unannotated blockage、suspect geometry、coverage gap 与 validation policy 一致。

只有 required core artifacts 已在 `ArtifactManifest` 中原子发布的 committed run 才产生 commit-linked `ValidationResult`。除 `run_record_freeze` exception 外，Stage 1–5 failure 使用包含 typed StageFailure 的 failure RunRecord：no-publication failure 的 snapshot / commit refs 可缺省，partial-policy terminal failure 只引用 earlier published commit ids / final stable snapshot，任何路径都不得为 failed delta 伪造 commit id。`run_record_freeze` 不产生 ValidationResult。`ValidationResult` 至少包含：

- `commit_id` / `snapshot_id`。
- core artifact paths 与 content hash；report / visualization manifest 属于后续 `ReportingResult`。
- check name、check type、severity、status。
- `status = pass | fail | skipped | deferred | degraded`。
- `severity / policy_outcome = info | warning | requires_review | fatal`；warning 不是 status。
- skipped / deferred / degraded 原因，例如 missing tool、missing license、fixture scope、rule unsupported、policy disabled。
- tool command、return code、stdout/stderr path、runtime、timeout、environment summary。
- localized object references，例如 device id、net id、component id、shape id、candidate id、rule id、bbox。
- failure policy outcome，例如 fatal、non-fatal warning、requires human review。

没有 golden target 的生产 ECO 仍然可以通过 self-consistency + signoff + audit-readiness 给出 pass/fail。v2 MVP 可以先以 self-consistency + fixture checks 作为完成标准，并在 validation result 中明确 SKILL / Calibre signoff 为 deferred。相反，有 golden target 的 fixture 如果 signoff 或 self-consistency 失败，也不能只因为 golden match 而 pass。

### 10.6 Reports、visualization 与 debug artifacts

Report 是审计 artifact，不是 state source。成功 report 应从 final immutable snapshot、ordered ChangeSet / CommitEvent chain、RunRecord、validation result 和 policy disclosure 生成；planning / constraint 信息只能读取 RunRecord 中冻结的 neutral audit records，不能读取 live object。No-publication failure report 从 failure RunRecord 与 optional pre-run stable-snapshot reference 生成，不输出 committed-change artifact；partial-policy terminal-failure report 还必须列出 earlier committed chain 与 failed / skipped deltas，不能把二者混写。`run_record_freeze` exception 的 diagnostic report 直接读取 StageFailure、completed neutral audit refs 与 optional earlier commit chain，并显式披露 RunRecord 缺失。

Report 应覆盖：

- 输入 evidence 摘要：CDL、GDS/bbox、Calibre query bundle、site config、tool mode。
- target intent：所有 delta、supported / unsupported 判断、atomic / partial policy。
- candidate 选择：候选内容、受影响区域、repair requirement、provenance seed。
- constraint result：规则、传播、失败原因、rollback 或 commit outcome。
- committed changes：base changes、current-semantic、occupancy、annotation、connectivity changes。
- derived changes：C1 markings、read-view invalidation / refresh summary。
- annotation coverage：coverage gap、unannotated blockage、suspect geometry。
- validation results：self-consistency、golden、signoff、audit-readiness checks；v2 MVP 中的 post-MVP / deferred 与 policy-disabled / skipped checks 必须清楚列出。
- skipped / deferred / degraded checks 与 warning severity：原因、风险、policy outcome。
- artifact manifest：路径、hash、生成时间、tool command summary。

Report 不应只统计 macro edit ops。对于不符合 v2 的 legacy `EditOp` 报告路径，应重构为基于 ChangeSet / CommitEvent 的报告生成；不保留以 edit-op count 为主体的适配输出。

Visualization 应从 committed delta、snapshot geometry、annotation overlay、connectivity component 和 validation mismatch 生成。它可以展示 before / after / target / LVS-derived overlay / DRC marker，但不得从 pre-commit edit stream 拼最终图。若 visualization 依赖可选库或 GUI 环境，缺失时应进入 `ReportingResult` / report 的 degraded record，而不是改写 core `ValidationResult` 或影响 core artifact correctness；要求 visualization 的 deployment policy 仍可据此使 pipeline outcome 失败。

## 11. v2 模块组织

第 11 节把前文的事实源、状态所有权、planning、constraint、transaction、export / validation 边界落到建议代码组织上。这里的目录结构不是唯一正确答案；真正不可违反的是依赖方向、状态所有权和阶段边界。

v2 模块组织必须服务于以下目标：

- Semantic domain 不依赖 importer、constraint engine、pipeline 或 exporter。
- Coordinate system 是坐标数学，不拥有 occupancy。
- Authoritative layout state 只由 `state/` 拥有；publication 只有两种 transaction protocol：Stage 2 baseline-only `InitializationTransaction` 与 Stage 5 ECO transaction。二者都不是第二个 state owner，normalization / pipeline 不得直接写 state。
- Annotation 只把 evidence 解释成 identity / coverage / conflict 信息，不直接执行 ECO。
- Planning 只生成 candidate / proposed mutation spec，不直接写 committed state。
- Constraints 只检查 transaction-private staged view，不持有 canonical occupancy / connectivity，也不依赖 transaction 实现类型。
- Stage 5 transaction 是 candidate 变成 committed snapshot 的唯一门；InitializationTransaction 只能从 evidence 建 baseline，不能应用 target intent。
- Derive 在 InitializationTransaction 或 Stage 5 transaction 的 private tentative state 上完成 C1 finalization，并从 frozen state 产生 read-only views；它不拥有 commit 生命周期。
- Export / validation / reporting 只读 final immutable snapshot、ordered ChangeSet / CommitEvent chain 与 RunRecord，不补写内部状态。
- Tech facts、evidence schema、artifact contract 与 tool-run result 必须有中立 owner，不能挂在 importer、exporter 或 validation 一侧形成反向依赖。
- Legacy MVP 代码不进入 `layauto_v2/` runtime package；可取用的纯逻辑应迁入对应 v2 职责并由 v2 tests 覆盖。

### 11.1 建议 package layout

```text
layauto_v2/
├── domain/
│   ├── geometry.py
│   ├── circuit.py
│   ├── intent.py
│   ├── identifiers.py
│   ├── evidence.py
│   ├── artifacts.py
│   ├── results.py
│   └── policy.py
├── tech/
│   ├── bundle.py
│   ├── layers.py
│   ├── rules.py
│   └── calibre_layers.py
├── state/
│   ├── semantic.py
│   ├── coordinate.py
│   ├── layout_store.py
│   ├── occupancy.py
│   ├── annotation.py
│   ├── connectivity.py
│   ├── mutation.py
│   └── snapshot.py
├── normalization/
│   └── builder.py
├── annotation/
│   ├── layer_overlay.py
│   └── coverage.py
├── planning/
│   ├── candidate.py
│   ├── resize.py
│   ├── routing.py
│   ├── repair.py
│   └── unsupported.py
├── constraints/
│   ├── engine.py
│   ├── rules.py
│   ├── drc_context.py
│   └── result.py
├── transactions/
│   ├── initialization.py
│   ├── transaction.py
│   ├── change_set.py
│   ├── commit_log.py
│   └── provenance.py
├── derive/
│   ├── markings.py
│   ├── views.py
│   └── invalidation.py
├── tooling/
│   ├── runner.py
│   ├── calibre.py
│   └── virtuoso.py
├── importers/
│   ├── gds.py
│   ├── cdl.py
│   ├── calibre.py
│   └── config.py
├── export/
│   ├── gds.py
│   ├── cdl.py
│   ├── json.py
│   └── skill.py
├── validation/
│   ├── self_consistency.py
│   ├── signoff.py
│   ├── golden.py
│   ├── policy.py
│   └── result.py
├── reporting/
│   ├── reports.py
│   └── visualization.py
└── pipeline.py
```

`tech/` 是 layer / rule / Calibre-layer registry 的中立 owner；`normalization/` 把 Stage 1 evidence 构建为初始 `AuthoritativeState`；`tooling/` 统一外部命令与 dialect；`reporting/` 在 export / validation 完成后生成审计输出。`domain/evidence.py`、`domain/artifacts.py` 与 `domain/results.py` 分别提供 importer→normalization、export→validation 与 tooling/importer/pipeline 共享的中立合同，避免任一消费模块反向依赖另一侧。

v2 fixture / test helper 放在 package 外的 `tests/fixtures/` 或 `tests/support/`，不得作为 runtime dependency。仓库级 `legacy_mvp/` 仍可保留为历史实现，但 `layauto_v2/` 不提供 legacy adapter；需要取用的 parser、unit conversion 或几何纯函数应迁入上述明确 owner，而不是从 legacy package import。

### 11.2 `domain/`

**职责。**
`domain/` 定义稳定、IO-independent 的领域对象，包括 geometry primitive、circuit IR、target intent、stable identifier、policy enum，以及跨模块使用的 evidence / artifact contract。它表达“对象是什么”和“intent 是什么”，不表达“对象从哪个文件来”或“如何提交修改”。

**可以依赖。**

- Python 标准库和纯 dataclass / typing。
- 不含 IO side effect 的基础几何工具。

**禁止。**

- 不依赖 GDS writer、Calibre runner、constraint engine、pipeline、exporter。
- 不保存可从 layout store / occupancy / annotation 推导的长期几何副本。
- 不把 legacy fixture 中的 instance name、net name 或 cell-specific geometry 写死为领域模型。

**关键对象示例。**

- `DeviceIR`、`NetIR`、`CircuitIR`。
- `ResizeIntent`、`RoutingIntent`、`UnsupportedIntent`。
- `ShapeId`、`CellId`、`ComponentId`、`CommitId`。
- `EvidenceRecord`、`ArtifactManifest`、`ExportPolicy`、`RunRecord`、`CommitAuditRecord`、`PlanningAuditRecord`、`ConstraintAuditRecord`、`ToolRunResult`、`ParseResult`、`StageFailure`、`ReportingResult`、`PipelineResult` 等中立合同。
- `EditPolicy`、`ValidationSeverity` 等稳定枚举。

### 11.3 `state/`

**职责。**
`state/` 独占 v2 `AuthoritativeState` 的所有权与坐标系统定义。该 aggregate 应清楚区分：

- `semantic.py`：current semantic state；target intent 仍是 transaction 外的 immutable input。
- `coordinate.py`：layer grid、track axis、B-tier axis、physical↔track 转换、bbox→cell projection 等坐标数学。
- `layout_store.py`：单一 geometry table，以 `partition = drawn | c1_derived` 区分权威 partitions，并以 `origin = source_evidence | transaction | derivator` 记录 provenance source；保存 shape id、bbox、layer / purpose、derivation policy 与 provenance。Stage 5 新建或替换的 OD / routing shape 属于 `partition = drawn, origin = transaction`；input C1 可属于 `partition = c1_derived, origin = source_evidence`，但只有在 `validate_and_adopt` 成功后才可进入 baseline。Shape annotation 只能是由 cell-level annotation 归纳的 read summary。
- `occupancy.py`：A-tier / B-tier discrete occupancy、blockage、via、cut、OD sharing / split 等可检查工作基底。
- `annotation.py`：CellId-keyed annotation、coverage / conflict，以及以 canonical semantic id 为 key 的 ixref / net-xref / `DeviceAnnotationSeed` indices 与 evidence provenance。
- `connectivity.py`：component membership、same-layer edge、via edge、cut barrier 与 diffusion sharing / split topology；component-to-net / annotation summary 位于 `derive/views.py`。
- `mutation.py`：可被 transaction staged / applied / rolled back 的 state mutation primitive，以及不暴露 transaction 实现的 `StagedStateView`、`AffectedScope`、trail / checkpoint protocol。
- `snapshot.py`：immutable committed snapshot，只保存 state content 与 domain-defined linkage ids，不依赖或嵌入 ChangeSet / CommitEvent。

**可以依赖。**

- `domain/` 的 identifier、geometry primitive、semantic id。
- Tech bundle 中的 layer / coordinate / rule metadata，但不直接读取文件。

**禁止。**

- `coordinate.py` 不能持有 occupancy；grid 只做坐标数学。
- semantic、single layout store（drawn / C1-derived partitions）、occupancy、annotation、connectivity 与 metadata 必须由同一 `AuthoritativeState` 版本化；各 components 之间不能形成互相漂移的权威副本。
- `Device.fin_track_indices`、`Net.segments`、`Net.vias`、gate tracks 等不能作为 state truth 长期存储；它们属于 `derive/views.py` 或 state-backed view。
- 不依赖 parser、Calibre query runner、decoder、exporter 或 pipeline。
- 不把 constraint engine cells 当作 occupancy truth。

**legacy 迁移注意。**
Legacy MVP 中 `MultiLayerGrid.b_tier_cells`、`Net.segments`、`Net.vias`、`Device.fin_track_indices`、`ConstraintEngine.cells` 都不能原样成为 v2 authoritative state。可复用的是坐标转换、bbox→cell projection、稳定排序、局部 connectivity 算法等纯逻辑；状态所有权必须迁移到 `state/`。

### 11.4 `annotation/`

**职责。**
`annotation/` 有两个显式模式：Stage 2 evidence overlay 消费 Stage 1 Calibre / LVS bundle，执行 layer mapping、identity translation、per-cell overlay 与 coverage / conflict 分析；Stage 5 proposed-state reconciliation 则消费 current AnnotationState、neutral `StagedStateView` / `StateDelta` / `AffectedScope` 和 current semantic ids，为变化 cells 生成 candidate-derived attribution 或 conservative invalidation，不重新读取 raw evidence。两种模式都只生成 proposed `AnnotationState` / delta，不拥有或直接修改 authoritative state；只有 InitializationTransaction 或 Stage 5 transaction 可通过 `state/` mutation API 安装结果，normalization builder 不直接 publish。

**可以依赖。**

- `domain/` 的 identifier。
- `state/coordinate.py` 的 projection math；tolerance / ambiguity policy 来自 `tech/` 与 run annotation policy。
- `state/` 的只读 geometry / occupancy / current-annotation / current-semantic view、proposed annotation schema，以及 `state/mutation.py` 的 neutral StagedStateView / StateDelta / AffectedScope protocols。
- `domain/evidence.py` 的 schema-canonical evidence record。
- `tech/` 的 layer registry 与 annotation policy。

**禁止。**

- 不把 `device_info` / `net_shapes` 当作完整几何事实替代 GDS。
- 不直接执行 resize、routing repair、cut insertion 或任何 ECO 修改。
- 不在 Stage 6 临时解释 LVS identity 来修补 exporter 输出。
- 不把 legacy `calibre_device_query.json` / `calibre_net_query.json` 作为 v2 主输入模型。

**关键输出。**

- Per-cell `device_ref` / `net_ref` / `pin_role` / `annotated_mask_color`、validity / conflict、coverage 与 evidence provenance。
- Proposed AnnotationState / delta，包括 candidate-derived attribution、invalidation 与 `unverified_after_edit` markers。
- Shape-level annotation summary；当 cell 不一致时 summary 应保持 unknown / ambiguous。
- Coverage report：annotated、unannotated blockage、suspect、conflict。
- Identity translation：layout instance → schematic instance，LVS net → schematic net / stable LVS index。

### 11.5 `planning/`

**职责。**
`planning/` 从 typed intent 与 current snapshot / state view 生成 candidate。Resize、routing-dependent macro、repair、unsupported intent failure 都在这里表达。

**可以依赖。**

- `domain/` intent / circuit IR。
- `state/` snapshot、coordinate、occupancy / connectivity query。
- `derive/views.py` 提供的只读 view，例如 segments、via coverage、fin attribution。
- `constraints/` 的 query interface 类型，但不直接驱动 commit。

**禁止。**

- 不直接修改 committed layout store、occupancy、connectivity 或 semantic IR。
- 不调用 exporter / decoder 来得到最终几何。
- 不把 raw CDL diff、raw ECO command 或 raw signoff log 作为长期输入；这些必须先在 Stage 2 归一化为 typed intent。
- 不静默跳过 unsupported delta；必须返回 typed unsupported result 或 raise typed error。

**关键对象示例。**

- `CandidatePlan`。
- `ResizeCandidate`。
- `RoutingCandidate`。
- `RepairRequirement`。
- `UnsupportedDeltaError`。
- `PlanningResult`，包含 `base_snapshot_id`、preconditions、`apply_atomicity` 与 `ProposedMutationSpec`。

### 11.6 `constraints/`

**职责。**
`constraints/` 消费 immutable `tech.rules.RuleRecord`，负责编译 rule predicates、建立 DRC evaluation context、domain / trail / propagation overlay 并产生 feasibility result；它不拥有 rule facts。

**可以依赖。**

- `domain/` id / policy。
- `state/coordinate.py`、`state/occupancy.py`、`state/connectivity.py` 的只读 query。
- `state/mutation.py` 提供的 `StagedStateView`、affected-scope 与 trail / checkpoint protocol。
- Tech rule records。

**禁止。**

- 不拥有长期 layout state。
- 不维护另一份可与 `state/occupancy.py` 漂移的 occupancy copy。
- 不把 per-cell scalar `net_id` domain 作为 same-conductor truth。
- 不把 CUT / VIA / DEVICE_DIFF 等 layer-implied occupant 强行展开成 `occ_type × net_id` 的大型 domain。
- 不把 unknown / unannotated geometry 当作 compatible-with-everything。
- 不 import `transactions/`；constraint API 接收中立 staged-view protocol，避免 `constraints/` ↔ `transactions/` 循环依赖。

**same-conductor 规则。**
Spacing / enclosure / cut / via / OD sharing 等 rule predicate 默认通过 `state/connectivity.py` 判断 connected component；semantic net label 只作为 reporting、LVS localization 或显式 policy exception 的输入。

### 11.7 `transactions/`

**职责。**
`transactions/transaction.py` 是 candidate 变成 committed state 的唯一 ECO 门。它负责 checkpoint、transaction-private base materialization、constraint check orchestration、annotation / derived finalization、commit、rollback、ChangeSet、CommitEvent、provenance 与 `CommitEnvelope` publication。只有整个 `apply_atomicity` scope 完成 finalization 且 per-commit audit record 可冻结后，才能原子发布新 state version、snapshot 与 sibling commit records；run-level RunRecord 在全部 Stage 5 plan groups 结束后由 orchestrator 冻结，默认 whole-intent 必须与唯一 CommitEnvelope 同批原子发布。

`transactions/initialization.py` 拥有 baseline-only `InitializationTransaction` publication protocol：它接收 `normalization/builder.py` 的 proposed initial state，复用 state mutation、annotation、connectivity 与 derive contracts，输出 baseline snapshot / `InitializationEvent`，但不应用 TargetIntent、不产生 ECO ChangeSet / CommitEvent。Normalization builder 与 pipeline 只能调用该 protocol，不能直接 publish state。

**可以依赖。**

- `domain/` id / intent / semantic delta。
- `state/` mutation API、snapshot API。
- `constraints/` feasibility API。
- `annotation/` 的 proposed-state refresh / invalidation API。
- `derive/markings.py` 的 pre-publication finalization API。
- `derive/invalidation.py` 的 view invalidation API。

**禁止。**

- 不允许 planner / macro 绕过 transaction 直接写 committed state。
- 不允许 constraint engine 的 checkpoint 代表完整 transaction rollback。
- 不允许 Stage 6 exporter 作为 canonical updater。
- 不把 legacy L1 `EditOp` 作为 commit channel 或 authoritative geometry。
- base materialization、mandatory constraint、annotation refresh、C1 finalization 任一步失败都必须回滚，不得留下 geometry、occupancy、connectivity、semantic、annotation、derived 或 cache partial state。

**关键输出。**

- `ChangeSet`：current-semantic、geometry、occupancy、annotation、connectivity、derived delta 与 invalidation metadata。
- `CommitEvent`：parent / new snapshot ids、plan-group / candidate ids、constraint audit refs、provenance、validation expectations。
- Immutable snapshot：供 Stage 4 planning、下一轮 Stage 5 transaction 与 Stage 6 只读消费。
- `CommitEnvelope`：per-publication 原子 unit，包含 state/snapshot 与 ChangeSet / CommitEvent / CommitAuditRecord sibling records；state 只通过 ids 引用后者。

### 11.8 `derive/`

**职责。**
`derive/` 负责三类派生结果：

1. `markings.py`：进入 exported layout 的 C1 derived geometry，例如 NWELL、BOUNDARY、VT、PP、NP、DNW 等。
2. `views.py`：不作为独立物理层输出的 read-only views，例如 routing spans、vias、fin attribution、gate tracks、annotation coverage、component summaries。
3. `invalidation.py`：根据 `state/mutation.py` 的 neutral `StateDelta` / `AffectedScope` 管理 affected region、cache invalidation 与 lazy recompute；transaction 可把同一 neutral delta 编入 ChangeSet，但 derive 不读取 ChangeSet 类型。

**可以依赖。**

- Transaction-private tentative state 或 immutable committed snapshot 的只读 view；不依赖 transaction / ChangeSet 实现类型。
- Tech rules / layer policies。
- Annotation summary 与 connectivity query。

**禁止。**

- 不在 Stage 4 planning 中持久写 state。
- 不在 Stage 6 export 中临时补跑来修复缺失 state。
- 不让 derived view 变成 planner / constraints / exporter 的长期 truth。
- 不允许 macro 直接覆写 C1 derived shape。

**FIN / POLY 语义。**
FIN static backdrop、OD active coverage、gate / fin attribution 等应通过 committed geometry + occupancy + annotation 派生。`nfin` resize 不应被表达为 FIN edit；FIN edit policy 应在 planner / constraint / transaction 边界被拒绝。

### 11.9 `importers/`

**职责。**
`importers/` 负责文件格式适配：GDS / lossless geometry 或 capability-scoped bbox readback、CDL parse、Calibre query output parse、config load。它输出 raw capture 或 schema-canonical evidence record，不构建 authoritative layout state；命令执行、dialect、timeout / license 分类由 `tooling/` 负责。

**可以依赖。**

- `domain/` 的基础数据类型。
- 纯格式 schema / tech config schema。
- `domain/evidence.py`、`domain/results.py` 的 ToolRunResult / ParseResult contracts 与 `tech/` schema；pipeline 把 raw-output refs 交给 importer，importer 不调用或 import `tooling/`。

**禁止。**

- 不执行 ECO 修改。
- 不生成 `Net.segments`、`ViaInstance`、`Device.fin_track_indices` 等工作状态。
- 不把 legacy `calibre_device_query.json` / `calibre_net_query.json` 作为 v2 主路径。
- 不在 importer 中做 annotation overlay；overlay 属于 `annotation/`。
- 不在 importer 中建立 constraint engine 或 transaction。

**legacy 迁移注意。**
历史 parser 中可取用 CDL tokenization、bbox parsing、Calibre query YAML parsing、unit conversion 和 schema validation；但“读 convenience net JSON → 建 segments / vias”的路径不进入 v2。若需要转换旧测试数据，只能使用 runtime 外的一次性 test-data conversion，并将结果固化为 v2 evidence fixture。

### 11.10 `export/`

**职责。**
`export/` 从 final immutable snapshot、ordered ChangeSet / CommitEvent chain、RunRecord、frozen tech context、export policy 和 site/tool config 生成物理 / 语义 artifacts：GDS、CDL、JSON snapshot、SKILL / Virtuoso script。Required artifacts 先写 staging，全部通过 hash / schema check 后才原子发布 immutable `ArtifactManifest`；失败返回 `StageFailure(stage=6, subphase=export)`，partial files 只作为 diagnostics。Human / machine-readable report 与 visualization 由只读 `reporting/` 在 validation result 可用后生成。

**可以依赖。**

- `domain/` id / semantic IR。
- Immutable `state/snapshot.py`。
- `transactions/change_set.py` 与 provenance。
- `domain/artifacts.py` 的 artifact manifest / export policy schema。
- `domain/results.py` 的 RunRecord / StageFailure contracts。
- Layer-purpose mapping、unit / DBU policy。

**禁止。**

- 不修改 `AuthoritativeState` 的任何 component，包括 layout、occupancy、annotation、connectivity、current semantic、C1 derived markings 或 read-view version / cache metadata。
- 不 replay legacy `EditOp` stream 来生成 canonical geometry。
- 不根据 raw target diff globals 临时改 output params。
- 不运行 C1 derivator 来补齐 snapshot。
- 不把 SKILL apply / dry-run 当作 Stage 5 commit。
- 不把 partial / staging file 列入 success ArtifactManifest，也不在 required core export 失败后运行正常 validation。
- 不把 report 或 visualization 当作 state source。

**ExportEdit 定位。**
如果 SKILL、report 或 visualization 需要 edit-like 指令，应从 final snapshot + ordered ChangeSet / CommitEvent chain 派生 artifact-specific `ExportEdit`。`ExportEdit` 是导出指令，不是 committed geometry，也不是下一轮 pipeline 的输入事实源。

**`reporting/` 边界。**
`reporting/` 有两个 typed 入口：success reporting 读取 frozen RunRecord、final snapshot / ordered commit-chain refs、ArtifactManifest、ValidationResult 与 policy disclosure；failure reporting 读取任一 frozen RunRecord（pre-commit 的 failure variant，或 Stage 6 failure 已存在的 success variant）+ StageFailure，stable-snapshot / earlier-commit-chain / manifest / validation refs 均可选。若失败本身是 `run_record_freeze`，则 reporting 可直接读取该 StageFailure 与已完成的 neutral audit refs，而不虚构 RunRecord。两类入口都生成 human / machine-readable report、optional visualization 和 `ReportingResult`。它可以依赖 validation 的 immutable result schema，但 `export/` 与 `validation/` 不 import `reporting/`，`reporting/` 也不得调用 mutable state / transaction / tool runner API。

### 11.11 `validation/`

**职责。**
`validation/` 负责 self-consistency、golden regression、signoff integration、SKILL dry-run / Virtuoso shape locate、validation policy、structured validation result 和 failure policy。v2 MVP 可以只实现 self-consistency 与 fixture golden；已声明但 post-MVP 的生产 signoff 记录为 deferred，policy disabled / not-applicable 才记录为 skipped。

**可以依赖。**

- Immutable snapshot。
- Artifact manifest。
- ChangeSet / CommitEvent。
- `domain/results.py` 的 immutable RunRecord / provenance、ToolRunResult、ParseResult / FindingRecord。
- Export policy / validation policy。
- `domain/artifacts.py` 的 artifact manifest。

**禁止。**

- 不 patch layout state。
- 不把 Calibre / Virtuoso output 直接写回 committed snapshot。
- 不把 missing tool、missing license、timeout、skipped check 当作 pass。
- 不只打印 stdout；必须产生 machine-readable validation result。
- 不用 golden target 取代 self-consistency / signoff / audit-readiness validation。

**关键输出。**

- `ValidationResult`。
- Check status：pass / fail / skipped / deferred / degraded。
- Status 语义：`skipped` = policy disabled / not applicable；`deferred` = contract 已声明但因 post-MVP / 当前 capability 暂缓且未运行；`degraded` = 检查实际运行但 coverage / quality 降级。Required integration profile 下的 missing tool / license / timeout 是 fail，不得用这些 status clean-pass。
- Severity / policy outcome：info / warning / requires_review / fatal。
- Artifact path / hash。
- Localized object reference：device、net、component、shape、bbox、candidate、commit、rule。
- Skipped / deferred / degraded reason。

### 11.12 `pipeline.py`

**职责。**
`pipeline.py` 负责串联 Stage 1–6，并把每个阶段的输入输出显式化。它是 orchestration layer，不是业务逻辑模块。

**可以依赖。**

- `tooling/`、`importers/`、`normalization/`、planning、constraint service initialization、transactions、export、validation、reporting 的 public facade。
- Run-level config / policy。

**禁止。**

- 不承载 resize / routing macro 细节。
- 不承载 DRC rule predicate。
- 不承载 exporter 细节。
- 不在 pipeline 中直接 patch geometry 或 output JSON。
- 可以把 annotation / constraints / derive service 注入 normalization / transactions，但不直接调用 mutable state API、constraint commit 或 C1 finalizer。
- 不吞掉 unsupported intent、constraint failure、transaction rollback、export failure 或 validation failure。

**Stage boundary 要求。**
`pipeline.py` 应显式记录每个 stage 的输入、输出和 failure result。Stage 1–5 的获取、归一化、planning、constraint 或 transaction 失败返回 `StageFailure` 并冻结 failure `RunRecord`；唯一例外是 `run_record_freeze` 本身失败，此时只保留 StageFailure + completed neutral audit refs + optional earlier CommitEnvelope ids，并阻止正常 Stage 6。Stage 6 export failure 返回 linked `StageFailure` 但不修改已冻结 success RunRecord。`ValidationResult` 只表示 checks，`ReportingResult` 只表示 report / visualization outcome，最终 immutable `PipelineResult` 汇总各 references 与 deployment-policy outcome。Stage 5 成功后才能发布 snapshot；Stage 6 只能读取 frozen RunRecord 与其 snapshot / commit references，core artifact references 另由 `ArtifactManifest` 传递。任何 stage 降级或跳过都必须进入相应 run / validation / reporting / pipeline record；不得通过 legacy adapter 改变主路径语义。

### 11.13 `legacy_mvp/` 与代码取用原则

仓库级 `legacy_mvp/` 是历史实现，不是 v2 package、runtime dependency 或迁移适配层。只有满足以下条件的现有逻辑才可取用并迁入 v2 owner：

- 复用的是纯函数、格式 parser、unit conversion、排序、bbox transform、测试 fixture generator 或外部工具薄封装。
- 复用后放入 v2 职责边界内，并有 parity / regression tests。
- 复用不会保留错误状态所有权，例如 grid 持有 occupancy、constraint engine 持有 canonical cells、decoder 作为 canonical updater、Stage 6 replay edit stream。
- 复用不会把 legacy fixture JSON 作为 v2 主事实入口。
- 复用不会让 legacy `EditOp` 成为 v2 commit channel。
- 复用不会为了兼容 legacy MVP 而引入长期 adapter 层。

应明确拒绝的 legacy 结构包括：

- FIN add/remove 作为 `nfin` resize 的物理修改语义。
- `calibre_device_query.json` / `calibre_net_query.json` 作为主 parser 输入。
- `Net.segments` / `Net.vias` / `Device.fin_track_indices` 作为 stored geometry truth。
- `MultiLayerGrid.b_tier_cells` 作为 occupancy owner。
- VIA0 同时表现为 via object、B-tier occupancy、LI/M1 wire stamp。
- `ConstraintEngine.cells` 作为 authoritative occupancy。
- Per-cell `net_id` domain 作为 same-conductor rule truth。
- `WritebackDecoder.apply()` 作为最终几何生成的 canonical path。
- Placeholder SKILL / stdout-only validation 被算作 production success。

### 11.14 模块依赖方向与边界测试

v2 应为模块边界建立轻量 architecture tests，避免实现过程中重新长出 legacy 状态流。

建议检查：

- `domain/` 不 import `importers/`、`constraints/`、`transactions/`、`export/`、`validation/`、`pipeline.py`。
- `tech/` 不 import `state/`、`annotation/`、`constraints/` 或 `pipeline.py`；它只拥有 immutable tech facts / schema。
- `state/coordinate.py` 不持有 occupancy storage。
- `state/` 不 import `transactions/`，snapshot / state metadata 只引用 domain ids。
- `normalization/` 与 `pipeline.py` 不直接调用 mutable state publication；baseline 必须经 InitializationTransaction。
- `constraints/` 不定义 canonical layout store / occupancy store。
- `export/` 和 `validation/` 不 import mutable transaction applier，不调用 derived finalization，不写 `state/` mutable API。
- `importers/` 不构建 segments / vias / fin attribution 等 state views。
- `planning/` 不调用 exporter / decoder，不修改 committed state。
- `pipeline.py` 不包含 macro-specific geometry arithmetic。
- v2 runtime 与 production test path 不 import `legacy_mvp/`；v2 fixtures / helpers 位于 `tests/fixtures/` 或 `tests/support/`。
- `constraints/` 不 import `transactions/`；`derive/` 不 import transaction / ChangeSet 类型。
- `export/` 与 `validation/` 共享 `domain/artifacts.py` 的中立合同、彼此不 import；需要合并两者结果的 report / visualization 位于 `reporting/`。
- `tooling/` 与 `importers/` 共享 `domain/results.py` / `domain/evidence.py`，彼此不 import。
- 禁止新增依赖 legacy `EditOp` 作为 Stage 5 commit 输出；任何 edit-like artifact 必须位于 `export/` 的 `ExportEdit` 层。
- 禁止新增对 legacy fixture JSON 的 v2 主路径依赖。

这些测试不替代功能测试，但能持续保护第 3、5、8、9、10 节定义的状态边界。当前 `layauto_v2/` 只是按本节边界建立的 v2 skeleton，不包含 legacy MVP 逻辑；历史 `legacy_mvp/` 不得被 v2 runtime 或 production tests import。一次性的离线数据转换若未来需要，应作为仓库外或 release tooling 处理，不进入 Stage 1–6。

## 12. 配置、tech bundle 与环境边界

本节定义哪些内容属于一次 run 的配置，哪些内容属于 tech bundle，哪些内容必须来自输入 evidence 或生产工具结果。原则是：site/run config 只能选择路径、工具模式、执行策略和环境适配；tech bundle 才拥有 layer、rule、unit / DBU expectation 与 mapping 等工艺事实。两者都不能制造某次设计的 layout / schematic / LVS 事实，也不能绕过第 2、3、5、8、9、10 节定义的状态边界。

Legacy MVP 中符合 v2 架构要求的实现可以按职责复用，例如 CDL parser、Calibre query parser、tech config loader、部分 GDS IO、fixture generation / test harness；不符合 v2 架构边界的路径应重构或删除，不需要为 legacy 行为设计 adaptation / migration path。

### 12.1 `site_config.yaml`

`site_config.yaml` 是一次 run 的 manifest。它描述输入/输出路径、tech bundle 入口、Stage 1 evidence acquisition 策略、tool adapter 参数、export policy 与 validation policy。它不承载 device instance、device pins、net membership、target nfin、shape bbox、Calibre query 内容等设计事实。

建议 schema 分层：

- `tech:` 只选择 versioned tech bundle，例如 `drc_rules.yaml`、`layer_map.yaml`、`calibre_layer_map.yaml`、foundry `.layermap` / purpose-map、单位 / DBU expectation；run-specific tolerance / snap policy 不重复写入这些 registry。
- `inputs:` 指向 evidence 文件。v2 主路径以 source CDL、target CDL 或显式 raw ECO intent、GDS / lossless geometry（通过 flat-rectilinear capability check 时可用 round-trip `bbox_by_layer`），以及 Stage 1 产生或读入的 `ixref_yaml` / `net_xref_yaml` / `device_info_yaml` / `net_shapes_yaml` 为核心输入。Target CDL 与 raw intent 至少提供一种；二者同时存在时必须做一致性检查。预生成 normalized YAML 只有在附带 raw-capture reference / hash 与 parser provenance 时才可读入，不能成为绕过 acquisition/parser 的 normalized-only shortcut。
- `outputs:` 指向 artifact 输出目录与命名策略；不得把输出路径反向作为 Stage 5 commit 事实源。
- `calibre:` 描述 Stage 1 Calibre / LVS query 获取策略，例如 `mode: calibre | dummy_fixture`、SVDB path、raw query output path、normalized YAML cache/output path、timeout、command dialect、binary path。`dummy_fixture` 只表示“读取预置 raw query captures，并用同一 parser 生成或核对 normalized YAML”；normalized YAML 不是与 raw capture 二选一的主输入，也不是 legacy parser mode。
- `virtuoso:` / 其他 tool blocks 只描述工具调用环境，例如 lib/cell/view、dry-run、`layer_purpose_dialect` / profile selection、`shape_match_tolerance`、undo policy；dialect 必须解析到 selected tech bundle，不能重定义 canonical layer / purpose。
- `geometry_policy.snap` / `geometry_policy.rounding` 描述 tech-compatible run policy；`annotation_policy` 选择 registry-defined overlay / ambiguity profile 并可在 tech 上限内收紧 tolerance；`virtuoso.shape_match_tolerance` 独立描述 tool locate tolerance。三者不得共用一个无类型 `bbox_tolerance`，site config 也不得放宽 tech bundle 的工艺边界。
- `validation:` 描述 fatal / warning / deferred / skipped policy、rule execution profile，包括 golden regression、self-consistency、signoff DRC/LVS、SKILL dry-run、fixture limitation 等类别。
- `format:` 可声明使用 v2 evidence schema 的版本。它不能声明 legacy parser / legacy decoder 为主路径，也不能允许 Stage 6 writeback 成为 canonical state mutation。

路径可以是绝对路径，也可以相对于 `site_config.yaml` 所在目录解析。loader 必须做 schema validation：缺失 required input、未知字段、路径不存在、mode 与输入集合冲突、legacy convenience input 误用于 v2 主路径，都应在 Stage 1 acquisition 开始前返回 typed `ConfigError` / `StageFailure`；不能伪装为 Stage 6 `ValidationResult`。

`site_config.yaml` 可以包含用于打开工具对象的名字，例如 Virtuoso `lib/cell/view` 或 GDS `top_cell_override`。这些名字只用于定位工具环境中的对象，不能覆盖从 CDL/GDS/LVS evidence 得到的 semantic identity。若工具入口名与 evidence 中的 cell / subckt identity 不一致，应记录为 validation issue，并由 policy 决定是否 fatal。

### 12.2 `drc_rules.yaml`

`drc_rules.yaml` 描述可机器消费的 rule records，而不是散落在代码里的常量。所有尺寸单位默认使用 nm；字段名应稳定，例如：

- `id`：稳定 rule id，如 `LI.S.1`、`V0.E.LI`。
- `type`：规则类型，如 `min_pitch`、`min_width`、`min_spacing`、`min_enclosure`、`min_extension`、`exact_size`。
- `layers`：相关 layer 名称，必须能在 `layer_map.yaml` 中解析。
- `value_nm`：标量或 axis-keyed 值，例如 `{x: 1, y: 5}`。
- `condition`：可选上下文条件，例如 fin role、width class、colour class、derived-layer condition。
- `source`：foundry / project rule source、版本或可审计引用。
- `notes`：解释或适用范围；不承载某个 fixture 的例外。

Rule loader 必须校验 rule id 唯一、layer 可解析、单位明确、axis 名称合法、rule type 与 layer 数量匹配。不能把 rule deck 中没有覆盖的 signoff violation 当作“已验证正确”。

规则的工艺值与适用条件属于 `drc_rules.yaml`；deployment 的 `site_config.yaml.validation.rule_execution_profile` 可以增加 / 强化 `frontline | signoff` 检查并设置 severity / policy outcome，但不得把由 tech + action + capability 推导出的 candidate-touched mandatory Stage 5 rule 降级为 signoff / deferred。缺少 mandatory predicate 必须使 capability admission 失败。v2 MVP 未实现的非 mandatory coverage gap 必须显式进入 validation / fixture limitation report；不能靠 target golden 或 fixture 行为掩盖。

### 12.3 `layer_map.yaml`

`layer_map.yaml` 是 GDS layer、layout tier、坐标拓扑与编辑属性的技术事实源。最低应描述：

- `name`、`gds` / datatype、`purpose` 或 foundry purpose 映射。
- `tier`：A / B / C1 / C2。
- `role`：fin、poly、interconnect、via、cut、diffusion、well、boundary、marker、annotation 等。
- `orientation`：A-tier track layer 的 H / V。
- `ortho`：A-tier layer 的正交 partner，例如 `LI <-> M1`、`FIN <-> POLY`。
- `connects`：via layer 连接的上下层，例如 `VIA0: [LI, M1]`。
- `axes`：非 via B-tier layer 的离散化轴，例如 `OD: [POLY, FIN]`；via 可直接复用 `connects` 作为轴定义。
- `edit_policy`：direct edit policy，例如 `static_backdrop`、`entity_constrained`、`routing_editable`、`derived_refresh_only`、`auxiliary_policy_controlled`、`no_direct_edit`。
- `derivation_policy`：geometry 来源或刷新方式，例如 `drawn_input`、`static_pcell_backdrop`、`prepublication_derived`、`tool_marker`。FIN 在 v2 中是 static backdrop，应表达为 `static_backdrop` / `no_direct_edit` + `static_pcell_backdrop`，同时仍保留 A-tier track abstraction；NWELL / BOUNDARY / VT / PP / NP / DNW 等 C1 layer 则应表达为 `derived_refresh_only` + `prepublication_derived`。v2 architecture 不把单个 `derived: true` 字段作为 FIN 与 C1 的统一语义。
- drawn-patterning policy / optional `drawn_mask_color` interpretation：解释 canonical GDS layer/datatype 或 shape property，可参与工艺规则；独立 `display_color` 只服务 visualization / reports。
- `derived_layer_refs`：只列出可作为 annotation evidence source 的 `calibre_layer_map.yaml` stable names，不重复声明 `carries`、mask、tolerance 或 trim policy。

Grid topology 不应在 parser / grid factory 中硬编码。`orientation`、`ortho`、B-tier `axes` / via `connects` 应由 layer map loader 提供，并做以下校验：

- `ortho` 对称：`ortho(ortho(L)) == L`。
- 正交 layer orientation 必须一横一竖。
- B-tier axes 必须解析到 A-tier layer。
- via `connects` 必须解析到两个可连接 layer。
- derived / non-editable layer 上的 direct edit 应在 Stage 4 capability admission 或 Stage 5 constraint / transaction boundary 被拒绝，不能拖到 export。
- `derived_layer_refs[*]` 必须能在 `calibre_layer_map.yaml` registry 中唯一解析，且 resolved entry 的 `associates_with` 必须包含声明该 ref 的 canonical GDS layer。

Annotation 权威位置应与第 3 / 5 节一致：`state/annotation.py` 中以 occupancy `CellId` 为 key、与同一 `AuthoritativeState` 共同版本化的 table 是权威；occupancy records 与 routing read views 只通过 id 查询它。`ShapeRecord.net_id` / `ShapeRecord.device_id` 只是 per-cell consensus 后的 summary。一个 GDS shape 被 cut 或 diffusion sharing 分裂成多个 identity region 时，summary 可以为 `None`，不能强行写入单一 net/device。

### 12.4 `calibre_layer_map.yaml`

`calibre_layer_map.yaml` 是 Calibre / LVS derived-layer registry。它描述 production query output 中的 layer name 如何映射回 v2 canonical GDS/domain layer，以及这些 derived layers 能携带哪些 annotation。

建议 schema 至少包含：

- `schema_version`。
- `layers:` 或等价顶层 registry。
- 每个 entry 的 `name`：Calibre / LVS derived layer 名。
- `associates_with`：该 derived layer 对应的 canonical GDS/domain layer 或组合，例如 gate recognition、S/D diffusion、routing passthrough、via passthrough、bulk region、marker region。
- `carries`：可携带的 annotation 字段，例如 `device_id`、`net_id`、`pin_role`、`annotated_mask_color`、`none`。
- `semantic_role`：device_channel、device_diffusion、routing_conductor、via、bulk、marker、structural 等。
- `device_type_hint` / `pin_role_hint`：用于 device attribution、S/D disambiguation、report。
- `multi_patterning`：mask / patterning metadata；纯 UI `display_color` 不属于本 registry。
- `annotation_match_tolerance`：该 derived evidence 与 canonical geometry overlay 的 per-layer tolerance / named tolerance profile，单位明确且 site config 只能收紧。
- `exclude_from_grid`：只用于 annotation/report、不参与 grid stamping 的 derived layers。
- `derivation_doc`：来源、SVRF 派生语义、或待 foundry deck 验证的说明。
- `dialect` / `aliases`：处理 production Calibre layer name、AGF/ASAP7 名称、项目 canonical layer name 不一致的问题。
- `trim_policy` / `effective_region_policy`：若该 layer 声称是 effective conducting / active region，应说明 cut / extension trimming 规则；没有实现 trimming 时只能标为 raw bbox / untrimmed evidence。

`calibre_layer_map.yaml` 不拥有 annotation 结果，也不承载 device instance name、target intent、candidate choice 或某次 run 的 query 内容。它只是解释 Stage 1 query evidence 的 tech registry，并且是 derived evidence 的 `associates_with`、`carries`、`annotated_mask_color` / patterning、annotation-match tolerance 与 trim policy 的唯一 mapping authority；`layer_map.yaml` 只以 `derived_layer_refs` 引用这些 entries，同时继续独占 canonical GDS layer/datatype 与 drawn-patterning policy。

当前 fixture 中 `device_info.yaml` 使用 `ngate_lvt` / `pgate_lvt`，`net_shapes.yaml` 使用 `LI` / `VIA0` / `M1`。这些名称都必须能通过 `layer_map.yaml` + `calibre_layer_map.yaml` 解析到 v2 canonical layer 与 `carries` 语义。若 production registry 使用 `GATE` / `ACTIVE` / `V0` / `LIG` / `LISD` 等名称，而项目 canonical layer 使用 `POLY` / `OD` / `VIA0` / `LI`，必须通过 alias / dialect 显式处理，不能靠字符串相等。

### 12.5 配置边界：哪些信息不进入 config

以下信息来自输入 evidence 或运行结果，不应作为语义事实写入 config：

- Device instance name。
- Device type、parameters 与 pins。
- Net membership、net type、pin-to-net 拓扑。
- `nfin` target delta 或其他 ECO intent 内容。
- Design cell / subckt identity。工具入口名可以出现在 tool block 中，但不能覆盖 evidence identity。
- Shape bbox、track index、fin attribution、via list、segment list。
- Calibre query result 内容。
- LVS-derived device/net identity、`lvs_index`、S/D swap 结果。
- DRC/LVS pass/fail 结果。
- 任何为了让 fixture 通过而覆盖事实源的 “expected geometry” 开关。

可以进入 config 的，是“如何读取/运行/验证”的策略，例如路径、tool mode、timeout、layer dialect、validation severity policy、fixture evidence source、export artifact naming、是否启用 optional golden comparison。单位与 tolerance 必须按用途分开：evidence record 声明 source unit / precision，tech bundle 声明预期 DBU / unit，`geometry_policy.snap` / `.rounding` 控制 canonical coordinate policy，`calibre_layer_map.yaml` 的 per-layer `annotation_match_tolerance` 控制 evidence overlay，`virtuoso.shape_match_tolerance` 控制 Stage 6 tool locate；site config 只能选择 tech-compatible profile 或收紧边界。单位缺失只能在 schema 明确允许时使用一个有 provenance 的默认值；显式单位 / DBU 冲突必须 typed-fail，不能用 tolerance 吞掉。即使这些策略会影响 pipeline 行为，它们也不能替代 Stage 1/2 的 evidence normalization 或 Stage 5 的 committed state。

### 12.6 Calibre / LVS query evidence 获取与结构化输入

Calibre / LVS query bundle 属于 Stage 1 evidence acquisition。v2 不再把它称为 “Stage 1.5”；query execution 由 `tooling/` 负责，parser / schema writer 由 `importers/` 负责，两者通过 `ToolRunResult` 与 schema-canonical evidence contract 连接。

Stage 1 应支持两类 evidence 获取方式：

- `calibre`：从真实 LVS SVDB 运行 query，获取 raw `iXref.temp`、`nXref.temp`、`NET NAMES`、per-device `DEVICE INFO <layout_inst>`、per-net `NET SHAPES <lvs_name>`。
- `dummy_fixture`：从 fixture 目录读取预置 raw query captures，走同一 parser 与 normalized YAML/object schema。它用于没有 Calibre 环境的测试，不是 legacy layout parser mode。

Stage 1 输出应同时保留：

- raw query captures：便于审计、复现 parser bug、对照 Calibre format drift。
- normalized objects / YAML：
  - `ixref.yaml`：layout instance ↔ schematic instance，包含 S/D swap。
  - `net_xref.yaml`：schematic net ↔ LVS net name ↔ stable `lvs_index`。
  - `device_info.yaml`：per-layout-instance derived-layer bbox evidence，单位为 µm 或显式声明单位。
  - `net_shapes.yaml`：per-net derived routing/conducting bbox evidence，保留 `lvs_index`、`lvs_name`、`schematic_name`。
- query provenance：mode、source path / svdb、command dialect、timeout、tool version / unknown、parser version、raw-output path。

Stage 1 只做格式解析、显式单位解码为 schema-canonical representation、基本格式一致性检查与 evidence 保存，并保留 original value / unit / precision backlink。Identity join、canonical coordinate snap、空间投影、current/target construction 与 annotation overlay 属于 Stage 2。Stage 1 不应直接构造 `Net.segments`、`Net.vias`、`Device.fin_track_indices`、occupancy、connectivity 或 editable geometry state。

若 query output 缺失、格式漂移或 terminator 缺失，Stage 1 必须返回 typed `EvidenceIssue` 与 linked `ParseResult`；active acquisition profile 声明为 required 的 evidence 无法取得或解析时，再提升为 `StageFailure` 并进入 failure RunRecord。Policy 明确允许缺少的 optional evidence issue 仍须进入 neutral audit / coverage record，Stage 2 将相关 geometry 视为 unannotated / suspect 并采用保守策略。Layout instance 无法 join 到 schematic instance、net name 无法 join 到 `lvs_index`、derived layer 无法映射时，Stage 2 同样返回 typed normalization issue；required identity / mapping 失败才是 terminal StageFailure。任何情况都不能伪装为 Stage 6 `ValidationResult`，也不能静默 fallback 到 fixture 命名相等或 legacy JSON。

### 12.7 生产工具环境适配

生产环境差异通过 tool adapter boundary 处理，不渗入 domain / state / planning / constraint 语义层。典型配置包括：

- Calibre：binary path、SVDB path、DRC/LVS rule deck path、query mode、command dialect / template、timeout、working directory、environment variables、license handling、raw-output 保存路径。
- Virtuoso：lib/cell/view、technology library、tech-declared layer-purpose dialect / profile selection、SKILL dry-run / apply mode、`virtuoso.shape_match_tolerance`、transaction / undo policy。
- GDS / OA / JSON：unit precision / DBU adaptation、top cell selection、tech-declared layer-purpose dialect / alias selection、`geometry_policy.snap` / `.rounding`；adapter config 不得覆盖 canonical layer / purpose truth。
- Signoff：DRC / LVS severity policy、允许 deferred 的检查、是否要求 real-tool closure、是否允许 dummy fixture evidence。

所有工具调用都应返回中立 `ToolRunResult`，而不是只打印 stdout/stderr。它只包含 execution facts：tool name、mode、command 或 redacted command、input / raw-output refs、exit status、timeout / license / environment 分类与 stdout/stderr refs。Stage 1 importer 或 Stage 6 validation parser 另行产生以 `tool_run_id` 单向关联的 `ParseResult` / EvidenceRecord / FindingRecord；冻结的 ToolRunResult 不反向引用后产生的 parse result，tooling 也不拥有 parsed findings。Stage 1–5 orchestrator 按 active acquisition policy 把 required / terminal acquisition、execution 或 parse failure 分类为 StageFailure，optional issue 则进入 neutral audit / coverage record；Stage 6 validation policy 把 tool / parse failure 与 findings 映射为 failed `ValidationResult` 及 severity / policy outcome。

工具缺失、license 不可用、timeout、rule deck 缺失或命令失败进入 ToolRunResult；format drift、terminator / query 字段缺失进入 linked ParseResult。Stage 1 acquisition 的 execution / parse failure 由 acquisition policy 决定是否形成 terminal StageFailure；Stage 6 的 tool / parse failure 与 findings 进入 structured failed ValidationResult。v2 MVP 没有生产工具环境而检查属于声明的 post-MVP capability 时记录为 deferred；policy disabled / not-applicable 才记录为 skipped，不能用 dummy output 伪装成 signoff clean。

Calibre query command-string drift 属于 tool adapter dialect 问题。若不同部署需要不同命令拼写或 preamble，应通过 adapter config / template 扩展，并由测试覆盖；不应把具体命令硬编码到 domain 或 state 构建逻辑中。

### 12.8 Fixture 策略：基于真实 query 事实构建 synthetic cases

Fixture 的目标是稳定复现 production evidence flow，而不是复刻历史 convenience model。Synthetic fixture 应至少包含三类输入事实：GDS geometry、CDL、Calibre-like query bundle（`ixref` / `net_xref` / `device_info` / `net_shapes`）。它可以简化电路规模，但不得引入与 production fact model 相反的假设；v2 fixture generator / adapter 位于 `tests/fixtures/` 或 `tests/support/`，不得 import `legacy_mvp/`。

明确禁止把以下 legacy convenience assumption 当作 v2 正确事实：

- per-device FIN。v2 中 FIN 是 static backdrop，active fins 来自 `FIN ∩ OD ∩ device attribution`。
- `calibre_device_query.json` / `calibre_net_query.json` 作为主路径 truth。它们不是 v2 evidence bundle。
- 未经 layer mapping / trimming 验证的 effective-region claim。若 dummy `net_shapes` 只是 raw GDS bbox，应在 fixture limitation 中明示。
- target GDS/JSON 作为唯一正确性 oracle。fixture golden 只能做 regression；生产 ECO 可以有多个合法解。
- 已知 DRC violation 或 stale fixture 被 byte-golden 掩盖。spacing、enclosure、rounding、stale generation 等问题应进入 fixture limitation 或独立 correctness test。

建议 fixture 分层：

- `regression fixture`：小规模、byte-golden、用于防止无意输出漂移。
- `synthetic edge case`：专门覆盖 conflict、sharing、cut、unannotated blockage、S/D swap、renumbered net、annotation-match tolerance、off-grid drift 等边界。
- `tool-captured fixture`：来自真实 Calibre / Virtuoso 输出的脱敏样例，用于验证 command parser、layer dialect、unit conversion、effective-region trimming。

Fixture 应同时保存 raw query captures 与 normalized YAML，并有检查证明二者同源：

- raw `iXref.temp` → `ixref.yaml`。
- raw `nXref.temp` + `NET NAMES` → `net_xref.yaml`。
- raw `device_info_<layout_inst>.txt` → `device_info.yaml`。
- raw `net_shapes_<lvs_name>.txt` → `net_shapes.yaml`。
- Flat-rectilinear-capable GDS round-trip → `bbox_by_layer`；其它 geometry capability 使用 lossless schema / direct GDS representation。
- CDL source/target → semantic IR / target intent。

Fixture 生成流程应可重复。若 generator 是权威，应有检查确保重新生成后 fixture 目录干净；若 generator 依赖可选包或特定 writer，应把该依赖记录为 test requirement，而不是让 stale fixture 长期漂移。每个 fixture 应附带 machine-readable limitation report，说明哪些 production checks 是真实覆盖、哪些是 dummy/deferred。

## 13. Backlog / audit highlights 的架构覆盖

本节集中说明 backlog 与 correctness audit 在 v2 architecture 中的使用方式。它们不是 legacy 行为的兼容清单，也不是独立于前 12 节的新需求池；它们的作用是把已经验证过的 v1 / fixture / input-side 问题映射到 v2 的事实源、状态所有权、tech bundle、fixture 与 validation 合同中。

纳入本节的 highlight 必须满足两个条件：

1. **工程事实可验证。** 需要能从现有代码、fixture、规则文件或 audit 记录中确认问题不是凭空假设。
2. **architecture 尚需承载。** 如果前文已经给出目标合同，本节只引用其 architecture home，避免在局部章节重复扩写；如果前文只零散提到，本节给出应落入哪个合同面。

### 13.1 已被 v2 主体吸收的 backlog highlights

| highlight | 工程事实确认 | v2 architecture home |
|-----------|--------------|----------------------|
| FIN 被 legacy resize 当作可编辑层，且 dummy FIN 是 per-device stripe | generator 逐 device 生成 FIN stripe；backlog M8 指出 resize 删除 FIN `ShapeRecord` 与 FIN edit path | 第 4.1 / 4.5 / 6.2：FIN 是 static backdrop；`nfin` resize 只改变 OD active coverage；FIN direct edit 应被拒绝。 |
| Fin attribution 只按 Y，无法区分同一 fin track 上不同 X 范围的 device | legacy parser 从 `fin_y_positions` 写 `Device.fin_track_indices`；backlog M8 要求 X/Y 几何归属 | 第 3.7 / 4.5 / 6.4：active fins 来自 `FIN ∩ OD ∩ device attribution`，并由 device bbox / gate footprint / OD overlap 推导。 |
| legacy JSON 把 GDS、CDL、Calibre query 与工作状态揉成 parser-friendly 输入 | current config 仍有 `calibre_device_query.json` / `calibre_net_query.json`；backlog M7 sub-slice 1.7 要退休它们 | 第 2.2 / 5.10 / 12.1：v2 主路径接受 source/target CDL 或显式 raw intent、GDS / lossless geometry（flat-rectilinear capability 内可用 bbox）、tech bundle，以及 `ixref` / `net_xref` / `device_info` / `net_shapes` evidence bundle。 |
| 同一 physical via / routing occupant 有多份 working representation | backlog M9 指出 `ShapeRecord`、`ViaInstance`、`CellOccupancy`、CSP cells 等重复表达 | 第 3.5 / 4.2 / 11.3：layout store 与 occupancy store 分别是 `AuthoritativeState` 内 geometry / occupancy 的权威 components；`ViaInstance` / segments / vias 只能是 read view 或 export view。 |
| same-net DRC 依赖 scalar `net_id`、unknown `None` 过于乐观 | backlog M11 指出 `CellState.net_id`、domain fan-out、`net_id=None` optimistic spacing | 第 3.6 / 8.1–8.6：same-conductor reasoning 走 connectivity component；constraint engine 不拥有 net-labeled occupancy truth。 |
| Stage 6 / decoder / edit stream 曾承担最终几何落点 | backlog M13 指出 Stage 6 replay edits、derivator/export mutation、stdout validation 等边界问题 | 第 2.6 / 9 / 10：Stage 5 commit authoritative state；Stage 6 只读 snapshot，输出 structured validation result。 |

### 13.2 Audit-derived highlights 的 architecture obligation

correctness audit 是 input-side / fixture / format 审计；其中有些问题已经被第 3–12 节吸收，有些不是 core state model 问题，但必须体现在 fixture、tech bundle 或 validation policy 中。v2 不应把这些问题当作 legacy fixture 的正常行为，也不应为它们设计兼容路径。

| audit highlight | 工程事实确认 | architecture obligation |
|-----------------|--------------|-------------------------|
| 当前 fixture 名称大量使用 “buffer”，但电路是单级 inverter | generator 中只有 `MN0` / `MP0` 两个 transistor，pins 构成 inverter；CDL cell 名是 `INV_N*_P*` | 命名问题不改变 core architecture；fixture/report/artifact 命名应遵循 semantic IR，不用文件名或 legacy label 覆盖 CDL / LVS identity。 |
| boundary dummy POLY 与 OD 相交但不在 CDL 中 | generator 在 x=0 / 108 放 dummy POLY，OD 横跨 cell width；dummy gate `net=''` | Stage 2 annotation / coverage / conflict policy 必须保留并保守处理 unannotated geometry；fixture limitation 应声明 dummy-device / LVS-recognition gap。 |
| odd width + `int()` truncation 导致 FIN / LI / VIA0 0.5 nm off-centre | generator `add_shape()` 对坐标直接 `int()`；FIN/LI/VIA0 宽度为奇数 | Stage 1 显式解码 source unit / precision，Stage 2 统一 snap / rounding；annotation-match 与 tool-shape-match tolerance 分开，off-grid validation 必须显式，fixture golden 不能掩盖 rounding artifact。 |
| LI pitch / width / spacing 自洽性不足，fixture 存在 LI spacing 风险 | `LI.P.1=27`，`LI.W.1=17`，`LI.S.1=17`；adjacent LI tracks 只相隔 27 nm | `drc_rules.yaml` 拥有 rule fact；candidate 触及范围内可判定的 spacing 是 Stage 5 mandatory frontline check，完整 deck 另由 Stage 6 signoff，未覆盖项进入 validation coverage gap。 |
| VIA0 LI/M1 enclosure 问题与 via-reach extension 公式不完整 | `V0.E.LI` / `V0.E.M1` 在 rule deck 中存在；generator 只按 enclosure 常量延伸 LI，未加 via half-size；M1 signal stub 宽度固定 20 nm | Candidate 触及的 via enclosure / extension 必须进入 Stage 5 mandatory predicate；若 tech predicate 不可用则 capability admission 失败。Stage 6 signoff 提供额外闭环，不能替代 pre-commit gate。 |
| `device_info` 与 legacy JSON bbox rounding / seed geometry 不一致 | legacy JSON 用 integer half pitch；`device_info` 用 float half pitch，且 seed bbox 是 synthetic gate rectangle | `device_info` 只能作为 annotation seed；Stage 1 显式解码 unit / precision，Stage 2 overlay 使用 canonical snap、registry-defined annotation-match tolerance、layer mapping 与 ambiguity policy，不能把它当 drawn geometry truth。 |
| `net_shapes` 是 raw GDS bbox，不是 trimmed effective conducting region | generator 直接遍历 `layout_data['shapes']` 输出 `NET_SHAPES_LAYERS` | `calibre_layer_map.yaml` / `layer_map.yaml` 必须区分 raw bbox evidence 与 effective-region evidence；未实现 trimming 时只能在 coverage / limitation report 中声明 raw bbox。 |
| Calibre HDB / LVS query format 未经真实 Calibre binary 验证 | audit 与 backlog 均记录 HDB command / output dialect 未验证 | Stage 1 tool adapter 必须保存 raw captures、normalized YAML、parser provenance；format drift / missing terminator / dialect mismatch 进入 structured evidence error。 |
| fixture regeneration 依赖 gdstk 且 committed fixture 有 drift | generator 的 GDS readback 调用 `gds_to_bbox_by_layer()`；GDS reading path 要求 `gdstk`；audit 记录 regenerated diff | Fixture strategy 必须要求可重复生成、regenerated-clean check 或 machine-readable limitation report；依赖缺失不能静默通过。 |
| placeholder SKILL / stdout-only validation | current SKILL helper 只 `printf`，不执行 shape locate / resize；backlog M13 要求 structured validation | 第 10.3 / 10.5：placeholder、dummy、skipped、stdout-only check 不能作为 Virtuoso/SKILL integration profile 的 production pass；该 profile 启用时必须 fatal。 |

### 13.3 避免重复的落点规则

后续如果 backlog 或 audit 新增问题，应按以下规则落位，而不是继续堆到 fixture 策略或任意章节：

- 涉及事实源、annotation、legacy JSON、LVS query schema 的，落到第 2 / 5 / 12 节。
- 涉及 geometry / occupancy / connectivity / `Device` / `Net` ownership 的，落到第 3 / 4 / 8 / 9 / 11 节。
- 涉及 `nfin`、FIN、OD、POLY、routing repair 物理语义的，落到第 4 / 6 / 7 节。
- 新增问题不再新建独立 backlog / audit / legacy-flow 文档；应直接落入对应 architecture section。历史 shipped record 只在 `docs/archive/changelog.md` 保留。
- 涉及 DRC / LVS / SKILL / report / golden / fixture limitation 的，落到第 10 / 12 节。
- 只有跨多个章节、且容易被重复或误解的 highlight，才汇总到本节；本节只做覆盖矩阵，不替代前文的 architecture 合同。
