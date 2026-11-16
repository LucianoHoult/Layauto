# W014 外部 body 调查与实现建议

执行调查，基于 `8f3f39562ed04d790c8d6c015f7c9b8742b6a3c4`；这是方案输入，
不代替独立方案 review，也不是 PM 验收。适用规则只有根 `AGENTS.md`。

## 输入及所有权

- 只消费 W011/W013 共同的真实 `LocalConnectivityResult` 捕获链、W011 的
  device/channel/active 关联及 source circuit、W013 的 net evidence/区域和分量结果。
- `body_evidence` 是 reader 保存的 `EvidenceRecord('body', ..., (body_source,
  gds_source))`；原始 bytes 位于共同 `NormalizationInput.parse.sources`。
  physical/rules owner 分别由同一 tech 记录的已声明来源提供，不能另读文件。
- reader `_body` 已认证 source GDS bytes/top/profile/operator/unit、synthetic
  状态、身份唯一、内部引用和 layer role；尚未认证 `local_bindings` 的 bbox 与
  真 GDS 对象相同，也未执行 body 几何。新入口必须补闭合这些事实。
- 真 `DrawnRecord` 没有 `BN`/`MN` 等作者名字。context 中名字是文档内部 id；
  以 **layer + 精确物理 nm bbox** 在已认证 layout 中唯一匹配，保留实际
  `GeometryRecordId`、source、unit/policy ref。零匹配和多匹配均定位拒绝，不能按
  名字、流顺序或某份 spec 匹配。每个已提供 local binding 都核，不只核两条路径。
- FRAME 指向唯一实际 BOUNDARY，bbox、top、单位和 identity transform 闭合。
  所有 external shapes 保持 x_max <= FRAME.x_min；不加入本地 occupancy/graph。

## 最小纯计算步骤

1. 核 `toy_device_terminal_context/2` 的 ordered D/G/S/B、one_to_one、禁止
   reduction/swap，以及 `body_context/2` 和已消费 profile 文本/字段。校验所有
   用到的 T04/T05/T08 规则 id、scope、predicate、evaluator、relation/assurance、
   unit 和参数，未知语义 typed unsupported；阈值读取同源 rules，不硬编码 10/1。
2. 将 context 的全部 local binding 精确连接到真实记录。source selected-cell
   devices 和 body associations 必须集合相同且一一对应；多、缺、重复不可忽略。
3. 对每个 device 的真实 active，以 `body_context_profile.types[model]` 寻找
   同类、完整包含 active 的唯一 local body，核它是指定 local_body。记录四边
   enclosure，T04 用最小值和同源 `active_enclosure_nm` 比较。几何包围事实与
   阈值判定分开：不足时仍保留已存在的路径和数值。
4. 对全部本地相反类型 body 对和全部外部相反类型 body 对审计正面积 overlap；
   不能只检查选中的 body。点/边接触无正面积，不能误报 overlap。
5. 每条声明路径核 local/external body layer 相同且符合 device 类型，tap 类型
   符合模型，local/external rail 为 M1。枚举所有候选：local body 与同类
   external body 的 FRAME 左边界正长度接续只能有一个；external rail 与本地
   M1 的正长度接续只能有一个，且必须等于指定 id。不能用一条满足的候选遮盖
   第二条匹配。保存候选全集、接续长度和实际记录 refs。
6. **全体** external BTAP_N/P 独立做 T05 审计，而非只遍历 associations 的 tap：
   tap 必须正面积接触唯一同类 external body 与唯一 external M1；分别计算
   四边 margin，并与 `T05.contact_enclosure.parameters.enclosure_nm` 比较。
   未引用但坏掉的额外 tap 也必须产生定位 issue。指定路径消费对应审计，保留
   W010 已有本地 T05，不能用外部成功覆盖本地失败。
7. 最后才连接 net：实际 local rail 的精确 nm 矩形须有映射到 M1 的**完整精确
   rail query evidence**；保留 query key、NetId、记录及字段来源。不能仅取
   component consensus，因为 45.05nm query 仍可能完整覆盖 45nm rail。
   多个不同 net 是 conflict；缺真实注记是 unknown；已提供但不精确的 rail
   证据单列 `BodyTargetRailMismatch`/exact-evidence issue，不当作普通缺资料。
8. observed net 来自上述 evidence，分别比较 source B 与
   `association.expected_semantic_rail` 两个主张。wrong_rail 原见证只改后一主张，
   故应保留 observed=VSS、source=VSS，并定位 context claim mismatch；不能把
   expected_semantic_rail 当 observed。整体 T08 不把 claim mismatch 伪装通过。

精确算法用 `Fraction` nm（本地 canonical DBU 经 `UnitBinding.canonical_to_nm`），
external schema 的 integer nm 先变成 Fraction。正面积接触用两轴严格 `>`；
共享边长度用接触坐标精确相等及区间交集严格 `>0`；corner 长度为零。
四边 enclosure 为 `(inner.x0-outer.x0, inner.y0-outer.y0,
outer.x1-inner.x1, outer.y1-inner.y1)`，不得截断或 float 比较。

## 建议保留的 body 行

一行属于 `(DeviceId, B)` target；包含 active/association/channel ref、实际
local body record/node/component refs、context source 与 association JSON pointer、
四个 external/context 内部 id 及源 JSON pointers、实际 local rail record/node/
component refs、完整各阶段候选集、body/rail edge lengths、active 和 tap 两侧
四边 margins、T04/T05 rule refs/threshold/status、exact query evidence refs、
source NetId、context claim 文本、observed net set、三项分别比较的状态，以及
`association_scope=read_only_external_context` / `local_graph_union=false`。
来源链可共享顶层 binding，无需复制完整 W011 和 W013 result。

整个 draft 仍保留本地 BN/BP component 的 unknown，正常 14 nodes/8 edges/
6 components 不改变；external 六个图形不成为本地节点。`production_matched_body_evidence=false`
和 `lvs_status=not_run` 保持，不构造 run terminal。

## 正常独立小样张

以下只作为测试独立预期，runtime 不读取 spec/oracle/helper：

| device | 实际链 | body/rail edge nm | active margin min nm | tap body/rail min nm | observed |
| --- | --- | --- | --- | --- | --- |
| MN0 | BN → BN.ext → TN.ext → MN.ext → MN | 90 / 10 | 20 | 8 / 2 | VSS |
| MP0 | BP → BP.ext → TP.ext → MP.ext → MP | 100 / 10 | 10 | 8 / 2 | VDD |

BN `[0,0,120,90]` 包围 ON `[20,20,100,70]` 的四边 margin 为
`[20,20,20,20]`；BP `[0,100,120,200]` 包围 OP `[20,110,100,180]` 为
`[20,10,20,20]`。TN.ext `[-12,50,-8,54]` 在 BN.ext `[-20,0,0,90]`
中四边为 `[8,50,8,36]`，在 MN.ext `[-20,48,0,58]` 中为 `[8,2,8,4]`。
TP.ext 同样最小 8/2。来源：已验收 `body/context.json`、`oracle.json` 的
`body_associations` 及 `tech/rules.json`；独立复核应以真实捕获重算。

## 既有见证与真实到达边界

`failures/cases.json` 中七个新增 body 用例为下面除 C22 外七项。旧 phase 字段
是未来完整 pipeline 目标；当前 W014 纯组件不能伪造 sealed/terminal：

| 用例 | 当前最早边界 | W014 应记录/检验 |
| --- | --- | --- |
| C22 missing_body_operator | reader `validate_tech`：RequiredBodyOperatorUnavailable | 采信真实 reader error，W014 未调用 |
| missing_body_context | reader acquire：RequiredBodyContextUnavailable | 采信 reader error，保留已读 completed/sources |
| body_wrong_binding | reader `_binding`：BodySourceBindingMismatch | 采信 reader error，W014 未调用 |
| body_wrong_type | reader 准入（BODY_N/P 均为 body role） | W014 模型类型核对：BodyTypeMismatch |
| body_disconnected | reader 准入 | W014 精确边长零：BodyContinuationMismatch |
| body_ambiguous | reader 准入 | W014 枚举第二同类接续候选：BodyUniqueMatchFailure |
| body_enclosure | reader 准入 | 仍保存正面积路径，外部 T05 violation：BodyTapEnclosureFailure |
| body_wrong_rail | reader 准入 | observed VSS 不变，context claim VDD 不符：BodyTargetRailMismatch |

REQ-01：临时副本 raw `net_shapes_n_lo.txt` 把 `(1160,900)/(960,900)` 改为
`(1160,901)/(960,901)`，重绑 header/raw hash/normalized cache；GDS/source/body
不变。query x_max 精确为 `901/20=45.05nm`，不等于 local rail `45nm`，
exact rail 证据不能成立。不得 `int()` 或容差配成 45，也不能仅以 W013 分量
known(VSS) 宣称 body 证明通过。新增测试应真实 reader/captures 进入。

还需失败/边界探针：点触 body、点触 rail、仅边触 tap、错误 rail layer role
（reader BodyReferenceTypeMismatch）、错/漏/重复 local binding、同层同 bbox
双真记录、active 包围不足、遗漏/重复 association、全部适用 local/external
相反类型 overlap、额外未引用坏 tap、tap 多 body/多 rail、修改 profile/operator
文本/规则 evaluator/阈值、source B mismatch、unknown/conflict query、外部 source
错 run/top/unit/owner，以及 W011 原 extraction_mismatch 4 对 source 5 保留。

## 依据及未覆盖

已调查架构 §2.3、3.3/3.6、4.5–4.7、5.6–5.9、11.2/11.5/11.9/11.15；
实际生产者 `normalization/{channel_identity,net_annotation,geometry}.py`、
`domain/{geometry,channel_identity,net_annotation}.py`、`state/layout_store.py`；
reader `_body`/`_parse_inputs`、tech schema、physical/rules/body 文档、W004
helper/fixture-support 精度回归和历史 REQ-01。helper 只能作为调查参考，不能
成为 runtime 依赖或唯一测试答案。此调查未运行产品测试、未改 runtime/fixture，
尚不构成 A3–A5 实现或验收证据。
