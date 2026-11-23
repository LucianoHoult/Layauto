# W018 — 实施工艺坐标与离散占用状态内核

## 任务要求（PM）

M1，Stage 2。交付可被后续 Stage 2 组装代码调用的产品组件。起点是 W017 已集成的 main `504d9b07c08160d46a9aaa4fd3346a144ac5db32`，分支 `codex/w018-coordinate-occupancy-core`。执行版已交付。PM 接收核验发现一项配置错误定位问题，当前待局部补修及复核。[PM1 接收与补修交接](#pm1-receipt)[架构 §2.3、§3.4–3.6、§11.3](../architecture.md) · [W017 来源及复算](W017/proposal.md)

**从已有代码接起。** W008 已把认证的 drawn records 按各层图形边缘分格，并保留每个占用片段。本次从同一份精确几何及明确给出的逐层坐标参数出发，在选定坐标系下构建可重建的占用状态。复用已有矩形、单位绑定、来源引用和求交逻辑。W009 的有效区域与原始 drawn 几何分别标记来源。旧组件和消费者继续按原索引工作。同一几何保留一个权威来源，各种索引均能追溯到它。[坐标](../../layauto_v2/state/coordinate.py) · [占用](../../layauto_v2/state/occupancy.py) · [有效区域](../../layauto_v2/state/regions.py)

### 先交付独立可读的逐层配置样例

第一项交付是[逐层配置样例](W018/layer-discretization.example.yaml)。此文件是 PM 按真实层表准备的 synthetic 审阅稿，可直接看出一维、二维及跳过投影各需哪些字段，以及 15 层中哪些资料仍缺。FIN 引用工艺包已有参数；LI 与 M1 的网格为明确标注的测试设定。样例随工艺包使用；换 cell 时可复用同一个适用的工艺包。

执行者先核对样例的字段、单位、来源与缺项，提交可审阅版本，给出一维中心及二维格边的手算预期，然后用同一版字段和数据接入读取器与内核。正式测试经所选工艺包装载对应声明。若实施中调整字段，更新样例及测试并说明变化。既定语义直接推进；出现新的对外语义才提交具体分歧。[W017 决策更新](W017-coordinate-occupancy-projection.md#pm2-layer-decision)

| 验收 | 正式代码应做到的事 |
| --- | --- |
| A1 坐标 | 从实际选用的工艺配置读取各层显式声明的投影类型及其对应参数，校验并绑定单位、原点和有限范围。给定方向、原点、节距和偏移，精确换算物理点、轨道号与格边。用现有 FIN 配置和 GDS 复算 18 条中心线，检查两轨之间、负坐标、非零偏移和半开边界。 |
| A2 占用 | 给定已校验的 layout 及逐层投影声明，构建不可变的离散占用结果。可按层和格取全部片段，也可从原图形找回全部覆盖。每片携带确切边界、单位和 record 来源；有效片段另保留 region/piece 及 CUT 贡献者。支持同格多占据及不同来源的相同矩形。 |
| A3 端到端 | 正式测试从文件中的逐层配置和实际 GDS 经产品读取、认证、构建入口生成结果；S2 四片无重叠地拼回 32 DBU²，S3 两块 LI 各 36 nm²，间隔 2 nm，在指定示例格中仍分别可追溯。另测换轴或相位后覆盖变化、原几何稳定。20×10 和 32×16 只作各自样张的显式参数。 |
| A4 边界和成本 | 缺轴保留原几何。测试错单位/异源有效区域、越界和巨幅稀疏网格。先估算命中的总片数，只为实际占用分配；用显式测试预算检验累计超限时结果完整性。记录代表路径的耗时、峰值与片数。 |
| A5 工程交付 | 在 `layauto_v2/` 和正式 tests 实施，给一条从真实文件构建占用并检索来源的可复现命令。未参与实现者检查接口依赖、精确性、覆盖重建、兼容性和资源。按[验证复用规则](../collaboration/rules.md#verification-reuse)开发期跑新增/受影响项，冻结交付时执行双版本全量、typing、构建、干净安装及源码外 smoke。 |

### 层分类和验证范围（A1–A4 验收细则）

2026-11-23 用户确认，开发样本与后续生产适配统一采用**在对应工艺配置中直接声明每层投影类型和参数**的方式。随所选 tech bundle 读取一次；同一配置可供适用的 cell 复用。层条目可直接填写参数，也可显式引用该 tech bundle 中已有的权威参数。程序依据声明分派算法，层名用于关联几何与配置。层级分类、形状外观、间距和电气连接都不能代替这项声明。[架构 §4.8、§12.3](../architecture.md)

| 层条目的投影声明 | 所需参数及行为 |
| --- | --- |
| 一维轨道（示例 FIN） | 声明轨道的索引轴、中心线节距、基准位置与编号约定，定义单位和适用范围。基准也可引用明确的边缘偏移与宽度并换算到中心。例如本样本采用 Y 轴，下边缘 24 nm 加半宽 1 nm，中心线从 25 nm 起每 10 nm 一条。离轨或形状不适用时保留原几何并标出原因。 |
| 二维占用（示例 M1、LI） | 声明 X、Y 两组格边轴，各含节距、相对原点的偏移和有效范围，单位可显式引用公共定义。矩形按两轴切出精确交片。同一算法消费不同层自己的两轴。生产数值随工艺提供，样例数值只在其显式声明下生效。 |
| 不参与主占用（如当前 BOUNDARY、MARKER） | 声明跳过投影，不要求轨道参数；保留图形和来源。是否导出、保留或派生继续读取各自的配置字段。 |

**验收。** 逐项核对 fixture 的 15 个声明层，图形计数与坐标资料完整性分别报告。旧版工艺包缺少新坐标声明时，已有读取和几何能力继续可用；请求新投影时指出对应层的缺项。新版配置若显式写了二维却漏 Y 轴、节距非法或引用失效，要能定位到具体层和字段。只有所需参数有效且几何适用时才生成对应结果；内核不得改用其他投影类型继续计算。

使用版本明确的测试工艺包或临时绑定副本，保留 W003/W004 原始 fixture 及既有身份。从真实配置分别实跑 FIN 一维、M1 与 LI 二维、显式跳过；校验 M1 与 LI 在各自坐标下的真实覆盖。再用不同层标识声明等价一维参数验证复用，以及二维缺轴、类型和参数不相容的反例。独立 reviewer 核对从配置到算法的调用链和输出，检查是否有按层名切换算法或自动猜维度的路径。

**实施边界。** 工艺读取与绑定由配置/归一化部分负责，坐标和占用内核只接收已校验的声明及所需的本地几何。执行者给出兼容版本、具体字段和可运行的配置示例，正式测试覆盖读入到构建的全链路。W017 的独立 selection 文件仍是历史候选，本包按本节已确定的工艺配置入口实施。W016 公开入口的接入、公开查询 API、产品默认片数与 Stage 2 baseline 发布留待相应任务。

## 启动指令

> 以执行角色在本分支实施 W018 A1–A5。先交付上方逐层配置样例和手算预期，再从实际逐层配置读取显式类型并校验相应参数。按上方细则核对全部声明层，用 FIN、M1、LI 和跨层反例验证配置驱动的算法分派。对照 W017 样张，先在任务执行区列出复用位置、内核输入/状态所有权和验收路径，然后直接写产品代码与正式测试。用可实际构建、双向检索且可从源几何重建的离散占用结果交付。若发现确需改变对外输入或已有语义，带反例交 PM，继续其余内核工作。完成独立复核后将代码、证据和完整提交 SHA 推回原分支交 PM。

## 执行、review 与 PM 验收

执行者和 reviewer 分别追加受测版本、命令和独立结论。当前仅有 PM 任务交接。

### 执行起点与配置核对

起点 `e5ea3a08ff6ddd8f406b55067761e5a69627a420`。核对 drawn 的 15 项、formats 的单位合同、physical 的三个 FIN 参数、coordinate 原点及主 GDS 的 BOUNDARY/XY 后，将[样例](W018/layer-discretization.example.yaml)整理为工艺包可直接指定的完整 coordinate owner。沿用 bundle/owner v2，在 `coordinate_projection.id` 区分旧示例与 `layauto-layer-discretization/1`。新 owner 直接保存原点，将原审阅稿的十个缺项移入注释。正式路径从同一份 YAML 字节加载五项运行声明。二维 pitch、offset 和 cells 为显式 synthetic 参数。

| 层 | 主 GDS 记录 | 坐标资料 | 层 | 主 GDS 记录 | 坐标资料 |
| --- | ---: | --- | --- | ---: | --- |
| BOUNDARY | 1 | 显式跳过 | BODY_N | 1 | 缺声明 |
| BODY_P | 1 | 缺声明 | OD | 2 | 缺声明 |
| POLY | 1 | 缺声明 | FIN | 18 | Y 中心轨 |
| LI | 3 | X/Y 格边 | CUT | 0 | 缺声明 |
| CONTACT | 4 | 缺声明 | VIA0 | 3 | 缺声明 |
| GCONTACT | 1 | 缺声明 | BTAP_N | 0 | 缺声明 |
| BTAP_P | 0 | 缺声明 | M1 | 4 | X/Y 格边 |
| MARKER | 1 | 显式跳过 | 合计 | 40 | 15 层 |

**实现前手算。** 样本 1 DBU = 1 nm。FIN 按 Y 编号，轨 k 的中心为 0 + 24 + 2/2 + 10k nm，k=0…17。首两轨 25、35 nm，末轨 195 nm；30 nm 距两轨分别为 +5、−5 nm。按实际中心回查编号，stream 次序不参与编号。轨号下界对应所声明的 first_centre。

- LI 的 X 格边为 20i（i=0…8），Y 格边为 10j（j=0…20）。首记录 [28,34) × [30,55) 命中 (1,3)、(1,4)、(1,5)，高度 10、10、5。三条记录分别出 3、3、14 片，共 1110 DBU²。
- M1 的 X 格边为 16i、Y 格边为 20j（i、j=0…10）。首记录 [0,45) × [48,58) 在 x=16、32 切开，格 (0,2)、(1,2)、(2,2) 的面积为 160、160、130。四条记录分别出 3、3、2、2 片，共 1340 DBU²。
- S2 的 X 边 −6、4、14 和 Y 边 −3、1、5 将 [−2,6) × [−1,3) 切为宽 6、2，高 2、2 的四片，面积 12+12+4+4=32 DBU²。点 (4,1) 属 (1,1)，最大外边开。
- S3 单独声明 32×16 DBU。LI [130,150) × [20,24) 扣除宽 2 的 CUT 相交部分后，左右宽各 9，面积各 36 nm²，间隙 2 nm；两片同落 (4,1)，保留各自 region/piece 与共同 drawn/CUT 来源。

**实施路径。** W005 安全解析所选 tech owner，W008 认证捕获与 LayoutDraft，W009 提供同源 region、piece 与贡献者。配置/归一化负责校验和绑定；state 的纯坐标对象负责换算，离散占用持有双向索引，片段沿用 Rect.intersection、UnitBinding 和源 ID。开发先跑声明读取、W008/W009 组合、S1–S4 及错误/预算测试，冻结后以同一源码、样例和测试完成双解释器工程矩阵并交独立复核。

### 执行交付与复现

配置提交 `fb6010a87d7bb0f88c84fa95eb4d0c7c79b80a0c`。冻结产品、测试及演示提交 `186c426ea550a6941ead417cd640a86c37017ba5`。工艺包的 `owners.coordinate.path` 指向样例 YAML，文件 SHA-256 为 `fefb1bb72c15a131206f2885e1d9dc7ad98463aab676237a410a99d9c3d82890`。主图与专例使用已有 GDS；原 fixture 子树为 `c8b85527a7063f4d489f9af6d45fb61204389190`。演示在临时副本中更新工艺选择和现有捕获的闭包绑定。

在仓库根目录用开发环境执行下列命令。第一条从文件构建占用，列出逐层实数和 FIN、LI、M1 各一个格的原记录、字节偏移及全部覆盖片数。第二条从专例 GDS 验证同格两片及 CUT 来源。

```sh
python -m docs.tasks.W018.example
python -m pytest -q tests/contracts/test_w018_projection.py::test_cut_islands_same_cell_loses_no_area_or_provenance
```

**A1 与 A2。** 内部组装入口 `normalization.projection.build_discrete_occupancy(geometry, fragment_budget=..., effective=...)` 接受成功的 W008 结果，可选同一捕获的 W009 结果。工艺引用使用已认证的六个 owner；一维参数既可直接填写精确 nm，也可引用样例中的权威字段。一维声明的 `index_axis` 决定条带法向，`first_centre` 对应闭编号窗下界。二维坐标使用同包原点和 canonical DBU，格边偏移以原点为基准。换算物理点时将 `layout.units.canonical_tick_nm` 传给 CellGrid 的 `physical_to_index` 和 `index_to_physical`。[声明校验](../../layauto_v2/tech/projection.py) · [捕获绑定](../../layauto_v2/normalization/projection_model.py) · [坐标数学](../../layauto_v2/state/projection_axes.py)

成功结果的 `value.layers` 将 drawn 计数和声明状态分列；`in_cell`、`for_layer`、`for_record` 支持 drawn/effective 视图。每片都有确切 Rect、单位引用、模型身份、源 record ID 与 GDS 位置，有效片另带 region、piece 与贡献者。占用以同一源对象建立只读索引；每次更换坐标，仍可回到 W008 layout 或 W009 region 重算。[构建入口](../../layauto_v2/normalization/projection.py) · [占用与查找](../../layauto_v2/state/discrete_occupancy.py)

**A3 实测。** 主 GDS 的 40 条源记录形成原 W008 索引 41 片；新模型产生 FIN 18、LI 20、M1 10 片。LI (1,3) 为 [28,34) × [30,40)，回查字节偏移 1648 的原图得到 3 片。M1 (2,2) 为 [32,45) × [48,58)，源偏移 2352。测试以独立区间成员关系和面积验证每个已投影 record 的完整覆盖，包含边、顶点和同形异源记录。LI 移相后 23 片、互换轴节距后 16 片，W008 源几何相等。S2 在临时真实 GDS 中重建 32 DBU²；S3 格 (4,1) 内保留一个 drawn 和两个 effective，来自 LI 偏移 182 与 CUT 偏移 246，净面积 72 nm²。[端到端合同测试](../../tests/contracts/test_w018_projection.py) · [坐标边界测试](../../tests/unit/test_w018_axes.py)

**A4 缺项与预算。** 旧 owner 的 15 层均报告缺声明。新版显式跳过与资料缺失各有独立状态，空层也有记录。对显式二维删除 LI 的 Y 轴，W008 保有 40 条几何，新投影返回含选定文件 URI、哈希和 `/coordinate_projection/layers/LI/y_edges` 的配置异常。离轨、形状不适用和部分越界逐来源留存原因。预算由调用方明示。主图预算 47 时返回所需总数 48、首次超限的来源和空占用结果，预算 48 可完整生成。在十亿乘十亿格的满窗反例上，先算得 10¹⁸ 片，调用格边求交之前即返回超限。

冻结版 Python 3.12.14，运行 `python -B -m docs.tasks.W018.example --resources` 单次测量。时钟为 perf_counter，峰值为 tracemalloc 记录的 Python 分配。文件至占用含 W005 读取与 W008 认证；内核一列从已绑定模型和 layout 开始。两个范围均含 15 层和双向索引。测量与同机工程矩阵并行，毫秒数仅描述此次运行。[资源原始输出](W018/resources.json)

| LI 配置 | LI 片 / 全图占用格 | 内核 ms / 峰值 bytes | 文件至占用 ms / 峰值 bytes |
| --- | ---: | ---: | ---: |
| 样例 20×10 DBU | 20 / 48 | 3.925 / 32,610 | 8,557.498 / 7,316,372 |
| 同窗细化到 1×1 DBU | 1,110 / 1,138 | 51.689 / 440,774 | 8,307.849 / 7,238,840 |
| 原节距，每轴十亿格 | 20 / 48 | 3.051 / 32,938 | 8,836.801 / 7,520,832 |

### A5 冻结验证与 PM 交接

**开发期实跑。** Python 3.12.14 运行 W018 坐标、模型及端到端测试，加 W007 依赖边界，共 35 passed；针对共享读取和旧组件另跑 17 项，覆盖真实 site、闭包选择和缺项、W006 readback、W008 原分格与 owner 认证、W009 CUT 孤岛、W016 无 body 分析。配置校验开发回归 68 passed。独立 reviewer 用 3.10.22 跑 36 项定向检查，并直接解码 GDS，与逐 DBU 方块覆盖和来源逐项核对。冻结前发现的大有理数模型身份问题 R1 已修复并有持久回归。[复核报告与反例](W018/review.md)

**最终实跑。** 从冻结提交 `186c426ea550a6941ead417cd640a86c37017ba5` 导出干净源码，两个解释器均运行完整 `tests/`，包含 fixture_support。收集顺序摘要均为 `87dc9e509e1773e0a9452eda9f9ea7e30b91b6b23a3732543f3ee72eb3640c5e`。每个通过节点与本侧收集结果一一对应。另分别运行 strict mypy、构建 wheel/sdist、在新 venv 中安装该 wheel、pip check 和源码目录外 `python -I` 实际读 GDS。两侧各有 127 个已安装运行时文件与冻结源逐字节相同。[矩阵与构建身份](W018/evidence/matrix.json) · [命令及原输出索引](W018/evidence/commands.json) · [冻结输入清单](W018/evidence/freeze.json)

| Python | 全量 pytest | pytest 耗时 | strict mypy | 干净安装与源码外 smoke |
| --- | --- | ---: | --- | --- |
| 3.10.22 | 1,995 passed，8 subtests passed | 5,137.82 s | 81 个源文件通过 | 15 层、40 条、48 片及 3 个 GDS 来源通过 |
| 3.12.14 | 1,995 passed，8 subtests passed | 3,840.87 s | 81 个源文件通过 | 同一组输入及预期通过 |

**交 PM。** 建议接收 W018 A1–A5，剩余必须修正项 0。本次范围为显式声明的 synthetic flat-rectangle 工艺与只读内核。产品默认预算、W016 入口接入、生产 PDK 适配与 Stage 2 baseline 发布仍由后续任务负责。后续证据补记只涉及任务文档和原输出；按冻结清单和实际输入身份采信上述矩阵。PM 在实际合并版本补跑样例、S3 和旧 owner 兼容组合；产品、样例、正式测试、解释器或依赖变化时重新核定验证范围。[安装结果实数与回溯](W018/evidence/wheel-smoke.json)

<a id="pm1-receipt"></a>

### PM1 接收核验与补修交接

PM 核验的分支交付为 `73a8eaab95c2090ceb8066fa35fb37cecdc53b1f`，冻结实现为 `186c426ea550a6941ead417cd640a86c37017ba5`。本次实跑 Python 3.12.14 的 W018 坐标、占用模型和配置至 GDS 合同测试共 34 项通过。仓库示例产生 48 片，按原始记录回查成功。复跑独立 GDS 探针得到 40 条源记录，CUT 两侧各 36 nm²、间隔 2 nm，并复现 R1 修正后的大分母用例。

PM 实算 [冻结清单](W018/evidence/freeze.json) 310 项及[矩阵](W018/evidence/matrix.json)所列 6 份证据的 SHA-256，均匹配。两份原始全量日志末行均为 1,995 passed、8 subtests passed。双解释器全量、typing、构建与安装采信该冻结版本的交付证据。当前判断适用于 synthetic 样本和内核。

**PM-01（P2，合并前修正）。** 在样例 LI 声明中保留有效的嵌套字段 `x_edges.pitch_dbu = 20`，并在 LI 下额外添加一个字面键 `"x_edges/pitch_dbu": 987`。从正式文件入口读入后，投影正确拒绝未知键并保留 40 条原几何、正确文件和哈希。但返回的字段位置是 `/coordinate_projection/layers/LI/x_edges/pitch_dbu`，按路径读取实际得到合法值 20。要定位被拒绝的字面键，字段位置应为 `/coordinate_projection/layers/LI/x_edges~1pitch_dbu`。此项影响 A4 的错误字段定位，正常坐标、面积与来源复算均通过。

从仓库根目录可复现：

```bash
PYTHONPATH=tests/contracts python -B - <<'PYCODE'
from pathlib import Path
from tempfile import TemporaryDirectory
from w005_cases import copy_input
from w018_cases import select_projection, build_geometry_from_site
from layauto_v2.normalization.projection import build_discrete_occupancy
from layauto_v2.normalization.projection_model import ProjectionConfigError

with TemporaryDirectory() as temp:
    root = copy_input(Path(temp))
    select_projection(root, mutate=lambda p: p["layers"]["LI"].update({"x_edges/pitch_dbu": 987}))
    geometry = build_geometry_from_site(root)
    try:
        build_discrete_occupancy(geometry, fragment_budget=100)
    except ProjectionConfigError as error:
        print(error.issue.code, error.issue.message, error.issue.source.field)
        print(len(error.geometry.layout.records))
    else:
        raise AssertionError("the unsupported field was accepted")
PYCODE
```

**执行交接。** 在原 W018 分支局部修正错误字段的路径编码。为含 `/` 和 `~` 的字面键补定向回归。由独立 reviewer 从实际配置经产品入口复核，按返回路径从同一份输入读取被拒绝的键值，并对照原合法字段、来源 URI/hash 和保留的原几何。若调整公共 schema helper，加跑受影响的旧配置诊断。保留原复现及冻结矩阵，在补修回执中列明本次实跑及未覆盖范围。优先将局部修正与复核交回 PM，无需为本次回执重跑两套全量。
