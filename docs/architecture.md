# Layauto architecture

> **文档定位。** 本文描述 Layauto v2 的目标架构：它以 backlog 中已经识别的关键问题为约束，重新定义事实源、状态所有权、修改语义、约束检查、事务提交、导出与验证边界。现有实现下文统一称为 **legacy MVP**，只作为 legacy/reference implementation 与可复用代码来源；它跑通过端到端链路，但不作为目标架构的正确实现基线。本文中的 **v2 MVP** 则指目标架构的首个实现范围。具体开发顺序、任务拆分与 agentic coding 执行计划应另行维护。
>
> **仓库定位。** `docs/architecture.md` 是当前 docs 下唯一 active v2 architecture source of truth。原 backlog 与 correctness audit 的要求已吸收到本文第 13 节及相关主体章节；旧版 MVP flow 已从 active docs 与 v2 主路径移除；历史 changelog 已归档到 `docs/archive/changelog.md`。legacy MVP 实现已整体移入 `legacy_mvp/`，只作参考与选择性代码复用来源；新的 v2 实现应落入 `layauto_v2/`。

## 1. 项目定位与目标边界

### 1.1 Layauto 要解决的问题

Layauto 是面向 FinFET 标准单元的**增量式版图自动修改框架**。它不从零 placement / routing，也不试图替代 foundry PCell 或完整 signoff flow；它在已有 GDS 几何、CDL 电路语义、LVS/Calibre annotation、工艺规则与工程约束的共同基础上，对 target intent 所描述的局部变化进行受约束、可追踪、可验证的版图修改。Target intent 通常来自 source/target CDL diff，也可以来自显式 ECO command、用户 intent 或经归一化的上一轮 signoff feedback。

核心问题可以概括为：

> 当目标 intent 要求某个标准单元发生局部变化时，系统应如何从真实工程事实出发，规划合法修改，提交到唯一权威状态，并导出可验证产物。

这里的“真实工程事实”包括四类：

- GDSII/OASIS 或 capability-declared semantic-lossless normalized geometry 提供几何事实；`bbox_by_layer` 只用于已证明可无损表示的 axis-aligned rectangle record subset。
- CDL / target intent 提供的电路语义事实。
- Calibre / LVS query 提供的 annotation 与 identity join 事实。
- Tech bundle 提供的 layer、坐标、规则、连通与派生 policy 等技术事实。

`site_config`、tool mode、export / validation policy 只选择一次 run 如何读取、执行和验收，不是 design truth 或 tech truth；它们不能覆盖上述事实。

### 1.2 v2 架构目标

v2 的目标不是把 legacy MVP 局部修补到“能继续跑”，而是重新收敛到以下架构原则：

- **事实源清晰。** 几何、语义、annotation、派生视图各有明确来源，不互相伪装。
- **状态所有权单一。** 版图几何和 occupancy 不应在 parser、grid、engine、decoder、output JSON 中形成多个互相漂移的权威副本。
- **修改语义基于 physical / extraction profile。** 例如在首版候选 `explicit_static_fin_plus_active_window` profile 中，`nfin` resize 不是删除 raw FIN，而是改变 tech-declared active window / OD coverage，并触发相关 routing / via / marking 修复；其它 FinFET representation 不得套用该操作。
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

- 单个标准单元内的增量 ECO。v2 MVP 的最低 acceptance capability 是具名 `FinCountSemanticsProfile` 下的 fixed-frame `nfin` shrink；首个 profile 可以是 `explicit_static_fin_plus_active_window`，但 tech bundle 必须同时给出 fin representation、device/channel recognition、canonical fin-count extractor、canonical `fins_per_finger / finger_count / multiplicity`（及 profile声明的其它真实 model parameter axes）到模型/CDL token的映射、独立的 layout↔schematic device-reduction contract与 resize operator。Profile 不匹配、或任一必要 LI / VIA0 / M1 / marking repair capability 缺失时，该 intent typed-unsupported。Grow 与其它 action 只有在 capability registry 显式声明时才支持，否则 typed-fail。
- 固定 standard-cell frame：cell boundary、rails、profile-declared FIN/gate、frame-static well/boundary、rail topology及 `boundary_halo_signature`保持。候选触及 halo 时，`AbutmentContextContract` 必须枚举完整合法 neighbour equivalence classes（含方向、镜像/row transform）或给出 sound coverage proof并逐类检查；“representative”样本不能证明完备性，缺少合同即 capability fail。
- 以 GDS 几何 + Calibre query bundle + CDL 语义构建 layout state。
- 在 planner / constraint / transaction 边界内完成候选修改、可行性判断和提交。
- v2 MVP 从 committed snapshot 导出 GDS / CDL / JSON / report / machine-readable validation result；SKILL / Virtuoso mirror 与真实 Calibre signoff 通过 policy-enabled Stage 6 扩展点接入，可以明确 defer 到 post-MVP。

**暂不作为 v2 初始目标：**

- 跨 cell / multi-cell routing 与全局优化。
- 从零 placement / routing 或由 netlist 合成完整新版图。
- 完整 device add / device remove / buffer insertion / arbitrary net reroute 的生产级实现。
- M2 及以上完整金属栈、多重图形化、cut-mask、coloring 的完整 signoff 语义。
- 完整 foundry DRC / LVS signoff 自动闭环；v2 先定义可接入边界。

上述优先范围是 **capability contract**，不是对所有 FinFET PDK、CDL 方言或 stream-format 的普遍陈述。每次 run 必须在 Stage 1/2 冻结 `GeometryCapability`、`CdlDialectProfile`、`FinCountSemanticsProfile`、device/body extraction policy 与 rule-coverage profile；缺少其中任一 required operator 或无法证明输入落在声明子集时必须 typed-fail，不能靠 fixture 形状、参数名或工具默认值猜测。

**待选的首版输入范围。** 本文不宣称已选定或验证真实 PDK。`explicit_static_fin_plus_active_window` 是首版候选 profile；首版是否仅接受 one-to-one layout↔schematic mapping、single-finger、no-device-reduction，应在真实 tech/model/query evidence 上确认并由项目验收范围决定。下文 static-fin 示例仅在该 profile 被明确选择且通过 capability admission 时适用；未声明支持的输入仍 typed-unsupported，不因保留扩展点而自动获准。

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
  → publish-time CAS + immutable repository-root publication
  → export + validation
```

Validation / tool feedback 若要触发下一次修复，只能作为**下一轮 run** 的 Stage 1 evidence，再经 Stage 2 归一化为 typed intent；Stage 6 不得在当前 run 内据此 patch committed snapshot。

这个闭环中有两个关键断点：

- **commit 之前**只有候选和事务上下文，不能把几何修改提前写成事实。
- **commit 之后**exporter 只能读取 committed snapshot，不能再修补内部状态。

## 2. 总体数据流与阶段边界

### 2.1 Stage 编号约定

v2 采用连续 Stage 1–6。Query bundle归入 Stage 1；annotation refresh、policy-controlled geometry preserve/frame/derived finalization与 view invalidation归入 Stage 5 repository publication；导出/验证归入 Stage 6。

| Stage | 名称 | 目标职责 | 不应承担的职责 |
|-------|------|----------|----------------|
| Stage 1 | 输入证据获取 | 读取 CDL、GDS/geometry、Calibre/LVS query bundle、tech bundle 与 site/run config，形成 raw captures + schema-canonical evidence records | 不构建工作状态，不做 identity/spatial overlay，不做几何修改 |
| Stage 2 | 语义/空间归一化与状态构建 | 构建 current semantic state、immutable TargetCircuit / TargetIntent、几何 store、坐标系统、annotation state、occupancy / connectivity 与初始 views | 不做 ECO 修改，不复制多个权威几何源 |
| Stage 3 | 约束上下文初始化 | 基于 Stage 2 的坐标系统、occupancy 与 connectivity 初始化 constraint engine、rule context、domain / trail | 不重新拥有 layout state，不规划修改，不提交状态 |
| Stage 4 | 修改意图与候选规划 | 把 Stage 2 归一化后的 typed target intent 转换为 candidate plans | 不直接消费 raw diff / raw command，不绕过 state / grid 手工拼最终 bbox，不提前 side-effect |
| Stage 5 | 可行性检查、事务提交与派生刷新 | 在 private overlay检查 base/annotation/lifecycle state，再由 repository CAS发布一个新 root | 不暴露半提交状态，不导出文件，不把 Python对象名当原子保证 |
| Stage 6 | 导出、生产工具交互与验证 | 从 committed snapshot 导出 MVP artifacts，并按 policy 运行可选 production integration / signoff / report | 不 mutate Layauto AuthoritativeState，不把工具输出反向 patch 成事实 |

Pipeline 入口必须先调用 `PublicationRepository.create_attempt(...)` 创建 **unsealed pre-context** `RunAttempt`，绑定 raw request descriptor/digest、入口可得的 input/config/policy selection digests 与 starting state head；它不能提前声称已得到 canonical target、tech 或 evidence。Stage 1/2 完成后才用 `seal_context(...)` 绑定 canonical TargetIntent、tech/evidence/capability content ids；新 lineage 可由 `initialize(..., sealed_context=...)` 在发布 baseline 时原子完成同一 seal。Unsealed attempt 只能记录 audit并 terminalize 为 pre-context failure，不得进入 Stage 4/5。这样 input/parser/normalization failure 与后续 mutation run 都有同一可恢复 run identity。

### 2.2 Stage 1：输入证据获取

Stage 1 的输出是 raw captures、schema-canonical evidence records、已校验的 tech models 与 run config，而不是 layout model。这里的 canonicalization 只做格式/schema 解析、**精确**单位解码及 provenance 保留；identity join、空间投影、annotation overlay 和 current/target state construction 属于 Stage 2。Source evidence 的坐标/尺寸必须从原始 numeric encoding直接 exact-decode为 integer tick、`Decimal` 或 rational，包括从 GDSII REAL8 bytes恢复其精确有理值，而不是先经过 Python `float`。随后按第 12.5 节 versioned `UnitScaleContract` 与 tech-declared nominal DBU/unit 核对：有限精度 unit encoding 与 nominal scale 的已声明等价不等于 source-coordinate snap。Original bytes/lexeme、exact decoded value、nominal scale、precision、equivalence contract 与 source-DBU backlink必须保留；binary `float` 不得进入 canonical geometry、rule predicate 或 content hash。Stage 2 必须在已验证的 scale binding 下选择能精确表示 source integer ticks / drawn geometry 的 canonical integer DBU，不能取整改写 source geometry；snap/rounding 只用于新 candidate 合法化，annotation matching 使用独立 tolerance。Stage 6 canonical → artifact unit / DBU serialization 是独立的纯输出变换。

输入包括：

- Source CDL，以及 target CDL / ECO command / 用户指定 intent / 未来 signoff feedback raw input 中至少一种 target-intent source；多种并存时 Stage 2 必须验证一致性。
- 原始 GDSII / OASIS 或声明 capability 内 semantic-lossless 的 normalized geometry；只有每个 record 都通过 axis-aligned-rectangle losslessness check 时才可使用 round-trip `bbox_by_layer`。GDS `BOUNDARY`/`BOX` 的 normalized geometry被证明恰为轴对齐矩形时可以进入该 subset；任意 rectilinear polygon不能仅因边均正交就退化为其包围盒。不受当前 `GeometryCapability` 支持的 reachable hierarchy、element、transform、property 或 repetition 必须保真 passthrough 或 typed-unsupported。
- Calibre / LVS query bundle：`ixref`、`net_xref`、`device_info`、`net_shapes`。
- 技术配置：site config、layer map、Calibre layer map、DRC rules。

Stage 1 应做的事：

- 解析 source CDL；若提供 target CDL 则提取 target circuit / raw diff，若提供其它 raw intent 则保留为待 Stage 2 归一化的 evidence。
- 运行 profile-declared Calibre/LVS query 或读取 dummy fixture raw captures，保存可审计的 raw query output 与 schema-canonical evidence YAML/对象；这些对象仍不是 domain/layout facts。Query bundle header 必须绑定 source layout hash、source netlist **transitive dependency closure** hash与 top identities，以及 deck/map/runset/include/preprocess/options closure hashes、query database/run id、tool/dialect version及 LVS completion/match status；与本 run 输入不一致时 fatal，或只在显式 degraded profile 下作为 suspect evidence。Dummy fixture 必须以 raw captures 为源并走同一 parser / schema，不得绕回 legacy `calibre_device_query.json` / `calibre_net_query.json` 主路径，也不得用 normalized-only input 绕过 parser。
- 从 stream input 读取当前 `GeometryCapability` 内 semantic-lossless geometry；仅对逐 record 证明为 lossless axis-aligned rectangle 的 subset 归一为 `bbox_by_layer`，并保留未 annotation 的几何。这里的 lossless 是 canonical geometry/hierarchy/metadata 语义等价，不承诺 byte、record order 或 writer-specific fracture 相同。
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
| Current semantic state | Source CDL | `domain.circuit` 定义 value types；`state.semantic` 持有 current state | planner、transaction、CDL exporter、report / validation | commit 表示 declared intent；snapshot内 assurance只反映 publication前运行的 trusted extractor，Stage 6 LVS另写 ValidationResult而不回改 snapshot |
| Immutable target reference | Target CDL / raw intent 经 Stage 2 归一化后的 `TargetCircuit` / `TargetIntent` | `domain.circuit`、`domain.intent`；由 RunRecord / snapshot context 引用 | planner、whole-intent closure validation、report | 不属于 `AuthoritativeState` 的 mutable current semantic component，不被 commit 改写 |
| Geometry store | GDSII/OASIS 或 capability-scoped normalized geometry | `state.layout_store` | annotation overlay、occupancy projection、planner、transaction、exporter | 以 tagged geometry/hierarchy/transform/property records 保留声明 capability 的语义；`bbox_by_layer` 只覆盖 flat rectangle subset |
| Annotation state（由 overlay 产生） | Calibre query bundle：`ixref`、`net_xref`、`device_info`、`net_shapes` | `annotation.layer_overlay` 产生 `AnnotationTargetId`-keyed state；`state.annotation` 受事务管理 | planner、constraints、DRC/LVS localization、coverage report | target 是 exact occupant/shape/device region；仅在 atomic grid capability 内才退化为 bare `CellId` |
| Occupancy store | geometry store + layer tier + Stage 2 coordinate system | `state.occupancy` | constraint engine、planner、transaction、connectivity broad phase、read / export views | canonical discrete working/index abstraction；每 cell 可含多个 exact-coverage occupant fragments，不能独自证明几何、连通或 DRC clean |
| Connectivity state | exact effective-conductor/device/body regions + tech connection/separation operators；occupancy 仅作索引，annotation只供 identity/relation summary | `state.connectivity` | constraint engine、router、transaction、validation / report | physical topology interpretation；annotation不得增删 edge/component，不把 transistor S↔D 当 conductor edge |

这些对象的产生顺序是有依赖关系的：source CDL 形成 current semantic state；target CDL / raw intent 单独形成 immutable target reference；stream evidence 先形成 geometry store；tech layer map / rule deck 先形成 Stage 2 coordinate system 与 effective-geometry/device-extraction operators；geometry store 再结合 coordinate system 和 layer policy 投影为 multi-occupant base occupancy，并由 exact effective conductor、terminal、via、cut与 body regions及 tech contact/separation operators建立 physical connectivity。Calibre evidence通过 layer mapping和 tolerance policy形成 `AnnotationTargetId`-keyed annotation state，把 identity/relation assurance关联到既有 exact regions/components；缺失或变化的 annotation不得制造或删除 physical edge。Read / export views（routing spans、gate tracks、fin attribution、annotation coverage、artifact edit view 等）只从这些权威对象重算或缓存，不作为新的事实源。

Stage 2 的关键原则：

- Stream/capability-declared semantic-lossless geometry 是几何事实源；bbox 只覆盖已声明 subset；LVS shapes 是 annotation 与 identity evidence，不是完整几何替代品。
- `Device` / `Net` 是语义 IR，不应长期保存可从 layout store 推导的几何副本。
- Annotation overlay 是 evidence-to-identity 的解释过程；其权威结果进入 AuthoritativeState 内 `AnnotationTargetId`-keyed annotation state，occupancy / shape / component 只持有 reference 或可重算 summary。`AnnotationTargetId` 可以引用 occupancy fragment、shape region、device region或 body region；bare `CellId` 只在已证明 cell 边界细化覆盖所有 relevant geometry/cut/annotation boundary 时成立。Overlay 算法本身不拥有 layout state。
- Grid / coordinate system 在 Stage 2 建立，用于 geometry-to-cell projection；它是坐标系统，不能成为 layout occupancy 的长期 owner。
- Constraint engine 可以建立检查用 cache / trail，但不能成为 occupancy 或 connectivity 的另一份权威副本。
- Unannotated shapes 必须保留，并按保守策略作为 blockage / suspect geometry 进入后续判断。

Stage 2 有两个互斥退出路径。新 lineage 走 baseline-only `InitializationTransaction`：它构建 neutral `PreparedPublication(kind=baseline)` 后调用第 2.6节唯一 `PublicationRepository.initialize(...)`，在同一 publication transaction内执行 state-head create-if-absent、context seal与 attempt revision advance，发布 version 0 snapshot、InitializationEvent与 composite head。已有 lineage只加载所请求 head并调用 `seal_context(...)`；canonical context必须与 snapshot binding完全相容，不再运行 baseline initialize。新 evidence/tech/coordinate binding需要新的 lineage或显式 future rebase protocol，不能改写旧 lineage。并发冲突 typed-fail。Policy-controlled geometry逐层 preserve/frame/derive，缺 operator/comparator不得发布。

### 2.4 Stage 3：约束上下文初始化

Stage 3 初始化“判断候选是否合法”所需的约束上下文。它读取 Stage 2 已经建立的 coordinate system、layout state、occupancy 与 connectivity，但不重新构建或拥有这些状态。

主要内容：

- 读取 Stage 2 已建立的 layer grid、track coordinate、B-tier axes 等坐标系统。
- 加载 DRC rule records 与 rule predicates。
- 建立 constraint engine 的 domain / trail / propagation context。
- 接入 Stage 2 的 occupancy store 与 connectivity index。
- 标记固定几何、blockage、effective cut/operator result、qualified via edge、diffusion terminal sharing等约束语义。

v2 的目标合同是：constraint engine 不拥有 layout state，也不维护一份可与 layout store 漂移的 occupancy copy；它只在 Stage 2 的 coordinate system、occupancy 与 connectivity 之上叠加 rule predicates、domain、trail、propagation context 和 candidate feasibility API。

允许为了性能建立检查用 cache / index，但这些 cache 必须可由 Stage 2 state 重建，有明确 invalidation 规则，不作为 authoritative occupancy / connectivity，也不能被 planner、transaction 或 exporter 当作 layout truth。

### 2.5 Stage 4：修改意图与候选规划

Stage 4 将 Stage 2 归一化后的 typed target intent 转换为 candidate plans；它不直接消费 raw CDL diff、raw command 或 raw signoff log。

以 `nfin` resize 为例，planner 应解释：

- 目标设备是谁。
- semantic delta 是什么，例如 `MN0.nfin: 5 → 4`。
- selected profile 对该 delta 的 physical/extraction operator 是什么，例如 static-fin profile 的 active/OD coverage 改变。
- 可能受影响的 LI / VIA / M1 / policy-controlled markings 与 boundary/body context 是哪些。
- 是否需要 LI / VIA / M1 / cut-effective-geometry / marking 局部 repair 或候选排序。

Stage 4 的候选是“待检查计划”，不是已提交修改。它可以包含 grid cells、shape ids、semantic ids、repair requirement、old/new coverage、预期 derived refresh region、provenance seed 等，但不能把候选直接写成 committed geometry。

Unsupported intent 应在 Stage 4 显式失败。失败结果应说明：哪个 intent 无法被当前 planner 覆盖、是否有部分候选被拒绝、系统是否已经保持无副作用状态。

一个 executable `PlanningResult` 只绑定一个 `base_snapshot_id`，并包含 deterministic-ordered、fully-ground、dependency-closed alternatives。Explicit partial policy每轮必须让 declared remaining-obligation set严格缩小，或让显式 well-founded rank严格下降，并禁止已满足 obligation回退；content fingerprint只用于 identity/cycle detection，不能充当有序 progress metric。上一轮 candidate/precondition/trail不得复用，禁止 empty/no-op envelope，并设置 max iterations与 final closure check。

### 2.6 Stage 5：可行性检查、事务提交与派生刷新

Stage 5 是唯一可以把候选变成权威状态的阶段。

持久可见性的唯一 owner 是 `PublicationRepository`，不是 Python transaction object。它在同一 selected backend/transaction domain内拥有 state-lineage head与每个 `RunAttempt` 的 revision/context/stage5/terminal pointers，并只接受 `domain/publication.py` 的 canonical neutral DTO：

- `create_attempt(...)`：在 pipeline 入口创建 unsealed attempt，只绑定 starting state head、raw request/input descriptor digests与入口 config/policy selection digest。
- `seal_context(...)`：Stage 2 后绑定 canonical TargetIntent、tech/evidence/config/policy/capability content ids；refs必须可解析且 digest一致，seal 后不可更改。新 lineage可由 `initialize(..., sealed_context=...)` 原子完成 baseline create-if-absent与 context seal。
- `initialize(...)`：baseline create-if-absent，并同时推进 attempt revision。
- `publish_whole_and_close_stage5(...)`：default whole-intent在 CAS 前预构造 deterministic state/commit ids并冻结 RunRecord，再让 CommitEnvelope、new state head与 `Stage5Closure(with_run_record)` 一次可见。
- `append_partial(...)`：partial envelope、state-head advance与 run-attempt chain revision同事务可见。
- `close_stage5(...)`：partial/no-change/failure冻结 RunRecord并发布 `Stage5Closure(with_run_record)`；no-change不改 state head。若恰在 RunRecord构造失败，则发布 discriminated `Stage5Closure(run_record_freeze_failure)`，只含 StageFailure、completed neutral audit refs与 optional committed chain，且只能 terminal reject。
- `finalize_precontext_failure(...)`：只允许 unsealed attempt；同事务冻结最小 failure RunRecord（run id、completed neutral audits与 typed StageFailure；canonical context refs缺省）并 terminalize，不得带 CommitEnvelope或 post-change artifact。它不是第二个“无 RunRecord”例外。
- `finalize_pipeline(...)`：原子发布 Stage 6 refs、immutable `PipelineResult`与唯一 terminal pointer。`PipelineResult.lifecycle_status = terminal`，`deployment_disposition = accept | requires_review | reject`；validation/report/export结果到 deployment disposition 的聚合由 frozen policy明确。Crash位于 stage5-close与terminalize之间时，recovery可重跑纯 Stage 6或标 interrupted。

Repository必须在同一 CAS/transaction内校验 **phase + revision + execution mode**，而不只校验 revision：

| Current phase | Operation | Next phase | Guard |
|---------------|-----------|------------|-------|
| absent | `create_attempt` | `unsealed` | caller-supplied stable `proposed_run_id`、starting-head CAS；revision = 0 |
| `unsealed` | `seal_context` / new-lineage `initialize` | `sealed_open` | context refs完整；冻结 `execution_mode = whole_intent \| explicit_partial` |
| `unsealed` | `finalize_precontext_failure` | `terminal` | 无 CommitEnvelope/post-change artifact；最小 failure RunRecord |
| `sealed_open` | `append_partial` | `sealed_open` | 仅 `explicit_partial`；chain连续且 state CAS成功 |
| `sealed_open` | `publish_whole_and_close_stage5` | `stage5_closed` | 仅 `whole_intent`；state、envelope、RunRecord与 closure一次可见 |
| `sealed_open` | `close_stage5` | `stage5_closed` | partial/no-change/failure closure符合 discriminated schema |
| `stage5_closed` | `finalize_pipeline` | `terminal` | terminal bundle绑定同一 closure/final snapshot |
| any phase at/after original operation | same-key/same-digest replay | unchanged | 只返回该 operation的既有 result refs；不重做 mutation |

每次请求先在同一原子域查询 idempotency record并比较 canonical digest；命中 same-key/same-digest时绕过当前 head/revision guard返回原 refs，same-key/different-digest立即 typed conflict。只有首次执行才校验 transition与 preconditions。Seal 后再次 seal、unsealed直接 Stage 5 close、whole/partial API混用、未 stage5-closed就正常 finalize及 terminal后新 mutation均为 typed transition conflict；只有表中 idempotent replay例外。

`create_attempt(expected_state_head=...)` 对请求的 starting head做 CAS并创建 revision 0；它尚无 prior attempt revision。Pipeline/caller在首次调用前生成并跨重试保留 `proposed_run_id`，create request digest包含它，因此“repository已创建但响应丢失”的重试仍命中同一 attempt。其余 attempt mutation都比较 `expected_attempt_revision`；会创建/推进 state的 `initialize/publish/append` 还比较 `expected_state_head`。`no_change` closure必须 CAS其作出结论时观察的 state head，避免发布已过时的 no-change；其它 run-only close/finalize绑定 immutable `final_snapshot_id`并记录 `head_status_at_finalization = current | superseded`，即使另一 run随后推进全局 head也必须能 terminalize。该字段只是 finalization瞬间的 observation；要求 latest-at-consumption的 consumer必须把 terminal bundle的 lineage/snapshot与 live head原子重验，不能信任历史枚举。是否允许 superseded结果为 `accept` 由 frozen deployment policy决定。Repository-scoped idempotency table以 `(operation_kind, proposed_or_final_run_id, idempotency_key)` 原子记录 canonical request digest和 result refs；proposed/expected lineage与heads进入 request digest/preconditions。同 key同 digest返回原结果，即使 head已推进；同 key异 digest返回 typed conflict；该记录与 root/run-pointer switch同事务提交。Repository不 import `transactions/`，transactions只构建 neutral DTO/canonical bytes。

“同事务可见”与“断电后持久”是两项物理 backend contract：要么使用提供 durable commit语义、能原子更新 state head与 attempt revision/pointer的单一 ACID transaction/WAL，要么先 durable写入 content-addressed immutable siblings，再对包含两者的 **单一 composite repository-root record** 做一次条件 CAS。Local-FS durable profile必须 fsync sibling files及其 parent metadata、原子 replace root并 fsync root parent；object-store durable profile必须声明 immutable-write durability/read-after-write consistency与 single-root linearizable conditional CAS。Object store上的两个独立 conditional writes不构成该原子性；local filesystem也不能靠依次替换两个 head file模拟。不满足 durability条件的实现只能标 process-local/best-effort。Crash-durable profile 的 crash-injection contract test必须覆盖 sibling写入、root switch与响应丢失三个边界。Process-local MVP 可以按第 9.2 节实现进程内原子 publication、rollback 与幂等重试，不承诺跨进程/断电恢复；durable backend 与 crash-recovery 验收不因此变成 MVP 必做项。

流程：

1. 接收带 `state_lineage_id`、`base_snapshot_id`、old-state preconditions、idempotency key 与 `apply_atomicity` 的 fully-ground selected plan group，并打开 transaction-private overlay / checkpoint。
2. 将 Stage 4 已具体化的 proposed base mutations应用到 transaction-private overlay，由 exact effective geometry与 tech operators重建/更新 tentative physical connectivity；planner的 annotation refresh/invalidation request交给 `annotation/` 生成 tentative `AnnotationState`与 relation assurance。Annotation只关联 identity/relation，不得增删 physical edge；未具体化的 required repair不可执行，planner也不得直接给出任意 authoritative annotation value delta。
3. Constraint engine 根据 tech / layer / action policy 独立补全 mandatory checks，并从 staged delta 重算、扩张 affected scope；candidate 自报的 checks / region 只能增加检查，不能缩小检查范围。
4. 在 overlay 中仅对输入依赖已就绪且未标 dirty 的 DRC / connectivity / blockage / intent-invariant / rule predicates 做 early check；stale precondition 或有效检查失败则丢弃 overlay，并生成结构化失败结果。依赖尚未刷新的派生几何/annotation 的检查保持 pending，不得用旧值判 infeasible，也不得视为 pass。
5. 在同一 overlay按 versioned dependency DAG finalise annotation attribution/validity与逐层 policy-controlled geometry，然后检查其消费者。任一 actual delta都必须把下游 annotation、exact device/body extraction、effective conductor、physical connectivity、relation assurance、intent invariants与 rule predicates标 dirty并按拓扑序重算；annotation delta本身只触发 identity/relation-dependent checks，不改变 physical topology。只有声明“不参与上述任一消费者”并有 dependency proof的 marking才可 late-finalize。Closure无法证明时全量重算或 typed-unsupported；存在 dependency cycle时只有绑定终止/唯一性证明的 bounded fixed-point contract才可迭代，否则 capability fail。直至无 dirty/pending node且全部 mandatory checks通过才可发布，任一有效检查失败整体回滚。
6. Whole-intent先用 deterministic ids冻结 PreparedPublication + RunRecord，再调用 `publish_whole_and_close_stage5(...)`；partial调用 `append_partial(...)`，全部 groups结束后才 `close_stage5(...)`。Repository在 publish-time重验 state/run heads与 preconditions，令 state version=parent+1并只切换 roots；冲突要求 replan。RunRecord freeze失败时 whole-intent不发布 state，partial earlier envelopes不伪装回滚且正常 Stage6被阻止。

Stage 5 的合同：

- 失败的 plan group 不得留下 partial edit；whole-intent / dependency-group policy 下，组内后续 candidate 只能读取同一 overlay 中的 tentative state，直到整组一次发布。
- Candidate-level policy 下，已发布 candidate 通过新 snapshot 对下一轮 Stage 4 可见；下一个 candidate 必须基于该 snapshot 重新生成。该 partial-apply 语义必须显式启用、可审计，且不需要等 Stage 6 decoder 回放。
- Commit 的目标是 authoritative layout state，而不是 output JSON、legacy edit stream 或 exporter-side patch。
- Policy-controlled geometry finalization位于 Stage 5 private overlay、repository publication之前；它不是 Stage 6 side effect。
- v2 不把 legacy L1 EditOp / ShapeEditRecord 作为核心状态模型；Stage 5 产生的是 ChangeSet / CommitEvent，Stage 6 如需 SKILL 或 diff visualization，可从 ChangeSet 派生 artifact-specific ExportEdit。任何 edit event 都不是 authoritative geometry。
- v2 不定义 legacy `EditOp` / decoder writeback / output replay / `engine → shape_pool` writeback 等过渡路径。正确目标是 Stage 5 transaction 直接提交到唯一 authoritative layout state；不符合该边界的 legacy 实现应作为错误状态流删除或重构，而不是进入 v2 architecture。

`AuthoritativeState` 是唯一权威聚合；各 component table 有各自明确 owner，但只能通过同一 transaction gate 一致发布，不能成为彼此竞争或漂移的副本。它至少包括：

- current semantic state：从 source CDL 初始化、已提交的 `Device` / `Net` / pins / params；immutable target circuit / intent 单独保留。
- geometry store：单一 tagged geometry/hierarchy/property graph，包含 drawn 与 policy-controlled partitions、record ids、element-specific stream layer key/canonical purpose、origin/lifecycle、annotation summary 与 provenance；flat bbox只是 declared subset，C1 不是第二 geometry owner。
- occupancy state：A-tier / B-tier multi-occupant cells、exact coverage refs、blockage、via、cut、OD / diffusion sharing broad-phase data。
- annotation state：`AnnotationTargetId`-keyed identity / pin-role attribution、source-evidence backlink、validity 与 conflict metadata。
- connectivity state：effective conductor/terminal/body region membership、exact same-layer / via edges、tech-defined cut effects 与 diffusion sharing / split topology；不拥有 semantic / annotation summary。Gate/channel 把 active 分为 S/D terminal regions，transistor S↔D 关系属于 device semantics 而不是 conductor edge。`ComponentId` 是 snapshot-scoped stable id，topology mutation 的完整 snapshot-to-snapshot lineage（unchanged / merge / split / removed / created-without-predecessor）必须进入 ChangeSet，调用方不得假定 id 跨 snapshot 自动延续。
- Policy-controlled layout geometry：geometry store 中每层按 `preserve_drawn | frame_static | prepublication_derived`（contextual derivator 可另标）管理。只有绑定 generator/version/dependencies/dirty-scope/equivalence comparator 的 layer 才进入 `c1_derived` partition；BOUNDARY、well、VT、implant 等不能按名称被普遍假设为可局部重算。
- read-view version / invalidation metadata；segments、vias、fin attribution、gate tracks、annotation coverage、net-to-component summary 等 materialized views 是 non-authoritative cache，可删除并从 snapshot 重建。
- immutable context / state linkage：`state_lineage_id`、`coordinate_system_id`、`tech_bundle_id`/hash、`evidence_bundle_id`与 `evidence_assurance = lvs_matched | bound_unverified | synthetic`、`state_version`、snapshot/parent/commit/change ids。Coordinate/tech/evidence binding 在 baseline 后不可由 ECO transaction 改写；关键 device mapping非 matched/complete 时 resize capability不得启用。Sibling records与 snapshot同 publication可见。

Immutable snapshot 必须满足**递归不可变与无可写别名**，而不仅是 `@dataclass(frozen=True)` 或 `MappingProxyType` 的浅只读：nested sequence/map 要 defensive-freeze 为真正 immutable value，COW/persistent structure 更新创建新节点，wrapper 的 backing 不得被外部持有。Lazy/materialized cache 位于 snapshot 外并以 snapshot id 索引。Publication 前后可用 canonical content digest 验证旧 snapshot 未变。

所有持久 records 必须有 versioned wire schema 与显式 encode/decode。Typed IDs、Enum、Path、Decimal、tuple/frozenset 和非字符串-key table 不能依赖默认 JSON/YAML round-trip；map/table 编码为规范 records 或规范字符串 key，集合与 fields 显式排序，UTF-8、数字/路径/enum representation 固定，拒绝 NaN/Infinity。Content identity与 idempotency digest使用对 canonical record bytes明确指定的 cryptographic algorithm（例如 SHA-256）；ArtifactManifest的 integrity hash则对**实际存储的 artifact byte stream**取值，另需 semantic digest时使用不同字段/algorithm contract。禁止 Python `hash()`、dataclass `__hash__` 或 set/dict iteration order充当跨进程 identity。

### 2.7 Stage 6：artifact export 与 validation

成功 run 的 Stage 6 只读取 final committed snapshot、该 run 的 ordered ChangeSet / CommitEvent chain、immutable `RunRecord` / diagnostic provenance、site/tool config、export policy、validation policy，以及可选的 fixture golden target。Whole-intent 的唯一 RunRecord在 state publication前冻结并随 `publish_whole_and_close_stage5(...)` 一次可见；partial/no-change则在 `close_stage5(...)` 时冻结。它包含 input summary（含 tech / coordinate ids 与 hashes）、neutral PlanningAuditRecord / ConstraintAuditRecord、Stage 1–5 audit records、ordered commit ids、final snapshot id 与 provenance，不嵌入 planning / constraint implementation objects。Stage 6 必须按该 ordered chain 汇总 validation expectations、ExportEdit 与 report delta，不能只读取最后一个 commit。Stage 6 产出的 ArtifactManifest、ToolRunResult、ValidationResult、ReportingResult 分别引用同一 run id / final commit-snapshot ids，不反向修改 RunRecord。Stage 6 不读取 live planner / mutable transaction object，也不把 Stage 1 raw evidence 或 target diff globals 当作输出事实源。

Stage 6 输入包括：

- immutable committed snapshot。
- Ordered ChangeSet / CommitEvent chain（默认 changed whole-intent 一项；`no_change` 为空）。
- immutable RunRecord / diagnostic provenance。
- site/tool config。
- export policy。
- validation policy。
- optional golden target。

输出包括：

- Required v2 MVP core artifacts：GDS、JSON / machine-readable layout snapshot、CDL；以及 policy-enabled optional integration artifacts，例如 SKILL / Virtuoso script。
- Immutable export `ArtifactManifest`；每个 selected artifact 使用 immutable/versioned URI、size、cryptographic hash、type与requiredness，manifest不得引用 staging或可覆盖路径。Validation/report/pipeline records由后续对象持有，不能在 manifest 冻结后回填。
- Stage 6 `ToolRunResult` / `ParseResult`、`ValidationResult`。
- Human / machine-readable report、optional visualization / debug artifacts 与 `ReportingResult`。

成功路径的 Stage 6 先冻结 ExportPlan并写 unique immutable/versioned objects。`ArtifactPublicationCapability`区分 atomic visibility与 crash durability：local-FS durable profile要求同一 filesystem、文件 fsync、涉及 rename/replace的源/目标 parent-directory metadata fsync及 root replace后 parent fsync；object-store profile要求 immutable object、conditional create/CAS与声明的 read-after-write consistency。不满足时只能标 process-local/best-effort。最后发布单一 ArtifactManifest pointer；它只证明 export set完整/可寻址，不是 deployment approval或多文件物理事务。

Validation/reporting完成后，pipeline调用 `PublicationRepository.finalize_pipeline(...)` 原子发布 PipelineResult与 terminal run/release pointer。Production consumer必须从 `PipelineResult.lifecycle_status=terminal` 且 `deployment_disposition=accept` 的 terminal root解析 manifest+validation；不得仅凭 ArtifactManifest消费未验证产物。若 consumer policy要求结果仍是 lineage latest，还必须把 terminal bundle的 lineage/final snapshot与 live repository head原子重验，`head_status_at_finalization` 不能替代消费时检查。Orphan/staging object由 recovery/GC清理。

对被捕获 failure，pipeline构建 terminal PipelineResult并经 repository terminalize；Stage 1/2 context seal前的失败走 `finalize_precontext_failure(...)`。Crash-durable profile 的 crash/OOM/power loss由 repository-owned RunAttempt journal恢复：每个 partial envelope绑定 run id、chain index、previous envelope和 context digest。Recovery只从该 attempt的 durable run-head/last envelope继续，且仅当它仍等于 lineage head、所有 bound content可解析且 digest一致；head分叉/输入漂移则 interrupted/requires-review，除非显式 full reconcile/rebase policy。Process-local profile 不声称具备此恢复能力；存储不可用时只能 best effort。

Target delta 在 baseline/current snapshot 已完全满足，且本 attempt 尚未发布任何 ECO CommitEnvelope 时使用 run-wide `no_change` success variant：不生成 ECO CommitEnvelope，`RunRecord.ordered_commit_ids=[]`、`final_snapshot_id` 指向当前稳定 snapshot，Stage 6 仍可正常导出/验证；不得伪造 empty commit。若 explicit partial run 已发布 earlier envelopes，后续 replan 得到无剩余 delta 只表示该迭代无新 candidate，必须作为 changed partial success 关闭并保留完整 ordered chain，不能改成空链 `no_change`。`ValidationResult` 因此强制 `run_id + final_snapshot_id`，commit/ordered-chain 仅在 run-wide no-change 时可为空。

Stage 1–5 的 failure path 按 publication state 区分两类；除下段 `run_record_freeze` 唯一例外外，两类都必须冻结 RunRecord。**No-publication failure** 表示本 run 尚无 CommitEnvelope（默认 whole-intent failure 属此类）：failure RunRecord 只强制包含 run id、已完成的 neutral stage audit records 与 typed StageFailure，last-stable-snapshot / planning / constraint audit refs 按到达阶段可选；只能生成 diagnostic report，不得生成“修改后”geometry artifact。**Partial-policy terminal failure** 表示 explicit candidate / dependency-group policy 下已有 earlier CommitEnvelopes：已发布 commits 不伪装回滚，failure RunRecord 必须列出 applied / failed / skipped deltas、ordered commit ids 与 final stable snapshot；在 RunRecord 成功冻结后，是否允许导出由 policy 决定，任何输出必须标为 non-production / requires-review。Failure reporting 对 ChangeSet / ArtifactManifest / ValidationResult 使用 optional refs，绝不能把 failed delta 伪装成 committed artifact。

Stage 5 已关闭、且 policy 允许进入 Stage 6 后发生的 export / validation / reporting failure 使用既有 frozen RunRecord，加上 linked StageFailure 和已完成的 artifact/check refs；既有记录可以是 success/no-change，也可以是 policy-enabled diagnostic export 的 partial-failure variant。不得重写 RunRecord、回滚已发布 state，也不因 no-change 没有 commit 就误用上述 pre-export failure 路径。Pipeline 按 frozen policy 汇总并 terminalize；required export/check/reporting failure 阻止 production acceptance，failure reporting 的 optional refs 见第 11.11 节。

`run_record_freeze` 是上述两类中唯一允许缺少 RunRecord 的 record-construction failure：repository以 `Stage5Closure(run_record_freeze_failure)` 原子记录 typed StageFailure、已完成的 neutral audit refs与 optional ordered CommitEnvelope ids，并直接或在 optional diagnostic report后发布 `deployment_disposition=reject` 的 terminal PipelineResult。该 variant 不进入正常 Stage 6 export 或 `ValidationResult`；diagnostic reporting 直接消费这些 refs，不能虚构 success / failure RunRecord。

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

因此，v2 的目标不是把所有事实压缩成一个 table，而是让每一层的来源、可变性、transaction 责任和重算路径清楚。`AuthoritativeState` 是单一聚合，受控包含 current semantic、single geometry store（drawn/preserved/frame-static/derived lifecycle）、occupancy、annotation、connectivity 与 view-version/linkage metadata；各 component 有明确 owner，但只能一起发布。

v2 的基本原则是：

- GDSII/OASIS 或 capability-declared semantic-lossless evidence 是 drawn geometry 的事实源；bbox evidence受 proven axis-aligned rectangle record subset限定。
- Source CDL 初始化 authoritative declared semantic state；physical/extracted equivalence由 assurance字段区分，target是独立 desired reference。
- LVS / Calibre query 是 geometry ↔ schematic identity 的 annotation evidence。
- `AuthoritativeState` 是 committed state 的唯一聚合 owner；layout store 按 drawn/preserve/frame/derived lifecycle持有 geometry，occupancy/annotation/connectivity/current semantic各自持有明确维度。
- Occupancy store 是后续候选规划、约束检查与事务提交使用的离散几何工作基底。
- Connectivity state 以 exact effective geometry为真值、occupancy为索引，是 physical component/terminal/body split/share 的权威结构；DRC exemption仍由 RuleRecord relation basis决定。
- Grid / coordinate system、constraint engine、exporter、reporter 只能读取或派生视图，不能成为第二套 layout truth。
- Read / export views 必须可从 authoritative state 重算；它们不能反向成为事实源。

### 3.1 几何事实源

几何事实来自 GDSII/OASIS 或声明 capability 内 semantic-lossless 的 normalized geometry；只有逐 record 证明可无损映射为轴对齐矩形的 v2 MVP subset 才能用等价的 `bbox_by_layer` evidence。`GeometryCapability` 必须声明 stream format/version、hierarchy/flatten policy、支持的 element kinds、transform/array/repetition/property/text policy 与 round-trip comparator；reachable unsupported record 必须被保真 passthrough 为 fixed/non-editable record，或在 baseline 前 typed-fail。该 capability 内的每个 drawn record 应进入 layout store，携带：

- stable `shape_id`。
- layer / purpose / optional `drawn_mask_color`；纯 UI 属性使用独立 `display_color`。
- tagged geometry，例如 boundary/polygon、path、box、text、cell reference/array、transform、repetition 与 properties；flat-rectangle subset 才可退化为 bbox。
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

语义事实来自 CDL 与 target intent。CDL并非无方言通用语法；Stage 1分别冻结 source/target parser profile，并冻结兼容的 output `CdlDialectProfile`/supported subset。Profile必须定义 identifier case-folding/escaping、subckt pin order、globals、model token、terminal order、numeric suffix与 scale/unit、continuation/directive、parameter-expression grammar/evaluator/rewriter，以及 source→canonical→output 的保真 comparator。若 affected parameter是表达式而 profile不能 soundly evaluate并重写为目标语义，必须 typed-unsupported，不能字符串替换或按 Python表达式求值。`.include`/library与 preprocess依赖必须解析为 immutable transitive dependency closure并进入 content hash；导出时生成 self-contained portable bundle，或用 immutable dependency manifest重写/绑定引用，不能把可能失效的原相对路径当成完整 artifact。Opaque record只有在 profile能证明其与 edited semantics无依赖时才可原样 passthrough；否则 typed-fail。`CurrentCircuitState`从 source CDL初始化并随 commit更新，Target保持 immutable。

- cell / subckt identity。
- `Device`：instance name、device type、parameters、pins。
- `Net`：net name、net type、pin membership。
- target delta / intent：resize、add/remove、reroute、cut/share/split 等。FinFET size语义先归一为 `fins_per_finger`、`finger_count`、`multiplicity`（及 profile声明的其它真实 model parameter axes），再由 model/dialect profile映射到 `NFIN`、`NF`、`M` 或其它具体 token；token名不保证跨模型承担同一轴，禁止凭参数拼写猜测。Device-reduction policy/cardinality属于独立 layout↔schematic extraction metadata，不是默认 CDL parameter axis。Resize intent必须明确改变哪个 canonical parameter axis，未被 intent改变的轴才是不变量。

`Device` / `Net` 是 semantic IR，不应长期保存可从 layout store + annotation + occupancy 推导出的几何副本。`ixref` / `net_xref` join、LVS index/layout name 以及来自 `device_info` 的 device bbox / gate seed bbox 属于 annotation state / `DeviceAnnotationSeed`，以 canonical semantic id 为 key；它们是 run-scoped evidence backlink 或 stamping seed，不是 semantic field 或 geometry owner。

以下内容在 v2 中不属于 `Device` / `Net` 的权威语义状态：

- `Device.fin_track_indices`。
- `Device.gate_track_idx`。
- `Net.segments`。
- `Net.vias`。
- routing bbox 列表。
- via bbox 列表。
- 可由 selected profile 的 effective FIN/active/gate/device extractor 重算的 fin attribution/count。

如果迁移期继续暴露这些字段，它们只能是从 authoritative layout state 重算的查询结果或短期缓存。任何 planner 或 transaction 都不应只依赖这些缓存来决定物理修改。

### 3.3 LVS annotation overlay

LVS / Calibre query 的角色是 annotation，不是完整几何事实。它负责把 layout-side geometry 和 schematic-side identity 连接起来：

- `ixref`：layout instance ↔ schematic instance，包含 S/D swap 等信息。
- `net_xref`：layout net / LVS index ↔ schematic net。
- `device_info`：per-device derived-layer seed shapes。
- `net_shapes`：per-net routing-layer shape evidence。

annotation 可以不完整，也可能有 sub-nm drift、layer-name difference、effective-region trimming difference。因此 overlay 需要 tolerance、layer mapping、coverage report 和 conflict policy。

v2 的 annotation home 应是 `state.annotation` 中以 `AnnotationTargetId` 为 key 的 table；occupancy fragment 只持有 reference，而不是 identity fields。`AnnotationTargetId` 至少能引用 `(layer, CellId, OccupantFragmentId)`，并可引用不进入主 occupancy 的 `ShapeRegionId` / `DeviceRegionId` / `BodyRegionId`。它不能退化为 bare CellId 或仅 shape-level summary，因为一个 GDS record 可能：

- 被 cut 分成多个连通区域。
- 跨越多个 device 的 diffusion sharing 区域。
- 一部分有 LVS annotation，一部分没有。
- 在不同 cells 上携带不同 net / device / pin role。
- 因 effective-region trimming 与 drawn bbox 不完全一致。

因此 overlay 的目标是把 `device_id`、`net_id`、`pin_role`、LVS-derived `annotated_mask_color`、coverage/conflict marker 等 identity references 写入 region/fragment-keyed authoritative annotation table。只有当所有 relevant geometry/evidence boundary 都与 cell partition 对齐时，才允许以 bare occupancy `CellId` 作无损快路径。Shape-level `net_id` / `device_id` 与 connectivity component summary 只能作为可重算 consensus：当覆盖 regions 完全一致时可以汇总；一旦不一致，应保持 unknown / ambiguous，并把细节留在 fragment annotation 与 coverage report 中。未定义的 “store cell” 或 mutable connectivity component 不得成为 annotation owner。

Annotation overlay只负责 identity association与 relation assurance；via/cut/diffusion/device-terminal physical topology仅由 exact effective geometry与 tech operators决定。Component-to-annotation/net/device summary可以读取 per-region/fragment annotation重算，但该 summary不是 physical edge的输入。

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

Layout store 保存 drawn geometry，是 stream / semantic-lossless normalized evidence（或 capability-scoped bbox）归一化后的几何事实承载者。Occupancy store 则是 drawn geometry 经 coordinate system 投影后的离散 working/index abstraction；它不是 continuous geometry 或 exact topology 的替代物。

二者关系是：

- layout store 记录 capability-declared tagged geometry/hierarchy/property、canonical layer/purpose，以及 source-evidence 或 commit/derivator provenance。
- coordinate system 定义 track、cell、pitch、offset、orientation、B-tier axes。
- occupancy store 记录 `(layer, cell, occupant_fragment)` 的 coverage，以及该占据的 kind、exact-geometry reference、annotation-state reference 和 blockage / via / cut / OD 等语义标记；同一 cell 可以有多个彼此不连通的 fragments。

Occupancy 不是原始事实源：base cell projection 可由 layout store + coordinate system + layer policy 重建；包含 annotation reference、blockage / conservative classification 等语义的 enriched occupancy 还需要 annotation state 与 conservative policy，connectivity 则从 effective geometry 另行重建。Occupancy 也不是普通 cache，因为 v2 的 candidate planning、CSP broad phase、transaction delta 和 affected-scope indexing 都以它为主要工作对象；但 spacing/enclosure/line-end/min-area/connectivity 的 final mandatory predicate 必须读取 exact effective geometry，除非 tech capability 已证明该 cell projection 对该 predicate 无损且无 false negative。

目标状态容器应统一管理：

- drawn geometry records。
- A-tier / B-tier occupancy。
- shape-to-cell projection。
- cell-level device / net / pin annotation references。
- blockage / unknown / suspect geometry。
- cut / via / diffusion sharing state。
- commit-visible current state。

实现可以分层存储，例如 current-semantic table、geometry table、occupancy table、annotation table、connectivity table，但 architecture 要求它们是同一 `AuthoritativeState` 的受控 components，由一个 transaction gate 原子发布。其它对象必须是 read view、cache、transaction overlay 或 export artifact。

可测试的 projection invariant 是：每个纳入 occupancy capability 的 editable drawn record 都有可由 exact geometry 重建的 projection；每个 physical coverage delta 都绑定同一 transaction 内的 exact-geometry delta。纯 annotation reference / blockage-policy 更新单列为 non-drawn state delta，不能借 occupancy assign/release 隐式创造或删除 drawn geometry。

一个 physical occupant 在 working state 中只能有一个权威 occupancy 表达。例如 VIA0 的目标表示不应同时是 `ViaInstance`、B-tier occupancy、LI WIRE cells、M1 WIRE cells 和 CSP assignment。正确做法是：VIA0 drawn geometry 进入 layout store；其 occupied cells 进入 occupancy store；其跨层导通作用由 connectivity state 的 via edge 表达；任何 `ViaInstance` 只是查询或导出视图。

同理，OD active region、LI/M1 routing、raw CUT与其 effective result、blockage都由同一 substrate/reference chain表达，再由不同 view暴露。

### 3.6 Connectivity state 作为拓扑解释层

Connectivity state 以 exact effective geometry 为真值、以 occupancy 作为 spatial broad phase，用于解释哪些 conductor/terminal/body regions 属于同一个 topological component。它不是 CDL net label 的副本，也不是普通 derived view；它是 routing feasibility、via connectivity、cut effect、diffusion sharing / split 与 rule-declared relation predicate 的权威拓扑结构。

Connectivity state 应覆盖：

- same-layer edge只由 tech-declared contact predicate建立，显式区分 area overlap、edge abutment、corner/point touch、mask/purpose/property条件；cell adjacency只枚举候选。
- via/contact 与上下层 effective conductor 的 qualified overlap/contact edges；存在 via cell 本身不足以建边。
- cut layer 按 tech-declared `cut_target` / Boolean `effective_geometry_operator` 作用后的 geometry；raw cut 不是跨 layer 通用的标量 barrier。
- diffusion terminal sharing / split；effective S/D region 必须排除 gate/channel separator，不能把晶体管两端 union 为 conductor。
- tech-dependent well/substrate/body-region graph，或 MVP 明确冻结该域并以 baseline LVS + body/boundary invariant 阻止变化。
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

- DRC predicate 按 `RuleRecord.relation_basis` 查询 `geometry_only | same_component | same_extracted_net | semantic_net | voltage_class | mask_property | none`，并检查 `required_relation_assurance`；connectivity component不是所有 rule的通用 exemption。`same_extracted_net` 只接受绑定当前 exact region、未被 affected scope失效且来自 matched extraction evidence的 relation；candidate-derived semantic attribution、stale pre-edit label、ambiguous或 `unverified_after_edit` ref都视为缺 context。缺少 required relation context时按 `missing_context_policy` fail/defer；只有绑定具体 fallback relation/value与单调安全 proof时才可 `conservative_fallback`，不能猜测。
- `CellState` / CSP domain 不携带长期 `net_id` / `device_id` ownership。
- `net_id=None` 不表示“与所有 named nets 兼容”；unknown / unannotated geometry 默认按 blockage、suspect conductor 或 conservative conflict 处理。
- VIA 是跨层 connectivity edge，不需要用 LI/M1 上额外的 via-as-wire double stamp 伪造连通。
- CUT 通过 tech-declared target/Boolean operator 改变 effective geometry、component relation、device recognition 与 rule checking；其 occupancy 标记只作索引。
- diffusion sharing / split 是 topology 与 physical attribution 的共同问题，不能写入 current semantic `Device.shared_with[]` 作为孤立 truth；如需展示，只能从 occupancy / connectivity / annotation 派生 view。

Connectivity state 必须纳入 transaction checkpoint / restore / commit。任何 occupancy change、via add/remove、cut add/remove、OD split/share 都必须在 overlay 中增量更新；如果先标 invalid，则必须在 publication 前重建受影响 components。只有 non-authoritative index / cache 可以跨 commit 保持 invalid。`ComponentId` 在一个 snapshot 内稳定；跨 topology mutation 时，ChangeSet 必须记录 old→new component lineage（unchanged / merge / split / removed / created-without-predecessor），调用方只能经 lineage 追踪，不能把旧 id 静默沿用到新 snapshot。

Physical component 只表示 snapshot 声明的 geometry scope / hierarchy 内的物理导通。Scope 外 pin、global rail 或互连提供的 net association 必须来自显式、证据绑定的 hierarchy/pin/global-connect relation policy，不能仅凭同名 net 在本地图中增加 physical edge；这不扩展 v2 MVP 的跨 cell routing 范围。

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
profile-defined effective FIN
  ∩ effective active / OD
  ∩ recognized gate/channel
  → qualified fin/channel crossings
  + DeviceId / gate-stripe / device-reduction grouping
  → per-finger fin-count
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

**Policy-controlled layout geometry 单独处理。**

NWELL、BOUNDARY、VT、PP、NP、DNW 等 C1 records 不是普通 read view，但也不自动等于 derived。Tech profile 逐层声明 preserve/frame-static/derived；只有 certified derived layer 在 Stage 5 private overlay 中重算，所有 lifecycle 结果都在 publication 前比较、检查并进入 snapshot。Stage 6 只序列化 final result。

FIN static/no-edit（若 profile声明）、C1 tier 与 derived lifecycle 相互独立；实现不能用一个 `derived` 布尔值混代三者。

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
- geometry store 的 drawn/preserved/frame-static/prepublication-derived partitions 与 lifecycle metadata。
- occupancy。
- authoritative annotation state / references / validity metadata。
- connectivity components。
- blockage / unknown / suspect markers。
- `coordinate_system_id`、`tech_bundle_id` / hash 与 neutral state-linkage metadata；full tech objects、ChangeSet / CommitEvent / RunRecord 不嵌入 snapshot。

实现上可以是 defensive deep-freeze、copy-on-write 或 persistent data structure；任何 wrapper 只有在 backing 已冻结且无 external writable alias 时才合格。Stage 4–6 看到的 nested graph 必须递归不可变、版本化、可重跑。

## 4. Layer tier 与物理实体抽象

第 4 节定义 layer tier、物理实体、编辑策略与 connectivity 语义之间的关系。v2 中，**tier 是粗粒度 representation / lifecycle class**：A/B 描述参与 occupancy 的 1D/2D 离散化，C1/C2 描述不进入同一主 occupancy 的 derived / auxiliary geometry 生命周期。Tier 不能单独决定是否可编辑；一个 layer 的完整架构属性至少包括：

- **tier**：A/B 的 coordinate / occupancy projection，或 C1/C2 的非主-occupancy geometry lifecycle class。
- **role**：物理或工艺角色，例如 fin、gate、interconnect、via、cut、diffusion、well、boundary、text、marker。
- **edit policy**：layer map 提供默认值，例如 static backdrop、entity-constrained edit、routing-editable、derived-refresh-only、auxiliary-policy-controlled；shape / region / physical-entity record 可以施加更严格的 `fixed_frame` / `no_direct_edit` override，限制优先。
- **connectivity / annotation policy**：effective conductor/device/body operator、via/contact predicate、cut target/Boolean effect、diffusion sharing / split、blockage，以及哪些 occupant regions 可引用 annotation state。
- **lifecycle / derivation policy**：`preserve_drawn | frame_static | prepublication_derived`，以及 contextual derivator 的 generator/version/dependencies/dirty-scope/equivalence contract。

因此，v2 不应把 “Tier A” 理解为“都用 TrackSegment 独立存储并可由 macro 直接改”，也不应按 layer 名称推断 lifecycle。FIN 只有在 selected profile 声明时才是 A-tier static backdrop；NWELL、BOUNDARY、VT、PP、NP、DNW 等每一层都可能是 preserved drawn、frame static 或 certified derived，必须由 tech profile 逐层决定。

### 4.1 Tier A：1D coordinate / backdrop / routing layers

Tier A 表示在 selected tech capability 中可**无损或保守**投影到 track coordinate 的层，例如某些 FIN、POLY、LI、M1。Preferred direction 不表示该层所有 geometry 都是一维：jog、rail、pin、off-track 或 bidirectional shape 仍保留 exact 2D geometry，只有声明 `projection_kind` 及 soundness 的 subset 才走一维快路径。

v2 中 Tier A 至少分三类：

- **Profile-scoped static backdrop layer：FIN。**
  - 只有 `FinCountSemanticsProfile.fin_representation = explicit_static_fin_plus_active_window` 才要求 raw FIN 由 PDK/PCell/cell architecture 给出固定 pitch backdrop。
  - 该 profile 的 `nfin` resize 不删除、不新增 raw FIN geometry；其它 representation 需要自己的 resize operator，否则 unsupported。
  - Active fin attribution 由 profile-defined effective-fin/channel/device-recognition operator 推导，并同时处理 gate-stripe grouping、canonical size axes与 one-to-one/device-reduction cardinality；具体 `NFIN/NF/M` token只由 model/dialect profile映射，不能只数唯一 fin track或按 token名猜测。
  - 在该 profile 内，FIN 具备明确的 `no_direct_edit` / `static_backdrop` 标记；该 policy 与 C1 lifecycle 分开表达。
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

Tier B 表示需要二维 cell/fragment occupancy 的层，例如 OD、VIA0、CPO、M0_CUT、FIN_CUT。它承载 broad-phase active/via/cut/diffusion indexing；exact via edge、cut effect、device terminal 与 conductor connectivity 仍由 tech operator 在 effective geometry 上建立。

- **OD / diffusion。**
  - OD/active 在 static-fin 候选 profile 中是 `nfin` resize 的核心作用对象；其它 profile 可以使用不同 effective-active representation。
  - 对该 static-fin profile 的 `nfin` resize，目标是调整 device active window/OD coverage，使 extractor 识别的 per-finger active fin 数符合目标，而不是删除 raw FIN。
  - OD occupancy 必须携带或可定位 device attribution、pin role、sharing / split、blockage / suspect 标记。
  - 多 device 共享 diffusion 时，sharing 不应只保存在 `Device.shared_with[]` 之类 metadata 中，而应体现在 occupancy、connectivity component 与 semantic attribution 的一致关系中。
- **VIA layer：VIA0。**
  - VIA0 drawn shape 进入 layout store。
  - VIA0 occupied cell 进入 occupancy store。
  - VIA0 的电学作用由 connectivity state 中的跨层 via edge 表达。
  - 不应同时用 `ViaInstance`、B-tier cell、LI wire cell、M1 wire cell、CSP assignment 等多个可漂移工作表示来表达同一个 physical via。
  - 如保留 `ViaInstance` 类型，只能作为只读查询 / API 兼容 shim / export view，不能拥有独立状态。
- **CUT layers：CPO、M0_CUT、FIN_CUT。**
  - Raw CUT 是 drawn negative/trim/control geometry，不是跨工艺通用的 scalar barrier。
  - Layer map 必须声明 `cut_target` 与 Boolean `effective_geometry_operator`；effective result 才改变 component relation、routing、device recognition 与 diffusion split/share。
  - CUT occupancy 必须纳入 transaction checkpoint / restore / commit，并在 overlay 中触发 connectivity 增量更新或 publication 前 affected-component rebuild。
  - 首个 `nfin`-only profile 默认禁止 fin-targeting / gate-targeting CUT edit；只有独立 capability 能证明 effective fin/channel 和 extracted device topology 满足 intent invariant 时才可启用。

Tier B 的 projection 应写入唯一 occupancy store。Grid 只提供 B-tier axes 和 bbox-to-cell projection，不拥有 `b_tier_cells` 这类 layout content。Constraint engine 可以缓存检查结果，但不能成为 Tier B occupancy 的第二份权威副本。

### 4.3 Tier C1：policy-controlled final layout geometry

Tier C1 是不进入主 occupancy、但必须随 snapshot 保真的 policy-controlled layout geometry。NWELL、BOUNDARY、VT、PP、NP、DNW 等只是可能成员，不能按名称一律视为可由 tentative A/B state 局部重算；tech profile 必须逐层声明 `preserve_drawn | frame_static | prepublication_derived`，contextual derivation 还必须声明所需邻接/halo。

C1 的合同是：

- `preserve_drawn` 必须保留 source geometry；`frame_static` 必须与 parent/boundary signature 一致；二者不得被 derivator重建。
- `prepublication_derived` 的输入来自 transaction-private tentative state、semantic/device metadata、tech rules 与完整 derivator contract；缺少 certified derivator 默认不是 derived。
- Derived finalization 在 Stage 5 base materialization 之后、commit publication 之前完成；其实际 delta 必须再次扩张 affected scope并重跑被触发的 mandatory predicates，失败则整体回滚。
- 刷新结果进入 committed snapshot，成为 Stage 6 可序列化的 layout geometry。
- Stage 6 只读取并导出 C1 state，不临时修补 C1。
- 普通 candidate / macro 不得直接 patch derived C1 shape；preserved/frame-static layer 也只能经其显式 edit capability 修改。
- 对 fixed-frame `nfin` resize，BOUNDARY、frame-level NWELL 及其它声明为 frame invariant 的 geometry 必须与 parent snapshot 相同；任何 delta 都是 failure，除非存在显式 frame-edit intent / capability。其它真正依赖 delta 的 marking family 才进入 dirty scope。

需要注意，C1 tier、derived lifecycle 与 FIN static profile 是三个独立维度；都可能触发 direct-edit rejection，但不能共用一个布尔 `derived` 字段替代完整合同。

### 4.4 Tier C2：auxiliary / marker / policy-controlled geometry

Tier C2 包括 TEXT、marker、DIODE / ESD marker layer 或其它不进入主 CSP / routing occupancy 的辅助几何。真实参与导电、device recognition 或 DRC 的 DIODE / ESD active / routing shapes 仍按对应 A/B layer role 建模，不能因器件类别被整体降为 C2。C2 不应简单理解为 LVS annotation overlay；它们仍可能是 GDS 中真实存在的 drawn geometry或生产工具需要保留的 marker / waiver carrier。

C2 的合同是：

- C2 record 必须进入 layout store，按 GeometryCapability 保留 text/geometry/property/hierarchy semantics、source evidence、layer/purpose、provenance 与 annotation summary。
- 默认情况下，C2 不参与主 routing / diffusion / via occupancy，也不作为 planner 修改的直接目标。
- 如果某类 C2 对象允许编辑，必须有显式 edit policy、validation policy 和 provenance，并通过 Stage 5 transaction / commit log，而不能由 exporter 或脚本绕过权威状态。
- 如果某类 C2 对象影响 DRC/LVS、ESD、diode recognition 或 tool waiver，其语义应通过 policy / validation hook 暴露，而不是混入 LVS annotation overlay 的 identity stamping 逻辑。

因此，C2 更准确的定位是 “auxiliary / marker / policy-controlled geometry”，而不是普通 “editable annotation”。

### 4.5 Profile-scoped FIN / gate representation

FinFET PDK 对 fin 的版图表达并不统一。首版候选 profile `explicit_static_fin_plus_active_window` 把 raw FIN 建模为固定 pitch backdrop，并把 fin-count 变化实现为 effective active window 改变；只有明确选择且验证该 profile 后才适用。若 PDK 以 active width、fin block/cut、PCell parameter或其它 representation 表达 fin 数，必须选择另一 profile/operator，不能套用下面公式。

正确的 active fin attribution 是：

```text
effective FIN geometry
  ∩ effective active / OD geometry
  ∩ recognized gate/channel region
  → qualified fin/channel crossings
  + DeviceId / gate-stripe / device-reduction grouping
  → profile-defined per-finger fin count
```

这意味着：

- `Device.fin_track_indices` 不应作为长期存储字段驱动 resize。
- 在该 profile 中 FIN stripe 不应按每个 device 局部生成或删除。
- 同一 fin track 可以跨多个 device x-range 存在；device bbox/query anchor只作 broad phase，最终归属由 profile-defined exact recognized channel/device regions、qualified fin/active crossings与 canonical DeviceId/gate-stripe grouping判定。
- 多 device 沿 X 方向复用同一批 FIN track 时，active fin attribution 必须同时考虑 X 与 Y，不能只按 fin Y 坐标归属。

Gate / POLY 不能被简化为普通 rectangle patch。POLY 与 gate pitch、device recognition、gate-cut、pin access、source/drain attribution 和 routing topology 相关。Effective S/D conductor region 典型地由 active region 排除 recognized gate/channel 后得到；gate/channel 是 terminal separator，晶体管的 S↔D device relation绝不是 conductor edge。v2 首个 `nfin` resize profile 可以要求 effective gate/channel topology 不变；若 intent 需要移动、截断或重建 gate，必须由专门 planner 与 extraction capability处理。

### 4.6 OD active region、diffusion sharing 与 device attribution

在 `explicit_static_fin_plus_active_window` profile 中，OD/active window 是 `nfin` resize 的主要编辑对象。对一个 device 从 `nfin = old` 改到 `nfin = new`，planner 应提出 profile-defined active coverage 候选，并声明受影响的：

- OD occupancy cells。
- device attribution。
- S/D pin role attribution。
- diffusion sharing / split relation。
- nearby LI / VIA / M1 access region。
- 需要刷新的 derived markings 与 read views。

OD change 不能只更新 drawn bbox，也不能只更新 semantic `Device.nfin`。成功 commit 后，current semantic state、layout store、occupancy、annotation attribution / validity、connectivity state、derived geometry 与 provenance 必须一致。

Diffusion sharing / split 应作为 occupancy + connectivity + semantic attribution 的共同关系：

- occupancy 表示哪些 OD cells 被 active diffusion 占据。
- connectivity state 表示哪些 extracted S/D terminal regions 属于同一 diffusion conductor component，是否被 effective cut/split 断开；不得跨 recognized gate/channel union。
- annotation / semantic attribution 表示 component 或 cell 与哪些 device、pin role、net identity 相关。
- report / validation 可以从上述结构派生 `shared_with` 之类展示字段，但它们不是权威事实源。

### 4.7 VIA / CUT / routing connectivity

VIA、CUT 与 routing layers 的核心语义应由 connectivity state 统一解释。

- VIA 是跨层 connectivity edge。
  - VIA0 connects policy 来自 layer map / tech bundle，例如 `connects: [LI, M1]`。
  - Connectivity state 先以 occupancy 枚举候选，再按 via 与上下层 effective conductor 的 tech-defined exact overlap/contact predicate 建立 edge。
  - Rule checking 使用 via geometry、enclosure、spacing 和 component relation，而不是依赖 via-as-wire double stamp。
- CUT 是 effective-geometry operator 的输入。
  - CPO / M0_CUT / FIN_CUT 按 tech-declared target/Boolean recipe 切断、trim 或限制相应 layer/entity；不同 CUT 不共享一个隐式语义。
  - CUT 变化必须触发 connectivity component 更新，并进入 transaction checkpoint / restore / commit。
- Routing layers 的修改必须从 candidate path / candidate shape change 开始。
  - Router / planner 只产生 plan。
  - Constraint engine 以 occupancy broad phase + exact geometry判断 spacing/enclosure/blockage/via legality，并按每条 rule 的 relation basis处理 exemption。
  - Transaction commit 成功后才更新 layout store、occupancy 与 connectivity。
  - Exporter 不能通过修改 output JSON 的 shape bbox 来补齐 routing state。

对于 unknown / unannotated geometry，不能把 `net_id=None` 当作“与所有 net 兼容”。未解释几何应按 blockage、suspect conductor 或 conservative conflict 进入 routing / DRC 判断，直到 annotation overlay 或人工 policy 明确其语义。

### 4.8 Layer map 与 tech bundle

Layer map 和 tech bundle 是 v2 的工艺参数化边界，但不承载 cell-specific intent 或 target delta。

Layer map 应描述：

- canonical layer/purpose 与 element-tagged `StreamLayerKey` 的映射：普通 geometry 使用 layer/datatype，TEXT/BOX/NODE 等使用其对应 stream type；purpose/name 是外部 tech 语义，不是 GDSII record 的通用字段。Unknown key 必须保留为 fixed/non-editable 或 typed-fail，不能丢弃。
- tier：A / B / C1 / C2。
- role：fin、poly、interconnect、via、cut、diffusion、well、boundary、text、marker 等。
- `projection_kind`、coordinate axes/lattice/pitch/offset、preferred/bidirectional/jog policy；projection axis 不从 electrical connection 猜测。
- connectivity/extraction policy，例如 via `electrical_connects` 与 exact contact predicate、cut `cut_target` / effective-geometry operator、conductor/device-terminal/body role。
- default edit policy，例如 `static_backdrop`、`routing_editable`、`entity_constrained`、`derived_refresh_only`、`auxiliary_policy_controlled`；shape / entity 的 stricter override 优先。
- lifecycle / derivation policy：`preserve_drawn | frame_static | prepublication_derived` 及其 derivator contract，或 selected FIN profile 的 no-direct-edit guard。
- canonical stream-layer-key / purpose mapping，以及对 `calibre_layer_map.yaml` stable names 的 `derived_layer_refs`；不重复 derived `carries`、tolerance、trim 或 alias/dialect metadata。

Tech bundle 应描述：

- pitch、width、spacing、enclosure、extension、minimum area 等 rule records。
- coordinate system 参数，例如 track pitch / offset、B-tier axes。
- rule predicate 的参数化输入。
- `FinCountSemanticsProfile` 与 `DeviceExtractionContract`：fin representation、model/terminal mapping、canonical size axes到具体参数 token的映射、gate-stripe grouping、effective active/channel recipe、layout↔schematic mapping cardinality、body/bulk policy、extractor/version 与 resize operator。`NFIN/NF/M` 只是某些 profile的可能 token，不是全局语义轴。S/D terminal symmetry/swap 必须按 model/tech/body context显式声明，不能假设所有 MOS S/D 可自由互换。首个 MVP 可以限定 one-to-one、single-finger、no-device-reduction；其它输入 typed-unsupported。
- RuleRecord 的 relation basis 与所需上下文，例如 physical component、extracted/schematic net、voltage class、mask property 或 none。
- signoff 所需 rule-deck / layer-map 的逻辑 identity、version 与 compatibility metadata；具体 filesystem path / binary path 属于 site/tool config。

Layer map / rule deck 不应包含：

- cell-specific intent。
- device instance name。
- target `nfin`。
- 某次 ECO 的 candidate choice。
- fixture-only convenience field。

Schema 不得使用单个 `derived: true` 同时代表 direct-edit rejection、FIN profile与 C1 lifecycle；必须拆成 `edit_policy`、selected physical profile与逐层 lifecycle/derivation contract。

需要注意，Layer map / tech bundle 只定义 layer 的工艺语义、映射规则和 policy；它不保存某次 Calibre query 的 annotation 结果。`layer_map.yaml` 拥有 canonical GDS layer 的 drawn-patterning policy，并解释 GDS geometry 上的 `drawn_mask_color`；`calibre_layer_map.yaml` 独占 derived evidence 的 `annotated_mask_color` / carries / tolerance / trim mapping。Stage 2 必须按 tech reconciliation policy 比较两者：一致时形成 rule-facing color view，冲突时标记 suspect / conflict 并按 policy typed-fail 或 requires-review。`device_id`、`net_id`、`pin_role`、coverage / conflict marker 等属于 per-run annotation result。`display_color` 仅服务 UI，不得与任一工艺颜色共用无类型 `color` 字段。

## 5. LVS / Calibre annotation boundary

第 5 节定义 v2 如何把 Calibre/LVS query结果作为 annotation evidence 接入 Stage 1–2。核心原则是：**stream/capability-declared semantic geometry提供 drawn truth；`bbox_by_layer` 只覆盖 proven axis-aligned rectangle record subset；CDL dialect profile提供 circuit semantics；query bundle提供绑定到确切 baseline的 identity evidence。** LVS shape不是 stream geometry替代物。

Annotation boundary 需要同时解决四个问题：

1. 哪些输入是原始证据，哪些是必须丢弃的 legacy convenience path。
2. 如何把 LVS 侧 instance / net identity 归一到 schematic identity。
3. 如何通过 GDS↔LVS layer mapping 把 derived-layer evidence stamp 到 occupancy。
4. 如何报告 coverage gap、conflict、ambiguity，并把 unknown geometry 保守地交给后续约束系统。

### 5.1 v2 输入事实组成

v2 fixture 与生产输入应由以下事实组成：

- **Source CDL + target-intent source。** Source CDL 提供 current circuit；target CDL 或声明的 raw ECO / user / prior-feedback intent 至少提供一种，并在 Stage 2 归一化为独立 immutable TargetCircuit / TargetIntent。
- **GDSII/OASIS 或 capability-scoped normalized/bbox geometry。** 提供声明 capability 内完整 drawn semantics；超出 flat subset 时不得以 bbox 包络替代。
- **Calibre query bundle。** 包含 QueryBundleHeader 及 instance/net xref、device/net region等 normalized capabilities；具体文件名由 dialect profile决定。
- **Tech bundle。** 提供 layer map、Calibre layer registry、rule records、coordinate / derivation policy 等技术事实。
- **Site/run config。** 选择 tool path、query mode、输入输出路径与 validation / tolerance policy；它不是 design 或 tech fact。

Stage 1 负责读取或生成上述 evidence，并保存 raw output 与 schema-canonical middle files。Stage 2 才负责 semantic / identity / spatial normalization，并构建 current semantic state、immutable TargetCircuit / TargetIntent、layout store、occupancy、annotation state 与 connectivity state。

Fixture 应尽量模拟真实 Calibre query bundle。允许使用 dummy / synthetic middle files，但它们必须使用与生产路径一致的 schema 与 identity 语义；不应再发明只服务当前 parser 的 convenience JSON 作为 v2 主输入。Dummy / synthetic query fixture 模拟的是 Stage 1 Calibre query evidence，不是 legacy MVP parser input；它必须保存 raw captures 与 normalized YAML，并由同一 parser 生成或校验。

### 5.2 GDS geometry：bbox_by_layer

`bbox_by_layer` 是 v2 MVP **逐 record 证明无损的 axis-aligned rectangle subset** 的 GDS drawn geometry 结构化表示。一个 GDS `BOUNDARY`/`BOX` 的 normalized polygon恰为轴对齐矩形时可连同 record id、layer/purpose、properties与provenance进入该 subset；任意 rectilinear polygon不能只存其包围盒。它必须保留该 subset 内所有 drawn geometry，包括没有 LVS annotation 的 shape，例如 filler、dummy、marker、ESD、waiver carrier、unannotated routing fragment 或 cell-level wrapper。其它 boundary/polygon、PATH、TEXT、SREF/AREF、transform、array/repetition、property，以及 OASIS-specific records，系统必须使用 capability-declared tagged geometry/hierarchy representation、固定 passthrough，或在 Stage 1 typed-fail；不能用 bbox 包络冒充 round-trip geometry。

生产路径中，`bbox_by_layer` 只在所有纳入 record 通过 axis-aligned-rectangle losslessness check 时可由 GDS reader 生成并支持 semantic round-trip。测试路径中也应使用同一 capability/schema，使 parser、layout store construction、annotation overlay 和 exporter regression 共享同一入口。

`bbox_by_layer` 的合同是：

- 记录 element-tagged stream layer key、canonical purpose、optional `drawn_mask_color`、exact bbox与 source record/properties；非矩形 polygon必须进入可保真的 normalized geometry schema，而不是塞入 bbox-only contract。
- 记录或引用 source unit / DBU、exact decoded scale 与第 12.5 节 nominal scale binding。Source integer ticks / drawn geometry 不做 snap：Stage 2 必须在已验证的 scale binding 下选择能精确表示它的 canonical integer DBU，或 typed-fail；snap 只用于把新 candidate 合法化到 tech grid，annotation tolerance 只用于匹配 evidence。Stage 6 写目标 DBU 前必须检查 representability/坐标范围；unit-encoding equivalence 与 geometry quantization 分开记录，任何 policy-allowed coordinate quantization 都要记录 delta，不能用 `int()` 截断或 byte-golden 静默吸收。
- 不附带 schematic identity 的臆测。
- 不因为 LVS query 没有覆盖某个 shape 就丢弃该 shape。
- 不从 `device_info` / `net_shapes` 反向补造 drawn geometry。

GDS geometry 进入 layout store 后，后续 overlay 只能把 `device_id`、`net_id`、`pin_role`、`annotated_mask_color`、coverage marker、conflict marker 等写入 `AnnotationTargetId`-keyed state；shape 仅保留 consensus summary。`drawn_mask_color` 仍属于 geometry evidence，两者按第 4.8 节 reconciliation policy 对齐；不能把 LVS shape 当作新的 geometry truth。

### 5.3 LVS identity：ixref / net_xref

`ixref` 负责 layout instance identity 与 canonical schematic `DeviceId` 的 join。Calibre query 中的 layout instance name 可能是 `M0` / `M1` 这类 LVS 侧命名，而 semantic IR 与 target intent 通常使用 schematic instance name，例如 `MN0` / `MP0`。因此，任何来自 `device_info` 的 layout instance name 都必须先通过 `ixref` 翻译到 canonical `DeviceId`，再进入 annotation state 或 report；join table 不写回 `DeviceIR`。

`net_xref` 负责 layout net / LVS index 与 canonical schematic `NetId` 的 join。内部 net可能被 Calibre renumber 或重命名，因此 LVS index / normalized layout-net identity 只作为 **run-scoped stable evidence key** 和 debug backlink；跨 run / commit 的 canonical key 仍是 cell-scoped schematic `NetId`。

Identity join 的目标合同是：

- `Device.inst_name` 等 semantic IR 字段使用 schematic identity。
- `state.annotation` entry 可以同时保留 layout/LVS identity 与 schematic identity，但必须标明来源；occupancy record 只引用该 entry。
- report 面向工程师时应显示 schematic name，同时保留 LVS index / layout name 作为 debug backlink。
- artifact 文件名、fixture 目录名、tool entry name 或 legacy label 不能覆盖 CDL / LVS evidence 中的 cell、subckt、device、net identity；命名不一致应进入 validation / report，而不是反向改写 semantic IR。
- 如果 `ixref` / `net_xref` 缺失、冲突或无法解释，Stage 2 应产生结构化 annotation error / coverage warning，而不是静默 fallback 到字符串相等或 legacy fixture naming assumption。
- Tool-reported S/D swap、pin role、body tie 等细节应保留为 annotation/provenance；只有 `DeviceExtractionContract` 对该 model/body context声明 terminal symmetry时才可规范化 swap，否则必须保留有序 terminals或 typed-fail。

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

这些 records 必须保留 query 实际返回的 geometry kind、source decimal lexeme/unit 与 `exact | approximate_bbox | untrimmed` quality；经 layer mapping、exact unit conversion、annotation-match tolerance、containment/overlap policy 与 optional effective-region trimming 后，才能 stamp 到 occupant regions。Tolerance 不修改 source geometry。Approximate/bbox-only evidence 不得越过真实边界过度标注；无法分辨时必须 ambiguous/typed-fail。它们不替代 GDS geometry，也不能直接生成 `Net.segments`、`Net.vias`、`Device.fin_track_indices` 等工作状态。

对于 `nfin` resize，`device_info` 可以帮助定位 device gate / bbox anchor；但 active fin attribution 仍应由：

```text
profile-defined effective FIN
  ∩ effective active / OD
  ∩ recognized gate/channel
  → qualified fin/channel crossings
  + DeviceId / gate-stripe / device-reduction grouping
  → per-finger fin count
```

推导，并按 `FinCountSemanticsProfile` 处理 canonical `fins_per_finger / finger_count / multiplicity`与其 model/dialect token映射，同时由独立 `DeviceExtractionContract` 处理 multiple gate stripes及 layout↔schematic device reduction/cardinality；超出 selected capability 明确声明的 mapping/finger-count/device-reduction 子集则 typed-unsupported，而不是由 `device_info` 或 per-device fin list 直接决定。

### 5.5 GDS↔LVS layer mapping

生产 Calibre query 的 layer name 往往不是 GDS layer name。例如 gate recognition layer、S/D derived layer、SADP color layer、effective conducting region layer、cut-shadow-trimmed region 都可能有独立名称。

因此 v2 需要显式的 stream-geometry↔LVS layer mapping，且每个维度只能有一个 authority：`calibre_layer_map.yaml` 是 derived-evidence registry；`layer_map.yaml` 独占 element-tagged stream keys、canonical purpose、drawn-patterning、via `electrical_connects`、cut operator、tier与 edit/lifecycle policy。Loader 必须验证每个 reference 唯一解析，重复或冲突声明 fatal。

- 某个 GDS layer 可接受哪些 LVS / Calibre derived layers 作为 annotation source。
- 每个 derived layer carries 哪些 annotation，例如 `device_id`、`net_id`、`pin_role`、`annotated_mask_color`、well / implant flavour 等。
- via layer 的 `electrical_connects` 与 exact contact predicate，例如 `VIA0` connects `[LI, M1]`。
- cut layer 的 target/effective-geometry operator。
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

### 5.6 Per-region / fragment annotation overlay

目标 annotation home 是 **`state.annotation` 中以 `AnnotationTargetId` 为 key 的 table**；occupancy fragment 只引用它，不拥有 identity fields。Bare `CellId` 只在 atomic-grid capability 内是合法 target。它不是仅 shape-level summary，因为一个 GDS record 可能：

- 被 cut 分成多个连通区域。
- 跨越多个 device 的 diffusion sharing 区域。
- 一部分有 LVS annotation，一部分没有。
- 在不同 cells 上携带不同 net / device / pin role。
- 因 effective-region trimming 与 drawn bbox 不完全一致。

因此，v2 annotation overlay 的 authoritative result 应写到 fragment/region-keyed table，并由 occupancy occupant record 引用。`ShapeRecord.net_id`、`ShapeRecord.device_id`、`ShapeRecord.pin_role` 或 connectivity-local summary 如果保留，只能是 per-region annotation 的可重算 consensus：

- 如果 shape 覆盖的 regions 对某个 annotation field 完全一致，可以汇总到 shape summary。
- 如果 regions 不一致，应保持 unknown / ambiguous，并把细节留在 fragment annotation 与 coverage report 中。
- Planner、constraint、transaction 不应只依赖 shape-level summary 判断物理修改是否合法。

Overlay 流程应至少包括：

1. 读取 GDS geometry，构建 layout store 与 occupancy projection。
2. 读取 `ixref` / `net_xref`，建立 layout/LVS identity 到 schematic identity 的 join table。
3. 使用 GDS↔LVS layer mapping 找到每个 GDS layer 对应的 derived-layer evidence。
4. 以 occupancy spatial index 枚举 A/B-tier candidate regions，再用 exact/quality-aware interval、area overlap、containment 与 tolerance predicate stamp annotation；cell-center 不得作为未证明无损的唯一判据。
5. 若 evidence boundary 穿过 cell、同 cell 有多个 occupant 或 bbox evidence 不能区分 identity，生成细分 fragment或 ambiguous result，禁止整 cell 过度标注。
6. 对 device identity 先执行 LVS layout instance → schematic instance 翻译，再 stamp `device_id`。
7. 对 net identity 保留 LVS index / layout name，并映射到 schematic net name。
8. 处理 conflict / sharing / ambiguity，并生成结构化 coverage report 与 conflict report。
9. 从 per-region annotation 生成 shape-level consensus summary，无法 consensus 时保持 unknown / ambiguous。

Stage 2 的 refs 描述 **source evidence**。ECO 改变 geometry / occupancy 后，Stage 5 必须在同一 transaction 中提交 candidate-derived attribution，或 invalidate 受影响 refs 并标记 `unverified_after_edit`；旧 `device_info` / `net_shapes` 不得静默投影到新 cells。Annotation delta / validity / provenance 进入 checkpoint、ChangeSet 与 snapshot；新的 Calibre output 只有作为下一轮 Stage 1 evidence 重新摄入后，才能替换 source-evidence annotation。

Annotation overlay 只解决 identity association；via / cut / diffusion sharing 带来的 topology association 由 connectivity state 解决。二者共同作用于 occupancy，但职责不同：

```text
occupancy fragment / shape or device region
  + annotation identity references
  + connectivity component
  + component-to-net/device summary
  → localization / DRC / LVS / report 使用的完整解释
```

### 5.7 Conflict、sharing 与 ambiguity policy

Annotation conflict 不能简单按“后写覆盖前写”处理。v2 应区分至少以下情况：

- **正常 co-occurrence。** 例如 gate cell 同时带有 `device_id` 与 gate-net `net_id`，这是正常 gate attribution。
- **Diffusion sharing。** OD / S/D derived layer 上多个 device attribution 可能表示共享 diffusion，应进入 occupancy sharing / connectivity component / pin-role attribution，而不是直接报错。
- **Relation-aware co-occurrence。** 多个 annotated regions 可能属于同一 physical component或 extracted/semantic net；是否允许 spacing exemption 只由具体 RuleRecord 的 relation basis 判断，不能由 overlay 全局决定。
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
- connectivity localization / component-to-identity summary 所需的 annotation references；physical topology 只由 exact effective geometry 与 tech operators 初始化，不由 identity label 建边。

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
5. 在同一 overlay 按依赖顺序 finalise annotation / derived state，并由 constraint engine 检查输入已就绪的 tentative state；只有完整 mandatory closure 通过后，才按 apply_atomicity 发布 CommitEnvelope。

这里的 candidate delta 是“待检查的状态变化描述”，不是事实本身。它可以引用 shape id、cell id、device id、net/component id、old/new coverage、受影响区域和 provenance seed；但在 feasibility 成功之前，不得永久修改 `AuthoritativeState` 的任何 component 或 exporter artifact。

这个边界是 v2 相比 legacy MVP 的关键修正：宏不能先改 `shape_pool`、`grid.b_tier_cells` 或 output JSON，再依赖后续步骤补救；宏只能先提出候选，事务提交成功后才把候选写入唯一权威状态。

### 6.2 `nfin` resize 的物理含义：由 profile 决定

`nfin` 不是脱离 PDK/device model 即可解释的通用几何字段。Canonical model-parameter axes是 `fins_per_finger`、`finger_count`、`multiplicity`（及 profile声明的其它真实参数轴）；`NFIN/NF/M` 等 token的实际含义由 model/dialect profile决定。Gate-stripe grouping与 device-reduction policy/cardinality属于 `DeviceExtractionContract` 的 layout↔schematic mapping metadata，不假定存在对应 CDL token。Stage 2 只有在该 contract能把 target device无歧义映射到受支持的 layout device/group、把 intent解析到明确 canonical parameter axis，并能从 effective geometry复算 `fins_per_finger` 时，才允许相应 resize capability。若首版选择 one-to-one / single-finger / no-device-reduction 子集，则超出该子集的映射在 admission 时 typed-unsupported；是否采用该限制见第 1.4 节。

当选择 `explicit_static_fin_plus_active_window` profile 时，物理操作是：raw FIN 保持不变，planner 修改 profile-declared OD/active window；fin-count extractor先按 effective FIN、effective active与 recognized gate/channel识别 qualified crossings，再按 canonical DeviceId、gate-stripe grouping与 device-reduction policy计算 `fins_per_finger`。邻接 S/D/body attribution只用于 extraction/invariant校验，不作为与 channel相交的计数项。其它 PDK 可能通过 active width、fin block/cut、PCell parameter 或不同 device-recognition recipe 表达 fin 数，必须提供另一 resize operator，否则 typed-unsupported。

Commit 后的 current semantic `nfin` 表示 Layauto已提交 intent；snapshot只有在 publication前 selected trusted extractor覆盖的 invariants复核成功时才标 `extractor_verified`，否则为 `committed_unverified`。该 assurance不等于 extracted-layout↔schematic match；Stage 6 LVS结果进入独立 ValidationResult，不回改 snapshot，下一轮可把它作为 evidence。FIN attribution等仍是 derived views。

### 6.3 固定 cell frame 下的 resize placement model

v2 对 standard-cell 内 `nfin` resize 采用固定 frame 模型：

- cell boundary 不因一次局部 drive-strength ECO 改变。
- VSS / VDD rails、M1 rail locations、rail-side gate endpoints、profile-declared FIN/gate invariants、frame-static well/boundary geometry及 `boundary_halo_signature` 保持稳定。
- Static-fin profile 的 `nfin` shrink / grow 通过调整 device active/OD coverage 完成；其它 profile 不共享该假设，grow 仍须独立 capability admission。
- gap-side shrink 只是特定 cell/profile 可声明的 deterministic candidate-order heuristic，不是普遍物理方向。
- anchor direction 应从几何关系推导，例如 device 与 rail / gap 的相对位置；不应仅依赖 `nmos` / `pmos` 字符串硬编码。
- POLY / gate 在 MVP `nfin` shrink 中通常作为 attribution anchor 保持不动；只有当候选明确证明 gate endpoint、pin access 或 design rule 需要调整时，才规划局部 gate / access 修复。

`boundary_halo_signature`覆盖 tech halo内 raw/effective geometry、pattern/mask、well/select/body与 ports。若 delta触及 halo，必须检查 `AbutmentContextContract`证明完备的全部 neighbour等价类，或在实际完整 tiled context运行 required signoff；cell-alone/少量 representative样本不足，两者不可用则 capability fail。

在声明该 heuristic 的 inverter profile 中，`MN0: 5 → 4` / `MP0: 7 → 6` 可以优先尝试减少靠近 N/P gap 的 active coverage；但 extractor、mandatory DRC、pin access、boundary-halo 与 target invariants 才决定候选是否合法，不能把 fixture 方位写成通用规则。

这个 placement model 只定义初始 v2 的 deterministic policy。将来可以由 search / RL / LLM 或更复杂 router 选择不同合法候选，但这些候选仍必须满足同一事实模型：先规划 OD / access / routing 的 state delta，再经 constraint 检查后提交。

### 6.4 Profile-scoped resize candidate 内容

Resize planner 至少应显式处理以下问题：

- selected profile 的 raw/effective FIN、active、gate/channel 与 fixed-frame invariants。
- fin-count extractor 对 old/new effective geometry的 `fins_per_finger` 结果、canonical size axes到具体 CDL token的 mapping，以及独立 gate-stripe/device-reduction extraction metadata。
- 新旧 effective active coverage 对 committed semantic `Device.nfin`、device/terminal attribution、diffusion sharing、split diffusion 与 assurance 的影响。
- 被 OD shrink / grow 影响的 S/D LI bars、via coverage、M1 stubs 与 local net connectivity。
- 受影响区域内是否存在 unannotated blockage、raw/effective cut、policy-controlled marking或 signoff-only risk。
- publication 前需要按 layer lifecycle preserve / compare / finalise 的 policy-controlled geometry。
- publication 前需要刷新或 invalidate 的 read views，例如 fin attribution、gate tracks、segments、vias、annotation coverage、net-to-component summary。

Static-fin 候选 profile 的 resize candidate 不应包含 raw `add FIN` / `remove FIN` 或 fin/gate-targeting cut edit。其它 representation 只有在独立 capability 给出 operator、完整 extraction invariant 与 mandatory checks 时才可编辑相关 geometry；否则应判定 unsupported 或要求更高层 cell regeneration。

### 6.5 Routing、via、cut 与 derived markings 的局部修复

OD active coverage 改变可能连带影响多类局部对象：

- S/D LI bars 的长度、端点或覆盖关系。
- VIA0 / local via 的 enclosure、连接关系与可保留性。
- M1 stubs 或更高 routing 的局部连接。
- cut operator 对 effective geometry、connectivity component 与 device recognition 的影响。
- policy-controlled layer 的 preserve/frame/derived 处理，例如 tech-declared well、boundary、VT/implant family。
- DRC / LVS localization 所需的 annotation summary 与 provenance。

这些修复应遵循同一个边界：

1. planner 从 candidate 的 old/new state delta 中计算受影响区域。
2. constraint engine 基于 occupancy、connectivity、blockage 与 rule predicates 判断局部修复是否可行。
3. transaction 在 private overlay中 materialize concrete repair；actual geometry/effective-operator delta独立更新 physical connectivity，annotation refresh/invalidation request只生成 tentative identity/relation state与对应 checks。
4. derived finalization / view invalidation 完成后，再随同一 CommitEvent 原子发布 authoritative state。
5. Stage 6 只从 committed snapshot 导出 artifacts，不临时补 bbox，也不把 L1 EditOp replay 当作事实落点。

Routing / via 修复不应依赖“同名 net label 就等价”的 shortcut；rule predicate 必须使用自身声明的 relation basis。Semantic/extracted net、physical component、voltage/mask property 是不同输入；缺少所需 context时按该 rule的 `missing_context_policy` fail/defer，或仅在绑定具体 fallback relation/value与单调安全 proof时 conservative fallback。不为 per-cell `net_id` label 设计兼容层。

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
- `operand_ref`：默认只使用 run-stable semantic id 或 snapshot-independent declarative locator。若 raw intent 锚定 shape/component，必须同时记录 origin snapshot，并在每轮 replan 经 lineage + current exact geometry 重新解析；一对多、无匹配或歧义 typed-fail。Snapshot-scoped `ShapeId` / `ComponentId` 只进入该 snapshot 的 CandidatePlan。
- `semantic_before` / `semantic_after`：参数变化、topology 变化或 connectivity intent。
- `scope`：single device、single net、single cell、bounded region 等。
- `hard_constraints`：必须满足的约束，例如固定 rail、固定 boundary、不可移动 shape、avoid region。
- `preferences`：可排序偏好，例如 gap-side shrink、少改动、低 via count、保持 pin access。
- `required_capability`：该 delta 需要哪个 planner / macro capability 覆盖。
- `provenance`：从哪些 evidence、annotation 或 diff 规则产生。

Stage 4 必须先对全部 target delta 做 **all-delta capability admission**：只要存在 unsupported delta，整个 planning result 默认失败，不进入 Stage 5；不能像 legacy MVP 那样在 dispatch 表中把无 macro 覆盖的 diff 静默过滤。执行原子性由独立的 `apply_atomicity = whole_intent | dependency_group | candidate` 决定，默认 `whole_intent`。未来如果需要 partial apply，必须由显式 policy 打开，并在 report / validation result 中标记 skipped / already-applied delta、风险与 non-production / requires-review outcome。

若 semantic/extraction-aware diff 证明全部 target delta 已在 current snapshot 满足，Stage 4 返回本迭代的 `NoChangePlanningResult`，不生成 candidate或 ProposedMutationSpec。Pipeline 只有在本 attempt 尚未发布 envelope 时才按第 2.7 节 run-wide no-change success 处理；已有 partial chain 时则保留该链、复核 target closure 并关闭 changed partial success。

### 7.2 Planner / macro interface

Planner 的输出是 `PlanningResult`，而不是 edit stream。每份 planning result 绑定一个 base snapshot、包含一个 publication group 的候选 alternatives；partial chain 中每个新 snapshot 都对应一份新的 PlanningResult。一个 planning result 应包含：

- candidate plan 列表，通常按 delta 或 dependency group 组织。
- `state_lineage_id`、`base_snapshot_id`、candidate read-set/old-state preconditions、idempotency key 与 `apply_atomicity`。
- deterministic-ordered fully-ground/dependency-closed plan-group alternatives 与 selector/tie-break metadata。
- unsupported delta 列表。
- planning warnings，例如 evidence 不完整、annotation coverage 降级、候选空间被 policy 缩小。
- required checks，例如 DRC、connectivity、blockage、same-component、pin access、derived refresh。
- affected regions，例如需要重算 occupancy、connectivity、derived marking 或 annotation coverage 的区域。
- expected validation assertions，例如 “selected profile invariants”、“committed fin-count intent matches target”、“trusted extractor/LVS assurance status”、“affected net remains connected”。
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
- connectivity effects：可能新增/删除的 component/via edge、cut-operator result、diffusion terminal sharing relation。
- repair requirements：受 resize 影响的 LI / VIA / M1 / cut / derived marking 修复需求；可执行 candidate 必须已解析成 concrete sub-candidate。
- finalization scope：policy-controlled geometry lifecycle、annotation attribution/validity、read/export views 的刷新或 invalidation 范围。
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

第 7.3 是第 7.2 通用 planner contract 在 v2 MVP `nfin` resize 上的特例化。Resize planner 不重新定义物理语义；它必须遵守第 6.2–6.5 的 selected FinCount/DeviceExtraction profile、fixed frame/boundary halo与局部 repair 边界。

对于一个 `Device.nfin: old → new` delta，推荐映射为：

- `TargetDelta`：device parameter resize，operand 是目标 `device_id`，semantic delta 是 `nfin old → new`。
- `PlanningTask`：single-device resize task，记录 policy、scope、dependency 和 required capability。
- `MacroPlanner`：resize planner，根据 semantic IR、layout state、occupancy、connectivity 和 annotation references 生成候选。
- `CandidatePlan`：一个或多个 old/new OD coverage candidate，附带 affected occupancy、connectivity effects、repair requirements、required checks、candidate ranking metadata 和 provenance。
- `RepairRequirement` / `SubCandidate`：LI / VIA0 / M1 / cut / derived marking 的局部修复需求，或已经具体化的 repair sub-candidate。
- `ProposedMutationSpec`：Stage 5 可消费的 fully-ground current-semantic update、geometry/occupancy delta、connectivity expectation、annotation request与 lifecycle dirty-scope hint；planner不能直接指定 authoritative annotation value 或 derived shape。

在 static-fin profile 内，resize candidate 不应包含 `add FIN` / `remove FIN` 操作。FIN attribution、gate tracks、segments、vias、annotation coverage 等应作为 committed state 的 derived views 重算；planner 不应把这些派生视图作为长期可变字段直接改写。

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

Stage 4 输出的 `PlanningResult` 是下一次 Stage 5 feasibility / transaction 的输入；partial policy 每发布一个 envelope 就返回 Stage 4 生成新结果。Default whole-intent在唯一 publication前把本轮中立 planning/constraint audits冻结入 RunRecord；partial/no-change在全部 Stage 4↔5 迭代结束、`close_stage5(...)` 前按序冻结。Stage 6不直接读取 live PlanningResult。

接口关系如下：

- Constraint system 消费 proposed delta / context，并独立从 tech / layer / action policy 推导 mandatory checks 与 expanded affected scope；candidate 的 required checks / region 只是附加 assertion / hint。
- Transaction system 把 `ProposedMutationSpec` 映射为 staged changes；检查和 finalization 成功后按 `apply_atomicity` 原子发布 authoritative state。
- Commit 后产生 `ChangeSet` / `CommitEvent`，而不是把 Stage 4 candidate 本身当作 committed geometry。
- Export / validation / reporting 从 final immutable snapshot、ordered ChangeSet / CommitEvent chain 与 frozen RunRecord 中的 planning provenance 生成 artifacts、report 和 validation result。
- Candidate、ChangeSet、ExportEdit 三者必须分层：candidate 是计划，ChangeSet 是已提交事实，ExportEdit 是 artifact-specific 派生产物。

这个边界保证：规划可以产生多个候选和失败解释；约束系统可以拒绝候选且无副作用；成功提交会更新权威状态；导出阶段只读取 committed snapshot，不再补写 architecture state。

## 8. 约束系统与可行性检查

第 8 节定义 Stage 3 / Stage 5 中“候选是否合法”的判断模型：occupancy 是离散 broad-phase/working基底，exact effective geometry与 rule-declared relation 是 final predicate truth，constraint engine 只叠加 domain/solver trail/rule predicates，不拥有另一份版图状态。

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

- `feasible | infeasible | indeterminate | error`；只有 `feasible` 可提交，timeout、resource limit、predicate unavailable 不得冒充 infeasible 或 feasible。
- violation list。
- affected cells / neighborhoods。
- propagated domain changes。
- connectivity delta / refresh request。
- immutable `ConstraintResult` / requested neutral delta；不得返回可写 transaction object、callback 或 transaction-private trail entry。

有效检查集必须是 `tech/layer/action policy` 推导的 mandatory checks 与 candidate intent-specific assertions 的并集。Scope seed 是 old/new geometry footprint 的并集，随后按 rule halo、whole touched shape/entity、via/cut/enclosure partners、pre/post connectivity components、body/boundary context与 derived dependency closure 扩张；shrink/delete 不能只看 new footprint。无法证明有限闭包时，mandatory rule 必须 full-check 或 capability fail。Candidate 自报字段不得关闭 predicate 或缩小范围。

v2 目标合同是：constraint engine 可以维护 solver-local domain、trail、propagation queue、局部 rule cache 和 checkpoint metadata，但不能维护一份独立的 layout occupancy truth。ConstraintContext 必须绑定 `base_snapshot_id`，publication 后旧 trail/checkpoint 不得复用。Transaction-private overlay/journal 负责所有持久 component rollback；solver trail 只回滚本次 attempt 的 domain/queue/cache。Engine 以 occupancy id/fragment ref 叠加 working state，候选提交仍由 transaction 保护。

因此，constraint engine 的 cell state 应尽量缩小为候选检查需要的状态轴，例如 empty / occupied / barrier / fixed / candidate marker，以及必要的 rule-local width / line-end metadata。Occupant kind、shape reference、semantic net/device identity 属于 occupancy store 或 annotation / semantic IR，不应长期复制到 engine state。

### 8.2 Legacy CSP 中应吸收的 modeling / propagation 机制

Legacy MVP 的 CSP 实现虽然在状态所有权和 `net_id` 建模上不符合 v2 目标，但其中有几类机制是 v2 可以且应该吸收的。吸收方式不是复制当前对象结构，而是保留其算法合同并换到 v2 的 store / connectivity / transaction 边界上。

应吸收的部分：

- **规则模板化。** 现有 DRC rule 使用 stencil / trigger / forbidden 的模式：某个确定 cell 状态触发规则，然后在邻域 stencil 内剪掉非法状态。v2 可以保留这种 rule predicate 组织方式，但 forbidden 的判定应从 `CellState(net_id)` 集合剪枝，改为查询 occupancy / connectivity / geometry context。
- **Sound propagation。** 每个 propagator 声明 wake condition 与 sound-pruning contract；singleton/determined-only propagator 是可保留的模板子集，但 bound/domain propagator 也可从 non-singleton domain 安全剪枝。传播 fixpoint 或非空 domain 本身不证明存在可行解。
- **队列式局部传播。** queue 可从 changed cell/fragment 做局部 cascade；范围由 rule dependency、affected closure 和 connectivity delta 限定。是否增量检查必须由 predicate 的 soundness contract 决定，不能以性能偏好漏检。
- **分层 trail。** 可逆 trail 的思想可用于 solver-local domain/queue/cache；所有 authoritative component 的 staged mutation与 rollback 由 transaction overlay/journal 拥有，不能混成一个 constraint checkpoint。
- **proposal API。** ProposedMutationSpec 由 transaction-private `MutationSink` materialize为 staged geometry/occupancy；constraint只读该 view。Proposal可能失败并由 transaction overlay整体丢弃，不写 engine occupancy copy。
- **deterministic commit delta。** ChangeSet从 transaction journal而非 solver trail汇总，按 canonical identity稳定排序并记录可审计 old/new。
- **fixed / conservative conflict。** Unannotated geometry、blockage、raw cut与 fixed frame不能被候选静默覆盖；cut的实际 barrier/effective effect仍由 tech operator计算，不能靠 singleton label代替。
- **可逆 connectivity trail。** No-compression reversible union-find 只适用于 additive overlay/rollback新增 merge。Edge removal、cut effect或 terminal split必须从 final staged effective-geometry graph做 affected-component canonical rebuild，或使用真正 fully-dynamic transactional structure；结果不得依赖 mutation应用顺序。
- **传播统计。** legacy `propagate_stats` 记录按 seed layer 聚合的 calls / visited cells / time。v2 应保留类似 observability，用于发现 rule 或 layer 的传播热点，并把它纳入 validation / performance report。

不应吸收的部分：

- 不吸收 per-cell `CellState.net_id` 作为 same-conductor 判据。
- 不吸收 `occ_type × net_id` 的 domain 展开。
- 不吸收 engine 自己长期持有 occupancy copy 的所有权模型。
- 不吸收 VIA0 通过 LI/M1 wire double-stamp 伪造跨层连通的做法。
- 不吸收 `net_id=None` 彼此兼容的乐观 spacing 语义。

因此，v2 的 constraint engine 可以使用“模板化局部规则 + sound propagation + solver-local reversible trail”的算法骨架；但 Stage 5 只接受 fully-ground、无未决选择且 dependency-closed 的 `ProposedMutationSpec`。Propagation 仅作 pruning / early conflict，final overlay 必须由 exact evaluator 逐项检查全部 mandatory predicates；若未来允许 non-ground candidate，则必须另行定义 branching/backtracking/search，否则该 candidate non-executable。

### 8.3 Rule records 与 predicates

Rule deck 应使用结构化 rule records 表达 min width、spacing、pitch、enclosure、extension、exact size、coloring、cut / barrier、via relation 等规则。Constraint engine 消费其中可在 candidate 阶段判断的 subset。

Rule predicate 的输入应是明确的上下文对象，而不是散落读取 artifact 或 legacy working representation：

- coordinate context：layer、track axis、pitch、width、orientation、B-tier axes。
- occupancy context：某 cell / neighborhood 是否被占用、被何类物理对象占用、是否 fixed / blockage / barrier。
- geometry context：exact effective geometry、shape/fragment coverage、enclosure / overlap / extension；grid/bbox 只作 broad phase，除非 predicate capability 已证明无损。
- connectivity/relation context：exact topology component及 rule-declared extracted/semantic net、voltage、mask等 relation inputs；cut/via 必须使用 tech operator。
- annotation / semantic context：用于报告、localization、intent policy或 RuleRecord显式要求的 relation input，不是全局默认判据。

对 capability 已声明支持、且 candidate触及的基础局部规则，Stage 5必须用 exact evaluator检查，包括 spacing、via enclosure、cut-effective geometry、OD terminal sharing/spacing与 blockage。缺 predicate或闭包证明时 admission失败。复杂 coloring/density/deck-derived规则可明确为 signoff-only。

对 `nfin` resize，Stage 5 还必须执行 intent invariants，而不能把它们只留作 Stage 6 expectation：selected extractor 对 parent/candidate 得到的 `fins_per_finger` 分别等于 `semantic_before/after`；`finger_count`、`multiplicity`等**未被该 intent改变**的正交 model-parameter axes保持；layout↔schematic device-reduction cardinality按独立 extraction invariant保持；effective channel/device cardinality、profile-declared FIN/gate/frame/body/boundary halo invariants保持；未受影响 device的 count/topology不变；touched pin/device reachability满足 intent；具有冲突 annotation的 components不得被合并。DRC feasible但 intent invariant失败的 candidate仍不可提交。

### 8.4 Occupancy-aware DRC

DRC 使用 occupancy 作 spatial index、使用 exact effective shape geometry 作 final truth，而不是直接基于 derived views 或 output JSON。离散 cell predicate 只有在 tech capability 对该 rule family 证明 conservative/lossless 且无 false negative 时才可独立给出 clean；否则 spacing、enclosure、min-area、line-end等必须运行 continuous-geometry exact evaluator。

CSP-frontline 至少应覆盖这些局部规则族：

- same-layer spacing / adjacent-track spacing。
- min width / exact width / line-end 与 extension 检查。
- via enclosure、via-to-wire overlap、via stack relation。
- cut operator 对 effective geometry/connectivity/device recognition的影响。
- OD spacing、diffusion sharing、split diffusion 的局部合法性。
- blockage / fixed geometry conflict。
- policy-controlled layer 的 preserve/frame/derived lifecycle与 actual delta触发的 mandatory checks。

Occupancy-aware DRC 的正确状态依赖第 3、5、9 节定义的单一状态所有权：candidate 在 Stage 5 transaction 中 staged 到 occupancy / layout store 后检查，成功后提交到同一个 authoritative state。不能出现“engine 接受了候选，但 shape_pool / layout_store 仍是旧 LI/M1 几何，导出靠 decoder patch”的状态漂移。

### 8.5 Rule-declared relation reasoning

Same-net spacing exemption 不应简单比较 cell 上的 scalar `net_id`，也不能普遍等同于“同一物理 component”。Foundry/project rule 可能要求 physical component、extracted net、schematic net、voltage class、mask property 或完全不允许 exemption；每条 RuleRecord 必须显式声明 relation basis。

这样可以避免：

- same net label 但物理 disconnected 的对象被错误放宽。
- unknown / unannotated geometry 被乐观处理。
- via-as-wire 多重表示被用于伪造跨层连通。
- cut / barrier 已经切断几何，但 label 仍让 rule 误以为连通。

Connectivity index 应由 exact effective geometry 建立，occupancy 只作 broad phase；至少包含：

- same-layer tech-declared contact-predicate edge（明确 overlap/edge/corner 与 mask/purpose条件）。
- VIA / contact 与上下层 effective conductor 的 qualified overlap/contact edge。
- CUT operator 作用后 geometry 对 edge 的删除/禁止。
- gate/channel 分隔后的 S/D terminal regions、OD sharing/split 与可选 body-region graph。

Net label可用于报告/LVS和 explicit predicate。RuleRecord同时声明 `required_relation_assurance`；例如 `same_extracted_net` 只能由绑定当前 exact region、仍有效的 matched extractor evidence满足，candidate-derived semantic label或 `unverified_after_edit` 不能冒充 extracted relation。缺 context或 assurance不足时按该 rule的 `missing_context_policy` fail/defer；只有绑定单调安全 proof与 fallback relation/value时才可 conservative fallback，不能全局假设“不应用 exemption”必然安全。

这个修订与 backlog 中的 M11 方向一致：legacy union-find 不应只是测试覆盖的附属设施，而应成为 spacing / connectivity rule 的生产消费者；跨层连通必须通过 via edge 表达，而不是依赖 VIA0 被同时伪装成 LI/M1 wire。

### 8.6 Domain model 与 propagation 边界

Legacy MVP 的 domain 按 `occ_type × net_id` 展开，会制造大量不可达或无意义状态，例如 CUT 带 net 的组合，并使 domain 大小随 net 数增长。v2 不应继承这种 domain 设计。

v2 的 domain model 应遵守：

- domain 只表达候选检查真正会分支或传播的状态轴。
- semantic `net_id` / `device_id` 不进入 per-cell domain；它们属于 semantic / annotation / component summary。
- occupant kind 优先从 layer / occupancy record 得到；只有同层确实存在多种合法 occupant kind 时才进入 domain。
- Raw CUT 是 occupancy/index record与 effective-geometry operator输入，不是带 net fan-out的可选状态或通用 barrier。
- unknown/unannotated只表示 identity未知，不得改变 exact-geometry connectivity；它仍按 tech contact predicate并入 physical component，同时把 component identity标为 unknown/suspect。需要 identity/relation的 predicate按 missing-context policy处理。

Propagation 的职责是对 staged candidate 做 sound pruning 和冲突发现，不是替代解搜索或 final verification。当前架构以 planner 提出 fully-ground candidate、engine 检查为主；若 candidate 仍有未决 domain，必须进入另行定义的 search/branching，或返回 non-executable。`ConstraintResult=feasible` 只在 exact mandatory evaluator 全部完成后产生。

### 8.7 CSP-frontline rules 与 signoff-only rules

v2 应区分：

- **CSP-frontline rules。** 修改候选必须立即满足，例如 exact local spacing、via enclosure、blockage conflict、cut-effective geometry、OD terminal sharing/split、fixed boundary halo与 selected profile invariants。
- **Signoff-only rules。** 需要完整 foundry DRC/LVS 或复杂 coloring / density / full derived-layer deck 才能判断的规则。
- **Deferred rules。** 目标架构已留接口，但当前实现暂不覆盖，需要在 validation report 中说明风险。

Validation report 必须说明哪些规则在 CSP-frontline 检查，哪些交给 signoff，哪些被降级或跳过。对于被降级或跳过的规则，report 应记录原因：缺少 PDK deck、缺少 Calibre runtime、fixture 不覆盖、当前 planner scope 不支持，或该规则本身属于生产 signoff-only。

### 8.8 Rule gaps 与 correctness highlights

v2 开发应特别避免继承 backlog 已经指出的 correctness gaps。第 8 节相关的重点包括：

- 在 selected static-fin profile 中，raw `add FIN` / `remove FIN` 及未经 capability许可的 fin/gate-targeting cut edit应被拒绝；其它 PDK representation 不得套用该结论。
- VIA0 不应同时作为独立 via、B-tier occupancy、LI/M1 wire 多重表示；via enclosure 与跨层 connectivity 应从统一 occupancy + via edge 判断。
- LI / M1 的 committed 几何必须写回 authoritative state；不能只在 engine 或 EditOp stream 中存在。
- Raw `net_shapes` / `device_info` 是 annotation evidence，必须经过 layer mapping、effective-region tolerance 和 identity translation；不能直接当作完整几何事实或 rule truth。
- Missing annotation不能制造 disconnected component；exact connectivity照常建立，identity标 unknown/suspect，relation-dependent rule fail/defer或使用带 proof的 declared fallback。
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
- commit log / ChangeSet / CommitEvent / per-publication CommitAuditRecord append；default whole-intent的 run-level RunRecord在唯一 group publication前冻结，explicit partial/no-change的 RunRecord在所有 groups结束后的 stage5 closure前冻结。

Transaction 的核心 staged object 是 `StagedStateView` 上的 state delta，transaction owner 不是 constraint engine 本身。Constraint engine 只消费 query-only staged-view，维护 solver-local trail并返回 immutable rule result；transaction-private mutation sink/checkpoint 不暴露给 constraints。真正的 commit 目标是整个 `AuthoritativeState`。

OD/VIA/CUT/diffusion变化都服从同一事务边界；必须在同一 overlay stage/validate exact geometry、occupancy fragments、annotation、component/via edges、cut-effective result、current semantic、lifecycle scope与 ChangeSet，不能只改 bbox/grid/helper/artifact。

标准顺序是：

1. 接收 fully-ground selected plan group / `ProposedMutationSpec`，校验 `state_lineage_id`、`base_snapshot_id`、old-state preconditions、idempotency key 与 `apply_atomicity`。
2. 从 parent snapshot 打开 transaction-private overlay / checkpoint。
3. 在 overlay 中 materialize proposed geometry、occupancy与 current-semantic changes；由 exact effective geometry和 tech operators重建/更新 physical connectivity，annotation algorithm根据 refresh/invalidation request生成 tentative `AnnotationState`与 relation assurance，形成对外不可见的 tentative base state。Annotation不得增删 physical edge/component。
4. 从 old/new footprint 独立推导 mandatory checks / affected closure：rule halo + whole entity + via/cut/enclosure partners + pre/post components + body/boundary/derived dependencies；无法证明局部闭包时 full-check 或 capability fail。Sound propagation 与 early exact checks 只消费输入依赖已就绪且未标 dirty 的 state；依赖待刷新的派生几何/annotation 的 intent invariants、rule predicates 和 repair checks 保持 pending。
5. 若任一有效 early check 失败，丢弃 overlay / restore checkpoint，并返回 typed failure；不得因 dirty/stale dependency 的旧值而提前拒绝 candidate。
6. 在同一 overlay按显式、versioned dependency DAG finalise annotation attribution/validity与逐层 policy-controlled geometry，再执行其消费者。任一 actual delta都标记并按拓扑序重算其下游：annotation、exact device/body extraction、effective conductor、physical connectivity、relation assurance、solver/component summaries与 read views。Annotation变化只影响 identity/relation消费者，不改变 physical topology。
7. 从每次 actual final delta重算 affected closure，执行所有 pending mandatory checks 并重跑受影响的 intent invariants与 mandatory DRC predicates，直至 DAG无 dirty/pending node且全部检查通过。只有有 termination/unique-result proof的 bounded fixed-point contract可处理声明 cycle；闭包不可证明时全量重算或 capability fail。仅有 dependency proof确认不参与 extraction/body/connectivity/relation/rule消费者的 marking可 late-finalize。
8. 比较 old/new base、annotation与所有 final state，生成完整 ChangeSet。
9. 若 finalization 或 post-check 失败，必须丢弃 overlay / restore parent snapshot，并返回 typed failure。
10. Default whole-intent用 deterministic ids冻结 neutral PreparedPublication与唯一 RunRecord，再调用 `PublicationRepository.publish_whole_and_close_stage5(...)`；repository重验 state/attempt revisions与 preconditions，并以一次 ACID commit或 composite-root CAS让 immutable siblings、state head与 stage5 closure可见。Explicit partial policy则调用 `append_partial(...)`，发布后由 pipeline返回 Stage 4，以新 snapshot规划 remaining delta；Stage 5不复用或 rebase旧 candidate，全部 groups结束后才冻结 RunRecord并调用 `close_stage5(...)`。Stage 6只能读取 stage5-closed attempt。

默认 changed whole-intent只有一个 CommitEnvelope，final RunRecord与它通过同一 repository root publication可见；`no_change` 的 chain为空、复用当前 snapshot并经 `close_stage5(...)` 可见。Explicit partial policy可以先发布多个 envelopes；final RunRecord freeze failure不回滚已发布 envelopes，而是发布 `Stage5Closure(run_record_freeze_failure)`、阻止正常 Stage 6 export并 terminal reject。

Planner / macro 不能直接修改 committed layout store、`shape_pool`、B-tier occupancy、semantic device/net state 或 output artifact。它们只能产生 candidate / `ProposedMutationSpec`。任何需要持久修改的内容，都必须通过 Stage 5 transaction 发布到 authoritative state。

### 9.2 Commit to authoritative state

Commit 的目标是 authoritative layout state。成功 publication 后，后续 planner/constraints/read-view/exporter读取同一 repository head/snapshot；policy-controlled finalization已在 publication前完成。

`AuthoritativeState` 是一组有明确 component ownership 的 committed state graph。实现可以拆分 immutable storage object，但只有 `PublicationRepository` 拥有 lineage head与 RunAttempt pointers；process-local MVP至少用 single-writer publication mutex + compare-and-swap。Crash-durable profile必须用提供 durable commit语义的单一 ACID transaction/WAL，或先 durable写入 content-addressed immutable siblings、再对同时包含 state head与 run-attempt index/revision/pointers的 **一个 composite repository root** 做条件 CAS；local-FS路径执行 sibling/root file与 parent-directory fsync，object-store路径要求 durable immutable writes、read-after-write consistency与 single-root linearizable CAS。否则只能声明 process-local/best-effort。Object-store两个 key的独立 conditional write或 local-FS依次替换两个文件都不够；只冻结名为 `CommitEnvelope` 的 Python object也不构成原子 publication。

一次成功 commit 必须满足：

- geometry store 与 occupancy state 对同一物理对象给出一致 old/new。
- B-tier occupancy、A-tier occupancy、annotation 与 connectivity state 同步更新；rule-domain / cache 只需刷新或明确失效，不成为持久 truth。
- current semantic `Device` / `Net` state反映已提交 intent，并携带 publication-time `committed_unverified | extractor_verified` assurance；Stage 6 LVS status留在独立 ValidationResult。Physical pin-role attribution留在 AnnotationState，diffusion sharing留在 occupancy/connectivity，Target不改写。
- policy-controlled geometry 已按 preserve/frame/derived lifecycle 处理，并通过由实际 delta 触发的 post-finalization predicates。
- derived read views 已刷新或明确失效，不能被后续阶段静默读取为 truth。
- 下一次 macro / planner 在同一 pipeline run 中读取到本次 commit 后的状态，不需要等待 Stage 6 decoder replay。
- ChangeSet / CommitEvent 已记录足够 old/new identity，使后续 ExportEdit、report、validation 和 debug 不需要把 L1 edit stream 当作几何事实源。

v2 可以复用 legacy MVP 中职责边界清楚、且不违背上述状态所有权的局部实现，例如稳定排序、纯 bbox 转换函数、可回滚 trail 的算法思想、纯导出 helper。凡是依赖 output replay、pre-commit side effect、独立漂移状态或 `EditOp` 作为唯一几何事实的实现，都不属于 v2 commit architecture。

### 9.3 Rollback consistency

失败回滚后必须保持一致：

- geometry 没有 partial tagged-geometry / hierarchy / property 或 bbox-index change。
- occupancy 没有 partial assign/release。
- annotation state 没有 partial attribution、stale-valid marker 或丢失的 invalidation。
- connectivity 没有残留 union、via edge、cut-effective geometry或 diffusion terminal sharing/split state。
- current semantic state 没有 partial parameter、device、pin 或 net update。
- derived geometry 没有 partial refresh 或 provenance stamp。
- derived read views / caches 没有 stale exposure。
- commit log 不记录 successful commit event。
- output artifact、ExportEdit、SKILL、report、validation result 不以失败 candidate 的 partial state 为输入。

Rollback 的判断基准是 `apply_atomicity` 对应的 parent plan-group snapshot，而不是某一个内部对象的 checkpoint。只恢复 constraint engine cells 不足以构成 rollback；layout store、occupancy store、annotation state、current semantic state、connectivity index 和 derived state 都必须恢复或未曾被持久修改。

失败 candidate / plan group 可以产生 diagnostic event，例如 `PlanningFailure`、`ConstraintFailure` 或 `TransactionRollbackEvent`，并在 Stage 5 终止时冻结到 failure RunRecord 用于 debug 和报告；但它们不是 CommitEvent，不能被 Stage 6 当成 committed delta 导出。若失败点正是 `run_record_freeze`，则按第 2.7 节唯一例外只保留 StageFailure + completed neutral audit refs。Partial-policy run 已有的 earlier CommitEvents 仍有效，必须与 failed delta 分列。

### 9.4 Policy-controlled geometry finalization

Tier C1 layer 逐项使用 `preserve_drawn | frame_static | prepublication_derived` lifecycle。NWELL、BOUNDARY、VT、PP、NP、DNW 等名称本身不决定哪一种：只有绑定 generator/version/dependencies/context/dirty-scope/equivalence comparator 的 layer 才能称为 derived；其余默认 preserve 或 frame-static。

如果 dependency proof确认某类 C1 derived marking不参与 device/body extraction、effective conductor/connectivity、relation context、intent invariant或该 action的 mandatory rules，它不需要在 candidate staging的每一步都实时维护；否则必须位于相应消费者之前。v2 的默认模型是 dependency-ordered final derivation：

1. Stage 5 在 transaction-private overlay中 materialize tentative base geometry、occupancy与 current semantic state，并形成 initial annotation/extraction/connectivity state；此时尚未 commit/publish，初次检查也不是最终 closure。
2. Preserve layer 与 source/parent 做 exact semantic equality；frame-static layer 与 boundary-halo signature 比较；derived layer 才从 declared dependencies/context 重算。
3. Actual preserve/frame/derived delta与上一版比较，并据此沿 dependency DAG扩张 affected closure；重算 downstream annotation、device/body extraction、effective conductor/connectivity与 relation assurance。Physical topology只响应 geometry/effective-operator delta，不响应 annotation label本身。
4. 对全部 downstream delta触发的 intent invariant、spacing/enclosure/boundary/body/relation/context rules运行 mandatory post-finalization predicates，直到 DAG stable；无法证明局部/contextual closure时全量重算或 unsupported。
5. Base delta 与 final policy-controlled delta 一起进入 ChangeSet/CommitEvent；全部一致且检查通过才可发布。

Certified derivation 可以是全量 recompute，也可以是有完整 dependency closure 的 incremental recompute；无法证明闭包时必须全量重算或 capability fail。关键要求是 deterministic、可重算、可比较、可审计。

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
- state lineage、parent/new snapshot、commit/run ids、timezone-aware UTC timestamp 与 tool/environment provenance；timestamp 不进入 semantic content identity，除非 schema 明确隔离。

ChangeSet 应具备稳定排序和可审计 old/new state。Candidate/rule/seed/neighbour/queue/connectivity rebuild 与 persisted collection都使用 canonical key/tie-break id；禁止依赖 set iteration、由 set 构造 dict 的顺序、equal-priority object comparison或 Python hash。编码/hash前显式排序。

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

Stage 6 不能重新解释 raw target diff，不能读取 mutable transaction overlay，不能把 output artifact 当作 state source，也不能把生产工具输出直接 patch 回 layout state。Stage 1–5 的 no-publication failure（本 run 尚无 CommitEnvelope）只允许从 failure RunRecord + optional last-stable-snapshot ref 生成 diagnostic report，不允许 geometry export；已有 earlier envelopes 的 partial-policy terminal failure 仍按第 2.7 节 policy 处理。Stage 5 已关闭后的 Stage 6 failure 保留既有 frozen RunRecord，不能仅凭 commit chain 是否为空选择 failure variant。`run_record_freeze` exception 则直接从 StageFailure + completed neutral audit refs 生成 diagnostic report，同样不得进入正常 Stage 6。Legacy MVP 中符合 v2 边界的 GDS IO、CDL writer、Calibre query parser、可视化 helper 或测试 harness 可以按职责复用；不符合 v2 边界的 edit-stream writeback、output-side patch、placeholder SKILL、stdout-only validation 等路径应重构或删除，不设计兼容 adapter。

### 10.1 Stage 6 no-mutation boundary

Stage 6 是对 Layauto `AuthoritativeState` 的只读边界。它不允许修改 current semantic、geometry、occupancy、annotation、connectivity、derived markings 或 read-view version metadata。这个边界保证纯 artifact generation 可重跑、可比较、可审计；显式启用的外部 SKILL apply 另按 production-integration policy 管理其副作用、幂等与 undo，不改变该内部只读合同。

Stage 6 禁止：

- 修改 AuthoritativeState 的任何 component。
- 在 export 过程中运行或补跑 policy-controlled geometry finalization。
- replay legacy MVP edit stream 来生成 canonical geometry。
- 根据 Stage 1 target diff globals 临时修改 output params。
- 根据 output JSON / GDS / SKILL 反向修补 committed state。
- 把 validation mismatch 静默降级为 stdout。
- 把 skipped / deferred / error，或 coverage-degraded / environment-limited 检查汇总成 required-scope clean / production pass；已完成子范围的 pass 必须保留覆盖限制。

如果 Stage 6 发现 snapshot 缺少 policy-controlled geometry lifecycle result、authoritative AnnotationState、geometry identity/capability，frozen tech context缺少 stream-layer/unit/dialect mapping，或 commit chain缺少 expectations，应在对应 subphase typed-fail。缺失/stale non-authoritative summary可纯重算，但不得写回 snapshot。

Policy-controlled geometry已在 Stage 5 repository publication前 preserve/compare/finalise并检查；Stage 6只序列化 snapshot中已有 geometry，不运行 writeback/derivator补丁。

### 10.2 GDS / JSON / CDL export

Exporter 应从 immutable snapshot、由 snapshot / RunRecord ids 解析出的 frozen versioned tech context，以及 export policy 生成 artifact：

- **GDSII / OASIS。** Snapshot 提供 capability-declared tagged geometry/hierarchy/property records；frozen tech context 提供 element-tagged stream-layer-key ↔ canonical purpose mapping 与 exact unit/DBU scale；export policy 提供 deterministic semantic ordering。Exporter 不 replay ChangeSet 来“得到”最终几何。只有已声明 capability 的 subset 才能声称 **semantic** round-trip；byte、record order、timestamp、polygon fracture、path encoding不要求相同。
- **JSON snapshot。** 使用 versioned wire codec输出 current semantic/assurance、tagged geometry、occupancy fragments、annotation validity、connectivity、lifecycle summary与 linkage ids；typed keys/sets不得依赖默认 JSON coercion。JSON是 artifact，不是下一轮事实源。
- **CDL。** 按 frozen source/output `CdlDialectProfile` 从 current semantic state与保留的 source AST/token provenance输出；必须遵守 identifier case/escape、numeric suffix与expression rewrite语义，保留 subckt pin order、globals、model/terminal mapping、scale/unit/directive、未编辑参数及 opaque required records，并经 `FinCountSemanticsProfile` 把 canonical size axes映射到该 model的 `NFIN/NF/M` 或其它 token。`.include`/library依赖输出为 self-contained portable bundle或 immutable dependency manifest；若 affected expression无法 soundly evaluate/rewrite、source→output profile不兼容或依赖closure不完整则 typed-fail，不得从 raw diff/target或 hard-coded list 拼最终 params。
- **Optional debug / fixture JSON。** 可以为了回归测试保留简化格式，但必须标注为 artifact/debug view，不能成为 v2 parser 主输入。

输出顺序、canonical→artifact unit / DBU serialization、stream-layer mapping、tagged geometry serialization 必须可测试。输出 nominal DBU 无法精确表示坐标、超出 writer range 或需要未授权 rounding 时 typed-fail；获准 coordinate quantization 必须记录 exact delta。UnitScaleContract 单独验证 nominal DBU 的有限精度 stream encoding，并保留 raw scale / equivalence provenance；这不能授权 coordinate quantization。Stage 6 的反向 serialization 是纯输出变换，不写回事实。Byte-golden drift 不是天然错误；self-consistency 在同一 verified scale binding 下比较 canonical geometry/hierarchy/metadata semantics，并解释 shape order、unit、fracture或实际几何变化。

Stage 6 artifact 的读取边界如下：

| Artifact | 从 snapshot 读取 | 从 commit sibling records 读取 | 其它 frozen inputs | 禁止事项 |
|----------|------------------|-------------------------------|--------------------|----------|
| GDSII/OASIS | tagged geometry/lifecycle partitions | provenance ref、optional order hint | stream capability/key/DBU mapping | 不以 bbox或 edit stream修补 semantics |
| JSON snapshot | current semantic/assurance、geometry、occupancy、annotation、connectivity、lifecycle/linkage | ChangeSet summary、commit refs | versioned codec/export policy | 不依赖默认 Python JSON/hash语义 |
| CDL | current semantic state + source dialect-preservation refs | semantic-delta provenance | CdlDialectProfile、model/parameter mapping | 不丢 globals/pin order/model/directive，不从 diff/target硬编码 params |
| SKILL / Virtuoso script（post-MVP） | shape ids、exact geometry/fingerprint、bbox spatial prefilter、hierarchy/instance path、identity anchors | ExportEdit、provenance | frozen tech layer-purpose mapping、tool config、assertion policy | v2 MVP 不依赖它完成 layout 修改；不把 SKILL 当作 state commit |
| Human / machine report | snapshot summary | ordered ChangeSet / CommitEvent chain | RunRecord、ArtifactManifest、ValidationResult、reporting policy | 不读取 live planner / transaction，不只统计 macro edit ops |
| Validation result | snapshot | commit id、validation expectations | ArtifactManifest、RunRecord、ToolRunResult / ParseResult、validation policy | 不只打印 stdout；不吞掉 skipped / deferred / degraded checks |
| Visualization | snapshot geometry / annotation / connectivity | committed delta、provenance | RunRecord、ValidationResult、reporting policy | 不从 pre-commit edit stream 拼图 |

### 10.3 SKILL / Virtuoso interaction

v2 MVP 的主输出路径是 Python-based exporter：从 committed snapshot 直接导出 GDS / JSON / CDL，并通过 self-consistency / fixture validation 检查这些 artifact。只要这条路径能产生可被下游工具读取、可回归、可审计的 layout artifact，SKILL / Virtuoso 交互就不是 v2 MVP 完成版图修改的必要步骤。

SKILL / Virtuoso 的定位应降级为 **post-MVP production integration / mirror-to-editor artifact**：当生产流程要求把 Layauto 已经 commit 的修改真实反映到 Virtuoso layout editor 中，或需要在 Virtuoso database 中保留可审计的人工复现脚本时，再从 final snapshot + ordered ChangeSet chain / ExportEdit 生成 SKILL。它的目的不是替代 Python exporter，也不是成为权威 commit 机制，而是把同一份已提交状态投射到 Virtuoso 环境。

因此 v2 MVP 对 SKILL 的要求是保留清晰边界，而不是实现完整生产脚本：

- Python exporter 生成的 GDS / JSON / CDL 是 MVP 的 primary artifact。
- SKILL emitter 可以暂不实现；若 v2 MVP contract 声明该 post-MVP check，则 validation policy 应把 SKILL dry-run 标记为 deferred；只有 policy disabled / not-applicable 才是 skipped。
- 如果后续实现 SKILL emitter，它必须只读 final snapshot + ordered ChangeSet chain / ExportEdit，并包含 lib/cell/view、hierarchy/instance path、exact geometry/fingerprint、layer-purpose mapping、Virtuoso shape-match tolerance、shape locate assertion、provenance comment、ambiguity / missing-shape failure、tool stdout/stderr / return code 等结构化记录。Bbox/tolerance 只枚举候选；最终匹配必须核对 exact geometry、layer-purpose 与 instance context，多解或缺失 typed-fail，不能仅凭相同 bbox 修改 shape。
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
- LVS 必须先比较 exported / extracted layout 与 exported current-semantic CDL snapshot；默认 `whole_intent` run 还必须证明 current semantic 等于 immutable target CDL / TargetIntent。Partial / waived run 的 target mismatch 必须显式报告为 non-production / requires-review，不能 clean-pass。内部 net renumber、S/D swap、layout instance rename 必须通过本次 Stage 6 LVS run 产生、且绑定 exported GDS/CDL 的 matched xref / terminal mapping 解析到 frozen canonical DeviceId/NetId，并遵守 model/body context 的 terminal-symmetry contract。Stage 2 annotation 只提供 baseline provenance，不复用其 run-scoped LVS id。该 validation-local join 仅服务结果解析与 localization，不写回 snapshot；无法 join 时返回 typed mapping/localization gap，不凭名字猜测。
- DRC/LVS violation 应定位到 schematic net / device / connected component / candidate / commit provenance；无法定位时要给出 typed localization gap。
- Tool command failure、format drift、missing binary、timeout、license failure、SVDB missing、rule deck missing、layer map mismatch 都应成为结构化 validation result。
- Calibre output 不得直接 patch layout state；它只能产生 validation result、diagnostic artifact，或作为下一轮修复 intent 的 evidence 输入。

同样，deferred 只表示 v2 core MVP 可以先没有真实 Calibre 环境；一旦 run policy 声明启用 Calibre closure profile，DRC clean、LVS match、query-result parse 和 violation localization 就是该 profile 的结构化 fatal gate。dummy Calibre、缺失 license、缺失 rule deck 或 skipped/deferred signoff 不能作为该 profile 的 production pass。

第 10 节只定义边界。生产级 runner / dialect 位于 `tooling/`，格式 parser 分别位于 `importers/` / `validation/`，localization helper 位于 `validation/`；当前 v2 MVP 不需要实现完整 Calibre DRC / LVS closure。

### 10.5 Validation model

Validation 分层：

1. **Golden regression。** 用于 fixture / CI。检查输出是否与预期 golden 一致。适合 synthetic fixture，不应被当作生产 ECO 的唯一正确性标准。
2. **Self-consistency。** 检查 artifact与 final snapshot/ordered chain/current semantic assurance/stream+dialect+unit mapping/lifecycle result一致。
3. **Signoff validation。** 运行 DRC / LVS / SKILL dry-run / optional Virtuoso shape locate 等生产检查；v2 MVP 已声明但暂缓实现的检查标记为 deferred，policy disabled / not-applicable 才标记 skipped。
4. **Audit-readiness validation。** 在生成 report 前检查 frozen RunRecord、provenance、policy disclosure 与 localized references 是否足以解释修改；report / visualization artifact 本身由后续 reporting subphase 生成，避免 validation ↔ reporting 循环。

Self-consistency 至少应检查：

- 在声明的 geometry capability 内，用 re-reader 比较 canonical hierarchy/regions/transforms/properties 与 snapshot semantics；bbox-only run 只有逐 record 通过 axis-aligned-rectangle losslessness check 才能声称 semantic round-trip。Production profile 还应使用独立 downstream tool open/syntax gate，避免 writer与同源 reader的 common-mode bug。
- JSON export 与 snapshot content 一致。
- CDL 重新按同一 declared dialect parse 后，与 current-semantic state、source pin/global/model/directive preservation及 parameter mapping做 semantic equality；production 最终仍以 LVS 为 gate。
- 对已生成的 SKILL / ExportEdit，self-consistency 只做静态 reference / exact geometry-fingerprint / hierarchy-instance path / bbox prefilter / layer-purpose / provenance 一致性检查；真实 Virtuoso dry-run / shape locate 仅归入 signoff/tool validation。已在 v2 contract 声明但 capability 暂缓实现时记为 deferred；run policy disabled / not-applicable 时记为 skipped。
- Frozen reporting input 中的 change counts、affected regions、target intent、candidate id、constraint result 与 ChangeSet 一致。
- policy-controlled geometry 已经按 lifecycle 包含在 snapshot 中，而不是 Stage 6 临时生成。
- Selected fin/device profile 的 raw/effective invariants、extracted fin count、routing/via/cut-effective-geometry repair、body/boundary context与 connectivity 等符合 commit expectations。
- Annotation coverage、unannotated blockage、suspect geometry、coverage gap 与 validation policy 一致，并按既有 provenance/validity 区分 source-bound、candidate-derived/inherited、unverified-after-edit 与 unknown/ambiguous；source coverage 不能推断 post-edit LVS match，后者只由对应 Stage 6 ValidationResult 声明。

只有 required core artifacts 经 manifest commit marker 可见的 success/no-change run 才产生 `ValidationResult`；它绑定 `run_id`、`final_snapshot_id`、`ordered_commit_ids`/chain hash（no-change 可为空）、artifact manifest id、`checks: tuple[CheckResult, ...]` 与 deterministic aggregate outcome。每个 `CheckResult` 分开记录：

- `execution_status = pass | fail | error | skipped | deferred`。
- `coverage = complete | degraded | none`；complete 只表示声明的 check/profile scope 完整执行，不表示整个 foundry deck 均已覆盖。
- `finding_severity = info | warning | error`。
- `policy_disposition = accept | requires_review | reject`。
- reason、tool/evidence refs、localized object references、runtime/return code。

检查完成并发现违例为 `fail`；missing tool/license、timeout 或 parser failure 等无法完成检查的 execution failure 为 `error`，enabled-required profile 必须同时 `reject`。`deferred` 只表示当前 milestone 已声明但未执行，`skipped` 只表示 disabled/not-applicable，二者 coverage 为 none。`degraded` 是独立 coverage/quality 维度，可与 pass/fail/error 同时记录，不能抹掉已发现的违例；局部 pass 不能被汇总成 required-scope clean。Partial/no-change/failure path 不得伪造单个 commit id。

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
- annotation coverage：coverage gap、unannotated blockage、suspect geometry，以及 source-bound / candidate-derived/inherited / unverified-after-edit / unknown/ambiguous 的 provenance/validity 分组；不得把 source-LVS assurance 当作 post-edit LVS proof。
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
- Derive 只对 tech-declared `prepublication_derived` layers在 private tentative state上执行 certified finalization，并从 frozen state产生 read-only views；preserve/frame lifecycle与 commit由 transaction/repository协调。
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
│   ├── codec.py
│   ├── publication.py
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
├── repository/
│   ├── publication.py
│   └── run_journal.py
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

`tech/` 是 layer/rule/extraction registry owner；`normalization/`只构建 ProposedInitialState；`domain/publication.py`拥有 neutral `PreparedPublication`/`Stage5Closure`/`TerminalPipelineBundle` schema与 canonical digest；`repository/` 是 state-lineage head和 run-attempt revision/terminal pointer的唯一 CAS/transaction owner。Transactions只构建 neutral DTO，不被 repository import。`domain/codec.py`拥有 wire/canonical bytes contract。

Python reference profile 必须在 `pyproject.toml` 明确 `requires-python`；当前项目最低基线保持 Python 3.10+，不得仅因示例 syntax/typing 偏好提高版本要求。Runtime 与 optional GDS/YAML/tool dependencies、strict type-checker 与 supported interpreter matrix 应显式声明并在 CI 校验。Typing/Protocol/TypedDict 只提供静态合同，不替代 runtime schema validation；`@runtime_checkable` 也不能验证方法签名或数据结构。所有 YAML 使用 safe loader、拒绝 duplicate/unknown keys与 custom executable tags、限制 size/depth，并先构造 validated immutable DTO；rule/config 不得 `eval` 任意 expression。

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

- `DeviceIR`、`NetIR`、`CircuitIR` 与 CDL source-document preservation refs（pin/global/model/directive/opaque supported records）。
- `ResizeIntent`、`RoutingIntent`、`UnsupportedIntent`。
- `GeometryRecordId`/`ShapeId`、`CellId`、`OccupantFragmentId`、`AnnotationTargetId`、`ComponentId`、`CommitId`。
- `EvidenceRecord`、`ArtifactManifest`、`ExportPolicy`、`RunRecord`、`CommitAuditRecord`、`PlanningAuditRecord`、`ConstraintAuditRecord`、`ToolRunResult`、`ParseResult`、`StageFailure`、`ReportingResult`、`PipelineResult` 等中立、discriminated contracts；success/no-change/no-publication-failure/partial-failure/interrupted 等非法字段组合不能靠一组 Optional 凑出。
- `EditPolicy`、`ValidationSeverity` 等稳定枚举。
- Versioned wire codec、canonical-byte/digest algorithm 与 typed id encoding；不使用 Python object hash。

### 11.3 `state/`

**职责。**
`state/` 独占 v2 `AuthoritativeState` 的所有权与坐标系统定义。该 aggregate 应清楚区分：

- `semantic.py`：current semantic state；target intent 仍是 transaction 外的 immutable input。
- `coordinate.py`：layer grid、track axis、B-tier axis、physical↔track 转换、bbox→cell projection 等坐标数学。
- `layout_store.py`：单一 tagged geometry/hierarchy/property store，以 layer lifecycle/partition 和 origin 分开记录，flat bbox 只是 capability subset。Shape annotation 只能是 region annotation 的 read summary。
- `occupancy.py`：A/B-tier multi-occupant fragment coverage、blockage、via/cut/OD broad-phase working/index data。
- `annotation.py`：`AnnotationTargetId`-keyed annotation、coverage/conflict，以及 canonical semantic id-keyed ixref/net-xref/seed indices。
- `connectivity.py`：exact effective conductor/device-terminal/body regions、qualified same-layer/via edges、cut operator result与 diffusion topology；summary 位于 `derive/views.py`。
- `mutation.py`：transaction-private mutation primitives与 neutral DTO；对 constraints 只暴露 query-only `ReadOnlyStagedState`/`AffectedScope`，不暴露 mutation sink/checkpoint。
- `snapshot.py`：transitively immutable、无 writable alias 的 committed snapshot，只保存 state content 与 domain linkage ids。

**可以依赖。**

- `domain/` 的 identifier、geometry primitive、semantic id。
- Tech bundle 中的 layer / coordinate / rule metadata，但不直接读取文件。

**禁止。**

- `coordinate.py` 不能持有 occupancy；grid 只做坐标数学。
- semantic、single tagged layout store（drawn/policy-controlled partitions）、occupancy fragments、annotation、connectivity与 metadata必须由同一 `AuthoritativeState`版本化；各 components不能漂移。
- `Device.fin_track_indices`、`Net.segments`、`Net.vias`、gate tracks 等不能作为 state truth 长期存储；它们属于 `derive/views.py` 或 state-backed view。
- 不依赖 parser、Calibre query runner、decoder、exporter、pipeline、repository 或 transaction implementation。
- 不把 constraint engine cells 当作 occupancy truth。

**legacy 迁移注意。**
Legacy MVP 中 `MultiLayerGrid.b_tier_cells`、`Net.segments`、`Net.vias`、`Device.fin_track_indices`、`ConstraintEngine.cells` 都不能原样成为 v2 authoritative state。可复用的是坐标转换、bbox→cell projection、稳定排序、局部 connectivity 算法等纯逻辑；状态所有权必须迁移到 `state/`。

### 11.4 `repository/`

**职责。**
`repository/publication.py` 是第 2.6 节 `PublicationRepository` public facade与 selected persistence backend owner；`repository/run_journal.py` 实现同一 composite root/transaction domain中的 RunAttempt revision、stage5 closure与 terminal pointers。它们持久化 `domain/publication.py` 定义的 neutral `PreparedPublication`、`Stage5Closure`与 terminal DTO，并提供 create/seal/initialize/publish/close/finalize/load/recover API；不把 Python transaction object当持久 schema。

**可以依赖。**

- `domain/` 的 publication/result ids、versioned codec与 canonical bytes。
- Immutable state snapshot/storage primitives；backend adapter可依赖标准库或 selected database/object-store client。

**禁止。**

- 不 import `transactions/`、`planning/`、`constraints/`、`export/`、`validation/` 或 `reporting/` implementation。
- 不用两个独立 mutable heads模拟 state/run原子性；backend必须满足 ACID或 single composite-root CAS合同。
- 不在 recovery中从全局 latest snapshot猜测某个 run的位置；只使用该 attempt的 durable pointer与 sealed context。

### 11.5 `annotation/`

**职责。**
`annotation/` 有两个显式模式：Stage 2 evidence overlay 消费 Stage 1 Calibre / LVS bundle，执行 layer mapping、identity translation、per-cell overlay 与 coverage / conflict 分析；Stage 5 proposed-state reconciliation 则消费 current AnnotationState、neutral `StagedStateView` / `StateDelta` / `AffectedScope` 和 current semantic ids，为变化 cells 生成 candidate-derived attribution 或 conservative invalidation，不重新读取 raw evidence。两种模式都只生成 proposed `AnnotationState` / delta，不拥有或直接修改 authoritative state；只有 InitializationTransaction 或 Stage 5 transaction 可通过 `state/` mutation API 安装结果，normalization builder 不直接 publish。

**可以依赖。**

- `domain/` 的 identifier。
- `state/coordinate.py` 的 exact projection math；tolerance / ambiguity policy 来自 `tech/` 与 run annotation policy。
- `state/` 的只读 geometry / occupancy / current-annotation / current-semantic view、proposed annotation schema，以及 `state/mutation.py` 的 neutral StagedStateView / StateDelta / AffectedScope protocols。
- `domain/evidence.py` 的 schema-canonical evidence record。
- `tech/` 的 layer registry 与 annotation policy。

**禁止。**

- 不把 `device_info` / `net_shapes` 当作完整几何事实替代 GDS。
- 不直接执行 resize、routing repair、cut insertion 或任何 ECO 修改。
- 不在 Stage 6 临时解释 LVS identity 来修补 exporter 输出。
- 不把 legacy `calibre_device_query.json` / `calibre_net_query.json` 作为 v2 主输入模型。

**关键输出。**

- Per-region/fragment `device_ref` / `net_ref` / `pin_role` / `annotated_mask_color`、validity/conflict、coverage 与 evidence provenance。
- Proposed AnnotationState / delta，包括 candidate-derived attribution、invalidation 与 `unverified_after_edit` markers。
- Shape-level annotation summary；当 cell 不一致时 summary 应保持 unknown / ambiguous。
- Coverage report：annotated、unannotated blockage、suspect、conflict。
- Identity translation：layout instance → schematic instance，LVS net → schematic net / query-run-scoped opaque LVS index。

### 11.6 `planning/`

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
- 不静默跳过 unsupported delta；预期的 unsupported/config/evidence/constraint failure 统一返回 tagged result variant。Exception 只用于 programmer bug或不可预期 infrastructure，并在 pipeline boundary 转为 `InternalStageFailure`；不得捕获 `KeyboardInterrupt`/`SystemExit`。

**关键对象示例。**

- `CandidatePlan`。
- `ResizeCandidate`。
- `RoutingCandidate`。
- `RepairRequirement`。
- `UnsupportedPlanningResult`（expected failure variant，不依赖 exception control flow）。
- `PlanningResult`，包含 `base_snapshot_id`、preconditions、`apply_atomicity` 与 `ProposedMutationSpec`。

### 11.7 `constraints/`

**职责。**
`constraints/` 消费 immutable `tech.rules.RuleRecord`，负责编译 rule predicates、建立 DRC evaluation context、domain / trail / propagation overlay 并产生 feasibility result；它不拥有 rule facts。

`ConstraintResult` 是 `feasible | infeasible | indeterminate | error` 的 discriminated variant；只有 fully-ground overlay 上 exact mandatory predicates全通过才是 feasible。Timeout、resource limit或 predicate unavailable必须 fail closed。

**可以依赖。**

- `domain/` id / policy。
- `state/coordinate.py`、`state/occupancy.py`、`state/connectivity.py` 的只读 query。
- `state/mutation.py` 提供的 query-only `ReadOnlyStagedState` 与 affected-scope protocol；constraint 自己拥有 solver trail，不接触 transaction checkpoint/mutation sink。
- Tech rule records。

**禁止。**

- 不拥有长期 layout state。
- 不维护另一份可与 `state/occupancy.py` 漂移的 occupancy copy。
- 不把 per-cell scalar `net_id` domain 作为 same-conductor truth。
- 不把 CUT / VIA / DEVICE_DIFF 等 layer-implied occupant 强行展开成 `occ_type × net_id` 的大型 domain。
- 不把 unknown / unannotated geometry 当作 compatible-with-everything。
- 不 import `transactions/`；constraint API 接收中立 staged-view protocol，避免 `constraints/` ↔ `transactions/` 循环依赖。

**relation-aware 规则。**
Spacing/enclosure/cut/via/OD 等 predicate 读取 exact geometry与 `RuleRecord.relation_basis` 所要求的 component/extracted-net/semantic-net/voltage/mask context；不设置一种全局默认 relation。

### 11.8 `transactions/`

**职责。**
`transactions/transaction.py` 是 candidate 变成 neutral prepared publication的唯一 ECO 门。它负责 private overlay、constraint orchestration、annotation/policy-controlled finalization、rollback与 sibling record freeze；真正 publication只能调用 `PublicationRepository` 的 `publish_whole_and_close_stage5(...)` 或 `append_partial(...)` public facade。RunAttempt journal属于 `repository/`，不属于 transaction。

`transactions/initialization.py` 拥有 baseline-only `InitializationTransaction` protocol：它接收定义在中立 `state/mutation.py` 的 `ProposedInitialState`，冻结 `domain/publication.py` 的 PreparedBaseline 后调用 repository create-if-absent/context-seal；它不 import `normalization/`，normalization也不 import `transactions/`。Pipeline依次调用 builder与 transaction facade，不能直接 publish state。

**可以依赖。**

- `domain/` id / intent / semantic delta。
- `state/` mutation API、snapshot API。
- `constraints/` feasibility API。
- `annotation/` 的 proposed-state refresh / invalidation API。
- `derive/markings.py` 的 pre-publication finalization API。
- `derive/invalidation.py` 的 view invalidation API。
- `repository/` 的 public facade；参数只能是 neutral domain publication DTO与 typed preconditions。

**禁止。**

- 不允许 planner / macro 绕过 transaction 直接写 committed state。
- 不允许 constraint engine 的 checkpoint 代表完整 transaction rollback。
- 不允许 Stage 6 exporter 作为 canonical updater。
- 不把 legacy L1 `EditOp` 作为 commit channel 或 authoritative geometry。
- base materialization、mandatory constraint、annotation refresh、policy-controlled finalization任一步失败都必须丢弃 overlay，不得留下 partial state。

**关键输出。**

- `ChangeSet`：current-semantic、geometry、occupancy、annotation、connectivity、derived delta 与 invalidation metadata。
- `CommitEvent`：parent / new snapshot ids、plan-group / candidate ids、constraint audit refs、provenance、validation expectations。
- Immutable snapshot：供 Stage 4 planning、下一轮 Stage 5 transaction 与 Stage 6 只读消费。
- `CommitEnvelope`：per-publication immutable logical unit；只有 `PublicationRepository.publish_whole_and_close_stage5` / `append_partial` 在 publish-time ACID/composite-root CAS中切换唯一 root后才具有原子可见性，类型名本身不提供原子性。

### 11.9 `derive/`

**职责。**
`derive/` 负责三类派生结果：

1. `markings.py`：只处理 tech profile 明确标为 `prepublication_derived` 的 C1 geometry；well/boundary/VT/implant 等名称本身不决定生命周期。
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
Selected FinCount/DeviceExtraction profile决定 raw/effective FIN、active、gate/channel与 fin-count语义。Static-fin 候选 profile拒绝 raw FIN edit；其它 representation没有声明 operator时 typed-unsupported。Gate/channel terminal separation与 fin attribution从 committed exact geometry + annotation/extraction重算。

### 11.10 `importers/`

**职责。**
`importers/` 负责文件格式适配：GDSII/OASIS capability geometry、CDL dialect-aware parse、query dialect parse、safe config load。它输出 raw capture或 versioned evidence record，不构建 state；命令执行由 `tooling/`负责。

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

### 11.11 `export/`

**职责。**
`export/` 从 final immutable snapshot、ordered ChangeSet/CommitEvent chain、RunRecord、frozen tech context、export policy和site/tool config生成 artifacts。Required objects 写入 unique immutable/versioned path并按 selected durability profile同步/验证后，最后发布一个 `ArtifactManifest` pointer作为 **export-set complete/addressable** marker；它不宣称多文件物理事务，也不是 production release pointer。只有 repository terminal root所引用、且 `deployment_disposition=accept` 的 PipelineResult可授权 production consumer。Human/machine report与 visualization 由只读 `reporting/` 后续生成。

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

### 11.12 `validation/`

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

- `ValidationResult(run_id, final_snapshot_id, ordered_commit_ids/chain_hash, manifest_id, checks, aggregate_outcome)`；no-change chain可为空。
- Per-check `execution_status = pass | fail | error | skipped | deferred`。
- 独立 `coverage = complete | degraded | none`，语义以第 10.5 节为准；degraded 不替代 pass/fail/error verdict。
- 独立 `finding_severity = info | warning | error` 与 `policy_disposition = accept | requires_review | reject`，不得混成一个 enum。
- Reason、tool/evidence/artifact refs与 localized object refs。
- Required profile 的 missing tool/license/timeout/parser failure 必须 `error + reject`；完成检查后发现违例为 `fail`。

### 11.13 `pipeline.py`

**职责。**
`pipeline.py` 负责串联 Stage 1–6，并把每个阶段的输入输出显式化。它是 orchestration layer，不是业务逻辑模块。

**可以依赖。**

- `tooling/`、`importers/`、`normalization/`、planning、constraint service initialization、transactions、export、validation、reporting 的 public facade。
- `repository/` 的 public facade，用于 pre-context attempt、context seal、Stage 5 closure、terminal publication与 recovery；只传 neutral domain DTO/ids。
- Run-level config / policy。

**禁止。**

- 不承载 resize / routing macro 细节。
- 不承载 DRC rule predicate。
- 不承载 exporter 细节。
- 不在 pipeline 中直接 patch geometry 或 output JSON。
- 可以把 annotation / constraints / derive service 注入 normalization / transactions，但不直接调用 mutable state API、constraint commit 或 C1 finalizer。
- 不吞掉 unsupported intent、constraint failure、transaction rollback、export failure 或 validation failure。

**Stage boundary 要求。**
`pipeline.py` 应显式记录每个 stage 的输入、输出和 tagged failure result。被捕获的 Stage 1–5 failure冻结 failure RunRecord；`run_record_freeze` 本身失败按专门 variant处理。Crash-durable profile 的 crash/OOM/power loss 由 durable RunAttempt journal与启动 recovery补成 interrupted/requires-review record，不能承诺在故障瞬间一定有 PipelineResult；process-local MVP 不承诺断电恢复。Stage 6 failure不修改前置 RunRecord。`ValidationResult` 只表示 checks，`ReportingResult` 只表示 report/visualization outcome，最终 PipelineResult汇总 refs。Changed success在 Stage 5 publication后才有新 snapshot；no-change success复用当前 snapshot且 commit chain为空。任何降级/跳过都进入相应 record。

### 11.14 `legacy_mvp/` 与代码取用原则

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

### 11.15 模块依赖方向与边界测试

v2 应为模块边界建立轻量 architecture tests，避免实现过程中重新长出 legacy 状态流。

建议检查：

- `domain/` 不 import `importers/`、`constraints/`、`transactions/`、`export/`、`validation/`、`pipeline.py`。
- `tech/` 不 import `state/`、`annotation/`、`constraints/` 或 `pipeline.py`；它只拥有 immutable tech facts / schema。
- `state/coordinate.py` 不持有 occupancy storage。
- `state/` 不 import `transactions/`，snapshot / state metadata 只引用 domain ids。
- 任何 lineage head或 RunAttempt pointer更新只经 `repository/publication.py`；contract tests覆盖 concurrent same-parent publish仅一方成功、same-key/same-digest响应丢失重试、same-key/different-digest conflict、create-if-absent 与 pre-context failure；选择 crash-durable profile 时另须覆盖 composite-root crash injection 与 attempt-scoped recovery。
- `normalization/` 与 `pipeline.py` 不直接调用 mutable state publication；baseline 必须经 InitializationTransaction。
- `normalization/` 不 import `transactions/`，`transactions/` 不 import `normalization/`；二者只共享中立 `ProposedInitialState`/PreparedBaseline DTO。
- `constraints/` 不定义 canonical layout store / occupancy store。
- `export/` 和 `validation/` 不 import mutable transaction applier，不调用 derived finalization，不写 `state/` mutable API。
- `importers/` 不构建 segments / vias / fin attribution 等 state views。
- `planning/` 不调用 exporter / decoder，不修改 committed state。
- `pipeline.py` 不包含 macro-specific geometry arithmetic。
- v2 runtime 与 production test path 不 import `legacy_mvp/`；v2 fixtures / helpers 位于 `tests/fixtures/` 或 `tests/support/`。
- `constraints/` 不 import `transactions/` 且只接收 query-only staged view；`annotation/` / `derive/` 不 import transaction / ChangeSet 类型。
- `export/` 与 `validation/` 共享 `domain/artifacts.py` 的中立合同、彼此不 import；需要合并两者结果的 report / visualization 位于 `reporting/`。
- `tooling/` 与 `importers/` 共享 `domain/results.py` / `domain/evidence.py`，彼此不 import。
- 禁止新增依赖 legacy `EditOp` 作为 Stage 5 commit 输出；任何 edit-like artifact 必须位于 `export/` 的 `ExportEdit` 层。
- 禁止新增对 legacy fixture JSON 的 v2 主路径依赖。
- Canonical codec tests覆盖 typed ids、region-key tables、Decimal/Enum/Path、set ordering、NaN/Inf rejection与跨进程 digest；测试明确禁止 built-in `hash()` 作为 persistent id。
- Snapshot tests覆盖 nested collection alias mutation，证明 publication后旧 snapshot content digest不变；frozen dataclass/MappingProxyType本身不算通过。
- Geometry/annotation/connectivity tests覆盖同 cell多 fragment、相邻 cell但几何不接触、gate分隔S/D、qualified via overlap、cut Boolean与 non-rectangle stream typed-fail/semantic round-trip；changed-route的 candidate label/`unverified_after_edit` ref不得获得 `same_extracted_net` exemption。

这些测试不替代功能测试，但能持续保护第 3、5、8、9、10 节定义的状态边界。当前 `layauto_v2/` 只是按本节边界建立的 v2 skeleton，不包含 legacy MVP 逻辑；历史 `legacy_mvp/` 不得被 v2 runtime 或 production tests import。一次性的离线数据转换若未来需要，应作为仓库外或 release tooling 处理，不进入 Stage 1–6。

## 12. 配置、tech bundle 与环境边界

本节定义哪些内容属于一次 run 的配置，哪些内容属于 tech bundle，哪些内容必须来自输入 evidence 或生产工具结果。原则是：site/run config 只能选择路径、工具模式、执行策略和环境适配；tech bundle 才拥有 layer、rule、unit / DBU expectation 与 mapping 等工艺事实。两者都不能制造某次设计的 layout / schematic / LVS 事实，也不能绕过第 2、3、5、8、9、10 节定义的状态边界。

Legacy MVP 中符合 v2 架构要求的实现可以按职责复用，例如 CDL parser、Calibre query parser、tech config loader、部分 GDS IO、fixture generation / test harness；不符合 v2 架构边界的路径应重构或删除，不需要为 legacy 行为设计 adaptation / migration path。

### 12.1 `site_config.yaml`

`site_config.yaml` 是一次 run 的 manifest。它描述输入/输出路径、tech bundle 入口、Stage 1 evidence acquisition 策略、tool adapter 参数、export policy 与 validation policy。它不承载 device instance、device pins、net membership、target nfin、shape bbox、Calibre query 内容等设计事实。

建议 schema 分层：

- `tech:` 只选择 versioned tech bundle，例如 rules/layer/query registries、Geometry/CDL/FinCount/DeviceExtraction profiles、foundry map、exact unit/DBU expectation；run-specific policy不重复定义 tech facts。
- `inputs:` 指向 source/target CDL或 raw intent、GDSII/OASIS/capability geometry，以及 QueryBundleHeader + normalized query capabilities。Target source至少一种；多种并存时一致性检查。预生成 YAML只有在绑定 raw-capture hash、query baseline hashes/top/deck/status与 parser/dialect provenance时可读，不能绕过 acquisition/parser。
- `outputs:` 指向 artifact 输出目录与命名策略；不得把输出路径反向作为 Stage 5 commit 事实源。
- `calibre:` 描述 Stage 1 Calibre / LVS query 获取策略，例如 `mode: calibre | dummy_fixture`、SVDB path、raw query output path、normalized YAML cache/output path、timeout、command dialect、binary path。`dummy_fixture` 只表示“读取预置 raw query captures，并用同一 parser 生成或核对 normalized YAML”；normalized YAML 不是与 raw capture 二选一的主输入，也不是 legacy parser mode。
- `virtuoso:` / 其他 tool blocks 只描述工具调用环境，例如 lib/cell/view、dry-run、`layer_purpose_dialect` / profile selection、`shape_match_tolerance`、undo policy；dialect 必须解析到 selected tech bundle，不能重定义 canonical layer / purpose。
- `geometry_policy.snap` / `geometry_policy.rounding` 描述 tech-compatible run policy；`annotation_policy` 选择 registry-defined overlay / ambiguity profile 并可在 tech 上限内收紧 tolerance；`virtuoso.shape_match_tolerance` 独立描述 tool locate tolerance。三者不得共用一个无类型 `bbox_tolerance`，site config 也不得放宽 tech bundle 的工艺边界。
- `validation:` 描述 fatal / warning / deferred / skipped policy、rule execution profile，包括 golden regression、self-consistency、signoff DRC/LVS、SKILL dry-run、fixture limitation 等类别。
- `format:` 可声明使用 v2 evidence schema 的版本。它不能声明 legacy parser / legacy decoder 为主路径，也不能允许 Stage 6 writeback 成为 canonical state mutation。

路径可以是绝对路径，也可以相对于 `site_config.yaml` 所在目录解析。所有 YAML 须有 `schema_version`，使用 safe loader并拒绝 duplicate/unknown keys、custom executable tags、超限 size/depth；loader 在边界构造 validated immutable DTO。缺失 required input、路径不存在、mode 与输入集合冲突等预期失败返回 tagged config result，再由 pipeline 映射为 `StageFailure`；typing/TypedDict 不算 runtime validation，不能伪装为 Stage 6 `ValidationResult`。

`site_config.yaml` 可以包含用于打开工具对象的名字，例如 Virtuoso `lib/cell/view` 或 GDS `top_cell_override`。这些名字只用于定位工具环境中的对象，不能覆盖从 CDL/GDS/LVS evidence 得到的 semantic identity。若工具入口名与 evidence 中的 cell / subckt identity 不一致，应记录为 validation issue，并由 policy 决定是否 fatal。

### 12.2 `drc_rules.yaml`

`drc_rules.yaml` 描述可机器消费的 closed rule variants，而不是散落在代码里的常量。Source 值必须有显式 unit 或 bundle-level、带 provenance 的唯一 default；decimal 以字符串/exact numeric token解析，按第 12.5 节已验证的 nominal scale binding 精确转换为 canonical DBU，binary float 不进入 rule truth。Rule threshold 不因 stream unit 的编码误差被重新缩放、取整或放宽；不可精确表示时使用 capability-declared exact rational predicate 或 typed-fail。字段示例：

- `id`：稳定 rule id，如 `LI.S.1`、`V0.E.LI`。
- `type` / `predicate_id`：registry 中封闭的规则类型，如 `min_pitch`、`min_width`、`min_spacing`、`min_enclosure`、`min_extension`、`exact_size`；不得 eval YAML/Python expression。
- `layers`：相关 layer 名称，必须能在 `layer_map.yaml` 中解析。
- `params`：与 predicate variant 匹配的 typed 参数；长度是 exact decimal+unit 或 canonical DBU，axis mapping 必须封闭校验。
- `condition`：typed closed context variant，例如 fin role、width class、colour class、derived-layer condition。
- `relation_basis`：`geometry_only | same_component | same_extracted_net | semantic_net | voltage_class | mask_property | none`。
- `required_relation_assurance`：该 relation允许的 provenance/validity等级；`same_extracted_net` 至少要求绑定当前 exact region的 matched extraction evidence，affected/ambiguous/stale/`unverified_after_edit` relation不满足。
- `missing_context_policy = fail | defer | conservative_fallback`；fallback必须绑定具体 relation/value与单调安全 proof，不能由 engine全局猜测。
- `geometry_capability` / dependency closure：该 predicate 的 exact evaluator、允许的 conservative grid fast path、wake/dependency/halo/whole-entity requirements。
- `source`：foundry / project rule source、版本或可审计引用。
- `notes`：解释或适用范围；不承载某个 fixture 的例外。

Rule loader 必须做跨字段 runtime validation：rule id唯一、layer可解析、单位/representability/axis合法、variant与layer/params/relation/geometry capability匹配。缺少 exact evaluator或无 false-negative 的 conservative proof时不能把该 rule记作 Stage 5 clean，更不能把 deck 未覆盖 violation 当作“已验证正确”。

规则的工艺值与适用条件属于 `drc_rules.yaml`；deployment 的 `site_config.yaml.validation.rule_execution_profile` 可以增加 / 强化 `frontline | signoff` 检查并设置 severity / policy outcome，但不得把由 tech + action + capability 推导出的 candidate-touched mandatory Stage 5 rule 降级为 signoff / deferred。缺少 mandatory predicate 必须使 capability admission 失败。v2 MVP 未实现的非 mandatory coverage gap 必须显式进入 validation / fixture limitation report；不能靠 target golden 或 fixture 行为掩盖。

### 12.3 `layer_map.yaml`

`layer_map.yaml` 是 GDS layer、layout tier、坐标拓扑与编辑属性的技术事实源。最低应描述：

- `name` / canonical purpose 与 element-tagged `stream_layer_keys` 映射；普通 geometry 的 `(layer, datatype)`、TEXT/BOX/NODE 对应 type 分开，purpose 不假装是 GDS record 字段。
- `tier`：A / B / C1 / C2。
- `role`：fin、poly、interconnect、via、cut、diffusion、well、boundary、marker、annotation 等。
- `projection_kind` / `coordinate_axes`：exact/conservative grid model、x/y pitch/offset、preferred/bidirectional/jog policy；可选 `ortho` 只属于声明该 lattice 的 profile。
- `electrical_connects`：via/contact连接的上下层；不复用为 placement axes，并附 exact contact predicate。
- `cut_target` / `effective_geometry_operator`：raw cut作用对象与 Boolean recipe。
- `edit_policy`：direct edit policy，例如 `static_backdrop`、`entity_constrained`、`routing_editable`、`derived_refresh_only`、`auxiliary_policy_controlled`、`no_direct_edit`。
- `lifecycle_policy`：`preserve_drawn | frame_static | prepublication_derived`；derived entry 必须绑定 generator/version/dependencies/context/dirty-scope/comparator。FIN static/no-edit只由 selected `FinCountSemanticsProfile` 声明；NWELL/BOUNDARY/VT/implant等不能按名称自动归类。
- drawn-patterning policy / optional `drawn_mask_color` interpretation：解释 canonical GDS layer/datatype 或 shape property，可参与工艺规则；独立 `display_color` 只服务 visualization / reports。
- `derived_layer_refs`：只列出可作为 annotation evidence source 的 `calibre_layer_map.yaml` stable names，不重复声明 `carries`、mask、tolerance 或 trim policy。

Grid topology 不应在 parser/grid factory 中硬编码。Projection model/axes与 electrical connects分别由 layer map提供，并做以下校验：

- 对声明 orthogonal lattice 的 profile 才验证 `ortho(ortho(L)) == L` 与一横一竖；其它 layer可 bidirectional/off-track。
- Projection axes 必须解析到 coordinate model；via `electrical_connects` 只验证可连接 layer，不能推导 axes。
- derived / non-editable layer 上的 direct edit 应在 Stage 4 capability admission 或 Stage 5 constraint / transaction boundary 被拒绝，不能拖到 export。
- `derived_layer_refs[*]` 必须能在 `calibre_layer_map.yaml` registry 中唯一解析，且 resolved entry 的 `associates_with` 必须包含声明该 ref 的 canonical GDS layer。

Annotation 权威位置应与第 3/5 节一致：`state/annotation.py` 中以 `AnnotationTargetId` 为 key、与同一 `AuthoritativeState` 共同版本化的 table 是权威；bare CellId 只用于 atomic-grid capability。`ShapeRecord.net_id/device_id` 只是 per-region consensus summary；被 cut、sharing或 cell内多 fragment分裂时不得强行写单一 identity。

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

可以进入 config 的，是“如何读取/运行/验证”的策略，例如路径、tool mode、timeout、dialect、validation profile、artifact naming。单位与 tolerance 按用途分开：source evidence保留 exact decoded unit/DBU；canonical DBU 必须在 verified scale binding 下精确容纳 drawn geometry；`geometry_policy.snap/rounding` 只约束新 candidate与获准的 output coordinate quantization，不能改写 source integer ticks；`annotation_match_tolerance` 只匹配 evidence；`virtuoso.shape_match_tolerance` 只预筛 tool object。Site config只能选择 tech-compatible profile或收紧边界，不能把真实 unit/DBU conflict 用 spatial tolerance 吞掉。

`UnitScaleContract` 由 versioned tech/format profile 拥有，显式区分 **raw encoded scale** 与 **nominal physical DBU**。GDSII REAL8 等有限精度编码不一定能精确表示十进制的 1 nm；不能要求其 decoded rational 与 exact decimal 无条件逐值相等。合同须固定 nominal scale、允许的 encoding provenance/precision、确定性的 equivalence test 与误差界，只接受该数值编码误差范围内的唯一 scale binding；缺少证明、匹配多个 nominal scale 或真实单位冲突时 typed-fail。该界不能来自 annotation/shape-match tolerance，也不能被 site config 任意放宽。Source XY integer ticks 必须原样保留；raw bytes、exact scale、nominal scale、encoding delta 与 contract version 进入 provenance/content identity，canonical rule/geometry 比较使用同一已验证的 nominal scale。此合同只解释单位数值的序列化，不允许移动 shape、修复 off-grid input 或掩盖几何量化。

### 12.6 Calibre / LVS query evidence 获取与结构化输入

Calibre / LVS query bundle 属于 Stage 1 evidence acquisition。v2 不再把它称为 “Stage 1.5”；query execution 由 `tooling/` 负责，parser / schema writer 由 `importers/` 负责，两者通过 `ToolRunResult` 与 schema-canonical evidence contract 连接。

Stage 1 应支持两类 evidence 获取方式；核心合同是 normalized evidence capabilities，具体命令/文件名属于 versioned `CalibreQueryDialect`：

- `calibre`：从 profile-declared query database 运行 adapter template，取得 instance-xref、net-xref、device-region、net-region capabilities。`iXref.temp`、`nXref.temp`、`NET NAMES`、`DEVICE INFO`、`NET SHAPES` 仅是一个 dialect/project adapter 的示例，不是通用 SVDB 文件或命令事实。
- `dummy_fixture`：从 fixture 目录读取预置 raw query captures，走同一 parser 与 normalized YAML/object schema。它用于没有 Calibre 环境的测试，不是 legacy layout parser mode。

Stage 1 输出应同时保留：

- `QueryBundleHeader`：query-run/database id、source layout hash、source netlist transitive include/library/preprocess closure hash与 top identities、hierarchy mode、deck/layer-map/runset/include/options closure hashes、tool/query-dialect/parser versions、LVS completion/match status与 assurance；closure manifest逐项列出 immutable dependency URI/content hash与 preprocessing semantics。所有 records 引用同一 header，Stage 1 与本 run inputs逐项核对。
- raw query captures：便于审计、复现 parser bug、对照 tool/dialect format drift。
- normalized objects / YAML：
  - `ixref.yaml`：layout instance ↔ schematic instance，包含 S/D swap。
  - `net_xref.yaml`：schematic net ↔ LVS net name ↔ **query-run/database-scoped opaque** `lvs_index`；跨 run identity 只能用 canonical semantic id。
  - `device_info.yaml`：per-layout-instance derived-layer tagged geometry evidence，保留 `exact | approximate_bbox | untrimmed` quality；unit/scale必须由每条 record显式声明或由已绑定的 query-dialect/header精确声明，不存在通用 µm 默认值。
  - `net_shapes.yaml`：per-net derived routing/conducting tagged geometry evidence，采用同一 explicit/header-bound exact unit合同，并保留 quality、`lvs_index`、`lvs_name`、`schematic_name`；bbox-only输入必须标 `approximate_bbox`并走保守 overlay。
- query provenance：header id、mode、source/query-db refs、command dialect/template id、timeout、tool/parser versions与 raw-output refs。

Stage 1 只做格式解析、exact unit decode、基本格式检查与 evidence 保存，并保留 original lexeme/value/unit/precision/source-DBU backlink；unit-scale binding 遵守第 12.5 节合同。Stage 2 在已验证的 scale binding 下选择能精确容纳 drawn geometry 的 canonical DBU，做 identity join、空间投影与 annotation matching；source geometry不 snap。Stage 1 不直接构造 occupancy/connectivity或 editable state。

若 query output 缺失、format/terminator漂移、header hash/top/deck/status 不匹配，Stage 1 必须返回 typed `EvidenceIssue` 与 linked `ParseResult`；required profile 中任何 binding mismatch fatal，只有显式 degraded/non-production profile 可把它保留为 suspect evidence。Layout instance/net/layer join 失败同理结构化处理，关键 device mapping 不完整时不得执行 resize。任何情况都不能伪装为 Stage 6 `ValidationResult` 或 fallback 到命名相等。

### 12.7 生产工具环境适配

生产环境差异通过 tool adapter boundary 处理，不渗入 domain / state / planning / constraint 语义层。典型配置包括：

- Calibre：binary path、SVDB path、DRC/LVS rule deck path、query mode、command dialect / template、timeout、working directory、environment variables、license handling、raw-output 保存路径。
- Virtuoso：lib/cell/view、technology library、tech-declared layer-purpose dialect / profile selection、SKILL dry-run / apply mode、`virtuoso.shape_match_tolerance`、transaction / undo policy。
- GDSII/OASIS/OA/JSON：format capability、exact unit/DBU adaptation、top/hierarchy policy、element-tagged stream-layer-key/purpose mapping、candidate/output quantization policy；adapter config 不得覆盖 canonical geometry/layer truth。
- Signoff：DRC / LVS severity policy、允许 deferred 的检查、是否要求 real-tool closure、是否允许 dummy fixture evidence。

所有工具调用都应返回中立 `ToolRunResult`，而不是只打印 stdout/stderr。它只包含 execution facts：tool name、mode、command 或 redacted command、input / raw-output refs、exit status、timeout / license / environment 分类与 stdout/stderr refs。Stage 1 importer 或 Stage 6 validation parser 另行产生以 `tool_run_id` 单向关联的 `ParseResult` / EvidenceRecord / FindingRecord；冻结的 ToolRunResult 不反向引用后产生的 parse result，tooling 也不拥有 parsed findings。Stage 1–5 orchestrator 按 active acquisition policy 把 required / terminal acquisition、execution 或 parse failure 分类为 StageFailure，optional issue 则进入 neutral audit / coverage record；Stage 6 按第 10.5 节将 tool / parse failure 映射为 per-check `execution_status=error`，完成检查后发现违例映射为 `fail`，再结合 coverage、severity 与 policy disposition 聚合为 `ValidationResult`。

工具缺失、license 不可用、timeout、rule deck 缺失或命令失败进入 ToolRunResult；format drift、terminator / query 字段缺失进入 linked ParseResult。Stage 1 acquisition 的 execution / parse failure 由 acquisition policy 决定是否形成 terminal StageFailure；Stage 6 使用上述 error/fail 分流及独立 coverage 维度，enabled-required profile 的执行错误必须 reject。v2 MVP 没有生产工具环境而检查属于声明的 post-MVP capability 时记录为 deferred；policy disabled / not-applicable 才记录为 skipped，不能用 dummy output 伪装成 signoff clean。

Calibre query command-string drift 属于 tool adapter dialect 问题。Profile 必须声明 tool/version、query DB kind、command/script template、terminator、unit、escaping与 captured-fixture hash；net/instance name 作为 typed parameter传入 adapter，禁止直接拼 shell command。不同部署通过 profile扩展并由 captured tests覆盖，不把具体命令硬编码到 domain/state。

### 12.8 Fixture 策略：基于真实 query 事实构建 synthetic cases

Fixture 的目标是稳定复现 production evidence flow，而不是复刻历史 convenience model。Synthetic fixture 应至少包含三类输入事实：GDS geometry、CDL、Calibre-like query bundle（`ixref` / `net_xref` / `device_info` / `net_shapes`）。它可以简化电路规模，但不得引入与 production fact model 相反的假设；v2 fixture generator / adapter 位于 `tests/fixtures/` 或 `tests/support/`，不得 import `legacy_mvp/`。

明确禁止把以下 legacy convenience assumption 当作 v2 正确事实：

- 把任一 FIN representation 当作通用事实。Fixture 必须声明 `FinCountSemanticsProfile`；static-fin fixture 的 active count 也必须走完整 effective-fin/active/gate/device extractor。
- `calibre_device_query.json` / `calibre_net_query.json` 作为主路径 truth。它们不是 v2 evidence bundle。
- 未经 layer mapping / trimming 验证的 effective-region claim。若 dummy `net_shapes` 只是 raw GDS bbox，应在 fixture limitation 中明示。
- target GDS/JSON 作为唯一正确性 oracle。fixture golden 只能做 regression；生产 ECO 可以有多个合法解。
- 已知 DRC violation 或 stale fixture 被 byte-golden 掩盖。spacing、enclosure、rounding、stale generation 等问题应进入 fixture limitation 或独立 correctness test。

建议 fixture 分层：

- `regression fixture`：小规模，以 canonical geometry/hierarchy/metadata 与 semantic golden 为主；byte-golden 可附加保护序列化稳定性，合法 fracture、path encoding 或 ordering 变化不直接视为几何语义错误。
- `synthetic edge case`：专门覆盖 conflict、sharing、cut、unannotated blockage、S/D swap、renumbered net、annotation-match tolerance、off-grid drift 等边界。
- `tool-captured fixture`：来自真实 Calibre / Virtuoso 输出的脱敏样例，用于验证 command parser、layer dialect、unit conversion、effective-region trimming。

Fixture 应同时保存 QueryBundleHeader、raw query captures 与 normalized YAML，并有检查证明二者同源。以下文件名只是 selected captured dialect 的示例：

- raw `iXref.temp` → `ixref.yaml`。
- raw `nXref.temp` + `NET NAMES` → `net_xref.yaml`。
- raw `device_info_<layout_inst>.txt` → `device_info.yaml`。
- raw `net_shapes_<lvs_name>.txt` → `net_shapes.yaml`。
- Proven axis-aligned-rectangle-record GDS semantic round-trip → `bbox_by_layer`；其它 capability 使用 tagged hierarchy/geometry/property schema或 fixed passthrough。
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
| FIN 被 legacy resize 当作可编辑层，且 dummy FIN 是 per-device stripe | generator 逐 device 生成 FIN stripe；backlog M8 指出 resize 删除 FIN `ShapeRecord` 与 FIN edit path | 第 4.1 / 4.5 / 6.2：static-fin/active-window 只是具名 capability；在该 profile 内 raw FIN edit 被拒绝，device extractor 对 effective FIN/active/gate关系复算 fin count。 |
| Fin attribution 只按 Y，无法区分同一 fin track 上不同 X 范围的 device | legacy parser 从 `fin_y_positions` 写 `Device.fin_track_indices`；backlog M8 要求 X/Y 几何归属 | 第 3.7 / 4.5 / 6.4：fin-count先由 selected profile 的 effective geometry与 recognized gate/channel识别 crossings，再按 device/gate-stripe/device-reduction规则分组；canonical size axes最后映射到 model-specific NFIN/NF/M等 token。 |
| legacy JSON 把 GDS、CDL、Calibre query 与工作状态揉成 parser-friendly 输入 | current config 仍有 `calibre_device_query.json` / `calibre_net_query.json`；backlog M7 sub-slice 1.7 要退休它们 | 第 2.2 / 5.10 / 12.1：v2 主路径接受 source/target CDL 或显式 raw intent、GDS / lossless geometry（proven axis-aligned rectangle record capability 内可用 bbox）、tech bundle，以及 `ixref` / `net_xref` / `device_info` / `net_shapes` evidence bundle。 |
| 同一 physical via / routing occupant 有多份 working representation | backlog M9 指出 `ShapeRecord`、`ViaInstance`、`CellOccupancy`、CSP cells 等重复表达 | 第 3.5 / 4.2 / 11.3：layout store 与 occupancy store 分别是 `AuthoritativeState` 内 geometry / occupancy 的权威 components；`ViaInstance` / segments / vias 只能是 read view 或 export view。 |
| same-net DRC 依赖 scalar `net_id`、unknown `None` 过于乐观 | backlog M11 指出 `CellState.net_id`、domain fan-out、`net_id=None` optimistic spacing | 第 3.6 / 8.1–8.6：每条 rule声明 relation与 missing-context policy；未知 annotation不改变物理连通，fallback必须有单调安全 proof。 |
| Stage 6 / decoder / edit stream 曾承担最终几何落点 | backlog M13 指出 Stage 6 replay edits、derivator/export mutation、stdout validation 等边界问题 | 第 2.6 / 9 / 10：Stage 5 commit authoritative state；Stage 6 只读 snapshot，输出 structured validation result。 |

### 13.2 Audit-derived highlights 的 architecture obligation

correctness audit 是 input-side / fixture / format 审计；其中有些问题已经被第 3–12 节吸收，有些不是 core state model 问题，但必须体现在 fixture、tech bundle 或 validation policy 中。v2 不应把这些问题当作 legacy fixture 的正常行为，也不应为它们设计兼容路径。

| audit highlight | 工程事实确认 | architecture obligation |
|-----------------|--------------|-------------------------|
| 当前 fixture 名称大量使用 “buffer”，但电路是单级 inverter | generator 中只有 `MN0` / `MP0` 两个 transistor，pins 构成 inverter；CDL cell 名是 `INV_N*_P*` | 命名问题不改变 core architecture；fixture/report/artifact 命名应遵循 semantic IR，不用文件名或 legacy label 覆盖 CDL / LVS identity。 |
| boundary dummy POLY 与 OD 相交但不在 CDL 中 | generator 在 x=0 / 108 放 dummy POLY，OD 横跨 cell width；dummy gate `net=''` | Stage 2 annotation / coverage / conflict policy 必须保留并保守处理 unannotated geometry；fixture limitation 应声明 dummy-device / LVS-recognition gap。 |
| odd width + `int()` truncation 导致 FIN / LI / VIA0 0.5 nm off-centre | generator `add_shape()` 对坐标直接 `int()`；FIN/LI/VIA0 宽度为奇数 | Source geometry以 integer DBU/exact scale保留且不 snap；新 candidate量化与 annotation/tool tolerance分开，禁止 `int()` 截断，fixture golden不能掩盖 quantization。 |
| LI pitch / width / spacing 自洽性不足，fixture 存在 LI spacing 风险 | `LI.P.1=27`，`LI.W.1=17`，`LI.S.1=17`；adjacent LI tracks 只相隔 27 nm | `drc_rules.yaml` 拥有 rule fact；candidate 触及范围内可判定的 spacing 是 Stage 5 mandatory frontline check，完整 deck 另由 Stage 6 signoff，未覆盖项进入 validation coverage gap。 |
| VIA0 LI/M1 enclosure 问题与 via-reach extension 公式不完整 | `V0.E.LI` / `V0.E.M1` 在 rule deck 中存在；generator 只按 enclosure 常量延伸 LI，未加 via half-size；M1 signal stub 宽度固定 20 nm | Candidate 触及的 via enclosure / extension 必须进入 Stage 5 mandatory predicate；若 tech predicate 不可用则 capability admission 失败。Stage 6 signoff 提供额外闭环，不能替代 pre-commit gate。 |
| `device_info` 与 legacy JSON bbox rounding / seed geometry 不一致 | legacy JSON 用 integer half pitch；`device_info` 用 float half pitch，且 seed bbox 是 synthetic gate rectangle | `device_info` 只能作为 annotation seed；Stage 1 显式解码 unit / precision，Stage 2 overlay 使用 exact coordinate conversion、registry-defined annotation-match tolerance、layer mapping 与 ambiguity policy，不能把它当 drawn geometry truth。 |
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
