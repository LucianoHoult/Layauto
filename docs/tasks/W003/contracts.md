# M1 文件及共享记录样张合同

本包用显式的小子集解释每个字段，以便 reviewer 从输入算出答案。它落实 [W003 要求](../W003-m1-fixture-contracts.md)，没有修改 [架构](../../architecture.md)。`w003-example/1` 是本包示例版本；未来 runtime schema、CLI 与产品持久化实现另行派发、review，不由本文件发布。

## 文件链与双方 owner

| 边界 / 来源 | Producer → consumer | 必需材料、单位/引用和子集 |
| --- | --- | --- |
| Source GDS | 手写 synthetic spec → fixture writer；未来 importer → normalization | 单 top `INV_M1_SYNTH`；flat axis-aligned BOUNDARY，仅精确闭合矩形。每个 element-tagged layer/datatype、XY integer tick、UNITS REAL8 原 bytes 和 exact rational 保留；unknown key、非矩形、hierarchy、property、PATH/TEXT/BOX 等本子集外记录拒绝，不包络或丢弃 |
| Source/target CDL | 独立文本样本 → importer → current circuit / immutable target | 同一 top/pin order；TOY_N/TOY_P 有序 D G S B、显式 NFIN/NF/M/L/W/VT；模型含义由 toy profile 给出，不能从 token 猜。只支持所声明 literal/suffix/注释/空白；include/library/表达式/未知 directive/escape 均拒绝；空 include closure 也留记录。全量语义比较包括未改参数、模型、端子、top、pins |
| 四类 raw query | spec 的 synthetic capture → 将来的正式 importer | instance/net xref、device/net rectangle region；header、unit、lexeme、count、terminator 和 dialect version 完整；raw 是输入，normalized 仅可重解析缓存/期望。无真实 binary invocation，无 matched/live 声称 |
| Header/closure | fixture assembly → importer 基础 binding 校验 → normalization identity join | source layout/netlist/top、netlist transitive closure、deck/map/runset/options/preprocess closure、四 raw 实际 bytes hashes、parser/dialect/generator 版本；header hash、缺项/漂移 required-fail。合成 query database id 只在本 bundle 内有效 |
| Drawn/derived registry | toy tech → config loader、normalization/annotation/extraction/export | drawn registry 独占 stream key、tier、projection、edit/lifecycle、via/cut；derived registry 独占 carries、quality/trim/tolerance/aliases。ref 唯一解析，双重或未知映射拒绝 |
| Geometry/CDL/FinCount/DeviceExtraction/body/units/rules | toy tech → Stage 1–6 对应 consumer | 完整 toy 算子和适用范围；normal no_change 的全部 mandatory checks 不能 disabled/deferred。single-finger/one-to-one/no reduction；resize operator 不支持，不能据本包启用真实 shrink |
| Site / export / validation policy | fixture run selection → pipeline/config importer | 路径相对 site YAML 所在目录；选择 tech/inputs/raw/normalized/mode/output，不能重复 design facts。required GDS/CDL/JSON + 人机报告；immutable versioned output path；源坐标禁止 snap，输出不可表示/越界拒绝。synthetic 正常 requires_review；required failure reject |
| Layout JSON / GDS / CDL 期望 | 手写 oracle + 独立 reader → future exporter/checks | geometry 全记录语义、current semantic、occupancy、annotation、connectivity、lifecycle/linkage；source=target 不许可省略 mandatory checks；golden 只是回归，独立表/reader 才是另一路依据 |

所有 YAML 需 `schema_version`，safe loader；拒 duplicate/unknown keys、executable tags、超限 size/depth。样本不定义通用 Calibre、CDL 或 GDS 新标准。具体合成语法和坐标值以 fixture spec/profile/raw 为本包来源。单位按架构 §2.2/§12.5：REAL8 编码允许的舍入误差只用于证明唯一 nominal scale；它不是 geometry rounding 或 annotation tolerance。Stage 2 必须保持原 tick 可精确表示，Stage 6 另作纯输出变换。

## 共享记录与 exact wire

`examples/schema.json` 列出每种样张的 required/optional/forbidden 字段和 discriminator。每条记录都有 `schema_version`、`kind`、typed `id`、`example_only: true`；没有字段表外的扩展键。它是最小实例的中立字段合同，不实现 runtime DTO/codec。产品 owner 映射依据架构 §2.1–2.7、§11.2–11.13，非代码模块存在性声明。

| 记录 | Producer → consumer | 最小约束 |
| --- | --- | --- |
| ToolRunResult / ParseResult / EvidenceRecord | tooling → pipeline → importer；importer → normalization | ToolRun 仅 execution facts，不含 parse/findings；Parse 单向关联 tool_run_id，Evidence 关联 raw/hash/header/parse、原 bytes/lexeme/exact units。dummy fixture 不伪造 Calibre run，未来读取 fixture 的 execution outcome 也只是预期 |
| ProposedInitialState | normalization → InitializationTransaction | 绑定 evidence/tech/coordinate/capability，current 与 target 分离，geometry/occupancy/annotation/connectivity/lifecycle 全部有 component refs；不是可直接提交的用户输入 |
| PreparedBaseline | InitializationTransaction → repository | `kind=PreparedBaseline`、publication_kind=baseline；expected absent head、attempt revision、sealed context、prepared snapshot refs 与 lifecycle audit；失败不能发布半 baseline |
| ImmutableContext / Snapshot | Stage 2 + initialization → repository / read consumers | version 0、InitializationEvent；state linkage 与各 component refs；target/context 是独立 sibling，完整 tech 不嵌入 snapshot；递归冻结、无 writable alias、cache 外置是未来 runtime 验收，JSON 文件不能证明内存性质 |
| RunAttempt | pipeline request → repository | unsealed revision 0 仅 raw descriptor/入口 digest、starting head；sealed 才绑定 canonical context。operation/run/key/request digest 幂等；no_change close 必须 CAS 观察到的 state head |
| NoChangePlanningResult / neutral audit | planning / constraints → pipeline/RunRecord | all-delta semantic+extraction equality，candidate/mutation 皆无；whole-cell mandatory checks 有明确适用范围和结果。不能只以 CDL 文字或 5/7 相等通过 |
| RunRecord / Stage5Closure | pipeline 构造、repository 冻结 → Stage 6 | no_change 空 ordered_commit_ids，final snapshot 仍必须存在；stage audits 中立化。Stage 6 不回填 RunRecord。baseline initialization 不是 ECO envelope |
| StageFailure | stage boundary → pipeline/failure reporting | run、stage、category/code、reason、completed refs、localized refs；pre-context 不含未建立 canonical refs，freeze failure 独立 variant；不是 ValidationResult |
| ArtifactManifest | export → validation/reporting/pipeline | 同 run/snapshot、core objects required、immutable URI/type/size/actual-byte hash；只说明完整可寻址，不授权 production，report/validation 后续 refs 不回填 |
| ValidationResult / CheckResult | validation → reporting/pipeline | run/snapshot/chain/manifest；status、coverage、severity、disposition 四维独立，reason/localized refs/runtime/return code；只有 core manifest 成立后才正常 validation |
| ReportingResult / PipelineResult | reporting → pipeline；repository terminal → consumer | 报告失败不修改 checks；Pipeline 绑定原 closure/run/snapshot/result refs，terminal 与 accept/requires_review/reject 分开；production consumer 必须从 terminal root 判断，不能只拿 manifest |

本包 exact encoding 选择如下，待 reviewer/PM 核对后才可供下一实现任务采用：

Snapshot 的 component refs 指向独立期望中的字段/fragment witness，用于展示编码，不是完整预制状态。`expected/layout.json` 明示 `is_complete_runtime_snapshot=false`；它的 geometry、terminal graph 与 current semantic 有完整本例期望，occupancy 以两个 fragment 的同 cell 反例及相关 region 样张说明。后续实现必须从实际 Stage 1/2 构造全部 occupancy/annotation components，逐项验证这些独立期望与投影不变量，不能以直接加载该 JSON 或只比其中已列字段代替完整 snapshot/export 验收。

- ID 为 `{ "type": "RunId", "value": "example-run" }`；ref 保留 type，不把裸字符串碰巧相等当 join。示例 ID 是可读 symbol，不冒充内容 hash。
- 坐标、版本、size、序号是 JSON 整数；rational 是约分后的 `{ "numerator": "1", "denominator": "1000000000" }`，分母正；Decimal 若用则 tagged decimal-string，无 float/NaN/Infinity。enum 为字段表中字符串；路径为显式 UTF-8 POSIX 相对路径或 URI，禁止隐式 cwd。
- 顺序有语义的 pins、vertices、ordered_commit_ids 保序。集合按 typed key 排序成数组；非字符串-key table 编成 `{key,value}` records 并按 canonical key bytes 排序。不得默认 JSON coercion 或 Python hash。
- 样张规范字节为 UTF-8、JSON keys lexicographic 排序、无多余空白、ensure_ascii=false、无末尾换行；SHA-256 应对这些 bytes 计算。示例 schema 校验辅助只服务本包，后续需显式产品 encode/decode。
- Artifact `actual_byte_sha256` 对实际文件 bytes，和 `semantic_digest` 分字段。样张如果没有真实产品文件，只存期望文件的 ref/type，不能捏造产品 byte hash；附件 manifest 可列真实样张 bytes 并标 sample objects。

## 正常与失败组合

正常预期：unsealed attempt → raw/schema evidence → proposed → prepared baseline → version 0 snapshot + seal → Stage 3/4 mandatory whole-cell checks → no_change closure（state 不变、空 ECO chain）→ core artifacts/Manifest → ValidationResult → 人机报告/ReportingResult → terminal requires_review。示例 `pass` 表示未来应该观察到的结果，不是本轮运行证据。

| 失败变体 | 必有 / 可有 | 禁止 / publication 后果 |
| --- | --- | --- |
| pre_context | 最小 failure RunRecord、StageFailure、completed neutral audits；diagnostic report 可选 | canonical context、ECO、post-change geometry、ValidationResult 禁止；未建 baseline 不发布 |
| sealed_no_publication | failure RunRecord、StageFailure；stable baseline/planning/constraint refs 随阶段可有 | 无 ECO；baseline 保留；只能 diagnostic report，不能 geometry export |
| run_record_freeze | Stage5Closure(run_record_freeze_failure)、StageFailure、completed audits | 唯一可无 RunRecord；不进入正常 export/ValidationResult；terminal reject；不捏造 failure RunRecord |
| export_failure | 已冻结 no_change RunRecord、StageFailure、stable snapshot；可有 orphan/staging refs | incomplete core set 没有 success Manifest，不能正常 validation；既有 snapshot 不改 |
| check_fail / check_error | 原 RunRecord + Manifest + ValidationResult + StageFailure | 分别 fail / error；required reject；golden match、degraded coverage 不覆盖 failure |
| reporting_failure | 原 RunRecord/Manifest/ValidationResult + ReportingResult + StageFailure | 不改检查结果掩盖报告失败；required report 失败 terminal reject |
| terminal_storage_failure | 原 frozen records + failure diagnostic，可能只有 best-effort observation | 不声称已发布 terminal pointer，不捏造 terminal accept；process-local 不承诺断电恢复 |

`examples/failures.json` 分别给上述记录/ref 组合和有/无 artifact 断言。Stage 6 no_change 的失败仍保留原 no_change RunRecord；空 ECO chain 不能使它倒退成 pre-context failure。显式 partial、重新 seal、unsealed close、未 close 正常 finalize、terminal 后 mutation、同 key 异 digest 均须 typed conflict；同 key 同 digest 重放必须先返回旧 refs，不被后来的 revision/head 变化误拦。

Unexpected programmer/infrastructure error 在 pipeline boundary 变为 InternalStageFailure；KeyboardInterrupt/SystemExit 不吞，crash/OOM/断电不保证当场存在 PipelineResult。本包仅示范错误记录，未实现 repository、terminal publication、原子性或恢复。
