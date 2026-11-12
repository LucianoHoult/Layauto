# W013 — 网络区域标注与覆盖草稿

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| 目标 | 将同源CDL/query的网络身份关联到既有本地有效区域和物理分量，输出可追溯的标注、覆盖缺口、歧义/冲突及分量网络摘要 |
| 里程碑/依赖 | M1 Stage 2组件，承接W007 net identities/seeds、W008索引、W009有效区域、W010局部物理图；W011继续保留既有FIN能力。本任务不完成整个M1 |
| 授权 | 2026-11-11用户同意结束本轮A2尝试、继续网络标注，并明确减少重复验证为标准流程；W012停止决定见[PM7](W012-capture-wire-performance.md#pm7-a2-stop) |
| 恢复 | 从A1验收main 2489b4609ae97d8211bf450d55cac9392492ac71建立codex/w013-net-annotation-coverage；接手本任务准备提交的最新远端head。不得从6045d8f的A2产品分支派生或带入其两codec改动/新增测试 |
| 阶段 | **可执行：先具体方案及独立方案review，必须项关闭后在既定范围实施；有关键预期空白则带实例交PM。** 未运行W013，未进行独立派发review，不宣称方案或代码已通过review |
| 范围/owner | annotation的匹配/覆盖逻辑、domain中立DTO、state.annotation草稿所有权及必要normalization入口/codec与测试；具体最小文件列表由方案给出。可写新docs/tasks/W013/附件与本任务执行/方案区；PM维护要求/阶段/current-work |
| 非目标 | 不改已验收fixture/答案、A1/A2历史证据、物理边/几何、source/target语义；不实现完整工艺坐标、外部body连通、全套器件/pin/color标注、规则豁免、事务baseline/发布、ECO后重新提取、Stage6或真实EDA。既有body输入要求及U06不由本任务改写 |
| 架构依据 | [architecture](../architecture.md) §3.3、§3.5–3.8、§5.3–5.9、§11.2/11.5/11.9/11.15；[协作规则](../collaboration/rules.md#verification-reuse)及[U06](../roadmap.md#production-body-evidence) |
| 分工 | 执行落实最小方案/代码/证据；未参与对应设计/实现者独立方案及代码review；PM最后接收/集成。沿用独立执行session，入口见[prompt](W013/execution-prompt.md) |

### 具体范围与正确性依据

首先使用现行synthetic profile、exact axis-aligned rectangle与已声明layer/tolerance/trim规则；不得自行发明容差、质量升级或生产映射。W007已经完成net_xref到cell-scoped NetId的join并保存NetAnnotationSeed，本轮消费这些真实输入，追溯到原captures；不能再次靠名字猜网，也不能把oracle当产品输入。

以W009有效region/必要fragment为标注目标，空间索引只枚举候选，最终由精确几何关系判定。查询边界只覆盖一部分region时，保留精确覆盖部分及缺口，不能给整个shape/cell贴满标签；具体target identity、分割/歧义表示、coverage分母与重叠去重规则必须在方案中说明并review。未支持的approximate_bbox/untrimmed、非零容差/trim组合应保留quality/source和明确unsupported/ambiguous，不假装exact成功。已支持正常数据不得以一概unsupported规避本任务。

本地scope与外置body分开：只关联本地有效导体及既有W010分量。现有完整oracle含外部body节点/边，须明确取其本地投影，不能把16节点/10边的完整样本解释冒作W010本地图。先复核W010现行14节点/8边/6分量的实际输入，独立oracle映射仅用作测试判据。A的主分量及两个孤岛即使同网也仍为三个物理分量；标签不制造连通。

| 验收项 | 输入/条件 → 预期行为及验证 |
| --- | --- |
| A1 同源与身份 | W007 semantic/net identities/seeds与W009/W010输入属于同一捕获/tech/unit/top/scope/run → 可组合；跨run/database、伪造/缺失/冲突xref或owner/来源错配 → 定位typed issue/失败。保留QueryKey opaque lvs_index（含007）、layout名、canonical NetId及原source backlink，不按数字或字符串相等替代身份 |
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

## 执行结果（执行）

2026-11-12当前为实施前调查交接，**未实现W013，A1–A8未完成，不是完整产品交付**。
[preflight回执](W013/preflight-audit.json)与[可复现审计工具](W013/preflight-audit.py)保存远端/工作区、
263项旧A1文件hash一致、当前环境及真实reader→W007/007拒绝探针；
[独立反例](W013/review-evidence/input_contract_probe.stdout.json)另核完整captured-source认证拒绝伪造007。

实跑：上述轻量调查与文档检查。按身份采信：仅同源A1上游历史证据，历史耗时不当本机测量。
未覆盖：W013新产品、三路资源组合、新冻结双3.10/3.12全量/typing/build/双干净安装smoke及代码review。
补跑触发：P01与方案必须项关闭后实施；最早组合即测direct/readback/mismatch；资源放大先交PM，
最终产品重新冻结跑新矩阵，相关源码再变仍重新冻结验证。旧A1矩阵不能替代新产品矩阵。
下一步仅交PM明确P01并恢复本任务，不改PM阶段/current-work、不合main或启动下一任务。

## Review 结论（reviewer）

未执行。分别绑定方案与代码版本，列实际审查/独立见证、finding原文、修正及复核；0必须项不能替代未完成工程或性能证据。

## PM 验收与交接（PM）

2026-11-11：从已验收A1 main准备此任务，W012 A2候选保留原分支且不集成。此处仅准备开发交接，没有实施或验收W013；关键方案独立review是实施前要求。当前只检查文档、来源/链接和恢复范围，不为纯文档重跑产品测试。下一执行session按prompt先方案review再实现，完成后交PM，不能自行合main/验收或启动下一节点。
