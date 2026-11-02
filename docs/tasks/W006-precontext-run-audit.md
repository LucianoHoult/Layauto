# W006 — 运行入口与输入失败记录

让W005读取组件进入有运行身份的实际调用链：读取之前先建立run；坏输入能留下同一run下的读取事实、解析错误、失败记录和最终拒绝结果；正常输入携带证据交给后续Stage 2。

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| ID / 目标 | W006；实现process-local的pre-context入口、审计与失败终结，成功读取交接仍为unsealed |
| 里程碑 / 依赖 | M1的第二个产品切片；依赖已验收W003/W004输入与W005组件。W005经[PR #59](https://github.com/LucianoHoult/Layauto/pull/59)合入main `4db3aa81d6f01496a680bdcb264afe99cd80f3f3`，验收见[W005 PM4](W005-input-reading-binding.md#pm4-integration-20261102)；完整M1仍待后续组合 |
| 授权依据 / 当前阶段 | 用户2026-11-02交回专门session的独立合并前review；沿用独立执行session。**可执行（局部补修）：W006 IPMR-01为P2必须修正项，阻止合并。** 原[PM1](#pm1-20261102)技术接收及合并建议因新反例暂停，当前处置与修复交接见[PM2](#pm2-ipmr01-20261102)；尚未验收或合并W006 |
| 恢复位置 | `codex/w006-precontext-run-audit`；独立review交付`ccd157fe1a3dee4267d4f0b119a4eda53cfdcf9f`，产品/回归仍为`cc42ae62585755b0b914d4dbec43324941bfe7c6`，尚无IPMR-01产品补修。接手包含PM2的后续文档提交，准确SHA见Git/回复。先核对远端、HEAD及已有差异，不假定临时环境/未提交文件跨session存在 |
| 允许修改 | `layauto_v2/pipeline.py`；新增职责明确的`repository/`、`tooling/`及必要中立`domain/` request/ids/results/publication合同；必要的W005读取/捕获接口重构；`tests/unit/`、`tests/contracts/`及真实文件组合测试；受影响typing/build配置、README及本任务执行/review附件 |
| 非目标 | 不实现Stage 2语义/空间/body/extraction及baseline/seal，不判断no_change，不实现ECO/Stage 5修改、Stage 6 geometry导出/完整报告，不运行真实EDA或生产上传，不承诺持久化/跨进程恢复；不发布新稳定CLI或新增必需外部输入文件，不改已验收fixture/答案/合同来迁就实现 |
| 架构依据 | 基线中的[architecture](../architecture.md) §2.1–2.2、§2.6–2.7、§9.2、§11.2/11.4/11.10/11.13/11.15、§12.1/12.6–12.7；以各段原文为准。另读[W002](W002-first-input-admission.md) E6/E7/R4、[W003合同](W003/contracts.md)共享记录/失败/F1–F2与[W005后续组合表](W005-input-reading-binding.md#pm已确定的任务拆分) |
| 分工 / 阻塞 | 一名执行者完成IPMR-01局部修复，未参与该修复者独立复核关闭；PM维护阶段并重新核验。IPMR-01关闭前阻止合并及后续产品推进；本次修复属于既定A7，无新的用户预期待决 |

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

本轮内部接口方案与时序保存在[interface-plan](W006/interface-plan.md)。未参与实现的 reviewer 在实施前提出 IR-01（已发布审计后的稳定恢复请求）与 IR-02（路径基准及捕获身份），执行者修正后由其独立关闭，见[接口 review](W006/interface-review.md)。以下起步要求保留作为原派发依据；实现没有新增外部 manifest 或稳定 CLI。

起步先补一页内部API/DTO与调用时序方案，至少给出：

- caller raw request/入口可得digest与后续实际读取事实的区别，F1完整性如何验证；无需新外部manifest文件。
- acquisition与现有reader如何共享同一捕获bytes，ToolRun/Parse单向关联及早期配置失败如何记录；必要重构保持W005组件入口兼容。
- 输入就绪结果如何交接仍unsealed attempt，以及repository-owned content/refs的读回方式。
- create/finalize的atomic root、revision/phase/幂等及失败注入点；freeze失败专门路径如何不放开普通unsealed close。
- 意外Exception、interrupt、terminal存储失败时能承诺/不能承诺的结果；新增模块的typing、解释器与安装验证安排。

执行者调查现有v2与legacy候选，说明可取用的纯逻辑及不适用部分，不能引入归档runtime依赖。请未参与实现者独立检查方案与上下游合同；原范围内修正后继续实现，不在普通内部设计完成后停下来要求用户再次确认。若确需新增强制外部输入、改变site解释、改变run成功语义或扩大durability/生产承诺，准备具体实例、依据和影响交PM/用户，不静默决定。

## 执行结果（执行）

### E1 恢复、实现与交付身份

2026-11-02，以执行角色接手。初始 checkout 为干净的 `work@4db3aa81d6f01496a680bdcb264afe99cd80f3f3`；获取目标分支后核对 `FETCH_HEAD` 与用户交接 SHA 一致，切换到 `codex/w006-precontext-run-audit@7320e5d6e819a422e0a446309eb039b1f05e7dd0`，无已有 staged/unstaged/untracked 修改。根 AGENTS 为唯一适用规则，已读协作/环境、架构原条款和 W002/W003/W005 双方合同。

执行集成由 `/root` 负责；publication 与测试子任务在各自 worktree 进行，集成后统一验证。接口和最终 reviewer 均未参与产品实现。已有 W005 exact codec、SourceFile/evidence 和 parser 被复用；调查 legacy pipeline 后未迁移其先解析 site、隐含默认路径及输出写回逻辑，没有新增 archive runtime 依赖。

| 版本 | 可复核内容 |
| --- | --- |
| `36161ca84f69de589a2733ad94d5c7a41a892cf3` | 首次完整实现与测试；[R1证据](W006/verification/r1/engineering-receipt.json)只证明该版本，不能覆盖 review 补修 |
| `3a597742b72d29971f56b9e47e1bf7147ec068f3` | CR-01/02/03 首次修正；64 项定向通过，review 又发现 CR-02 空消息 fallback 遗漏。该版本未执行完整工程矩阵，不作为最终交付验证 |
| **`cc42ae62585755b0b914d4dbec43324941bfe7c6`** | **最终产品与回归版本**；补齐空消息诊断，所有独立 findings 复核关闭。后续交付提交只保存本任务执行/review与验证证据；准确交付/远端 SHA 以 Git 和交回 PM 的回复为准 |

### E2 A1–A8 覆盖与实际行为

| 要求 | 实现与验证结果 |
| --- | --- |
| A1 | `prepare_inputs` 首先 `create_attempt`，成功取得身份后才驱动 parser。正常、缺失、坏 site 顺序 spy 通过；create 存储失败/typed conflict 均不读取解析，稳定 caller run/key 支持响应丢失重放。 |
| A2 | 独立测试 caller 按实际选择构造完整 5+9+13 声明，并单独对照 F1 样张；产品不知道27项或样张路径。声明 hash 与实际 bytes 分别冻结，漂移返回 InputDrift，未读声明返回 UnreadSelection；第二套名字、raw路径与site文件名通过。捕获时路径映射避免 symlink 切换重读；未捕获的 `link/../source.cdl` 不获错误绑定。 |
| A3 | Tooling 实际捕获 SourceFile，经 pipeline send 回同一个增量 parser；正常31份读取（含4个可选缓存）返回 unsealed InputsReady 与可解析 refs。显式 versioned wire/typed refs、nested alias、canonical digest与跨进程 hash-seed 检查通过；无 canonical context、baseline、seal或成功terminal。 |
| A4 | 临时副本覆盖已验收 missing_terminator 的坏header/raw并去掉对应cache，再构造声明。真实错误为 MissingTerminator；ToolRun读取成功、Parse失败、StageFailure定位/raw SHA、completed evidence、failure RunRecord、closure及terminal reject沿同run可查。未用提前hash mismatch代替解析错误，未声称调用Calibre。 |
| A5 | Repository mutex + 单 immutable composite root 同时拥有 content、attempt与幂等。create/finalize丢响应、同key同digest、异digest竞争、16线程重放及读者不可见半记录通过；4线程真实入口同request只获取一次。失败checkpoint保存原finalize请求，terminal写失败后即使磁盘输入改变也不重读。 |
| A6 | 首次执行检查head/revision/phase/mode与run/ref/hash；错误head/revision、错run/ref/hash、terminal后新mutation及partial均typed拒绝。幂等命中先于已变化的guards。没有未实现seal/initialize/正常close/partial假成功接口。 |
| A7 | RunRecord构造失败只发布run_record_freeze_failure closure与reject，原StageFailure/audits保留。terminal切换前失败明确未发布；切换后丢响应通过实际读回确认。审计存储或ToolRun构造失败交回PublicationUnavailable及内存facts，不伪造terminal。意外异常保留InternalStageFailure/cause chain；格式化失败、surrogate、空消息及诊断再失败均不替换原KeyboardInterrupt/SystemExit。 |
| A8 | Python3.10/3.12完整读取与新入口回归、strict typing、新sdist/wheel、干净wheel安装及源码外正常/F2 smoke均通过；实际矩阵与限制见E3。 |

Repository只提供本切片所需create、audit/checkpoint、pre-context finalize及readback。路径/bytes获取、解析、发布分别由tooling/importers/repository拥有，只有pipeline编排。原 `read_inputs` 签名和组件异常传播保持；fixture、答案、support、W003/W004/W005历史、architecture、current-work与legacy均未改。

### E3 最终工程证据

最终受测源码清单：[source-manifest](W006/verification/final/source-manifest.json)，覆盖214项产品/测试/fixture/配置/说明；工程快照、构建包及逐文件来源见[engineering-receipt](W006/verification/final/engineering-receipt.json)和[构建身份](W006/verification/final/build-artifact-identity.json)。[完整命令](W006/verification/final/commands.txt)保留独立工程检查的实际cwd、解释器、参数和退出码。主线程开发版命令在仓库根执行，源码在检查前后均与最终产品提交相同。

| 实际环境 / 命令 | 结果与证据 |
| --- | --- |
| Linux x86_64，CPython3.12.14；`python -B -m pytest -p no:cacheprovider tests/unit tests/contracts -q` | **389 passed，117.01s**；[日志](W006/verification/final/pytest312.txt)、[环境](W006/verification/final/environment312.json) |
| CPython3.10.22，最终commit独立snapshot；同一完整pytest命令 | **389 passed，153.98s**；[日志](W006/verification/final/pytest-310.txt)、[环境与实际导入位置](W006/verification/final/environment310.txt) |
| 两解释器 `python -m mypy`（strict，Python3.10语法） | **21 source files，无错误**；[3.12](W006/verification/final/mypy312.txt)、[3.10](W006/verification/final/mypy-310.txt) |
| 最终commit导出的源码执行 `python -B -m build --outdir <dist>`，新Python3.12环境安装wheel | 默认先构建sdist再从sdist构建wheel；构建、安装和pip check通过；[build](W006/verification/final/build.txt)、[install](W006/verification/final/wheel-install.txt)、[pip check](W006/verification/final/wheel-pip-check.txt)。wheel/sdist中74个包源文件与Git相同，含py.typed，无tests/legacy runtime。 |
| 干净安装、源码外执行[wheel_smoke.py](W006/verification/wheel_smoke.py) | 27项声明→InputsReady/unsealed、refs读回及重放；真实F2→MissingTerminator/reject均通过，[日志](W006/verification/final/wheel-smoke.txt)证明导入来自新venv的site-packages。 |

最终wheel SHA-256为 `ca51366350ce95aba68df523ffaee653cd546a52ad8cfb0f61348bcfa430e8b0`；sdist为 `9e802f092248b57d469bc5992f227ad3f55016f56d9c0e5c52a6ef30bc153724`。日志、manifest和可重运行smoke随Git保存；本机临时venv/build目录不当作跨session交付。

### E4 Review处置与交回PM

接口IR-01/02及最终CR-01/02/03均按原要求修正，原finding与复现保留，独立关闭见下方review段。CR-02修正复核追加的空消息反例也已补回归并关闭；执行者没有代写reviewer结论。最后一次产品改动后重新运行完整双解释器矩阵并重新构建安装包，没有沿用旧包证明新源码。

**未执行/不在范围：** Stage2语义/空间/body/extraction、baseline/seal/no_change、Stage5 ECO/完整mode矩阵、Stage6几何导出/完整报告/正常terminal、完整M1；真实Calibre/Virtuoso/PDK、matched/live或生产准入、隔离生产上传；durable存储/跨进程或断电恢复、crash/OOM当场结果保证；其他OS/解释器，Python3.10的干净wheel安装（3.10执行完整源码测试，干净安装为3.12）；legacy回归和fixture重生成。没有启动下一任务。

用户已授权本任务提交推送；执行交付到指定W006分支并核对远端完整SHA后交回PM。PM仍负责接收/验收、current-work与集成决定；本轮不自行验收、合并main或删除分支。

### E5 IPMR-01 局部补修（2026-11-02，执行）

按 PM2 接手：初始为干净的 `codex/w006-precontext-run-audit@ccd157fe1a3dee4267d4f0b119a4eda53cfdcf9f`，远端 W006 为用户指定的 `e8fec97b918938a5b431eb8ad38c2d63ed67e9d2`；核对其仅含 PM 交接文档后 fast-forward，main 仍为 `4db3aa81d6f01496a680bdcb264afe99cd80f3f3`。没有覆盖已有修改或 reset/force push；沿用根 AGENTS、协作/环境规则及 W006 A7、architecture §2.7/11.13、W003 失败合同和现有接口边界。

**补修产品与回归提交：`f19ac0448a5d0111f799660bd7be043ebfd16e41`。** 产品仅改 `pipeline.py` 的 ToolRun freeze 异常分支：已有 `StageFailure` 不再被覆盖，保留原 type/message/cause chain；二次冻结失败仍由 `PublicationUnavailable.operation/message/causes` 单独表达。没有原 failure 时继续创建冻结诊断；sources/events/completed evidence 和未发布状态保持，未改 DTO/schema，未借用 RunRecord freeze closure。新增 `test_w006_ipmr01.py` 保护 parser/acquisition 双 Exception、两层 cause、空消息/surrogate/坏 `__str__`、单独 freeze 失败及原 KeyboardInterrupt/SystemExit 对象传播。

| 本轮实际验证 | 结果与证据 |
| --- | --- |
| 原复现先红后绿 | 未改原 `double_exception.py`：补修前 exit 1，仅二次 ValueError；修后 exit 0，原 RuntimeError→LookupError 与二次 ValueError 分开，27 sources/8 evidence 保留，checkpoint/terminal 均无。[前](W006/ipmr01-verification/repro-before.txt)、[后](W006/ipmr01-verification/repro-after.txt)。 |
| 新增持久回归先红后绿 | 同一份测试字节在旧实现 **8 failed / 8 passed**，修后 **16 passed**；[前](W006/ipmr01-verification/regression-before.txt)、[后](W006/ipmr01-verification/regression-after.txt)。这两次在产品提交前运行，实际文件身份及最终提交映射见[identity](W006/ipmr01-verification/product-identity.json)。 |
| 最终提交 Python 3.12.14 完整回归 / typing | `python -B -m pytest -p no:cacheprovider tests/unit tests/contracts -q`：**405 passed，134.53s**，覆盖 W005 原回归、正常/F2、原诊断回归及本次新增；strict mypy **21 source files 无错误**，pip check 通过。[pytest](W006/ipmr01-verification/pytest312.txt)、[typing](W006/ipmr01-verification/mypy312.txt)、[环境](W006/ipmr01-verification/environment312.json)。 |
| Python 3.10.22 受影响回归 / typing | 独立 snapshot 的五个 W006 测试文件首轮 **120 passed / 1 failed**：工程快照漏带 F1 样张 `docs/tasks/W003/examples/records.json`，报 FileNotFoundError。原样补入同提交文件后，失败的 1 项定向重跑通过；两次共 **121 个不同用例通过**，不冒记单次全绿。strict typing **21 模块通过**。首轮、补跑及 snapshot 修正身份均保存在[工程回执](W006/ipmr01-verification/engineering/engineering-receipt.json)。 |
| 最终源码新构建与干净安装 | 从 f19ac04 导出的源码构建 sdist→wheel，新 Python 3.12 venv 安装/pip check、源码外 `-I` 正常/F2 smoke 和 parser/acquisition 双异常 smoke 均通过；新包各 74 个产品文件与 Git 一致。初始 snapshot 216 项，补入 F1 测试样张后 217 项；补入项不改变包源文件，无需重建。[包身份](W006/ipmr01-verification/engineering/artifact-identity.json)、[正常/F2](W006/ipmr01-verification/engineering/wheel-normal-f2-smoke.txt)、[双异常](W006/ipmr01-verification/engineering/wheel-ipmr01-smoke.txt)。 |

完整命令、cwd、解释器、退出码、日志 hash、源码/包身份及采用边界见[补修执行回执](W006/ipmr01-verification/receipt.json)。本次新 wheel SHA-256 为 `8b71ed7438c1c95e1987d13d08c4dce23d21fc80e91d86a339d260b83ef5e064`，新 sdist 为 `31dc9826729e5488c867bb3451dd62c8b234663b461a958c30afc884aa033d63`；未用旧 cc42ae6 的包证明新修复。新包 bytes 在本轮可用并已核验，临时 venv/dist 不假定跨 session 存在。

本轮主线程执行修复；`/root/ipmr01_engineering` 独立完成 3.10 与包工程验证；未参与修复的 `/root/ipmr01_fix_review` 负责[补修独立报告](W006/ipmr01-fix-review.md)及 reviewer 追加，finding 是否关闭由其判断，执行者不代写。原 finding/复现/历史报告、fixture/答案、W005 输入定义、PM 段、任务阶段和 current-work 均保留。未运行 3.10 的 W005 全量或干净 wheel 安装、其他平台、legacy/fixture 生成、真实 EDA/生产、durability 或 Stage2–6/完整 M1；这些不由本补修宣称通过。提交推送本次产品、回归及执行/review 证据后交 PM 重新接收，不自行验收、合并或启动下一任务。

## Review 结论（reviewer）

接口 review 见[独立接口报告](W006/interface-review.md)，IR-01/IR-02 已修正并独立复核。最终代码 review 见[独立代码报告](W006/code-review.md)，主审 `/root/final_review` 与 repository 专项均未参与实现。

最终受审产品/回归提交为 `cc42ae62585755b0b914d4dbec43324941bfe7c6`；CR-01（解析中途路径漂移/捕获）、CR-02（诊断替换中断及空异常消息）、CR-03（未捕获路径别名误绑定）均保留原反例并经独立复核关闭，**剩余必须修正项 0**。版本、五个复现及修正后 73 项专项回归、12 项真实文件代表组合、21 模块 strict typing 证据见[review身份清单](W006/review-verification/identity.json)及报告。正常读取仍仅 unsealed InputsReady；此为技术 review，不代写 PM 验收、main 集成或完整 M1 结论。

### IPMR1 独立合并前复核（2026-11-02）

本次独立 reviewer 以 main `4db3aa81d6f01496a680bdcb264afe99cd80f3f3` 为 base，交付 `cd1c847e74dc399ce32eeaf01c1ff5ab825c000d` 为 head，核对产品/回归仍为 `cc42ae62585755b0b914d4dbec43324941bfe7c6`。报告见[独立合并前复核](W006/independent-premerge-review.md)。先按原合同及实际 diff 检查，再核对历史 review/PM 证据，未以既有接收替代判断。

**新增 IPMR-01（P2，必须修正），剩余必须修正项 1，阻止当前版本合并。** parser 意外 Exception 后若 ToolRun 诊断冻结再次抛 Exception，`pipeline.py` 覆盖已建立的 failure，返回的 `PublicationUnavailable` 丢掉原异常及 cause chain。主审及只读 Repository 专项独立复现一致；[最小复现与输出](W006/independent-premerge-review.md#ipmr-01)随报告保存。需保留原 stage failure 并另记二次诊断失败，补双重错误回归后由独立 reviewer 复核；本轮未修改实现或自行关闭新 finding。

本次 Python 3.12.14 实际执行：W006 入口/异常/边界 49 项、Repository/边界 58 项（两命令重叠 2 项）、W005 原回归 284 项及 21 模块 strict typing 均通过；新增缺陷探针按合同断言退出 1。source/test/fixture/工程证据身份核对通过；原 Python 3.10 与构建安装证据按报告采用，原 wheel 不在本环境，未冒记重新核验包字节。IR-01/02、CR-01/02/03 原反例关闭依据保留；本条追加不改写原 finding、PM 接收事实或任务阶段。交 PM 安排修复和复核，不代替验收、main 集成或完整 M1 判断。

### IPMR2 局部补修独立复核（2026-11-02）

未参与补修实现的 reviewer `/root/ipmr01_fix_review` 以 PM2 交接 `e8fec97b918938a5b431eb8ad38c2d63ed67e9d2` 为 base，对产品/回归 `f19ac0448a5d0111f799660bd7be043ebfd16e41` 完成独立复核。[补修报告](W006/ipmr01-fix-review.md)保存依据、实际命令、证据采用和范围；原 IPMR1 finding、复现及历史报告保持原样。

**W006 IPMR-01 经独立复核关闭，剩余必须修正项 0。** 已有 StageFailure/cause chain 不再被 ToolRun freeze 的第二个 Exception 覆盖，顶层 PublicationUnavailable 单独保留二次诊断；无原 failure 时仍有冻结诊断。亲自运行原复现 exit 0、新增及旧 review 回归 **33 passed**，另两组独立探针确认原异常快照在二次格式化和诊断 readback 再失败时保持，未捏造 checkpoint/terminal；原 KeyboardInterrupt/SystemExit 对象传播不回退。

已独立核对本次执行证据：3.12 全套 **405 passed**、两解释器 21 模块 typing、新包干净安装源码外正常/F2及双异常 smoke。3.10 首轮 **120 passed / 1 failed** 的失败是 snapshot 漏带 F1 样张；补入同提交原文件后该项 **1 passed**，采用为两次运行共 121 个不同受影响用例通过，不冒记单轮全绿。reviewer 直接核验新 wheel/sdist 各 74 项产品 bytes 及最终 217 项 snapshot/Git/工作区身份一致。结论仅覆盖 PM2 局部补修；交 PM 重新接收，不代写任务阶段、PM 验收、main 集成或完整 M1 判断。

## PM 验收与交接（PM）

**当前结论见[PM2](#pm2-ipmr01-20261102)：W006 IPMR-01开放，暂停原技术接收及合并建议。** 以下原派发、PM1及其回执保留历史事实，不代表新反例已关闭。

**原派发记录（2026-11-02，已完成交回）：** 派发时只有任务要求和分支准备，未验收W006；执行者完成实现与独立review后，将本任务产物、证据及记录提交推送到`codex/w006-precontext-run-audit`，使用项目既有GitHub noreply身份，核对远端完整SHA并交回PM。远端变化先核对并安全集成，不force push；不自行验收、合并main、删除分支或扩展下一产品任务。该段保留原交接边界，当前接收结果见PM1。

**派发文档复核（2026-11-02，PM记录）：** 未参与草稿设计/编写的`w006_handoff_review`对照架构及W002/W003/W005完成独立检查，剩余必须修正项为0；整体交接中一处旧W005分支导航句已修正并复核。受审任务全文SHA-256为`59b296fa93d7fc72e59a9b68b46ce1e50819fdb27f7bd938dcef702c841e7179`，对应追加本段前的内容；六份文档的状态、103个本地链接、相关锚点及W005集成身份/历史保护核对通过。此为派发要求review，不替代未来接口方案或产品代码review。

<a id="pm1-20261102"></a>
### PM1 分支技术接收（2026-11-02）

**结论：A1–A8在本任务范围内满足接收条件，剩余必须修正项0；建议合入main后完成集成验收。** 当前阶段仍为待验收，集成状态为未合并；本轮没有合并、删分支或启动下一产品任务。正常输入只交接unsealed attempt，不能据此宣称完整M1或整轮运行成功。

PM从干净工作区取得并核对远端交付`628cc94383fa4c68bd44de51117ef06451ed3a9e`，最终产品为`cc42ae62585755b0b914d4dbec43324941bfe7c6`。直接检查pipeline、读取/捕获接口及W005兼容性，并委派未参与该实现的repository/domain与证据专项；原接口IR-01/02、代码CR-01/02/03及CR-02空消息追加项均保留且独立关闭，无新增必须修正项。详细命令、输出、环境与采用边界保存于[PM接收回执](W006/pm-receipt.json)。

| 核验方式 | 实际结果 |
| --- | --- |
| PM本机完整回归 | Python3.12.14，`python -B -m pytest -p no:cacheprovider tests/unit tests/contracts -q`：**389 passed**；包含W005读取、真实正常/F2入口及W006失败/重试组合。仅有第三方anyio的pytest弃用warning |
| PM本机strict typing | `python -B -m mypy --cache-dir /workspace/work/w006-pm-mypy-cache`：**21 source files，无错误** |
| 独立repository专项 | 核对单root原子发布、幂等优先、稳定失败checkpoint和unsealed边界；[公共API探针](W006/pm-verification/repository_scope_probe.py)验证错ref/hash/run拒绝、切换前失败/切换后丢响应重放、freeze诊断异常及原始中断传播，无半发布 |
| 身份与历史保护 | 214项source、88项tested-source、116项fixture在最终产品、交付及工作区一致；31项工程证据hash、16项review身份及接口方案hash一致。最终产品后99个变化路径均为docs；fixture、答案、support、架构及W003/W004/W005历史未改 |
| 采用已核对的独立证据 | Python3.10完整389项、两解释器typing、新sdist/wheel、Python3.12干净安装及源码外正常/F2 smoke均对应最终产品。原W006环境与wheel不在本机，74个wheel产品文件身份采用已发表的独立review核验，不冒记为PM本轮重建或重验原包 |

PM本轮未重跑Python3.10、构建/干净安装或fixture生成；原执行也未覆盖Python3.10干净wheel安装、其他平台/解释器、真实EDA/生产、durability及后续Stage2–6。源码回归环境复用现有PM虚拟环境，明确不作为干净安装证据。

下一步先核对拟合并head与已审产品身份，完成main合并及受影响组合验证，再记录W006最终验收。之后收敛后续Stage2任务：把输入转换为内部模型并完成该阶段校验，继续明确baseline/no_change、Stage6闭环的任务归属；本轮不提前实现或宣称这些能力。远端main在接收时仍为`4db3aa81d6f01496a680bdcb264afe99cd80f3f3`。

<a id="pm2-ipmr01-20261102"></a>
### PM2 接收独立复核与局部修复交接（2026-11-02）

**接收W006 IPMR-01为P2必须修正项，当前1项开放，阻止合并。** 独立review交付`ccd157fe1a3dee4267d4f0b119a4eda53cfdcf9f`只增加报告、复现及reviewer记录；产品、fixture与测试相对`cc42ae6`未变。PM核对[报告](W006/independent-premerge-review.md#ipmr-01)、pipeline控制流与既有DTO，并在Python3.12.14复跑原[double_exception.py](W006/independent-premerge-verification/double_exception.py)：实际退出1，原RuntimeError/LookupError均丢失，只剩二次ValueError；27份来源、8份completed evidence仍在，checkpoint/terminal为空。实际命令与输出见[PM复现回执](W006/ipmr01-pm-reproduction.json)。本轮只复现此缺陷，没有重跑全套测试或构建。

PM1的389项通过及历史findings关闭记录保持原事实；它们没有覆盖这次普通异常叠加诊断冻结异常的组合，不能继续作为当前无阻塞项的结论。无需重开W003/W004样本或改变W005输入定义，也不增加外部输入、持久化或新阶段承诺。

**修复目标与边界：** 在ToolRun冻结失败时，保留已经构造的原StageFailure及cause chain；二次冻结异常由`PublicationUnavailable.operation/message/causes`表达，`pending_failure`保存原失败。此前没有failure时仍需给出冻结异常对应的诊断。现有DTO足以表达这两层原因，优先局部修正；具体实现由执行者负责。继续保留实际sources/events/completed evidence，不伪造ToolRun、checkpoint、terminal或RunRecord；ToolRun冻结失败不改走repository的`run_record_freeze_failure`分支。原KeyboardInterrupt/SystemExit对象继续传播。

**关闭条件：** 原复现及新增持久回归证明parser/acquisition意外Exception（含cause chain）后freeze再失败仍可区分两层原因；检查保留的bytes/hash/events/evidence与未发布状态。单独freeze失败、空消息/非法Unicode/坏`__str__`、原始中断传播的既有能力不回退。最终补修版本须有受影响回归、正常/F2组合、W005保护及strict typing验证；Python3.12完整回归、Python3.10受影响回归和最终源码的新构建/干净安装smoke分别记录实际结果。原双解释器389项及旧wheel只能证明旧版本，不能代替新修复验证。未参与补修实现的reviewer复核后决定是否关闭，交PM重新接收；关闭前不合并或进入后续任务。

#### IPMR-01独立执行session prompt

```text
按Layauto项目规范，以执行角色完成W006 IPMR-01局部补修，并安排独立复核。
从codex/w006-precontext-run-audit包含PM2的最新PM交接提交恢复；review基线ccd157fe1a3dee4267d4f0b119a4eda53cfdcf9f，产品仍为cc42ae62585755b0b914d4dbec43324941bfe7c6。核对远端、HEAD及已有修改，不覆盖或force push。
读取AGENTS、README、协作/环境规则、current-work、W006 PM2及原行为要求7/A7、独立合并前报告和复现，回查相关architecture原文与接口合同。
先运行原double_exception.py确认失败，再作最小修复：原stage failure/cause chain不被第二次ToolRun冻结异常覆盖；两层原因均可查，已有bytes/hash/events/evidence保留，未发布则仍明确无checkpoint/terminal。
保留没有原failure时的freeze诊断、空消息/Unicode/坏__str__处理与KeyboardInterrupt/SystemExit原对象传播；不把ToolRun冻结失败伪装成RunRecord冻结失败，不改schema/输入/fixture/答案来迁就实现。
补parser及acquisition双Exception的持久回归；按PM2关闭条件验证。运行3.12完整回归、3.10受影响回归、strict typing；以最终补修源码重建包并验证干净安装下正常/F2及本缺陷路径，准确记录实际矩阵、源码/包身份和未执行项，不沿用旧包证明新修复。
请未参与补修实现者独立复核原复现及相关边界，保存W006/ipmr01-fix-review.md并追加任务reviewer记录；执行者不得自写关闭结论。原finding、复现和历史报告保留，执行记录追加在W006执行区。
提交推送代码、回归、必要证据与执行/review记录到当前W006分支，沿用项目noreply身份，核对远端完整SHA交PM。不自行验收、合并main、删除分支或启动下一任务。
```

### 独立执行session prompt

以下为已完成派发的历史prompt，保留原授权与范围；当前恢复应从PM2的IPMR-01补修交接继续，不重新执行本段。

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
