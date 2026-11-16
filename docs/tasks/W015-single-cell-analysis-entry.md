# W015 — 单 cell 读取与分析入口：合同及实施准备

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| ID / 目标 | W015；把W014 U06场景变成可直接实施的单cell分析入口方案：未选择外部body资料时保留可认证的本地事实，并明确缺项、错误及受限操作 |
| 里程碑 / 依赖 | M1旁的生产读取适配准备，承接W005–W014；服务后续单cell分析与受限修改，不替代M1完整Stage2、baseline和Stage6闭环 |
| 授权依据与范围 | 用户2026-11-16在W014验收及U06方案说明后要求推进下一步；沿用独立执行session。本轮执行调查、具体合同/样张、最小改造方案及独立方案review，完成后交PM接收 |
| 起始版本 / 分支 | main `3b8d78902591bca32ec9b8ee5d3167d115e1a974`（W014已验收）；`codex/w015-single-cell-analysis-plan`最新远端准备提交。准备提交仅文档，不带入W012 A2候选 |
| 当前阶段 / 阻塞 | **方案已验收并集成。** PR72及[PM1](#pm1-acceptance)接收A1–A7；首个产品实施另见[W016](W016-single-cell-analysis.md)，本任务通过不表示入口已实现 |
| 写入范围 | 本任务的方案、执行、review区及`docs/tasks/W015/`中的方案、候选样张和只读调查探针/小型输出。PM要求、阶段、current-work由PM维护 |
| 非目标 | 本轮不改runtime、正式测试、固定fixture/答案、现行schema/wire及架构正文；不实现生产parser、baseline LVS冻结验证、上层几何窗口、实际修改/发布、EDA调用或新wire性能优化 |
| 架构依据 | 上述main的[architecture](../architecture.md) §2.2–2.3、3.6、5.6–5.9、11.10/11.13/11.15与12；[U06](../roadmap.md#production-body-evidence)、[W014生产方案](W014/production-body-scope.md)、[W014 PM2](W014-terminal-body-relations.md#pm2-integration)；具体格式仍为提案，不能覆盖现行合同 |
| 负责人 | PM准备与接收；独立执行session调查/方案；未承担方案设计的reviewer审合同、来源和实施范围 |

### 已确认的目标与边界

1. 不提供独立tapcell不等于cell几何错误。本地source声明、真实几何与query关联、父级/global关系、body物理证明分别保留，不能相互代替。
2. 增设明确的**读取/分析入口**；原`read_inputs`/W006完整读取合同和既有调用者保持其原有语义。新入口名称、签名及DTO由方案提出，不预设“忽略body错误”开关。
3. 用户未选择外部证据，与选择了但文件丢失、格式错、绑定错或关系违例不同。后者仍是实际错误；有可保留的诊断事实不等于请求成功。
4. 人工标注只表达预期；本地VDD/VSS名字不证明上层电源、domain或body导通。未知几何继续保守处理，不能清空coverage/conflict或W011参数差异。
5. 本轮先收敛读取/分析能力。可信LVS冻结和最小几何窗口只定义后续接入点与证明要求，暂不选定新生产格式或实现受限修改。
6. 保留完整运行的mandatory要求；分析完成不产生baseline、no_change、成功terminal、生产准入或修改许可。

### PM已核的改造动因（执行仍须按版本定位）

现行`importers/reader.py::_parse_inputs`在完成本地解析前读取必需body文件；
`normalization/geometry_input.py`认证body记录、来源及角色，
`normalization/geometry.py::GeometryResult.body_evidence`和W014关系结果也依赖该证据。
因此不能仅删除site必填字段、捕获`RequiredBodyContextUnavailable`后继续，
或伪造一个成功ParseResult/空body记录喂给旧链。W015必须调查真实依赖和最小兼容分拆。

### 验收项

| 编号 | 交付与可观察结果 | 依据、限制与检查方式 |
| --- | --- | --- |
| A1 现状及依赖 | 从site/schema、实际文件获取、ParseResult、认证adapter到W008–W014公开入口，画出哪些本地计算依赖body的实质语义、哪些仅受整包认证耦合；列文件/符号/消费者及现行失败阶段 | 以基线源码和最小只读探针核实；不只读任务摘要。调查legacy相关代码可取用范围，不能引入归档runtime依赖 |
| A2 最小入口合同 | 提出一个推荐Python入口、请求/结果类型及精确状态表，列必需/可选输入、默认值与scope；明确分析目的、保留证据和局部结果如何取用，缺项/不支持/错误/违例如何表达 | 分开API候选和已生效合同；说明target/intent、export/validation policy、query header等完整运行依赖在分析入口是否需要。若不需要，给兼容分拆方法，不能偷偷生成target=source或虚构policy/body证明 |
| A3 输入输出样张 | 至少覆盖下表S1–S7，给最小请求、代表输出、各字段来源、可继续检查和受阻操作；报告本地语义/观测、父级关系、body证明、缺项/错误五类事实 | 使用人工构造并明确标synthetic的候选样张；期望依据来自合同/独立手算，不称现runtime已产出，不把toy字段推广为所有PDK |
| A4 兼容与来源 | 给最小文件改动表、现有公共入口/DTO/wire/调用者兼容表、认证与异常保留路径；本地纯计算不自行IO/查repository，事实仍绑定真实captured bytes、身份、units和profile | 禁止通过伪成功receipt、空body占位、monkeypatch认证或吞异常复用旧链；若新receipt必须独立版本化，说明迁移和旧格式拒绝规则。缺外部证据不能削弱GDS/CDL/query/tech认证 |
| A5 实施与验证计划 | 将最小可运行分析闭环拆成有限步骤，明确第一实现包范围与A3测试映射、旧入口回归及错误链探针；说明真实方言/工具证据尚缺什么，输出最小生产资料调查表 | 首个实现包应能从真实文件读取到本地结果/缺项，不能只做内存DTO或复述U06。可先用已有synthetic捕获验证新合同，但必须披露生产适配未验证；本轮不承诺真实工具支持 |
| A6 资源与证据计划 | 列捕获/认证/重建调用图、可复用结果、新wire必要性；定义首次可运行时的耗时/内存/编码大小检查及退回PM的条件 | 不嵌套复制多份完整W011/W013/W014链，不以少认证换速度。只为调查运行必要的小型探针，不重复双全量/打包/安装或复制大wire；数字注明测量或估计 |
| A7 独立方案review与交接 | 未参与设计者检查A1–A6及来源/失败边界，关键断言独立核对；必须项关闭后提交完整方案、实施prompt草案、决策表和恢复点 | 原finding/失败保留；本次实跑、按身份采信、未覆盖及补跑触发分别列出。交PM接收，不自行修改产品、验收、合main或启动实施 |

### S1–S7：方案必须给出的样张

| 场景 | 必须体现的行为 |
| --- | --- |
| S1 仅底层cell，无外部证据选择 | 本地source和可认证的几何/连通/FIN/query结果可用；B观测和父级/global关联分别未知，列依赖缺项；六个D/G/S的有限比较不等于完整提取匹配 |
| S2 本地无tap，有当前支持的正确外部synthetic上下文 | 接续已实现W014范围，外部图形保持独立，不增加本地union；不同输入scope在同一报告中可区分 |
| S3 未选与选错的对照 | 未选、选中但缺文件、坏格式、错layout/instance绑定、已知几何违例逐类给结果；后四类不能静默变为未选或unknown |
| S4 只有人工供电意图 | 声明可显示且有来源；observed net/body assurance不据此补齐，依赖证明的操作仍受限。是否首包接收声明文件由方案明确，不预设格式 |
| S5 未来可信LVS/最小几何窗口 | 示意证据绑定、scope、有效期/失效条件；首包尚不支持的输入明确unsupported，不伪装实际已认证。父级映射与body证明相互独立 |
| S6 无body且本地存在其他问题 | FIN mismatch 4对5、query缺口/冲突及另一类本地输入错误仍如实保留/拒绝，不能因分析模式清空；列出哪些早期错误使本地事实尚不可认证 |
| S7 完整运行或超范围操作 | 原完整读取/运行要求保持；分析结果不能直接取得修改/发布许可。未来改动超出冻结证明或证据版本变化须失效重验，不能沿用旧assurance |

### 阶段安排与待决项

本轮产物建议为`plan.md`、`interface-examples.md`、`implementation-proposal.md`、
`independent-review.md`、`delivery.md`及必要的`evidence/`。
实施建议必须附可直接交给下一执行session的prompt草案和明确验收项，避免再次只交原则描述。

用户已确认“缺外部资料仍能分析本地事实”的方向，无需再次选择D1或逐项批准内部实现。
本轮先把具体入口/状态/输入格式做成可审阅方案，交PM判断是否仍在既有授权内；
只有新增关键输入解释、能力承诺或使用预期超出上述方向时，才带最小样张、影响及推荐交用户。
这是具体合同尚待收敛的阶段边界，不是要求所有后续内部实现都再问用户。

生产资料调查遵循[隔离边界](../environment/remote-development.md#隔离生产服务器用户确认的边界)：
不能要求上传真实PDK/raw/log/hash或默认允许反馈pass/fail；现有资料不足先记录未知并推进独立方案。
当前未知真实环境不阻塞本轮准备，但不能由synthetic样张推断生产适用。

## 方案与决定（执行准备，PM接收）

执行候选已形成：[源码依赖与决定](W015/plan.md)、[入口合同](W015/entry-contract.md)、
[S1–S7具体样张](W015/interface-examples.md)、[兼容实施与资源计划](W015/implementation-proposal.md)、
[可派发实施prompt草案](W015/implementation-prompt.md)。新入口/格式尚未实施，待PM接收；
架构建议仅存提案，现行完整read_inputs/W006、DTO/wire及mandatory不变。

## 执行结果（执行）

2026-11-16：从指定分支起点`e7c92c03d0b48aa143259da4fc9fbedc382efee0`执行，
启动工作区干净。已交候选Python API/请求/状态/来源合同、S1–S7与实际候选manifest/header、
兼容文件/DTO/wire表、有限真实文件首包步骤、T01–T10、资源门及生产资料未知表。
实跑旧reader/geometry及6个临时反例、候选输入生成、现有parser对候选实际引用消费及文档/来源检查；
未改产品/正式测试/固定fixture，
未跑无关双矩阵/构建/安装或大wire。首轮探针期望代码错误及候选URI闭合失败均保留，修后exit0。
完整A1–A7定位、实跑/按身份采信/未覆盖/补跑触发与PM恢复点见[执行交接](W015/delivery.md)。
未参与设计reviewer已独立复核并关闭必须项，结果见下区及完整报告。
review后仅补交接/文档检查，核心受审候选身份保持；提交推送原分支后交PM接收，不自行验收或实施。

## Review结论（reviewer）

2026-11-16：未参与设计的`/root/w015_independent_review`独立review方案初稿
`5a815f58584746986b344f7616786b6360986e42`及修后冻结候选
`a2d55dbf20c1b07b9f5ca3faddad9c6a8721637b`，**方案review通过，剩余必须项0**。
[完整报告](W015/independent-review.md)保留原findings与修后独立复核，不替代PM接收/产品实施review。

| Finding | 严重性、影响与依据 | 执行处理及版本 | 独立复核结论 |
| --- | --- | --- | --- |
| F01 | must：原候选header raw URI与requests.path不符，tech owner路径相对根失效；独立实际parse_query返回RequestBindingMismatch | `bcb676944acbda8853b15c52777e06d76ba9a176`生成独立URI重定位tech/requests副本，原输入不改 | 最终候选13 closure/9 raw逐hash、6 owner/6 request URI与现parser消费闭合，关闭；原失败保留 |
| F02 | must：同名LocalAnalysisReceipt同时列domain数据与重parse认证构造器，认证/依赖边界不唯一 | 同修复commit明确domain.LocalAnalysisEvidence/只读view和normalization.LocalAnalysisReceipt认证wrapper | 构造、结果ref/无权能view与不反向import parser明确，关闭 |
| F03 | minor：W009检查误写为codec重建，实际仅closed graph+encode | 同修复commit修正文档 | AST/源码和最终文本一致，关闭 |
| F04 | minor：资源门将历史build+encode+decode写成已测build+report，口径不可直接比较 | `a2d55dbf20c1b07b9f5ca3faddad9c6a8721637b`明确历史参照/同口径reference及无reference绝对门 | 独立核差异和原资源说明，关闭 |

本次独立实跑原/修后候选来源与现query parser小型反例、284项产品/tests/config逐文件身份与
关键源码/PM边界检查；未跑新分析API、双全量/typing/build/安装/大wire或资源benchmark。
旧W014能力/矩阵按未改身份作基线，不冒记新入口通过。实跑/采信/未覆盖/补跑触发详见完整报告。
S1–S7为候选synthetic，新产品仍需真实文件验收、旧DTO/wire parity、独立实现review与规范最终矩阵。
仅可交PM接收方案，未自行验收、合main或启动实施。

## PM验收与交接（PM）

本轮PM仅建立要求和执行入口。W015方案未交付、未验收，产品尚未实施。
执行分支及[启动prompt](W015/execution-prompt.md)可供独立session恢复；
完成A1–A7后交PM接收具体合同及第一实现包，不自行进入产品修改。


<a id="pm1-acceptance"></a>

### PM1 方案接收与下一实施包

PM已读取交付`a73713bc8ff7e1e2d4cc61ab93fbd3ace178753d`的合同、S1–S7、源码调查、
实施步骤及独立review；A1–A7接收。F01候选URI闭合、F02认证wrapper所有权已独立关闭，
F03/F04源码和资源口径修正成立，剩余必须项0。11个受审核心文件与冻结`a2d55db…`哈希一致，
284个runtime/tests/config与原产品逐字节相同；后续补记未冒称新产品验证。

通过[PR72](https://github.com/LucianoHoult/Layauto/pull/72)集成，merge为
`d0bb5628384f3a9fec1fe87b6311b854996f574b`，tree等于交付head。
本次重跑文档/身份核查、已有parser候选探针，并在实际merge重跑候选组合；均通过，
详见[PM回执](W015/pm-receipt/README.md)。不重复双全量/typing/build/安装或大wire，
不将已有parser探针、空CI状态或方案review当成新分析入口/生产通过。

采纳推荐的独立只读入口、独立manifest/header及local认证、facet状态和旧接口兼容方案。
具体synthetic输入格式和窄人工声明属于用户已确认方向内的实现收敛，不新增生产能力承诺，
无需重新选择D1。正式分析边界同步架构，首包实施交[W016](W016-single-cell-analysis.md)。
W016明确补资料后新调用/重认证、无交互挂起，local是选定cell scope且首包限flat；
Receipt再次消费只作内部探针，不据此新增公开续算API。上述澄清不改变受审核心方案。

历史候选和原失败/评审材料保留，W015分支不删除。下一session从W016准备分支按新prompt
实施，不重新执行W015方案prompt；当前尚未实现新API，完整M1与真实EDA/PDK边界不变。
