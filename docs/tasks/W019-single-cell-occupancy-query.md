# W019 在单 cell 分析入口查询工艺网格占用

## 任务要求（PM）

**阶段为可执行。** 本任务属于 M1 的 Stage 2。基线为已集成 W016、W018 的 main `0af9bfe18f9a8606d5b1cf3c707b8e75b28a064c`，执行分支为 `codex/w019-single-cell-occupancy-query`。执行 session 负责方案、实现和证据，独立 reviewer 复核，PM 负责验收和集成。

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
