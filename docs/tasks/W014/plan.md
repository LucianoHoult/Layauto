# W014 具体执行方案

执行角色；基线 `8f3f39562ed04d790c8d6c015f7c9b8742b6a3c4`，产品基线为
W013 已验收实现。本文待独立 review；review 必须项关闭前不实施 runtime。
遵循 [任务](../W014-terminal-body-relations.md)、[架构](../../architecture.md)
§2.3、3.3/3.6、4.5–4.7、5.6–5.9、11.2/11.5/11.9/11.15。

## 输入、复用与最小文件表

公开 `build_terminal_relations(LocalConnectivityResult) -> TerminalRelationsResult`。
只接收成功的真实 W010 捕获结果，适用于 reader direct 与 W006 caller-read
readback；不接收两个可任意拼装的 W011/W013 Result。公开构造先检查原始
closed/native graph，再进入**未改的 W010 canonical encode/decode**认证完整
reader→semantic/geometry/effective/local 来源链。normalize 同一 semantic_input
一次，从其真实 identities/seeds 构建 W011 ChannelIdentityDraft 与 W013
AnnotationDraft，使用现行公开纯 builder，不重新实现两项算法。

| 文件 | 职责 |
| --- | --- |
| `domain/terminal_relations.py` | 最小 TerminalTarget/TerminalRelation/ref，native/closed/immutable validation、source/observed 分开、canonical value |
| `derive/terminal_relations.py` | 中立聚合：一次 local/source/seed/owner 输入，重算 channel/net/body 和全部关系；保留紧凑 channel observations、完整 W013 compact annotation 与差异 |
| `derive/body_relations.py` | 独立只读 body 几何链、全部 T04/T05 适用对象、精确 rail evidence 与 claim 对照；细节见 body-design-notes |
| `normalization/terminal_relations.py` | 捕获认证及结果，完整输入只保留一次；expected error 形成 located issues；意外异常原样传播 |
| `normalization/terminal_relations_codec.py` | 新版本闭合 wire；Result 中一次完整旧 W010 canonical Value + compact outputs；neutral draft 保留一次 neutral local context 及完整 source/seeds/owners |
| `normalization/__init__.py`、`pyproject.toml` | 导出新入口及纳入 strict typing |
| 新 `tests/contracts/*w014*`、`tests/unit/*w014*`、case helper | 真实 reader 组合、精确独立数学/攻击/错误历史；测试数据仅临时副本 |
| `docs/tasks/W014/` | 方案/review/执行/资源/验证证据与 U06；任务文件只更新执行者所属段 |

不修改 W011/W013/旧 codec 或 fixture、spec、oracle、expected。不会导入
tests/support/w004_body 或 legacy 作为 runtime；它们只是合同/反例调查。

## 中立输入与同源闭合

`TerminalRelationsDraft` 保存一次 local、source、channel_seeds、net_evidence、derived、
body EvidenceRecord、capture_binding。输出字段由构造器重算（init=False），公开
encode 会重建并逐字段 canonical 比较，防止 frozen shell 被 object.__setattr__
篡改。新叶 DTO 逐字段检查 typed IDs、role/ref kinds、唯一完整序列、native scalar、
FrozenMap tuple backing 与循环；先检查原存储，再作防御快照，拒绝可写 alias。

neutral 层验证完整 local 重建，source 的全部字段/preservation 重建，W011
seed provenance/derived operand 和 W013 capture_source set/fragment/component
closure；比对 channel source、local/effective/layout/unit/operator refs 和 annotation
同一 source/capture。body EvidenceRecord 有序保留两个来源：sources[0] 为唯一
context 文档 owner，sources[1] 为它绑定的实际 source GDS；两项 URI/hash 都必须
属于同一 captured source set，不能丢 GDS 来源或把两项顺序互换。其 payload
schema/role、source GDS digest、top、unit/profile/identity transform、FRAME、
所有 local body/rail bbox 均回绑真实 GDS record 与 SourceRef。rules 来自
local.binding.rules，同 physical/drawn/derived 的捕获 owner 经公开旧链认证。
neutral 自洽不冒称 captured-input receipt，Result 才承担捕获真实性。

## target 与状态样张

TerminalTarget 由 binding ref + DeviceId + ordered role D/G/S/B 标识；同一共享
gate node 可以属于两个不同 device/role targets。Relation 分列 source expected
NetId/SourceRef、channel ref、local node/component refs、W013 target/evidence refs、
local observed nets、独立 body path ref/context observed nets、comparison。
CDL port 只保留 semantic 事实，不声明物理 pin access。target intent 不参与 source
比较；Result 另保留一次 compact `semantic_facts: NormalizationFacts`（无 captured
input 子树），直接保留 immutable target 和全部 target differences。完整 semantic
input 同时仍由原捕获 input 可达，并在 coverage 中指明。

| target | expected | local observed | context observed | 判定 |
| --- | --- | --- | --- | --- |
| MN0.D / MN0.G / MN0.S | Y / A / VSS | Y / A / VSS | 空 | equal |
| MP0.D / MP0.G / MP0.S | Y / A / VDD | Y / A / VDD | 空 | equal |
| MN0.B | VSS | unknown（BN component） | VSS（独立已证链） | equal |
| MP0.B | VDD | unknown（BP component） | VDD（独立已证链） | equal |

无 observed net → unknown，多个 observed nets → conflict，唯一且不等 expected →
mismatch；定位缺项/多义、缺链 → indeterminate 并有 located issue。不能调换 S/D
消除 mismatch。normal result success 只表示组件计算完成；terminal comparison
equal 不等于 source extraction equal：extraction_mismatch 仍保留 MN0 4 对 5。
upstream semantic admission error 可无 draft；channel/annotation/body 的 expected
component issues 可保留完整 diagnostic draft。误绑/错误 supplied evidence 不降级
为普通 unknown；Result error 与 relation 状态分列。unknown/conflict 不算通过。

逐 source device 的四角色必须有一行，包括无法定位时的诊断行。builder 对所有
source devices、recognized channels、body associations 作完整性/唯一性检查；
重复/遗漏/外来 target、遗漏 audit、被改输出均不能通过 neutral/Result/wire 重建。

## body 几何与规则事实

已支持类型闭包为当前 `body_context_profile.types` 的 BODY_N/P 与 BTAP_N/P。
W010 已拒绝闭包外 conductive/body/body_contact role 声明；测试新增合法
registry body/body_contact role 的临时变体，记录真实 W010 拒绝边界，不伪称
到达 W014。W014 补核 W010 尚未执行的 BTAP_N/P 实际 role/连接声明及 profile
types 全闭包：BTAP_N/P 必须是 `role=body_contact`、`purpose=drawing`，
`electrical_connects=(对应BODY_N/P,M1)`、现行正面积唯一的 contact_predicate、
`enclosure_rule=T05.contact_enclosure`，不能把 BTAP_N 改连 BODY_P 后仍执行
固定N链。测试逐字段变体，未知声明返回该 drawn owner 字段的 located
unsupported。未知类型按实际抵达边界拒绝，不能静默忽略后声称 T04/T05
完整覆盖。

使用 Fraction nominal nm，取同源 T04/T05 数值；不 int 截断或用容差补空白。
每 active 按 model body type 寻找同类唯一 enclosing local body；local→external
body 与 external→local M1 必须在 FRAME 左边界有正长度共同边，点接触不成立。
tap 对 body/rail 用正面积接触，按类型和全部对象核唯一性。最后对真实 local M1
的 W013 query evidence 求精确同 bbox 的 toy_m1 证据，取它的 NetId；expected
CDL 与 context.expected_semantic_rail 都只作后置对照。45.05 对 45 是 located
BodyTargetRailMismatch，不能用 W013 component 有关联掩盖这个错误。

| 覆盖 | 遍历范围 | 独立事实 / 判定 |
| --- | --- | --- |
| T04 active enclosure | 全部已准入 device/active | 各四边 margin/min、同类唯一 local body；正常 min20/10nm 对阈值10 |
| T04 opposite overlap | 全部 local 和全部 external N×P body | 每对正面积交集；不可仅查两条声明成功链 |
| T04 body chain | 全部 associations 与 source devices/channel 完整映射 | local body continuation、tap 两侧唯一性、rail continuation、query observed、claim 对照 |
| T05 external | 全部 external BTAP_N/P，含未被 association 指定的 tap | 每侧四边 margin/min、阈值、包围 pass/violation；正常body8/8，rail2/2nm |
| T05 local | W010 全部原 audits | 原对象/状态不改，不以外部通过覆盖本地 violation |
| T08 | source device×D/G/S/B 完整有序集 | source/observed八端有限比较；physical nodes/edges/components 不变 |

几何链成立与规则 enclosure violation 分列。supplied malformed/unsupported owner
按实际边界返回定位错误；reader 已拒绝的缺 context/operator 不伪装到 W014。
本轮不生成 pipeline terminal 或 sealed stage；物理 graph 始终14/8/6，BN/BP
unknown，无额外 union，外部6图形不进入 occupancy/layout/export。

## 资源调用图与验证

```text
reader / caller-read readback → W008 → W009 → W010 captured input (one)
  → W014 public constructor: old W010 encode/decode authentication (one)
  → normalize same semantic input (one)
  → W011 neutral builder + W013 neutral builder (share local/source/derived)
  → body + ordered terminal relations → compact output
Result encode: re-enter public W014 constructor (one old authentication)
  + old W010 encode only → one canonical Value subtree + compact output
Result decode: old W010 decode + public W014 constructor (two authentications)
  + compare all compact output fields; do not call full encode again
```

Neutral draft retains one local context; compact channel observations 不含另一个 local；
Result wire 不再包含 neutral draft 的完整输入。运行时无“已认证”私有标记绕过公开
认证。最早可运行时串行 direct/readback/mismatch 独立进程测 elapsed/peak RSS/
wire bytes/compact增量/认证调用数，对比 W013 同环境 workload，存原命令/输出与
源身份。显著放大先交 PM，不能靠削认证或删测试；开发先新增及受影响范围。

A1–A7测试含跨run/tech/region同值不同来源，完整targets、source-target分离、
unknown/conflict/mismatch，所有body适用对象/7见证及精确反例，完整DTO/codec
alias/native/字段/来源/确定性与异常object/cause/context/suppression。原失败与修正
保留。最终冻结源码/测试/config后双Python3.10/3.12全量、typing、build、双clean
安装源码外direct/readback/mismatch；未参与实现者独立code review及修正复核。
使用单一source/evidence manifest与可重建快照，review/PM按身份采信完整矩阵，
只补独立风险探针，不因换角色复制大wire或再跑同矩阵。

A8在 [production-body-scope](production-body-scope.md) 独立提案；现行 reader
body_context 仍必填，D1=A不再问。执行最终使用项目noreply提交推送原分支，核
远端完整SHA，将A1–A9/原失败修复/资源限制交PM；不代写验收/阶段/current-work，
不合main、不删除分支。
