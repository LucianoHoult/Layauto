# W025 从已发布版图测量 CUT 后的 LI 间距

## 任务要求（PM）

**阶段为可执行，归属 M1 的 Stage 3。** 执行分支为 `codex/w025-effective-li-spacing`。在 [W024 的只读规则上下文](W024-stage3-rule-context.md#pm2-integration) 上实现第二条规则 `T06.li_spacing`。给定一个已发布的第 0 版，下游应能看到本地互连层（LI）在切割后还剩哪些区域、最近的两个区域相距多少、是否达到本次工艺规定的最小间距。执行 session 实施，独立 reviewer 核对方案和代码，PM 验收。

依据为[架构 §2.4、§8、§11.7](../architecture.md)、[绑定的 T06 声明](../../tests/fixtures/w003_m1/tech/rules.json)和[物理算子](../../tests/fixtures/w003_m1/tech/physical.json)。有效区域由 Stage 2 产生，可沿版本中的 region、piece、原 LI 及 CUT 找回实际几何和来源。适用范围为当前 synthetic 工艺。后续节点承接其余八条规则、完整目标判定、零修改收口和导出。

**与 Stage 5 的交接。** W025 交付 T06 和 T07 的只读求值能力。样例显式调用它们来验证测量与来源。M1 的正式运行由 Stage 5 在 Stage 4 确认目标已满足后，调用同一套检查器检查当前快照并决定能否收口。该调用链在后续 M1 集成任务实现。[架构 §2.6](../architecture.md#stage5-rule-invocation)

<a id="spacing-family"></a>

### 本轮开发边界：共用最小间距检查

T06 和 T07 通过已绑定的工艺声明选择检查对象、最小距离、单位、接触及关系条件。T07 读取金属 M1 的原始矩形；T06 读取 LI 经 CUT 后的有效区域，包括一个区域由多块矩形组成的情况。两条公开路径共用精确测距、阈值比较和几何见证的计算。共用计算读取只读几何和已绑定的参数，版本认证及各输入的来源由入口保留。按现有输入合同核对 ID、evaluator、范围和物理算子；当前工艺只接受已登记的规则版本。[W024 测距实现](../../layauto_v2/constraints/rules.py) · [现有工艺输入合同](../../layauto_v2/tech/schema.py)

独立 reviewer 沿两条入口核对实际调用。用一个轻量对照说明，同一种几何与接触语义用于另一金属层时，测距代码能够原样复用；可在工艺规则绑定之后测试另一层的同类操作数。正式工艺文件与端到端验证使用当前支持的层。另在 2 nm 样本的临时工艺副本中把 T06 阈值改为 3 nm，同步谓词中的数值并重绑 header。预期原图和 2 nm 实测值相同，T06 变为一对违规，T07 仍为 5 nm 通过。

PM 已在 `f6356cb`、Python 3.12.14 上验证这个变阈值输入。用 `stage_gap(parent, 2)` 构造临时输入，在 `tech/rules.json` 修改 T06 的 `parameters.min_distance_nm` 和 `predicate`，按现有 helper 重绑 header 后，经公开入口发布并打开快照。规则文件 SHA-256 为 `65c8ecd3bc0c168f6e5d505561d6467a57dc38f5f9409684bd834dbe956a647d`，GDS SHA-256 为 `7d25599e5deb32ff67c4f5b7ac3b9b84fa931b56131170494ff659fc25fadec3`。快照读回的线端为 X=139、141 nm，规则阈值为 3 nm，T07 为 5 nm 通过。该版本的 T06 状态仍为待求值。

**给后续候选修改的设计交接。** 用下方两份样本回答“只移动 CUT 的右边缘，会重查哪些 LI”。从切口的旧位置和新位置追到受影响的原 LI、切后的两侧区域，再查最小间距范围内的邻近 LI。给出图形来源、比较范围和可独立核对的预期；若局部范围无法证明完整，可退回全层精确检查。W025 用已发布快照验证这条依赖和判定。到 M2 首次真实修改，再用事务内候选验证触发重查、安全排除违规选择以及撤回试改。传播只排除能证明违规的选择，最终仍由 Stage 5 在具体候选上执行精确必需检查。[架构 §8.1–8.6](../architecture.md#8-约束系统与可行性检查)

### 两个可手算的对照

使用 W024 正常完整 cell 的两份临时副本。各自追加同一条 LI，矩形为 `(130,20)–(150,24)` nm。切口在 Y 方向穿过整条 LI，只改变它的右边缘。两份副本使用同一工艺规则和同一套 32×16 DBU 的 LI 索引格，重新绑定后分别发布，测量入口读取已封存的上下文。第一例坐标来自 W004 的[独立切割样本](../../tests/fixtures/w003_m1/special/cut_islands/spec.json)，其中另有一条远端 LI；该独立样本的三对间距有[手算答案](../../tests/fixtures/w003_m1/special/cut_islands/oracle.json)。完整 cell 中追加的两条记录位于 GDS 字节偏移 2672（LI）和 2736（CUT）；独立小样本对应的偏移为 182 和 246。完整 cell 和独立样本分别核对。

| CUT 的 X 范围 | 同一格 (4,1) 内留下的两块 LI | 对该对以及全 cell 的预期 |
| --- | --- | --- |
| 139 到 141 nm | 左块 36 nm²，右块 36 nm² | 最小间距 2 nm，达到 2 nm 阈值，T06 通过 |
| 139 到 140 nm | 左块 36 nm²，右块 40 nm² | 最小间距 1 nm，该对违反 T06；M1 上的 T07 仍为 5 nm 通过 |

两份完整输入各有 5 个有效 LI 区域，共 10 个无序对。正常主图中原有的 3 条 LI 位于 GDS 偏移 1648、1712、1776。按原图坐标及上述切口复算全部 10 对，2 nm 例中均达标，1 nm 例中仅切口两侧违规。

[PM 输入构造与已发布图形核对](W025/pm_inputs.py)已在 W024 的实际合并提交 `90dcd50`、Python 3.12.14 上实跑。两次均成功发布并读回表中的两个有效区域，原 LI 和 CUT 偏移分别为 2672、2736，查询前后仓库一致，T07 均为 5 nm 通过。两个样本的 T06 判定由执行 session 实现。用下列命令从仓库根目录复现输入。

```sh
PYTHONPATH=.:tests/contracts python -B docs/tasks/W025/pm_inputs.py
```

### 验收项

| 项 | 可观察结果 |
| --- | --- |
| A1 版本和规则 | 从同一只读上下文的不可变快照、绑定的工艺声明及算子实算 T06。报告显式给出版本、规则字段和单位。保留使用者已有的 W024 单规则入口及其行为，并提供在同一次检查中读到 T06、T07 各自结果的入口；正常配置的报告仍列出其余八条待求值规则。两条规则共用同一份已打开的上下文，并按[本轮开发边界](#spacing-family)复用最小间距检查。 |
| A2 全 cell 精确间距 | 在完整 cell 范围比较独立的有效 LI 区域。用精确几何和所选同层接触语义处理手算两例。保留同一 drawn LI 经 CUT 分开的不同区域，区分一个连通区域内部的矩形分块。若一个区域含多块矩形，依据其实际边界求距。对同格、同来源或相同网名的分离区域照常测量。 |
| A3 来源和依据 | 从结果找回获得最小值的实际位置或矩形、两侧 region/piece、原 LI 和参与切割的 CUT 的 GDS 位置与摘要，以及阈值在所选规则文件中的字段。用独立样本或独立手算复核距离和归属。固定 fixture、oracle 和 PM 的参考程序仅作对照。 |
| A4 缺项与兼容 | 使用一个可通过上游封存的、与 T06 检查器能力不符的声明，核对 T06 按绑定 policy 报出具体字段和原因，T07 可独立求值。沿用上游已拒绝的输入、检查异常和跨版本拒绝语义。核对正常、违规及缺项查询前后的仓库和 attempt。 |
| A5 交付与验证 | 提供真实输入到公开结果的示例，展示两份样本的 T06/T07、最近一对及来源。记录上下文加载与求值的增量成本。执行、review 和 PM 依[验证分工](../collaboration/rules.md#verification-reuse)运行新增及受影响范围；双解释器全量留在完整 mandatory 与无修改闭合的阶段集成。 |

## 方案、实施与复核

先列出绑定入口、区域和分块的身份、处理接触与最小间距的方式，以及下游怎样分别查询两个规则的结果。核对现有 W009/W010 精确几何、W023 快照和 W024 的判据，复用合适的部分。独立 reviewer 在实现前审方案，在交付前从原始几何独立核对至少一个等号样本和一个违规样本，再检查一个多块区域或标签容易引起误判的例子。执行和 reviewer 各自在此记录版本、检查、结果和剩余限制。

## 执行 session 启动指令

> 在 `codex/w025-effective-li-spacing` 执行 W025 A1–A5。先按“本轮开发边界”写方案，说明如何选择原图或 CUT 后有效区域、复用精确间距计算，以及单改 CUT 时要重查哪些 LI；交独立 reviewer 复核后实施。保留 W024 公开入口，通过同一次只读调用取得 T06、T07 和其余八项的状态。验证 2 nm 等号通过、1 nm 违规，以及固定原图只把阈值改为 3 nm 后的判定。每例都能回查规则、LI、CUT 和几何见证。覆盖多块区域、错误声明及既有 T07 行为。开发、交付和 review 跑新增及受影响范围，按受测版本复用已有证据。推回原分支交 PM 验收。Stage 5 正式调用和 M2 候选传播各按路线图后续集成。

### 执行方案（起点 879079ec）

沿用 W024 的 open_constraint_context 认证一次 run、head、snapshot 和工艺。保留 check_m1_spacing 的 T07 单查；新增 check_spacing，在同一上下文按 catalog 顺序给出两个 RuleCheck 及其余声明的状态。按登记的 ID、exact_evaluator_ref、schema、scope 选择适配器，从声明读取 parameters.min_distance_nm，核对 predicate、nm、geometry_only/none 和绑定的 spacing/1、same_layer_contact/1；T06 另核对 CUT 差集语义。能力缺项沿用定位到字段的 policy 结果。

T07 每个 drawn M1 BOUNDARY 是一个单矩形操作数。T06 从快照的 LI 原记录沿 effective_by_record 找到各独立 region，每个 region 以准确的 piece 矩形集合为操作数。共用全层无序对循环，对每对搜索 piece 的笛卡尔积，取最小闭矩形距离平方；零距离并列时优先保留实际发生正面积或正长度边接触的见证。点触距离为零，仍参与阈值比较。用 canonical_tick_nm 作精确平方换算，严格小于才违规。见证保留 region/piece、owner、CUT 和 GDS 位置、摘要；用报告的版本和 rule.location 回查快照、工艺字段。相同 owner、格号、标签均不消对。

CUT 右缘从 141 移到 140 nm 时，原 LI（偏移 2672）的左块仍止于 139、面积 36，右块左界从 141 移到 140、面积从 36 增到 40 nm²。两侧身份和成对关系均需重取。未来局部重查应从新旧 CUT 的并集查所有相交 drawn LI，重建每个 owner 的全部旧/新 region（含消失、增生、分裂和合并）。按两版完整 region 的各块外扩本次阈值，查询所有相交格及边界，去重 region 后精确比较受影响区域彼此及与候选邻居。索引须覆盖旧/新状态；要更新全局最近值还须保留其余对的结果或重算。此次两份快照均直接查全层 5 个区域、10 对，作为完整性对照。

### 实施与验证交接

实现与测试提交为 `d1252db5eec5236c5eee438181caa5f7698a4e50`。运行[公开示例](W025/example.py)可从每份临时完整输入发布第 0 版，删除临时目录，再从同一上下文查询两条规则。报告的 `for_rule` 按规则 ID 取结果，`operands` 保留各区域全部分块，`pairs` 保留每对最近分块，`violations` 列出不达标对。两侧见证的 `source` 指向 drawn 记录；`region_id`、`piece_id` 和 `cuts` 可结合报告版本查证有效边界与 CUT 来源。示例打印 GDS 字节偏移、摘要及 `tech/rules.json` 内的阈值字段，本组 T06/T07 分别为 `/rules/5/parameters/min_distance_nm` 和 `/rules/6/parameters/min_distance_nm`。

| CUT 右缘（nm） | T06 实测 / 阈值（nm） | T06 状态和违规对数 | T07 实测 / 阈值（nm） | 首次打开上下文（s） | 组合求值（ms） |
| ---: | ---: | --- | --- | ---: | ---: |
| 141 | 2 / 2 | pass，0 | 5 / 5，pass | 1.271355 | 1.151 |
| 140 | 1 / 2 | violation，1 | 5 / 5，pass | 0.883231 | 0.983 |
| 141 | 2 / 3 | violation，1 | 5 / 5，pass | 0.848112 | 0.964 |

每组均有 10 对 LI、6 对 M1、8 条 pending。后两组仅原 LI（2672）经 CUT（2736）分出的左右两块违规；第一、三组连两端 region 和 piece 的 ID 都相同。T07 最近两条原 M1 位于偏移 2480、2544。计时取同次运行中发布完成后的两个单次墙钟区间，含同时运行其他定向检查的主机负载。对缺项样本，将 T06 scope 改为仅含带标签区域并重新封存，得到 indeterminate、具体 scope 字段及绑定的 indeterminate_then_reject，T07 仍通过。三组及缺项均检查 attempt 和仓库查询前后相等。

[独立 reviewer 的方案与代码复核、全对复算表](W025/review.md)记录了两条公开路径的实际调用链、同名 LI 和另一份 L 形样本。[独立探针](W025/review_gds.py)以真实 GDS 坐标和单位计算，再与公开结果对比。供 PM 在集成版本按风险复跑；当前等待 PM 验收。

在仓库根目录复现本次新增与受影响范围（Linux，CPython 3.12.14，PyYAML 6.0.3，pytest 9.2.0，mypy 2.4.1）：

```sh
python -B -m pytest -p no:cacheprovider -q tests/unit/test_w02{4,5}_spacing.py tests/contracts/test_w024*.py tests/contracts/test_w025_effective_li.py
python -m mypy layauto_v2/constraints
PYTHONPATH=.:tests/contracts python -B docs/tasks/W025/example.py
PYTHONPATH=.:tests/contracts:docs/tasks/W024 python -B docs/tasks/W025/review_gds.py --published --notch
```

**实跑结果。** W025 几何单测 5 项、公开发布合同 5 项，W024 单查、错误路径、跨版本认证及模块依赖等 28 项，合计 **38 项通过**。联合收集也取得 38 项。受影响的 constraints 包共 6 个源文件通过 strict mypy。pytest 的外部 anyio 插件报告一个 pytest 10 API 弃用提醒。除实施前方案外，reviewer 已在上述产品提交上完成原图复算及调用链检查，复核证据提交为 `f9c4fd1`。

**采信与集成边界。** 与 W024 修复产品 `c311297` 比对，pipeline、state、domain、tech 和固定 fixtures 无差异；沿用 [W024 已验收记录](W024-stage3-rule-context.md#pm2-integration)作为这些生产者的基线，本次对变更的查询路径使用上述新实测。若合并改变绑定、几何、缺项行为或输入，须补跑对应定向合同与独立原图探针。双解释器全量由 PM 留在完整 mandatory 与零修改收口的阶段集成。Stage 5 正式调用与 M2 事务内候选重查按原路线图推进。
