# W011 执行记录（工程结果待补齐）

执行负责人：`/root`；核心实现辅助：`/root/contract_survey`；测试辅助：`/root/geometry_survey`。本稿于 2026-11-09 按产品修正提交 `8917d38d916c914bfa785cb116982f3f299b38de`、含最终回归的冻结提交 `02725e2e90be6b3145be915be699aa64ce998ed7` 核对。它记录已实现内容、已有定向实证及尚待完成的交付检查，**不是 A1–A8 最终通过、独立 review 结论或 PM 验收**。

## 恢复、授权与读取

- 起点 main：`61775e8fde6e9ea247ec08a32067c44c3be48ff8`；原 W011 分支 PM 准备提交：`81e01da1e5a6ce8e7132f3cebf8ee92bc237246f`。启动时分别用 `git ls-remote --heads origin main codex/w011-channel-identity-fin-count` 核实完整 SHA。
- 恢复前 checkout 为 `/workspace/Layauto` 的干净 `work` 分支，无 staged/unstaged/untracked 用户改动。fetch 的受限 refspec 仅写 FETCH_HEAD；核实准备提交后建立原名 `codex/w011-channel-identity-fin-count`，没有修改 main。
- 已读根 AGENTS、README、协作/本地及远端环境规则、current-work、[W011 要求](../W011-channel-identity-fin-count.md)、所引架构原文、实际 physical/derived/drawn/formats/rules owner、W003 合同/手工见证及 W007–W010 生产者/消费者合同；适用路径未发现局部 AGENTS。
- 先形成[执行方案](plan.md)，再由未参与设计的 reviewer 完成[独立方案 review](plan-review.md)。实现采用独立 worktree 分工，由 `/root` 集成；reviewer 未参与实现或正式测试编写。
- 本次执行修改产品、必要回归/typing/README 和 W011 附件；不修改 fixture/oracle/expected、架构、current-work 或 roadmap，不合 main、不自行验收、不删除原任务分支、不启动下一任务。提交身份沿用 `LucianoHoult <LucianoHoult@users.noreply.github.com>`；最终提交/推送身份仍须由交付记录实核。

## 实现与证明边界

入口是 [`build_channel_identity`](../../../layauto_v2/normalization/channel_identity.py)：只接收成功的 W010 `LocalConnectivityResult`，对原对象先检查 closed graph，再完整重建 W010→W009→W008→W007 捕获链。W007 `normalize` 使用该链已有的 `GeometryInput.semantic_input`；调用方不能另传独立语义结果拼接。组件不读文件/repository、不调用 EDA，不读取 spec/oracle/expected，不推进 W006 attempt。

[`ChannelSeed` 等中立 DTO](../../../layauto_v2/domain/channel_identity.py)保存原 QueryKey、DeviceId、xref、每字段来源和 exact seed；[`annotation/channel_identity.py`](../../../layauto_v2/annotation/channel_identity.py)只决定 seed 与已有 channel 的候选、唯一定位及覆盖。完整候选逐 seed 保留，不用名称、排序、最近中心或另一个 seed 替多解 seed 选答案。相同身份多个 seed 保留为多条证据。partial seed 可以唯一定位；coverage 保持精确有理 union，不把唯一定位写成完整区域 annotation。

[`derive/fin_count.py`](../../../layauto_v2/derive/fin_count.py)逐 channel 枚举所有真实 drawn FIN，分别保留 outside、touch、qualified、partial。只有正面积且完整跨越 channel X、完整落入 active Y 的 FIN 才有计数资格；等号允许，边/角接触不计。query bbox、CDL NFIN、面积除法和固定 5/7 都不是计量输入。相同长 FIN 可以对不同 X 范围的 channel 分别产生 crossing；18 根原 FIN、原重数及重复/重叠关系不被改写。

[`ChannelIdentityDraft`](../../../layauto_v2/derive/channel_identity.py)保留全部观察、关联、测量、拓扑引用、source 比较和 issues。正常样本应由几何得到 MN0 的 F01–F05 共 5 根、MP0 的 F07–F13 共 7 根，两 channel 长度 4 nm、逐合格 FIN 宽度 2 nm。Fxx 是独立手工答案/测试中的回链名称，runtime 只使用实际 record identity。原 `extraction_mismatch` 的 ON.y1=64 nm 与 F05.y0=64 nm 仅触边，实际 MN0 为 4、source CDL 仍为 5；该有限比较必须保留 mismatch。

身份不足和几何不足分别表达。**seed 缺失/歧义时，channel 几何 count 仍可独立算得；没有成立的 DeviceId 关联，就不对该 channel 生成无依据的 source 参数比较。** 具体样本：仅将 MN0 seed 改为 `[58,70,62,80]` nm，它与 N channel 只有边界接触、正面积候选为零；原 channel 的几何 count 仍为 5，但没有 MN0 关联，也不对该 channel 作 source 比较，结果保留 located issue。这澄清方案把定位问题与几何问题合写为“受影响 count=None”的表述，不改变任务要求；独立 reviewer 已对照任务核对这一解释。partial FIN 或涉及正面积 channel 候选的重复/重叠 FIN 使对应几何 count 为 `None`；仍保留 channel L 和每个正面积 FIN 的实际 W，存在有效 device 关联时保留全部可判 L/W 比较。零 crossing 时 W 没有实测，`coverage.unmeasured_width_channels` 明确列出，不能由空比较集合推断 W 已验证一致。

source `fins_per_finger`、`channel_length` 和逐 FIN `fin_width` 比较与 target intent 分离，长度/宽度用 Fraction 精确换为 metres 与 CDL canonical axes 比较；`differences` 保存全部 mismatch。NF/M=1 只是既有准入要求，不是本轮几何测出的 multiplicity。source mismatch 可以是 `status=success` 且 `comparison_status=mismatch`；这表示计量完成并发现不等，不代表一致或整轮成功。target 与全部 target differences 保留在独立 semantic result，target 尚未达到不变成 source extraction 错误。

G/S/D 只引用同一 W009/W010 的 region/node/component；多个相同 POLY records 的 G nodes 均保留，正常两个 channel 共享 G node。有序 S/D 沿用 W009，不造边、不跨 channel union S/D、不合并 body 域，不删除或消除原 T05 violation。body evidence/readback/完整 source/query 捕获保留；完整 net/body/model/VT 匹配、T02/全部 mandatory rules、工艺坐标、生产 U06、baseline/no_change/Stage 6 均未交付。

## A1–A8 对应实现、正式回归与已知证据

下表的测试名称对应已经入库的测试代码；**测试存在不等于最终版本已跑过**。完整矩阵结果须由后文工程表补齐。正式测试分为 [geometry](../../../tests/contracts/test_w011_geometry.py)、[contracts](../../../tests/contracts/test_w011_contracts.py)、[exceptions](../../../tests/contracts/test_w011_exceptions.py)，临时输入修改使用 [w011_cases](../../../tests/contracts/w011_cases.py) 复制并重绑真实捕获，不覆盖固定 fixture。

| 要求 | 已实现及正式测试入口 | 当前已有实际证据与限制 |
| --- | --- | --- |
| A1 同源纯组合 | normalization 完整认证已有 W010 输入、同源运行 W007，保留 completed 和 unsealed attempt。`test_actual_direct_composition_is_pure_and_retains_original_inputs`、`test_actual_w006_readback_preserves_unsealed_attempt_and_direct_result`；跨源/owner 负例为 `test_public_results_reject_cross_capture_semantic_or_graph_substitution`、`test_complete_input_chain_rejects_grouped_payload_forgery`、`test_derived_source_role_is_bound_to_actual_capture`。 | 独立来源 probe 在 `f493233` 上实际通过 normal direct、caller-read readback、禁文件/repository IO 下构造与完整 readback codec、attempt 不变；原 probe 后续 target harness 出错，不能把整次退出 1 写成全通过。原脚本/限制见 [source-probe-initial-receipt.json](review/source-probe-initial-receipt.json)。最终版本双路径结果 pending。 |
| A2 正常完整结果 | 全部 18 FIN 对每 channel 判定，5/7 crossing 集合、L/W、四个有序 S/D、共享 G 和全部来源回链。`test_normal_result_matches_all_independent_crossings_and_retains_18_fin`、`test_all_topology_refs_reach_actual_ordered_regions_and_shared_gate`。 | 早期实际正常 smoke 和独立 probe 得到 5/7；`c37eecf` 的 [source-completed-fixed.stdout.txt](review/source-completed-fixed.stdout.txt) 保留正常 5/7 控制及随后拒绝伪造 completed 的结果。最终完整集合回归 pending，不能以两个数替代集合验证。 |
| A3 几何边界 | exact crossing、X/Y 归属、大整数、完整/partial/零面积、等号、长 FIN 跨 channel、重复关系及重排。`test_exact_fin_geometry_against_independent_open_atom_witnesses`、`test_same_long_fin_crosses_channels_at_two_distinct_x_ranges`、`test_unproven_duplicate_or_overlapping_fin_never_claims_valid_count`、`test_duplicate_fin_outside_channels_is_retained_without_poisoning_counts`、`test_record_reordering_changes_provenance_but_not_crossing_semantics`。 | 独立几何 probe 在冻结 `975852d` 上用整数 open-cell/边界见证验证 250 个随机 FIN × 2 个真实 channel 共 500 项判定；另有实际几何变体组合，范围和原失败见 [geometry-review.md](review/geometry-review.md)。不把中立算法探针冒充每个变体均完整通过 captured result；最终正式回归 pending。 |
| A4 定位/覆盖 | 全 seed/device/channel 核对，partial/有理覆盖、多份同身份 seed exact union、未消费 net seeds 保留；无 fallback。`test_unique_partial_and_multiple_same_identity_seeds_keep_exact_coverage`、`test_all_seeds_devices_and_channels_participate_without_fallback`。 | 冻结 `975852d` 的实际 raw→W007 seed→中立 locator 验证 5/8 partial、重叠 union=1、多解/触边/同身份冲突/缺 seed；300 个 Fraction union 独立见证通过，见 [geometry-fixed-probe.log](review/geometry-fixed-probe.log)。执行补修分支六条实际完整定位负例曾通过；该临时诊断不替代最终归档矩阵。CR-05 的具体 JSON pointer 残留另外修复并独立解析回 D0/D1，见 [geometry-pointer-fixed.log](review/geometry-pointer-fixed.log) 及 reviewer 的最终 commit 映射。 |
| A5 source 比较/target 分离 | 保存所有可判 count/L/W 与声明值、来源及 mismatch，unknown count 不抹掉 L/W。`test_existing_extraction_mismatch_is_actual_four_against_source_five`、`test_source_l_and_w_mismatches_are_all_retained_and_target_is_separate`、`test_target_only_multiple_axes_do_not_change_source_geometry`、`test_partial_crossing_preserves_unknown_count_and_all_decidable_l_w`、`test_zero_crossing_does_not_claim_width_was_verified`、`test_actual_geometry_length_and_width_are_not_backfilled_from_profile_or_cdl`。 | 独立几何专项已有正常 L/W 实测、原 mismatch 和几何边界变体实证，范围见 [geometry-review.md](review/geometry-review.md)。正式 target witness 使用现有支持的 NFIN/L/W 变更，未为了 `alternate` VT 放宽 literal grammar；原 reviewer harness 失败保留。最终新增回归及全部差异结果 pending。 |
| A6 closed/immutable 与异常链 | 所有新集合取一次 snapshot；中立成员及完整 supplied draft 重建，typed canonical 完整 DTO/semantic/completed/issues 对比，拒绝 Python bool/int/Fraction 等值伪造；wire schema/字段闭合。`test_all_public_records_roundtrip_are_frozen_and_rebuild_stably`、`test_public_draft_reconstructs_complete_correlated_tables`、`test_native_collection_snapshots_detach_all_caller_aliases`、`test_foreign_mutable_aliases_rejected_before_codec_can_copy_them`、`test_wire_is_closed_versioned_and_requires_every_field`，以及 CR01/CR04 回归。异常覆盖 `test_new_boundaries_keep_exception_identity_cause_context_and_suppression`、`test_actual_nested_w010_w009_w008_w007_wire_preserves_history`、`test_expected_error_then_second_authentication_fault_keeps_preexisting_history`、`test_cr02_nested_parameter_constructor_keeps_original_exception_history`、`test_cr03_actual_w007_expected_failure_then_completion_fault_keeps_history`；malformed controls 另列测试。 | 原 CR-01–04 findings 和各阶段残留均保留在 [code-review.md](code-review.md)。已有冻结候选的叶子拒绝、正常 roundtrip、六类异常原对象/链、16 种 W007 exemplar 与 384 个 malformed 对照、实际 admission/identity completion 两路线及 completed bool 伪造复核。`8917d38` 进一步以完整 draft constructor+wire 修补摘要投影缺口；该候选完整 Result 的 NF 来源 999、等值 Fraction 行号和 completed bool 伪造已被独立实测拒绝；CR-01–06 代码必须项均闭合，最终全矩阵仍 pending。 |
| A7 scope 与 owner | 继承原 local graph/audits/body scope，验证实际消费 physical/derived/drawn 语义，额外 `role=fin` 不默忽略，未消费 T02 数值完整保留。`test_original_t05_violation_and_body_scope_remain_visible`、`test_consumed_operator_changes_fail_at_located_component_boundary`、`test_additional_fin_role_declaration_is_not_silently_ignored`、`test_unconsumed_t02_profile_numbers_are_retained_without_claiming_rule_execution`、`test_w007_unsupported_admission_is_retained_without_false_channel_success`。 | 原 T05/body 保留和几何范围已有专项检查；CR-06 对同位置 seed registry operand 与 derived owner 的矛盾在 `8917d38` 中增加完整声明及来源位置核对。其独立原 probe 保留在 [boundary-owner-receipt.json](review/boundary-owner-receipt.json)，修后同一矛盾实证已独立拒绝、合法控制通过；最终正式回归 pending。 |
| A8 工程与交付 | 新路径纳入 strict typing；`test_new_modules_have_named_dependency_and_io_guards` 防 runtime 引入 legacy/tests/IO 或逆向 owner 依赖。原1465保留、新增必要回归、双完整解释器、构建和双干净安装源码外 direct/readback 仍是本次必需交付项。 | 本稿不汇总尚未完成的矩阵、包、安装或最终 SHA 为通过。详见下方 pending 清单；独立方案 review 通过不替代代码复核或工程结果。 |

正式测试预检的原失败、修正前候选和中断记录见 [test-preflight/manifest.json](test-preflight/manifest.json)：早期合同 36 项、review 定向 20 项及 CR04 定向 3 项分别通过；setup 失败与 SIGTERM/SIGINT 中断均保留原输出和完整源码/fixture 快照，不计为通过。最后三项 provenance/定位/owner 回归由最终双完整矩阵覆盖。

## 独立 findings 的执行处理

原 [CR-01–CR-06](code-review.md) 及复现材料完整保留；以下只记录执行修正，不替 reviewer 宣布关闭：

- CR-01：中立 seed 补齐 opaque text tuple、每字段 derivation/sources、具体 location/lexeme 和 identity/geometry operands 的自洽验证。公开构造与 codec 不再接受三个原 malformed 样本。
- CR-02：W011 新嵌套 semantic leaf/result 路线必须保留意外 constructor 异常；删除 W007 codec 的宽泛异常转换，malformed 字段仍由明确的 constructor/位置验证拒绝。
- CR-03：W007 expected admission/identity 异常退出 handler 后，才构造 progress facts 和 error result；业务 issue/progress 不变，二次意外异常的既有 context/cause/suppression 不再被处理中的预期异常覆盖。
- CR-04：新 aggregate 重新验证嵌套成员，completed/issues 使用 exact canonical 比较；顶层对 supplied draft 再进完整公开 constructor，并比较完整 wire，不能仅比较摘要或 Python 数值等值。未计量 NF/M 的独立字段来源也在完整验证范围内。
- CR-05：seed 诊断从实际 derivation 的 `sources[0]` 取 SourceRef；随后保留原 record JSON pointer，在 message 中写具体 seed ID 和分析算子，不把 pointer 改成不存在的分析字段。原 wrapper 异常和后发现的 pointer 残留分别保留。
- CR-06：中立 aggregate 交叉核对 seed 保存的 registry operand 与传入 derived owner 的完整声明、URI/SHA 和 registry pointer；同一来源位置不能同时声明 POLY 与 METAL。

三处上游窄修是新 W011 公共组合实际可达路径的必要修正：`normalization/codec.py` 保留 semantic constructor 的意外异常，`normalization/component.py` 保留 expected error 后 completion 异常历史，`domain/source_location.py` 对非 map、缺 SHA、非法 UTF-8 显式给 ValueError，使移除宽 catch 后 malformed 控制仍诚实拒绝。它们未改变 W007 wire schema、参数轴、准入结果、fixture 或输入格式，不是顺带重构上游合同。相关既有 W007 合同/输入定向测试已实际得到 148 passed，见已归档的[命令/退出/耗时](preflight/upstream-fix-01/result.json)、[原输出](preflight/upstream-fix-01/stdout.txt)、[源码清单](preflight/upstream-fix-01/source-manifest.json)及[原位到归档的字节核对](preflight/upstream-fix-01-archive.json)。该定向结果不替代最终双完整矩阵。

## 交 PM 的物理解释扩展样本

现有 `distinct qualified FIN rectangles` 没有独立证明两个重合/重叠 records 对应几根物理 FIN。当前只保留事实并按无法证明落入子集返回 unsupported，不制定去重或相加规则。

| 相对正常样本的临时变体（nm） | 当前应保留的可判事实 | 若未来要求有效 count，必须补什么 |
| --- | --- | --- |
| 再增加一条与 F01 `[10,24,110,26]` 完全重合的独立 FIN record | 两个 GDS record/source、duplicate 关系、N channel 的正面积判断和实际宽度都保留；N count=None，P 的独立几何计量仍可为7。 | 独立工艺/提取证据明确这表示同一 FIN 的重复表示、两根独立 FIN，还是非法输入；不能只按 record 数或 bbox 去重选答案。 |
| 增加 `[10,25,110,27]`，与 F01 部分重叠 | 两条 FIN、交集、overlap 关系及受影响 channel 均保留；N count=None，已知 L/W 及 source 差异继续保留。 | 明确重叠是否允许、是否合并、是否无效，以及独立物理 FIN 的判据；现有示例无法证明。 |
| 将重复 FIN 放在所有 channel 外 | 重复关系及原 records 仍保留；不会抹掉其它 channel 已证明的计量。 | 不据此宣称 T02 width/pitch/phase 或整个图形集合通过；该规则义务仍后置。 |

这些是交 PM 的未来能力扩展反例，不是需要用户确认才能完成当前 conservative unsupported 的门槛。测试只验证现有“证据保留/不能默计”的边界，未修改 fixture、oracle 或答案以冻结新的物理计数语义。

## 最终工程、资源与 Git 交接（pending）

最终交付必须以同一可重建源码/测试/配置身份绑定真实命令输出；当前工程任务仍在执行。以下字段只能在实测后补录，不从正在运行、旧候选通过、文件存在或测试数量推断成功。

| 必需证据 | 本稿状态 | 完成时记录 |
| --- | --- | --- |
| 最终源码/测试/配置身份 | pending | 完整 Git SHA、tree/manifest、完整相关快照或可重建补丁；注明 staged/unstaged/untracked 边界。 |
| 原1465与新增回归、双解释器完整矩阵 | pending | 两个解释器的版本/路径、完整 node IDs 与原1465包含关系、argv/cwd/env/elapsed/exit/stdout/stderr、外层执行时间边界及其精度、失败及修后影响重核。 |
| 双 strict typing | pending | 实际 checker/解释器版本、命令、覆盖路径及原结果。 |
| wheel/sdist 构建 | pending | 构建命令、环境、产物哈希与完整源码身份对应关系。 |
| 双 fresh 安装及源码外 smoke | pending | 安装前后环境、实际 wheel/安装文件哈希、pip check；源码外 `-I -B` 实际 direct/readback 组合与未发布 attempt 事实。 |
| 完整结果资源 | pending | direct/readback 的 build、constructor/decode/encode、完整 wire 大小、来源保留链及 RSS；采样规模、共享负载和未测上限。 |
| 必须 findings 最终独立复核 | pending | reviewer 自行追加最终被审身份、原 finding 处置依据和剩余必须项，不用执行说明代写结论。 |
| 原 W011 分支推送与远端确认 | pending | 使用既有 noreply 身份提交/推送后，再 `git ls-remote` 核完整远端 SHA；交 PM，不自行验收或合 main。 |

资源算法为有限 seed×channel、FIN×channel 和 FIN² 关系扫描，加上 rational union 与完整捕获重建。公开结果同时保留 W010 receipt 和 W007 semantic result，后者也含捕获；完整 wire/重建成本不能用中立 draft 的体积或局部函数耗时替代。已有独立 completed probe 的约 1.4 GiB peak RSS 只属于其记录的候选、命令和共享主机情形，不是最终容量保证；最大输入、生产规模、并发性能未由这些样本证明。未扩展输入资源承诺，也未为降低成本改写上游 wire。
