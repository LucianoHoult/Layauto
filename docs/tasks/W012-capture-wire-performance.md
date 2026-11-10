# W012 — 完整捕获、wire 与重复重建性能优化

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| ID / 目标 | W012；降低真实组件组合中完整捕获保留、wire 编解码和重复认证/重建的耗时与内存，保持可审计来源及公开验证合同 |
| 里程碑 / 依赖 | M1 工程支撑，关联 R13/R27/R28；承接 W011 的明确稳定版本，优先于继续扩大状态链/输入。W011已由PR #65验收集成，见其PM2；本次先派发P1/P2调查 |
| 授权依据 | 用户明确要求：开发阶段先跑新增及受影响范围，最终交付再跑双全量；PM 单列完整捕获、wire 膨胀和重复重建优化任务，不能只减少测试数量 |
| 当前阶段 / 阻塞 | **可执行，仅限 P1/P2 成本调查、具体方案及其独立 review。** 优化实施尚未派发；没有已批准的 wire/cache 方案、降幅或生产资源上界 |
| 恢复 / 分支 | W011 原交付 `3c464baade7b6ea8c712cfb84265490b8e3f754e`，工程冻结 `e89bdaa6a091f56cfaf7862dced7232d34e22514`；[PM1](W011-channel-identity-fin-count.md#pm1-receipt)记录核验。W011已由PR #65合入main `59f2cda44e30779bb3e82346d71a389831314506`，最终验收见其PM2；从含验收补记的main另建 `codex/w012-capture-wire-performance`，main起点 `0a3326aa363477724465886cd05874d0997fba3e`，接手含本派发记录的最新W012分支head |
| 本次允许写入 | `docs/tasks/W012/` 下的测量工具、工具自检、命令/环境/源码与输入身份、原输出、成本分析、实施方案和独立review；执行者更新本任务的方案/执行区，reviewer更新review区。产品runtime、正式测试、fixture/答案、架构、历史附件及current-work不改 |
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

当前没有新的输入使用预期需用户立即决定。尚未选定优化算法、wire 合同或数值验收目标；后续准备按实际证据收敛。

### 本次 P1/P2 派发与完成判据

本次交付是调查和可实施方案。优化实现须等 PM 接收调查及独立 review 后再明确派发；上表 A1–A4 约束未来实施，不能把本次只完成调查写成产品优化完成。

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

## Review 结论（reviewer）

本任务的方案/代码/性能验收 review 未执行。

## PM 验收与交接（PM）

W011已验收集成后，PM首次派发本任务的P1/P2调查阶段；本次可执行不代表优化实施获批或性能目标已验收。未参与调查/起草的reviewer `/root/w012_handoff_review` 已完成[派发要求独立复核](W012/handoff-review.md)，必须修正项0；受审草稿SHA-256 `c448de9107f625cce700e81eb0584700202e2b47acfd79d94087556e78c04976`。本次只补实际main/分支/依赖状态及PM接收元数据，行为要求/PP1–PP5未改；最终发布身份由Git及交接回复给出。执行交PP1–PP5证据及review后停止，由PM决定实施范围和后续交接。


### 独立执行 session prompt（仅 P1/P2）

```text
按 Layauto 项目规范，以独立执行 session 完成 W012 的 P1/P2“成本调查与具体优化方案”，暂不实施产品优化。
从 codex/w012-capture-wire-performance 的 PM 准备提交恢复；起点为含 W011 最终验收的 main。先核对远端完整SHA、工作区、AGENTS/协作/环境规则，读取W012、W011 PM2/原资源数据及必要架构和codec/来源合同。
本次只允许W012测量工具/自检、身份与命令原输出、成本分析、具体方案/目标建议及独立review。runtime、公开DTO/codec、正式测试、fixture/答案、架构和current-work不改。完成PP1–PP5，不因“调查可执行”直接重构wire或增加trusted绕过。
先固定输入URI/RunRequest/环境/对象保留顺序并核源，完成测量计划和轻量工具自检；串行运行normal direct、normal readback、原extraction_mismatch的完整公开构造/encode/decode，核正常5/7、实际4对source5、来源/局部图/T05/body及unsealed attempt不变。无插桩基准与profile分开，保留所有计时、wire、内存及失败；hook不得额外编码巨大对象制造瓶颈。
测清bytes/捕获重复保留、嵌套wire展开和constructor重复认证的实际贡献，区分共享对象、重复内容和inclusive时间。以数据提出具体实施方案、量化目标建议、回归/攻击面及wire版本/兼容/digest影响，交未参与设计的reviewer独立复核并关闭必须项。
调查阶段按相同runtime身份采信W011双全量/typing/安装，不重复小时级双矩阵；本次工具自检和三条实际测量路径不可省。未来优化实施才按“开发新增/受影响、最终冻结双全量”验收。
使用项目noreply身份提交推送原W012分支并核远端完整SHA，交PM；不自行验收、合main、改current-work或启动优化实施/下一任务。若方案需改变关键对外行为/格式或架构，给PM具体实例和影响，不能猜测批准。
```
