# W011 执行方案

执行设计：`/root`，调查辅助 `/root/contract_survey`、`/root/geometry_survey`。2026-11-09。
起点 main `61775e8fde6e9ea247ec08a32067c44c3be48ff8`，准备分支/HEAD `codex/w011-channel-identity-fin-count@81e01da1e5a6ce8e7132f3cebf8ee92bc237246f`；两者均由 `git ls-remote --heads` 实核。恢复前 work 分支干净，无需保护的用户改动；fetch 的受限 refspec 只生成 FETCH_HEAD，核对后由该提交建原名分支。适用根 AGENTS，无局部 AGENTS。

## 所有权与入口

- `domain/channel_identity.py`：closed/versioned 中立值类型、typed refs、exact rational rectangle、seed evidence、每 seed 候选/交集、关联、每 FIN 判定、重复关系、measurement、有限参数 comparison。无 IO、normalization 或 state 依赖。
- `annotation/channel_identity.py`：从中立 DeviceId/QueryKey/seed record 与只读 W009 channel 求精确候选、coverage 和一对一定位；不引入 net label，不改变拓扑。
- `derive/fin_count.py`：只读逐 channel/FIN 的 exact 几何判定、重复关系、长度和逐根宽度；不修改 DeviceIR 或 raw FIN。
- `derive/channel_identity.py`：中立 `ChannelIdentityDraft` 聚合、owner 检查、关联到局部 node/component refs、source 参数比较及完整重建。输入包含同一中立 LocalConnectivityDraft、source circuit、投影 seeds 和 derived owner。它验证自洽，捕获认证归 normalization。
- `normalization/channel_identity.py`：`build_channel_identity(local: LocalConnectivityResult) -> ChannelIdentityResult`。先 closed graph 检查并经 W010 codec 全量重建捕获回执，取同一 GeometryInput.semantic_input 运行 W007 normalize；不接收调用方可拼接的独立 W007 result。不读文件/repository，不改变 W006 attempt。
- `normalization/channel_identity_codec.py`：closed canonical tagged wire，显式 registry，nested W010/W007 codec；constructor 与 decode 都重建全部关系与测量。schema `/1`，不重构上游 wire。

继承完整 W010 input/value、W009/W008 raw、source/target/differences/query、body scope/外部证据、readback。新 binding/ref 包含 local graph ref、source语义/证据、所有 seed/xref、physical/derived/drawn/formats/rules 的已认证 owner/单位/profile/scope。消费的 physical/derived 字段精确核验；未消费声明完整保留。规则只继承 W010 已执行 T05，不调用 T02。FIN role/purpose/identity operator 明确检查，不因 capability=true 自动接受。

## 定位证明与覆盖

每个 W007 device seed 投影为 domain 中立 seed evidence，保留 DeviceId、QueryKey、record、对应 identity/xref provenance。registry 必须唯一解析且声明 POLY/device_id/exact/rectangle/零 tolerance/recognized_channel_intersection/reject_ambiguous；不按 toy_ngate/pgate 名字推断模型。直接在 nominal nm 的 Fraction 上与所有 channel 作正面积交集。geometry channel ticks 精确乘 canonical_tick_nm；不能将有理 seed 取整或 snap。每 seed 的全候选和交集、原始 seed ref 都保存。

先逐 seed 判唯一性，再按 DeviceId 聚合：每个 seed 都必须恰好命中一个 channel；同一身份的所有 seed 必须指向同一 channel；一个 channel 必须恰好由一个 source device 解释，所有 source devices 与 recognized channels 都参与检查。不能利用别的 seed 或排序替多解 seed 选候选。没有 seed、零候选、多候选、同身份冲突、多个身份同 channel、多余 channel 均有 located issue，保留可算事实。相同 identity 的多个 seed 只是多条定位证据。

| 具体输入（nm） | 候选/关联 | coverage |
| --- | --- | --- |
| N seed `[58,20,62,70]` | 仅 N channel，MN0 唯一定位 | full，面积比 1 |
| N seed `[58,20,62,40]` | 仅 N channel，MN0 唯一定位 | partial，2/5；不称完整区域 annotation |
| N seed `[58,20,62,180]` | 同时 N/P，unsupported/ambiguity | 两个精确交集均保留，不以其它 seed 排除 P |
| MN0 两 seed `[58,20,62,45]`、`[58,45,62,70]` | 两证据指同 channel，仍一器件 | 分别 1/2；联合 coverage 1，保留各来源 |
| N seed `[58,70,62,80]` | 零正面积候选，missing location | 零；边界接触不匹配 |
| 有理 partial `[58,20,60.5,70]` | 仅 N channel | 5/8，精确有理交集 |

coverage 采用 exact union 的 rational rectangle 分片及面积，不把重叠 seed 面积重复相加。唯一定位关联不是全区域 annotation；本轮没有通用 annotation state。

## FIN 判定及未决物理解释

对每个 recognized channel 枚举所有原始 FIN records，保留每对判定和 geometry refs。先检查 FIN 与 channel 的正面积；无正面积分为 outside/touch（均不计）。正面积时要求 FIN.x0 <= channel.x0 且 FIN.x1 >= channel.x1，并且 active.y0 <= FIN.y0 且 FIN.y1 <= active.y1。等号允许；不满足为 partial/unsupported，不能取整。无需 FIN 在 active 的整个 X 内，要求的是 channel X 跨越。相同长 FIN 可在分离的 channel X 范围各自产生 crossing。

正常 N 的实际 crossing F01–F05，P 的 F07–F13；18 drawn records、12 crossings。extraction_mismatch 的 ON.y1=64，F05.y0=64 仅触边，MN0 实算 4。

对 FIN record 对保存 `duplicate`（相同 rectangle）或 `overlap`（正面积交集）关系、两个来源及受影响 channel。只要关系涉及 channel 中的正面积 FIN 候选，缺少独立物理 FIN 证明，受影响 channel count 为 unknown，返回 typed unsupported；不默默双计或 bbox 去重。完全不触及任一 channel 的重复关系仍保留，但不禁止其它 channel 的已证明计量。边界相接且无面积重叠不是此拒绝条件，T02 全宽/pitch/phase 仍另有义务。这个保守处理落实现有“不证明在子集则 unsupported”，不为重复输入制定新的物理计数答案。

交 PM 的具体未决扩展样本：再加一个与 F01 `[10,24,110,26]` 完全重合 FIN，或加 `[10,25,110,27]` 与其部分重叠；记录两个 GDS 来源，N count unknown，P 可保留 7。需要未来独立工艺/提取证据才能决定前例代表一根还是两根、后例的合并/无效语义；本轮不改 fixture/oracle 或冻结答案。

## 有限计量、拓扑与结果

每 channel 保存 length_nm、全部 FIN 判定、qualified crossing 的实际 width_nm；无 partial/独立性问题才有几何 count。关联有效时与 source selected cell device 的 canonical `fins_per_finger`、`channel_length`、每 crossing 的 `fin_width`逐项比较。长度宽度 nm 精确换成 metres 与 Parameter.exact 比；每个 comparison 保留 measured/declared、axis、CDL field source、channel/FIN refs、equal/mismatch。全量 differences 是所有 mismatch，不遇第一个即停止。没有有效关联时不凭顺序找 source 参数。NF/M=1 是 W007/profile 准入，不伪装几何实测。

成功计量可以携带 source mismatch，`comparison_status=mismatch`；不使用 full extraction equality 名称。target 及其所有差异仍在独立 semantic result，target-only NFIN/L/VT/结构变化不影响 source 几何比较。

S/D 通过该 channel owner 的 W009 有序 regions 找 W010 node，再找 component；G 通过全部 POLY contributors 找对应 nodes/components。保留多个相同 stripe POLY record 的各 node refs，正常两个 channel 共享同 G node。不按 DeviceId/net 名造边，不 union S/D 或 body，不改 audits；via_enclosure 的既有 violation 必须原样保留。

`ChannelIdentityDraft` 是只读分析草稿，保存完整观察/关联/测量及 located issues。公开构造时重算并逐项验证完整表，拒绝遗漏或添加、错误值/来源、假一致、错误拓扑、嵌套可变值。所有 collection 先取一次 snapshot，再验证保存的 tuple，不先迭代验证后再次拷贝。

`ChannelIdentityResult` 始终保留原 input、同捕获 W007 semantic result、completed。无问题为 success；FIN/source 参数不等仍可 success+明确 mismatch。定位/partial/重复问题为 error，同时 value 保留已计算 draft（受影响 count 为 None，绝不冒报有效计数）。不支持的 owner 或 W007 admission/identity 错误可在建 draft 前失败，此时 value=None，并保留 semantic/completed/located issues。error 与成功均须在公开构造重现；无已知问题时禁止人为造 error。

仅捕获具名预期 ChannelProblem/已返回的 W007 issues；不宽泛 catch ValueError/Exception。处理 expected 后退出 except 再构造 result，保证重认证中的意外异常既有 cause/context/suppression 不被污染；在 builder、constructor、codec 和实际 W010→W009→W008→W007 nested chain 注入验证，包括 KeyboardInterrupt/SystemExit。

## Legacy 调查

旧 `legacy_mvp/io_adapters/parser.py` 从便利 JSON/fin_y_positions 写 Device.fin_track_indices，solver 从 stored tracks 截取 resize，违背本轮 geometry/owner 合同，调查后不迁入。复用 v2 Rect 的正面积交集、Fraction/canonical codec 和已有完整捕获认证；不引入归档或 fixture helper runtime 依赖。

## 验证、资源与交付

1. 独立 reviewer 先审本方案与 A1–A8；修复必须项后实现。不同实现范围使用独立 worktree，由 /root 集成；不并写共享接口/任务/current-work。
2. 新测试覆盖实际 direct/readback/禁IO、正常完整集合、原 mismatch/via_enclosure、source L/W 多差异、target-only、部分/有理/多seed/冲突/缺失/多余channel、X/Y及长FIN、partial/等号/边角、重复/重叠、record重排和大整数，所有临时变体在复制输入重绑。
3. 公共 constructor/codec/digest/alias、篡改来源/owner、全部 nested 异常链及 expected后二次认证路径；具名 dependency guards覆盖新 domain/annotation/derive/normalization，禁止 legacy/tests runtime 依赖。
4. 原1465 node IDs全部保留，双 Python3.10/3.12全量、双 strict typing、新 wheel/sdist、两套fresh安装/pip check、源码外 `-I -B` direct/readback组合。最终源码/tests/config清单与完整快照、包/安装文件hash、argv/cwd/env/UTC/exit/原输出随 W011 evidence 保存；历史失败不覆盖。
5. 有限扫描复杂度 seed×channel、FIN×channel、FIN² 的重叠关系及 seed union；先实现可核验精确扫描，不顺带重构上游认证。记录 normal/variant build+wire、嵌套来源复制成本、RSS与规模；有限样本不作最大输入/生产性能保证，未测上限明示。
6. 独立代码 reviewer 不参与设计/实现；review后修改按影响复核，保留原 findings。最后使用项目既有 `LucianoHoult <LucianoHoult@users.noreply.github.com>` 提交推送原分支并核远端完整 SHA，只交 PM。

完整 net/body/model/VT、T02/全部规则、工艺坐标、生产U06、mutable state/baseline/no_change/Stage6均后置。current-work/roadmap/fixture/答案/架构合同不在本次执行修改范围。
