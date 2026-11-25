# W020 从同一次完整运行组装 Stage 2 初始状态所需事实

## 任务要求（PM）

W020 属于 M1 的 Stage 2。基线为已集成 W019 的 main `17437dc38abd66224ea3153c393e5199b1d9bd57`，执行分支为 `codex/w020-stage2-baseline-readiness`。2026-11-24 用户确认继续推进。已验收并集成。[PM 集成核验](#pm-integration)

**交付一条可运行的组装路径。** 给它一次完整运行已经读取并核验的输入，能从同一个 cell 的图形找到精确占用、物理区域、连通分量和已有网络标注，也能找回各自的输入依据。它应能指出哪些事实可供正式建立第 0 版快照使用、哪些仍缺少依据。第 0 版是后续规划和导出共同引用的起始版本。[架构 §2.3](../architecture.md#23-stage-2事实归一化与-layout-state-构建) · [M1 路线图](../roadmap.md)

| 验收项 | 可运行、可核对的结果 |
| --- | --- |
| A1 从完整运行取数 | 从真实 site、source/target CDL、GDS、raw query 和工艺文件调用 `prepare_inputs`。用同一 `InputsReady`、checkpoint 和其引用的已捕获内容组装。明确当前电路来自 source，目标来自独立 target，并绑定同一次读取的 layout、坐标及物理规则。执行前后核对同一 attempt 的阶段与版本。 |
| A2 给出一条跨组件实证 | 在临时样本中通过工艺包显式选择 W018 的逐层配置，用一个有 query 证据的导体贯穿 GDS 原记录 → 精确占用片段 → 有效区域及物理分量 → 对应的网络标注，列出每一步实际使用的标识和来源。逐段按精确区域及来源核验。另用 M1 的格 (2,2) 核对其 130 DBU² 线端与 GDS 偏移 2352。若目前某段连接缺失，给出可复现输入与缺失的关系，只在已有合同允许时补齐。 |
| A3 避免误组装、误判目标 | 用实际文件生成两份同名 cell、内容或绑定有差异的捕获。若接口接收外部组件，证明串用会被定位拒绝；若组件只能在单次捕获内部生成，证明两次调用交错也只引用各自的输入。再用 W003 的 `unsupported_target` 样本显示 FIN 数相同仍可有其他目标差异，保留具体器件、参数及来源供 Stage 4 使用。物理边由有效几何和工艺算子决定，query 只为已有区域或分量提供网络身份。 |
| A4 说清可用范围与发布缺口 | 对照架构 §2.3 的六类事实，对每项给出来源、能运行的见证，以及第 0 版发布还需要什么。原坐标配置和显式逐层配置分别展示，有无图形、缺声明、显式跳过与完整可计算覆盖须分清。保留无标注图形、本地 body 观测和外部 body 证据各自的范围。用一个具体缺项说明它会阻断哪一步，按所选样本和能力界定影响。 |
| A5 给下一步留下可复用入口 | 交付可复跑的调用例、定向回归和独立复核，记录受测版本。列出到首次正式发布的最小剩余动作及验收输入，分别标明属于事实组装、逐层初始化、原子发布还是后续无修改判定。在首次完整组装时记录耗时、峰值内存和报告大小，沿用已认证的对象或引用，避免把整份捕获反复复制进报告。 |

## 方案与执行

从 [W006 运行入口](../../layauto_v2/pipeline.py)、[完整运行的几何读取](../../layauto_v2/normalization/geometry_input.py)、[W014 端子关系](../../layauto_v2/normalization/terminal_relations.py)和 [W018 占用内核](../../layauto_v2/normalization/projection.py)开始。[W019](W019-single-cell-occupancy-query.md#pm2-integration) 提供可对照的只读分析结果。先画清同一份捕获如何传给各组件，用实际标识列出 A2 的示例，由独立 reviewer 核对事实所有权、来源绑定与失败行为，再实施。可以补必要的内部组装代码和小型合同测试。固定 fixture 使用临时副本，保留原件。

PM 在上述 main 用临时副本分别运行了 W006 读取、仓库凭据回读、W008 几何构建和 W018 drawn 投影。原配置读到 40 条图形，生成 0 个工艺网格片段。显式选择[逐层样例](W018/layer-discretization.example.yaml)后仍读到 40 条，得到 FIN 18、LI 20、M1 10 个片段。M1 (2,2) 对应 `source.gds` 偏移 2352，片段为 (32,48)–(45,58) DBU。两次 attempt 均保持 `unsealed`。这里核对到占用为止，跨到网络和连通关系是 A2 的交付内容。

本轮止于可复用、尚未发布的组装结果。W016/W019 的 `analyze_cell` 继续服务独立的单 cell 分析。完整运行沿用其已验收的输入选择和必填项。正式 `initialize`、已有 lineage 的 `seal_context`、Stage 3–5 无修改判定与收口、Stage 6 导出和回读各有自己的验收节点。若组装必须改变公开输入语义、证据权威或发布条件，带最小例子交 PM 决定。

开发、交付和独立复核默认跑新增及受影响项。已有 W019 双版本阶段矩阵按受测身份采信，后续全量由 PM 在阶段或里程碑集成时统一安排。改动运行代码时按影响做类型检查与安装冒烟，证据有缺口时补测对应路径。[验证分工](../collaboration/rules.md#verification-reuse)

## 执行结果、独立复核与 PM 验收

执行者追加方案、实现身份、复现命令、A1–A5 结果和未覆盖范围。独立 reviewer 追加跨来源反例、发现及修正复核。推回本分支交 PM 验收，PM 负责集成。

### 执行交付

交付候选 `e95ce132eee16dd8599fee1013a5c030491160ff`，运行代码 `2ef3662032332533046b4c294e4a3d3e5e9ea5e7`，任务分支起点 `fd629b1a0afc7b8dedb3ea0da52c86c574a7b210`。先按[执行方案](W020/plan.md)用真实文件跑通见证并取得[独立方案复核](W020/plan-review.md)，再实施。[独立交付复核](W020/code-review.md)含局部标注缩短、跨仓捕获交换两个反例及发现处置。交 PM 验收，集成由 PM 安排。

| 验收项 | 实际结果 |
| --- | --- |
| A1 | `assemble_stage2(repository, ready, fragment_budget=68)` 检查仓库 attempt、checkpoint 和对应的内容引用，由同一次回读构建 source、独立 target、layout、坐标和物理图。三种示例前后均为同一 attempt，`unsealed`、revision 1，无 terminal。 |
| A2 | LI 原图偏移 1648，格 (1,3) 的 drawn/effective 片均为 (28,30)–(34,40) DBU。它经 CONTACT@1840 连到 OD，经 VIA0@2096 连到 M1，分量共 3 个节点。R04 精确覆盖整片的 60 DBU²；`nXref.temp` 第 11 行将 n_lo 对应到 source CDL 的 VSS。另核 M1 (2,2) 在偏移 2352 的 130 DBU² 线端。各跳的完整 ID、原始 XY、源文件哈希及字段位置见[一次完整输出](W020/evidence/layered.json)。 |
| A3 | 两份同名 cell 从文件读入后移走输入树，在 A 的 parse 回读中完整组装 B，再继续 A。坐标、query、目标和 checkpoint 各自可查；移除 gate 标注后，物理图保持原有边和分量。串用另一仓库同 run ID 的 ready 被定位拒绝。W003 `unsupported_target` 的 MN0/MP0 源、目标及几何 FIN 均为 5/7，MN0 的 L 在 source.cdl 与 target.cdl 第 3 行第 39 列分别为 4n、5n；完整差异保留 `resize:channel_length` 及 `planner_admission_required`。 |
| A4 | 原坐标配置 40 条原图、0 个投影片；逐层配置 48 个 drawn 片和 20 个 LI effective 片，可逐源还原 FIN、LI、M1 的 25 条原图。七个有原图的层仍缺声明。两条 B 端本地网络未知，独立只读 body context 支持各自的 synthetic 关联。[六类事实、分层覆盖和发布缺口](W020/readiness.md)列出具体阻断以及每个后续动作的验收输入。 |
| A5 | 首次完整逐层组装 51.201 秒，实读到报告编码完成 52.669 秒，进程峰值 398.73 MiB，JSON 为 25,801 字节，未在报告中嵌套完整捕获。该次测量针对当前合成样本。受测命令、依赖、测试选择、安装及各输入变体的实测摘要见[验证回执](W020/evidence/verification.json)。 |

在项目根目录使用装好开发依赖的 Python 3.10+ 复跑。命令依次执行逐层样本、原坐标对照、FIN 相同但目标不同的对照。stdout 为 JSON，stderr 为用时、进程峰值和报告字节数。加 `--keep-input 新目录` 可在该目录的 `input/` 逐项核对原始字节。输入目录和 run request 参与捕获身份；独立复跑可按记录位置、覆盖范围和字段来源核对。

```sh
PYTHONPATH=. python docs/tasks/W020/example.py
PYTHONPATH=. python docs/tasks/W020/example.py --case original
PYTHONPATH=. python docs/tasks/W020/example.py --case unsupported_target
python -m pytest -q tests/contracts/test_w020_stage2.py
```

**验证分工。** Python 3.12.14 定向实跑新增 10 项、受影响的 W006/W007/W008/W014/W018/W019 合同 15 项，全部通过。严格类型检查覆盖 83 个源文件。sdist、wheel、干净安装依赖检查及安装版完整输入冒烟通过。W019 的[双版本阶段矩阵](W019/integration/stage-matrix.json)绑定 `679ff05acfdca48132a914898041c95a6b668905`，至 W020 起点的产品、测试及配置逐字节相同。其历史结果用于既有范围，W020 没有取得双版本全量结论。若代码、测试、相关输入、依赖或合并组合改变，先补跑受影响项；PM 在阶段集成版执行双版本全量。

## 执行 session 启动指令

> 以执行角色在 `codex/w020-stage2-baseline-readiness` 完成 W020 A1–A5。先用真实完整运行输入列出跨组件取数示例，经独立方案复核后实现。交付可复跑的一条链，从原图查到占用、物理分量和网络标注，并找回原始来源。验证两次捕获不会串用、FIN 数相同仍能识别目标差异，列出发布第 0 版前还缺什么。按任务卡跑新增及受影响项并做独立代码复核。将实现、命令、结果与完整 SHA 推回原分支交 PM。

<a id="pm-integration"></a>

## PM 集成核验

**W020 A1–A5 在 W003/W004 synthetic 范围验收。** [PR #83](https://github.com/LucianoHoult/Layauto/pull/83) 于 2026-11-25 合入 main。交付提交为 `752f1e5e0e52183e9d086d85a92ae097848e167c`，实际集成提交为 `6cd6b14d41b9f4bc32b64ca62d0be6a731d98391`。PR 候选与实际合并版的完整 tree 均等于交付版 `c8c7b437d90ec8b5238200414c296c1816247d55`。已核对发布版对应的两个受审 tree、默认报告与 W019 阶段矩阵的归档哈希。候选与交付版的 runtime、正式测试、配置、示例及其两个报告模块逐文件相同。

| PM 实跑（Linux，Python 3.12.14） | 结果 |
| --- | --- |
| 交付版，默认 `example.py --keep-input` | 从保留的 GDS 中以大端记录长逐条读取 XY。LI@1648 与 (1,3) 相交 60 DBU²，M1@2352 与 (2,2) 相交 130 DBU²。CONTACT@1840 和 VIA0@2096 与各自两端均交叠 16 DBU²。R04 经 nXref 第 11 行对应 VSS。报告内 45 处来源的文件哈希均与实际输入字节一致。组装 47.369 秒，报告 25,801 字节。 |
| 交付版，复跑[独立复核中的双仓探针](W020/code-review.md) | 同一请求两份捕获交叉使用均被拒绝。仅缩短 R04 直接标注，(1,3) 失去直接覆盖，正常版本同格为 VSS。两次组装的完整物理边和分量相等，各自仓库内容保持组装前的状态。 |
| 实际合并版，`example.py --case unsupported_target --keep-input` | 重算同样的几何见证，47 处来源哈希与实际文件一致。源、目标和实测 FIN 对 MN0/MP0 均为 5/7；MN0 的目标长度差异 4n → 5n 保留。两次示例前后 attempt 均相等，保持 unsealed、revision 1。 |
| 实际合并版，定向 pytest | `test_readback_rejects_foreign_attempt_for_same_run_id` 和 `test_normalization_and_new_domain_keep_pure_dependency_boundaries` 均通过。 |

CR-01、CR-02 的处置可追至[独立代码复核](W020/code-review.md)。原 10 项新增与 15 项受影响合同、83 文件严格类型检查、构建及安装冒烟按[受测身份与环境](W020/evidence/verification.json)采信。双解释器全量安排在第 0 版首次正式发布的 Stage 2 集成节点。当前只验证合成样本的事实组装；正式初始化、原子发布、无修改判定和生产 PDK/LVS 各按其所属节点验证。

下一项为 [W021 初始状态候选](W021-proposed-initial-state.md)。本轮的组装结果供其消费；缺失的 POLY 坐标仍保留具体用途与所需工艺声明。
