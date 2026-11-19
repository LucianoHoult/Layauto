# W017 工艺坐标与占用投影建议

**首包建议交付两个可独立请求的能力**。在固定 synthetic 单 cell 上按已知 FIN 中心查轨道号；在调用者显式选定两条格边轴时，把 drawn 矩形或 effective region 的每个 piece 精确分片。调用者仍能读回缺轴层的原几何。样张的数值和原型接口供 PM 决策。

## A1　逐层来源

层名、tier 和投影策略取自 drawn owner。表中“矩形”对应原值 `exact_fragment_rectangles`。记录数来自主 GDS 的 W008 layout，外部 tapcell 不计入。二维覆盖的 X、Y 均指格边轴，轨道号使用条带法向的中心轴。空缺表示该投影所需的 pitch、offset、轴引用和有限范围都缺相应技术声明。每一行还继承表后的单位、原点和边界约定。[层表](../../../tests/fixtures/w003_m1/tech/drawn.json) · [逐层实数](samples.json)

| 层（tier） | 主记录 | 原投影 | 方向及所需轴 | 可用来源、范围与首包结果 |
|---|---:|---|---|---|
| BOUNDARY（C1） | 1 | none | 无 | 保留 frame record、边界和 policy，跳过投影 |
| BODY_N（B） | 1 | 矩形 | 面域 X/Y | 双轴空缺；保留本地 body 几何 |
| BODY_P（B） | 1 | 矩形 | 面域 X/Y | 双轴空缺 |
| OD（B） | 2 | 矩形 | 面域 X/Y | 双轴空缺；active 或 terminal 边界不能提供 pitch |
| POLY（A） | 1 | 矩形 | 实物沿 Y；要查轨道需 X 中心轴，覆盖需两格边轴 | 唯一条带 X=[58,62] nm、中心 60 nm；pitch、周期相位及轨号范围均未定 |
| FIN（A） | 18 | 矩形 | 实物沿 X；`fin_y` 为 Y 中心轴 | width 2、下边 offset 24、pitch 10 nm 已声明；观测中心 25…195 nm。候选编号 0…17，仅此 GDS。划二维格仍缺沿长度的 X 格边与从 Y 中心定格边的约定 |
| LI（B） | 3 | 矩形 | 二维 X/Y，不给 routing 首选方向 | 正式双轴空缺。候选 `li_x/li_y`，X [0,160)、Y [0,200) DBU，分别每 20/10 DBU 一格，可求精确覆盖 |
| CUT（B） | 0 | 矩形 | 自身二维 X/Y | 双轴空缺；策略保留，主图记录为空。扣除 LI 的算子另有声明 |
| CONTACT（B） | 4 | 矩形 | 自身二维 X/Y | 双轴空缺；接 OD、LI 的电学关系不提供坐标 |
| VIA0（B） | 3 | 矩形 | 自身二维 X/Y | 双轴空缺；接 LI、M1 仅用于电学解释 |
| GCONTACT（B） | 1 | 矩形 | 自身二维 X/Y | 双轴空缺；接 POLY、M1 的关系独立 |
| BTAP_N（B） | 0 | 矩形 | 自身二维 X/Y | 双轴空缺；保留声明与零计数，外部支持按原 scope 读取 |
| BTAP_P（B） | 0 | 矩形 | 自身二维 X/Y | 同上 |
| M1（B） | 4 | 矩形 | 二维 X/Y，无声明首选方向 | 双轴空缺；水平实物、最小线距均不足以定轨 |
| MARKER（C2） | 1 | none | 无 | 保留未标注 marker 的 record 和 policy，跳过投影 |

**已声明。** `tech/coordinate.json#/coordinate_projection` 给出源 cell 局部坐标原点 [0,0] nm 及单位引用，标记 example_only。两项 GDS UNITS REAL8 由 `toy_gds_real8_nm/1` 分别精确解码并绑定 nominal；source tick 与 canonical DBU 在此样本均为 1 nm。保留 source XY 整数、单位 raw/精确值/nominal/差值与 unit_ref。坐标 GCD 不能确定物理步长。FIN 三个参数的字段分别为 `fin_count_profile.fin_width_nm`、`fin_lower_edge_offset_nm`、`fin_pitch_nm`。[坐标](../../../tests/fixtures/w003_m1/tech/coordinate.json) · [单位](../../../tests/fixtures/w003_m1/tech/formats.json) · [FIN](../../../tests/fixtures/w003_m1/tech/physical.json)

**观测与候选。** 水平 FIN 的 18 对上下边沿确定本样本的有限观测窗；把第一条编号 0、用闭区间 [0,17] 开放查询，是本次选定的接口约定。单根 POLY、实物边界、via 上下层、DRC 最小间距均不能补出周期、相位、方向策略或整层适用范围。LI 的 20×10、两个零格边偏移及 8×20 格均为新 synthetic 假设。覆盖窗取当前 frame 大小方便检查；没有 PDK 依据。S2 有限边列表为题设纯数学输入。S3 的 32×16 nm、原点和同格多片来自专例的手选 `index_witness`，调查脚本用该例 frame 上端向上取整限定桶数 5×13。三组格子各用自己的声明。[MR-051/052](../W003/manual-verification.md#mr-051网格必须有来源及分层坐标模型现粗索引见证不足2026-10-09) · [专例说明](../../../tests/fixtures/w003_m1/special/cut_islands/spec.json)

## A2　选择、计算与返回合同（待 PM 确认）

**输入选择。** 拟增加独立组件调用 `project_coordinates(geometry_result, selection, requests, *, effective_result=None)`。selection 指定单独的版本化候选文件；原型用同目录的文件名解析 URI。正常入口先完成 W005 读取、W008 同捕获认证。新 adapter 一次获取 selection 和 file 的原字节，校验版本、重复或未知字段、类型及引用。检查所选 SHA-256，再从同一 W008 receipt 取得已读 bytes，对比 tech bundle、drawn、formats、physical、coordinate、source.gds 六项实际哈希。GDS 绑定把样本有限窗限定在指定实物。产品可扩展为 tech model 与 per-capture domain 分开绑定，本包先用这一种。调用者替换了显式选择才会启用新字节；SHA 证明内容身份，工艺依据另列。原型只消费随文件列出的调查子集。[选择](selection.json) · [最小候选](candidate.json) · [绑定及换算](model.py)

| 字段/请求 | 语义 |
|---|---|
| `schema, classification, bindings` | selection 为 `w017-selection/1`，owner 为 `w017-coordinate-proposal/1`，synthetic。正式版本号和解释待批准 |
| `axes.<id>` | 中心轴 `fin_centres_from_profile` 仅用于此 toy 的 Y 法向，读取已绑定 physical 三参数，`indices` 为首末有效编号。规则格边 `regular_edges_dbu` 按 dimension、offset、正整数 pitch 与正整数 cells 定义。offset 相对源 frame origin，轴范围为 origin+offset 至该值加 cells×pitch；中心/格边不能互换 |
| `layers.<name>` | FIN 引用 track，B 层逐名引用 x 与 y；轴角色、法向及 policy 须兼容，不能从名称或邻层猜值。省略层或其中一根轴允许保留部分资料。显式悬空或错向引用使整份选择无效 |
| 轨道正反查 | 该 fixture 原点为零；正查 y=24+2/2+10k nm，逆查用有理数 (y−25)/10。域内非整数保留夹住它的两个 k 和有符号 `y−centre(k)`；两端之外标 outside_range。接受精确整数/有理物理点；图形始终保留原矩形。该首包条带限固定宽度、沿 X 的水平 FIN。双向、jog、pin、非条带等保留 exact 2D，按能力返回 unsupported_strip 或另行请求有声明的二维覆盖 |
| 点与矩形 | 一般格边 eᵢ 的 cell 为 [eᵢ,eᵢ₊₁)，二维取笛卡儿积；左下含、右上开。点可用 Fraction。矩形为正面积整数 canonical DBU，完全在域内时允许最大边贴外边。跨出任一边整项 outside_range，不交部分覆盖。面积与物理距离仍由源尺度换算 |
| 返回范围 | complete-model 请求在任何所需轴缺失时报告缺层/轴，可同时读取原几何；单项查询逐项返回 on_track/off_track、覆盖片段、missing_axis、projection_none、unsupported_strip 或 outside_range。invalid_declaration 单列并带文件 URI/hash、字段或字节定位；保留先前捕获资料。错误输入类型为 invalid_query；合规但超预算为 resource_limit |
| 身份与所有权 | 返回 envelope 绑定 schema、实际 selection/model/单位/geometry ref、层及请求；每片有 cell(i,j)、覆盖矩形、drawn record ID 或 effective region+piece refs 及 owner、CUT contributors。索引键含模型/域身份与 drawn/effective 视图；失败保留原请求位置和来源。产品 adapter 必须确保 effective.base 与所选同一 W008 base 完整匹配。散列使用规范 exact wire；相同 bbox 的两条 record 仍可区分 |

例如 `track(FIN,30 nm)` 返回 `off_track`，原 y=30，邻轨 (0,+5)、(1,−5) nm。`cover(LI, source.gds@record[...])` 的首条实物 [28,30,34,55] 在候选上得到 cell (1,3)/(1,4)/(1,5)，覆盖 Y 依次 [30,40)、[40,50)、[50,55)。一个漏写的 LI.y 报 `missing_axis @ /layers/LI/y`，写成 li_x 报 `invalid_declaration` 并回显错引用。机器样张以 JSON 字符串保留有理数，片段的模型/单位随上层 envelope 共用；调查表示不构成持久化产品 wire。[完整结果](samples.json)

**兼容与完整性。** W005 仍按旧 owner 的 example_only/不完整标记校验；W008 的 `drawn-layer-edges/1` 仍由每层实物边界重建，查询旧结果时仍得到原索引。新坐标草稿另有模型身份，不能填进旧 BaseCellId、替换旧 fragment 或作为完整 ImmutableContext 的 coordinate_ref。W016 的旧 manifest/header 及 `analyze_cell` 仍可在无外部 tapcell 时核对本地 D/G/S，B 与父级关系依 W016 保持未知。选中却无效的证据要定位报错。后续调用者逐一显式选用新版，跨索引比较以 record/region 和 exact coverage 重投影。[W008 合同](../W008-geometry-base-occupancy.md) · [W016 合同](../W016-single-cell-analysis.md)

## A3　实算和对照

从仓库根目录运行，使用 Python 3.12.14、PyYAML 6.0.3。第一条是 PM 起点；第二条从主 site 和隔离的专例副本产生实际结果；第三条对照保存的确定性输出。资源采样单独运行，时间/峰值允许随机器变动。

```sh
python -B docs/tasks/W017/pm_preflight.py
python -B docs/tasks/W017/run.py > /tmp/w017-samples.json
cmp /tmp/w017-samples.json docs/tasks/W017/samples.json
python -B docs/tasks/W017/run.py --resources
```

| 样张 | 实算与独立于实现的算术依据 |
|---|---|
| S1 | 第一个 FIN 上下边 24/26 nm → 25，第二个 34/36 → 35，末个 194/196 → 195。反查分别为 k=0、1、17。逆算 30 得 1/2，正向查两个相邻 k 各差 ±5。24.99 nm 已在这次中心域外。每条记录的两边、center、反算、record ID、stream index 与 byte offset 均可查 |
| S2 | X=[−6,4,14]、Y=[−3,1,5]，按 X=4 和 Y=1 切开 [−2,−1,6,3]。左右宽 6、2，各列下上高均 2；两列面积 (12,12)、(4,4)，合计 32。两组半开区间分别无缝并成 [−2,6)、[−1,3)，故积的并集等于输入，内部无重叠。[−2,−1,4,1] 仅落 (0,0)。3.99/0.99 与 4.01/1.01 分落两侧，点 (4,1) 属 (1,1)，外端 x=14 或 y=5 不属于任何格。每个片段引用单独输入文件的矩形序号 |
| S3 | 使用 W009 的临时捕获重绑器选择实际专例 GDS，更新 top、header、raw xref、body 的 bytes/hash 使 reader 能读取；仅用几何。W009 从 LI 与 CUT 求差。LB=[130,20,150,24]，CUT=[139,18,141,26]；交区宽 2、高 4，80−8=72 nm²。有效两片 X=[130,139)、[141,150)，Y=[20,24)，各 36 nm²。专例桶 (4,1) 为 [128,160)×[16,32)，两片均完整落入，region/piece 各异。第三条 LI 在 (1,1)，面积 40。原型只取 spec 的 index_witness，不读 annotations/shapes 作几何输入。查询桶不改变物理图；即使同名，2 nm 间隙仍在 |
| S4 | 原坐标 owner 能读原点、单位和 40 条原图，无法提供可执行全层工艺轴；S1 的 physical/实物证据可另行绑定。候选 LI 投影有 20 片。副本 Y 格边 offset 加 1 后有 23 片，首片只到 y=31；改为 X 每 10、Y 每 20 有 16 片，首个 record 横跨 x=30。漏 Y、错引用、错向、零 pitch 及更改文件却沿用旧哈希均有独立输出。把首根 FIN 作只读矩形查询，平移 +5 DBU 得 off_track，−1 得 outside_range，每个结果同时存原 record 和查询位置 |

S2 的源输入、手算和生成结果分开保存。S4 每项 edits 应用于原 candidate 的独立内存副本，按 `run.py:variant` 的 JSON 编码重算字节 SHA，再绑定新的 selection；stale_selection 专门保留旧哈希，错误与已选/实得身份同时可见。S3 用 temporary directory，正式 site/GDS/fixture 未写入。[数学输入](math-input.json) · [入口](run.py) · [实算输出](samples.json)

## A4　实施归属与成本

**依赖顺序。** importer 获取受选文件与字节身份；tech 校验声明；normalization 对照 W008 成功 receipt 与 W009 base（选 effective 时）做同源认证。state/coordinate 仅接收已解析数值做正反算；layout_store 保有 drawn，regions 提供独立有效区，occupancy 收集多片并建立按 cell/owner 的只读查询。后续 connectivity 从精确 effective geometry 求接触，annotation 引用 region/fragment；planner/CSP/transaction 可取占用作范围查找。生产者、计算与持有者均有唯一归属。[架构 §3.4–3.6、§11.3](../../architecture.md)

**可取用的实现。** W008 的 Rect、UnitBinding、LayerPartition 精确边界二分及求交可直接用；显式等距轴用整数向下/向上整除确定命中段，可避免展开长轴。W009 已有 CUT 差集、region/piece 与贡献者引用。legacy 的方向/逆算概念可参考；`round((coord_nm-offset)/pitch)` 会把半轨吞为一个整数，大坐标还会损精度。legacy grid 的 b_tier_cells、solver 的 deepcopy、net segments 及 engine cells 若分别写入会产生多份不同状态。新服务持不可变参数，在占用 owner 一次生成片段。[W008 坐标](../../../layauto_v2/state/coordinate.py) · [W009 有效区](../../../layauto_v2/state/regions.py) · [legacy grid](../../../legacy_mvp/core/grid.py) · [legacy solver](../../../legacy_mvp/core/solver.py)

**资源实测。** 主 GDS 为 2,680 bytes，40 条 drawn；W008 原索引为 41 个已占层格、41 个片段。下表仅量 3 条 LI 的新投影，含返回列表及已占格去重。单进程单次 tracemalloc Python 分配峰值与单调时钟；不含读取、认证、W008/W009 构建、持久化、进程 RSS。时间不作为 SLA。[原始读数和副本参数](resources.json)

| 候选 LI 格 | 可能格数 | 已占格 / 片段 | 耗时 ms / 峰值 bytes（本次） |
|---|---:|---:|---:|
| 20×10 DBU | 160 | 20 / 20 | 0.543 / 4,648 |
| 同窗细化至 1×1 DBU | 32,000 | 1,110 / 1,110 | 12.300 / 324,464 |
| 每轴扩至十亿格，pitch 保持 20/10 | 10¹⁸ | 20 / 20 | 0.616 / 4,648 |

单矩形命中量为两轴命中格数的乘积；所有 record/piece 单独累计，重复图形照计。规则轴查询 O(1)，有限不均匀边列表二分 O(log Nx + log Ny)，枚举及存储 O(实际片段总数)，已占格索引 O(已占格数)。S3 说明计数不能只看已占格。原型用整数先算乘积，每次从调用剩余预算扣除已交片数；10⁹×10⁹ 的满窗矩形在首片分配前报 resource_limit(10¹⁸)。失败不返回局部占用。10,000 是探针的测试预算。产品首包需把预算作为明确的运行限制，先预估总量再流式生成，整次成功后发布只读结果；超限保留原几何、请求及计数，不擅自放粗 pitch。

## 交 PM 的具体决定

1. **新输入与调用。** 建议采用上述单独选取、带哈希的部分模型和只读组件入口。代价是多一次选择及模型身份；旧 API 的相同输入不改变输出。批准时需确定正式 schema/API 名及可持久化范围。
2. **首包支持的解释。** 建议 FIN 只给本样本 Y 轨，闭区间 0…17，半轨返回两侧有符号偏差。LI 的 20×10 DBU 与 0/0 偏移只作为显式 synthetic 样张，其余轴暂缺。要扩大范围，需要 profile 提供方向、相位、节距、有限域和中心至格边定义。
3. **可见结果与失败。** 建议按请求返回部分能力与逐项诊断，显式无效声明拒绝整个模型；越界矩形不裁剪，同格可返回多片，返回来源及精确覆盖。预算超限返回数目与位置。需要 PM 确认这一外部预期及产品预算选值；10,000 仅供本轮试算。

[首个实施 prompt](implementation-prompt.md)
