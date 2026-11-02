# W007 内部接口方案（执行）

基线 `64b4ad2f77c017affade69374510dc12e534bc07`；执行者 `/root`。只完成任务 A1–A7 指定的纯语义切片，不发布稳定外部格式或推进 attempt。此文是待独立 review 的实现方案。

## 输入与两条适配链

`NormalizationInput` 是 domain 内 versioned、runtime-validated frozen DTO，保存同一次成功 `ParseResult` 的 value、completed evidence、SourceFile bytes（或等价完整 ParseResult），以及可选的中立 run/readback binding。`from_parse_result(result)` 接受 W005 成功结果；`from_inputs_ready(ready, checkpoint, parse_audit, tool_run, evidence_audits)` 接受调用方已经读回的 W006 domain 对象，函数本身不调用 repository。核对 kind/run/content_ref、checkpoint/attempt revision、ready.value、parse.tool_ref/tool_run_id、全部 evidence refs/content 和 captured source 集合；两者产生同一输入，来源关联额外保留但不影响语义比较。

输入构造验证固定 schema、唯一 required evidence kinds、value 与 completed payload 一致（tech owners/bundle 特殊映射）、SourceRef URI/hash 与实际 bytes 一致、嵌套 CDL/query provenance 可回到 captured source、CDL raw_document/hash 与来源一致、header 的 source/target/layout/raw/tech closure 与相同 source 集合一致。角色由 completed.kind 的捕获来源确定，再核对该角色的声明 hash；保留 header 原 URI，不要求其与 SourceFile.uri 字面相同，不按 hash 跨角色选择对象。W005 已验证的路径别名继续合法，不访问磁盘/resolve。信任边界为 W005 成功捕获的 parser 事实；此处证明 value/completed/嵌套来源与读回内容内部一致，不声称凭 SourceFile 重建捕获时全部 alias 路径。不同 run/source 的拼装通过上述关联与内容校验拒绝。公共无效 DTO 抛 ValueError；已验证输入的预期准入/关联失败返回 normalization issue。不会用新的 manifest 要求用户补数据。

## 语义、身份和目标

`domain.identifiers` 提供显式 typed `CellId`、`DeviceId`、`NetId`、`DeltaId` 和 query-run key；cell/name 组成语义身份，query key 包含 header/run/database 身份。identity 用版本化 canonical bytes/SHA-256，不用 Python hash。集合 canonical 排序；端口与端子保序。semantic digest 只包含 profile 所定义的语义，record digest 包含 bytes/lexeme/field provenance：format-only 输入语义相同仍保留各自不同来源。

`domain.circuit` 定义 source `SemanticCircuitDraft` 与独立 immutable `TargetCircuit`（可共享不可变值类型，无可写 alias）。包含全部 top/subckt、ordered ports/globals、Device（model、按该 model terminal_order 排列的 terminal refs、所有 canonical parameter axes）、Net（port/global 属性和全部 device-terminal memberships）。参数保留 token、canonical axis、Fraction/string exact value、unit、lexeme、SourceRef/完整字段 evidence。文档 preservation refs 保留完整 CDL evidence，不丢未选 top。Device/Net 不含 query keys 或几何。

所选 `toy_literal_cdl/1` 的完整 comparator 由 profile 选择，并显式验证其已实现含义；不凭参数名字推断。按 model.parameter_axes 取 canonical 轴。当前模型固定 D/G/S/B、sd_symmetry=false；xref swap 保留在 identity 事实并返回定位 UnsupportedTerminalSwap，不重排 semantic terminals。source finger_count/multiplicity 从 profile required 值准入；target 不做这些 source 限制。

`TargetDifference` 包含稳定 delta id、source=cdl_diff、op_type、typed operand、scope、before/after、required_capability、未满足规划义务、hard_constraints/preferences（无声明时空）、两侧 provenance。覆盖 cell 增删/身份、有序 ports、globals、device 增删/model、ordered terminals、net/member关系和每一个 canonical axis。全部 delta 保留，cell 重命名可表示 remove/add；device/axis 改变不得被 resize=false 过滤。C13 channel_length 4nm→5nm 保留，所有 difference 只是待后续 planner admission 的义务，不输出 no_change/baseline/terminal。

## Identity、seeds 与结果

纯 `normalize(input) -> NormalizationResult` 依次构造 source draft、target、完整 differences，再做 source admission/identity。result 为严格 success/error discriminated DTO；成功包含完整产物，错误包含定位 `NormalizationIssue` 与已完成 immutable facts/input provenance，禁止成功携 issues 或失败携完整成功 value。unexpected Exception、KeyboardInterrupt/SystemExit 原样传播，仅捕获组件自有 expected error。

iXref 全量关联 source top 的 device；先检查未知/缺失 source、layout 唯一性与覆盖，再判已覆盖 source 上的额外 layout multiplicity。C08 缺失source并多对一→UnsupportedDeviceCardinality；C09 finger_count≠required→UnsupportedFingerCount；C10 source全覆盖但额外layout归并→UnsupportedDeviceReduction。未知/冲突/缺失映射分别定位 typed issue；source multiplicity≠required 单独 UnsupportedMultiplicity。nXref/NET NAMES 全量关联 source Net，并检查唯一 key/index、重复/缺失/未知/冲突，不按字符串相似或序号猜测。

`DeviceIdentity`/`NetIdentity` 保留 run-scoped query backlink 和 xref provenance。`DeviceAnnotationSeed`/`NetAnnotationSeed` 独立关联 semantic id + query key + 原完整 region record，保留 exact vertices/bbox、kind/quality/unit/precision、opaque metadata 和字段来源。源query条目不能在join中悄悄消失。它们不代表空间覆盖、连接或body正确。

新增 domain codec 用显式 closed 类型/字段表复用已有 exact scalar codec；不改 W005/W006 wire schema。全部公共 DTO decode 后再跑构造验证，拒绝 unknown fields/version、错 typed ref/非法组合/非exact数。聚合 DTO 同时验证 foreign/missing/duplicate semantic IDs、完整 terminal/net membership、seed query key 与 semantic ID、diff operand/两侧 provenance 的一致性，不能只通过单字段类型检查。normalization 只依赖 domain/tech 的纯合同，不 import importers、pipeline、tooling、repository、transactions、state、legacy 或 tests/support。

## 调查与验证

复用 v2 `domain.codec` 的 FrozenMap/Fraction/canonical bytes，以及 W005 已捕获解析结果和 W006 中立 DTO/content refs；不调用旧 parser。legacy CDL/diff 候选需拒绝 float、隐式默认、只选NFIN、几何字段和query便利JSON路径；调查细节随执行记录保留。不迁移归档 runtime。

实际 W005 与 W006 readback 链、禁IO、手写完整语义判据、合法重命名/重排、C08/09/10正确重绑、C13及多delta/结构变化、xref缺失/未知/冲突/swap、真实 W005 header symlink alias 成功与不同内容 source/target/query 拼装拒绝、DTO alias/invalid/wire/hashseed/异常边界覆盖 A1–A6。A7 跑全部 W005/W006（含两项IPMR-01）、新测试、strict mypy、Python3.10及开发3.12、新sdist/wheel、干净安装源码外正常/拒绝/目标差异 smoke。测试和review绑定实际最终源码SHA/提交，保存命令/环境/结果/未覆盖范围。已验收fixture/答案/历史报告不改，PM验收与main合并留PM。

公共 API 拟定：`from_parse_result(ParseResult) -> NormalizationInput`；`from_inputs_ready(InputsReady, InputCheckpoint, ParseAudit, ToolRunResult, tuple[EvidenceAudit, ...]) -> NormalizationInput`；`normalize(NormalizationInput) -> NormalizationResult`。domain 内明确 CellId/DeviceId/NetId/DeltaId/QueryKey，及 Parameter/Terminal/Membership/Device/Net/Cell、SemanticCircuitDraft/TargetCircuit/TargetDifference；字段结构由实现保持封闭校验。内部按输入验证、语义构造、差异、identity分模块，公共codec独立于W006 wire。
