# W019 在单 cell 分析入口查询工艺网格占用

## 任务要求（PM）

**已合入 main，阶段全量回归运行中。** PM-01 已关闭。[PM2 集成核验](#pm2-integration) 本任务属于 M1 的 Stage 2。基线为已集成 W016、W018 的 main `0af9bfe18f9a8606d5b1cf3c707b8e75b28a064c`，执行分支为 `codex/w019-single-cell-occupancy-query`。执行 session 负责方案、实现和证据，独立 reviewer 复核，PM 负责验收和集成。

用户从现有 `analyze_cell` 入口分析一份本地 flat cell 后，应能按层、轨道或格号读取实际覆盖，再从片段找回原始 GDS 记录，也能从源记录查回它覆盖的片段。外部 tapcell 继续由调用方选择。首包沿用 W016 已支持的 synthetic 输入、W018 随工艺包读取的逐层声明和显式片数预算。[W016 公开入口](../../layauto_v2/analysis.py) · [W018 验收](W018-coordinate-occupancy-core.md#pm2-integration) · [架构 §3.4–3.5](../architecture.md#34-grid-作为坐标系统)

| 验收项 | 可观察结果与依据 |
| --- | --- |
| A1 从公开入口查图 | 从真实 analysis manifest、GDS、CDL、query 和 tech 文件出发，通过有文档的只读 Python 调用查询。主样本 drawn 视图逐层列出 15 层、40 条源记录，FIN 18 片、LI 20 片、M1 10 片。可区分有几何但缺声明、显式跳过、零条记录与可查询层中的空格。 |
| A2 金属部分占格 | 从公开入口查询 M1 的格 (2,2)。该格范围为 X 32–48、Y 40–60 DBU，片段范围为 X 32–45、Y 48–58 DBU，面积 130 DBU²。回查 GDS 偏移 2352 的原线，三个沿 X 排列的片段长度为 16、16、13 DBU。使用 W018 样例的显式格边；保留精确线端和图形来源。 |
| A3 本地图形与外部 body | 用相同本地 GDS、工艺包和 query，对比实际缺少外部 body 文件且未选择它，以及显式选择有效 synthetic context 两次分析。本地片段、坐标、面积、原 GDS 来源和查询结果相同；分析请求自身的身份可随选择改变。无外部证据时依赖它的 B 端/父级结论沿用 W016。另测已选择但错误的外部资料，保留其诊断及可独立计算的本地事实。 |
| A4 有效图形与例外 | 提供 drawn 与可用 effective 两种视图。用 W018 的 CUT 专例核对同一 LI 格内两片各 36 nm²、间隔 2 nm，分别可追溯到 region、piece 和对应的 LI/CUT 记录。旧坐标配置按层报告缺声明。显式声明无效时准确定位字段、URI、哈希；片数超预算时报告所需片数与已有来源。查询可区分空结果、欠缺依赖及超限，不把部分片段当成完整结果。 |
| A5 兼容、成本与交付 | 原有单 cell 调用和诊断可继续使用。用同一份分析取得的本地输入绑定坐标模型，复用已构建的 layout、可用的 effective geometry 和 W018 投影算法。比较不查询、首次查询、同一结果多次查格的读取/构建次数、耗时和报告体积。交付一个能从公开入口复现 A2 的短例，写明实跑命令、检查范围和独立复核结果。 |

### 已核对的开发起点

PM 在上述 main 上用 [W016 文件样本](../../tests/support/analysis_inputs.py)分别生成有、无 body 的输入，选用同一 [W018 坐标配置](W018/layer-discretization.example.yaml)，更新各自本地 query header 的工艺文件绑定，再调用 `analyze_cell`。两次均 completed，各读到 40 条几何，本地 layout 与连通图相等。偏移 2352 的 M1 原图均为 (0,48) 到 (45,58) DBU。这是现有输入能兼容的实测起点。A1–A5 的新查询须随实现另行验证。

W016 从本地捕获取得 [layout 与 effective geometry](../../layauto_v2/normalization/analysis.py)。W018 的[绑定入口](../../layauto_v2/normalization/projection_model.py)目前接收旧完整读取链的 GeometryResult，而[占用内核](../../layauto_v2/state/discrete_occupancy.py)已能消费 layout、绑定的坐标模型和可选 effective geometry。抽取必要的共同绑定逻辑，保留两个入口各自的来源认证。用户只选一次工艺包。使用该次捕获的实际字节和来源，避免重读文件、补造旧完整输入或建立第二份几何。格内片段、双向索引和报告摘要沿用已有对象或可重建引用。[W018 合同见证](../../tests/contracts/test_w018_projection.py) · [W016 诊断报告](../../layauto_v2/reporting/analysis.py)

## 方案与执行

先给出一个可调用的 Python 示例，列清从现有分析入口取得只读查询结果的方式、片数预算在哪一步提供、drawn/effective 的范围，以及缺声明、声明错误和超限各会看到什么。采用兼容、按需查询的方案，由调用方显式给出预算。接口命名及绑定函数放置由执行者决定。请独立 reviewer 核对依赖和来源，再直接实施；若必须改变既有输入含义、顶层状态承诺或设定生产默认预算，带具体案例交 PM。

使用临时样本副本验证，保留固定 fixture 身份。执行与交付均按[协作规则](../collaboration/rules.md#verification-reuse)运行新增及受影响项，重点覆盖 W016 入口、报告和 body 边界，以及 W018 的绑定和占用查询。按实际改动做类型检查、构建及干净安装后的公开入口冒烟。下一次双版本全量由 PM 在 W019 集成后的 Stage 2 公开入口组合验收中单列执行。

## 执行、review 与 PM 验收记录

当前交付为任务卡和开发指令。执行者在此追加方案、受测版本、示例、结果及未覆盖范围。独立 reviewer 追加反例、结论及修正复核。实现与证据推回本分支后交 PM。

### 执行交付，交 PM 验收

本分支从 `d0b8540e0e06326f51f7fd4c56d3e43c7ca667c1` 开始。[调用样例](W019/example.py)使用显式预算，按 M1 格号取片段，再按 GDS 原记录反查全部片段。独立 reviewer 先核对同次捕获的工艺来源、已有几何及预算边界，执行者随后实现。[方案复核](W019/design-review.md)

| 交付 | 完整提交 SHA |
| --- | --- |
| 受测实现、测试、示例、成本探针 | `cbcf381bb8a11876c5cf2fc0673305483fdb5ea7` |
| 执行证据、独立代码复核、公开说明补充 | `d9c1f7306f677cbbf160403541363950c66bc2d2` |

发布采用仓库既有 GitHub noreply 邮箱。上述两条可获取提交的 tree 分别与受测实现和复核证据完全一致，原始 SHA 对应关系见[验证身份](W019/evidence/verification.json)。

W019 A1–A5 已逐项实跑。实际无外部 tapcell、选择有效 context 及选择错误绑定时，本地占用和双向查询相等。M1 (2,2) 回溯偏移 2352，末格为 13 × 10 DBU。CUT 专例同格两片各 36 nm²，间隔 2 nm。旧配置、声明错误定位、缺依赖和累计超限均已核对。[执行交付](W019/delivery.md) · [命令、输入及验证身份](W019/evidence/verification.json)

定向 pytest 107 项全部通过，严格 mypy 检查 82 个源文件通过。sdist、wheel 构建及隔离安装后的公开入口冒烟通过。独立 reviewer 从 GDS 字节复算 48 个片段，核对两个认证入口、变轴反例及预算两侧，必须修复项为 0。[独立代码复核](W019/code-review.md)

请 PM 按冻结身份接收上述证据，在实际合并后的 Stage 2 公开入口组合验收中运行任务卡指定的双解释器全量。当前交付分支等待 PM 验收与集成。

## 执行 session 启动指令

> 以执行角色在 codex/w019-single-cell-occupancy-query 上完成 W019 A1–A5。先给出公开入口的调用样例并做独立方案复核，再复用 W016 本地输入和 W018 占用内核实现查询。用真实文件核对有无外部 tapcell 的本地结果一致、M1 部分占格、CUT 同格多片、缺声明及超限。开发和交付跑新增及受影响项，完成类型检查、安装冒烟和独立代码复核。将实现、证据及完整 SHA 推回原分支交 PM 验收。

<a id="pm1-receipt"></a>

## PM1 接收与补修

PM 于 2026-11-23 核查交付 `18ac5a7eabb7a0f9840601f4e0eade280522b3b2`。**待修正 1 项（P2），完成独立定向复核后再集成。** A1–A3 的主要结果成立。Python 3.12.14 下实跑公开示例、独立 GDS 探针和 W019 正式合同文件（11 项通过），覆盖 M1 的 16/16/13 DBU、三种外部 body 选择、CUT 同格两片及片数超限。核对了证据索引的 17 项 SHA-256，含归档内的 14 份原输出。执行侧 107 项通过和 82 个源文件类型检查通过按冻结实现 tree `44cf74fa56e08896fb834c8ce359d5638eac7d51` 采信。[原交付](W019/delivery.md) · [独立代码复核](W019/code-review.md)

**PM-01：组合输入丢失可独立定位的坐标配置错误（A4）。** 同一请求中，M1 的二维声明缺少 `y_edges`，同时工艺不支持矩形差集算子。查询包含 effective 时只报告算子错误。删除请求里的 effective 选择后，原样的坐标文件才报告缺轴。两种选择都已认证同一份本地图形，共 40 条记录。坐标绑定只依赖该 layout 和已取得的工艺资料，可以独立给出结论。[A4 要求](#任务要求pm) · [单 cell 独立诊断约定](W015/entry-contract.md) · [两处前提检查](../../layauto_v2/normalization/analysis_occupancy.py)

从仓库根目录运行 `python -B -m docs.tasks.W019.pm01_probe`。探针用临时副本重绑实际文件哈希，调用公开 API，对照错误代码、URI、字段、SHA-256 和报告。此交付的实跑结果如下。状态依次为原分析状态和占用查询状态。[可运行的探针](W019/pm01_probe.py)

| 输入及查询 | 状态 | 公开结果中的诊断 |
| --- | --- | --- |
| 仅缺轴，drawn + effective | completed / invalid_declaration | InvalidProjectionDeclaration |
| 仅算子不支持，drawn + effective | unsupported / not_evaluated | UnsupportedRegionOperator |
| 两项同时出现，drawn + effective | unsupported / not_evaluated | 仅 UnsupportedRegionOperator；同时检查 JSON 报告也缺坐标诊断 |
| 同一组合输入，仅 drawn | unsupported / invalid_declaration | InvalidProjectionDeclaration 与 UnsupportedRegionOperator |

坐标诊断应指向 `tech/layer-discretization.yaml#/coordinate_projection/layers/M1/y_edges`，算子诊断应指向 `tech/physical.json#/operators/rectangle_set_difference~11`。每个来源 SHA-256 都以相应输入文件的实际字节核对。

**补修交接。** 在原分支局部修复查询路径。请求占用且 drawn 已认证时，保留坐标声明检查和所选 effective 依赖各自可得的诊断。组合输入从公开结果和诊断报告均可找到两项原始原因，可定位至与单项输入相同的来源。受阻查询保留已认证的本地几何并给出无完整占用索引的状态。维持无查询调用、原分析顶层状态和仅 drawn 请求的既有语义。将组合输入与单项对照加入正式定向回归，由未参与修正者独立复核。按 [验证分工](../collaboration/rules.md#verification-reuse) 跑新增及受影响项，推回原分支。双解释器全量仍在实际集成后执行。

### PM-01 补修交付

从 `7a984a15b484bdbb0cf70c5ecf4cdafd2dcf4775` 实跑 PM1 原探针，组合输入缺少坐标错误，退出码为 1。受测修复为 `708c2a39c3d8a46514ac3aa2c01eb21aa334f9f7`。只要 drawn 已认证，查询就使用同一次捕获的 layout 与工艺记录检查坐标声明。所选 effective 同时受阻时，占用结果保留两项依赖及各自的原始诊断。[原探针](W019/pm01_probe.py) · [正式回归](../../tests/contracts/test_w019_analysis_occupancy.py)

组合输入的 `occupancy.issues` 和 JSON 报告的 occupancy 摘要均含下表两项。正式回归从报告引用找到捕获表，再把 URI、字段和文件字节哈希分别与单项输入比对。

| 错误代码 | 来源与字段 | SHA-256 |
| --- | --- | --- |
| `InvalidProjectionDeclaration` | `tech/layer-discretization.yaml#/coordinate_projection/layers/M1/y_edges` | `77c8c5c79c6f135339c7a0948f7d2704eb84194ba78a222eaa0035b063f08163` |
| `UnsupportedRegionOperator` | `tech/physical.json#/operators/rectangle_set_difference~11` | `6e61de7dec745b485734edd5f0ede049d69b09535386ad202930494680db13db` |

组合请求的原分析状态仍为 `unsupported`，40 条本地图形全部保留。drawn + effective 查询为 `not_evaluated`，`value=None`。同一输入仅查 drawn 时，占用状态为 `invalid_declaration`，算子错误仍在原分析 findings 中。省略查询时，占用结果为 `None`。三种调用的本地分析结果、顶层状态和 findings 相等。

修复提交的 Git tree 为 `5cf6ec15cf3171155f893cc06a3ab6495a5ad13d`。在其归档上用 CPython 3.12.14 实跑 W019 公开合同 12 项、W016 effective 及独立诊断回归 6 项，18 项全部通过。严格 mypy 通过 82 个源文件。sdist、wheel 构建通过，新 venv 从 wheel 安装后在源码目录外以 `python -I` 运行原探针通过。证据归档包含命令、原始输出、依赖、产物哈希及独立反例脚本 `pm01_extra_review.py`。[补修验证证据](W019/evidence/pm01-fix.tar.gz)

独立 reviewer 的定向结论见[补修复核](W019/pm01-fix-review.md)。原交付中未改的 W018 绑定与分格内核证据按源身份采信。源码、输入或依赖变化时补跑相关路径，双解释器全量按 PM1 安排在实际集成后执行。本分支交 PM 重新验收。

<a id="pm2-integration"></a>

## PM2 集成核验

补修产品提交为 `708c2a39c3d8a46514ac3aa2c01eb21aa334f9f7`。PM 核对交付版 `0429e49992be6cbdc207acb7c44c700a9673617f` 的产品与正式测试与该版一致，并核实补修归档中 11 份原始输出的 SHA-256。原始失败记录保留在 PM1。执行侧 18 项定向测试、82 个源文件的类型检查、构建及安装冒烟按该冻结身份采信。[补修复核](W019/pm01-fix-review.md)

[PR #81](https://github.com/LucianoHoult/Layauto/pull/81) 已合入 main。实际产品提交为 [679ff05](https://github.com/LucianoHoult/Layauto/commit/679ff05acfdca48132a914898041c95a6b668905)，Git tree 为 `fc6e4f30dc4df0b85c09a51c5afbad51c3092197`，与受审交付相同。PM 在候选上执行 2 项定向合同回归，并在候选和实际合并版分别运行 PM1 公开探针及 M1 查询示例。两项诊断及其原始来源均保留，查询状态为 not_evaluated，40 条本地图形保留，M1 线端可查回偏移 2352，三格宽 16、16、13 DBU。

阶段矩阵的两个独立干净工作区都检出上述实际产品提交。Python 3.10.22 和 3.12.14 各收集 2,010 个唯一节点，两份有序节点清单的 SHA-256 均为 `bb715d92a85369e09feb919e63301af0f6fabb9dcf2c6f0c08ac4bfd8b520c6c`。两侧正在运行整个 `tests/`，含 fixture_support。完整结果待回填。
