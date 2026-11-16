# W015 候选输入输出样张（A3）

以下全部为**人工构造、synthetic、候选预期**，不是新入口的实跑输出，也不是通用PDK格式。
Python入口/字段/状态以[entry-contract](entry-contract.md)为准。
用`@gds/@cdl/@query/@tech/@body/@manual`作为表格中的SourceRef缩写，实施后必须替换为
实际URI、SHA-256及field/record位置；这些符号不是合法hash，不得作为可执行fixture证据。

## 共用最小请求与来源

```python
AnalysisRequest(manifest_path=Path('/tmp/w015-demo/analysis.json'))
```

`/tmp/w015-demo/analysis.json`候选内容：

```json
{
  "schema_version": "layauto-cell-analysis-request/1",
  "purpose": "local_readonly",
  "mode": "dummy_fixture",
  "inputs": {
    "gds": "source.gds",
    "source_cdl": "source.cdl",
    "query_header": "query/local-header.json"
  },
  "tech_ref": "tech.json",
  "limitation_ref": "limitations.json",
  "external_body": {"kind": "not_selected"}
}
```

这是新manifest，不是改写现site_config.yaml。目录实际需要同源GDS/CDL、tech六owner、
limitations、local-header、requests/dialect及raw四capabilities；只有新版本来源认证后才
形成结果。首包验收使用现W003捕获的**临时副本和显式迁移生成的新header**，不读取答案。
完整可检查的[候选manifest](evidence/candidate-input/analysis.json)、
[header](evidence/candidate-input/local-header.json)与[来源记录](evidence/candidate-input/provenance.json)
已随本任务保存，生成规则见[合同](entry-contract.md)；不能把上面manifest直接
传给旧reader。无target/export_policy/validation_policy文件，仍能形成新本地闭环。

代表source片段（引用现source.cdl语义，独立手读）：

```spice
.SUBCKT INV_M1_SYNTH A Y VSS VDD
MN0 Y A VSS VSS TOY_N NFIN=5 NF=1 M=1 L=4n W=2n VT=toy
MP0 Y A VDD VDD TOY_P NFIN=7 NF=1 M=1 L=4n W=2n VT=toy
.ENDS INV_M1_SYNTH
```

| 输出字段 | 必须来自哪里 | 示例说明 |
| --- | --- | --- |
| source.ports/device.terminals/parameters | @cdl field_sources + @tech model axes | MN0 ordered D=Y/G=A/S=VSS/B=VSS，5/1/1/4nm/2nm/toy全部保留 |
| drawn/effective/local_graph | @gds XY/REAL8及record + @tech operators/rules | raw DRAWN不删，CUT只作用LI，S/D不union，BODY独立 |
| channel_fin | @gds FIN与OD/channel + @query device_info/xref + @tech | 5和7是候选正常计数，不能来自CDL填充计量答案 |
| terminals D/G/S | 几何channel定位 + node/component + @query net region/xref | 只表示有限local支持，保留实际coverage和冲突 |
| B support/body rule | @body绑定、exact路径/规则 + 本地rail annotation | source B不是observed B；选择的external证据独立 |
| parent_global | 首包无受信父级来源 | 即使本地叫VDD/VSS或body成立也unknown |
| manual_intent | @manual原声明 | expected标签，不是观测 |
| findings/missing_context/blocked_operations | 实际stage与依赖推导 | 不由golden/helper抄入事实 |

## S1：只提供底层 cell、无外部选择

输入用共用请求；manual默认未选择。代表输出摘录（`…`只表示省略完整refs/逐层coverage，
可审报告必须能展开；不是允许省略合同字段）：

```text
request_status: completed
scope: local cell INV_M1_SYNTH, flat, synthetic source_evidence
local.source: ports [A,Y,VSS,VDD]; ordered source terminals as above [@cdl]
local.facets.channel_fin: available; MN0 measured=5/source=5, MP0 measured=7/source=7 [@gds,@query,@tech]
local.facets.terminals:
  MN0 D: expected Y, observed [Y], equal; G: A/[A]/equal; S: VSS/[VSS]/equal
  MP0 D: expected Y, observed [Y], equal; G: A/[A]/equal; S: VDD/[VDD]/equal
  MN0 B: expected VSS, observed [], support indeterminate, comparison indeterminate
  MP0 B: expected VDD, observed [], support indeterminate, comparison indeterminate
local.facets.annotation: available; all region coverage/gaps/unmatched seeds retained; BN/BP local net unknown
parent_global: unknown (instance, child-pin mapping, global/domain evidence absent)
external_body: not_selected; assurance unknown; no local graph union
manual_intent: not_selected
target_comparison: not_requested
source_comparison: indeterminate (B + full model/VT extraction not proved)
missing_context: [parent_instance_mapping, global_voltage_domain, body_path_proof, remaining_mandatory]
blocked_operations: [full_run_admission, baseline, no_change, geometry_commit, export_publish,
                     parent_voltage_exemption]
```

可以读取local facet做只读几何/连通/FIN/query定位、coverage报告、已有局部规则检查。
六端一致也不能称八端或完整提取匹配；unknown几何仍blockage/suspect，不自动归网。
现W014正常本地图14node/8edge/6component只是历史同样本参考，未来新链须对同一GDS
逐对象证明相同，不能把数字直接写死作为产品计算。

## S2：无独立tapcell GDS，选择正确的synthetic外部上下文

最小请求差异：

```json
{"external_body":{"kind":"synthetic_context","uri":"body/context.json"}}
```

以上是对完整共用manifest的字段替换，非独立JSON manifest。body文件用现
`w004-synthetic-tapcell-context/2`绑定当前GDS/top/profile/unit/frame和对象。
其人工选择ref不产生物理edge；必须运行现W014 exact几何/规则评估的兼容内核。

代表输出：`completed`；local source/六端/FIN/coverage保持S1；BN/BP本地component仍unknown；
`external_body={status:evaluated, scope:external_readonly, paths:established,
T04_body:satisfied, T05_contact_enclosure:satisfied, claim_comparison:equal,
assurance:synthetic_only, production_matched_body_evidence:false, lvs_status:not_run,
local_graph_union:false}`。两B observed分别VSS/VDD仅在external scope有支持，
八端toy comparison可equal，完整source/model/LVS比较仍indeterminate。
`parent_global=unknown`，同名rail不证明上层供电、domain或access；被阻操作仍保留。

## S3：未选、选错、违例逐类对照

所有变体都用同一可认证本地输入，只替换`external_body`选择/对应外部文件。
body不在local closure内，所以外部读/解析失败不妨碍local认证；manifest变更必须有新local
header闭包绑定（synthetic准备步骤显式生成）。不以旧header hash失配替代真正待测错误。

| 输入变体 | 顶层状态、外部结果及原始原因 | local能否消费 / 受阻 |
| --- | --- | --- |
| `{kind:not_selected}` | completed；not_selected/missing_context | S1可读，只读；body未知不是违例 |
| `{kind:synthetic_context,uri:missing.json}`不存在 | rejected；error，read/SelectedBodyUnavailable（附URI，无伪造hash） | local保留；不自动挑同名body或把选择清掉 |
| body文件为`{` | rejected；error，parse/InvalidDocumentSyntax，实际捕获ref | local保留；不调用body几何 |
| body.source_gds.sha256指向旧GDS | rejected；error，binding/BodySourceBindingMismatch，期望实际ref | local保留；同top/bbox/网名不能修复 |
| 已选body的top不同 | rejected；error，binding/BodySourceBindingMismatch/top | local保留；没有body支持 |
| instance绑定错 | 首包toy格式不支持instance字段：rejected/UnknownField；不声称验证TOP/U8对TOP/U7 | local保留；未来带instance的受信格式必须typed binding error，见S5 |
| tap enclosure不足（已认证body文件） | rejected；evaluated，violation，保留精确四向margin/threshold/affected refs与W014原issue code | local保留；有几何路径不等于规则pass |
| body断链/错型/错rail/歧义 | rejected；保留现W014实际issue、chain/rule/claim三状态 | local保留；已知错误不能降unknown |

路径缺失在读取边界；结构坏在parser；top/hash/role错在认证；几何问题在评估。
不靠catch-all把四者统一成“未选择”。若本地也有问题按依赖分别报告，见S6。

## S4：只有人工供电意图

共用manifest加入`manual_intent={kind:declaration,uri:manual.json}`，external仍not_selected。
窄声明文件代表字段（source_layout/netlist的sha256必须是实际hash，以下ref为展示缩写）：

```text
schema_version: layauto-manual-supply-declaration/1
author: demo-engineer
created_at: 2026-11-16T00:00:00Z
source_layout: @gds
source_netlist: @cdl
cell: INV_M1_SYNTH
instance_hint: TOP/U7
assertions:
  - {device: MN0, role: B, expected_supply_label: GND1}
  - {device: MP0, role: B, expected_supply_label: PWR1}
```

输出`completed`，`manual_intent.status=declared`，显示原声明及@manual逐字段ref；
expected GND1/PWR1不改source VSS/VDD，expected/observed/parent分列。两B仍indeterminate，
父级/global仍unknown，缺项/阻止同S1。手工标签与source名字不同仅展示跨scope意图，
不能无parent mapping就断言short或equivalent。声明绑定错则rejected，local可保留。

## S5：未来可信LVS冻结 / 最小几何窗口

首包能识别两种selection，但无验证器，均`unsupported`，**不读取文件、不核SHA、不信内容**。

```json
{"external_body":{"kind":"trusted_lvs_freeze","uri":"extract-42.bundle"}}
```

或`{"external_body":{"kind":"geometry_window","uri":"body-window.bundle"}}`。
代表输出：`unsupported/UnsupportedExternalEvidenceKind`；local各facet同S1，
external_body.status=unsupported、selected URI保留、assurance unknown；parent/global未知；
可继续只读local，所有依赖受信证明的操作受阻。不是selected-not-found，也不是已验证生产证据。

未来证明合同的具体反例与要求（均不进入首包生产schema）：

| 路径 | 最小绑定及scope | 可证明 / 不证明 | 失效/拒绝例 |
| --- | --- | --- | --- |
| 可信baseline LVS冻结 | layout/source transitive closure、top、instance/层级变换、deck/map/runset/options/model/tool/profile版本、database/run、完成与matched原证据、覆盖body/active/boundary/halo对象、允许变化集和每候选保持证明 | 只在获信scope内提供冻结body assurance；不凭“LVS passed”补图形，不证明缺失的parent mapping | 布局h0而当前h1、TOP/U8而请求U7、body/active/导体/边界/halo/变换变化、提取依赖更新、无逐候选invariant证明→受影响assurance失效/重验；不可静默沿用 |
| 最小几何窗口 | 同源对象身份/版本、原坐标/units/transform、body→tap→rail完整路径和必要local pin、窗口边界/halo完整性、tech/rules/operators | 独立external path与规则，只在声明scope；不增local union、不自动证明global电压 | 窗口边缘截断路径、缺tap/enclosure partner、错对象/坐标、旧hash/instance→缺完整性或绑定错误；不得把截断当open已证实 |
| 父级pin/global关系（另一个证据域） | 指定TOP/U7的child pin→parent net→global/domain实际来源及依赖闭包 | 经受信格式核绑定后才能报告映射；有映射不证明body物理路径，body有效也不自动有映射 | TOP/U8 mapping、缺domain版本、仅人工标签→不建立观察关系 |

有效期不以时间窗口替代内容绑定；任何相关输入/版本/affected scope变化使受影响证明失效。
真实格式、trust authority和隔离环境验收均未确定，不能在首包里默认接受。

## S6：缺body仍保留本地差异/缺口/错误

| 变体（body都未选） | 候选结果 | 依据及可继续/不可继续 |
| --- | --- | --- |
| FIN完整几何只剩4条合格crossing，source MN0仍5 | completed；measured=4/source=5，source_comparison=mismatch，B indeterminate另列 | 独立计数4≠5；继承W011语义。保留每FIN qualification和位置，不能以target/source或body unknown覆盖差异 |
| query net区域未盖满局部端区 | completed；annotation available但gap；terminal observed/支持按实际component seed计算，不能推断满覆盖 | 人工微例target `[0,0,10,4]`面积40，seed `[0,0,6,4]`面积24，uncovered=16；这是overlay手算子例，不是完整fixture结果。是否足以支持某端必须按refs判断 |
| 两不同net query seed在同一exact区域相交 | rejected；annotation error，保留诊断fragment/component conflict，terminals受影响indeterminate/conflict | 手算两个seed `[0,0,6,4]`和`[4,0,10,4]`交叠面积8；不能后写覆盖，不能改physical graph；local source/geometry仍可看 |
| device query不完整、ambiguous channel/partial FIN | rejected；保留channel/identity原issue；不能认证的计数unknown，依赖端子not_evaluated | 不从source期望补齐；与body缺证明分列 |
| 原始raw少terminator/错误hash、GDS非矩形、CDL表达式/未知model、unit冲突 | rejected；local=None，已读/已parse证据按完成顺序保留，未成receipt | 这些早期错误使本地闭包尚不可认证；只能看diagnostic evidence，不声称已有local graph/FIN。unsupported方言单独归unsupported，已知坏格式为rejected |

完整首包回归要把这些手算/反例做成真实临时输入与重新绑定header，用相同parser走到结果；
本轮仅合同样张和旧链probe，不把未运行新链当通过。

## S7：完整运行、修改/发布及超范围

输入`purpose=full_run`（或未知modify）→首包`unsupported/UnsupportedAnalysisPurpose`，
不尝试转旧运行。调用旧`read_inputs(site_config.yaml)`且缺body仍按旧schema/读取错误；
旧W006失败审计、required policy、target及完整mandatory均保持。

拿S1/S2 completed结果直接交transaction/exporter→类型拒绝：它没有run/context/snapshot/
PreparedPublication，不是修改许可。首包不提供edit/publish API。
未来若冻结body证明后改active、boundary、相关rail/connector/halo，或换GDS/source/deck/
model/query版本，则受影响证明invalidated，要求重新认证/提取/完整性及mandatory检查。
不直接编辑tap并不能证明不影响body；新query不得覆盖旧snapshot；通过只读分析不产生
baseline、no_change、terminal、production admission，不能绕过G1–G4/G5。
