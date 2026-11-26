# W022 核对第 0 版发布前的逐层几何与占用

[PM-01 补修交接与复现命令](#pm01-repair) · [补修独立复核](W022/pm01-review.md)

## 任务要求（PM）

**当前状态为待补修。** 已声明二维网格的 POLY 能完整重建，但逐层校验仍将其投影判为失败。PM-01 经单变量输入复现。[PM 接收与补修](#pm1-receipt)

**本轮交付运行代码。** 从 W021 的 `ProposedInitialState` 出发，对本次捕获的每个本地层回答三个问题：哪些原始几何应保留、哪些占用应能从原图或有效区域重建、各项是否有足够依据进入后续发布步骤。下游能直接读取通过的检查及带来源的缺项。任务属于 M1 的 Stage 2，执行分支为 `codex/w022-layer-initialization-checks`，产品基线为 W021 实际集成提交 `565412819167cea6165486e5ee4b4319c6aca52f`。[W021 验收](W021-proposed-initial-state.md#pm2-integration) · [架构 §2.3](../architecture.md#23-stage-2事实归一化与-layout-state-构建) · [逐层生命周期](../architecture.md#94-policy-controlled-geometry-finalization) · [初始化事务](../architecture.md#118-transactions)

### 输入与手算依据

保留原 W003/W004 fixture 和 W018 配置。用临时输入副本，经原有 tech bundle 显式选择坐标文件并重绑 query header。以下两份坐标各有用途。

| 输入 | 预期与来源 |
| --- | --- |
| [W018 原样例](W018/layer-discretization.example.yaml) | 15 层中的 FIN、LI、M1 有坐标；BOUNDARY、MARKER 显式跳过投影；其余 10 层缺声明。POLY 仍有一条原图，能核对位置，无法初始化栅轨。 |
| [W022 完整 synthetic 正例](W022/layer-discretization.synthetic.yaml) | 沿用 W018 已有的 5 项声明。POLY 采用既有垂直栅测试的绝对轨道，保持 W018 的全局原点 (0,0)，令 -3 号轨中心为 60 nm、测试节距为 9 nm。另 9 层各自显式选用与 LI 相同的测试格边。假设只用于本正例。生产参数由工艺配置提供。[原 POLY 定向见证](../../tests/contracts/test_w018_projection.py) |

完整样例沿用 W018 schema，SHA-256 为 `cd25a045187c22d23040ea45363043b33b497d6318890a73a15782b293346009`。PM 已从实际读取的 GDS 走 W008 几何、W009 有效区域与 W018 投影，得到 15 层、40 条 drawn 记录。38 条需投影的原图获得 220 个 drawn 片，另有 92 个 effective 片；两条显式跳过投影的原图仍保留。PM 对照[手工样本](../../tests/fixtures/w003_m1/spec.json)按半开格边独立重算了 220 个 drawn 片。形状的层名在示例中用于定位，算法依据各层的显式声明选择。

PM 也从实际合并版走完 W006 读取、W020 组装及 W021 候选构建。显式片数预算 312 时，候选返回 10 层已重建、2 层显式跳过、3 层无本地图形。POLY 的 -3 号轨回到 GDS 偏移 432，M1 末格仍为 130 DBU²。组装前后仓库快照相等。这个结果验证 W022 正例的输入和上游入口；逐层保真校验本身由执行者交付。

复用 W018 的临时输入流程时，在 `PYTHONPATH=.:tests/contracts` 的仓库根目录可用下段准备输入。随后按 W021 示例对 `root / 'site_config.yaml'` 调用完整入口。本样例的 312 是实测片数，产品继续使用调用方给定的预算。

```python
from pathlib import Path
from shutil import copyfile
from w005_cases import copy_input, rebind
from w018_cases import COORDINATE_URI, select_projection

root = copy_input(temp_dir)  # 调用方创建的临时目录，类型为 Path
select_projection(root)
copyfile(Path("docs/tasks/W022/layer-discretization.synthetic.yaml"), root / COORDINATE_URI)
rebind(root)
```

### 验收项

| 项目 | 可复跑结果 |
| --- | --- |
| A1 按层核验并保留依据 | 从完整运行输入走 W020 → W021 → 本次检查。输出与同次候选、原始证据、坐标及比较器绑定。对每个本地层分别给出生命周期、原图与有效片的检查范围、结论及来源；可区分显式跳过投影、无本地图形、缺声明和重建失败。成功或失败时，原候选和仓库状态均可核对。 |
| A2 几何保真与固定外框 | 按本包的 [drawn 声明](../../tests/fixtures/w003_m1/tech/drawn.json)、[几何比较器](../../tests/fixtures/w003_m1/tech/formats.json)及 [lifecycle/1](../../tests/fixtures/w003_m1/tech/physical.json) 执行。10 层 preserve_drawn 按顶层身份、stream 元素、图层/用途映射、精确矩形与记录重数核对来源；5 层 frame_static 还须绑定实际 BOUNDARY 和适用的外框条件。正例 MARKER 保留、框为 (0,0)–(160,200) DBU。用独立样张证明丢一条重复记录、错绑外框或缺少必要算子/比较器会被检出。该工艺包声明的生命周期仅有上述两种。 |
| A3 工艺坐标和占用 | 按配置中的 1D、2D、显式跳过分派。在完整样例逐源验证投影片位于各自来源内、无丢失、可重建；可复用 W018/W021 已证明的不变量。保留格片到 GDS 记录、effective region/piece 的反查。验证 POLY 的 -3 号轨、M1 末格的 130 DBU²；用 W018 的 CUT 专例复核同格两片各 36 nm²、中间仍有空隙。 |
| A4 对照输入与失败 | 对照原 W018 样例和完整样例。POLY 缺声明时，指出受阻的是栅轨初始化，并保留该层已能核对的原图与生命周期。缩小 M1 网格覆盖范围时，定位越界的原记录。按既有层职责区分必须投影和显式免投影，避免通过删除必需声明获得整体通过。无效工艺字段若已由上游拒绝，保留其原始来源与拒绝阶段。混用其他捕获的证据须被拒绝，或由单一输入的接口排除。 |
| A5 发布交接 | 提供一条从真实文件运行检查的命令、成功与受阻样张，以及一份后续初始化事务可直接消费的只读结果。注明剩余发布条件。保留未知区域、外部 synthetic body 的证据范围和独立 target；目标有差异不会改写当前几何或产生 ECO。记录首次校验的增量耗时和输出体积。 |

## 执行与复核

先用两个输入展示同一层的预期结果，列明每项比较的独立依据。避免用候选与自身比较来证明保真；既有捕获中的源记录和已证的构造不变量可以复用。让独立 reviewer 核对来源、层策略和失败语义后实施。实现遵守中立候选与事务的依赖方向。调用期间沿用已取得的事实，优先复用已验证的算子和投影结果。若需要新生产工艺值或改变对外输入含义，用具体例子交 PM 决定。

开发与交付跑新增及受影响合同，包括涉及的模块边界。独立 reviewer 复算一个几何正例及一个拒绝例。双解释器全量安排在**首次原子发布第 0 版**的实际集成节点。W022 交付逐层校验；后续发布任务负责将快照、初始化事件和 head 一次写入并封存上下文。[验证分工](../collaboration/rules.md#verification-reuse)

## 交接记录

执行与独立复核记录见下文，最新验收结论见 [PM1](#pm1-receipt)。

## 执行 session 启动指令

> 在 `codex/w022-layer-initialization-checks` 执行 W022 A1–A5。从完整运行构建 W021 候选，再按显式工艺声明逐层核验原图保真、固定外框，以及占用片段能否重建。对照原 W018 配置与 W022 完整合成样例，证明 POLY 缺声明能定位、补声明后可核对，M1 末格和 CUT 同格两片都保留精确覆盖。给出可直接供后续初始化事务读取的校验结果。先独立复核方案，再实现、定向验证及独立代码复核。将代码、复现命令、证据与完整 SHA 推回原分支，交 PM 验收。

## 执行交接

受测代码与合同提交为 `1a576c8fa3f5afc25cbc9ab5ddc518ed21201574`，tree 为 `dc2e87f6e49e13a0e04d04378c3665d942982050`。执行从远端 `6581c250cf0d11b1869d96202d490a2d077ab9ea` 开始。独立审阅者先核对了捕获来源、T01 的适用范围、缺声明的职责和专例边界。[执行方案](W022/plan.md) · [方案复核](W022/plan-review.md)

### 事务读取方式

```python
from layauto_v2.normalization.initial_state import build_proposed_initial_state
from layauto_v2.pipeline import assemble_stage2
from layauto_v2.state.layer_checks import LayerInitializationChecks

facts = assemble_stage2(repository, ready, fragment_budget=312)  # 本次完整样例的调用方预算
checks = LayerInitializationChecks(build_proposed_initial_state(facts))
gate = checks.layers["POLY"]
```

`checks.passed` 汇总本次逐层检查。每层的 `drawn_issues`、`lifecycle_passed`、`frame_issues` 和 `projection_passed` 可分别读取。声明或用途不符见 `projection_issues`，逐源的越界、离轨等见 `initialization.diagnostics`，缺声明的操作及所需字段见 `initialization.gap`。同一候选上的 `occupancy.in_cell` 和 `for_record` 可继续查到原图、region、piece 和 CUT 来源。结果只接受一个候选，替换候选会重算结论，调用方不能传入另一次运行的逐层结论。[实现](../../layauto_v2/state/layer_checks.py) · [合同测试](../../tests/contracts/test_w022_layer_checks.py)

| 验收项 | 从文件实跑的结果 |
|---|---|
| A1、A2 原图及外框 | 完整样例的 15 层、40 条原图通过。10 层 preserve_drawn 和 5 层 frame_static 都对读捕获的 stream 元素与布局记录，按顶层、层/用途、整数矩形、记录重数及来源位置核对。5 层固定几何绑定偏移 112 的实际 BOUNDARY (0,0)–(160,200) DBU。T01 对所有非框原图查包含，MARKER 偏移 2608。重复 MARKER 中少一条时返回该条的偏移；换错框时所有 frame_static 层均受阻。 |
| A3 精确覆盖 | 完整样例有 10 层重建、2 层显式跳过、3 层有声明且无本地原图。38 条需投影原图共 220 个 drawn 格片，9 个有效源片共 92 个 effective 格片。合同对每个源用独立半开区间覆盖计算核对包含、无重叠及完整重建。M1 格 (2,2) 的交片为 (32,48,45,58)，面积 130 DBU²，原记录偏移 2352。 |
| A3 CUT 专例 | 原 W018 专例的 LI 偏移 182、CUT 偏移 246。格 (4,1) 留下 (130,20,139,24) 和 (141,20,150,24)，各 36 nm²，相隔 2 nm。另将相同线与切口坐标添加到完整电路的临时 GDS，直接从 W022 结果反查两块 LI 的独立 piece、region、共同 LI 原记录和 CUT 贡献者。 |
| A4 坐标对照 | W018 的 10 个必投层缺声明。POLY 原图及固定框通过，栅轨操作 `initialize_gate_tracks` 指向坐标文件的 `/coordinate_projection/layers/POLY`，列出节距、轴、首中心、范围等需要的字段。W022 以节距 9 nm、首中心 60 nm 查询 −3 号轨，回到偏移 432 的原条带 (58,10,62,190)。二维配置虽可覆盖条带，栅轨操作仍会报缺。 |
| A4 反例 | M1 的 x 轴只留三格后，2/4 条可重建，超界的两条定位到偏移 2480、2544。必投空层删除声明或改为 none 都受阻。免投 MARKER 缺坐标条目仍保留该诊断；越出实际外框另报 OutsideFrame。缺 lifecycle/1 或缺 comparator 从 Stage 1 原错误追到 owner 哈希及字段。不支持的比较器由 W008 拒绝，无效 M1 pitch 由 W018 绑定器保留原位置和几何。 |
| A5 证据范围 | 两份输入都保留 6 个 unknown 标注片、suspect_conductor 策略和只读 synthetic body，LVS 为 not_run。本次 C13 将 MN0 的目标 L 从 4n 改为 5n，差异仍在独立 target 中。两次组装与校验前后仓库快照均相同，attempt 为 unsealed。 |

### 复现

在仓库根目录，使用 Python 3.10+ 和项目开发依赖（`python -m pip install -e '.[dev]'`）。第一条命令从临时文件副本准备两个完整输入并输出逐层 JSON，其后的命令复跑合同与类型检查。

```sh
PYTHONPATH=.:tests/contracts python -B docs/tasks/W022/example.py
export PYTEST_DISABLE_PLUGIN_AUTOLOAD=1
python -B -m pytest -p no:cacheprovider -q tests/contracts/test_w022_layer_checks.py \
  tests/contracts/test_w007_contracts.py::test_normalization_and_new_domain_keep_pure_dependency_boundaries \
  tests/contracts/test_w008_geometry.py::test_domain_state_dependency_direction_and_no_hidden_occupancy_owner \
  tests/contracts/test_w013_contracts.py::test_new_modules_keep_declared_dependency_and_no_io_boundaries
python -B -m pytest -p no:cacheprovider -q tests/contracts/test_w020_stage2.py \
  tests/contracts/test_w021_initial_state.py tests/contracts/test_w018_projection.py
python -m mypy
```

[成功与受阻样张](W022/evidence/first-check.json)记录操作者可核对的层级结果、来源和首次增量测量。临时目录参与 W006 的运行身份，每次复现的 checkpoint、attempt 及测时会有差异。

| 首次增量检查 | 时间 | 返回后新增 Python 字节 | 含临时分配的峰值字节 |
|---|---:|---:|---:|
| W018 坐标 | 6.82 ms | 12,293 | 28,969 |
| W022 坐标 | 6.78 ms | 8,209 | 26,241 |

使用 Linux x86_64、CPython 3.12.14、PyYAML 6.0.3。tracemalloc 从各自的 W021 候选就绪后开始，只测首次构造校验结果，不含 W006/W020/W021 组装、JSON 或文件读写。两份诊断摘要合计 28,117 字节，SHA-256 为 `f1896d0f62a16deab8ffef4296b96aa4ae8468a4462e78d4819b8756ed134fee`。内存数据是 Python 分配量；下游复用原候选及占用索引。

后续初始化事务需冻结 current、独立 target、各层检查与上下文，核对 lineage、head 和 attempt revision，原子写入 version 0 snapshot、InitializationEvent 和 head，并封存 context。幂等重放、冲突下的原子性和双解释器全量属于首次发布的集成验收。实际工艺数值及生产 LVS 仍待相应环境提供。[发布义务](W020/readiness.md#最小剩余动作与验收输入)

[独立代码复核](W022/code-review.md)绑定上述受测提交，剩余必须修正项为 0。审阅者另从有缓存、原 target 的真实文件运行，直接解码 GDS。将 M1 的 x 轴缩至两格时，14 层通过，M1 的 4 条越界记录分别回指偏移 2352、2416、2480、2544。审阅者也复跑了 W018 原 CUT 专例。

本次复用 W008 捕获认证、W018 片段构造及 W021 逐源面积不变量。新增合同对完整样例另作逐源覆盖计算。依赖版本、GDS/工艺配置、候选构造、层职责或发布消费方式变化时，按受影响范围重跑。首次正式发布时由 PM 在实际集成提交运行双解释器全量。

**交 PM 验收。** 新增 W022 合同 10 项、模块边界 3 项、W018/W020/W021 合同 41 项，合计 54 项通过。mypy 检查 85 个源文件通过。临时向校验模块添加 repository 导入，边界测试按预期报告该文件和违规依赖。从受测源构建 sdist、wheel 并在单独虚拟环境核对了安装版模块字节及依赖。[验证结果及版本身份](W022/evidence/verification.json)

<a id="pm1-receipt"></a>

## PM1 接收与补修

2026-11-26 接收 `c7494e49f8042da79bb027630b7c1d84d47d6ca0`。受测产品及测试提交为 `1a576c8fa3f5afc25cbc9ab5ddc518ed21201574`，tree 为 `dc2e87f6e49e13a0e04d04378c3665d942982050`。PM 核对交付时的 runtime、测试、配置及示例与该版本相同，并核对两份坐标样本、两份 GDS 及 first-check.json 的归档哈希。**1 项 P2 必须修正，完成独立定向复核后再集成。**

PM 在 Linux / Python 3.12.14 实跑交付版的 6 项正式合同，全部通过：W022 完整配置逐源重建、W018 缺声明对照、非法格边、两例缺少必要工艺字段，以及 W008 的模块边界检查。前两项对照用时 112.86 秒，后四项用时 4.61 秒。两个原样本均符合任务卡预期。以下新反例检验另一份合法声明。

**PM-01　二维 POLY 已完整重建，投影状态却报告失败（A3、A4）。** 用户确定由各层配置显式选择坐标类型。W022 方案复核也要求将二维覆盖与一维栅轨能力分别定性。当前 `_projection_issues` 仅凭 drawn 的 gate 角色给已声明二维的层加入 `GateTracksUnavailable`，导致 `LayerCheck.projection_passed` 和整包 `passed` 都为假。该调用仅传入 W021 候选，没有单独选择栅轨操作。下游不能据此判断本次声明的占用是否可用于初始化。[逐层声明决定](W017-coordinate-occupancy-projection.md#pm2-layer-decision) · [W018 工艺配置合同](W018-coordinate-occupancy-core.md) · [W022 方案复核](W022/plan-review.md) · [判定实现](../../layauto_v2/state/layer_checks.py)

对照 W022 的完整合成配置，语义上只改 POLY 一层的坐标声明，使用与 OD 相同的 20 × 10 DBU 二维格边；将重新编码的坐标文件按实际字节重新绑定。完整链读取同一份 GDS。POLY 仍在偏移 432，矩形为 (58,10)–(62,190)。它沿 X 跨过 60，沿 Y 占 18 行，手算应有 36 个片段、合计 720 DBU²。运行时每个片段的格号与矩形均与手算相等，几何保真和外框通过，其余 14 层均通过，仓库快照前后一致。唯一失败原因是栅轨诊断指向坐标文件的 `/coordinate_projection/layers/POLY`。当前实现把实际投影与用途不同的轨号查询合并为同一个判定。

在仓库根目录运行以下命令。探针在交付版展示实测状态，最后一个断言为补修验收条件。[PM 单变量探针](W022/pm01_probe.py)

```sh
PYTHONPATH=.:tests/contracts python -B docs/tasks/W022/pm01_probe.py
```

**验收与执行交接**

- 已声明的二维投影完整重建时，二维投影检查应通过。此次单变量输入满足其它层条件，普通逐层检查整体应通过。二维声明无法给出一维栅轨号，保留这个可查询的能力边界；如果某操作另有明确的一维要求，将限制定位到该操作。不要为这个修正新增生产配置字段或改变 W018/W021 输入合同。
- 保留完整一维正例（−3 号轨中心 60 nm）、POLY 缺声明，以及已声明二维但越界的失败状态和来源。调整目前混有多个异常的正式测试，使它分别检验二维覆盖及栅轨能力；将只改 POLY 的回归加入正式合同，并由独立 reviewer 用另一组格边核对。重点验证其它层、原始几何和 attempt 的行为。
- 执行侧 54 项定向检查、85 个源文件 typing 和构建/安装按原受测身份采信；安装 smoke 使用带系统包可见性的独立 venv。双版本全量仍留到第 0 版正式发布的集成节点。修正改变的产品路径须定向复测。

**原执行 session 启动指令**

> 在 `codex/w022-layer-initialization-checks` 接续 W022 PM-01。先复跑 PM 的二维 POLY 单变量探针。按所声明的坐标类型判断占用是否完整，单独表达能否取得一维栅轨号。保留缺声明、越界与原一维正例，补正式定向回归。请独立 reviewer 用另一组格边及失败例复核后，将修正、证据和完整 SHA 推回原分支交 PM。当前验收范围到逐层初始化校验。

<a id="pm01-repair"></a>

## PM-01 补修交接

起点 `a6c2f1e62e26b1f6fc5f934ed0cb61a2957b8600`。改动前原样运行 PM 单变量探针，36 个格片、720 DBU²、偏移 432 和其余 14 层的检查均通过。原程序随后报告 `GateTracksUnavailable`，投影与整包判定均为假，最后的断言退出码为 1。

受测提交为 `03bbecc06e2dab2f383ba2b8e262f621d754e2fc`。下游从同一个 `LayerCheck` 读取两个结果。[判定实现](../../layauto_v2/state/layer_checks.py) · [定向合同](../../tests/contracts/test_w022_layer_checks.py)

| 读数 | 含义与来源 |
|---|---|
| `projection_passed` | 按本层显式选择的坐标类型及 W021 的逐源重建结果判断占用。必投层缺声明或声明为 none 有 `projection_issues`。格边或轨道不覆盖原图时，`initialization.diagnostics` 给出原因与原记录。该读数参与整包判定。 |
| `gate_track_numbers_available` | 对 gate 层，存在本地 drawn 栅且每条都已命中声明的一维轨道时为 True。二维、缺声明、没有本地栅或有栅未能定位时为 False。其它层返回 None。需要栅轨号的调用方可读该属性和 `initialization.projection.declaration`，再按需通过候选的占用索引反查轨号。POLY 缺声明时，W021 的 `gap` 仍保留栅轨操作名及所需字段。 |

```sh
PYTHONPATH=.:tests/contracts python -B docs/tasks/W022/pm01_probe.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest -p no:cacheprovider -q tests/contracts/test_w022_layer_checks.py
PYTHONPATH=.:tests/contracts python -B docs/tasks/W022/pm01_review_probe.py
```

同一份 PM 探针在受测提交上退出码为 0。原来的 36 个片段、720 DBU² 和 GDS 偏移 432 全部吻合，坐标声明为 `2d_cells`，投影与整包均通过，一维栅轨号不可用。完整一维样例仍能回查中心 60 nm 的 −3 号轨。原 W018 缺 POLY 声明时，保真和外框检查通过，必需占用受阻，栅轨号不可用。

独立 reviewer 从原始 GDS 复算了带相移的 11 × 17 DBU 格边。完整覆盖得到 24 片、720 DBU²；仅将 X 方向右边缘缩到 59 DBU 后，POLY 返回 `outside_range`，定位到原记录偏移 432。其余 14 层的格号、矩形、region、piece 和记录来源逐项相等，两次 attempt 均为 `unsealed`。独立复核剩余必须修正项为 0。[独立复核记录与输出](W022/pm01-review.md)

本次在 Linux、CPython 3.12.14 上跑完 13 项 W022 合同及 3 项模块边界检查，全部通过。mypy 对 85 个源文件检查通过。调用示例也分别从 W018、W022 的实际输入复跑，原有样张字段除运行身份与计时、内存测量外均吻合。探针修正前后的原始输出、测试节点及文件 SHA-256 已随分支保存。[执行证据](W022/evidence/pm01-verification.json)

原有 54 项检查、前次构建和安装记录按其受测版本保留。W018/W021 生产者、输入合同、fixture 及包配置与补修起点相同；本次重跑覆盖了变更的判定、示例、正式回归与模块边界。PM-01 补修及独立复核已交 PM 重新验收。双解释器全量仍由第 0 版正式发布的集成节点执行。
