# 候选只读单 cell 合同（A2/A4）

**候选 / synthetic 首包，产品尚不支持。** 本文定义未来实施的推荐方案；
旧 `read_inputs`、W006、全部旧 DTO/wire 保持，不接受此新输入。
状态和样张均不代表生产准入。约束来自架构§2.2/2.3、3.6、5.6–5.9、11.10/13/15、12，
本方案的独立入口须在后续实施任务由PM接收并同步正式文档owner。

## Python 入口与输入

```python
# 候选；不是当前可 import 的代码
from layauto_v2.analysis import AnalysisRequest, analyze_cell
request = AnalysisRequest(manifest_path=Path('/inputs/analysis.json'))
result = analyze_cell(request)  # 不需要repository、run id或tool_run_id
for finding in result.findings:
    display(finding)
if result.local is not None:
    # rejected也可以保留经单独认证的local；逐项看availability与scope
    display(result.local.source, result.local.observations)
# completed也不能传给prepare_inputs、planner、transaction或exporter
```

`AnalysisRequest`是冻结封闭类型，字段只有 `manifest_path: Path`（必须绝对路径）。
其它字段、错误类型、相对路径返回located请求错误；没有 `ignore_body`、
`target_equals_source` 或 `allow_mutation`。manifest内URI相对此文件parent，
遵守旧 `_Files` 的一次实际获取、symlink固定及located读失败边界；不跟随同名文件修复。
新 public facade 所有可预期文件/schema/binding/unsupported返回typed结果；
程序bug、非预期异常、KeyboardInterrupt/SystemExit原样传播。纯normalization/derive不得IO。

候选 `layauto-cell-analysis-request/1` JSON manifest（safe loader规则与旧config相同）：

| 字段 | 必需/默认 | 来源与责任 |
| --- | --- | --- |
| `schema_version` | 必需，固定上述版本 | 严格拒绝未知版本/字段/重复key/float/超size-depth |
| `purpose` | 必需，`local_readonly` | 不提供full_run、修改/发布模式 |
| `mode` | 必需，首包仅`dummy_fixture` | calibre/live/其它方言typed unsupported，不伪造tool |
| `inputs` | 必需，恰含`gds`,`source_cdl`,`query_header`三个非空URI | 选择实际本地文件；cell/top由文件事实获得 |
| `tech_ref` | 必需，URI | 现`w004-tech-bundle/2`；六owner及全validate_tech仍检查，不发明简化规则deck |
| `limitation_ref` | 必需，URI | 现limitations数据及synthetic限制保留，不从中生成答案 |
| `external_body` | 必需，tagged union（含下述future kinds） | `{"kind":"not_selected"}`，或`{"kind":"synthetic_context","uri":"body/context.json"}`；不接受null/空文件代表未选 |
| `manual_intent` | 可省略，默认`{"kind":"not_selected"}` | 或`{"kind":"declaration","uri":"manual.json"}`；只读预期 |

首包query必需。无query请求返回`rejected/MissingField`，可以保留此前安全获取/解析证据，
不承诺此包提供无query的单独GDS查看模式。source、tech、raw/header/identity没有缺省。
本地source profile只支持现flat矩形、literal CDL、one-to-one/single-finger/no-reduction
子集；保留所有drawn记录（含C1/C2/未标注BODY/未知区域），不把几何bbox化或snap。
六owner及body operator声明仍须有效：**没选body文件不等于允许坏tech owner**。

Target/原始操作intent、outputs/export_policy、validation_policy均不是本地分析输入，
若出现则unknown-field错误，不读取它们也不创造target。source设备参数比较与target差异
是两件事：本包仍输出source-vs-measured，`target_comparison=not_requested`。
人工声明不是Stage4 TargetIntent。完整Stage1/运行依旧要求至少一种真实target source和原policy。

## 新 query header 与来源认证

首包新增 `layauto-analysis-query-header/1`，沿用旧header以下**真实字段和约束**：
`header_id/query_run_id/query_database_id/query_database_absence_reason`、
`mode/classification/assurance/lvs_completion_status/lvs_match_status`、
`top_identities/hierarchy_mode/layout/source_netlist`、`tool`、
`query_dialect_version/parser_contract_version/product_parser_version`、
`query_unit/geometry_unit_contract/raw/limitations_ref`，并有`closure`。
每个字段的类型/验证与旧schema相同（header版本除外），没有target字段。
首包只能 synthetic、tool.executed=false/name/version=null、database=null且明确absence，
LVS状态仅not_run或unknown配对；不构造虚拟工具执行记录。parser实际版本由产品记录。

`closure.entries`恰为analysis manifest、GDS/source CDL、tech bundle和六owner、
limitations、requests、dialect的去重实际获取文件；以URI排序、原SHA-256、原compact JSON
算法校验sha256，无unknown dependency；raw另按四capabilities完整逐文件hash校验，
不可与closure/header重复。header自身不入closure；manifest只选header路径，故无hash环。
首包闭包不含target/export/validation/body/manual文件，后两者是另行获取/认证的scope。
manifest虽记录body/manual的选择URI，local认证不证明所选资料正确。
与旧捕获一样，header id/run id不由消费端偷偷改写，query normalized caches（若存在）
必须与重parse raw一致；缓存布局仍header所在目录的normalized/，不能当主事实。

**迁移：** 旧`w004-query-header/2`不能直接喂给新入口；返回
`unsupported/LegacyFullHeaderRequiresExplicitMigration`，旧入口对新版本同样拒绝。
后续实施只为synthetic提供runtime外fixture准备脚本：保留原header/raw bytes和原身份，
输出新local header和新manifest，使用明确新的synthetic header/run id，保留原header
`SourceRef`于迁移记录（不是新header的伪tool身份）；重新计算**实际**本地闭包和cache。
解析raw输出引用新header id，原raw不改。原文件保持。不是从旧error ParseResult恢复成功，
也不是把真实matched工具证据剪裁成更宽松的header；真实profile迁移尚不支持。

新`LocalAnalysisReceipt(schema_version='layauto-local-analysis-receipt/1')`持有一个immutable
capture table、role→source refs（包括第一次URI和获取时固定的alias映射）、解析记录和完整
本地绑定。认证按新规则从**保留的实际bytes**重新解析GDS/CDL、tech、header及全部raw，
逐字段比对payload、SourceRef/field source/record source arity，核URI角色、hash/top、
exact units、profile/operator、dependency closure、query xref/seed/limits/cache；不查磁盘，
不凭hash集合挑角色，不只验证一个digest。alias表是获取事实；新角色不能仅凭alias表
避开首获取URI/格式独特性和声明绑定检查。恶意同hash异角色/改payload/漏raw仍拒绝。

local receipt仅在local解析+认证完成后存在；typed错误在此前则`local=None`，保留完成的
证据但标`unavailable`，不把它们当几何/导通已认证。构造器及公开消费边界重新验证完整
local receipt，不能只信私有布尔标志。外部body/manual各自保留真实bytes和绑定状态，
不复制本地capture，也不成为local事实的认证前提。所选证据错误之后，local仍可成立，
但整个请求不成功。`analysis/report` JSON仅是诊断view，不能decode回受信receipt。

## 结果和判定（精确规则）

候选`AnalysisResult(schema_version='layauto-cell-analysis-result/1')`为discriminated union：

| request_status | 条件 | 允许保留的local/事实 |
| --- | --- | --- |
| `completed` | 支持的请求全部执行完；无读取/格式/绑定/unsupported/致命计算错误、无所选body违例、无error级annotation问题 | 必需local receipt；所有规定本地facet已得到值或显式有据unknown。缺body/parent、正常coverage gap、source FIN mismatch、local T05 violation可以在此，但分别保留，绝不汇总clean |
| `rejected` | 任一输入/绑定错误、选中body几何/规则违例，或本地channel/annotation计算error | findings必有error/violation原因；local仅当独立local认证已完成才保留；受影响facet可含诊断值，标error，不能当可认证测量 |
| `unsupported` | 只有不支持的purpose/profile/input kind/header版本，没有上述rejected原因 | findings必有unsupported；能独立完成local认证则可保留。首包S5请求先完成local分析，再报告selected evidence不支持；禁止把未识别证据用于assurance |

多问题优先级`rejected > unsupported > completed`。正常处理完可检测的独立facet再聚合，
不为了收集更多问题而跨越未满足的依赖。未完成facet列`not_evaluated`和dependency reasons，
不能将未执行编码为pass。未知body/parent是`missing_context`，不是局部输入错误；
有错绑定/已证实违例绝不改为unknown。即使completed也只是分析计算完成。

共同字段（union所有variant都有）：`request_ref`（manifest SourceRef，未读取时为路径位置）、
`captures`（一次byte集合，report只列ref/大小，不含raw）、`local: LocalAnalysis|None`、
`external_body`、`parent_global`、`manual_intent`、`findings`、`missing_context`、
`blocked_operations`、`target_comparison='not_requested'`。不得有snapshot/commit/terminal指针。
`LocalAnalysis`含receipt ref、source及facet，facet为
`{status: available|error|not_evaluated, value, issues, dependencies, scope, evidence_refs}`；
not_evaluated无value且必有依赖，error的value是明确诊断而非成功值。

| facet/列 | 内容来源与状态 | 消费规则 |
| --- | --- | --- |
| source | CDL ordered D/G/S/B、ports/nets、models及所有axes/lexemes/source refs | 只表示source声明，不反推observed |
| drawn/effective/local_graph | GDS exact geometry、tech operators、local T05 | topology依赖几何，不依赖query net label；T05 pass/violation与输入处理状态分开 |
| channel_fin | local+source+query device seeds/derived | FIN实测、差异、未知计数及原因逐项保留，mismatch不变parse错误 |
| annotation | local+query net seeds/derived/capture binding | region/seed/component完整覆盖与冲突；正常gap可available；error级冲突为error并使请求rejected |
| terminals | D/G/S来自channel region→node/component→annotation；B单独来自有效body evaluation | 每端 expected、observed集合、refs、support、equal/mismatch/indeterminate；无body时B的comparison indeterminate，不能抄source |
| parent_global | 首包恒`unknown`：未支持hierarchy pin mapping输入 | synthetic body能关联到本地rail net，也不证明父级/global供电或电压域 |
| external_body | not_selected / error / unsupported / evaluated，另有path/rule/comparison状态 | evaluated不等于production matched；violation导致rejected；不进入local union |
| manual_intent | not_selected / declared / error | 仅预期；显示作者/日期/scope/assertion SourceRef；不覆盖observed或assurance |
| findings | typed `{category,code,source,affected_refs,severity,message}` | category=read/config/parse/binding/unsupported/violation/mismatch/conflict；保留旧组件原因与位置，不能用顶层状态隐藏 |

完整source比较：任一已知测量/端子mismatch→`mismatch`；否则存在缺项、error、B未知或
未完成model/VT等→`indeterminate`。首包最多报告六个D/G/S有限一致或toy八端比较，
永远不报告完整LVS/extraction matched。`blocked_operations`总包含完整run准入、
baseline/no_change、实际修改、发布/export、依赖未证父级/电压关系的exemption；
它是理由清单，不是可被调用方取消的许可flag。可继续只读定位/检查和未提交影响草稿。

## 人工意图与未来证据

首包窄声明文件 `layauto-manual-supply-declaration/1`：`author`非空字符串、`created_at`
UTC时间、`source_layout/source_netlist`实际URI/hash、`cell`、`instance_hint`可空字符串、
`assertions`非空数组，每条恰`device`,`role`（仅B）、`expected_supply_label`字符串。
严格拒unknown/duplicate/超限/缺字段；绑定source/cell/device失败使请求rejected，保留local。
不接受bbox、observed、assurance、tool_status、allow_edit等字段；不新增几何/父级边。
这不是通用生产意图格式，只是候选synthetic分析声明，仍需独立实现review。

S5的selector可被新manifest识别为`trusted_lvs_freeze`或`geometry_window`（仅kind/uri），
首包不读取/解析资料，只返回unsupported并保留selection，不称“验证失败”或“已匹配”。
没有验证器就不能证明它有效；未来需另一个有profile/版本的格式，不能借kind名字自动信任。
证明边界与失效条件见[样张S5/S7](interface-examples.md)，父级映射与body证明是两个scope。
