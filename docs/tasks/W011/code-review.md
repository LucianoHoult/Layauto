# W011 独立代码 review

Reviewer：`/root/code_review`；独立专项 `/root/code_review/geometry_review`、`/root/code_review/boundary_review`。各 reviewer 未承担本变更设计、实现或正式测试编写。日期：2026-11-09。

**产品代码必须修正项 0（`8917d38d916c914bfa785cb116982f3f299b38de`）；A8 最终工程交付仍待复核，不能作为最终交付通过或 PM 验收。** 产品候选开始于 `a8d3987bc3295c84ff2aa62be0350af51955fbeb`，随后各次修正身份及独立验证记录如下；受审 base 为 PM 准备 `81e01da1e5a6ce8e7132f3cebf8ee92bc237246f`。正式新增回归已冻结至 `02725e2e90be6b3145be915be699aa64ce998ed7`（runtime 与 `8917d38` 相同），双完整矩阵、包与安装证据仍由执行侧完成，最终结论将在本报告追加。

## 范围与方法

已读取根 AGENTS、README、协作/环境规则、W011 任务与方案/独立方案 review，查询无局部 AGENTS；直接对照相关架构、physical/derived owner、W007–W010 公共结果和来源合同。检查新增 domain/annotation/derive/normalization 及 codec、typing、具名依赖守卫和 README；原 fixture/答案、PM/current-work 不改。

源码检查与实际独立 probe 分开记录。来源专项运行实际 direct/readback、完整公开重建、source/target 临时捕获变体及跨源拒绝；几何专项独立核 exact 集合/覆盖与 scope；边界专项检查中立 DTO、实际嵌套 codec 和 expected 错误后的异常历史。独立 probe 只保存于 W011 review 附件，不作为 runtime 或正式测试依赖。

## 原 findings（保留）

### CR-01 — ChannelSeed 中立公开合同接受伪造的来源字段和错误 metadata 类型（P2，必须修正）

受审版本：`f49323311bd817f066cb3e2411cad45219764f04`。位置：`domain/channel_identity.py::ChannelSeed.__post_init__`。

保持合法 seed 的字段集合及其余数值，仅分别将 `record.metadata_opaque` 改为整数 `7`、将 `record.field_sources` 各值改为整数 `0`、将 `identity_provenance.field_sources` 各值改为整数 `0`。三例均被公开 constructor 接受，且 W011 `encode_record/decode_record` 成功 roundtrip。实现检查了 key 集合，却没有验证 opaque text collection 和每个 source location 的形状/来源。

这不是有效的中立 seed evidence；后续 `seed_source` 等消费者要求实际来源位置。完整 captured result 重算可以拒绝外来 seed，因此本 finding 不声称已突破 captured authentication；它仍违反 A6 的 closed、自洽且来源可重建的公开 DTO/codec 合同。须在中立 owner 验证完整字段和 source location，拒绝这些 malformed 值，且保持与 W007 已支持合法 seed 的一致性。

独立原证据：`probe_leaf.py` / `leaf.stdout.txt`（归档位置见后续附件清单）。三个 case 的 `constructor_accepted` 和 `decode_accepted` 均为 true。

### CR-02 — W011 新 semantic_record 嵌套面转换了意外异常（P2，必须修正）

受审版本同上。位置：`normalization/channel_identity_codec.py` 的 `semantic_record` → `normalization/codec.py::_unpack` 的通用 constructor catch。

用合法 `ParameterComparison` wire，在 nested `Parameter.__post_init__` 注入带有既有 cause、context、suppression=false 的 `TypeError`、`KeyError`、`AttributeError`、`UnicodeError`。四例 W011 `decode_record` 均抛出新的 `ValueError`，不是原对象，且对外的 cause/context/suppression 改变。`ValueError` 和 `KeyboardInterrupt` 对照保留原对象及原链。

W010 主要嵌套 W007 input，而 W011 新增 `SemanticCircuitDraft`、`Parameter`、`NormalizationResult` 的嵌套公共路线；现有 W007 宽捕获不能被这条新路线当成 A6 原异常保真。须保留意外对象及已有异常历史，另以明确形状验证拒绝 malformed wire；覆盖完整 W011 result 和中立 leaf 路线，不只测试 `NormalizationInput`。

独立原证据：`probe_semantic_exception.py` / `semantic-exception.stdout.txt`。四种转换异常记录 `same_object=false`；两个对照为 true。

### CR-03 — W007 expected admission 错误后构造结果污染意外异常 context（P2，必须修正）

受审版本：`f49323311bd817f066cb3e2411cad45219764f04`。位置：`normalization/component.py::normalize` 的 `except NormalizationError` 分支，经 W011 `_evaluate` 实际调用。

在临时真实输入中将 source CDL 的 NF 改为 2，重绑 capture 后保留正常几何。控制运行由 W011 返回原 `UnsupportedFingerCount`。随后在 W007 `NormalizationResult` 构造注入带有既有 cause、context 的 TypeError，W011 builder 抛出同一对象且保留 cause，但其 `__context__` 被当前处理中的 `NormalizationError` 替换。该错误 completion 仍在 except 块中执行，违反 A6 对“处理预期错误后再次构造结果路径”的原异常历史要求。

须退出 expected handler 后再构造 completed facts 和 error result；保留原 expected issue、progress 和业务结果，不需要改变 wire 或扩大输入语义。独立原证据：`probe_expected.py` / `expected.stdout.txt`，admission case 为 `same_object=true`、`same_cause=true`、`same_context=false`。其它 expected identity/progress 路径核验继续保留各自输出。

第二条真实路径也已复现：将 xref 身份改为 `UNKNOWN` 并重绑捕获，控制运行返回 `UnknownDeviceIdentity`；在 expected identity 错误后的 `facts=replace(...)` 注入同类既有异常，原对象/cause 保留而 context 被当前 `NormalizationError` 改写。两条原始实际结果均归档于 `review/boundary-expected-*`，与 constructor 故障共同证明 completion 的两处构造都必须移出 handler。

### CR-04 — aggregate 仅凭数值相等接受违反 exact scalar 合同的嵌套叶（P2，必须修正）

受审版本：`f49323311bd817f066cb3e2411cad45219764f04`。独立轻量实证位置：`domain/channel_identity.py::ChannelMeasurement.__post_init__`；同类 equality-only 模式存在于 draft/result 的完整重建比较。

从合法 `FinEvaluation(width_nm=Fraction(2))` 复制对象，明确使用 `object.__setattr__` 绕过该叶 constructor 把 width 改为整数 `2`；Python 认为伪造叶仍等于原叶。公开 `ChannelMeasurement` constructor 接受该叶并保存整数 width，虽然其直接叶 constructor 拒绝此值，随后同一 measurement 的 W011 codec decode 也拒绝。中立 aggregate 的公开构造与 decode 对同一对象不等价；`validate_closed_graph` 只能证明 int 是闭合 scalar，不能替代 field-specific Fraction 合同。

这条探针有意模拟任务要求拒绝的调用方篡改，不声称普通 frozen dataclass 赋值能够成功，也尚不以轻量结果冒称已实测完整 captured 顶层绕过。须在每个新 aggregate 公共边界重建嵌套 leaf/aggregate，不能用 `bool/int/Fraction` 的 Python 等值替代 typed canonical 一致性；正式回归应扩展到 draft/result 与 semantic 嵌套。原脚本 `review/boundary-probe-equality.py`、原输出 `review/boundary-equality.stdout.txt` 保留直接非法叶拒绝对照，以及 public constructor accepted / codec rejected 的矛盾。

修后残留的独立实证：冻结 `3dbe2704ee03c3cd1cda3fb110b9b376cf9f0c3d`（含 `88fefa7`）实际构建 normal W011 result 后，仅通过公开 `replace(EvidenceRecord, payload=...)` 把 `completed` 的 `tech.payload.owners.physical.fin_count_profile.finger_count_required` 从整数 1 换成 bool True；这次无需绕过 frozen constructor。该证据中立形状合法且 Python 等值，但 canonical bytes 与同捕获原事实不同。公开 `replace(ChannelIdentityResult, completed=...)` 接受并保留 bool，说明仅 canonical 比对 value/semantic 还漏掉 completed。原脚本/输出 `review/source-completed-original.py`、`.stdout.txt`、`.stderr.txt`：退出 0，normal 5/7；`constructor_accepted=true`、`retained_type=bool`，67.54s、peak RSS 1,404,568 KiB。初次探针把 tech payload 的 owners 层漏写而未造成改动，该 harness assertion 失败也原样保留于 `source-completed-harness-original.*`，不算产品发现。

另一修后残留：冻结 `c37eecf` 的真实中立 draft，复制后将 source MN0 `finger_count` Parameter.source.line 从 3 改为 999、保留 field_evidence.line=3。公开 Draft 完整重构正确拒绝，但其 `canonical_bytes(to_value())` 与原对象完全相同：摘要只带 source 语义/preservation，未覆盖未计量 NF/M 的独立来源字段。Result 只 closed-graph 检查 supplied draft、再比此投影，不能代替完整 DTO 重建。独立 `review/boundary-projection-*` 保存 `draft_equal=false`、`same_projection=true` 与公开重构拒绝对照；没有运行的 full Result 路线不由该证据冒称已实测。须对 supplied draft 完整公开重构，并使用完整表示比较。

### CR-05 — 合法 seed 的定位失败诊断把来源 wrapper 当成 source location（P2，必须修正）

受审版本：`f436f591ca77af364293e8201cebc12635d7c53c`。位置：`annotation/channel_identity.py::seed_source`。

真实 normal 捕获经 W007 生成合法 `device_seed`，投影 `ChannelSeed` 后调用 `seed_source`，即抛出 `ValueError('source location requires nonempty text')`。`record.field_sources.record_id` 的实际形状为 `{derivation, sources: (...)}`，其中 `sources[0]` 才是带 `path`、`sha256`、`json_pointer` 的 location；原 helper 直接把 wrapper 传给 `ref_from_location`。正常唯一定位没有执行该 helper，因而正常 5/7 不足以覆盖此缺口。

定位零候选、多候选、身份冲突需要该 helper 生成 located issue；这条支持范围内的诊断路线会抛非预期 ValueError，不能返回保留全部已知事实的 error draft。须解包真实来源 operand，保留来源与 issue，不把 wrapper 缺口与 CR-01 的 malformed 中立 DTO 守卫合并。独立原脚本/完整 traceback 见 `review/geometry-seed-source-original.py`、`review/geometry-seed-source-original.log`。完整边界路线另行保留实跑结果。

定位残留：`975852d` 已修复 helper crash，但 Missing/AmbiguousSeedChannel 又把真实 record JSON pointer 覆盖成不存在的 `/recognized_channel_intersection`，使两条真实 seed 错误具有同一 SourceRef 与同一无 ID message。专项首次将 wrapper 修正视为整项闭合的判断已撤回并原样记载；`review/geometry-pointer-*` 保存修前两版本及修后独立逐项解析 JSON pointer 回到 D0/D1 的证据。此处只要求保留已有定位，不新增输入语义。

### CR-06 — 同一 registry 来源位置的 seed 声明与 derived owner 矛盾，中立聚合仍接受（P2，必须修正）

受审版本 `c37eecf844e27787b478bccddfdb8fdaba18bc06`。实际 read→W007 seed 的 `derived_layer.sources[1].lexeme.target_layer` 改为 METAL，并同步 geometry_kind/quality 的同位置副本；path=`tech/derived.json`、原 SHA、pointer=`/derived_registry/0` 全保留。传入中立聚合的真实 derived owner 对同一位置仍声明 POLY。公开 ChannelSeed 和实际 W010 local + W007 source/seeds 的 `build_channel_identity_draft` 均接受，issues 为空、count 5/7。

这两份已声明为同一来源位置的内容自相矛盾，属于中立聚合的自洽检查，区别于读取捕获字节才能证明的真实性；不要求中立层新增 IO，也不把单纯来源路径不同当作本实证。须交叉核对 seed 的已有 registry operand 与传入 owner 的声明/定位。原脚本、输出与 14.70s/660,112 KiB 资源记录见 `review/boundary-owner-*`；最初 GeometryInput.completed 写错的 harness 失败也保留，未算产品 finding。

## 修正与复核

执行修正按候选分别复核如下；原 findings 不删除或改写为“从未发生”。最终工程证据未审完，不以当前代码检查替代 A8。

- 冻结 `975852d3b9ea946aca24f727071cf26a7dce8bc7`：CR-01 三类 malformed seed 全拒绝，合法 seed roundtrip；CR-02 六类既有异常对象/链全部保留，另 16 种 W007 中立 exemplar roundtrip 和 384 个 field/type 对照中，369 个 ValueError 明确拒绝、15 个合法/可选中立变化接受、没有非 ValueError 形状泄漏；CR-03 两条真实错误捕获路线均保留同对象及 cause/context/suppression。原脚本与按候选 hash 清单见 `review/boundary-recheck-*`。
- 冻结 `88fefa7c550993ed0d53d4ae073419a36a7b200b`：原 CR-04 measurement 嵌套 int width 被公开 aggregate 拒绝，见 `review/boundary-members-*`；此结论不自动覆盖后续顶层残留。
- 冻结 `c37eecf844e27787b478bccddfdb8fdaba18bc06`：CR-04 completed 的同一实际 probe 被明确 ValueError 拒绝，normal 控制仍为 5/7。`review/source-completed-fixed.*` 保留源 hash、原输出与命令脚本；退出 0、65.57s、peak RSS 1,404,224 KiB。对 supplied draft 的完整字段重建仍另行复核。

### 产品修正最终复核：8917d38

CR-01/02/03 的原始修正仍保留，边界专项在最终 runtime 上补查原叶子/异常与 malformed 控制；CR-06 的同位置矛盾 owner 原实际样本在中立公开 draft 明确 ValueError 拒绝、合法 control 正常，见 `review/boundary-final-receipt.json` 和专项报告。

CR-04 最后残留已由主 reviewer 实际完整 Result 验证：正常同捕获、禁 Path IO 的构造得到 5/7、16 comparisons 及原图/body；分别把 supplied draft 的未计量 NF 来源改为 line=999、等值但错型 Fraction(3)，公开 Result 重建均明确拒绝；completed 的 boolTrue/int1 等值替代也明确拒绝。拒绝发生在真实 captured Result 路线，补全先前 neutral 投影探针的范围限制。逐项原输出、源 manifest 和命令见 `review/source-final-stage1.*` 与 `review/source-final-receipt.json`。

CR-05 的 wrapper 与定位 pointer 两层问题均关闭：专项从最终 `8917d38` Git archive 重跑两个真实 seed 的缺失候选诊断，各自 JSON pointer 可解析回 D0/D1，message 含 ID；最终 annotation 比早前 patch 多显式 `str(record_id)`，没有冒记字节相同，已重新验证。见 `review/geometry-pointer-891.log`、`review/geometry-pointer-commit.json`。几何和边界专项原 findings、首次关闭撤回、中间失败及修后证据全部保留。

最终独立 source/target 补证：只改 target 的 NFIN/L/W/NF/M 五轴，仍得到 source comparison equal、几何 5/7，并保留五轴 target differences；把该变体的 semantic receipt 混入原 Result 被拒绝。该次 probe 随后错误要求拒绝 target-only 来源的中立 draft，实际上所有 consumed source/geometry/seed/owner 与完整中立 DTO 均相同，可以替换；此 harness 退出 1 与解释原样保留，不列产品 finding，也不把捕获真实性强加到中立对象。未执行的 source 段随后独立续跑（`source-final-continuation.*`，退出 0）：source NFIN/L/W 同时变更保留全部 15 项 mismatch（1 count、2 L、12 W），实测仍为 5/7、4 nm、2 nm；漏 comparison、丢 local audit、假 error status 均拒绝。续跑 72.47s、peak RSS 1,410,952 KiB；完整最终 result codec/双安装仍由 A8 矩阵证明，未以此小范围 probe 替代。

### A8 矩阵发现的测试 setup 补修

`02725e2` 的 3.10 完整矩阵暴露 target-only 测试按 source 参数词序寻找 target 文本，在 helper 的 `assert before in text` 失败，尚未计算该 target 变体。执行者最小补修 `27f885497634d0f2ed50d293e00603309d34c0cd` 只调整 before/after 两行词序，全部业务断言、runtime、fixture 均未改。主 reviewer 独立轻量读取/normalize 核对实际三轴 delta 和保留字节，并审计原定向失败、修后 3.10 单项 `1 passed in 136.82s` 与提交字节一致性；增量必须项 0，详见 [增量 review](review/target-order-review.md)。旧失败/旧矩阵不能算最终通过，修改后须重新冻结双完整矩阵；A8 继续 pending。

新矩阵拟使用执行侧资源 gate，让两个解释器的旧阶段可并行、W011 从 fixture setup 前至进程退出保持互斥。独立[静态 harness review](review/resource-gate-review.md)保留 HG-01 原失败路径与修正，当前 gate/runner 必须项 0；完整 1605/原1465 门槛、测试及 fixture 均未削减。该结论只允许按记录条件运行，真实双矩阵、锁事件、包/安装/资源结果仍待 A8 核验，不能以门控小样替代正式回归。

旧矩阵第二个 setup 失败将 schema 已禁止的 `effective_fin_operator='foreign'` 交给 success-only helper，实际在 W005 reader 已返回 located InvalidSchema。补修 `1cb7e1bc654c61690427ac22481b985156d9c9e6` 保留四个原参数 ID：该项核实际 reader 的 typed error、精确来源与捕获/completed，其余三项仍完整运行 W011，并加强拒绝 issue 的来源断言。独立轻量实际读取确认既有边界，静态核对 tests-only 24 行增加、runtime/fixture 不变，再核正式 3.10 原四项 `4 passed in 182.45s` 与提交字节一致性；增量必须项 0，详见 [入口层级增量 review](review/operator-admission-review.md)。原失败保留，最终新冻结双矩阵仍 pending。

### 独立来源组合 probe 的原执行与 harness 更正

`review/source-probe-initial.py` 在 `f493233` 产品导入后顺序执行实际 normal direct、W006 caller-read readback、禁 `Path.read_bytes/read_text/open` 与 `repo.read` 下 W011 构造和完整 readback result codec，随后核 attempt 等值且 unsealed。原 stderr 停于后续临时 target 的 `read_inputs` assert，故以上前置 assertions 均已执行通过；由于原 probe 只在末尾打印 checks，不将空 stdout 冒记为完整成功 receipt。命令、原脚本/stdout/stderr、身份依据和限制见 `review/source-probe-initial-receipt.json`。

失败原因是 reviewer 将 target VT 改成既有 literal grammar 不支持的 `alternate`，轻量解析重现 `InvalidCdlValue('unsupported literal for VT')`；这是 probe 使用范围错误，不是产品 finding。后续 target witness 使用现有支持的 NFIN/L/W/NF/M 变化，不修改 fixture/owner 以接受新 VT。尚未执行的 target/source/cross-capture assertions 不由这次退出 1 推断通过。
