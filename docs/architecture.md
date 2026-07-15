# Layauto architecture

> **文档定位。** 本文描述 Layauto v2 的目标架构：它以 backlog 中已经识别的关键问题为约束，重新定义事实源、状态所有权、修改语义、约束检查、事务提交、导出与验证边界。当前 MVP 只作为 legacy/reference implementation 与可复用代码来源；它证明过端到端链路，但不作为目标架构的正确实现基线。具体开发顺序、任务拆分与 agentic coding 执行计划应另行维护。

## 1. 项目定位与目标边界

### 1.1 Layauto 要解决的问题

Layauto 是面向 FinFET 标准单元的**增量式版图自动修改框架**。它不从零 placement / routing，也不试图替代 foundry PCell 或完整 signoff flow；它在已有 GDS 几何、CDL 电路语义、LVS/Calibre annotation、工艺规则与工程约束的共同基础上，对目标 netlist 中的局部变化进行受约束、可追踪、可验证的版图修改。

核心问题可以概括为：

> 当目标 intent 要求某个标准单元发生局部变化时，系统应如何从真实工程事实出发，规划合法修改，提交到唯一权威状态，并导出可验证产物。

这里的“真实工程事实”包括三类：

- GDS / bbox-by-layer 提供的几何事实。
- CDL / target intent 提供的电路语义事实。
- Calibre / LVS query 提供的 annotation 与 identity join 事实。

### 1.2 v2 架构目标

v2 的目标不是把当前 MVP 局部修补到“能继续跑”，而是重新收敛到以下架构原则：

- **事实源清晰。** 几何、语义、annotation、派生视图各有明确来源，不互相伪装。
- **状态所有权单一。** 版图几何和 occupancy 不应在 parser、grid、engine、decoder、output JSON 中形成多个互相漂移的权威副本。
- **修改语义基于物理实体。** 例如 `nfin` resize 不是删除 FIN，而是改变 OD active coverage，并触发相关 routing / via / derived marking 修复。
- **规划先于提交。** macro / planner 产生 candidate；constraint engine 判断可行性；transaction commit 成功后才更新权威状态。
- **导出不是修补。** Stage 6 只从 committed snapshot 导出 GDS / CDL / JSON / SKILL / report / validation result，不再作为 canonical writeback 阶段。
- **面向 agentic coding。** 模块边界、接口合同、失败条件和 backlog highlights 应足够明确，使后续开发任务可以被拆分、验证和审计。

### 1.3 当前 MVP 的角色：legacy / reference / reusable code source

当前 MVP 以单级 inverter fixture 验证了从 CDL diff 到输出 GDS / CDL / JSON / report 的端到端链路：输入版图中 NMOS / PMOS 的 `nfin = 5 / 7`，目标 CDL 要求 `nfin = 4 / 6`。这个 fixture 仍有价值，但它有三种限定角色：

1. **Legacy implementation.** 当前路径包含已知架构债，例如 FIN 可编辑、Stage 6 writeback、shape_pool 漂移、legacy JSON 输入、fixture correctness gap 等，不应作为目标设计参考。
2. **Reference behaviour.** 它可以帮助定位哪些已有代码逻辑可复用，例如 CDL parser、Calibre query parser、tech config loader、部分 GDS IO 和测试 harness。
3. **Regression seed.** 它可继续作为 v2 初期合成测试来源，但 fixture 应逐步改为基于真实 Calibre query 事实构建，而不是保留 legacy convenience JSON 作为主路径。

因此，architecture 主体描述 v2 目标状态；当前 MVP 与目标状态的差异只在必要处作为 warning 或 backlog highlight 出现，完整问题清单以 backlog 和后续 plan 为准。

### 1.4 支持范围与暂不覆盖范围

**v2 优先支持范围：**

- 单个标准单元内的增量 ECO，优先覆盖 `nfin` resize。
- 固定 standard-cell frame：cell boundary、rail、关键 M1/LI topology 与 FIN backdrop 原则上保持稳定。
- 以 GDS 几何 + Calibre query bundle + CDL 语义构建 layout state。
- 在 planner / constraint / transaction 边界内完成候选修改、可行性判断和提交。
- 从 committed snapshot 导出 GDS / CDL / JSON / SKILL / report，并执行结构化验证。

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
  → constraint feasibility check
  → transactional commit
  → derived state refresh
  → immutable snapshot
  → export + validation
```

这个闭环中有两个关键断点：

- **commit 之前**只有候选和事务上下文，不能把几何修改提前写成事实。
- **commit 之后**exporter 只能读取 committed snapshot，不能再修补内部状态。

## 2. 总体数据流与阶段边界

### 2.1 Stage 编号约定

v2 采用连续的 Stage 1–6，不再使用 MVP 中的 “Stage 1.5”。Calibre / LVS query bundle 是输入证据获取的一部分，归入 Stage 1；derived markings / derived views 是提交后的状态刷新，归入 Stage 5；导出和验证统一归入 Stage 6。

| Stage | 名称 | 目标职责 | 不应承担的职责 |
|-------|------|----------|----------------|
| Stage 1 | 输入证据获取 | 读取 CDL、GDS/bbox、Calibre/LVS query bundle、site config，形成原始 evidence | 不构建工作状态，不做几何修改 |
| Stage 2 | 事实归一化与状态构建 | 构建语义 IR、几何 store、坐标系统、annotation overlay、occupancy / connectivity / derived views 初始状态 | 不做 ECO 修改，不复制多个权威几何源 |
| Stage 3 | 约束上下文初始化 | 基于 Stage 2 的坐标系统、occupancy 与 connectivity 初始化 constraint engine、rule context、domain / trail | 不重新拥有 layout state，不规划修改，不提交状态 |
| Stage 4 | 修改意图与候选规划 | 把 target diff / intent 转换为 candidate plans | 不绕过 state / grid 手工拼最终 bbox，不提前 side-effect |
| Stage 5 | 可行性检查、事务提交与派生刷新 | 对 candidate 做约束检查，在 transaction 内提交到权威状态，并刷新 derived state / commit log | 不导出文件，不把 output 当状态源 |
| Stage 6 | 导出、生产工具交互与验证 | 从 committed snapshot 导出 artifacts，运行 self-consistency / signoff / report | 不 mutate LayoutStore、occupancy、connectivity 或 semantic IR |

### 2.2 Stage 1：输入证据获取

Stage 1 的输出是原始 evidence bundle，而不是 layout model。

输入包括：

- 原始 CDL 与目标 CDL。
- 原始 GDS 或从 GDS round-trip 得到的 `bbox_by_layer`。
- Calibre / LVS query bundle：`ixref`、`net_xref`、`device_info`、`net_shapes`。
- 技术配置：site config、layer map、Calibre layer map、DRC rules。

Stage 1 应做的事：

- 解析 CDL，提取 source circuit、target circuit 与 target intent。
- 运行或读取 Calibre query，保存可审计的 raw query output 与 normalized YAML/对象。
- 从 GDS 读取几何 bbox，保留未 annotation 的几何。
- 校验 evidence 的基本一致性，例如 cell name、单位、layer name、device identity join 是否可解释。

Stage 1 不应做的事：

- 不应把 legacy `calibre_device_query.json` / `calibre_net_query.json` 当作 v2 主输入。
- 不应根据 query 结果直接生成 `Device.fin_track_indices` 或 `Net.segments` 等工作状态。
- 不应进行 resize 或任何几何写回。

### 2.3 Stage 2：事实归一化与 layout state 构建

Stage 2 的核心不是创建某个固定 package tree，而是把 Stage 1 的 evidence 归一化为几类**来源清楚、生命周期不同、后续消费者明确**的事实对象。下面出现的 `domain.*` / `state.*` / `annotation.*` 名称是建议实现落点，用于表达职责边界；真正的架构要求是数据所有权和依赖方向，而不是这些目录名本身。

Stage 2 产生的五类主要事实对象如下：

| 归一化产物 | 主要来源 | 建议实现落点 | 后续消费者 | 不应承担的职责 |
|------------|----------|--------------|------------|----------------|
| Semantic IR | CDL source/target、target diff、`ixref` / `net_xref` identity join | `domain.circuit`、`domain.intent` | planner、transaction、CDL exporter、report / validation | 不保存可从 geometry + annotation 推导的长期几何副本 |
| Geometry store | GDS round-trip / `bbox_by_layer` | `state.layout_store` | annotation overlay、occupancy projection、planner、transaction、exporter | 不直接解释 schematic identity，不丢弃 unannotated geometry |
| Annotation overlay | Calibre query bundle：`ixref`、`net_xref`、`device_info`、`net_shapes` | `annotation.layer_overlay`，结果写入 layout store / occupancy references | planner、constraints、DRC/LVS localization、coverage report | 不替代 GDS 几何事实，不直接执行 ECO 修改 |
| Occupancy store | geometry store + layer tier + Stage 2 coordinate system | `state.occupancy` | constraint engine、planner、transaction、connectivity、read / export views | canonical discrete geometry abstraction；不是 raw geometry source，但作为候选修改、CSP 检查和 commit 的主要工作基底 |
| Connectivity state | occupancy + via edges + cut barriers + diffusion sharing / split policy + annotation refs | `state.connectivity` | constraint engine、router、transaction、validation / report | occupancy 上的 topology interpretation；不等同于 `net_id` label，不承担 semantic netlist ownership |

这些对象的产生顺序是有依赖关系的：CDL evidence 先形成 semantic IR；GDS evidence 先形成 geometry store；tech layer map / rule deck 先形成 Stage 2 coordinate system（layer grid、track coordinate、B-tier axes）；geometry store 再结合 coordinate system 和 layer tier 投影为 occupancy；Calibre evidence 通过 layer mapping 和 tolerance policy 形成 annotation overlay，并把 identity references stamp 到 occupancy / store records；occupancy 再结合 via / cut / diffusion sharing 语义形成 connectivity state。Read / export views（routing spans、gate tracks、fin attribution、annotation coverage、artifact edit view 等）只从这些权威对象重算或缓存，不作为新的事实源。

Stage 2 的关键原则：

- GDS/bbox 是几何事实源；LVS shapes 是 annotation 与 identity evidence，不是完整几何替代品。
- `Device` / `Net` 是语义 IR，不应长期保存可从 layout store 推导的几何副本。
- Annotation overlay 是 evidence-to-identity 的解释过程；其结果可以写入 occupancy / store references，但 overlay 过程本身不拥有 layout state。
- Grid / coordinate system 在 Stage 2 建立，用于 geometry-to-cell projection；它是坐标系统，不能成为 layout occupancy 的长期 owner。
- Constraint engine 可以建立检查用 cache / trail，但不能成为 occupancy 或 connectivity 的另一份权威副本。
- Unannotated shapes 必须保留，并按保守策略作为 blockage / suspect geometry 进入后续判断。

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

Stage 4 将 target intent 转换为 candidate plans。

以 `nfin` resize 为例，planner 应解释：

- 目标设备是谁。
- semantic delta 是什么，例如 `MN0.nfin: 5 → 4`。
- 该 delta 对物理实体的正确作用是什么，例如 OD active coverage 改变，而不是 FIN 删除。
- 可能受影响的 LI / VIA / M1 / C1 derived markings 是哪些。
- 是否需要 router、rip-up、局部重连或候选排序。

Stage 4 的候选是“待检查计划”，不是已提交修改。它可以包含 grid cells、shape ids、semantic ids、routing path、old/new coverage、预期 derived refresh region、provenance seed 等，但不能把候选直接写成 committed geometry。

Unsupported intent 应在 Stage 4 显式失败。失败结果应说明：哪个 intent 无法被当前 planner 覆盖、是否有部分候选被拒绝、系统是否已经保持无副作用状态。

### 2.6 Stage 5：可行性检查、事务提交与派生刷新

Stage 5 是唯一可以把候选变成权威状态的阶段。

流程：

1. 打开 transaction checkpoint。
2. 将 candidate 映射到 occupancy / layout_store / semantic state 的 staged changes。
3. 调用 constraint engine 做 DRC / connectivity / blockage / rule feasibility check。
4. 如果失败，restore checkpoint，并生成结构化失败结果。
5. 如果成功，commit 到 authoritative layout state。
6. 刷新 derived markings 与 derived views。
7. 写入 commit log / change set / provenance。
8. 生成 immutable snapshot 供 Stage 6 使用。

Stage 5 的合同：

- 失败的 candidate 不得留下 partial edit。
- 成功的 candidate 必须对下一个 candidate 可见，不需要等 Stage 6 decoder 回放。
- Commit 的目标是 authoritative layout state，而不是 output JSON、legacy edit stream 或 exporter-side patch。
- Derived markings 是 post-commit state refresh，不是 export side effect。
- v2 不把 legacy L1 EditOp / ShapeEditRecord 作为核心状态模型；Stage 5 产生的是 ChangeSet / CommitEvent，Stage 6 如需 SKILL 或 diff visualization，可从 ChangeSet 派生 artifact-specific ExportEdit。任何 edit event 都不是 authoritative geometry。

Stage 5 commit 后的 authoritative layout state 至少包括：

- semantic state：committed `Device` / `Net` / pins / params。
- geometry store：committed drawn shapes、shape ids、layer / bbox / purpose、derived / non-derived 标记与 annotation summary。
- occupancy state：A-tier / B-tier occupancy、blockage、via、cut、OD / diffusion sharing。
- connectivity state：connected components、via edges、cut barriers、component-to-net summary。
- derived layout geometry：C1 derived markings，例如 NWELL / BOUNDARY / VT / PP / NP / DNW。
- derived non-geometry views：segments、vias、fin attribution、gate tracks、annotation coverage 等可重算视图。
- commit metadata：ChangeSet、CommitEvent、provenance、validation expectations。

Immutable snapshot 是上述 committed state 的只读冻结视图，供 Stage 6 export / validation 使用。实现上它可以是 deep copy、copy-on-write view、persistent data structure 或 immutable wrapper；architecture 只要求 Stage 6 视角下它稳定、只读、可重跑。

### 2.7 Stage 6：artifact export 与 validation

Stage 6 只读取 committed snapshot、ChangeSet / CommitEvent、site/tool config、export policy、validation policy，以及可选的 fixture golden target。它不读取 mutable transaction object，也不把 Stage 1 raw evidence 或 target diff globals 当作输出事实源。

Stage 6 输入包括：

- immutable committed snapshot。
- ChangeSet / CommitEvent。
- site/tool config。
- export policy。
- validation policy。
- optional golden target。

输出包括：

- GDS。
- JSON / machine-readable layout snapshot。
- CDL。
- SKILL / Virtuoso edit script 或其它生产交互脚本。
- Human report。
- Machine-readable report / validation result。
- Visualization / debug artifacts。

Stage 6 的验证模型分为四类：

1. **Golden regression。** fixture 有目标 GDS/JSON 时，可作为回归门禁；生产场景不一定有唯一 golden layout。
2. **Self-consistency。** 导出的 GDS/JSON/CDL/SKILL/report 必须与 committed snapshot 和 commit log 一致。
3. **Signoff/tool validation。** 接入 Calibre DRC / LVS、Virtuoso dry-run、shape locate 等生产检查。
4. **Audit/human validation。** 报告说明改了什么、为什么改、谁产生、哪些检查通过、哪些检查降级或跳过。

Stage 6 不应 mutate `LayoutStore`、occupancy、connectivity、semantic IR 或 transaction state。重复运行 Stage 6 应产生相同 artifact 或可解释的时间戳/路径差异。

### 2.8 Legacy MVP 与 v2 阶段边界的关系

MVP 的 Stage 1.5、Stage 6 writeback、legacy JSON parser、decoder-as-state-updater 等做法都属于迁移时期的实现细节。v2 不再把这些边界作为目标架构：

- Calibre query bundle 归入 Stage 1 evidence。
- Legacy JSON 不进入 v2 主路径。
- Stage 2 从 evidence 构建统一 layout state，而不是从 net JSON 和 bbox JSON 交叉构建多个几何副本。
- Stage 5 提交权威状态。
- Stage 6 只导出和验证。

可复用代码应按职责重新归位，而不是保留 MVP 的 stage 编号和状态流。

## 3. 事实源、状态所有权与派生视图

第 3 节定义 v2 中哪些对象是事实源，哪些对象拥有可变状态，哪些对象只是可重算查询或导出视图。这里的 “state” 不只表示内存对象所有权，也表示 v2 修改流程中的工作事实层级。

v2 区分四类对象：

1. **Raw / normalized facts。** 来自 GDS、CDL、LVS query 和 tech config 的事实，例如 drawn geometry、semantic IR、layer map、coordinate system。
2. **Canonical working abstraction。** 由 drawn geometry 投影得到的 occupancy store。它不是原始几何事实源，但它是 candidate planning、CSP checking、transaction commit 和 connectivity update 的主要操作对象。
3. **Interpretation layers。** 作用在 occupancy 上的 annotation overlay 与 connectivity state。前者解决 identity association，后者解决 topological association。
4. **Read / export views。** 从 committed state 派生的查询、缓存、报告和 artifact view。

因此，v2 的目标不是把所有事实压缩成一个对象，而是让每一层的来源、可变性、transaction 责任和重算路径清楚。当前 MVP 中同一物理对象同时存在于 `shape_pool`、`TrackSegment`、`ViaInstance`、`CellOccupancy`、CSP engine cells、output JSON 等多个工作表示的问题，在 v2 中必须收敛为单一权威状态与若干只读视图。

v2 的基本原则是：

- GDS / bbox evidence 是 drawn geometry 的事实源。
- CDL / target intent 是电路语义的事实源。
- LVS / Calibre query 是 geometry ↔ schematic identity 的 annotation evidence。
- Layout store / occupancy store 是 committed layout state 的唯一 owner。
- Occupancy store 是后续候选规划、约束检查与事务提交使用的离散几何工作基底。
- Connectivity state 是 occupancy 上的拓扑解释层，是 same-conductor / split / sharing 判断的权威结构。
- Grid / coordinate system、constraint engine、exporter、reporter 只能读取或派生视图，不能成为第二套 layout truth。
- Read / export views 必须可从 authoritative state 重算；它们不能反向成为事实源。

### 3.1 几何事实源

几何事实来自 GDS round-trip 或等价的 bbox-by-layer evidence。v2 中每个 drawn shape 应进入 layout store，携带：

- stable `shape_id`。
- layer / purpose / optional color。
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

迁移期可以直接复用当前 MVP 中职责已经匹配的代码，但不应通过过渡包装固化错误状态模型。任何保留的数据结构都必须重新归位为只读查询、性能缓存、报告/导出视图或待删除的过渡实现，并且有明确 owner、invalidation 规则和重算路径。

### 3.2 语义事实源

语义事实来自 CDL 与 target intent，包括：

- cell / subckt identity。
- `Device`：instance name、device type、parameters、pins、layout/schematic identity join。
- `Net`：net name、net type、pin membership、layout/schematic net join。
- target delta / intent：resize、add/remove、reroute、cut/share/split 等。

`Device` / `Net` 是 semantic IR，不应长期保存可从 layout store + annotation + occupancy 推导出的几何副本。允许保存必要 anchor，例如来自 `device_info` 的 device bbox / gate seed bbox，用于打破 annotation stamping 的循环依赖；但这些 anchor 是 annotation seed，不是 geometry owner。

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

v2 的 annotation home 应以 per-cell / per-occupancy carrier 为主，而不是仅 shape-level summary。原因是一个 GDS rectangle 可能：

- 被 cut 分成多个连通区域。
- 跨越多个 device 的 diffusion sharing 区域。
- 一部分有 LVS annotation，一部分没有。
- 在不同 cells 上携带不同 net / device / pin role。
- 因 effective-region trimming 与 drawn bbox 不完全一致。

因此 overlay 的目标是把 `device_id`、`net_id`、`pin_role`、color、coverage/conflict marker 等 identity references stamp 到 occupancy cell / store cell 上。Shape-level `net_id` / `device_id` 只能作为 consensus summary：当 shape 覆盖的 cells 对 annotation 一致时可以汇总；一旦不一致，应保持 unknown / ambiguous，并把细节留在 per-cell annotation 与 coverage report 中。

Annotation overlay 只负责 identity association；via / cut / diffusion sharing 带来的 topological association 由 connectivity state 负责。二者都落在 occupancy cell / component 上，并共同形成 localization 与 DRC/LVS 判断所需的完整解释。

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

Layout store 保存 drawn geometry，是 GDS / bbox evidence 归一化后的几何事实承载者。Occupancy store 则是 drawn geometry 经 coordinate system 投影后的离散几何抽象。

二者关系是：

- layout store 记录 shape / bbox / polygon / layer / purpose / source evidence。
- coordinate system 定义 track、cell、pitch、offset、orientation、B-tier axes。
- occupancy store 记录 `(layer, cell)` 上是否被某个 shape / physical occupant 占据，以及该占据的 kind、shape reference、annotation references 和 blockage / barrier / via / OD 等语义标记。

Occupancy 不是原始事实源，因为它可由 layout store + coordinate system 重建；但它也不是普通 cache，因为 v2 的 candidate planning、CSP-frontline rule checking、transaction commit、connectivity update 都以 occupancy 为主要工作对象。一次 transaction 中被 staged、检查、提交或 rollback 的，首先是 occupancy 及其关联的 semantic / connectivity / derived changes。

目标状态容器应统一管理：

- drawn geometry records。
- A-tier / B-tier occupancy。
- shape-to-cell projection。
- cell-level device / net / pin annotation references。
- blockage / unknown / suspect geometry。
- cut / via / diffusion sharing state。
- commit-visible current state。

实现可以分层存储，例如 geometry table、occupancy table、annotation table、connectivity table，但 architecture 要求只有一个 authoritative state owner。其它对象必须是 read view、cache、transaction overlay 或 export artifact。

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
- component-to-annotation summary。

Annotation overlay 和 connectivity state 都作用在 occupancy 上，但解决的问题不同：

- annotation overlay 解决 identity association：某个 occupancy cell 与哪个 schematic/layout device、net、pin role 相关。
- connectivity state 解决 topological association：多个 occupancy cells 是否物理连通，是否被 via 连接，是否被 cut 切断，是否因 diffusion sharing 形成共同 active region。

二者共同形成更完整的 id association：

```text
occupancy cell
  + annotation identity references
  + connectivity component
  + component-to-net/device summary
  → localization / DRC / LVS / report 使用的完整解释
```

Net label 是 semantic / annotation 属性，可用于报告、localization、LVS feedback 和 target intent 对齐；是否属于同一导体则应由 connectivity component 判断。

目标合同是：

- DRC spacing / same-conductor exemption 查询 connectivity component，而不是比较 scalar `net_id`。
- `CellState` / CSP domain 不携带长期 `net_id` / `device_id` ownership。
- `net_id=None` 不表示“与所有 named nets 兼容”；unknown / unannotated geometry 默认按 blockage、suspect conductor 或 conservative conflict 处理。
- VIA 是跨层 connectivity edge，不需要用 LI/M1 上额外的 via-as-wire double stamp 伪造连通。
- CUT 是 connectivity barrier，会改变 component relation，也会影响 rule checking 和 routing feasibility。
- diffusion sharing / split 是 topology 与 semantic attribution 的共同问题，不能只作为 `Device.shared_with[]` 一类孤立 metadata。

Connectivity state 必须纳入 transaction checkpoint / restore / commit。任何 occupancy change、via add/remove、cut add/remove、OD split/share 都必须同步更新或 invalidate connectivity state。

### 3.7 Read views、localization queries 与 artifact views

v2 仍然需要从 committed state 派生的读取面，但它们的必要性来自查询便利、性能、导出、报告和 debug，而不是状态所有权。它们不应成为 architecture 主干，也不应反向成为 planner、transaction 或 exporter 的事实源。

更准确地说，v2 有三类读取面。

**第一类：occupancy queries。**

这些是对 occupancy store 的不同读取方式，例如：

- 某 layer 上的连续 occupied cells。
- 某 net / component 对应的 routing span。
- 某 via layer 上的 occupied via cells。
- 某 device 附近的 OD / LI / M1 cells。
- 某 component 的 bounding envelope。

当前 MVP 中的 `Net.segments`、`Net.vias`、routing cells 等概念应在 v2 中降级为 occupancy query 或导出/报告读取面，而不是独立 state。

**第二类：identity localization queries。**

这些查询用于把 semantic IR 与 geometry / occupancy 定位起来，例如：

- 某 `Device` 对应哪些 OD cells。
- 某 `Device` 覆盖哪些 active FIN tracks。
- 某 `Device` 的 gate anchor / gate track 在哪里。
- 某 pin role 对应哪些 LI / M1 access cells。
- 某 schematic net 对应哪些 connectivity components。

当前 MVP 中的 `Device.fin_track_indices`、`Device.gate_track_idx` 不应作为 v2 `Device` 的 canonical fields。它们应由 semantic identity、annotation anchor、FIN/POLY/OD occupancy、connectivity component 和 tech coordinate system 动态求得；如需缓存，也必须可重算并有 invalidation 规则。

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

artifact views 从 immutable snapshot、ChangeSet / CommitEvent、export policy 和 validation policy 派生。它们不能反向修改 layout store、occupancy、connectivity 或 semantic IR，也不能通过 replay edit stream 才把 geometry 变成真实状态。

**Post-commit derived layout geometry 单独处理。**

NWELL、BOUNDARY、VT、PP、NP、DNW 等 C1 derived markings 不是普通 read view。它们是由 committed A/B-tier state、device metadata 和 tech rules 派生出来的 layout geometry。刷新时机是 Stage 5 commit 之后、Stage 6 export 之前；刷新后进入 committed snapshot。Stage 6 只序列化它们，不再临时修改它们。

### 3.8 Snapshot、commit log 与 provenance

每次成功 commit 应产生：

- committed layout snapshot。
- semantic delta。
- geometry / occupancy delta。
- connectivity delta。
- derived refresh delta。
- constraint result。
- provenance：target intent → planner → candidate → constraint result → transaction commit → derived refresh → exported artifact。

成功 commit 后，authoritative layout state 必须立即反映修改，并且后续 candidate 必须读取这个已提交状态。不能等 Stage 6 decoder 或 output JSON replay 才让修改“变成真实”。

失败 candidate 必须 restore 到 checkpoint，且不得留下 partial edit。无论失败发生在 occupancy feasibility、connectivity update、derived refresh 还是 semantic update 期间，都不能让 layout store、occupancy、connectivity、semantic IR、derived state 之间出现漂移。

ChangeSet / CommitEvent 是 provenance、debug、report、SKILL、diff visualization 和 validation 的输入，但不是唯一几何事实。几何事实已经在 committed layout snapshot 中存在；Stage 6 只能读取 snapshot 与 commit log 来导出 artifact。

Immutable snapshot 是 committed state 的只读冻结视图，至少覆盖：

- semantic state。
- drawn geometry。
- derived geometry。
- occupancy。
- annotation references。
- connectivity components。
- blockage / unknown / suspect markers。
- commit metadata。

实现上可以是 deep copy、copy-on-write view、persistent data structure 或 immutable wrapper；architecture 只要求 Stage 6 视角下它稳定、只读、可重跑。

## 4. Layer tier 与物理实体抽象

### 4.1 Tier A：1D track / backdrop / routing layers

Tier A 表示可投影到一维 track 的层，例如 FIN、POLY、LI、M1。它们共享 track abstraction，但 editability 不相同：

- FIN 是 static backdrop，不是 resize 中的 editable layer。
- POLY / gate 通常是 device topology 的关键实体，不能简单按 bbox 手工改动。
- LI / M1 是 routing / local interconnect，可作为候选修改的一部分，但必须经过 occupancy 和 DRC 检查。

因此 Tier A 的共同点是坐标抽象，不代表都可被 macro 任意 edit。

### 4.2 Tier B：2D occupancy layers

Tier B 表示需要二维 cell occupancy 的层，例如 OD、VIA0、CPO、M0_CUT、FIN_CUT。

- OD 表示 active diffusion coverage，并承载 device ownership / sharing 关系。
- VIA0 表示跨层 connectivity edge。
- CUT layers 表示 barrier / split 语义。

Tier B 应投影到 occupancy store，并被 constraint / connectivity 共同消费。

### 4.3 Tier C1：derived markings

Tier C1 包括 NWELL、BOUNDARY、VT、PP、NP、DNW 等 derived markings。它们不应由 macro 直接手工 patch，而应从 committed A/B-tier state、device metadata 和 tech rules 派生。

C1 refresh 发生在 Stage 5 commit 之后、Stage 6 export 之前。导出阶段只序列化已经刷新的 C1 state。

### 4.4 Tier C2：editable annotations

Tier C2 包括 DIODE、ESD、TEXT marker 等。它们可能不进入 CSP，但仍属于 layout store 中的几何/annotation 对象。C2 edit 如果存在，也必须有 provenance 和 validation policy，不能绕过 commit log。

### 4.5 Static FIN / gate backdrop

FinFET 标准单元中的 FIN 应被建模为固定 pitch 的连续 backdrop。`nfin` 变化不应删除 FIN geometry；哪些 fins electrically active，应由 `FIN ∩ OD ∩ device region` 这类几何关系决定。

Gate / POLY 同样不是普通 rectangle patch 对象。其位置、pitch、cut、device recognition 与 routing pin 语义相关；任何 gate 相关修改都应通过 physical entity model 和 constraints，而不是局部 bbox arithmetic。

### 4.6 OD active region、diffusion sharing 与 device attribution

OD 是 resize 的核心作用对象。对于 `nfin` resize，目标不是“FIN 数量减少”，而是 device active OD coverage 减少或调整，使得被 OD 覆盖并归属该 device 的 fin 数量发生变化。

OD 还承担 diffusion sharing 语义：多个 device 可以共享同一 OD region 的 S/D 部分。v2 中 sharing 不应只是 `shared_with[]` 的孤立 metadata，而应体现在 occupancy / connectivity / semantic attribution 的一致关系中。

### 4.7 VIA / CUT / routing connectivity

VIA 是跨层连通边，不应同时被建模为 via object、B-tier cell、LI wire、M1 wire 等多个互相重叠的工作表示。CUT 是连通性 barrier；它影响 connectivity index，也影响 rule checking 和 routing feasibility。

Routing layers 的修改应通过 candidate path、occupancy check、connectivity update 与 DRC rules，而不是直接修改输出 JSON 中的 shape bbox。

### 4.8 Layer map 与 tech bundle

Layer map 描述 layer 的 GDS pair、tier、role、orientation、connectivity、derived status、Calibre derived-layer mapping 等。Tech bundle 描述 pitch、width、spacing、enclosure、extension 等 rule records。

Layer map 和 rule deck 是目标架构的参数化边界；它们不应承载 cell-specific intent、device instance name、target nfin 等输入事实。

## 5. LVS / Calibre annotation boundary

### 5.1 v2 输入事实组成

v2 fixture 与生产输入应由以下事实组成：

- CDL source / target。
- GDS 或 bbox-by-layer 几何。
- Calibre query bundle。
- Tech / site config。

Fixture 应尽量模拟真实 Calibre query，而不是发明与生产不一致的 convenience JSON。

### 5.2 GDS geometry：bbox_by_layer

`bbox_by_layer` 是 GDS 几何事实的结构化表示。它必须保留所有 drawn geometry，包括没有 LVS annotation 的 shape。

生产路径中，`bbox_by_layer` 可以由 GDS round-trip 生成；测试路径中，也应以同样 schema 生成，使 parser、overlay 和 store construction 共享同一入口。

### 5.3 LVS identity：ixref / net_xref

`ixref` 负责 layout device identity 与 schematic device identity 的 join。任何来自 `device_info` 的 layout instance name 都应先通过 `ixref` 翻译到 schematic instance，再进入 `Device` / annotation。

`net_xref` 负责 layout net / LVS index 与 schematic net 的 join。内部 net 可能被 Calibre renumber；因此 stable key 应优先使用 LVS index，并在报告中映射回 schematic name。

### 5.4 LVS geometry annotation：device_info / net_shapes

`device_info` 提供 per-device derived-layer seed shape，用于 device attribution、gate/device bbox anchor、DRC error localization。

`net_shapes` 提供 per-net routing-layer shape evidence，用于 per-cell net annotation、DRC/LVS feedback localization 和 coverage check。

这些 shape 是 annotation evidence，需要 layer mapping、tolerance 和 effective-region trimming；它们不替代 GDS geometry。

### 5.5 GDS↔LVS layer mapping

生产 Calibre query 的 layer name 可能不是 GDS layer name。例如 gate recognition layer、S/D derived layer、SADP color layer、effective conducting region layer 都可能有独立名称。

因此 v2 需要 GDS↔LVS layer mapping：

- GDS layer → 可接受的 derived layers。
- derived layer carries 哪些 annotation：`device_id`、`net_id`、color 等。
- conflict policy：哪些 collision 是 diffusion sharing，哪些是 short / ambiguity。
- trimming / tolerance policy：如何处理 cut shadow、extension、sub-nm drift。

### 5.6 Per-cell annotation overlay

目标 annotation home 是 per-cell / per-occupancy carrier，而不是仅 shape-level summary。原因是一个 GDS rectangle 可能被 cut 分成多个连通区域，也可能在 OD 上跨 device sharing 区域；whole-shape `net_id` / `device_id` 只能作为 summary。Annotation overlay 解决 identity association；via / cut / diffusion sharing 带来的 topology association 由 connectivity state 解决。

Overlay 流程：

1. 使用 layer mapping 找到 GDS cell 与 LVS derived shape 的对应关系。
2. 按 cell center / overlap / tolerance 规则 stamp annotation。
3. 对每个 shape 汇总 annotation；若 cell annotation 不一致，则 summary 保持 unknown 或 ambiguous。
4. 生成 coverage report 和 conflict report。

### 5.7 Unannotated geometry 与 conservative policy

LVS annotation 不完整是常态。v2 对 unannotated geometry 的默认策略：

- 保留几何。
- 作为 blockage 或 unknown occupancy 进入约束上下文。
- 不自动 traverse、merge、delete。
- 与 annotated geometry 冲突时保守失败或标记 suspect。
- 在报告中暴露 coverage gap。

### 5.8 Legacy JSON 的非目标定位

`calibre_device_query.json` 和 `calibre_net_query.json` 属于 MVP convenience format，不是 v2 主路径。v2 可以保留读取这些文件的短期测试入口，但 architecture、fixture 和 agentic plan 不应依赖它们构建正确状态；相关代码应按职责重构到 Stage 1 evidence acquisition 或直接删除。

## 6. 基于物理事实的修改语义

### 6.1 修改对象：物理实体、语义 intent 与候选状态

版图修改不应从“目标参数变化”直接跳到“手写 bbox patch”。正确过程是：

1. 解释 target intent 的电路语义。
2. 找到受影响的物理实体。
3. 在 grid / occupancy / connectivity 表示中生成候选状态。
4. 由 constraint engine 判断候选是否合法。
5. 事务提交后由 layout store 和 derived state 统一反映结果。

### 6.2 nfin resize：OD active coverage 变化

在 FinFET standard-cell 中，`nfin` 变化的核心含义是 device active fin count 改变。由于 FIN 是 static backdrop，active fin count 应由 OD coverage 与 device region 决定。

因此 `nfin: 5 → 4` 的目标行为不是删除一条 FIN，而是调整 device OD active coverage，使该 device 覆盖的 active fin 数减少到 4，并保持 cell frame、rail、FIN grating 的稳定。

### 6.3 Static FIN / gate backdrop 下的 resize

Resize planner 应明确处理：

- 哪些 FIN track 仍存在。
- 哪些 FIN track 被 OD 覆盖并归属 device。
- OD shrink / grow 是否影响 diffusion sharing。
- Gate / POLY 是否需要调整，或只作为 attribution anchor 保持不动。
- LI / VIA / M1 是否需要局部修复以保持 pin connectivity 与 enclosure。

任何 resize candidate 都不应包含 `remove FIN` 这类操作。

### 6.4 Routing / via / derived markings 的局部修复

OD 改变可能影响：

- source/drain LI bars。
- VIA enclosure。
- M1 stub。
- local net connectivity。
- NWELL / BOUNDARY / VT / PP / NP 等 derived markings。

这些修复应从 committed candidate 的 state delta 出发，由 planner、constraint engine 和 derived refresh 共同处理，而不是在 exporter 中临时补 bbox。

### 6.5 MVP resize path 的 legacy 偏差

当前 MVP 中的 shrink-only path 包含若干与目标语义不一致的做法，例如 FIN edit、部分 side effect 不完全事务化、Stage 6 replay 成为事实落点、legacy fixture 几何不完全符合 PCell 心智模型等。这些问题作为 v2 开发 highlight 处理，不在 architecture 中逐项展开。

## 7. 修改意图与候选规划

### 7.1 Target intent / diff model

Target intent 是 Stage 4 的输入。它可以来自 CDL diff，也可以来自未来的 ECO command、DRC/LVS feedback 或用户指定 intent。

Intent 应包含：

- 操作类型：resize、add/remove、reroute、cut/share/split 等。
- operand identity：device、net、pin、region。
- semantic delta：参数变化、topology 变化、connectivity 变化。
- constraints / preferences：保持 rail、固定 boundary、avoid region、policy 等。

### 7.2 Planner / macro interface

Planner 的输出是 candidate plan，不是 edit stream。Candidate 应尽量以 domain/state 层对象表达：

- shape ids / cell ids。
- old/new occupancy。
- semantic updates。
- connectivity effects。
- affected derived regions。
- required rule checks。
- provenance seed。

Macro 是特定 intent 的 planner 实现。它可以调用 routing/search 子系统，但不能绕过 state/constraint/transaction 边界直接输出最终 GDS bbox。

### 7.3 Resize planning

Resize planner 应先支持单 cell `nfin` resize：

- 从 semantic IR 找到目标 device。
- 从 layout store / annotation 找到 device active region。
- 基于 static FIN backdrop 和 OD coverage 生成候选 OD 修改。
- 识别受影响的 LI / VIA / M1 / derived markings。
- 生成一个或多个可排序 candidate。

Shrink-only 可以作为早期 policy，但应被表达为 candidate selection policy，而不是硬编码在 bbox arithmetic 中。

### 7.4 Routing-dependent planning

Device add/remove、net reroute、buffer insert 等 intent 需要 routing subsystem。Router 本身应只读当前 state / occupancy / constraints，返回 path plan；具体 occupancy assign/release 仍由 macro 在 transaction 内 stage。

早期 routing 范围可以限制为 single-source、single-target、single-cell、bounded search；no-path 必须是显式结果。

### 7.5 Unsupported intent handling

当 target diff 包含当前 planner 不支持的操作时，应在 Stage 4 生成 typed failure，而不是静默跳过。失败必须发生在任何事务 side effect 之前，并进入 report / validation result。

## 8. 约束系统与可行性检查

### 8.1 Constraint engine

Constraint engine 的职责是判断 candidate 是否可行，并为 transaction 提供 checkpoint / restore / commit 所需的 trail 支撑。它不应成为另一个长期 occupancy owner。

它读取：

- layout store / occupancy。
- connectivity index。
- rule records。
- candidate staged changes。
- blockage / fixed / cut / via context。

输出：

- feasible / infeasible。
- violation list。
- affected cells / neighborhoods。
- propagated domain changes。
- connectivity changes。

### 8.2 Rule records 与 predicates

Rule deck 应使用结构化 rule records 表达 min width、spacing、pitch、enclosure、extension、exact size、coloring 等规则。Constraint engine 消费其中可在 candidate 阶段判断的 subset。

Rule predicate 应尽量以 occupancy / geometry / connectivity context 表达，而不是依赖输出 GDS 后的外部 DRC 才发现基础错误。

### 8.3 Occupancy-aware DRC

DRC 判断应基于 occupancy 和 shape geometry：

- same-layer spacing。
- adjacent-track spacing。
- via enclosure。
- cut barrier。
- OD spacing / sharing。
- blockage conflict。

CSP-frontline rules 读取的是 occupancy 这个离散几何工作基底，以及 connectivity state 提供的 component relation。Rule predicates 不应直接消费当前 MVP 的 `Net.segments` 或 `Device.fin_track_indices` 作为事实源；如需 segment / fin attribution，应通过 occupancy query 或 identity localization query 获得。

当前某些 rule 可能暂时只在 signoff DRC 中检查，但 v2 architecture 应把关键局部约束逐步提升到 CSP-frontline。

### 8.4 Connectivity-aware same-conductor reasoning

Same-net spacing exemption 不应简单比较 cell 上的 scalar `net_id`。更稳健的判断是：两个对象是否属于同一连通 component。

这样可以避免：

- same net label 但物理 disconnected 的对象被错误放宽。
- unknown / unannotated geometry 被乐观处理。
- via-as-wire 多重表示被用于伪造跨层连通。

Net label 可作为 component 属性用于报告和 LVS localization，但 rule 判断应以 connectivity 为准。

### 8.5 CSP-frontline rules 与 signoff-only rules

v2 应区分：

- **CSP-frontline rules。** 修改候选必须立即满足，例如局部 spacing、via enclosure、blockage conflict、cut connectivity。
- **Signoff-only rules。** 需要完整 foundry DRC/LVS 或复杂 coloring 才能判断的规则。
- **Deferred rules。** 目标架构已留接口，但当前实现暂不覆盖。

Validation report 必须说明哪些规则在 CSP-frontline 检查，哪些交给 signoff，哪些被降级或跳过。

### 8.6 Rule gaps 与 correctness highlights

v2 开发应特别避免继承 fixture 中已知 correctness gaps，例如 VIA0 enclosure、LI spacing、raw net_shapes effective-region 语义、device_info hardcoding、format unverified 等。它们应进入 plan / tests / validation，而不是作为 architecture 正常行为。

## 9. 事务提交、派生状态与变更记录

### 9.1 Transaction scope

Transaction scope 必须覆盖：

- layout store geometry changes。
- occupancy changes。
- connectivity changes。
- semantic state changes。
- derived cache invalidation。
- commit log append。

Transaction 的核心 staged object 是 occupancy changes。Geometry changes、semantic changes、connectivity changes、derived refresh / invalidation 和 commit log append 都围绕 occupancy change 保持一致。只要其中任一部分失败，整个 candidate 必须 restore 到 checkpoint。

### 9.2 Commit to authoritative state

Commit 的目标是 authoritative layout state，不是 output JSON，也不是当前 MVP 的 EditOp stream。成功 commit 后，后续 planner、constraint engine、derived refresh 和 exporter 都应读取同一个 committed state。

Authoritative layout state 是一组有明确所有权关系的 committed state graph，至少包括 semantic state、geometry store、occupancy state、connectivity state、derived layout geometry、derived non-geometry views 和 commit metadata。实现可以把这些对象拆分到不同模块，但 commit 必须保证它们在同一 transaction 边界内一致更新或一致回滚。

### 9.3 Rollback consistency

失败回滚后必须保持一致：

- geometry 没有 partial bbox change。
- occupancy 没有 partial assign/release。
- connectivity 没有残留 union / cut state。
- semantic IR 没有 partial parameter update。
- derived views/cache 没有 stale exposure。
- commit log 不记录成功事件。

### 9.4 Derived markings refresh

Derived markings 的区分来自 layer tier 对物理实体的抽象。C1 derived markings 是会进入 exported layout 的几何层，例如 NWELL、BOUNDARY、VT、PP、NP、DNW；它们属于 layout state 的一部分，但其几何来源是 committed A/B-tier state、device metadata 与 tech rules，而不是 macro 手写 shape。

C1 derived markings 应在 commit 后根据 affected neighborhood 刷新。实现可以选择全量 recompute 或 subscription-driven incremental recompute；architecture 要求 derived refresh 发生在 Stage 5 commit 之后、Stage 6 export 之前，并作为 committed snapshot 的一部分被导出。

### 9.5 Derived views refresh

Read views 与 C1 derived markings 不同：它们通常不是单独的 exported physical layer，而是对 committed state 的查询视图或 materialized cache。Routing spans、vias、fin attribution、gate tracks、annotation coverage 等读取面必须从 committed state 重算或失效。

Read views 可以为了 planner、constraint、report 或 debug 被缓存，但不能被当作独立 truth；任何 cache 都必须能从 authoritative layout state 重建。

### 9.6 Commit log / change set / provenance

Commit log 应记录：

- target intent。
- planner / candidate。
- constraint result。
- committed geometry / occupancy / semantic delta。
- derived delta。
- validation expectations。
- responsible code path / agent / macro。

这使报告、debug、DRC/LVS feedback 和回归定位可以从 artifact 追溯到具体 intent。

### 9.7 ChangeSet / CommitEvent / ExportEdit 的定位

v2 不把 legacy L1 EditOp / ShapeEditRecord 作为核心状态模型。Stage 5 commit 产生 ChangeSet / CommitEvent，用于描述 semantic、geometry、occupancy、connectivity 与 derived refresh delta，并记录 provenance。

Stage 6 如需生成 SKILL、diff visualization 或 human report，可以从 ChangeSet 派生 artifact-specific ExportEdit。ExportEdit 是 artifact 指令，不是 committed geometry；当前 MVP 的 EditOp 形态不进入 v2 architecture。

Derived-shape edit rejection 仍然重要：planner / macro 不应直接覆写 C1 derived shape，除非通过 derived refresh 或明确的 derived-rule provenance。

## 10. Export、生产工具交互与验证

### 10.1 Stage 6 no-mutation boundary

Stage 6 输入是 immutable committed snapshot、ChangeSet / CommitEvent、site/tool config、export policy 和 validation policy。它不允许修改内部状态。这个边界使导出可重跑、可比较、可审计。

Stage 6 禁止：

- 修改 layout_store / occupancy / connectivity / semantic IR。
- 运行 derived refresh。
- replay current-MVP edit stream 来生成 canonical geometry。
- 根据 target diff globals 修改输出 params。
- 把 validation mismatch 静默降级为 stdout。

### 10.2 GDS / JSON / CDL export

Exporter 应从 snapshot 生成：

- GDS：layer-purpose mapping、units、shape order、derived markings。
- JSON：machine-readable layout snapshot 或 debug representation。
- CDL：从 semantic IR 输出 device / net / params，不从 Stage 1 diff globals 硬编码。

输出顺序和单位转换应可测试，避免 byte-golden drift 无法解释。

Stage 6 artifact 从 snapshot / ChangeSet 的读取边界如下：

| Artifact | 从 snapshot 读取 | 从 ChangeSet / CommitEvent 读取 | 禁止事项 |
|----------|------------------|----------------------------------|----------|
| GDS | geometry store、derived markings、layer map、units | 可选 shape order / provenance reference | 不 replay current-MVP edit stream 修补 geometry |
| JSON snapshot | semantic、geometry、occupancy、connectivity、annotation summary | commit id、parent id、change summary | 不重新计算权威状态 |
| CDL | semantic IR snapshot | semantic delta provenance | 不从 Stage 1 diff globals 硬编码 |
| SKILL | shape ids、bbox、layer-purpose、snapshot geometry | ExportEdit、provenance | 不用不确定 bbox 静默删除；必须 dry-run / assert |
| Human report | snapshot summary | intent、candidate、constraint、commit、validation | 不只统计 macro edit ops |
| Validation result | snapshot、artifacts、policy | commit id、validation expectations | 不只打印 stdout |

### 10.3 SKILL / Virtuoso interaction

SKILL / Virtuoso script 是生产交互 artifact。它应包含：

- layer-purpose mapping。
- shape locate / bbox tolerance / identity matching。
- dry-run assertion。
- 每个 edit 的 provenance comment。
- ambiguity / missing-shape failure。

占位式 printf helper 不能作为生产成功。

### 10.4 Calibre DRC / LVS closure

生产 validation 应接入 Calibre DRC / LVS：

- DRC clean 是生产 fatal gate。
- LVS must match target CDL。
- DRC/LVS violation 应定位到 schematic net / device / candidate / commit provenance。
- Tool command failure、format drift、missing binary、timeout 都应成为结构化 validation result。

### 10.5 Validation model

Validation 分层：

1. **Golden regression。** 用于 fixture / CI，检查输出是否与预期 golden 一致。
2. **Self-consistency。** artifact 与 snapshot / ChangeSet / semantic IR 一致。
3. **Signoff validation。** DRC/LVS/SKILL dry-run 等生产检查。
4. **Audit validation。** human report 和 visualization 可解释修改。

Self-consistency 至少应检查：GDS round-trip geometry 与 snapshot geometry 一致；CDL export 与 semantic IR snapshot 一致；JSON export 与 snapshot content 一致；SKILL dry-run 能定位 snapshot 指定 shape；report 中 change counts 与 ChangeSet 一致；derived markings 已经包含在 snapshot 中，而不是 Stage 6 临时生成。

没有 golden target 的生产 ECO 仍然可以通过 self-consistency + signoff + audit 给出 pass/fail。

### 10.6 Reports、visualization 与 debug artifacts

Report 应覆盖：

- 输入 evidence 摘要。
- target intent。
- candidate 选择。
- constraint result。
- committed changes。
- derived changes。
- validation results。
- skipped / warning / degraded checks。

Visualization 应从 committed delta 和 validation mismatch 生成，而不是从 pre-commit edit stream 拼图。

## 11. v2 模块组织

### 11.1 建议 package layout

下面的 package layout 是一种建议实现形态，用于把前文的职责边界落到代码组织上。它不是唯一可行目录结构；目录名可以调整，但依赖方向和状态所有权不能反转。尤其需要保持：semantic domain 不依赖 IO / solver，state 拥有权威 layout 状态，annotation 只负责 evidence-to-identity overlay，constraints 消费状态但不拥有长期状态，export 只读 snapshot。

```text
layauto_v2/
├── domain/
│   ├── geometry.py
│   ├── circuit.py
│   ├── intent.py
│   └── identifiers.py
├── state/
│   ├── layout_store.py
│   ├── occupancy.py
│   ├── connectivity.py
│   └── snapshot.py
├── annotation/
│   ├── calibre_bundle.py
│   ├── layer_overlay.py
│   └── coverage.py
├── planning/
│   ├── candidate.py
│   ├── resize.py
│   ├── routing.py
│   └── unsupported.py
├── constraints/
│   ├── engine.py
│   ├── rules.py
│   └── drc_context.py
├── transactions/
│   ├── transaction.py
│   ├── commit_log.py
│   └── change_set.py
├── derive/
│   ├── markings.py
│   ├── views.py
│   └── subscriptions.py
├── importers/
│   ├── gds.py
│   ├── cdl.py
│   └── calibre.py
├── export/
│   ├── gds.py
│   ├── cdl.py
│   ├── json.py
│   ├── skill.py
│   └── reports.py
├── validation/
│   ├── self_consistency.py
│   ├── signoff.py
│   ├── golden.py
│   └── result.py
└── pipeline.py
```

### 11.2 `domain/`

`domain/` 定义稳定、IO-independent 的领域对象：geometry primitives、circuit IR、target intent、stable identifiers。它不依赖 Calibre、GDS writer、constraint engine 或 pipeline。

### 11.3 `state/`

`state/` 拥有 authoritative layout state：layout store、occupancy、connectivity index、snapshot。它定义哪些对象是 truth，哪些是 view/cache。

### 11.4 `annotation/`

`annotation/` 负责消费 Calibre bundle，执行 GDS↔LVS layer overlay，生成 coverage / conflict / suspect reports。它不直接执行 ECO 修改。

### 11.5 `planning/`

`planning/` 负责从 intent 和 current state 生成 candidate。Resize、routing-dependent macros、unsupported intent failure 都在这里表达。

### 11.6 `constraints/`

`constraints/` 负责 rule records、rule predicates、constraint engine 和 DRC context。它判断 candidate 是否可行，不拥有长期 layout state。

### 11.7 `transactions/`

`transactions/` 负责 checkpoint、restore、commit、change set 和 commit log。它是 candidate 变成 committed state 的唯一门。

### 11.8 `derive/`

`derive/` 负责 C1 markings、derived views、subscription / affected-neighborhood recompute。它只从 committed state 派生。

### 11.9 `importers/`

`importers/` 负责 GDS、CDL、Calibre query 的文件 / 工具格式适配。格式漂移应局限在这里和 `annotation/` 的边界内。

### 11.10 `export/`

`export/` 负责 GDS、CDL、JSON、SKILL、reports 等 artifact 生成。它只读 snapshot，不修改 state。

### 11.11 `validation/`

`validation/` 负责 self-consistency、golden regression、signoff integration、structured result。Validation result 应能驱动 pipeline failure policy。

### 11.12 `pipeline.py`

`pipeline.py` 负责串联 Stage 1–6，并将每个阶段的输入输出显式化。它不应承载宏逻辑、规则逻辑或导出细节。

### 11.13 legacy MVP 代码复用原则

复用现有代码时遵循：

- 可复用 parser / config / IO 的局部逻辑，但要换到 v2 职责边界下。
- 不复用会保留错误状态所有权的结构，例如 grid 持有 occupancy、decoder 作为 canonical updater。
- 不把 legacy fixture JSON 作为 v2 主事实入口。
- 所有复用代码需要有 parity / regression tests 证明行为符合 v2 contract。

## 12. 配置、tech bundle 与环境边界

### 12.1 `site_config.yaml`

`site_config.yaml` 描述一次 run 的环境和输入输出路径：CDL、GDS、Calibre query mode / svdb、tech files、output dir、validation policy 等。它不应承载 device instance、target nfin、cell-specific geometry 等事实。

### 12.2 `drc_rules.yaml`

`drc_rules.yaml` 描述 rule records。Rule 应结构化，包含 id、type、layers、value、severity、condition、notes 等字段。

### 12.3 `layer_map.yaml` / `calibre_layer_map.yaml`

`layer_map.yaml` 描述 GDS layer 的 tier、role、orientation、connectivity、derived status。`calibre_layer_map.yaml` 或等价 schema 描述 LVS derived layer 与 GDS layer 的映射、carries 字段、color / multi-patterning metadata。

### 12.4 配置边界：哪些信息不进入 config

以下信息来自输入 evidence，不应写入 config：

- Device instance name。
- Device type 与 pins。
- Net membership。
- `nfin` target delta。
- Cell name。
- Shape bbox。
- Calibre query result。

### 12.5 生产工具环境适配

生产环境差异应通过 adapter / config 边界处理：

- Calibre binary path、SVDB path、timeout、query mode。
- Virtuoso lib/cell/view、SKILL dry-run mode。
- Foundry layer map / purpose map。
- Unit precision 与 bbox tolerance。

工具失败必须结构化上报，而不是仅打印 stdout/stderr。

### 12.6 Fixture 策略：基于真实 query 事实构建 synthetic cases

Synthetic fixture 应模拟生产事实流：GDS geometry + Calibre-like query bundle + CDL。它可以简化电路规模，但不应引入与生产事实模型相反的 convenience assumption，例如 per-device FIN、current-MVP net JSON truth、未验证的 effective-region claim。
