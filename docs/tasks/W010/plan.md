# W010 实施方案

执行者 `/root`，2026-11-05。基线和远端目标均为 `9758a157115cc22d91ce095ac2002209b9f210d3`，checkout `/workspace/Layauto`，开始工作区干净。只修改 W010 授权路径，不维护 current-work、PM阶段或验收。方案 review 前不实现产品。

## 输入、所有权与接口

公开入口 `normalization.build_local_connectivity(EffectiveGeometryResult) -> LocalConnectivityResult`。只接受成功、闭合不可变的 W009 捕获回执。验证原对象图后，用现有 effective codec 完整往返重建并与输入比较；这将再次执行 W009、W008、GeometryInput、NormalizationInput 和 direct/readback 捕获认证，避免只编码而相信已构造的成组伪造值。保留原 input 对象和全部 completed；不读文件/repository，不推进 attempt。取 W008 input.value.tech.rules 的完整 payload，并绑定 tech evidence.sources[6] 的实际 rules role；physical/drawn 同理。仅中立 domain/state 接受可自洽的非捕获值。

`domain/local_connectivity.py` 定义 frozen DTO、typed LocalRef(kind=operators/node/edge/component/audit/draft)、LocalContactBinding、ContactNode、ContactEdge、EnclosureSide、ContactComponent、ContactProblem。`state/local_connectivity.py` 定义 LocalConnectivityDraft 和纯 builder/重建算法。`normalization/local_connectivity.py` 负责认证、成功/错误回执；`local_connectivity_codec.py` 负责 closed/versioned canonical wire、digest，嵌套 W009 wire 不吞异常。所有新 DTO 先复制输入集合一次，随后只验证所存 tuple；在 aggregate 和编码入口先检查整个原始对象图的 exact types，避免复制掩盖别名。

binding 保留完整 physical/drawn/rules owner、effective draft ref、canonical unit ref、top 及固定 `local_flat_cell/1` scope。逐项核对消费的 same_layer_contact/1、cross_layer_contact/1、局部层 role/purpose/连接对/predicate/enclosure_rule，以及 T05 的版本、scope、predicate、unit、1nm参数、geometry_only、required、assurance 和 reject_indeterminate。owner 先走现有 schema 检查；未知/矛盾已消费语义定位 ContactProblem，不把 capabilities 或其它 required refs 当执行证据。完整 owner 留存，coverage 明示只执行两种接触与局部T05，外部BTAP/body、FIN/提取/标注/其余规则/lifecycle/发布均未执行。

## 精确图及 enclosure

每个 OD S/D、LI 独立 ExactRegion 是一个节点；每条 POLY/M1/BODY_N/BODY_P 原 record 构造单矩形 identity ExactRegion 节点。node 保留 layer、完整 ExactRegion 和 binding ref，owner/contributor record IDs 可回查完整 retained base。channel 不入图；POLY 原样连续；connector 不作节点；其余 record 仍在 base。非空本地 BTAP 定位 unsupported。BODY 同层几何接触可以成边，OD/BODY 不跨层 union，外部 context 不入图。

穷举所有同层无序节点对，每对遍历 exact rectangle pieces；正面积交叠或正长度共边即一条 same-layer edge，点/角不成边。无需 raw occupancy 候选，不漏 CUT 新边界。对每条 CONTACT/VIA0/GCONTACT record，逐声明侧穷举独立节点，任一 piece 正面积交叠才入候选；每侧候选数必须恰为1，在同层 component 合并及 enclosure 前计数。每条 connector 独立 edge，保留其原 record ID、source 和 geometry；重复 connector 各自保留，重复导体节点可导致歧义并拒绝完整成功。

逐 connector/侧保留独立 EnclosureSide(node ref、connector id、binding、exact margin ticks、pass/violation)，edge 不受 audit 状态影响。1nm / canonical_tick_nm 用 Fraction；扩张 rectangle 可以有理数。包含算法按扩张边界和 region x 边界形成 exact x slabs，每个 slab 合并覆盖的 y intervals，要求整个目标 y 区间无缝覆盖；不以 bbox、单piece或面积和判真。边界等号允许，孔洞自然失败。图构建成功可伴 `local_enclosure_status=violation`，该状态只指局部已执行的 audit，不是整个T05/mandatory/准入成功。

以节点全量初始化邻接，再按已证明边 BFS 分组，含孤立节点。所有排序按内容 ref；component 完整成员与 binding 进入 typed ref。neutral draft constructor 重建 binding、完整 nodes/edges/audits/components 并逐项精确比较，拒绝漏边、多边、假 union、孤立节点丢失、假 audit/单位/来源。叶 DTO 检查结构和 refs，aggregate 才证明完整性。成功回执重建并绑定同捕获输入，error 回执须重现同一个 located ContactProblem，保留全部 completed 和原输入；预期失败不提供伪成功草稿。

provenance refs 绑定 effective ref、owner/单位/scope/源 record/几何及完整成员。另设 semantic_digest：以节点 layer/role/exact pieces 多重集合、按这些几何签名表示的全部边(含 connector 几何重数)、分量成员多重集合、逐侧audit集合和单位生成，与 source record 顺序无关；不承诺跨 mutation lineage，不带 net/device 标签。

## 失败、codec与资源

只捕获 ContactProblem（现有 schema错误显式转换到该 expected policy 问题）。新算法、重建、嵌套 decoder 不 catch 任意 ValueError/TypeError/KeyError/BaseException；意外错误和中断原对象、cause/context/suppression 保留。wire 先核对 tag/字段/类型再调用 constructor；畸形值明确 ValueError。codec 对任何新公开 record 可 roundtrip，嵌套回执通过原 W009 codec，重建不会重新读盘。

有限 O(N² P² + CNP + C P²) 扫描，其中 N 节点、C connector、P 每region片数；实际 enclosure x slabs 逐片排序，最坏 O(P² log P)。分量 O(N+E)。aggregate 和捕获认证会重复重建，编码/解码另持完整输入 bytes；不引入新的隐含容量上限。记录实际候选/边/片数、构建/roundtrip时间和有限压力规模，不作生产性能承诺。legacy 的按cell/net名union不可复用；只参考一般 BFS/union 思路，v2 不 import legacy/tests helpers。

## A1–A8验证与交接

新增真实 direct/readback 无IO组合与来源伪造反例；独立正常 oracle 成员/几何比较（14/8/6及8 connector两侧通过）；cut-islands 临时重绑3/0；原 via_enclosure overlay VN边仍有而LN audit violation。手算接触矩阵涵盖部分/整边、点/角、gap、负/大整数、CUT非原轴、多片；歧义涵盖无侧、多侧、重复导体、已同层连通候选、enclosure不得消歧；重复connector单独audit。独立有限 arrangement 点/线测试验证几何和集合包含，重排比较语义摘要。

公开 constructor/wire 破坏节点、边、分组、audit、ref/unit/operator和递归alias，畸形wire与算法故障分别测；异常矩阵覆盖新算法及W009/base/captured/direct/readback所有嵌套链，比较原对象和完整异常链。旧1149项原样保留。Python3.10与开发3.12完整v2、strict mypy、新wheel/sdist、两套干净venv源码外真实direct/readback smoke及pip check；保存源码/测试/配置/fixture manifest、完整源码snapshot、命令/环境/退出码/stdout/stderr、包hash及安装来源。

方案由未参与设计者独立review，通过必须项后实现；代码完成后由未实现者独立review，原finding、处置及复核各自保留。最终实现/测试/证据/记录提交推送原分支并查远端完整SHA，交PM；不验收、不合main、不改current-work、不开始下一任务。
