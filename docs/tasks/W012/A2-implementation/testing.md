# A2 新增测试与开发检查范围

测试作者 `/root/formal_tests`；独立 detached worktree `/workspace/work/w012-a2/tests`，起点 `0213c346ac03b7b7282aae522c299155958ac8f6`。只新增正式测试及本实施附件，未改原测试、fixture、判据或 PM 记录；候选两 runtime 文件由实施者复制用于测试，本作者没有设计或修改 runtime，也不承担独立 review。

## 新增正式测试

[`test_w012_typed_pack.py`](../../../../tests/contracts/test_w012_typed_pack.py) 共 82 项，实际候选 Python3.12.14 运行通过。命令、解释器、source SHA-256 与 stdout/stderr 见 [development/new-tests-command.json](development/new-tests-command.json)。首次 80 项通过后增加各 delegate 的公开 decoder 拒绝控制；首次测试源码、两次原输出均保留，未覆写。最终 82 项结果不是完整工程矩阵。

| 范围 | 新测试的独立依据与覆盖 |
| --- | --- |
| 两 registry 全字段 | 21 个 exact 注册类型与 dataclass 定义的全部字段逐项相等；私有 helper 按原 `_SPEC` 次序读取一次。每字段有唯一标记；同时比较未改 `_pack`/canonical 和用明确 `$map`/`scalar` 标签、JSON 参数构造的完整期望 bytes，不只比较 Python equality |
| 全 delegate | 两 owner 所有 classes tuple 成员、全部 tag、原对象 identity、调用次序与完整返回 bytes 逐项核验；spy 仅用于隔离分派，不能冒记为完整来源认证。真实 EnclosureSide/FinEvaluation roundtrip 另外走原 geometry/effective/publication encoder |
| scalar/map/tuple | 明确 bool/int/Fraction 等值三种编码不同；Unicode、escape、空及非 ASCII bytes、约分 rational、100 位整数、opaque 保留键、tuple 物化；map 在后续 tuple item 改变原 map 前已经立即 detach。只在 test 私有机制见证中故意破坏 immutable 值，不改变产品准入 |
| 公开 encoder/decoder | 7 个真实公开小 DTO 的原完整 bytes、hash、exact 重建类型；root subclass/foreign、mutable str/equal-object/list 原图检查先于 pack；wrong-type equal rational coordinates 在 constructor/decoder 拒绝；缺/额外字段、unknown/错 tag、scalar collection、tuple、各 nested bytes/exact-result、duplicate/float/whitespace/schema 拒绝 |
| 异常历史 | 真公开 encoder 剩余 scalar freeze 与 nested encoder 故障保持同一 object/cause/context/suppression，含 ValueError/TypeError/KeyboardInterrupt/SystemExit；原 JSON 大整数转换先于整串 UTF-8，surrogate 的完整 UnicodeEncodeError args 与旧 `_pack` 路径一致 |

全 registry field shell 是专门隔离字段读出与标签行为的 test-only exact class 对象，没有调用语义 constructor；不声称它们是合法 DTO、可接受完整 Result 或捕获证据。公开完整来源、run、owner 与重建仍由以下原正式回归及三路真实组合核验，不能用这 82 项替代。

## 建议串行运行的受影响原正式回归

由集成执行者在主 checkout 统一调度，避免与完整性能筛选并发。这里列选择理由；本测试作者没有运行这些重型 fixture，也没有将建议写成通过。

- W010 `test_all_new_public_records_roundtrip_with_stable_digests_and_frozen_fields`、`test_public_collections_take_one_snapshot_and_do_not_keep_caller_aliases`、`test_nested_foreign_and_mutable_aliases_are_rejected_before_encoding_copies_them`、`test_new_literal_fields_reject_mutable_equal_objects`、`test_audit_margin_is_an_exact_native_fraction`、`test_fraction_subclass_and_mutable_fraction_components_do_not_enter_audit`、`test_foreign_metaclass_equality_cannot_impersonate_a_registered_record`：完整真实 owner 的全记录及 closed/exact/alias。
- W010 `test_rules_payload_and_actual_source_role_must_match_this_capture`、`test_w010_reauthenticates_grouped_payload_forgery_against_retained_bytes`：实际 rule/source owner；`test_public_builder_reauthenticates_full_direct_or_readback_capture_chain` 与 `test_neutral_and_readback_outer_paths_reach_the_same_protected_boundaries`：readback/run 及下层完整认证。
- W011 `test_all_public_records_roundtrip_are_frozen_and_rebuild_stably`、`test_public_results_reject_cross_capture_semantic_or_graph_substitution`、`test_derived_source_role_is_bound_to_actual_capture`、`test_native_collection_snapshots_detach_all_caller_aliases`、`test_foreign_mutable_aliases_rejected_before_codec_can_copy_them`、`test_complete_input_chain_rejects_grouped_payload_forgery`：完整真实记录、来源及五 consumed owner。
- W011 `test_cr01_seed_leaf_rejects_untyped_opaque_and_provenance_fields`、`test_cr04_equal_numeric_values_cannot_bypass_nested_representation_validation`、`test_cr04_completed_capture_payload_uses_typed_canonical_equality`、`test_cr06_seed_owner_operand_must_match_retained_derived_payload`、`test_cr04_full_result_rebuilds_unmeasured_source_provenance_beyond_projection`：保留旧 finding 与非投影 provenance/type 防线。
- `test_w011_exceptions.py` 全文件：实际 nested W007–W010 constructor、预期错误后的第二次认证、nested Parameter、诊断故障及原 cause/context/suppression，不由新私有 spy 代替。
- W009 `test_new_collections_never_validate_and_copy_different_iterations`、`test_closed_graph_checks_original_payload_before_canonical_folding`、`test_exact_fraction_must_also_have_native_integer_components`、`test_original_receipt_graph_requires_known_record_types_before_encoding`：原 single snapshot/原图/精确 Fraction 合同。

最终全量若获筛选依据后继续，应保留原 1656 个 node ID 并加入本 82 项；以新冻结源码/测试/配置在双解释器实际完成，不采信 A1 旧结果为本算法已过。
