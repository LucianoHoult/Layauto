# W006 — 运行入口与输入失败记录

让W005读取组件进入有运行身份的实际调用链：读取之前先建立run；坏输入能留下同一run下的读取事实、解析错误、失败记录和最终拒绝结果；正常输入携带证据交给后续Stage 2。

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| ID / 目标 | W006；实现process-local的pre-context入口、审计与失败终结，成功读取交接仍为unsealed |
| 里程碑 / 依赖 | M1的第二个产品切片；依赖已验收W003/W004输入与W005组件。W005经[PR #59](https://github.com/LucianoHoult/Layauto/pull/59)合入main `4db3aa81d6f01496a680bdcb264afe99cd80f3f3`，验收见[W005 PM4](W005-input-reading-binding.md#pm4-integration-20261102)；完整M1仍待后续组合 |
| 授权依据 / 当前阶段 | 用户2026-11-02同意继续合并、验收并准备下一任务；沿用独立执行session。**可执行：先补内部接口方案并独立review，原范围内修正后直接实施。** 本次PM仅准备要求/分支，尚无W006产品实现或测试结果 |
| 恢复位置 | `codex/w006-precontext-run-audit`，从上述main集成版本建立，接手使用包含本任务的PM交接提交，准确SHA见Git/回复。先核对远端、HEAD及已有差异，不假定临时环境/未提交文件跨session存在 |
| 允许修改 | `layauto_v2/pipeline.py`；新增职责明确的`repository/`、`tooling/`及必要中立`domain/` request/ids/results/publication合同；必要的W005读取/捕获接口重构；`tests/unit/`、`tests/contracts/`及真实文件组合测试；受影响typing/build配置、README及本任务执行/review附件 |
| 非目标 | 不实现Stage 2语义/空间/body/extraction及baseline/seal，不判断no_change，不实现ECO/Stage 5修改、Stage 6 geometry导出/完整报告，不运行真实EDA或生产上传，不承诺持久化/跨进程恢复；不发布新稳定CLI或新增必需外部输入文件，不改已验收fixture/答案/合同来迁就实现 |
| 架构依据 | 基线中的[architecture](../architecture.md) §2.1–2.2、§2.6–2.7、§9.2、§11.2/11.4/11.10/11.13/11.15、§12.1/12.6–12.7；以各段原文为准。另读[W002](W002-first-input-admission.md) E6/E7/R4、[W003合同](W003/contracts.md)共享记录/失败/F1–F2与[W005后续组合表](W005-input-reading-binding.md#pm已确定的任务拆分) |
| 分工 / 阻塞 | 一名执行者负责集成；未参与变更实现者做接口及最终review；PM接收并维护任务阶段/当前入口。无新的用户预期待决；接口细化见下，不能将内部选择变成额外审批门 |

### 行为要求与边界

1. **先有运行身份，再解析输入。** 正式编排入口先经`PublicationRepository.create_attempt`创建unsealed revision 0，绑定caller跨重试保留的`proposed_run_id`、operation/key、lineage、expected starting head和raw request/入口可得selection digests。不为发现依赖而先解析site/header，也不预填canonical target、tech或evidence context。create失败不得继续解析或伪造已创建run。
2. **区分请求声明与实际读取事实。** F1测试caller可按已验收样张提交完整27项input/raw/config/policy选择和声明hash；产品不能加载`examples/records.json`获取答案，也不能写死27或固定文件名。声明hash与后续实际bytes独立核验，漂移明确失败。入口尚未取得的实际hash进入后续审计，不回填或改写已冻结request/digest；不能为此要求用户额外提供一种新manifest文件。site缺失、不可解析等情况仍需落在已有attempt下的失败链。
3. **真实获取→解析的单向记录。** `tooling`只记录实际fixture读取的execution facts，`pipeline`把同一次捕获的bytes/refs交给importer，ParseResult单向关联tool_run_id；ToolRun不包含解析结论、不反向引用Parse。保留W005原组件行为与同bytes解析/校验承诺。允许为共享捕获对象重构内部IO接口，禁止两次独立读取后仅凭同路径认定同源。`dummy_fixture`不声称调用Calibre、matched/live或生产通过；acquisition失败与parse失败分别归类，未读到的bytes不造hash。
4. **正常读取交给后续阶段。** 返回明确的内部“输入就绪”交接结果，携带同一attempt、已完成ToolRun/Parse/evidence refs及已验证输入。attempt仍unsealed、无canonical context；不seal、不构造baseline，不输出success/no_change/accept的terminal PipelineResult。该入口只承担pre-context切片，不能宣传为完整run已完成。名称与DTO细节留接口方案。
5. **坏输入形成完整失败链。** config/read/parse/binding等预期错误映射为中立StageFailure，保留run、stage、category/code、原始原因、定位和已完成审计refs；repository通过`finalize_precontext_failure`原子冻结最小failure RunRecord并发布唯一terminal reject。原始文件、实际hash、ToolRun、Parse、Failure及RunRecord可沿refs追溯。禁止未建立的canonical refs、ECO envelope、post-change geometry、success Manifest或ValidationResult。诊断报告可选，本任务不要求新的完整人机报告格式。
6. **Repository拥有发布和重试。** 使用架构已允许的process-local原子域，统一管理immutable content、attempt revision/phase/terminal pointer与幂等记录；pipeline不得自行更新pointer。首先在同一原子域检查`(operation, run_id, key)`及canonical request digest：same-key/same-digest返回原refs，即使revision/phase已推进；异digest typed conflict。首次执行才检查starting-head CAS、phase/revision及实际触及的mode约束。竞争、失败及重试不得留下半记录/半terminal。只实现本切片需要的public operations；未实现的seal/正常close/finalize/partial不提供假成功接口，不因缩小范围放开非法状态。
7. **双重失败与异常。** RunRecord构造失败采用唯一`run_record_freeze_failure` closure，保留StageFailure/completed audits并terminal reject；不创造第二种无RunRecord例外，不通过普通`close_stage5(unsealed)`绕过guard。terminal/storage失败保留已有事实和best-effort诊断，未发布则明确无terminal pointer，不能伪装reject已经持久可查。pipeline stage boundary将意外程序/基础设施Exception转为InternalStageFailure并保留根因，W005组件本身继续传播其意外异常；KeyboardInterrupt/SystemExit不得吞掉，best-effort记录不能取代重新传播。process-local不承诺crash/OOM/断电当场有结果。
8. **中立合同与既有能力保护。** 本切片实际交付的request、RunAttempt、ToolRunResult、StageFailure、RunRecord、closure和terminal结果具有runtime discriminated schema、版本、稳定typed refs及可重复canonical digest，递归不可变，无可写alias；跨记录run/ref/hash关系可校验，不用Python hash。`domain`无IO，repository不依赖transactions/importers/tooling，importers与tooling互不依赖，只有pipeline编排。已实现W005读取和错误测试继续通过，历史样张只作测试判据；不把sample records当作运行时对象或预制返回值。

### 验收清单

| ID | 条件 → 可观察结果 | 验证要求与限制 |
| --- | --- | --- |
| A1 入口次序 | 正常/缺失/坏site输入均先有create attempt，再有本次解析；create失败不继续读取解析链 | 真实编排调用加顺序spy；稳定caller run id在response-loss重试中保留；不以预先解析site绕过 |
| A2 F1请求与来源 | 完整27项样张选择在request中可核对，声明与实际read独立绑定；变化不修改原request | 使用实际文件及独立caller请求构造，定位input drift；第二套合法路径/选择证明非硬编码。生产入口不得读取records/oracle来填声明 |
| A3 正常交接 | 实际fixture经W005读取成功，返回同一unsealed attempt及可解析的immutable evidence refs | 核对schema、canonical digest、nested alias；无seal/baseline/state publication/成功terminal。不是完整M1通过 |
| A4 F2失败链 | 实际缺END OF RESPONSE的raw → fixture-read ToolRun → Parse → StageFailure → 最小failure RunRecord → terminal reject | 在临时副本应用已验收missing_terminator变体并核对header/raw；断言具体解析错误、bytes/hash、位置及completed，不由提前hash错误代替。工具记录不得装作真实Calibre |
| A5 幂等与原子性 | create/finalize响应丢失后same request返回原refs；同key异digest冲突；竞争只有一个发布结果 | 同一repository多调用/线程测试，读者看不到半记录/terminal；幂等先于已变化revision/phase guards。只证明进程内原子性，不宣称跨进程恢复 |
| A6 状态/关联守卫 | 错expected head/revision、错run/ref、terminal后新mutation、unsealed正常终结、未支持partial均明确拒绝 | 按实际接口和DTO进行反例；未交付Stage2/5方法不得靠empty stub返回成功，后续完整phase/mode矩阵仍保留 |
| A7 多重错误 | freeze失败有唯一无RunRecord的closure/reject；terminal写失败不谎报已发布；意外异常保留根因、中断继续传播 | 故障注入覆盖create、读取/解析、RunRecord freeze、terminal原子切换前后及响应丢失。核对实际持有的记录/refs与pointer；没有存储能力时不能保证可查terminal |
| A8 工程与范围 | 正常、F2及以上错误链经真实文件入口可运行；新结果/接口可从安装包导入 | 新单元/合同/组合测试及W005完整回归；strict typing覆盖新增模块；最低Python3.10与开发解释器验证；新sdist/wheel、干净安装和源码外正常交接/F2失败smoke。精确记录实际矩阵、未执行项及被测版本 |

F1/F2材料在[W003合同](W003/contracts.md)、[records样张](W003/examples/records.json)和[failures样张](W003/examples/failures.json)。运行时schema和字段组织由执行者按架构设计，不逐字复制`example_only`样张；不得削掉其operation/run/head/lineage/key、完整输入来源和失败记录义务。

### 后续组合归属

| 后续任务 | W006保留的义务 |
| --- | --- |
| Stage 2与baseline/no_change | 正常交接继续normalization，完整state/body/extraction/mandatory checks、seal/initialize、state-head与attempt联合CAS；其错误仍接入pre-context或sealed失败合同。C08/09/10/13及body几何等继续按W005表接收 |
| Stage 5与Stage 6完整M1 | no_change closure及整个phase/mode矩阵、readonly GDS/CDL/JSON导出、精度/overflow、readback/Manifest/Validation/Reporting/terminal组合；不能用W006的输入就绪替代正常terminal或M1验收 |
| 真实输入/工具与durability | G1–G5真实门、旧Virtuoso readback scope保持；process-local不自动升级为durable。MR-040配置机制精简另议，本任务不引入新的默认值/覆盖优先级 |

## 方案与决定（执行准备，PM 接收）

起步先补一页内部API/DTO与调用时序方案，至少给出：

- caller raw request/入口可得digest与后续实际读取事实的区别，F1完整性如何验证；无需新外部manifest文件。
- acquisition与现有reader如何共享同一捕获bytes，ToolRun/Parse单向关联及早期配置失败如何记录；必要重构保持W005组件入口兼容。
- 输入就绪结果如何交接仍unsealed attempt，以及repository-owned content/refs的读回方式。
- create/finalize的atomic root、revision/phase/幂等及失败注入点；freeze失败专门路径如何不放开普通unsealed close。
- 意外Exception、interrupt、terminal存储失败时能承诺/不能承诺的结果；新增模块的typing、解释器与安装验证安排。

执行者调查现有v2与legacy候选，说明可取用的纯逻辑及不适用部分，不能引入归档runtime依赖。请未参与实现者独立检查方案与上下游合同；原范围内修正后继续实现，不在普通内部设计完成后停下来要求用户再次确认。若确需新增强制外部输入、改变site解释、改变run成功语义或扩大durability/生产承诺，准备具体实例、依据和影响交PM/用户，不静默决定。

## 执行结果（执行）

未执行。执行者在此记录恢复位置、起点/产品提交、方案与实现范围、A1–A8实际命令/环境/结果、独立review处置及未执行范围。原W005验收与fixture记录保留，不代写PM阶段。

## Review 结论（reviewer）

未执行。接口review和最终代码review分别绑定明确版本；原finding保留，由reviewer填写独立关闭依据。报告放在`docs/tasks/W006/`；检查F1/F2真实链、先建attempt、same-bytes、所有权/原子性/错误和成功交接边界，不能只核对测试计数。

## PM 验收与交接（PM）

当前只有任务要求和分支准备，未验收W006。执行者完成实现与独立review后，将本任务产物、证据及记录提交推送到`codex/w006-precontext-run-audit`，使用项目既有GitHub noreply身份，核对远端完整SHA并交回PM。远端变化先核对并安全集成，不force push；不自行验收、合并main、删除分支或扩展下一产品任务。

**派发文档复核（2026-11-02，PM记录）：** 未参与草稿设计/编写的`w006_handoff_review`对照架构及W002/W003/W005完成独立检查，剩余必须修正项为0；整体交接中一处旧W005分支导航句已修正并复核。受审任务全文SHA-256为`59b296fa93d7fc72e59a9b68b46ce1e50819fdb27f7bd938dcef702c841e7179`，对应追加本段前的内容；六份文档的状态、103个本地链接、相关锚点及W005集成身份/历史保护核对通过。此为派发要求review，不替代未来接口方案或产品代码review。

### 独立执行session prompt

```text
按Layauto项目规范，以执行角色完成W006运行入口与输入失败记录。
从codex/w006-precontext-run-audit的PM交接提交恢复，先核对HEAD、远端和已有改动；W005已在main 4db3aa81d6f01496a680bdcb264afe99cd80f3f3合入，IPMR-01/FR1已关闭。
读AGENTS、README、协作规则、current-work、docs/tasks/W006-precontext-run-audit.md及引用的架构/W003 F1-F2合同。
先形成一页内部API/DTO/调用次序方案并安排独立接口review；原范围内修正后直接实现，不先开新的外部输入格式或把读取成功变成整轮成功。
落实parser前create_attempt、真实fixture读取与W005同bytes解析、F1完整request、F2失败链、process-local原子发布/幂等/守卫、freeze/terminal/interrupt边界，完成A1-A8。正常读取只交接unsealed attempt给后续Stage2。
保留已验收fixture、答案、历史review和W005组件能力；不做Stage2/baseline/no_change、ECO、Stage6导出或真实EDA。
实现完成后由未参与实现者独立review，修正必须修正项并复核关闭。保存实际代码版本、命令、矩阵、结果与未验证范围；不要只交本机临时附件。
提交推送本任务代码、测试及执行/review记录到当前W006分支，沿用项目noreply身份并核对远端SHA，交回PM。不自行验收、合并main、删分支或启动下一任务。
```
