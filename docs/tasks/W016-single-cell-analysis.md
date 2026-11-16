# W016 — 单 cell 只读分析入口实施

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| ID / 目标 | W016；从实际文件完成单个flat cell的只读分析，未选择外部body资料仍输出可认证本地事实及缺项；选择了错误资料则保留实际错误 |
| 里程碑 / 依赖 | M1内既有组件的独立分析入口，承接W005–W014和已接收W015方案；不是完整Stage2/运行出口，不代替后续坐标、mandatory、baseline与Stage6 |
| 授权 | 用户要求推进单cell分析并沿用独立执行session；W015交付后PM核具体方案、review及来源，按既定方向派发本实施包。内部实现自主推进，不重复询问D1 |
| 基线 / 分支 | W015方案merge `d0bb5628384f3a9fec1fe87b6311b854996f574b`；产品仍等同W014验收main `3b8d78902591bca32ec9b8ee5d3167d115e1a974`。恢复`codex/w016-single-cell-analysis`最新远端准备head，后续准备仅文档 |
| 阶段 / 阻塞 | **可执行：产品实施。** W015方案review必须项0；本任务仍需实现独立review及最终验证。当前没有必须用户再选的内部事项 |
| 写入范围 | `layauto_v2/`内本方案涉及的analysis/domain/tech/importers/normalization/annotation/derive/state/reporting及必要public exports；新增/受影响tests、typing配置、README和本任务执行材料。按方案列最小文件表，非相关重构不纳入 |
| 非目标 | 不改固定fixture/答案/历史证据；不改旧公开DTO/schema/wire/ref或完整运行要求；不支持任意层级/生产方言、无query模式、live EDA、可信LVS/窗口验证器、实际修改/发布、完整M1或新持久化wire |
| 架构依据 | [architecture](../architecture.md) §2.2只读分析边界、2.3、3.6、5.6–5.9、11.10/11.13/11.15、12.1；[U06](../roadmap.md#production-body-evidence)、[W015 PM1](W015-single-cell-analysis-entry.md#pm1-acceptance)及下述已采纳方案 |
| 负责人 | PM要求/接收；独立执行session实现；未参与实现者独立review、复核finding |

### 已采纳合同与PM澄清

采纳W015受审冻结`a2d55dbf20c1b07b9f5ca3faddad9c6a8721637b`的
[入口合同](W015/entry-contract.md)、[S1–S7样张](W015/interface-examples.md)和
[实施方案/T01–T10](W015/implementation-proposal.md)，在交付`a73713bc8ff7e1e2d4cc61ab93fbd3ace178753d`
中这些核心文件不变。旧候选文档保留其历史“尚未授权”表述，本任务是首包实施授权；
不能把它推广为真实生产格式或证明已实现。F01/F02关闭及F03/F04澄清见[独立review](W015/independent-review.md)。

- 公开入口`layauto_v2.analysis.analyze_cell(AnalysisRequest)`；独立manifest/header/receipt/result版本，固定`local_readonly`及`dummy_fixture`。GDS/source CDL、query及tech六owner/limitations仍必需；不要求target/export/validation文件，也不生成默认target。外部body显式选择`not_selected`或当前synthetic上下文，人工声明仅预期。
- 顶层`completed/rejected/unsupported`表示分析请求处理，按W015优先级及facet状态聚合，不把`completed`命名为完整验证通过。无body时B观测未知；父级/global首包恒未知。有错已选body、manual或本地错误必须原样定位；错误请求可保留已独立认证的local结果。
- **开始时选择资料；缺项随结果返回。** 首包无运行中交互补文件、挂起续传或自动重试。用户补资料后显式发起新的`analyze_cell`调用，重新获取并认证本次输入；旧结果不可变。若synthetic manifest选择变化使query closure变化，先按显式迁移生成对应新header，不能复用失配闭包或偷偷改证据身份。
- **local是选定cell的分析scope，flat是首包真实capability。** 外部指该scope之外的资料；不指主机位置或工艺层。首包不能展开任意cell层级；reachable hierarchy按现capability定位unsupported，不偷偷flatten。manual的`instance_hint`仅文字提示，不产生受信instance映射。
- domain只冻结Evidence和只读view，normalization拥有完整重parse认证的Receipt。首包只公开顶层分析，不增加可继续计算/持久化receipt API；资源计划中的再次消费仅为内部边界探针，不能据此扩大公共接口。report是诊断view，不能decode回受信状态。
- 显式未来selector `trusted_lvs_freeze/geometry_window` 返回unsupported且不读文件；没有验证器就不声明资料有效。生产冻结、窗口、父级映射、无query查看模式均留后续。
- 方案已有必要review，可按上述范围实施；实际文件表/依赖与状态表先落任务方案区。只对实质偏离既有方案的共享语义做补充方案review，不机械重开整份方案评审；若必须改旧合同或明显扩大状态链，先给具体反例/影响交PM。

### 验收项

| 项 | 输入/条件 → 结果 | 核验与正确性依据 |
| --- | --- | --- |
| A1 无body真实文件闭环 | 实际迁移的manifest/GDS/source/query/tech输入，无target/export/validation/body文件 → 本地source、exact drawn/effective/local graph、FIN、annotation、D/G/S及B未知、缺项/受阻报告 | T01；不能从error ParseResult造success，不能只测内存DTO。正常5/7及六端事实实算，完整source比较indeterminate |
| A2 独立body scope | 选择有效synthetic context → W014现有路径、T04/T05、端子比较保留；local graph/occupancy不变，BN/BP本地仍未知、parent未知 | T02；同来源旧W014逐对象/路径/规则比对，不能抄expected/spec/helper作为观测 |
| A3 错误资料与声明 | 未选、选中缺文件/坏格式/错hash/top/role/几何违例分别处理；manual只显示预期，错绑定及伪assurance字段拒绝；未来selector不IO且unsupported | T03–T05；真实文件反例，保留原code/ref及可独立认证local；不吞未知异常或把违例改unknown |
| A4 本地差异与依赖 | 无body仍保留FIN4对5、partial FIN、query gap/unmatched/conflict；未完成facet有dependency，早期不可信输入local=None | T06；独立手算面积/交叠、几何计数及错误链；source、observed、manual、parent、body分别解释 |
| A5 来源/不可变/补资料 | 捕获一次，纯计算只用实际bytes；同hash异角色/篡改payload/缺raw/alias/错误closure/重复字段/可变backing拒绝。补资料新调用重认证，旧结果不变 | T08及新增两次调用探针；改变manifest需相容header，否则定位拒绝；意外异常及interrupt原样传播 |
| A6 旧接口兼容与层级边界 | 旧read_inputs/W006要求、错误审计/retry，W007–W014DTO/wire/ref保持；新结果不能进旧pipeline/codec。层级超capability定位拒绝 | T07/T09；正常direct/readback/FIN mismatch及错body，旧完整wire/hash parity使用同输入/URI/版本口径；不得靠旧golden更新掩盖变化 |
| A7 资源有界 | 无body正常、有body正常、无body mismatch早期串行记录获取/认证/计算/report耗时、HWM、capture/report大小及构造次数 | T10及下述门；不得隐式多份完整Result嵌套，不跳认证取巧；新report不含raw，不引入全链wire层间传递 |
| A8 工程与独立review | 新增/受影响回归及接口防伪/异常/纯度检查，未参与实现者review并复核必须项；冻结后双3.10/3.12全量、typing、build、双clean安装源码外真实文件smoke | [验证复用](../collaboration/rules.md#verification-reuse)；至少覆盖A1/A2/A3/A4代表路径。完整源码/测试/config/输入/依赖身份及原输出可复用，明确未覆盖生产/EDA |

### 资源检查与执行顺序

按W015步骤先连通T01/S1认证与本地链，再annotation/端子/T06，随后body/manual。
最早可运行就检查相应case，三case齐备后补齐对照，不等最终矩阵才测成本。
PM采纳W015预算门：峰值>1GiB、每facet复制完整capture或认证次数无界增长，暂停扩包交PM；
report去重后>2倍capture bytes也须说明构成并交PM。只有取得同机同输入**同口径**reference
后才使用耗时/HWM>2倍门；原W014 build+encode+decode不能当作新build+report基准。
单case串行超过120秒先交测量、调用图和缩包建议，这是工程复核触发值，不是用户产品超时承诺。
继续做不受阻的诊断/定向修正，不能用删测试或省认证掩盖成本，不重启W012 A2候选。

开发迭代只跑新增及受影响范围；最终产品矩阵按A8一次冻结执行。review/PM换角色不触发
重复双全量/重封大wire；旧wire parity保留两侧源码/输入身份、长度/hash和精确比较方法，
不因已查旧证据就免去本次改动涉及的实际兼容验证。大型路径串行，失败/修复与原证据都保留。

## 方案与决定（执行准备，PM接收）

W015具体方案已采纳。待执行记录实际文件表、旧/新consumer、来源认证与异常路径、
A1–A8测试选择、资源计数方式及相对已采纳方案的差异；无实质变化不重做原则性规划。
生产资料未知遵守[隔离边界](../environment/remote-development.md#隔离生产服务器用户确认的边界)，
不索取raw/PDK/log/hash或默认可反馈pass/fail。新schema仅synthetic分析合同，不宣称生产适用。

## 执行结果（执行）

本轮已进入产品实施，但尚未交付完整入口。实际捕获/重parse认证、source/local/FIN及新annotation
内部链已连通；早期去重诊断report触发资源门，两轮缩减后仍为235613/44873 bytes（5.25倍）。
按任务门暂停body/manual/terminal/API扩包与最终矩阵，完成不受阻的定向防伪修正、58项回归和typing。
实际源码范围、原失败/测量、未完成A1–A8及恢复点见[资源交接](W016/resource-checkpoint.md)，
独立中间review见[review记录](W016/independent-review.md)。PM后续授权将本任务相关源码/测试/独立复核与证据提交推送为未完成检查点；
本轮仅补资源核算和封包，不扩剩余功能、不放宽资源门，不自行验收或合main。

## Review结论（reviewer）

独立 reviewer `/root/w016_review` 完成当前**资源中断检查点**审查，未参与产品实施；
不是 W016 完整实现通过。受审 293 个源码/测试/config 文件绑定
[源码身份](W016/evidence/source-identity.json)，独立逐文件核对无差异；完整结论、
原失败和可复用证据见[独立 review](W016/independent-review.md)。

| Finding | 严重性、影响与依据 | 执行处理及版本 | 独立复核 |
| --- | --- | --- | --- |
| R01 | must：初始 receipt 的 graph walk 未拒绝 nested SourceFile 额外可变字段；实际文件反例可重现 | 改用完整 native storage guard；绑定当前 source-identity | 实际文件反例现抛 ValueError，关闭该反例 |
| R02 | must：新 annotation binding 不在旧 validate_members 重构注册表，draft/view 边界缺新 binding 语义重构 | 显式重构 binding，并在 to_value 重验；同一冻结身份 | forged scope/validity/version 及 to_value 共四断言通过，关闭该反例 |
| 资源门 | 去重报告缩减后仍235613/44873=5.250663倍，超过2倍复核门；不是 raw/完整旧Result重复 | 执行保留构成及缩减前后输出，暂停body/manual扩包和最终矩阵 | 独立核报告hash、长度、1869对象及23 captures一致；交PM复核，不代验收 |

独立实跑基线 normal-direct W007–W014 完整 DTO/wire roundtrip，仅基线准备，**未跑候选双侧parity**；
唯一压缩快照已保留在任务 evidence。其余readback/mismatch/错body路径及最终双版本矩阵未跑。
当前缺顶层API、terminal/body/manual、状态/异常聚合与完整A1–A8，不能提交为完成交付。
执行的定向58项与typing按冻结身份采信；恢复后按实际改动和既定verification-reuse补验。

## PM验收与交接（PM）

W016仅完成任务准备，尚未实施/验收。执行session使用[完整prompt](W016/execution-prompt.md)，
完成独立review及工程交付后回PM；不启动下一任务、合main或删除分支。
