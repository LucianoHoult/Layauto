# 本次合并前 session 的公共与嵌套合同静态复核

受审版本：main `0a3326aa363477724465886cd05874d0997fba3e` → A1 `e4179dd42cc0de853df73bafd9140a363c8fa5be`。本专项为本次独立 reviewer 的只读辅助 `/root/nested_contract_audit`；未参与原 A1 方案、实现、正式测试或性能工具。本专项没有运行产品、正式测试、完整 codec/readback 或性能命令；以下为实际读取代码、diff、规范及已有测试后的静态结论，执行结果由主 reviewer 的新证据与原版本证据分别记录。

新增/剩余必须项 **0**。没有发现需要产品修复的可复现问题。

## 实际读取与结论

- 读取根 AGENTS、协作规则及任务 I1–I6/PM1–PM3；回查 architecture §3 的事实源、§3.7 FIN 派生、§3.8 递归不可变与外部 alias、§11.2 canonical codec/digest、§11.9 FIN 来源、§11.15 模块边界及 §12.8 synthetic 限制。全仓仅根 AGENTS。
- `git diff main..head -- layauto_v2 tests` 中唯一 runtime 改动是 `domain/codec.py::_decode` 的 hex 条件，唯一正式测试变化为新增 `test_w012_hex_validation.py`。原 matcher 调用仍在长度检查前，`fullmatch` 在此分支只执行一次；`bytes.fromhex`、最终 `ValueError`、`decode` 的重复 key 检查/非精确数字拒绝/canonical bytes 复验均未改。无 encoder、signature、trusted/cache、catch 或 constructor 次数的变更。
- 原 `(HH)*` 和新 `H* ∩ 偶数长度` 含空串且语言相同，H 仅 `[0-9a-f]`。这项数学结论不代替主 reviewer 的独立有限语言/错误对照，也不证明性能。本专项复读新增正式测试，见全部 ASCII 对、256 字节、Unicode/长尾、畸形 tag/JSON/重复 key/canonical 拒绝、matcher/fromhex 异常及调用次序覆盖。
- `decode` 仍把输入直接交 `json.loads`，其真实 JSON `$bytes` 字段为原生 `str`；object_pairs_hook 只建原生 dict，不注入子类。`_decode` 的原 `isinstance(..., str)` 未收紧。直接私调传入恶意 `str` 子类，新 `len(raw)` 可调用重写的 `__len__`，这一已披露的非阻断私有边界在 `plan-review.md` 保留；不能宣称任意私有子类副作用等价。公开输入类型及 canonical 对照没有被本次修改改变。
- 复读七个 codec：`domain.codec`、`domain.publication_codec`、`normalization.codec`、`geometry_codec`、`effective_codec`、`local_connectivity_codec`、`channel_identity_codec`。每个记录 codec 保留 `/1` schema、closed registry/type/field 校验、嵌套 bytes 的公开 decoder 与重建后 `_pack` 对照、最终 encode bytes 对照及 SHA-256。publication 仅其历史上无关 terminal/failure DTO 的有限异常翻译仍在，捕获输入 DTO 直接重建；semantic/geometry/effective/local/channel 的子 decoder/constructor 没有新增捕获或包装。
- 复读 `domain.evidence`/`domain.results` 的原生 immutable bytes、来源 hash、tuple 单次快照及 evidence/source 绑定；`ChannelIdentityResult` 保留 complete input 的闭合图检查、公开 encode/decode 重新认证、completed 全量字节对照、draft replace 和 semantic/draft 完整 wire 比较。builder 首次 `_require_input` 与 result constructor 第二次 `_require_input` 均在，预期 `ChannelProblem` 的 handler 先退出再构造结果，避免二次认证故障被挂上新 context。没有减少认证或把 hash 对照当完整 DTO/来源认证。
- 复读 `test_w011_exceptions.py`、`test_w009_nested_base_decode.py`、`test_w009_captured_decode_exceptions.py`、`test_w008_geometry_wire.py` 的实际注入与断言：故障在构造真实合法 wire 后注入，覆盖 complete direct/readback 各层 decode、SourceFile hash、nested Parameter、原预期错误后的第二次认证，以及 object/cause/context/suppression；畸形输入负对照同时存在。`test_w011_contracts.py` 继续覆盖来源拼装、可变 alias、错型等值、完整关联表和公开 roundtrip。
- 原 P1 probe 与 A1 probe 的完整路径检查继续核正常 5/7、mismatch 实际 4 对 source 声明 5 且恰一项差异、touch 证据、36 个 FIN evaluations 的全集/坐标/来源、40 drawn records/18 FIN、原局部图/T05/body及完整 DTO roundtrip；readback 另核 attempt/checkpoint 不变、unsealed、无 terminal。A1 installed smoke 还逐项核31捕获/hash/ref、14 nodes/8 edges/6 components/16 audits/body6、全部 crossing 的物理 nm 坐标和原 drawn FIN 坐标。输入和 runtime 位置分别指定，未把 target 当 source。
- 三固定性能输入本身不能覆盖全部 target-only/partial/unknown/异常负例。原正式 `test_w011_geometry.py::test_target_only_multiple_axes_do_not_change_source_geometry` 与 `::test_source_l_and_w_mismatches_are_all_retained_and_target_is_separate` 明确验证 target 独立；这些测试与其依赖源码无本次变化，是否通过以主 reviewer 核实的冻结双1656原输出为据。

## 有限补跑建议

主 reviewer 可按风险运行新增51项及既有基础合同，另选 W011 `test_expected_error_then_second_authentication_fault_keeps_preexisting_history` 的4个参数和 `test_actual_nested_w010_w009_w008_w007_wire_preserves_history` 的 readback/SourceFile hash 代表参数。后者 module fixture 会实际构造完整 direct/readback wire，应先核内存并串行；不必为本次两行条件变化重新运行全部小时级矩阵。

本专项未新观察任何生产输入、最大输入、原安装树或1.47GB大wire；wire实比/包安装/性能实测等事实不得从静态无 diff 推导，应按主报告分别标明本次实读、原版本采信与未验证范围。
