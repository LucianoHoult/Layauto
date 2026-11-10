# W012 — 完整捕获、wire 与重复重建性能优化

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| ID / 目标 | W012；降低真实组件组合中完整捕获保留、wire 编解码和重复认证/重建的耗时与内存，保持可审计来源及公开验证合同 |
| 里程碑 / 依赖 | M1 工程支撑，关联 R13/R27/R28；承接 W011 的明确稳定版本，优先于继续扩大状态链/输入。W011已由PR #65验收集成，见其PM2；本次先派发P1/P2调查 |
| 授权依据 | 用户明确要求：开发阶段先跑新增及受影响范围，最终交付再跑双全量；PM 单列完整捕获、wire 膨胀和重复重建优化任务，不能只减少测试数量 |
| 当前阶段 / 阻塞 | **可执行：仅兼容A1实施，派发要求独立复核必须项0，PM已接收。** P1/P2已验收，产品优化未实施；不批准B新格式、writer/reader/memo或整体降幅承诺，见 [PM1](#pm1-investigation)及[A1](#a1-implementation) |
| 恢复 / 分支 | A1从调查接收提交 `9b573c99d5f4021636f498292f42b53540bff1a1` 建立 `codex/w012-compatible-hex-validation`；接手含A1派发记录的最新head。原调查分支`codex/w012-capture-wire-performance`保留，产品runtime仍等同已验收main `0a3326aa363477724465886cd05874d0997fba3e`/W011冻结源；本轮准备不合main |
| 本次允许写入 | A1仅 `layauto_v2/domain/codec.py` 的bytes hex校验及直接必要的tests；本任务执行/方案区、W012下新的A1方案/验证/性能/review附件。不要覆盖P1/P2原测量工具、原输出、报告或finding；不改其它runtime、正式fixture/答案、架构或current-work。PM维护阶段/范围，reviewer维护其结论 |
| 约束 / 非目标 | 保留原始 bytes、来源/单位/owner/run 绑定、不可变性、公开 constructor/codec 完整验证和异常历史；不修改 fixture/答案、语义计量或生产输入要求，不扩展 body/U06 或物理能力。测试调度/并发 gate 本身不算本任务的性能成果 |
| 架构依据 | [architecture](../architecture.md) §2.2–2.3、§2.6、§3.7–3.8、§11.2/11.9/11.15；[协作规则](../collaboration/rules.md)的最终验证与证据要求；W005–W011 的来源、不可变 DTO、codec 和错误合同 |
| 分工 | PM 收敛目标与派发；执行者提供 profile/方案和实现；未承担设计/实现者分别复核方案与最终正确性、性能证据 |

### 已有基线与需要解释的成本

W011 原资源测量每个 case 含 31 份捕获、共 280,706 B，40 条 drawn records、18 FIN。以下来自[原资源回执](W011/resources/receipt.json)，经 [PM 核对](W011/pm-receipt.md)，不是本任务新测值：

| 完整 Result 路径 | wire bytes | 整进程峰值 RSS KiB | W011 build / encode / decode 秒 |
| --- | ---: | ---: | --- |
| normal direct | 54,050,313 | 2,847,416 | 37.209 / 1.522 / 46.759 |
| normal readback | 136,461,405 | 7,322,828 | 74.948 / 3.064 / 101.861 |
| extraction_mismatch | 54,049,506 | 2,854,456 | 35.419 / 1.397 / 45.179 |

原 constructor 认证包含于 build/decode，尚未独立计时；RSS 包含上游构造、imports、原对象和 wire，不能归因于 W011 增量分配。长矩阵 3.10 另有 9,257,804 KiB 采样高点，不能与 fresh-process 峰值混用。以上说明需要调查成本，不足以单独证明每类瓶颈及其占比。

### 准备与验收方向

| 项 | 要完成的可核对结果 |
| --- | --- |
| P1 成本定位 | 固定同一捕获、解释器、环境和对象保留顺序，区分获取、build、认证/重建、encode、decode；记录重复引用/bytes 贡献、调用次数、wire 大小及 fresh-process 峰值。不能只看整套 pytest 总时长或假定全部成本来自测试数量 |
| P2 方案与目标 | 对实际瓶颈提出可审阅方案和可复现基线；再收敛具体性能目标、预计影响及验证方式，经独立方案 review 后才派发实现。不凭空承诺百分比；如改内部 wire/refs，说明 schema 版本、兼容范围、digest 和迁移影响；涉及关键外部行为/格式或架构变化时按协作规则带具体材料交用户决定 |
| A1 正确性保持 | 正常 5/7、mismatch 实际4对source5、partial/未知范围及原图/body/T05事实保持；source/target 不混。所有捕获、来源及实际消费 owner 可解析、完整且绑定，不能用省略证据、调用方 trusted 标志或只比 hash 替代必须验证 |
| A2 边界保持 | 公开 constructor/codec 仍拒绝伪造/漏项/错型等值 scalar、跨捕获拼装和可变别名；原异常 object/cause/context/suppression、预期错误后二次故障和单次集合快照合同保持。若使用认证复用/cache，明确作用域、完整 key、失效规则及防绕过验证 |
| A3 性能实证 | 同条件前后分别运行完整 direct、完整 readback、原 mismatch，报告时间、wire、峰值、重复工作变化及退化；审查改善是否来自实际减少冗余。原脚本/数据/版本保留，不能把中立 draft、热缓存、不同捕获 URI 或不同对象保留范围冒充同条件完整 Result 对照 |
| A4 工程交付 | 开发时先新增及受影响范围；最终冻结后双解释器全量、typing、构建/干净安装与来源/异常负例按实际接口完成。记录选择依据和最终源身份；不将少跑测试、删断言或并发门控当成单次成本下降 |

当前没有新的输入使用预期需用户立即决定。A1只更换既有bytes hex校验的内部算法，不改变wire合同；20%/50%仍为整体兼容包建议而非A1硬门，新格式B须另备具体兼容/身份/迁移材料后再决定。

### 原 P1/P2 派发与完成判据（已交付并接收）

原阶段交付是调查和可实施方案，已由PM1接收；上表A1–A4为整体兼容优化方向。以下保留原PP1–PP5要求，本次实施范围以末尾的A1实施验收I1–I6为准。

| 项 | 本次须交付的证据 |
| --- | --- |
| PP1 冻结与测量计划 | 核对main起点、100runtime/262源与W011冻结等价；单独hash测量工具。固定输入URI、读取/cache模式、RunRequest、对象保留/GC顺序及环境，说明三条完整路径的断言。先完成轻量工具自检和测量计划，再运行重型组合 |
| PP2 无插桩新基线 | 三条完整路径各用fresh进程、串行完成build/完整encode/decode及真实结果断言。至少保留完整crossing、正常5/7、mismatch实际4对source5且恰一项差异、原局部图/T05/body及readback attempt/checkpoint不变/无terminal。保存每阶段时间、wire实际bytes/hash及整进程峰值；不要求把巨大wire本身重复提交Git |
| PP3 独立profile与成本分解 | 将基准与profile分开运行。统计完整捕获/重复引用/bytes/wire展开的贡献、公开constructor/认证的调用次数及exclusive/cumulative时间。区分共享Python对象、内容相同独立对象及wire按值重复展开；明确不能归因部分，不把inclusive时间相加为总耗时 |
| PP4 具体实施方案与目标建议 | 按实测瓶颈排序，给出推荐改动/owner、预期收益、数值目标建议及同条件前后验证方法；列正确性/来源/异常防线、wire版本兼容/digest/迁移影响及退化风险。提出具体建议，不能只重复“以后优化”或未经测量宣称全部来自单一瓶颈 |
| PP5 独立review与交接 | 未承担测量工具/方案设计者核对测量扰动、输入/源码/工具身份、结果断言、瓶颈及目标依据、正确性和兼容边界；所有必须项修正复核并保留原finding。交PM后停止，不自行实施优化、验收、合main或启动后续任务 |

测量安排：

- 原W011基线只作历史参照，不冒记为本机新测。可核对并复用其source snapshot及原probe思路，测量工具身份另存；完整输入/RunRequest使用固定位置，尤其mismatch overlay避免每次临时目录改变来源URI。未来前后对照保持相同捕获与保留范围。
- 检查本机资源和已有进程，重型baseline/profile串行。记录获取、各层build、W011 build、完整encode/decode；插桩结果仅用于归因，不作为无插桩性能基线。按数据需要有限重复，不机械重跑或并发小时级矩阵。
- hook中不额外encode、digest巨大对象、repr/asdict/deepcopy；优先读取已有长度、计数或有限标识。对象id只作进程内诊断，不成为持久内容身份。ru_maxrss不作函数前后差值归因，采样与整进程峰值分开。
- 从代码可调查的线索包括bytes的hex表示、下层完整wire作为bytes再次嵌入、Result多个分支重复保留捕获，以及builder/constructor/codec的重复认证。上述仅是待测假设，贡献由实际profile给出；不得为测量改写原runtime或绕过公开验证。
- 本次runtime不变，按源身份采信W011已验收双全量、typing和包/安装，不为调查文档/工具再跑小时级双矩阵；须实际运行工具自检和三条完整路径并独立复核。未来优化实施按协作规则：开发先新增/受影响，最终冻结仍双全量及必要工程验证。

## 方案与决定（执行准备，PM 接收）

本轮P1/P2调查已实际执行，产品优化未实施。[冻结测量计划](W012/measurement-plan.md)、[成本分析](W012/cost-analysis.md)及[具体实施方案/目标建议](W012/implementation-proposal.md)已形成；独立review结论归下段及其报告，不由执行者代写。推荐先处理保留 `/1` 格式的hex校验峰值和canonical/typed pack临时复制，保留公开constructor/codec认证及异常历史；新的自包含表格式单列待PM/用户决定，附旧decoder拒绝及digest/ref迁移实例，不默认批准。

## 执行结果（执行）

独立执行session从远端PM准备 `f3698b7ffda3b0737a2eb61ca85dbf3b40bc89fe` 恢复，main起点 `0a3326aa363477724465886cd05874d0997fba3e`。262源/100runtime与W011冻结 `e89bdaa6a091f56cfaf7862dced7232d34e22514` 逐项一致；按身份采信原双1605、typing54及构建/双安装，本次未重跑小时级矩阵。仅W012工具/证据/方案与本执行区改动；runtime、公开DTO/codec、正式测试、fixture/答案、架构和current-work不改。

| 判据 | 本轮实际证据与结果 |
| --- | --- |
| PP1 | [preflight](W012/preflight.json)及轻量[selfcheck](W012/selfcheck.json)通过；固定输入URI、原cache模式、RunRequest、GC与保留顺序。原工具冻结 `cfaf85e195fcbedb99fbd26b19787afb0577862d`，后续诊断工具独立hash/自检。原轻量自检错误预期与一次轮询transport中断均保留，未覆盖失败 |
| PP2 | 三条fresh、串行完整公开构造/encode/decode全部通过，见[六路命令回执](W012/measurement-receipt.json)。正常5/7、mismatch实际4对source5且一项差异、完整36项evaluation/crossing、来源/局部图/T05/body、readback unsealed/checkpoint不变/无terminal均核验。无插桩阶段总计91.922/187.952/88.231s，wire54,050,313/136,471,701/54,045,042B，峰值2,859,772/7,327,952/2,850,888KiB |
| PP3 | 独立profile三路全部通过，wire/captures与基线相同，详见[原始分解](W012/cost-summary.json)。区分唯一/同内容/逻辑展开bytes，outer hex约99.9%，W011 build两次完整认证累计约92–94%但与下层时间嵌套；domain.codec disjoint exclusive约51–52%。另完整readback[内存补测](W012/memory-profile-normal-readback.json)将最终7,319,108KiB峰值定位到既有118,841,892字符hex正则调用窗口，不当净分配；未额外编码大对象 |
| PP4 | [具体方案](W012/implementation-proposal.md)列owner/实施顺序、作用域/key/失效、来源/不可变/异常防线、攻击面、退化和wire兼容/digest影响。建议兼容A总耗时至少降20%/峰值至少降50%且 `/1` bytes/hash不变；可选B完整wire≤20MB/45MB/20MB。均为有依据的目标建议，未批准、未实现、未作收益承诺 |
| PP5 | 交未参与工具/方案设计的 `/root/independent_review` 独立复核，受审快照及最终findings由reviewer记录在下段。PM接收后再决定实施，本轮不验收/合main/改current-work/启动后续任务 |

[轻量证据核验](W012/validation.json)396项通过（非产品回归数量）；原W011工程证据21条命令原输出hash、262源、六路串行/工具/输出身份、补测身份和完整wire相等均实际核对。更广partial/未知、T05 violation、来源/异常攻击负例按同源W011采信，三条固定输入不冒记覆盖所有负例。所有原输出/失败、工具和命令随W012目录交付，最终提交/远端完整SHA在Git交接中实核。下一步仅交PM接收P1/P2。

### A1 执行结果（待PM核验）

本独立执行session从PM准备 `7f7c1304bdafd941791421cef64864fb1616303c` 恢复，先核远端/身份/规则并形成[最小方案](W012/A1/plan.md)，经未参与设计者[方案review](W012/A1/plan-review.md)后实施。产品/测试冻结为 `ca1f810c3c97376f71089d8b4054760ff198012f`；after的263源/测试/配置随后未变。唯一产品改动是原bytes分支改用非重复分组hex校验并后判偶数长度，仍先调用matcher，原fromhex、canonical重编码与全部认证边界保留。详细原输出/中断与恢复定位见[执行记录](W012/A1/execution.md)。任务阶段与接收仍由PM维护。

| 项 | 本轮实际结果与证据 |
| --- | --- |
| I1 | 空bytes、小写ASCII偶数hex接受语言及全部非法/canonical边界已核；新增51项正式合同测试，另有方案review的独立有限语言见证。见[开发原命令](W012/A1/development-commands.json)，原测试未改/删 |
| I2 | 18个fresh完整公开三路径样本逐块比较实际wire，所有before/after bytes、大小、hash/ref一致；schema `/1`、公开签名、encoder和全部捕获不变。见[性能回执](W012/A1/performance/receipt.json)；新旧profile构造/认证调用次数相同 |
| I3 | matcher/fromhex原异常object/cause/context/suppression、嵌套公开codec及W011二次故障、来源/错型等值/别名范围经开发273项及最终双全量验证；未扩大捕获/重包异常。原finding及本轮工具问题的复现/关闭均由独立review保留 |
| I4 | 同机同环境、固定URI/RunRequest/cache/roots/GC，三路径每侧3个fresh串行无插桩样本全部完成。direct/readback/mismatch中位耗时下降19.72%/22.80%/14.66%，整进程峰值下降88.59%/90.35%/88.65%，各次/小阶段增幅见[完整分析](W012/A1/performance-analysis.md)。独立profile的65个大hex窗口长度/顺序一致，峰值刷新5→0；不将profile耗时混入基准 |
| I5 | 固定mismatch35项按原清单重建核源，正常5/7、实际4对source5/恰一项差异、完整36项FIN/crossing、原图/来源/局部图/T05/body与target独立保持；readback unsealed、attempt/checkpoint不变且无terminal。见[preflight](W012/A1/preflight.json)、逐样本原输出及双安装smoke |
| I6 | 最终双解释器各1656 passed，原1605个node ID全保留；双strict typing各54源文件、构建、sdist3.10/wheel3.12全新安装源码外完整组合smoke通过，21条命令exit0，见[工程回执](W012/A1/verification-r2/receipt.json)及[实际前后包](W012/A1/package-comparison.json)。代码/正确性/性能独立结论由reviewer维护于下段 |

本轮wire减幅为0；20%/50%仍不是A1硬门或收益承诺。新版profile仍有720,336KiB整进程峰值，最后matcher窗口之后的余量未作allocator逐函数归因，具体边界已记录交PM；未扩到writer/memo或新格式。完成后仅推送原A1分支交PM，不自行验收/合main、改current-work或启动下一子项。

## Review 结论（reviewer）

独立 reviewer `/root/independent_review`（未承担测量工具/方案设计）已完成[PP1–PP5调查与方案复核](W012/independent-review.md)，受审base `f3698b7ffda3b0737a2eb61ca85dbf3b40bc89fe`、执行冻结 `4aad0169c47f17c2c97bae541b6bc38bb6aaf489`及单行修复 `27280c4ef243a96578b78e9794ff52407be86eff`。实际1521项独立轻量身份/原输出/统计/观测器核验通过，未重复重型矩阵。新增必须修正项1（R01：mismatch外层bytes事件数217而非222），已由执行修正、reviewer复核关闭；剩余必须项0。原finding/失败stderr、可选pattern类型过滤建议及复核处置均保留。调查与具体方案可交PM接收；目标降幅及新wire格式仍是建议，未批准实施、未作产品性能验收或main集成。

### A1 最终独立 review

未参与算法/测试/工具/执行方案设计的 `/root/a1_plan_review` 已完成[方案 review](W012/A1/plan-review.md)和[代码/正确性/性能最终 review](W012/A1/independent-review.md)。base `7f7c1304bdafd941791421cef64864fb1616303c`，最终受审提交 `44a91c472fdeba5bb4b8a6071c0580313336c379`，产品/测试仍为 `ca1f810c3c97376f71089d8b4054760ff198012f` 的冻结字节。唯一产品改动符合 I1–I6：matcher 先执行、小写ASCII偶数hex含空串语言相同；公开异常/canonical及`/1`字节/hash/ref、完整捕获和认证边界保持。

本轮必须项1（A1-R01：中断后重跑可能覆写原证据）在正式测量前修复，独立复现及guard复核确认关闭；剩余必须项0。原finding、原runner、原失败/检查输出和关闭依据均保留，旧P1/P2记录未改。独立实际核对18个fresh串行样本及完整wire逐块相等、两侧profile的65个matcher窗口/调用次数、四份真实包各100成员、双1656全量/原1605节点保留、双typing54、21条工程命令及双源码外安装smoke；未重跑重型组合。受审372文件及263源/测试/配置身份清单闭合。

三路径总耗时中位改善19.72%/22.80%/14.66%，峰值改善88.59%/90.35%/88.65%，wire减幅0。原各次峰值/六个小阶段增幅、单次profile decode约+0.82%及720,336KiB残余峰值的未归因边界均披露；不把profile、工程调度或20%/50%建议混作A1硬门。**最小A1复核通过，可交PM核验；不是PM验收或W012整体完成。** 不批准新格式/下一子项，不代改PM阶段、main或current-work。

## PM 验收与交接（PM）

W011已验收集成后，PM首次派发本任务的P1/P2调查阶段；本次可执行不代表优化实施获批或性能目标已验收。未参与调查/起草的reviewer `/root/w012_handoff_review` 已完成[派发要求独立复核](W012/handoff-review.md)，必须修正项0；受审草稿SHA-256 `c448de9107f625cce700e81eb0584700202e2b47acfd79d94087556e78c04976`。本次只补实际main/分支/依赖状态及PM接收元数据，行为要求/PP1–PP5未改；最终发布身份由Git及交接回复给出。执行交PP1–PP5证据及review后停止，由PM决定实施范围和后续交接。


<a id="pm1-investigation"></a>

### PM1 调查阶段验收与实施取舍

接收交付 `5085f994f0bd4b0c39f7ac1ccdbcacc43d281720`：PP1–PP5及独立review原R01修正/关闭成立，新增必须项0。PM实际1048项证据/工具核验、18项观测器透明性/异常小检查及原probe轻量selfcheck通过；262源/100runtime未改，原双全量/typing/包安装按同源证据采信，未重复重型基线/profile。详见[PM接收说明](W012/pm-receipt.md)及[机器回执](W012/pm-receipt.json)。本机固定mismatch目录不存在，35项origin/清单及原测量capture身份已核，后续同条件比较前须重建；不冒称本次重测。

**P1/P2调查阶段验收通过，W012产品优化尚未完成。** 先准备兼容A1，仅处理已定位的hex matcher瞬时内存成本，保持现有格式/字节/hash/ref、公开验证和异常合同。原20%/50%为完整兼容包的未验证目标建议，不自动成为A1硬门；必须实际报告完整三路前后峰值与耗时及退化。writer/reader/memo按A1实测再细化，B新wire另备具体兼容/身份/迁移材料后给用户决定，不让B阻塞A1。调查材料本轮保存原分支，未合main；下一实施另建分支并给独立执行prompt，原派发记录如下保留。

<a id="a1-implementation"></a>

### A1 实施要求（PM派发准备）

目标是消除现有 `domain.codec._decode` 的重复分组hex matcher造成的瞬时大内存成本，先验证最小兼容改动。算法可采用等价的不重复分组校验加偶数长度检查或有界扫描，由执行者给最小方案并经独立review；不把实施建议的某段正则当唯一可用实现。

| 项 | 输入/条件 → 预期与证据 |
| --- | --- |
| I1 接受语言和错误合同 | 空hex仍表示空bytes；只接受偶数长度的小写ASCII hex。大小写/奇数/空白/换行/Unicode近似字符及畸形tag/JSON/canonical表示的拒绝合同保持，不能只用宽松fromhex准入或顺手收紧公开类型。用独立有限语言对照和边界/生成见证证明等价 |
| I2 完整身份保持 | `/1` schema、公开签名、canonical bytes/wire大小、record_digest/content refs及所有源/run/owner关系不变；完整三路径wire/hash与同捕获原版逐字节一致。最终canonical重编码检查、原始bytes及完整Result不删减，不引入trusted/cache或改认证/constructor次数 |
| I3 失败与嵌套边界 | 已有公开decode/constructor错误及异常object/cause/context/suppression保持，包含matcher/fromhex、各层codec及预期错误后二次认证故障；不宽捕获/重包意外异常。保留原findings及回归，不通过删断言/降覆盖消除失败 |
| I4 完整性能证据 | 同机/解释器/依赖、固定输入URI/RunRequest/cache/保留roots/GC条件，优化前后完整direct/readback/原mismatch各fresh串行测量。开发先单组筛选，最终两侧各3次，用各次及中位数报告耗时、wire、整进程峰值和退化，可复用本轮已满足同条件身份的样本；历史不同环境单次不充当前before。核是否消除已定位的matcher峰值；若残余成本不明或需越界改动，交PM，不自行扩成writer/memo。新profile/窗口诊断与无插桩baseline分开，不能以microbenchmark或少跑测试代替完整结果 |
| I5 原产品行为 | 正常5/7、原mismatch实测4对source5/恰一项差异、完整FIN/crossing/来源、局部图/T05/body、readback attempt/checkpoint不变/unsealed/无terminal及target独立保持；更广受影响来源/错型等值/别名/异常负例按影响验证。输入目录与runtime导入位置分开，比较前按P1清单重建核对固定mismatch目录 |
| I6 工程与review | 开发新增/受影响优先；最终新冻结源双解释器全量、strict typing、构建和双干净安装源码外完整组合smoke。源码/测试/配置、工具/输入、原输出/失败和前后包身份可访问。独立方案/代码/正确性/性能review必须项0后交PM；不自行验收/合main、改入口或启动下一子项 |

I4要求完整路径实证，不承诺20%/50%降幅或生产上界。兼容A1的wire减幅必须为0；解决瞬时峰值后，剩余wire膨胀/重复重建按数据再安排。新格式B的公开范围、默认兼容、hash/ref及历史迁移均不在本次授权内。

### PM2 兼容A1派发

未参与调查/设计/起草的 `/root/w012_a1_handoff_review` 完成[派发要求独立复核](W012/A1-handoff-review.md)，必须修正项0；受审task SHA-256 `c9ab53287f654dcd26e4e5d4f5eea7abc1a29ee19695681e331076ec4774e105`、prompt SHA-256 `70ab51c2e5395d1d62c69ad88664decd7253a88c442997f624f6ec200ddd1c3a`。本补记仅更新阶段/PM接收，不改I1–I6或prompt。**A1可执行，交独立执行session先最小方案review后实现。** 没有新性能结果或A1验收结论；本次只做文档/来源/恢复检查，未运行新算法或重型矩阵。

下一执行session使用 [A1完整prompt](W012/A1-execution-prompt.md)，从含本记录的 `codex/w012-compatible-hex-validation` 最新PM准备提交恢复，最终SHA由Git与交接回复给出；原调查分支与PM1记录保留，main未合入本次准备。实施范围、B未批准及交PM停止边界按上文执行。原P1/P2 prompt仅为历史记录。

### 独立执行 session prompt（原P1/P2派发，已交付）

```text
按 Layauto 项目规范，以独立执行 session 完成 W012 的 P1/P2“成本调查与具体优化方案”，暂不实施产品优化。
从 codex/w012-capture-wire-performance 的 PM 准备提交恢复；起点为含 W011 最终验收的 main。先核对远端完整SHA、工作区、AGENTS/协作/环境规则，读取W012、W011 PM2/原资源数据及必要架构和codec/来源合同。
本次只允许W012测量工具/自检、身份与命令原输出、成本分析、具体方案/目标建议及独立review。runtime、公开DTO/codec、正式测试、fixture/答案、架构和current-work不改。完成PP1–PP5，不因“调查可执行”直接重构wire或增加trusted绕过。
先固定输入URI/RunRequest/环境/对象保留顺序并核源，完成测量计划和轻量工具自检；串行运行normal direct、normal readback、原extraction_mismatch的完整公开构造/encode/decode，核正常5/7、实际4对source5、来源/局部图/T05/body及unsealed attempt不变。无插桩基准与profile分开，保留所有计时、wire、内存及失败；hook不得额外编码巨大对象制造瓶颈。
测清bytes/捕获重复保留、嵌套wire展开和constructor重复认证的实际贡献，区分共享对象、重复内容和inclusive时间。以数据提出具体实施方案、量化目标建议、回归/攻击面及wire版本/兼容/digest影响，交未参与设计的reviewer独立复核并关闭必须项。
调查阶段按相同runtime身份采信W011双全量/typing/安装，不重复小时级双矩阵；本次工具自检和三条实际测量路径不可省。未来优化实施才按“开发新增/受影响、最终冻结双全量”验收。
使用项目noreply身份提交推送原W012分支并核远端完整SHA，交PM；不自行验收、合main、改current-work或启动优化实施/下一任务。若方案需改变关键对外行为/格式或架构，给PM具体实例和影响，不能猜测批准。
```
