# W011 执行记录

执行负责人：`/root`；核心实现辅助：`/root/contract_survey`；测试辅助：`/root/geometry_survey`。产品修正提交为 `8917d38d916c914bfa785cb116982f3f299b38de`，首轮回归冻结提交为 `02725e2e90be6b3145be915be699aa64ce998ed7`；两项测试准备/边界修正已集成至 `6ea8b0a`。**最终测试、构建及资源验证源为 `e89bdaa6a091f56cfaf7862dced7232d34e22514`**；双完整 1605 项矩阵、双 strict typing、构建、双干净安装源码外 smoke 和三项完整 Result 资源 probe 均已实测通过，见[工程总回执](verification/receipt.json)及[资源总回执](resources/receipt.json)。源码、测试及配置身份见 [verification/source-manifest.json](verification/source-manifest.json)。文档与证据交付身份由包含本记录的 Git 提交及交接回复确定，与直接运行矩阵的冻结身份分开记录。[最终独立 review](code-review.md)已核对代码及 A8，剩余必须修正项 **0**。本记录不代替 reviewer 原结论或 PM 验收。

## 恢复、授权与读取

- 起点 main：`61775e8fde6e9ea247ec08a32067c44c3be48ff8`；原 W011 分支 PM 准备提交：`81e01da1e5a6ce8e7132f3cebf8ee92bc237246f`。启动时分别用 `git ls-remote --heads origin main codex/w011-channel-identity-fin-count` 核实完整 SHA。
- 恢复前 checkout 为 `/workspace/Layauto` 的干净 `work` 分支，无 staged/unstaged/untracked 用户改动。fetch 的受限 refspec 仅写 FETCH_HEAD；核实准备提交后建立原名 `codex/w011-channel-identity-fin-count`，没有修改 main。
- 已读根 AGENTS、README、协作/本地及远端环境规则、current-work、[W011 要求](../W011-channel-identity-fin-count.md)、所引架构原文、实际 physical/derived/drawn/formats/rules owner、W003 合同/手工见证及 W007–W010 生产者/消费者合同；适用路径未发现局部 AGENTS。
- 先形成[执行方案](plan.md)，再由未参与设计的 reviewer 完成[独立方案 review](plan-review.md)。实现采用独立 worktree 分工，由 `/root` 集成；reviewer 未参与实现或正式测试编写。
- 本次执行修改产品、必要回归/typing/README 和 W011 附件；不修改 fixture/oracle/expected、架构、current-work 或 roadmap，不合 main、不自行验收、不删除原任务分支、不启动下一任务。提交身份沿用 `LucianoHoult <LucianoHoult@users.noreply.github.com>`；最终提交及远端完整 SHA 由 Git 和交接回复中的实核值记录。

## 实现与证明边界

入口是 [`build_channel_identity`](../../../layauto_v2/normalization/channel_identity.py)：只接收成功的 W010 `LocalConnectivityResult`，对原对象先检查 closed graph，再完整重建 W010→W009→W008→W007 捕获链。W007 `normalize` 使用该链已有的 `GeometryInput.semantic_input`；调用方不能另传独立语义结果拼接。组件不读文件/repository、不调用 EDA，不读取 spec/oracle/expected，不推进 W006 attempt。

[`ChannelSeed` 等中立 DTO](../../../layauto_v2/domain/channel_identity.py)保存原 QueryKey、DeviceId、xref、每字段来源和 exact seed；[`annotation/channel_identity.py`](../../../layauto_v2/annotation/channel_identity.py)只决定 seed 与已有 channel 的候选、唯一定位及覆盖。完整候选逐 seed 保留，不用名称、排序、最近中心或另一个 seed 替多解 seed 选答案。相同身份多个 seed 保留为多条证据。partial seed 可以唯一定位；coverage 保持精确有理 union，不把唯一定位写成完整区域 annotation。

[`derive/fin_count.py`](../../../layauto_v2/derive/fin_count.py)逐 channel 枚举所有真实 drawn FIN，分别保留 outside、touch、qualified、partial。只有正面积且完整跨越 channel X、完整落入 active Y 的 FIN 才有计数资格；等号允许，边/角接触不计。query bbox、CDL NFIN、面积除法和固定 5/7 都不是计量输入。相同长 FIN 可以对不同 X 范围的 channel 分别产生 crossing；18 根原 FIN、原重数及重复/重叠关系不被改写。

[`ChannelIdentityDraft`](../../../layauto_v2/derive/channel_identity.py)保留全部观察、关联、测量、拓扑引用、source 比较和 issues。正常样本应由几何得到 MN0 的 F01–F05 共 5 根、MP0 的 F07–F13 共 7 根，两 channel 长度 4 nm、逐合格 FIN 宽度 2 nm。Fxx 是独立手工答案/测试中的回链名称，runtime 只使用实际 record identity。原 `extraction_mismatch` 的 ON.y1=64 nm 与 F05.y0=64 nm 仅触边，实际 MN0 为 4、source CDL 仍为 5；该有限比较必须保留 mismatch。

身份不足和几何不足分别表达。**seed 缺失/歧义时，channel 几何 count 仍可独立算得；没有成立的 DeviceId 关联，就不对该 channel 生成无依据的 source 参数比较。** 具体样本：仅将 MN0 seed 改为 `[58,70,62,80]` nm，它与 N channel 只有边界接触、正面积候选为零；原 channel 的几何 count 仍为 5，但没有 MN0 关联，也不对该 channel 作 source 比较，结果保留 located issue。这澄清方案把定位问题与几何问题合写为“受影响 count=None”的表述，不改变任务要求；独立 reviewer 已对照任务核对这一解释。partial FIN 或涉及正面积 channel 候选的重复/重叠 FIN 使对应几何 count 为 `None`；仍保留 channel L 和每个正面积 FIN 的实际 W，存在有效 device 关联时保留全部可判 L/W 比较。零 crossing 时 W 没有实测，`coverage.unmeasured_width_channels` 明确列出，不能由空比较集合推断 W 已验证一致。

source `fins_per_finger`、`channel_length` 和逐 FIN `fin_width` 比较与 target intent 分离，长度/宽度用 Fraction 精确换为 metres 与 CDL canonical axes 比较；`differences` 保存全部 mismatch。NF/M=1 只是既有准入要求，不是本轮几何测出的 multiplicity。source mismatch 可以是 `status=success` 且 `comparison_status=mismatch`；这表示计量完成并发现不等，不代表一致或整轮成功。target 与全部 target differences 保留在独立 semantic result，target 尚未达到不变成 source extraction 错误。

G/S/D 只引用同一 W009/W010 的 region/node/component；多个相同 POLY records 的 G nodes 均保留，正常两个 channel 共享 G node。有序 S/D 沿用 W009，不造边、不跨 channel union S/D、不合并 body 域，不删除或消除原 T05 violation。body evidence/readback/完整 source/query 捕获保留；完整 net/body/model/VT 匹配、T02/全部 mandatory rules、工艺坐标、生产 U06、baseline/no_change/Stage 6 均未交付。

## A1–A8 对应实现、正式回归与已知证据

下表所列正式回归已在冻结源 `e89bdaa6a091f56cfaf7862dced7232d34e22514` 的 Python 3.10.22 与 3.12.14 完整矩阵中通过；两者均为 **1605 passed、exit 0**，包含原 1465 项和新增 140 项，原 ID 无遗漏。实际命令与输出见 [3.10 回执](verification/pytest-310.json)、[3.10 原输出](verification/pytest-310.stdout.txt)、[3.12 回执](verification/pytest-312.json)、[3.12 原输出](verification/pytest-312.stdout.txt)；[3.10 范围](verification/pytest-scope-310.json)与[3.12 范围](verification/pytest-scope-312.json)保留包含关系。正式测试分为 [geometry](../../../tests/contracts/test_w011_geometry.py)、[contracts](../../../tests/contracts/test_w011_contracts.py)、[exceptions](../../../tests/contracts/test_w011_exceptions.py)，临时输入修改使用 [w011_cases](../../../tests/contracts/w011_cases.py) 复制并重绑真实捕获，不覆盖固定 fixture。下列历史 probe 保留其实际受审身份、失败和范围，不冒充冻结源的完整矩阵。

| 要求 | 已实现及正式测试入口 | 当前已有实际证据与限制 |
| --- | --- | --- |
| A1 同源纯组合 | normalization 完整认证已有 W010 输入、同源运行 W007，保留 completed 和 unsealed attempt。`test_actual_direct_composition_is_pure_and_retains_original_inputs`、`test_actual_w006_readback_preserves_unsealed_attempt_and_direct_result`；跨源/owner 负例为 `test_public_results_reject_cross_capture_semantic_or_graph_substitution`、`test_complete_input_chain_rejects_grouped_payload_forgery`、`test_derived_source_role_is_bound_to_actual_capture`。 | 冻结源的 direct/readback、禁止 IO、原 attempt 保留及跨源拒绝回归在上述双矩阵均通过。历史独立来源 probe 在 `f493233` 上通过相应前段，后续 target harness 出错，整次退出 1 保留为失败记录；原脚本/限制见 [source-probe-initial-receipt.json](review/source-probe-initial-receipt.json)。最终双干净安装的源码外组合另由 A8 验证。 |
| A2 正常完整结果 | 全部 18 FIN 对每 channel 判定，5/7 crossing 集合、L/W、四个有序 S/D、共享 G 和全部来源回链。`test_normal_result_matches_all_independent_crossings_and_retains_18_fin`、`test_all_topology_refs_reach_actual_ordered_regions_and_shared_gate`。 | 冻结源的完整 crossing 集合、18 FIN 保留、L/W 和拓扑回链回归在双矩阵均通过，不仅核对两个 count。历史 `c37eecf` 的 [source-completed-fixed.stdout.txt](review/source-completed-fixed.stdout.txt) 仍保留正常 5/7 控制及随后拒绝伪造 completed 的结果。 |
| A3 几何边界 | exact crossing、X/Y 归属、大整数、完整/partial/零面积、等号、长 FIN 跨 channel、重复关系及重排。`test_exact_fin_geometry_against_independent_open_atom_witnesses`、`test_same_long_fin_crosses_channels_at_two_distinct_x_ranges`、`test_unproven_duplicate_or_overlapping_fin_never_claims_valid_count`、`test_duplicate_fin_outside_channels_is_retained_without_poisoning_counts`、`test_record_reordering_changes_provenance_but_not_crossing_semantics`。 | 冻结源的各项 exact geometry、重复/重叠和重排正式回归在双矩阵均通过。历史独立几何 probe 在 `975852d` 上用整数 open-cell/边界见证验证 250 个随机 FIN × 2 个真实 channel 共 500 项判定；实际几何变体组合、原失败及范围见 [geometry-review.md](review/geometry-review.md)。中立算法探针仍不等于每个变体均完整通过 captured result。 |
| A4 定位/覆盖 | 全 seed/device/channel 核对，partial/有理覆盖、多份同身份 seed exact union、未消费 net seeds 保留；无 fallback。`test_unique_partial_and_multiple_same_identity_seeds_keep_exact_coverage`、`test_all_seeds_devices_and_channels_participate_without_fallback`。 | 冻结源的唯一定位/覆盖分离、全部定位负例及来源回归在双矩阵均通过。历史 `975852d` 的 raw→W007 seed→中立 locator 验证 5/8 partial、重叠 union=1、多解/触边/同身份冲突/缺 seed，另有 300 个 Fraction union 独立见证，见 [geometry-fixed-probe.log](review/geometry-fixed-probe.log)。CR-05 原 wrapper 问题与后发现的 pointer 残留都保留；最终产品 `8917d38` 的独立重跑将具体 pointer 解析回 D0/D1，见 [geometry-pointer-891.log](review/geometry-pointer-891.log)及[受审身份](review/geometry-pointer-commit.json)。 |
| A5 source 比较/target 分离 | 保存所有可判 count/L/W 与声明值、来源及 mismatch，unknown count 不抹掉 L/W。`test_existing_extraction_mismatch_is_actual_four_against_source_five`、`test_source_l_and_w_mismatches_are_all_retained_and_target_is_separate`、`test_target_only_multiple_axes_do_not_change_source_geometry`、`test_partial_crossing_preserves_unknown_count_and_all_decidable_l_w`、`test_zero_crossing_does_not_claim_width_was_verified`、`test_actual_geometry_length_and_width_are_not_backfilled_from_profile_or_cdl`。 | 冻结源的真实 4 对 source 5、全部可判差异、partial 的 L/W 保留、零 crossing 的 W 未测及 target 分离回归在双矩阵均通过。历史独立几何专项实证范围见 [geometry-review.md](review/geometry-review.md)。正式 target witness 使用既有 NFIN/L/W grammar；原 reviewer 的 `alternate` VT harness 失败及首轮正式测试的 target 词序 setup 失败均保留，后者修正与重核详见下文。 |
| A6 closed/immutable 与异常链 | 所有新集合取一次 snapshot；中立成员及完整 supplied draft 重建，typed canonical 完整 DTO/semantic/completed/issues 对比，拒绝 Python bool/int/Fraction 等值伪造；wire schema/字段闭合。`test_all_public_records_roundtrip_are_frozen_and_rebuild_stably`、`test_public_draft_reconstructs_complete_correlated_tables`、`test_native_collection_snapshots_detach_all_caller_aliases`、`test_foreign_mutable_aliases_rejected_before_codec_can_copy_them`、`test_wire_is_closed_versioned_and_requires_every_field`，以及 CR01/CR04 回归。异常覆盖 `test_new_boundaries_keep_exception_identity_cause_context_and_suppression`、`test_actual_nested_w010_w009_w008_w007_wire_preserves_history`、`test_expected_error_then_second_authentication_fault_keeps_preexisting_history`、`test_cr02_nested_parameter_constructor_keeps_original_exception_history`、`test_cr03_actual_w007_expected_failure_then_completion_fault_keeps_history`；malformed controls 另列测试。 | 冻结源的公开 DTO/完整 Result 重建、alias、typed 等值伪造、嵌套异常历史和 malformed controls 回归在双矩阵均通过。原 CR-01–04 findings、各阶段残留、16 种 W007 exemplar/384 个 malformed 对照及六类异常复核均保留在 [code-review.md](code-review.md)。`8917d38` 的完整 Result 对 NF 来源 999、等值 Fraction 行号及 completed bool 伪造另有独立实测拒绝；最终代码及 A8 必须项为 0 的结论出自该独立报告。 |
| A7 scope 与 owner | 继承原 local graph/audits/body scope，验证实际消费 physical/derived/drawn 语义，额外 `role=fin` 不默忽略，未消费 T02 数值完整保留。`test_original_t05_violation_and_body_scope_remain_visible`、`test_consumed_operator_changes_fail_at_located_component_boundary`、`test_additional_fin_role_declaration_is_not_silently_ignored`、`test_unconsumed_t02_profile_numbers_are_retained_without_claiming_rule_execution`、`test_w007_unsupported_admission_is_retained_without_false_channel_success`。 | 冻结源的原 T05/body、owner 定位拒绝、未消费 T02 和 W007 unsupported 回归在双矩阵均通过；schema 禁止值与 W011 语义 unsupported 分别在实际入口核对，首轮误用 success-only helper 的失败保留于下文。CR-06 原矛盾 probe 见 [boundary-owner-receipt.json](review/boundary-owner-receipt.json)；`8917d38` 修后同一矛盾已被独立拒绝、合法控制通过。 |
| A8 工程与交付 | 新路径纳入 strict typing；`test_new_modules_have_named_dependency_and_io_guards` 防 runtime 引入 legacy/tests/IO 或逆向 owner 依赖。原1465保留、新增必要回归、双完整解释器、构建和双干净安装源码外 direct/readback 均为本次必需交付项。 | 双完整矩阵、双 strict typing、工程/安装环境 pip check、wheel/sdist 构建、双 fresh 安装 smoke 和三项完整 Result 资源 probe 均实测通过；命令、身份、输出和限制已归档。最终独立代码及 A8 复核必须项为 0；各项回执与交付身份约定见下表。 |

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

## 首轮完整矩阵及测试补修（原记录保留）

首轮冻结 `02725e2e90be6b3145be915be699aa64ce998ed7` 的 Python 3.10 全量实际为 **2 failed, 1603 passed / 9500.70s**，命令 exit 1；[原输出](verification-attempt-01/pytest-310.stdout.txt)和[实际命令回执](verification-attempt-01/pytest-310.json)均完整保留。这不是通过记录。旧 runner 在该完整回执后被停止，刚启动的 Python 3.12 collect-only 被终止，旧版 3.12 full 未运行；信号、PID、外层时间和原输出见[尝试关闭记录](verification-attempt-01/attempt-closure.json)及[归档证据清单](verification-attempt-01/evidence-manifest.json)。后续通过没有覆盖或撤销本次失败。

两项均为正式回归的准备/边界错误，未修改 runtime、schema、fixture 或原断言中的几何答案：

- target CDL 故意使用反序参数；旧测试以 source 词序替换，失败于 helper 的 `assert before in text`，尚未进入目标变体计算。修正匹配词序后同一单项实际 **1 passed / 136.82s**，独立 read+W007 验证仅 MN0 target 的 NFIN/L/W 三轴改变；原失败与修后证据见 [target-only-repair](test-preflight/target-only-repair/README.md)，独立结论见 [target-order-review](review/target-order-review.md)。
- `effective_fin_operator=foreign` 已被现有 schema 在 reader 入口以 `config/InvalidSchema` 拒绝；旧 helper 却要求先有成功 W010。原参数 ID 保留，改为精确验证该入口的字段位置、坏 owner bytes/SHA、五份捕获和 config completed；其它三个 schema 合法但语义不支持的变体仍完整运行 W011 并检查 located unsupported。修后原四项实际 **4 passed / 182.45s**；证据见 [owner-boundary-repair](test-preflight/owner-boundary-repair/README.md)，独立结论见 [operator-admission-review](review/operator-admission-review.md)。

修后总数仍为 1605，原 1465 ID 不变。新 runner 于 2026-11-09 12:07:35.745096 UTC 从冻结源 `e89bdaa6a091f56cfaf7862dced7232d34e22514` 启动；两份完整矩阵已结束且 exit 0。实际 pytest 进程的起止时刻各见下表，不把 launcher 时刻当作两个子进程的精确起点。新版工程 harness 允许两个旧回归段并行，首个 `test_w011_*` 的 fixture setup 前取得共享 `flock`，raw 非继承 fd 持到进程退出；W011 重型重建互斥，构建、双安装 smoke 和资源 probe 后置串行。脚本仅协调执行，未跳过、重排或改写断言；[独立 gate review](review/resource-gate-review.md)保留 HG-01 原 finding 和修正，剩余 harness 必须项 0。[正式锁事件核对](verification/resource-gate-validation.json)已通过，两个进程使用相同 inode；`RELEASED` 是父进程观察完成的时刻，可能晚于另一进程取得内核锁，不是内核解锁时刻。门控小样仍只证明门控；正式运行的[外层回执](preflight/final-attempt02/final-launch-receipt.json)、[并发/内存采样](preflight/final-attempt02/resource-observations-summary.json)和原始记录均已保存。

## 最终工程、资源与 Git 交接

原 1465 项双基线已完成：Python 3.10.22 为 1465 passed / 5084.47s，Python 3.12.14 为 1465 passed / 3874.19s，均 exit 0；252 个基线文件及双 collection ID 核对一致。完整来源与原命令输出见 [baseline/receipt.json](preflight/baseline/receipt.json)，这不替代最终新增回归矩阵。

本次测试及构建均在 `/workspace/work/w011-final-e89bdaa/source` 的冻结快照执行；[262 文件源码/测试/配置清单](verification/source-manifest.json)和[完整快照](verification/source-snapshot.tar.gz)绑定 `e89bdaa6a091f56cfaf7862dced7232d34e22514`。该清单记录冻结时唯一未跟踪范围为本次 `verification/` 证据目录。[工程总回执](verification/receipt.json)已在全部 21 个命令完成后复核 262 个源码/测试/配置文件和 100 个 runtime 文件；随后三项资源 probe 也逐次核对源未变，并再次核对全部 262 文件。后续执行文档、review 与证据的交付提交将有不同 SHA；提交前已再次核对冻结清单及变更边界；最终提交和远端完整 SHA 由 Git 与交接回复另记，不冒记文档提交已重新运行矩阵。

| 完整矩阵 | 实际结果与时长 | 命令起止 UTC 与原记录 |
| --- | --- | --- |
| Python 3.10.22 | 1605 passed / pytest 12905.97s；命令 12908.836s；exit 0。命令时长包含 gate 等待约 2603.347s，不是纯测试计算耗时。 | 2026-11-09 12:07:37.957123 至 15:42:46.793380；[命令/环境覆盖](verification/pytest-310.json)、[原输出](verification/pytest-310.stdout.txt)、[解释器及依赖](verification/environment-310.stdout.txt)。 |
| Python 3.12.14 | 1605 passed / pytest 7310.82s；命令 7313.363s；exit 0。 | 2026-11-09 12:07:37.853692 至 14:09:31.215976；[命令/环境覆盖](verification/pytest-312.json)、[原输出](verification/pytest-312.stdout.txt)、[解释器及依赖](verification/environment-312.stdout.txt)。 |

两份矩阵均含原 1465 项及新增 140 项，无跳过或遗漏原 ID。解释器分别为 `/workspace/work/w011-engineering/dev310/bin/python` 和 `/workspace/work/w011-engineering/dev312/bin/python`，pytest 9.2.0、mypy 2.4.1；完整依赖版本与命令级环境覆盖以上述原记录为准。UTC 为进程边界观察，elapsed 由单调计时得到；gate 等待值取 WAIT/ACQUIRED 观察间隔，不作为性能基准。工程与资源命令已经结束，原输出按[工程证据清单](verification/evidence-manifest.json)和[资源证据清单](resources/evidence-manifest.json)保存；最终独立交付结论见 reviewer 保存的[代码及 A8 报告](code-review.md)和[实际审计结果](review/final-a8-audit.stdout.json)。

| 必需证据 | 本稿状态 | 已完成记录或待补范围 |
| --- | --- | --- |
| 测试/构建冻结身份及最终交付身份 | 冻结身份已归档；交付身份见 Git 与交接回复 | `e89bdaa6a091f56cfaf7862dced7232d34e22514`、262 文件清单与快照见上文；交付前已核源码/测试/配置未变，只有 W011 文档与证据待纳入交付提交。本记录不自包含自身最终提交哈希。 |
| 原1465与新增回归、双解释器完整矩阵 | 通过 | 两份均 1605 passed、exit 0；命令、输出与环境见上表，完整 collection IDs 见 [3.10](verification/collection-310.stdout.txt)和 [3.12](verification/collection-312.stdout.txt)，原1465包含关系见双 scope 回执。首轮失败及修正后完整重跑分别保留。 |
| 双 strict typing 与工程环境依赖 | 通过 | mypy 2.4.1 使用各自解释器运行 `-m mypy`，均为 54 source files 无问题、exit 0；[3.10 命令](verification/typing-310.json)/[输出](verification/typing-310.stdout.txt)、[3.12 命令](verification/typing-312.json)/[输出](verification/typing-312.stdout.txt)。两个工程环境 `pip check` 亦 exit 0，见 [3.10](verification/pip-check-310.json)、[3.12](verification/pip-check-312.json)；这不替代 clean 安装环境的检查。 |
| wheel/sdist 构建 | 通过；实际安装验证另列 | 使用冻结源、Python 3.12.14、build 1.6.1，`python -m build --outdir …/verification/dist` exit 0，命令耗时 3.616s；[命令](verification/build.json)、[输出](verification/build.stdout.txt)、[包身份](verification/package-identity.json)保存 wheel/sdist SHA-256 及各 100 个 runtime 文件哈希。wheel 为 `7ba118f36d864b7097fc3c87de43fc398cd93ef215a24be87e764096162540d8`，sdist 为 `1e6219a2fc82525ea9efc94bd3d4dc770b5a2742f668490979e639d6ad2f1b2b`。 |
| 双 fresh 安装及源码外 smoke | 通过 | Python 3.10.22 从 sdist、3.12.14 从 wheel 安装至两个全新 venv；[安装身份](verification/installation-identity.json)记录 artifact SHA、各 100 个实际安装 runtime 文件与 source 一致、`fresh_environment=true`。两个安装环境 `pip check` 均 exit 0，见 [3.10](verification/installed-pip-check-310.json)、[3.12](verification/installed-pip-check-312.json)。源码外 `-I -B` 组合 smoke 均 exit 0，详见下文。 |
| 完整结果资源 | 三项有限样本通过 | normal direct/readback 与原 extraction_mismatch 各用独立 fresh 进程串行完成，完整 Result build/encode/decode、wire、捕获保留和 RSS 原数据见下文；constructor 认证包含在 build/decode 内，未单独计时。 |
| 必须 findings 最终独立复核 | reviewer 结论：剩余 0 | [独立报告](code-review.md)绑定最终冻结源、原 findings 处置与工程索引；[只读审计](review/final-a8-audit.py)实际 exit 0，原结果保留。执行记录引用该结论，不代写 review 或 PM 验收。 |
| 原 W011 分支推送与远端确认 | 最终完整 SHA 以 Git 与交接回复为准 | 使用既有 noreply 身份提交至 `codex/w011-channel-identity-fin-count` 并推送；推送后以 `git ls-remote` 核远端完整 SHA。交 PM，不自行验收或合 main。 |

双 clean smoke 的工作目录为 `/workspace/work/w011-final-e89bdaa/installed-cwd`，使用各自 `clean-310/bin/python`、`clean-312/bin/python` 的 `-I -B` 隔离模式；实际导入均来自相应 venv 的 `site-packages/layauto_v2`。输入使用冻结快照的真实 fixture，执行代码来自实际安装产物。两者都完成 normal direct、W006 caller-read readback 和原 extraction_mismatch 的完整构造及 codec 重建：正常 5/7、mismatch 4/7 且恰一项 source 差异、18 FIN、原 local graph/body 和 `attempt_unchanged=true`；readback attempt 保持 unsealed。3.10 命令耗时 620.633s，3.12 为 450.631s，均 exit 0；[3.10 命令](verification/installed-smoke-310.json)/[原结果](verification/installed-smoke-310.stdout.txt)、[3.12 命令](verification/installed-smoke-312.json)/[原结果](verification/installed-smoke-312.stdout.txt)保留实际安装路径、逐 case wire/digest、计时和限制。

资源 probe 使用 Python 3.12.14，在 `/workspace/work/w011-final-resources-e89bdaa` 串行启动三个 fresh 进程，实际导入 `/workspace/Layauto/layauto_v2`；[资源来源身份](resources/source-identity.json)将每次 runtime、配置、probe/launcher 字节与已完成矩阵绑定。全部 exit 0，公开完整 Result roundtrip 相等，构造和 codec 阶段禁文件/repository IO；readback 不推进 attempt。下表列这些资源进程的原测值，秒数保留三位；完整精度、上游步骤、命令/环境/UTC/原输出见各回执。双安装 smoke 有自己的捕获与 wire 回执，其字节数不与本表混用。

| 独立进程 case | W011 build / encode / decode（s） | 完整 Result wire（B） | 进程 `ru_maxrss`（KiB） | 命令耗时与证据 |
| --- | --- | --- | --- | --- |
| normal direct | 37.209 / 1.522 / 46.759 | 54,050,313 | 2,847,416 | 101.154s；[原数据](resources/normal-direct.json)、[命令](resources/normal-direct.command.json)。 |
| normal readback | 74.948 / 3.064 / 101.861 | 136,461,405 | 7,322,828 | 211.577s；[原数据](resources/normal-readback.json)、[命令](resources/normal-readback.command.json)。 |
| extraction_mismatch | 35.419 / 1.397 / 45.179 | 54,049,506 | 2,854,456 | 95.969s；[原数据](resources/extraction-mismatch.json)、[命令](resources/extraction-mismatch.command.json)。 |

三个 case 各有 31 份原始捕获、合计 280,706 B，保留 40 条 drawn records（其中 FIN 18 条）、两 channel 的 36 项 FIN 判定，以及 14 local nodes、8 edges、6 components、16 项 T05 audits。normal direct/readback 分别是 count 5/7、comparison equal；原 extraction_mismatch 为 4/7、comparison mismatch、差异数 1。逐项 capture URI/SHA/bytes 和完整 wire SHA 在原数据内。公开 `ChannelIdentityResult` 同时保留 W010 receipt 和 W007 semantic result，后者也含捕获；readback 还保留 W006 prepare_inputs 的输入准备及 caller-read 回读事实，因此必须披露完整保留链的 wire 与重建成本，不能用中立 draft 体积代替。

以上 RSS 是每个独立进程的高水位，包含 imports、W005/W006 获取、W008–W010 构造、完整 W011 Result 及 wire encode/decode；它不是 W011 增量分配。**constructor 认证包含于 build/decode，未单独计时。** 计时顺序和对象保留按归档脚本执行，未从进程高水位推断某一个函数的分配量。

完整工程运行另有[1399 次原始采样](preflight/final-attempt02/resource-observations.jsonl)及[观察汇总](preflight/final-attempt02/resource-observations-summary.json)。观察始于 2026-11-09 12:08:03.555075 UTC，晚于 runner 启动约 28 秒，终于 16:01:11.130687；实际间隔约 10.004–10.033s，期间采到的各进程最大 RSS 为：

| 观察对象 | sampled RSS max（KiB） |
| --- | --- |
| Python 3.10 完整矩阵进程 | 9,257,804 |
| Python 3.12 完整矩阵进程 | 6,248,624 |
| clean 3.10 三 case 组合 smoke 进程 | 9,119,696 |
| clean 3.12 三 case 组合 smoke 进程 | 6,927,912 |

这些是长进程离散采样值，smoke 在同一进程完成三个组合，不对应上表某一 fresh case 的准确峰值；采样起点前和采样间隙未覆盖。共享 cgroup 采样最大内存为 **12,299,743,232 B**。`memory.peak=13,762,666,496 B` 在观察前后均未变，是既有会话累计高水位，不能归于本次任务；`memory.events` 各计数前后均为 0。原 gate 规划中的约 7 GiB 是准备时有限观察依据，最终披露以上实际采样，不将规划估计冒记为实测上限。

[实际执行限制](verification/resource-limits.json)及各资源回执均记录 Linux 共享环境、16 GiB cgroup 内存、`cpu.max=400000 100000`、可见 CPU 数 5；详细 swap/rlimits、依赖版本、原命令和输出可按证据清单复查。资源算法有有限 seed×channel、FIN×channel、FIN² 关系扫描，加上 rational union 与完整捕获反复认证。历史 completed probe 的约 1.4 GiB peak RSS 继续归属于其候选与命令，不与最终数据合并。全部结果只证明这些有限 synthetic 输入在该共享 executor 下完成；共享负载会影响耗时，最大输入、渐近性能、生产规模、多片段压力及并发性能均未获证明。未扩展资源承诺或为降低成本改写上游 wire，完整 net/body/model/T02/全部规则、工艺坐标、发布/no_change/Stage 6 及 U06 仍在原任务边界外。


## 交付差异检查与原输出保真

交付前再次核对：全部 262 项冻结内容未变；PM 要求/阶段及 PM 验收历史段与准备提交逐字一致；current-work、roadmap、架构、协作规则、fixture/答案和 legacy 均无执行改动。执行提交全部沿用项目 noreply 身份。文档本地链接有效，`git diff --check 81e01da1e5a6ce8e7132f3cebf8ee92bc237246f -- '*.py' '*.md' pyproject.toml` exit 0。

原始命令输出按字节及封存哈希保留，不为消除格式提示改写证据。包含所有原日志的完整 `git diff --check` 会报告 [geometry-r1.log](test-preflight/geometry-r1.log) 的 8 行尾空白、[首轮全量原输出](verification-attempt-01/pytest-310.stdout.txt)的 5 行尾空白，以及[最终 build stderr](verification/build.stderr.txt)末尾空行；这些均为原工具输出。源码、测试、Markdown 和 Python 工程脚本的检查通过，证据索引未因格式检查而改变。
