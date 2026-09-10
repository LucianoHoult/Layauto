# W003 人工核验清单（PM）

先确认“这套题和答案是否正确、是否是你希望程序处理的样子”，再开始产品实现。例如 N/P 的目标仍为 5/7，程序应保持几何和电路语义，检查全部 toy 规则；即使数字相同，间距错也必须失败。

本页由 PM 维护人工核验记录，来源为 [W003](../W003-m1-fixture-contracts.md) 已独立 review 的固定交付。坐标、规则、格式和错误类别的来源仍是原 fixture/spec/oracle/contracts；下表仅是方便逐项阅读的展示，不是新的 oracle 或产品合同。用户尚未进行本轮确认，所有状态均为**待确认**。

## 核验版本与方法

- 跨平台审核分支：`codex/w003-manual-review`，材料提交 `01535055f5d661a2964443dec76fc7f7f305e3e0` 已推送；本页及其图、原始输入、期望输出、负例、合同与报告均随分支保存。直接按下方链接阅读，不需要本机临时目录或先运行辅助脚本。发布不代表用户已确认。
- 基线：`main@b1f0301cf76b2e1808cb293cfdb4e1bfededde73`。
- 固定接收包：`/private/tmp/layauto-w003-independent-review-i8gqzwtw`；`full.patch` SHA-256 为 `c03a90b4f49c51a2343d54ad110420801d7b39966f6f5b6ec34c7b5b8fd1178f`。
- 独立 review 的 2 项 P2 已修复并复核关闭，0 项未关闭实质 findings；这是本地 synthetic 样本/合同技术结论，用户确认、W003 最终验收及产品运行分别记录。
- 建议依次核验 A → B → C → D；可以回复“编号：确认 / 需修改（期望）/ 未决（疑点）”。“确认一组”只覆盖该组明确列出的项目，不外推到其余材料。
- PM 记录答复和受影响版本，执行者解释或修正；有改动先串行修正、复核相关技术证据，再确认受影响项。没有变化的材料不机械重做。

## A. 正常版图、电路与独立答案

![正常例坐标图](fixture-layout.png)

图仅辅助阅读。以下逐形状、连通和规则表分别摘自 [spec](../../../tests/fixtures/w003_m1/spec.json) 与 [手写 oracle](../../../tests/fixtures/w003_m1/oracle.json)，技术 review 已另用独立 reader/整数算法核对实物 GDS。

| ID | 需要逐项确认的事实与使用预期 | 用户状态 |
| --- | --- | --- |
| A1 | 同一 inverter，固定 160×200 nm；nominal 1 nm 整数 tick。两器件 single-finger、one-to-one、无归并；NFIN=5/7、NF=1、M=1。W=2n、L=4n、VT=toy 仅为 toy 模型解释。source/target 全部语义相同，允许文字/参数顺序不同 | 待确认 |
| A2 | 下表全部 44 个 drawn rectangles；18 根 FIN 保留，N 计 F01–F05，P 计 F07–F13，其余 6 根不计。每个 qualified crossing 为 4×2=8 nm²，总面积40/56 nm² | 待确认 |
| A3 | 下表全部10个 connector edges、8个端子、6个物理连通分量和禁止直接相连的对象；S/D 关系不是导线，body 通过显式 BTAP 接 rail | 待确认 |
| A4 | CUT 把 LB 分成两岛，二者都标 A，却彼此及与真实 A gate 均不连通；MARK 是未注释非导体。**建议保留为拓扑/覆盖披露测试，但它是带刻意孤岛的 synthetic 工程正例，不表示完整生产 LVS 匹配**。是否符合你对“正常例”的使用预期需确认 | 待确认 |
| A5 | 下表 T01–T10 是这个 toy 的全部 required 检查；N/P 数字相等也必须执行。未知 context→indeterminate/reject，执行错误→error/reject；不允许 site policy 禁用 | 待确认 |

### A2 的全部形状

坐标顺序 `[x0,y0,x1,y1]`，单位均为 nominal nm；表中 F 编号按原身份排列，非按 y 排序。

| Shape | Layer | 矩形坐标 | FIN 计数归属 |
| --- | --- | --- | --- |
| FRAME | BOUNDARY | `[0, 0, 160, 200]` | — |
| BN | BODY_N | `[0, 0, 120, 90]` | — |
| BP | BODY_P | `[0, 100, 120, 200]` | — |
| ON | OD | `[20, 20, 100, 70]` | — |
| OP | OD | `[20, 110, 100, 180]` | — |
| G | POLY | `[58, 10, 62, 190]` | — |
| F01 | FIN | `[10, 24, 110, 26]` | MN0 |
| F02 | FIN | `[10, 34, 110, 36]` | MN0 |
| F03 | FIN | `[10, 44, 110, 46]` | MN0 |
| F04 | FIN | `[10, 54, 110, 56]` | MN0 |
| F05 | FIN | `[10, 64, 110, 66]` | MN0 |
| F06 | FIN | `[10, 84, 110, 86]` | 不计入器件 |
| F07 | FIN | `[10, 114, 110, 116]` | MP0 |
| F08 | FIN | `[10, 124, 110, 126]` | MP0 |
| F09 | FIN | `[10, 134, 110, 136]` | MP0 |
| F10 | FIN | `[10, 144, 110, 146]` | MP0 |
| F11 | FIN | `[10, 154, 110, 156]` | MP0 |
| F12 | FIN | `[10, 164, 110, 166]` | MP0 |
| F13 | FIN | `[10, 174, 110, 176]` | MP0 |
| F14 | FIN | `[10, 194, 110, 196]` | 不计入器件 |
| F15 | FIN | `[10, 74, 110, 76]` | 不计入器件 |
| F16 | FIN | `[10, 94, 110, 96]` | 不计入器件 |
| F17 | FIN | `[10, 104, 110, 106]` | 不计入器件 |
| F18 | FIN | `[10, 184, 110, 186]` | 不计入器件 |
| LN | LI | `[28, 30, 34, 55]` | — |
| LP | LI | `[28, 130, 34, 155]` | — |
| LY | LI | `[84, 30, 90, 165]` | — |
| LB | LI | `[130, 20, 150, 24]` | — |
| CUTB | CUT | `[139, 18, 141, 26]` | — |
| CNS | CONTACT | `[29, 40, 33, 44]` | — |
| CND | CONTACT | `[85, 40, 89, 44]` | — |
| CPS | CONTACT | `[29, 140, 33, 144]` | — |
| CPD | CONTACT | `[85, 140, 89, 144]` | — |
| VN | VIA0 | `[29, 50, 33, 54]` | — |
| VP | VIA0 | `[29, 150, 33, 154]` | — |
| VY | VIA0 | `[85, 92, 89, 96]` | — |
| GC | GCONTACT | `[59, 92, 61, 96]` | — |
| TN | BTAP_N | `[8, 50, 12, 54]` | — |
| TP | BTAP_P | `[8, 150, 12, 154]` | — |
| MN | M1 | `[0, 48, 45, 58]` | — |
| MP | M1 | `[0, 148, 45, 158]` | — |
| MA | M1 | `[50, 90, 75, 98]` | — |
| MY | M1 | `[80, 90, 110, 98]` | — |
| MARK | MARKER | `[145, 180, 150, 185]` | — |

### A3 的连接与端子

Connector 必须对声明两侧各恰好一个导体有正面积交集，另检查每侧至少 1 nm enclosure。同层只允许正面积重叠或正长度共边产生连接，角接触和网格邻接不导通；网名不生成物理边。

| Connector | 直接连接的两端 |
| --- | --- |
| CNS | ON.S ↔ LN |
| CND | ON.D ↔ LY |
| CPS | OP.S ↔ LP |
| CPD | OP.D ↔ LY |
| VN | LN ↔ MN |
| VP | LP ↔ MP |
| VY | LY ↔ MY |
| GC | G ↔ MA |
| TN | BN ↔ MN |
| TP | BP ↔ MP |

| Device / terminal | 物理 region | Component | Net |
| --- | --- | --- | --- |
| MN0.D | ON.D | C_Y | Y |
| MN0.G | G | C_A | A |
| MN0.S | ON.S | C_VSS | VSS |
| MN0.B | BN | C_VSS | VSS |
| MP0.D | OP.D | C_Y | Y |
| MP0.G | G | C_A | A |
| MP0.S | OP.S | C_VDD | VDD |
| MP0.B | BP | C_VDD | VDD |

| Component | Regions | Net |
| --- | --- | --- |
| C_VSS | ON.S, LN, MN, BN | VSS |
| C_VDD | OP.S, LP, MP, BP | VDD |
| C_Y | ON.D, OP.D, LY, MY | Y |
| C_A | G, MA | A |
| C_A_island_left | LB.left | A |
| C_A_island_right | LB.right | A |

以下每对均**没有直接边**：ON.S ↔ ON.D；OP.S ↔ OP.D；LB.left ↔ LB.right；LB.left ↔ G；BN ↔ BP；BN ↔ ON.S；BP ↔ OP.S。BN 与 ON.S、BP 与 OP.S 仍分别通过共同 rail 间接相连。

### A5 的规则逐项答案

| Rule | 适用对象/答案（全部为 toy 预期 pass） |
| --- | --- |
| T01.frame | all 43 non-frame drawn shapes |
| T02.fin_grid | 18 FIN rectangles |
| T03.recognition | MN0, MP0 |
| T04.body | ON in BN, OP in BP, BN disjoint BP, TN connects BN to MN, TP connects BP to MP；minimum_active_enclosure_ticks=10 |
| T05.contact_enclosure | CNS, CND, CPS, CPD, VN, VP, VY, GC, TN, TP；minimum_enclosure_ticks=1 |
| T06.li_spacing | all 10 unordered pairs of 5 effective LI rectangles, geometry_only, no same-net exemption；minimum_distance_ticks=2 |
| T07.m1_spacing | all 6 unordered pairs of 4 M1 rectangles, geometry_only；minimum_distance_ticks=5 |
| T08.terminal_graph | 8 terminals, 10 connector edges, 6 components and listed non-edges |
| T09.lifecycle | all 44 drawn records; no ECO; preserve/frame equality |
| T10.coverage | all drawn/effective regions |

## B. 正常文件链、格式与单位

[文件合同](contracts.md) 定义双方 owner 和支持/拒绝子集；[fixture README](../../../tests/fixtures/w003_m1/README.md) 定义具体语法，不能只看示例恰好读通。所有原始文件均可从以下链接展开；本组与 C 共同覆盖75个fixture文件。

| ID | 文件入口 | 核验与待确认的预期 | 用户状态 |
| --- | --- | --- | --- |
| B1 | [source.gds](../../../tests/fixtures/w003_m1/source.gds)<br>[source.cdl](../../../tests/fixtures/w003_m1/source.cdl)<br>[target.cdl](../../../tests/fixtures/w003_m1/target.cdl) | 单cell、flat、仅含BOUNDARY矩形的GDS；完整 CDL top/pins/D G S B/model/NFIN/NF/M/L/W/VT。当前拒绝 hierarchy/property/TEXT/非矩形及 CDL include/表达式等，不静默丢弃或猜值 | 待确认 |
| B2 | [query/raw/instance_xref.txt](../../../tests/fixtures/w003_m1/query/raw/instance_xref.txt)<br>[query/raw/net_xref.txt](../../../tests/fixtures/w003_m1/query/raw/net_xref.txt)<br>[query/raw/device_regions.txt](../../../tests/fixtures/w003_m1/query/raw/device_regions.txt)<br>[query/raw/net_regions.txt](../../../tests/fixtures/w003_m1/query/raw/net_regions.txt) | 四 capability 数量2/4/2/10；I/N/D/R、x,y 整数坐标、nm、COUNT、END。**建议作为本地合成语法保留，真实 Calibre dialect 另用允许披露的格式核实**；接受本例不证明生产文本能被解析 | 待确认 |
| B3 | [query/header.json](../../../tests/fixtures/w003_m1/query/header.json)<br>[query/normalized/instance_xref.yaml](../../../tests/fixtures/w003_m1/query/normalized/instance_xref.yaml)<br>[query/normalized/net_xref.yaml](../../../tests/fixtures/w003_m1/query/normalized/net_xref.yaml)<br>[query/normalized/device_regions.yaml](../../../tests/fixtures/w003_m1/query/normalized/device_regions.yaml)<br>[query/normalized/net_regions.yaml](../../../tests/fixtures/w003_m1/query/normalized/net_regions.yaml) | 从 raw 重解析并核对 normalized；header 绑定同源 bytes/top/closure/version，synthetic/not_run 与工具未知值如实呈现。normalized 不是替代 raw 的输入通道，net index 前导零保留 | 待确认 |
| B4 | [tech.json](../../../tests/fixtures/w003_m1/tech.json)<br>[site_config.yaml](../../../tests/fixtures/w003_m1/site_config.yaml)<br>[export_policy.json](../../../tests/fixtures/w003_m1/export_policy.json)<br>[validation_policy.json](../../../tests/fixtures/w003_m1/validation_policy.json)<br>[limitations.json](../../../tests/fixtures/w003_m1/limitations.json) | toy registry/model/body/operator/T01–T10 明示；site 路径相对其文件，策略不放宽物理要求。正常 requires_review，required failure reject；未实现 resize/live/真实 PDK | 待确认 |
| B5 | [expected/output.gds](../../../tests/fixtures/w003_m1/expected/output.gds)<br>[expected/output.cdl](../../../tests/fixtures/w003_m1/expected/output.cdl)<br>[expected/layout.json](../../../tests/fixtures/w003_m1/expected/layout.json)<br>[expected/unit-provenance.json](../../../tests/fixtures/w003_m1/expected/unit-provenance.json) | 输出语义保真而不强制 GDS bytes 相等；REAL8 half-ULP 仅解释单位编码，不能移动 XY。expected GDS 原 KLayout UNITS 曾超界，仅 UNITS 被规范化且原始值留档；layout JSON 是最小 component/fragment 展示，后续产品必须生成完整 snapshot，不能照样张删省 | 待确认 |
| B6 | [README.md](../../../tests/fixtures/w003_m1/README.md)<br>[spec.json](../../../tests/fixtures/w003_m1/spec.json)<br>[oracle.json](../../../tests/fixtures/w003_m1/oracle.json) | 本页 A 的全部 shape/crossing/graph/rule 展示与源表一致；spec 是制作说明、oracle 是手写答案，均不作为 future runtime 绕过真实输入链的最终状态 | 待确认 |

## C. 全部22个输入反例

每例以正常fixture为底，严格应用 [cases.json](../../../tests/fixtures/w003_m1/failures/cases.json) 的 `replacement_files` 和 `remove_files`；链接目录可查看全部替换输入。19例已重绑定配套header/raw/cache，只有 raw_byte_drift、header_top_mismatch、normalized_cache_drift 故意保留绑定错误。无需每例重复核对未改形状，但须核对全部替换/删除项及错误原因。

所有案例的**未来产品**断言均为 terminal reject、0 个 ECO commit、无正常 export manifest。P=pre_context（未seal，无正常几何导出）；S=sealed_no_publication（保留稳定baseline，无ECO/正常几何导出）；E=export（保留既有no_change RunRecord和snapshot，导出失败不生成成功manifest）。这些是未来断言，当前辅助检查并未运行产品失败管线。

| ID / case | 人工检查的局部差异 | 期望问题 / phase | 用户状态 |
| --- | --- | --- | --- |
| C01 / [unit_mismatch](../../../tests/fixtures/w003_m1/failures/unit_mismatch/) | source GDS unit改成2nm，与声明的1nm源单位不符；配套header已重绑定 | `UnitScaleMismatch` / P | 待确认 |
| C02 / [missing_terminator](../../../tests/fixtures/w003_m1/failures/missing_terminator/) | instance raw删END；删除旧normalized缓存，失败样张也引用此坏raw | `MissingTerminator` / P | 待确认 |
| C03 / [wrong_count](../../../tests/fixtures/w003_m1/failures/wrong_count/) | net xref实际4条，COUNT写5；删除旧缓存 | `CountMismatch` / P | 待确认 |
| C04 / [dialect_drift](../../../tests/fixtures/w003_m1/failures/dialect_drift/) | device region的RECT改BBOX，不得当作精确矩形接收；删除旧缓存 | `UnsupportedGeometryToken` / P | 待确认 |
| C05 / [unknown_unit](../../../tests/fixtures/w003_m1/failures/unknown_unit/) | net region单位nm改mystery；删除旧缓存 | `UnitBindingMismatch` / P | 待确认 |
| C06 / [raw_byte_drift](../../../tests/fixtures/w003_m1/failures/raw_byte_drift/) | net raw索引042改043，header/hash不更新（故意错误） | `RawHashMismatch` / P | 待确认 |
| C07 / [header_top_mismatch](../../../tests/fixtures/w003_m1/failures/header_top_mismatch/) | header source top改WRONG_TOP（故意错误） | `TopBindingMismatch` / P | 待确认 |
| C08 / [mapping_many_to_one](../../../tests/fixtures/w003_m1/failures/mapping_many_to_one/) | Q17/Q93都映射MN0，违反一对一 | `UnsupportedDeviceCardinality` / P | 待确认 |
| C09 / [multifinger](../../../tests/fixtures/w003_m1/failures/multifinger/) | MN0 NF=1改NF=2 | `UnsupportedFingerCount` / P | 待确认 |
| C10 / [device_reduction](../../../tests/fixtures/w003_m1/failures/device_reduction/) | 增加Q18→MN0的第三条映射，需归并解释 | `UnsupportedDeviceReduction` / P | 待确认 |
| C11 / [cdl_expression](../../../tests/fixtures/w003_m1/failures/cdl_expression/) | NFIN=5改成NFIN={2+3}；数值等价也不支持表达式 | `UnsupportedCdlExpression` / P | 待确认 |
| C12 / [cdl_include](../../../tests/fixtures/w003_m1/failures/cdl_include/) | 添加.INCLUDE private_model.cdl；本例是合成字符串，没有私有文件 | `UnsupportedDependencyDirective` / P | 待确认 |
| C13 / [unsupported_target](../../../tests/fixtures/w003_m1/failures/unsupported_target/) | target MN0 L=4n改5n；5/7不变也不是no_change | `UnsupportedTargetAxis` / S | 待确认 |
| C14 / [count_correct_rule_wrong](../../../tests/fixtures/w003_m1/failures/count_correct_rule_wrong/) | MY左边80改79，M1间距5→4nm；FIN仍5/7 | `MandatoryRuleViolation:T07.m1_spacing` / S | 待确认 |
| C15 / [via_enclosure](../../../tests/fixtures/w003_m1/failures/via_enclosure/) | VN由[29,50,33,54]移到[33,50,37,54]，超出LN enclosure | `MandatoryRuleViolation:T05.contact_enclosure` / S | 待确认 |
| C16 / [extraction_mismatch](../../../tests/fixtures/w003_m1/failures/extraction_mismatch/) | ON上边70改64，物理N计数4而CDL仍5；P仍7 | `ExtractionCountMismatch` / S | 待确认 |
| C17 / [gds_text](../../../tests/fixtures/w003_m1/failures/gds_text/) | 加入当前子集不支持的TEXT记录，不能丢弃 | `UnsupportedGdsElement:TEXT` / P | 待确认 |
| C18 / [gds_nonrectangle](../../../tests/fixtures/w003_m1/failures/gds_nonrectangle/) | 加入非矩形几何，不能使用bbox冒充保真 | `UnsupportedNonrectangle` / P | 待确认 |
| C19 / [output_nonrepresentable](../../../tests/fixtures/w003_m1/failures/output_nonrepresentable/) | 输出DBU选择2nm，源中奇数坐标无法精确表达；不round | `OutputCoordinateNotRepresentable` / E | 待确认 |
| C20 / [output_overflow](../../../tests/fixtures/w003_m1/failures/output_overflow/) | 输出DBU选择1e-9nm，坐标超GDS 32-bit范围；不截断 | `OutputCoordinateOverflow` / E | 待确认 |
| C21 / [normalized_cache_drift](../../../tests/fixtures/w003_m1/failures/normalized_cache_drift/) | 仅缓存中A改Y，raw不变（故意错误） | `NormalizedCacheMismatch` / P | 待确认 |
| C22 / [missing_body_operator](../../../tests/fixtures/w003_m1/failures/missing_body_operator/) | 从tech删除body/1必需算子 | `RequiredBodyOperatorUnavailable` / P | 待确认 |

覆盖核对：B列出24个正常/说明文件，C包含索引及全部替换输入；去重后恰为75个实存fixture文件，无遗漏或额外文件。C的错误类别拼写沿用cases.json，产品enum尚未由本页发布。

## D. 共享记录、正常产物与失败报告

这组检查“需要看到什么”和“失败时不能看到什么”。20条正常记录、8类失败组合以及人机报告全部是 expected/example，尚无产品 run。它们不是另外8个几何fixture，也不能当作已经运行出来的日志。

| ID | 核验对象与使用预期 | 用户状态 |
| --- | --- | --- |
| D1 | [schema](examples/schema.json) 与 [contracts](contracts.md)：owner、typed id/ref、必需/可选/禁止字段、exact值编码、哈希对象。仅作为实现前样张；产品CLI/wire发布需下一任务明确，不把阅读认可扩展为生产API冻结 | 待确认 |
| D2 | 下表20条 [records](examples/records.json)，逐条能沿ref找到前因后果；create-attempt摘要绑定run/head/实际输入选择，未seal不提前声称canonical context；baseline初始化与ECO分开 | 待确认 |
| D3 | [人读报告](examples/report.expected.md)、[机器报告](examples/report.expected.json) 与B5的GDS/CDL/JSON：能解释输入、5/7、几何/拓扑/规则、没有ECO、bytes与语义差异、未覆盖项与requires_review；不能只列edit数量 | 待确认 |
| D4 | 下表8类 [failures](examples/failures.json)，逐条核对允许/禁止的记录及artifact。Required fail/error/export/report failure始终reject；只有manifest不能认定生产可消费 | 待确认 |

### D2 的20条记录

| 序号 | Kind / variant | 样张ID | 用户状态 |
| --- | --- | --- | --- |
| D2.01 | ToolRunResult | fixture-read | 待确认 |
| D2.02 | ParseResult | query-parse | 待确认 |
| D2.03 | EvidenceRecord | evidence | 待确认 |
| D2.04 | ImmutableContext | context | 待确认 |
| D2.05 | LifecycleAuditRecord | lifecycle | 待确认 |
| D2.06 | ProposedInitialState | proposed | 待确认 |
| D2.07 | RunAttempt / unsealed | attempt-unsealed | 待确认 |
| D2.08 | PreparedBaseline | prepared | 待确认 |
| D2.09 | Snapshot | baseline-0 | 待确认 |
| D2.10 | InitializationEvent | init | 待确认 |
| D2.11 | RunAttempt / sealed_open | attempt-sealed | 待确认 |
| D2.12 | PlanningAuditRecord | planning | 待确认 |
| D2.13 | ConstraintAuditRecord | mandatory | 待确认 |
| D2.14 | NoChangePlanningResult | no-change | 待确认 |
| D2.15 | RunRecord / no_change | run-record | 待确认 |
| D2.16 | Stage5Closure / with_run_record | closure | 待确认 |
| D2.17 | ArtifactManifest | manifest | 待确认 |
| D2.18 | ValidationResult | validation | 待确认 |
| D2.19 | ReportingResult | reporting | 待确认 |
| D2.20 | PipelineResult | terminal | 待确认 |

### D4 的8类失败组合

| ID / variant | 必须看见的结果 / 不得伪造的结果 | 用户状态 |
| --- | --- | --- |
| D4.1 / pre_context | 最小failure RunRecord、StageFailure与已完成audit；缺terminator引用真实坏raw；无canonical context/ECO/正常geometry/ValidationResult | 待确认 |
| D4.2 / sealed_no_publication | failure RunRecord、StageFailure，稳定baseline按阶段可有；无ECO，只可diagnostic report | 待确认 |
| D4.3 / run_record_freeze | Stage5Closure记录freeze failure；唯一允许无RunRecord的例外，无正常export/ValidationResult，不编造RunRecord | 待确认 |
| D4.4 / export_failure | 原frozen no_change RunRecord和snapshot保留，可有orphan/staging；核心产物不全则无成功Manifest/正常validation | 待确认 |
| D4.5 / check_fail | 原RunRecord+Manifest+ValidationResult+StageFailure，检查确认为fail，required则reject | 待确认 |
| D4.6 / check_error | 记录检查执行error，不能当fail/pass或以golden匹配掩盖，required则reject | 待确认 |
| D4.7 / reporting_failure | 保留既有检查结果，加ReportingResult/StageFailure；required报告失败则reject | 待确认 |
| D4.8 / terminal_storage_failure | best-effort失败诊断；不能声称terminal pointer已发布，不能编造accept或断电恢复证明 | 待确认 |

## 确认记录与下一步

| 批次 | 状态 | 答复/决定与受影响版本 |
| --- | --- | --- |
| A 正常例与独立答案 | 待确认 | 尚无用户答复；A4需明确确认带孤岛的工程正例定位 |
| B 文件链与格式 | 待确认 | 尚无用户答复；B2的synthetic语法、B5的最小JSON及单位来源需要按具体样张理解 |
| C 全部22负例 | 待确认 | 尚无用户答复；以C01–C22为范围，不按抽样通过 |
| D 记录与报告 | 待确认 | 尚无用户答复；D2/D4需覆盖全部明细 |

全部组确认且相关修正经review后，PM才决定W003最终验收及后续M1 parser/输入绑定任务。这里不创建或授权实现任务；W003辅助reader不作为产品parser上传。平台、Python/离线依赖、可外传信息和内网真实验收回执由PM另行协调，不用本地synthetic结论代替。

## 展示来源身份

下列hash绑定本页摘录的源材料，用户答复引用本页编号时同时绑定本节版本；若源文件改变，先更新展示和受影响确认记录。完整75文件身份仍以固定包snapshot/manifest为准。

- [spec.json](../../../tests/fixtures/w003_m1/spec.json)：SHA-256 `bcfe2e34460d49a5a77619b4cf8884b8004786ffe50bb7d2efd25a59a8409505`。
- [oracle.json](../../../tests/fixtures/w003_m1/oracle.json)：SHA-256 `6268db9090251f9a7ed7a562e0ad62e919304cef9da3edf09fae747cc5f03191`。
- [failures/cases.json](../../../tests/fixtures/w003_m1/failures/cases.json)：SHA-256 `036f9f84966cd7eda2f6738e3dbd53e7f4fca5b0dd3290402f3df20dab13cb77`。
