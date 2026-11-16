# W015 兼容实施方案及首包验收（A4–A6）

**提案，未实施。** 首包目标：实际文件→新local receipt→本地source、drawn/effective、
local graph、FIN、query覆盖/冲突、有序端子与缺项报告；可选当前synthetic body和窄人工声明。
无产品许可前不启动。来源及异常规则见[合同](entry-contract.md)，场景见[样张](interface-examples.md)。

## 不能低估的隐藏耦合与最小分拆

除reader/GeometryInput外，W013 `domain/net_annotation.py::AnnotationBinding`严格要求
`layauto-net-capture-binding/1`且含真实`normalization_input_sha256`和readback结构；
`state/annotation.py::AnnotationDraft`严格要求旧binding类。它**不是任意FrozenMap通道**。
W014 `derive/body_relations.py::evaluate_body`又要求body来源出现在annotation旧capture集合。
因此新链不能把local digest冒名填到旧normalization字段，也不能向已认证annotation后加body。

推荐在旧wrapper之下提取纯operand内核，新链用**新类型**完成scope绑定，旧类仍只接原格式：

1. 获取/认证：新AnalysisParser从manifest获取本地文件，建立明确角色、alias及SourceFile表；
   保留完整typed异常路径。提取reader无IO的header-status/local bindings helpers，参数显式区分
   `full_run`与新的独立schema校验器；不得让旧校验器接受缺字段。shared IO driver不改变旧顺序。
2. source/identity：将semantic `_cells`之上的source构造和`admit_source/join_identities`使用的
   source/tech/header/query/SourceRef输入提成中立显式operand，旧normalize仍构独立target及完整
   differences，新builder只产source/identity/seeds，绝不构NormalizationFacts或NormalizationInput。
3. 几何链：直接用认证的GDS/drawn/formats建layout→partition→occupancy；physical建
   `state/regions.py::build_effective_draft`；rules建`build_local_connectivity_draft`。
   不调用W008–W010完整receipt wrapper，不删local BODY/C1/C2，不修改这些中立DTO。
4. channel：复用`build_channel_identity_draft(local, source, ChannelSeed, derived)`，其输入
   内部一致性与来源闭合由新receipt wrapper核；计量不依赖target或external body。
5. annotation：新增 `AnalysisAnnotationBinding`与`AnalysisAnnotationDraft`（独立版本），
   绑定真实`local_receipt_sha256`、source refs、local/effective/unit/partition refs及全部query seeds。
   从现 `annotation/net_regions.py::build_net_annotation_draft/overlay`、`derive/net_annotation.py`及
   `domain/net_annotation.py::policy_for`/`state/annotation.py`所用算法抽出无receipt的kernel：
   参数为已验证的局部ref、typed source、derived/drawn策略、target集合及source身份集合。
   复用现有NetEvidence/TargetEvidence/fragment/coverage/component等中立leaf（refs按新binding
   内容生成），新binding的校验规则逐项等强保留。**不放宽旧AnnotationBinding/AnnotationDraft**；
   旧wrapper把旧binding投影成kernel operands并重构原DTO，原ref/wire不变。新wrapper重构新DTO。
   必须覆盖全部targets/fragments/coverage/conflict/unmatched/classification和原存储真实性guard，
   不能只写summary或绕过旧DTO验证。新DTO包含新类型就不能混入旧codec。
6. body：保留原`evaluate_body`签名/校验/ref/输出；内部提取一个显式的pure evaluator，接收
   已验证channels、annotation的中立观测投影、body evidence和**有scope的来源绑定集合**。
   旧wrapper仍传原annotation capture集合，旧行为不变；新wrapper传认证local集合＋另行认证
   的body文档/GDS角色，核所有body local_bindings对当前GDS逐对象匹配、profile/unit/frame/类型。
   不修改annotation本地binding或复制重建annotation来塞body；不复用旧Result冒充新receipt。
   共用exact几何predicate和规则算法，外部scope不进入local graph。
7. terminals：从旧`_relations`抽出D/G/S定位、source/observed比较的纯内核，接受channels/
   annotation中立投影及可选的**已评估**body路径；无body的新wrapper显式构B indeterminate。
   旧TerminalRelationsDraft仍要求每device body path及旧binding，旧refs/wire输出逐字兼容。
   新AnalysisTerminal记录用新binding ref，不能作为旧TerminalRelationsDraft传入。

以上提取是为两个有独立证据合同的wrapper共用算法；不是引入一个可随意标trusted的通用receipt。
若实际验证表明必须更改旧DTO/wire、复制旧链才能做新annotation，或本拆分不能有界完成，
停在具体调用图/失败反例交PM缩包，不用伪成功receipt走捷径。

## 最小文件改动表（未来，不是本轮diff）

路径以现模块边界为准，新增名称候选；实施可合并小文件，但职责不合并。

| 路径/符号 | 最小改动/旧责任保持 | 必须验证 |
| --- | --- | --- |
| `layauto_v2/domain/analysis.py`（新） | request/result/local receipt、facet/finding、external/manual状态；独立schema版本 | union非法组合、nested alias/forged字段、refs/角色完整性 |
| `layauto_v2/tech/analysis_schema.py`（新） | manifest/local header/manual封闭schema和跨字段校验；导入config的schema dispatch只增加新kind | 旧site/header拒新格式，新kind不调用validate_tech的宽松分支 |
| `layauto_v2/importers/analysis_reader.py`（新）、`reader.py`、`config.py` | 新读取流程及shared acquisition/local-binding helpers；旧InputParser/read_inputs顺序与失败不改 | 真实文件、异常原样、一次获取、path/limits/symlink、所选证据错误 |
| `normalization/analysis_input.py`（新） | 本地receipt重parse认证；独立external认证/诊断；不依赖repository | raw/tech/source/payload篡改、角色替换、URI alias/ref/hash/arity、错误completed可信边界 |
| `normalization/semantic.py`、`identity.py`及必要`_validation.py`helper | 提取source-only内核，旧完整validate_parse/KINDS不放宽 | 原source/target diff/ordered terminal/identity拒绝保持 |
| `domain/analysis_annotation.py`、`state/analysis_annotation.py`（新） | 独立annotation binding/draft及等强完整重构校验 | 新capture binding不能冒旧normalization，report不能回灌 |
| `annotation/net_regions.py::build_net_annotation_draft/overlay`、`derive/net_annotation.py`及`domain/net_annotation.py`/`state/annotation.py`内部helper | 纯算法提取到本owner内kernel；旧DTO构造器/schema/fields/version不变，新wrapper自己验证 | exact fragments/coverage/conflict，旧dto/wire/digest parity，native存储guard |
| `derive/body_relations.py`、`derive/terminal_relations.py` | 抽纯operand内核，保持旧公开wrapper严格签名和行为；新增analysis wrapper放analysis模块 | 无body不evaluate；有body角色/scope核；旧八端/vi例/alias/forged refs保持 |
| `normalization/analysis.py`（新） | 纯编排一次source/local/channel/annotation/body/terminal，不调用完整W011/W013/W014 Results | 新receipt唯一来源；逐facet依赖与聚合状态 |
| `reporting/analysis.py`、`analysis.py`（新） | 顶层facade只串获取→纯分析→报告对象；新JSON view不编码raw、不decode成受信receipt；不隐式写文件 | 外部无union、无运行发布API，调用者在结果中取值 |
| `tests/unit/test_analysis_*.py`、`tests/contracts/test_analysis_*.py`、`tests/support/analysis_inputs.py`（新）、相关typing清单 | 显式synthetic输入准备，新schema迁移记录；旧fixture不改，helper不生成观测oracle | S1–S7与来源/旧接口回归；正确性另有手算及旧结果独立对照 |
| 正式owner文档/实施任务记录 | PM接收方案后同步架构分析边界、公开入口文档、验证证据 | 不通过执行记录静默覆盖架构 |

targets和classifications现由`annotation/net_regions.py::build_net_annotation_draft`构建；
不得因提取helper而跨层import。新`domain/`不依赖importers/state，构造器的capture认证编排位于normalization；
冻结neutral receipt数据形状位于domain。typed trusted边界采用normalization的认证wrapper，
不能在domain内import解析器来取得认证。公共analyze_cell不暴露未认证结果构造捷径。

## 兼容矩阵

| 现行入口/类型/消费方 | 实施后承诺 | 防错误混用 |
| --- | --- | --- |
| read_inputs / InputParser / ParseResult `/1` | 完整字段、顺序、错误、捕获/完成记录不变 | 新manifest不进旧解析；不从error构success |
| prepare_inputs / InputsReady / W006审计与retry | 不改，不接分析结果；完整运行仍必需body/target/policies | 无仓库/attempt/context/checkpoint/terminal写入 |
| NormalizationInput/Facts/Result `/1`及semantic codec | fields/strict version/target differences不变 | 新source-only facts不冒其类型；旧codec拒新DTO |
| GeometryInput/GeometryResult及W008–W010 codecs | 旧完整认证及body_evidence不变，旧wire/ref稳定 | 新链只复用中立计算，不新增optional body到旧DTO |
| W011/W013公开build与result/codec | 重构内核前后相同输入完整DTO、wire/digest相同 | 新annotation binding独立，不重标旧normalization hash |
| W014 build_terminal_relations、TerminalRelationsDraft/Result/codec | 原body强制、路径/规则/比较与ref不变 | 新B unknown不注入旧draft；旧codec拒新analysis aggregate |
| new LocalAnalysisReceipt/result/report | `/1`新版本，report仅view，独立local与external refs | 不能进入run/planner/transaction/export；首包无executable wire decoder |

异常：底层InputError/SchemaError等只在相应reader/认证边界转located finding，保留原code/ref。
中立ChannelProblem/AnnotationProblem/BodyProblem按实际依赖保留，未知异常和process interrupts
不兜底成body unknown。scope外关联不得创建edge；所有实质几何规则/单位/模型来源不变。

## 第一实现包顺序与验收门（A5）

1. 冻结基线，先落新schema/真实文件读取/认证和S1 smoke；移走target/export/validation/body
   **文件本身**仍能从新manifest完成来源认证；旧read_inputs/W006仍拒缺必需body。
2. source-only identity与neutral几何链连通后立即做S1正常及坏raw/tech/GDS/CDL探针，不等待report
   美化。与旧同captured本地图逐对象/单位/policy/ref依据对照；refs因新binding而不同须解释。
3. 做新annotation wrapper与D/G/S/B未知报告；跑S6手算面积、conflict和FIN 4对5。测资源后再扩包。
4. 接入可选旧synthetic body和manual声明，完成S2/S3/S4；S5 unsupported和S7类型边界。没有
   external文件、所选坏文件、所选有效但违例必须是不同结果。
5. 独立review关键来源/旧兼容/反例、闭合must；冻结源码/测试/config后按项目最终产品矩阵执行，
   再交PM做接收/实际集成组合。本轮不运行这些未来矩阵。

| 验收ID | 实际未来测试，不以mock parse或oracle代替 | 对应 |
| --- | --- | --- |
| T01 | 临时实际文件缺target/export/validation/body；本地全链结果+缺项。source所有axes仍有来源，无target对象 | S1,A2,A5 |
| T02 | 有效toy body与旧W014同来源逐path/rule/terminal parity；local graph/occupancy不变、BN/BP未知、parent未知 | S2,A4 |
| T03 | 未选/丢失/坏syntax/错hash/top/role、body wrongtype/ambiguous/disconnected/enclosure/wrongrail真实输入；local保留＋顶层reject；instance未知字段拒绝 | S3,A4 |
| T04 | 只manual→declared；不改任何observed/body/parent；坏绑定/伪assurance字段拒；CDL/source意图分别显示 | S4 |
| T05 | 两future selector→unsupported，确认未IO/未验证；未来schema/instance概念不冒作当前支持 | S5 |
| T06 | FIN4对5；query partial/gap/unmatched/conflict手算；partial FIN/多channel/device seed缺失；GDS非矩形/单位冲突/CDL表达式/原raw缺terminator/hash/tech operator错误 | S6,A1,A4 |
| T07 | full_run/修改purpose拒；分析值不是旧receipt/publication DTO，不能发布；旧完整reader/W006缺body的错误及审计/重试不变 | S7,A4 |
| T08 | 捕获后改磁盘不影响纯分析；每actual path只读一次，symlink/alias角色错误；伪SourceRef/同hash换角色/少raw/改payload/重复记录/mutable backing/多余字段拒；unexpected异常与interrupt原样 | A4 |
| T09 | 旧W007–W014同source直接/readback/FIN mismatch完整DTO/wire/digest parity，正/错body均覆盖；边界依赖tests | A4,A6 |
| T10 | 三个早期case阶段耗时/HWM/captured/encoded bytes与调用计数；report单capture，无旧多Result嵌套，serial cold重建边界计数有界 | A6 |

旧source/target差异、closure、终结错误、codec存储真实性和annotation错误路径是重构的直接影响，
定向回归覆盖这些，不按任务号盲选测试数。最终矩阵仍双Python3.10/3.12全量＋typing＋build/
双干净安装来源外实际文件smoke；依赖/原始输出/版本/输入身份随Git交付。review/PM按
[verification-reuse](../../collaboration/rules.md#verification-reuse)核身份采信、补关键反例与集成组合。

## 资源计划（A6）

旧W014正常路径图：完整W010receipt→roundtrip认证→normalize→neutral channel一次＋
neutral annotation一次＋body一次；公开encode/decode还会重构和再认证，不能只计helper。
原R4 direct/readback/mismatch原样本约61.894/114.963/61.919秒、196.40/491.91/204.29MiB，
新增wire约345944/345944/344703 bytes；仅引用[原资源记录](../W014/resource-review.md)，
不是本主机复测或新入口预算保证。W012 A2未集成，不复活候选优化。

新路径目标：每actual文件一次获取→一次local full-byte认证→共享中立source/local graph→
channel一次/annotation一次→可选body一次→terminal/report。normalization消费公开receipt时
需再次认证就明确计数；neutral构造器完整一致性重建不能跳。无隐式全链encode/decode做
层间传递；不同时持有W011/W013/W014完整Result。report的captures为单表，facet只存ref，
raw仅在receipt capture表一份；中立对象共享引用，编码view不递归复制其local/effective链。
不靠省来源检查提速；若新binding需要编码，先只有exact canonical binding digest，不新增
可持久化全链wire。复杂性能优化另立任务。

首次可运行T01/T02/T06立刻串行测三case：无body正常、有body正常、无body FIN mismatch。
记录同主机/解释器/依赖/输入/源码hash/limits；分别计获取/认证/中立计算/report时间与
`ru_maxrss`、capture去重bytes、report bytes、认证与neutral builder次数；同case再消费已有
receipt观察重建次数。不产生大wire拷贝、不并行重链；记录估计与实测分别。
预计顶层正常一次分析的channel/annotation/body（若选）各一次，认证读后一次、公开重新消费
一次；neutral内部防伪重构次数另列，不能混称总成本为一次。

提议早期退回PM门（方案预算，不是既有性能承诺）：同机同输入串行时间或HWM超过旧W014
公开build+report可比路径2倍、峰值>1GiB、report去重后>2倍capture bytes、或发现每facet
复制完整capture/认证次数随facets增长，暂停扩包/最终矩阵，交调用图、测量/失败及缩包方案。
没有可比旧路径时不得伪造倍率，使用绝对1GiB/重复capture/无界次数门并说明不足。
通过门只允许继续工程，不代表性能优化、最大输入或生产支持。

## 最小生产资料调查表（不向外索取保密内容）

| 未知 | 未来内网调查项目/最小脱敏结构问题 | 现在的限制 |
| --- | --- | --- |
| OS/CPU/Python/离线依赖 | 由内网操作者核安装可行条件，允许反馈什么另行确认 | 不能从cloud Python推目标机可用 |
| 实际CDL/几何/query方言 | 先描述数值脱敏后的字段结构、单位表示、层级/终止符/引用关系；是否准许反馈这些格式需守用户边界 | 无raw/PDK/log/hash上传；不承诺parser |
| query来源身份/trust | 内网核deck/options/transitive closure/tool/database/match字段是否存在及如何绑定 | 仅synthetic/not_run，live及G1–G4/G5未通过 |
| cell/pin/父级/global | 格式能否表达instance/pin map/domain及版本scope，不询问实际网名/数值 | 首包parent/global未知 |
| 无tap替代证明 | 内网核可信baseline覆盖对象/invariant或窗口边界完整性是否可表达 | 首包仅unsupported |
| 内网验收回执 | PM先确认能否反馈公共代码版本/测试编号/通过失败类别 | **不能默认允许外传pass/fail、结果、日志或hash** |

当前只记录未知，不要求上传任何生产材料。真实证据可留内网，不从脱敏格式或本地synthetic
成功推断真实matched、生产准入或修改能力。
