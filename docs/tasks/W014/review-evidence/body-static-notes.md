# W014 body 独立只读专项

Reviewer `/root/plan_review/rule_scope_check` 未参加对应方案设计或实现。
本文件记录实际检查范围；最终合并结论由主 reviewer 维护。

## 已核依据和边界

读取根 AGENTS、协作 review/验证复用条款、W014 任务/方案/body 调查材料，
真实 reader `_body`、tech schema、W010 local owner admission、W011 真实
ChannelIdentityDraft、W013 annotation 入口，并静审新增 terminal domain、
derive aggregate、normalization/codec 和已有正式 W014 测试。

截至本段检查时 `derive/body_relations.py` 尚未落盘，因此下述结论不代表该模块
已 review 或 A3–A5 实现通过。未运行产品捕获链、全量、typing 或安装矩阵。

- Aggregate 使用同一 W010 输入，normalize 一次并调用真实 W011/W013 neutral
  builders。逐 source device 保留四个 ordered target；共享 gate 仍分别关联两器件。
- body observed 与 local observed 分列；local graph 不增加边或 union。source
  comparison 因 issues/unknown/conflict 保持 indeterminate，原 FIN mismatch 可达。
- reader body record 有序保留 context 文档与实际 source GDS 两个来源；不能把它
  当 single-source derived owner。新增 aggregate 已明确两来源闭合。
- W010 已拒绝其它新增 body/body_contact 导体层；但刻意豁免 BTAP_N/P 的外部
  connector 声明。W014 因而必须核这两层 electrical_connects、contact_predicate、
  enclosure_rule，不能认为“已有 tech schema”已经证明其物理语义。
- 所有 external shapes 均应满足 scope；全部 local/external N×P body pair、全部
  external tap 应被审计，不能只沿两条成功声明路径循环。

## 已报告事实摘要问题

初稿 `TerminalRelationsDraft.coverage` 固定 `lvs_status='not_run'`，而真实 reader
准入 `not_run` 和 `unknown`。仅将 context 的该字段改为 `unknown` 并真实重绑，
仍可进入 W014；固定摘要会改写已捕获事实。已报告主 reviewer，纳入其 CR02；
修正与关闭由主 review 维护。此项来自明确分支静审，未冒称运行该产品反例。

## 独立原始资料数学核对

用 Python3.12 标准库只读 `body/context.json` 与独立 `spec.json`，使用 Fraction
自行计算边界长度、四边 margins、全候选集和异型 body 正面积交集；没有导入
runtime body helper 或被审算法。实际输出如下：

| device | body/rail 边长 | active margins | tap body margins | tap rail margins |
| --- | --- | --- | --- | --- |
| MN0 | 90 / 10 | 20,20,20,20 | 8,50,8,36 | 8,2,8,4 |
| MP0 | 100 / 10 | 20,10,20,20 | 8,50,8,46 | 8,2,8,4 |

body 候选分别仅 BN.ext/BP.ext，rail 候选分别仅 MN/MP。本地唯一 N×P pair
BN/BP、外部唯一 N×P pair BN.ext/BP.ext 的正面积交集均为零。
精度控制 `Fraction(901,20) != Fraction(45)` 为 True；B 的 rail 关联必须有
完整精确 bbox 证据，不能以已知 local component consensus 遮盖这项差异。

## 后续必核

待 body 模块就绪后逐字段核来源/绑定、全对象 audit、边与点/面积判据、全部
候选唯一性、规则阈值/语义、exact query rail、claim 与 observed 分离、错误路径
保留及实际所有状态。此专项实跑限上述轻量独立数学；上游合同与原验收证据仅作
身份明确的依据，不替代新 W014 最终双矩阵。实现或输入变化触发受影响复核。

## body 初版静审（模块落盘后）

实读 `derive/body_relations.py` 全部初版；本段仍不冒称捕获链产品实跑。
以下具体问题已分别报告主 reviewer，finding 编号、修复与最终关闭由主报告维护：

1. 每器件循环的 `issues[:start]` 包含以前器件的局部错误。只把 MN0 的
   association.local_body 从 BN 改为 BP（reader 两者 body role 均准入），MN0
   产生 BodyObjectBindingMismatch 并提前 continue；独立正确的 MP0 在循环末
   看到该旧错误，也被清空 observed/chain。这把局部错误传播到了无依赖的器件。
   应区分循环前真正的 global binding 错误与器件局部错误。
2. `edge_length` 只检查任意共享边，没有要求接续坐标等于 FRAME.x_min。将本地
   MN body 和 rail 左边改为 -10、相应 external 右边改为 -10、tap x 移到
   [-18,-14]，并真实同步 GDS/context，可保持 active 包围及 tap enclosure；
   external 仍满足 x_max<=0，generic edge 给出90/10，但接续在 -10 而非 FRAME
   左边0。上游 W010 不执行 T01，不能假定所有本地图形已证实在 frame 内。
3. global binding 错误最后才清 chain/observed，早先计算的 rule_status/claim_status
   可能仍为 satisfied/equal。几何 margins 可保留，依赖无效绑定的通过判断需要
   同步失效或重新计算，不能互相矛盾。

另已提示两个 API/范围核验点：独立 `evaluate_body` 的 source closure 不应只看
local_ref；以及 exact rail VSS 同时伴随部分重叠 VDD 的 W013 conflict 时，B 的
有限 exact 比较不能遮盖该冲突。Aggregate 从同源重建并保留全部 W013 issues，
这两点尚待主 reviewer 决定所需具体 API/状态约束，不在本专项冒记为已复现失败。

## 修后静审

已完整复读 body 模块 SHA-256
`be59c340a021d9a9a3f25fa97729a8f2040c769522c9d36cbda6595377cad485`。
主报告已将上述问题编号为 CR04（器件间污染）、CR05（失效状态）、CR06（FRAME）、
CR07（exact anchor 遮盖冲突），另 CR08 记录未消费 gate_operator 语义。

- CR04：global_binding_invalid 在 device 循环前冻结，器件局部问题不会进入它。
- CR05：geometric 先包含全局有效性，后续 rule/claim 不会继续通过；实际几何
  margins 与已证实违例仍保留，不把事实全部丢弃。
- CR06：候选使用 frame_edge_length，要求 local.x_min 与 external.x_max 同等于
  FRAME.x_min，且 Y 方向交集严格正长。generic edge 数值只作为另列几何事实。
- CR07：存在 exact rail anchor 后，再合并该实际 local component 的全部 net
  与证据，部分冲突不再被完整 bbox 遮盖；没有 exact anchor 时仍不会凭分量
  推出 body 证明，45.05 对 45 的要求保持。
- CR08：_EXTRACTION 已校验现行 gate_operator 完整文本。schema 仅准入任意
  text 不代表已支持其语义，新门可定位拒绝改变的 gate 解释。

新增正式 body_scope 测试静审覆盖以上反例及 orphan tap、额外异型 body overlap、
点/边触碰等范围。静态支持这些修正；实际产品探针由主 reviewer 跑并维护关闭
结论，本专项没有冒称独立重复运行。当前未发现新增 body 静审阻塞项。

## 调查纠正：gate_operator 的真实拒绝边界

上述 CR08 关于“公开链未验证 gate_operator”的归因撤回；原调查记录保留，不能
据此宣称 W014 修复了公开准入漏洞。本专项先前只检索 W010/W011 相关检查，
遗漏 W009 的 `domain/regions.py`：`CONSUMED_PHYSICAL` 已列出
`/device_extraction_contract/gate_operator`，`OperatorBinding.__post_init__`
逐项核对所选 physical owner，改变的语义返回 `UnsupportedRegionOperator`。

实际 [targeted-r3 原输出](../development/targeted-r3.stdout.txt) 为 **64 passed /
1 failed**：失败原因是新测试准备误以为此变体可以进入 W014，但真实调用链已在
reader→W008→W009 拒绝，错误明确定位 `tech/physical.json` 的上述字段。本次
只读取该原证据与 W009 实现，没有重复运行产品链。不能把这个失败记成 W014
公开行为缺陷，也不能把后续测试改正记成 runtime 修复。

root 将正式测试改成核实际 W009 拒绝边界；W014 runtime 不因本纠正改变。
新 body neutral evaluator 的防御性 gate 文本检查可以保留，但其价值仅是中立
输入边界防御，不能声称关闭了此前不存在的公开缺口。CR08 的 public-missing-guard
must 归因已撤回，主 reviewer 维护最终 finding 状态与修后证据。

## 最终 body / aggregate 静审状态

最后仅用只读文件检查复核任务 A3/A4/A5/A6；没有运行产品 probe、pytest、
wire 或资源命令，未与 root 的 R4 资源工作并发执行产品链。实际核对身份为：

| runtime 文件 | SHA-256 |
| --- | --- |
| `derive/body_relations.py` | `be59c340a021d9a9a3f25fa97729a8f2040c769522c9d36cbda6595377cad485` |
| `derive/terminal_relations.py` | `f3ff5334b0d29ccf818ad7b50a3c6983b4418b733a02c8a8db18a91477d54c4a` |
| `normalization/terminal_relations.py` | `456f5421607812a6a65bc36d6d87b64c95322d2d52def37da4804a0a9acce27e` |

**本专项未发现新的必须修正项。** 现行 toy 范围内，body 模块逐一匹配所有提供的
local binding，核唯一实际 FRAME 和全部 external scope；全部本地及外部 N×P
body pair、全部 external BTAP 均有审计，含未被成功 association 引用的对象。
每个已准入 source device 对应 active 的 typed local body 唯一性和四边 enclosure
单独核算，额外未关联 active 明确标 indeterminate。T04/T05 阈值取同源规则；
几何正面积/FRAME 正长度接续、规则 enclosure 和网络/claim 比较分列。

T05 的新增计算限外部 tap，原本地 T05 audits 和状态经同一 local 对象完整保留；
没有以外部成功覆盖本地 violation。B 的证明要求 exact rail anchor，随后保留
该实际物理分量的全部冲突网络，45.05 与 45 不会被取整或 component consensus
补成证明。器件局部错误不再污染其它独立器件；全局绑定失效不会留下通过的依赖
状态。每个 source device 的 D/G/S/B 完整输出，source expected 与 observed 分开，
原 W011 4 对 5 差异及 W013 coverage/conflict 可达；不制造本地 union 或外部节点。

CR08 的公开漏洞归因仍按上节撤回：改变 gate_operator 已由 W009 拒绝，新增
neutral 防御不能被称为修复该公开边界。其它 findings 的实际独立修后探针与关闭
状态以主 review 原证据为准；本节仅提供独立静态复核，不代写总 review 或 PM
验收。未覆盖真实 EDA/PDK、生产 U06 实现、其它 mandatory rules、完整 LVS/
model/VT/pin-access、baseline/no_change/Stage6；最终工程矩阵/安装/资源证据由
相应 reviewer 按实际冻结身份核验。本节所列相关代码或输入变化时补受影响复核。
