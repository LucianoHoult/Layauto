# 首次发布第 0 版还缺什么

本例的输入是 W003/W004 的合成单元 `INV_M1_SYNTH`。使用完整运行的 site 配置、两个 CDL、GDS、raw query、工艺包和只读 body context。每次组装返回本次捕获的对象。示例 JSON 中的 `scope` 只摘取复核所需的字段，来源用捕获中的 URI、SHA-256 和可用的字段或字节位置标识。[调用示例](example.py) · [报告字段的计算](scope_report.py) · [架构 §2.3](../../architecture.md#23-stage-2事实归一化与-layout-state-构建)

## 六类事实

| 事实及其来源 | 可运行见证 | 第 0 版还需要的工作 |
| --- | --- | --- |
| 当前电路语义。source CDL 的声明，经 formats 与物理模型解释 | `current_semantic` 列出所选 cell、MN0/MP0、四个 net、source CDL 的哈希和语义摘要 | 以 source 草稿初始化可受事务更新的 current semantic component。把几何 FIN、端子比较与声明的提取保证程度分别记录。 |
| 独立、不可变的目标。target CDL 经同一方言归一化 | `immutable_target` 留有独立文件、语义摘要和差异 ID。正常样本两份原文不同而语义相等。采用 `unsupported_target` 时 MN0 的 NFIN 仍为 5，L 从 4n 变为 5n | 将目标与完整 typed differences 作为外部不可变引用绑定到 run context，把器件、参数、双方位置和未处理义务交给 Stage 4。 |
| 几何。GDS BOUNDARY 记录经 drawn 的层映射、formats 的单位绑定 | `geometry` 有 40 条记录，1 DBU = 1 nm。MARKER 在偏移 2608，范围 (145,180)–(150,185) DBU，`has_net_target=false` 仍保留原记录身份和位置 | 按声明生命周期装入唯一 layout store，保留单位、记录重数和来源。逐层初始化见下表。 |
| 标注。query header、原始 xref/shape、derived registry、源电路身份及精确区域 | LI 格 (1,3) 可追到直接覆盖该片的 R04、n_lo 及源网络 VSS。`annotation` 以本地标注目标的面积为分母，得到直接覆盖 3170 nm²、未覆盖 31920 nm²，直接冲突面积为 0 | 将 region/shape 上的标注、证据范围、有效性与保守处理方式冻结到 AnnotationTargetId 对应的状态。保留 MARKER 等非网络目标和导体上未覆盖部分。 |
| 占用。原图和有效区域结合本次 tech bundle 的坐标、单位、逐层声明 | `occupancy.layers` 对每层分别给出记录、声明、片数、精确重建数与诊断。M1 格 (2,2) 的覆盖为 130 DBU² | 对选定能力要求的层补齐声明、完成初始化和有效片反查，绑定同一个 coordinate model、单位、几何以及保守占用策略。 |
| 物理连通。有效区域结合 drawn/physical/rules 的接触、分离与连接器算子 | `connectivity` 列出 14 个本地节点、8 条边、6 个分量。两个本地 B 端各有 body 分量，`local_observed_nets=[]`。从 `body/context.json` 和本地 rail 标注独立得到 MN0→VSS、MP0→VDD，报告保留两个 association 字段 | 冻结本地成员和边，保存端子/外部 body 关系的独立范围、规则与保证程度。本样本采用合成外部路径， `local_graph_union=false`，实际 LVS 状态为 `not_run`。 |

## 原坐标和显式逐层配置

两次各通过 tech bundle 选择 coordinate owner。15 层的图形来自同一个 GDS 内容。不同坐标配置产生各自的 model id。每个 `drawn_reconstructed` 计数，都将同 record 的格片取精确并集，再与原矩形比较。`effective_reconstructed` 按 W009 piece 引用与精确矩形作同样比较。M1 的 W010 导体节点沿用原矩形。W009 为 LI、OD 产生可单独投影的有效片。[W018 逐层声明](../W018/layer-discretization.example.yaml) · [原坐标声明](../../../tests/fixtures/w003_m1/tech/coordinate.json)

| 层与本地原图数量 | 原坐标配置 | 显式逐层配置 |
| --- | --- | --- |
| FIN 18，LI 3，M1 4 | 各层均缺声明，均为 0 个 drawn 片 | FIN 18 个轨道片、LI 20 个格片、M1 10 个格片，可完整重建这三层的 25 条原图。LI 的 20 个 effective 格片还可分别重建 3 个 W009 原片。 |
| BOUNDARY 1，MARKER 1 | 缺声明，有图 | 显式 `projection_none`，保留两个图形及其生命周期。 |
| BODY_N 1，BODY_P 1，OD 2，POLY 1，CONTACT 4，VIA0 3，GCONTACT 1 | 缺声明，有图 | 这七层仍缺声明，现有图形可回查，工艺格片为 0。OD 有 6 个 W009 原片，均缺工艺格片。 |
| CUT、BTAP_N、BTAP_P 各 0 | 缺声明，无本地图形 | 均缺声明且无本地图形。零记录只描述这次捕获。 |

例如，POLY 在 GDS 偏移 432 有一条 (58,10)–(62,190) DBU 的栅。缺少该层的一维节距、相位和范围，无法把它初始化为可复算的栅轨占用。已有精确 POLY/OD 相交、器件定位和本地连通仍可核对。只读外部 tapcell 的形状不能补作本地缺失的图形或工艺参数。

## 最小剩余动作与验收输入

| 归属 | 动作 | 用于验收的输入和判据 |
| --- | --- | --- |
| 事实组装 | 以六类草稿及其缺项构建不可变 `ProposedInitialState` 和待封存的上下文。将未知区域、阻挡或可疑图形、标注有效性、工艺与单位等证据引用归入各自的状态对象 | 使用同一次完整 W003 捕获核对对象与来源。引入其他运行的资料应失败。标注覆盖不足的区域按适用策略保守处理，保留 local body unknown 和外部 synthetic 路径。 |
| 逐层初始化 | 在该能力所需的层上补齐并校验工艺坐标。按 drawn owner 的 `preserve_drawn`、`frame_static` 或 `prepublication_derived` 逐层核验并冻结几何 | 用声明齐备的 tech 包与原图检验逐源覆盖。C1 BOUNDARY 检查 frame/boundary 签名，C2 MARKER 检查 preserve 等价和来源。本包选 preserve 或 frame-static。将来选 derived 的层要绑定有版本的算子、依赖及等价比较器。缺必需声明或比较依据时应定位到层，阻止这项能力的发布。 |
| 原子发布 | 新 lineage 通过 baseline-only `InitializationTransaction` 与 `PublicationRepository.initialize`，一次创建 version 0 snapshot、InitializationEvent、head，封存 context 并推进 attempt revision | 对新 lineage、预期空 head、预期 attempt revision 及幂等键核验一次成功、同请求重放及冲突无部分状态。已有 lineage 取指定 head，核验 context 相容性后走 `seal_context`。本任务的 attempt 停在 `unsealed`。 |
| 后续无修改判定 | 已发布 snapshot 上，Stage 3 建约束上下文，Stage 4 核对整个目标，Stage 5 对稳定 head 做 CAS 并关闭本次 run | 以正常无变化样本、仅长度变化但 FIN 相等样本、提取不匹配样本，验证目标及适用的规则/提取义务。满足无修改判据且本轮无既往 ECO 时才记录 `no_change`、空 commit 链和实际 snapshot ID。随后 Stage 6 验收导出、回读、验证及最终报告。 |

前三项属于首次正式发布。最后一项消费发布结果，另行验收。[事务与运行阶段](../../architecture.md#26-stage-5可行性检查事务提交与派生刷新) · [逐层几何生命周期](../../architecture.md#94-policy-controlled-geometry-finalization)
