# W013 — 网络区域标注与覆盖草稿

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| 目标 | 将同源CDL/query的网络身份关联到既有本地有效区域和物理分量，输出可追溯的标注、覆盖缺口、歧义/冲突及分量网络摘要 |
| 里程碑/依赖 | M1 Stage 2组件，承接W007 net identities/seeds、W008索引、W009有效区域、W010局部物理图；W011继续保留既有FIN能力。本任务不完成整个M1 |
| 授权 | 2026-11-11用户同意结束本轮A2尝试、继续网络标注，并明确减少重复验证为标准流程；W012停止决定见[PM7](W012-capture-wire-performance.md#pm7-a2-stop) |
| 恢复 | 从A1验收main 2489b4609ae97d8211bf450d55cac9392492ac71建立codex/w013-net-annotation-coverage；当前main基线为d6182fe6893c26490f9d58c6b808a5ce9910384b；交付63a0962后接手本分支最新PM接收head，按合并前独立review prompt继续。不得从6045d8f的A2产品分支派生或带入其两codec改动/新增测试 |
| 阶段 | **待验收：PM分支技术接收已完成；合并前独立session复核待进行。** 执行/R2工程及既有独立review按PM1核对接收；未最终验收或合main，见下方PM1 |
| 范围/owner | annotation的匹配/覆盖逻辑、domain中立DTO、state.annotation草稿所有权及必要normalization入口/codec与测试；具体最小文件列表由方案给出。可写新docs/tasks/W013/附件与本任务执行/方案区；PM维护要求/阶段/current-work |
| 非目标 | 不改已验收fixture/答案、A1/A2历史证据、物理边/几何、source/target语义；不实现完整工艺坐标、外部body连通、全套器件/pin/color标注、规则豁免、事务baseline/发布、ECO后重新提取、Stage6或真实EDA。既有body输入要求及U06不由本任务改写 |
| 架构依据 | [architecture](../architecture.md) §3.3、§3.5–3.8、§5.3–5.9、§11.2/11.5/11.9/11.15；[协作规则](../collaboration/rules.md#verification-reuse)及[U06](../roadmap.md#production-body-evidence) |
| 分工 | 执行落实最小方案/代码/证据；未参与对应设计/实现者独立方案及代码review；PM最后接收/集成。沿用独立执行session，入口见[prompt](W013/execution-prompt.md) |

### 具体范围与正确性依据

首先使用现行synthetic profile、exact axis-aligned rectangle与已声明layer/tolerance/trim规则；不得自行发明容差、质量升级或生产映射。W007已经完成net_xref到cell-scoped NetId的join并保存NetAnnotationSeed，本轮消费这些真实输入，追溯到原captures；不能再次靠名字猜网，也不能把oracle当产品输入。

以W009有效region/必要fragment为标注目标，空间索引只枚举候选，最终由精确几何关系判定。查询边界只覆盖一部分region时，保留精确覆盖部分及缺口，不能给整个shape/cell贴满标签；具体target identity、分割/歧义表示、coverage分母与重叠去重规则必须在方案中说明并review。未支持的approximate_bbox/untrimmed、非零容差/trim组合应保留quality/source和明确unsupported/ambiguous，不假装exact成功。已支持正常数据不得以一概unsupported规避本任务。

本地scope与外置body分开：只关联本地有效导体及既有W010分量。现有完整oracle含外部body节点/边，须明确取其本地投影，不能把16节点/10边的完整样本解释冒作W010本地图。先复核W010现行14节点/8边/6分量的实际输入，独立oracle映射仅用作测试判据。正常六分量按现行local oracle为四个网络关联分量及两个本地body未知分量；A的主分量与两个孤岛属于cut专例，即使同网也仍为三个物理分量。标签不制造连通，不能把历史旧正常样本当现行答案。

| 验收项 | 输入/条件 → 预期行为及验证 |
| --- | --- |
| A1 同源与身份 | W007 semantic/net identities/seeds与W009/W010输入属于同一捕获/tech/unit/top/scope/run → 可组合；跨run/database、伪造/缺失/冲突xref或owner/来源错配 → 定位typed issue/失败。保留现行方言实际产生的QueryKey ordinal字符串索引、layout名、canonical NetId及原source backlink；007按P01决定为拒绝反例，不按数字或字符串相等替代身份 |
| A2 精确区域 | 按registry carries/associates_with与实际单位、质量、trim规则匹配；cut后的左右区域、部分交叠、同cell多occupant、边界接触/零面积、重叠同网证据不能整shape过标或重复累计。区域/fragment身份、精确面积/coverage与未覆盖部分可重建、顺序确定 |
| A3 分量摘要 | 正常既有六个本地分量的网络关联对照独立本地判据；多个断开分量可同NetId，不新增或删除物理edge。一个分量出现不可解释的不同NetId须保留全部证据并报conflict；不最后写覆盖、不用语义网名合并分量，component摘要不冒作每个region已直接覆盖 |
| A4 缺口与质量 | 未匹配query、未标注导体、部分coverage、marker/非导体分类及多候选/质量不足分别报告；unknown不是兼容任意net。原drawn/effective仍完整保留。coverage在本次scope内逐layer列总目标、覆盖/未覆盖/冲突与证据来源，说明计量单位和分母；coverage gap不自动等同整轮失败或成功 |
| A5 DTO/公开边界 | 不可变且无可写alias、精确native scalar/类型、完整字段和owner/source绑定；需要持久化的中立草稿具有确定canonical roundtrip/ref，并拒绝伪造/错型/不完整来源，保留原异常object/cause/context/suppression。原已验收codec及其wire/ref不变；不得为提速跳过公开认证或只存无法校验的ref |
| A6 作用域与有效性 | 输出声明source-evidence/local scope、绑定当前几何/输入身份；不套到变化后几何或当新LVS证明，不发布authoritative state、不创建成功terminal。包含不支持质量/缺证据的结果必须显露限制，不降低mandatory规则或body要求 |
| A7 组合成本检查点 | 方案先画输入/输出/认证/序列化调用边界及预计新增捕获；不默认再包一层完整W011 Result。最早可运行组合即用固定正常/direct、readback和既有mismatch记录耗时/峰值/wire字节，复用同源上游证据。新增工作与未改上游分列，必要时同机复测A1基线；单次波动不当稳定增长/收益。明显放大重复编码、资源阻塞或成本无法解释时，在最终重型矩阵前交PM具体测量/结构方案，不能无限扩链或静默删验证 |
| A8 工程与review | 按协作默认流程：开发新增/受影响，关键独立判据/错误路径和实际组合；最终新冻结双3.10/3.12全量、typing、构建与双干净安装源码外smoke。独立review核方案/代码/证据/资源限制，修正复核必须项，交PM；review不机械重跑最终矩阵，实际合并后由PM做必要组合验证 |

### 实施前方案要求

1. 读实际W007 seeds/identity、W009 region、W010 graph、tech owners/query raw+normalized和独立oracle/手工意见（尤其A孤岛、cut、MARK与coverage），列现有接口与legacy可取用/需改造/不可取用理由；不引入legacy runtime。
2. 给出具体输入绑定、neutral target/annotation/coverage/issue字段、输出owner、canonical验证与异常边界；明确正常/部分/冲突/unsupported结果和region覆盖与component推断的区别，提供小输入→输出样张。不是新报告UI或生产格式承诺。
3. 明确最小文件列表和独立测试判据，按新增能力挑受影响测试；给资源检查点及“本次实跑/采信/未覆盖/触发补跑”表。比较直接复用已有证据/草稿的组合方式与重复全量嵌套的成本，保持所有必需来源/认证；不在本任务重写通用wire或继续A2。
4. 在修改关键产品合同前完成独立方案review。既定架构内具体算法自主处理；新增输入解释、关键格式/使用预期、缺失policy或架构冲突，先形成具体反例/方案/影响交PM，未决项不猜测批准。通过后实施并独立代码review。

## 方案与决定（执行）

2026-11-12，执行从远端 `d6182fe6893c26490f9d58c6b808a5ce9910384b` 恢复原W013分支，
核得A1祖先和产品/测试无差异，未取用A2。已准备[具体方案候选](W013/interface-plan.md)、
[输入反例及PM待决P01](W013/pm-decision.md)，交未参与设计/实现者[独立方案review](W013/interface-review.md)。
P01涉及“含007”与现行已验收ordinal捕获解释冲突，关键产品实施等待PM明确；不自行扩展格式。

后续用户答复（2026-11-12）：保持当前真实捕获范围；007记为不支持/拒绝反例。
执行按[决定记录](W013/pm-decision.md#p01-用户决定2026-11-12执行按原答复记录)采用选项A，
不改旧parser/QueryKey准入；在独立实施门复核后继续当前W013，不将本答复当产品验收。

## 执行结果（执行）

2026-11-12首轮实施前调查交接时，**未实现W013，A1–A8未完成，不是完整产品交付**。
[preflight回执](W013/preflight-audit.json)与[可复现审计工具](W013/preflight-audit.py)保存远端/工作区、
263项旧A1文件hash一致、当前环境及真实reader→W007/007拒绝探针；
[独立反例](W013/review-evidence/input_contract_probe.stdout.json)另核完整captured-source认证拒绝伪造007。
[独立交接证据核证](W013/evidence-review.md)确认来源、实际import、初审可重建身份与PM原文范围；
新产品尚未实施，未将同身份A1历史证据当作W013最终矩阵。

实跑：上述轻量调查与文档检查。按身份采信：仅同源A1上游历史证据，历史耗时不当本机测量。
未覆盖：W013新产品、三路资源组合、新冻结双3.10/3.12全量/typing/build/双干净安装smoke及代码review。
补跑触发：P01与方案必须项关闭后实施；最早组合即测direct/readback/mismatch；资源放大先交PM，
最终产品重新冻结跑新矩阵，相关源码再变仍重新冻结验证。旧A1矩阵不能替代新产品矩阵。
下一步仅交PM明确P01并恢复本任务，不改PM阶段/current-work、不合main或启动下一任务。

### 用户决定后的实现恢复点（执行，2026-11-12）

P01已按用户选项A记录并经独立实施门复核关闭。当前产品/测试/配置源码已落在
`119189d5a958b617fe754b61c4e3b8a7e8a9f9fb`后续同源版本；实际完整字节身份以
[定向验证回执](W013/development/targeted-attempt-01.command.json)的
`6463eb67b1c1ce5b9fd1fca436fa499a4ad14da004ef8fcd913872bd350443a9`为准。
新增6个runtime模块、normalization公开入口和typing范围，以及4个新测试文件；
旧codec/fixture/答案/历史finding/报告未改。当前不是完整产品交付：最终工程证据仍在执行。

实际开发验证：75项新增与受影响query/identity/dependency范围合计**110 passed / 450.21s**，
源码前后身份一致；双3.10.22/3.12.14 strict mypy均60文件通过。全量实际collection为1731，
保留原1656项并新增75项。独立[代码/合同review](W013/code-review.md)保留CR-01–03原失败，
operator owners、可写map backing与分类/contributor闭合均已修正并独立复核，当前必须项0。

[首完整direct](W013/resource-attempt-02/normal-direct.json)以及
[首轮三路](W013/resource-attempt-03/suite.json)保留修前源码身份和原始time/RSS/wire；
首direct的嵌入W010旧wire SHA与同机W010参考完全一致，未新增整份W011捕获。
CR修正后当前正在同一新源上复测三路，记录已有公开认证调用及其inclusive耗时；
旧结果不冒记为修后同源或稳定性能改善。

当前分工：实跑为上述开发/独立探针和已有组合；按身份采信仅未改上游原合同/历史证据；
最终双全量、构建和双全新安装源码外组合smoke尚待新冻结执行。三路成本清楚且资源节点核验后
启动最终1731项双解释器矩阵；源码/测试/config再变仍重新冻结验证。PM阶段/current-work不变，
最终仅提交推送原W013分支交PM，不合main、不自行验收或启动下一任务。


### 最终新冻结 R2（执行，2026-11-12）

修后三路成本已完成并经独立资源核证，见[成本与限制](W013/resource-summary.md)；
原实际受测source_id仍为`6463eb67…3443a9`，不改写为后来的测试身份。
首轮最终矩阵在双解释器的同一保留W007架构guard失败：旧白名单未声明W013两个
normalization模块对只读`AnnotationDraft`的必要依赖。已保留[原失败/受控停止](W013/verification/controlled-stop.json)
与[单点复现](W013/development/retained-boundary-failure.command.json)，**首轮不算全量通过**。
执行只为这两个文件/这个类补精确白名单，未放开mutable state或发布依赖；
[三个相关架构检查](W013/development/retained-boundary-after.command.json)实跑3 passed。

独立[测试delta复核](W013/review-evidence/retained-boundary-delta-review.stdout.json)确认273项
完整路径集合不变，只有`tests/contracts/test_w007_contracts.py`字节变化；106个runtime文件、
config、输入及新增75项测试不变。按资源工作负载不执行该test的事实，
[资源采信证明](W013/resource-r2-identity-adoption.json)与[独立核证](W013/review-evidence/resource-r2-adoption-review.json)
采用原测量，不把它冒记成新source实跑；资源必须项0。
原clearance的review commit引用错误另以[不可变补正](W013/resource-clearance-reference-correction.json)
及[独立核证](W013/review-evidence/resource-clearance-reference-review.json)保留追溯，原字节不改。

新的完整源码/测试/config身份为
`2c5724a9d3ecf99913857ad89015c03c03475ae762c1c8ab00b5146fd3eec278`，
冻结HEAD `2a45938`；[R2快照/映射](W013/verification-r2/source-manifest.json)包含全部273项实际字节。
已按此新冻结启动双3.10.22/3.12.14各1731项，随后双typing、构建、双干净安装与源码外
三路smoke；[R2目录](W013/verification-r2/)只收本次原记录，旧失败不覆盖。
当前仍在执行，尚不宣称新最终矩阵通过或A1–A8完整交付。


### 最终执行交付（2026-11-12，待PM接收）

**实施与最终工程验证已完成；A1–A8覆盖见下表，独立最终review以下段结论为准，不代PM验收。**
最终完整源码/测试/config身份为
`2c5724a9d3ecf99913857ad89015c03c03475ae762c1c8ab00b5146fd3eec278`，
冻结提交`2a45938aba8e751183d472d660a1ab66a1063636`。
[最终R2回执](W013/verification-r2/receipt.json)为`passed`；
[273项完整映射](W013/verification-r2/source-manifest.json)、
[可重建源码快照](W013/verification-r2/source-snapshot.tar.gz)与
[全部原证据hash](W013/verification-r2/evidence-manifest.json)可定位实际受测字节。
所有命令结束后再次核原工作区/执行snapshot/源码路径集合、三冻结工具、clearance及原collection
字节不变；后续提交只补本任务文档/证据，不以新的Git HEAD冒充不同受测源。

| 要求 | 本轮交付与证据 |
| --- | --- |
| A1 同源/身份 | 复用真实W007 xref→NetId/QueryKey seeds，完整W010公开认证后从同一semantic input重建。source/run/database/owner错配及伪造xref拒绝；保留原1/2/3/4字符串和全部来源。007按用户选项A为拒绝反例，未改旧parser/QueryKey |
| A2 精确区域 | Fraction nm、tech layer mapping、声明quality/tolerance/trim裁交；独立target/fragment及同网union去重。partial、CUT gap、边/点零面积、同cell多occupant及query未匹配均有明确验证 |
| A3 本地分量 | 正常14节点/8边/6分量对照独立local oracle，4关联+2未知body分量；cut专例中同A网仍三物理分量。无新增/删除物理edge，component关联不替代region直接覆盖，外部body节点/边未纳入 |
| A4 缺口/质量 | 正常14 targets、8份net evidence、40项drawn分类：总35090/直接覆盖3170/未覆盖31920 nm²，MARK25另列非导体。冲突、unknown、trim及unmatched证据保留；不升级非exact质量，现行上游拒绝范围不假称已支持 |
| A5 公开DTO/codec | 不可变、防御快照、native scalar/完整closed graph、全字段与owner/source验证；neutral与captured认证分层。CR-01–03原失败及修正复核保留，原异常object/cause/context/suppression保真。新wire仅含一次完整旧W010 canonical Value，旧codec/wire/ref未改 |
| A6 有效性/owner | state.annotation拥有compact proposed draft，annotation纯匹配、derive只读摘要。固定source-evidence/local与当前geometry/input/run binding；body/completed原证据保留，readback attempt/checkpoint不变且terminal为空 |
| A7 组合成本 | 调用/序列化图和实际1/1/2共4次W010公开decode认证相符；[首完整组合及修后测量](W013/resource-summary.md)分别保留源身份，完整W011 Result零份。修后固定三路新compact约0.315MB，成本主要为未改上游认证，资源节点无must。R2仅test delta按工作负载身份采信，原测量不改标 |
| A8 工程/review | 新冻结双全量、双strict typing、构建与双干净安装源码外三路smoke全部实跑通过；独立方案门、代码/合同/组合/资源探针、完整源/输入/工程身份审查分别留证。原guard失败和受控停止不计为通过，R2双矩阵已重新完整执行 |

具体文件职责/调用图/小输入输出见[方案](W013/interface-plan.md)，实际最小文件变化和独立判据
入口见[范围专项](W013/handoff-scope-audit.md)。产品仅6个新模块、公开入口/typing清单；
测试为3个新收集模块+1个共享helper和旧W007精确依赖白名单维护。未改已验收fixture/答案、
旧codec/finding/报告、architecture、roadmap/current-work、任务PM要求/阶段/验收段。

| 最终实跑 | 结果及原记录 |
| --- | --- |
| Python3.10.22全量 | 1731 passed，pytest报告9252.87s；[原输出](W013/verification-r2/pytest-310.stdout.txt)/[进程回执](W013/verification-r2/pytest-310.json) |
| Python3.12.14全量 | 1731 passed，pytest报告6653.50s；[原输出](W013/verification-r2/pytest-312.stdout.txt)/[进程回执](W013/verification-r2/pytest-312.json) |
| 双strict typing/pip check | 两套均60源文件通过，依赖检查均0；命令/依赖/解释器身份在最终回执中 |
| wheel/sdist构建 | 两包全部106个runtime文件逐hash等于冻结源码；[包身份](W013/verification-r2/package-identity.json) |
| 3.10全新sdist安装 | 源码外`-I -B` direct/readback/mismatch全部通过，434.159s；[原输出](W013/verification-r2/installed-smoke-310.stdout.txt) |
| 3.12全新wheel安装 | 同样三路全部通过，313.429s；[原输出](W013/verification-r2/installed-smoke-312.stdout.txt) |

[双安装身份](W013/verification-r2/installation-identity.json)证明导入来自各自clean venv的
site-packages，106个runtime字节均与源/包相同；smoke不加载tests/support或oracle答案，
同时核完整public roundtrip、直接result digest、neutral防伪、精确coverage和run/body绑定。
安装smoke的临时mismatch URI只作正确性；不将它的耗时/wire与固定URI资源测量混比。
上表为本环境实际命令，不从旧A1跨环境秒数推断性能改善。

| 验证分工 | 交PM时事实与限制 |
| --- | --- |
| 本次实跑 | 开发新增/受影响110项、必要3项guard修正验证、独立关键反例/精确数学/实际captured异常链、最早及修后三路资源、R2双1731全量/typing/build/双安装三路smoke，以及独立完整身份审计 |
| 按身份采信 | 资源04的原source6463eb67…按106 runtime/config/input/probe完全相同采信到R2，唯一delta是未执行于资源workload的旧guard test；原独立探针亦按相同runtime采信。旧A1仅为来源/合同及原collection对照，未替代新产品最终矩阵 |
| 未覆盖 | synthetic支持范围外的真实EDA/生产PDK、非矩形/非exact或新容差policy；完整M1、body/U06与其它规则/生命周期闭合及baseline/terminal发布。现有body要求不改。分支尚待PM实际接收/集成 |
| 补跑触发 | 源码/测试/config/相关输入/依赖变化、实际合并冲突或组合行为变化、身份不闭合/证据缺失或新风险；相关源变后重新冻结并完成要求的最终矩阵。文档/引用补记及换session/角色本身不触发重复双全量；PM在实际集成版本补必要组合验证 |

最终只沿原`codex/w013-net-annotation-coverage`分支以项目noreply身份提交推送，核远端完整
SHA交PM；不自行验收、合main、删分支、改变PM阶段/current-work或启动下一任务。

## Review 结论（reviewer）

2026-11-12，独立 reviewer `/root/independent_review`（未参与方案设计或实现）完成本轮
[方案 review](W013/interface-review.md)，原 findings 固定在
`0794d2dc90baaf8d3180e9ce4f4d91683fe90dc7`。修后方案 SHA-256 为
`827dd88dd7eb638fa8ec98b15768e9ccb30880eed549d4257fc5337abda1830d`；PR-02 的
完整认证/序列化展开与 PR-03 的 retained roots/独立W011基线范围已在方案层修正并复核关闭。
PR-01/P01（当前ordinal捕获不能表示007的验收解释）仍待PM决定，**未通过实施门**。
独立轻量探针、原失败与源码身份核对见报告附件；没有W013产品、代码/组合/资源review或新最终
矩阵，不把本次方案复核或旧A1证据记作A1–A8完成。

后续实施门复核（2026-11-12）：用户已明确选择“保持当前真实捕获范围；007记为不支持/拒绝
反例”。独立reviewer核对[追加决定](W013/pm-decision.md#p01-用户决定2026-11-12执行按原答复记录)
及方案新SHA-256 `7591fa5d2deb24ced2f2301db7d4cf953801d704ac812e9da092010262f40e1c`，
PR-01/P01关闭，PR-02/03既有修正仍成立，**方案实施门通过，可在当前真实捕获范围实施**。
这只解除方案门；代码/合同/组合/资源review及新产品最终矩阵仍未执行，不构成产品或PM验收。


### 最终独立review（2026-11-12，reviewer）

**代码/合同/组合/资源及最终工程证据review通过，剩余必须修正项0；支持交PM，不代PM验收。**
受测冻结提交`2a45938aba8e751183d472d660a1ab66a1063636`，完整source_id
`2c5724a9d3ecf99913857ad89015c03c03475ae762c1c8ab00b5146fd3eec278`。
[完整review](W013/code-review.md#最终独立review结论2026-11-12)保留CR-01–03原失败、修正及独立复核，
P01按用户选A保留007拒绝；当前synthetic/local范围下A1–A8交付及执行表与实际证据一致。

主reviewer `/root/independent_review` 未参与设计/实现，独立审实际diff、来源/owner/公开合同、
精确coverage/本地oracle、canonical与原异常链，补关键反例并复核修正；另以
[最终只读审计](W013/review-evidence/code-static/final_r2_complete_audit.stdout.json)核21条实际命令、
81份证据manifest、273源/测试/config、106runtime与包/安装字节身份。
[工程专项148项](W013/final-evidence-review.md#r2最终工程身份核证完成追加2026-11-12)亦通过。
新R2双3.10.22/3.12.14各1731全量、双60源strict typing、build和双fresh安装源码外三路smoke
均有实际通过证据；首轮中断矩阵不计通过，旧A1矩阵未替代新产品矩阵。

实跑为上述独立反例/合同/源与证据身份检查；按身份采信新R2原工程实跑及resource04的精确
runtime/input/probe相同采信链，不重复全量或捕获。137项固定输入审计与历史README/资源review
引用补正闭合，原probe/失败/日志/manifest保留。未覆盖真实EDA/完整M1、外部body/U06与其它既有
后续义务、baseline/terminal发布及实际main集成；本输出仍为source-evidence/local草稿。
源码/测试/config/相关输入/依赖变化、实际组合变化或证据身份缺口触发相应复核和重新冻结验证；
文档补记/换session本身不触发重复双全量。PM在实际接收/集成版本补必要组合验证。

### 合并前独立新会话复核（reviewer，2026-11-13）

**可进入 PM 集成及组合验证；本次未发现新的阻塞项，必须修正项 0。**
新会话 `/root` 及四个只读专项均未参与 W013 设计、实现或正式测试编写；
受审 base=`d6182fe6893c26490f9d58c6b808a5ce9910384b`，
head=`f31df3f3e6cd5df7ecef2e1f91977c3b68a9fac4`，273 项完整 source_id 仍为
`2c5724a9d3ecf99913857ad89015c03c03475ae762c1c8ab00b5146fd3eec278`。
[独立报告](W013/independent-premerge-review.md)逐项列 A1–A8、CR-01–03、来源/几何/公开边界、
实跑、采信及限制；[新有界证据](W013/review-evidence/independent-premerge/README.md)保留原输出与 hash。

实际补跑独立集合 768 项、fragment/oracle 算术、neutral 攻击/精确 guard、reader→W007/W008
来源反例、完整 direct public roundtrip/派生字段篡改/原异常链及 actual W013 run/database/top
三字段篡改拒绝；59 项独立证据审计闭合 273 源、81 证据、21 命令、两包106 runtime及原环境链。
R2 双1731、双typing60、构建和双 clean 安装三路 smoke、resource04 的 test-only delta
采信链按精确身份复用，未机械重跑；旧 source6463…测量未改标为 R2。
仅新增报告/必要有界证据并追加本 reviewer 区，不改产品/正式测试/fixture/历史报告或 PM 段。
结论限现行 synthetic exact/local source-evidence 草稿；真实 EDA、外部 body/U06、完整 M1 与
实际 main 集成版本未覆盖。交 PM 核实际集成版本并做必要组合验证；不代 PM 验收或合 main。

## PM 验收与交接（PM）

2026-11-11：从已验收A1 main准备此任务，W012 A2候选保留原分支且不集成。此处仅准备开发交接，没有实施或验收W013；关键方案独立review是实施前要求。当前只检查文档、来源/链接和恢复范围，不为纯文档重跑产品测试。下一执行session按prompt先方案review再实现，完成后交PM，不能自行合main/验收或启动下一节点。

<a id="pm1-receipt"></a>

### PM1 分支技术接收（2026-11-13）

远端交付核为63a0962f1b56655f234140822bffa8f56b7bb15f，main仍d6182fe6893c26490f9d58c6b808a5ce9910384b。PM读取任务/方案决定、scope audit、最终code-review及resource-summary，CR-01–03关闭按既有独立复核采信；产品13路径变化，fixture及A2两codec未改。源冻结2a45938aba8e751183d472d660a1ab66a1063636，完整source_id=2c5724a9d3ecf99913857ad89015c03c03475ae762c1c8ab00b5146fd3eec278。

本次实际运行[只读收据核对](W013/pm-receipt-check.py)：273源码/测试/config对磁盘、冻结Git、交付Git及源码tar逐项一致；81项证据hash、21条命令exit/原输出hash通过；wheel/sdist各106 runtime内容等于冻结源。命令为python -B docs/tasks/W013/pm-receipt-check.py，exit0，结果见[PM回执](W013/pm-receipt.json)。未运行新产品测试、全量、安装或性能实验；双1731、typing60和安装smoke按同源原证据采信，不把PM核对当新独立产品review。

A1–A8已有执行/独立证据，允许进入合并前独立session复核；**本项仅分支技术接收，尚未最终验收或集成。** 正常4关联+2本地body未知、直接覆盖3170/总35090nm²、MARK25另列，支持边界不等于完整body/M1。资源04采信链由原独立核证承担；约0.315MB增量避免新增W011整包，完整上游认证成本仍在，不比较不同终端workload得出提速结论。

PM同步纠正任务历史“含007”文字并明确正常/孤岛专例区别，依据用户P01选A、MR-020/034及现行已验收fixture；不是修改输入合同、fixture或按实现重定答案。原要求字节可在交付63a0962追溯，旧执行/reviewer段及失败记录未改。

下一步使用[合并前独立review prompt](W013/independent-premerge-prompt.md)，重点新公开DTO/canonical来源闭合、几何coverage与CR修正，不机械重复R2双全量。若无阻塞，再由PM处理实际main集成及必要组合验证；当前main未变，不启动下一功能任务。
