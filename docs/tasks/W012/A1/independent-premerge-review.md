# W012 A1 独立 session 合并前复核

**复核通过，可交 PM 安排 main 集成及实际合并版本的组合验证；新增及剩余必须修正项均为 0。** 结论绑定下列 base/head 及实际源码，不代写 PM 最终验收或 W012 整体完成。

Reviewer：本次独立 session `/root`，未参与 A1 设计、实现、正式测试或性能工具。只读辅助 `/root/nested_contract_audit`、`/root/performance_audit`、`/root/engineering_audit` 也未参与此前工作；辅助分别写本次独立证据，最终判断由本 reviewer 负责。日期：2026-11-11。

## 恢复、规范与完整范围

首次实际 `ls-remote` 核得 main `0a3326aa363477724465886cd05874d0997fba3e`、A1 `e4179dd42cc0de853df73bafd9140a363c8fa5be`；`/workspace/Layauto` 初始为干净的 `work` 分支，HEAD 在 main 起点，无 staged/unstaged/untracked 修改。明确 fetch 原分支引用后恢复 `codex/w012-compatible-hex-validation`，仅一个工作树，无已有写入冲突，故不另建 worktree。后续[范围检查](premerge-review-evidence/scope.json)再次实核相同远端完整 SHA、祖先关系及全仓唯一根 `AGENTS.md`。当前云环境标识与选定 executor 一致。

实际读根 AGENTS、README、docs 导航、协作规则和本地/远端环境规则；读 W012 I1–I6/PM1–PM3、A1 方案/方案 review、执行/性能分析、原独立 review、A1-R01 及原输出/关闭证据。回查 architecture §2.2–2.3、§2.6、§3.7–3.8、§11.2/11.9/11.15、§12.8，以及 W005–W011 来源、不可变、公开 constructor/嵌套 codec 和异常合同。未将磁盘文件存在或旧摘要当作本次执行通过。

| 身份 | 完整提交与本次核对 |
| --- | --- |
| main / 本次 review base | `0a3326aa363477724465886cd05874d0997fba3e` |
| A1 准备 | `7f7c1304bdafd941791421cef64864fb1616303c` |
| 产品/正式测试冻结 | `ca1f810c3c97376f71089d8b4054760ff198012f`；263 源/测试/配置逐项与本次 head 相同 |
| 性能编排冻结 | `d9d68475fefbeb420e738ad2ee5c2b6e92e7c5ec`；原工具/运行身份另核 |
| 最终工程 source-manifest 的记录起点 | `212554cdc402f6b86e92b8b81cd43752a01ff858`；不误当产品冻结提交 |
| 原独立 review 所审提交 | `44a91c472fdeba5bb4b8a6071c0580313336c379`；263 文件及100 runtime 与本次逐项等价 |
| 原执行交付 | `db07a16fb7cbbac030adae84a9eb88cc0c8aa650` |
| 本次受审、含 PM 接收的 head | `e4179dd42cc0de853df73bafd9140a363c8fa5be` |

完整 main→head 为 **595 路径：593 文档/调查工具/证据、1 runtime、1 新增正式测试**。前序 P1/P2 调查尚未合 main，已纳入审查：旧92项交付 manifest、六路原命令/输出、工具、成本分析/方案及原 R01（outer bytes 222/222/217）均闭合，35项 mismatch origin bytes 本机逐项重读长度/hash。旧任务文本按其原 review commit 的 Git blob 核验，后续合法追加不能误判为旧证据被改写。A1 准备之后原 P1/P2 附件未变。原独立 review 后107路径是 review/证据封包和 PM 接收；已实际核源码等价，未只看提交名称。

现有 README/current-work 的 PM 更新属于待审交付，内容仍明确 main 未集成、后续范围未启动；本次未修改它们。此次写入仅本报告、新独立证据及 W012 reviewer 区追加。

## I1–I3：产品、语言、canonical 与异常

唯一产品 diff 为 `domain.codec._decode` 的 bytes 条件从 `re.fullmatch(r'(?:[0-9a-f]{2})*', raw)` 改为 `re.fullmatch(r'[0-9a-f]*', raw) and len(raw) % 2 == 0`，另两行说明。原 `isinstance(..., str)`、`fromhex`、错误 raise、JSON duplicate-key/非精确数字拒绝及最终 canonical bytes 复验均保留。没有 encoder、schema、签名、digest/ref、catch/trusted/cache 或 constructor/认证次数变更；原正式测试无删改，只新增51项。

令 H 为16个小写 ASCII hex 字符，原 `(HH)*` 与 `H* ∩ 偶数长度` 相同，含空串。本次另做[独立实际探针](premerge-review-evidence/contracts/probe.py)：从 Git 读取并执行两份真实 codec 源码，以独立逐 nibble 状态机生成 bytes（无正则、len/parity 或 fromhex oracle），核 **150,728 个有限候选**：全部 Latin-1 对（包含全部 ASCII 对）、65,536种二字节的合法四字符表示、7字符字母表长度0–5、Unicode见证及131,072字符合法前缀的长尾。接受/拒绝、结果、canonical bytes 和错误类型/参数前后相同；不是只比新旧 matcher 或复述数学证明。见[结果](premerge-review-evidence/contracts/result.json)、[成功命令](premerge-review-evidence/independent-probe-r3.command.json)及原 stdout/stderr。

另实际核19种畸形 tag/JSON、重复 key、浮点/常量、空白/换行、转义和 canonical 拒绝；观察合法 Unicode escape 经 JSON/hex 得到 bytes 后，仍由原最终 canonical 复验拒绝。真实公共 JSON `$bytes` 字段是原生 `str`，matcher 先执行一次（含奇数/非法输入），fromhex 仅对原合法语言执行。公共输入类型前后实测保持：canonical bytes、bytes 子类、bytearray 被现行实现接受，JSON 文本 str 在最终 bytes 对照拒绝，memoryview/None/int/list 为 TypeError；未按类型注解顺手收紧或另立新类型承诺。

matcher/fromhex 注入 ValueError/TypeError/KeyError/KeyboardInterrupt/SystemExit、两种 suppression，在两版各边界的40组独立见证中保持原 exception object/cause/context/suppression。私调 `_decode({'$bytes': 恶意str子类})` 的 `__len__` 新副作用已实际复现：原版接受，交付版传播该私有 len 故障。它与原方案 review 已披露的非阻断边界一致；公开 JSON 路径不注入该子类，不声称任意私有子类副作用等价。

七个公共/嵌套 codec 已实读：domain exact、publication、semantic、geometry、effective、local connectivity、channel identity。各层 `/1`、closed tag/字段/类型校验、子 decoder/constructor、完整 `_pack` 对照及最终重编码不变。publication 对历史无关 terminal/failure DTO 的有限翻译未被扩成捕获链 catch；各层捕获/来源/immutable/认证仍在。详见[静态合同专项](premerge-review-evidence/contracts/static-review.md)。

本机 Python3.12.14 新跑正式回归：新增51项及既有 W005 合同合计 **89 passed / 0.50s**，见[命令](premerge-review-evidence/targeted-formal.command.json)；另按风险串行运行完整嵌套、二次认证及 target/source 代表回归，**22 passed / 374.21s**，见[收集清单](premerge-review-evidence/affected-collection.stdout.txt)、[命令](premerge-review-evidence/affected-formal.command.json)和[原输出](premerge-review-evidence/affected-formal.stdout.txt)。本次正式回归合计111项，包含真实direct/readback完整wire后注入的跨层故障、4种预期错误后二次认证故障、公开builder/constructor再认证，以及target-only多轴/source L/W差异。没有重复原小时级双全量或18条 benchmark。

## I2、I5：完整 wire、来源与产品行为

原18条样本及两侧 profile 的完整结果检查核正常 MN0/MP0=5/7；原 mismatch 为实测4对source5，恰一项差异；完整36项 FIN evaluation/crossing、40 drawn records/18 FIN、来源/单位/owner、局部图14 nodes/8 edges/6 components、16 T05 pass、body6与完整 DTO roundtrip 保持。target 仍独立于 source；readback attempt/checkpoint 不变，unsealed、无 terminal。完整 smoke 检查器另逐项核31捕获原bytes/hash/ref及 crossing 坐标/来源，未以缩减根对象、捕获或短 wire 制造改善。

| 固定 URI 完整路径 | 每次 wire B | SHA-256（before/after/profile 对应身份保持） |
| --- | ---: | --- |
| normal direct | 54,050,313 | `4d07033687223809e542ea661138fe0566ed162f6eab17fb7d4f806745377f16` |
| normal readback | 136,471,701 | `1b75a398b4a2f22c156600fbe19590c182f37a77d0c171ab0a8b7a79e23cd795` |
| extraction mismatch | 54,045,042 | `83713d7586b02181697f10ac45c59490f2c3aa02fcea37ecf92b740a03b8e2b1` |

本机实际读取逐条命令、原 stdout/stderr、结果和完整 bytecmp 回执及 hash，核比较在被测阶段后以1MiB块覆盖全长。**原大 wire 本机不存在，本次没有重比18份 baseline 的约1.47GB或另两份 profile wire。** 原独立 reviewer 在受审 `44a91c472fdeba5bb4b8a6071c0580313336c379` 实际重读18份 baseline及2份 profile wire 的逐块实比，按本次确认未变的源码/工具/原记录采信。此层级与本次新运行的有限 synthetic 结果明确分开。

`performance/commands.json` 最后 `after-extraction-mismatch-r3`、`profile/commands.json` 最后 `after-normal-readback-r1` 确实缺 bytecmp 字段；对应单条 `.command.json` 和最终 receipt 保存相同、完整比较成功的记录，且 stdout/stderr/结果身份闭合。没有最后样本缺失的真实缺口，保留原索引及历史 hash，不回写历史。

## I4：18样本重算与归因限制

本次从真实18份 `wall_seconds` 分别求每次所有阶段之和，再取每路径每侧三次中位；未用阶段中位相加，也未混入 runner 启动/写wire/轮询。核同机/解释器/依赖记录、100runtime实际导入根、固定 URI/RunRequest/cache/roots/GC、fresh Popen及实际串行时间轴；before 是本轮旧源新测，baseline 无 hook/cProfile，profile及工程矩阵随后运行。没有把热缓存、少测、漏捕获或工程并发当产品收益。[性能独立专项](premerge-review-evidence/performance/report.md)及[重算原结果](premerge-review-evidence/performance/result.json)保留各次和逐阶段数值。

| 路径 | 阶段总秒中位 before→after | 整进程峰值KiB中位 before→after | 耗时 / 峰值下降 |
| --- | --- | --- | --- |
| normal direct | 94.418923→75.799891 | 2,851,076→325,436 | 19.72% / 88.59% |
| normal readback | 186.625165→144.066817 | 7,344,896→708,536 | 22.80% / 90.35% |
| extraction mismatch | 93.170488→79.514097 | 2,860,516→324,668 | 14.66% / 88.65% |

六处小阶段增幅保留：direct W005 +3.61%/W008 +2.46%；readback prepare +4.74%/W009 +0.65%；mismatch W008 +0.84%/encode +0.82%。三次样本不够判定噪声或稳定因果，也不表示所有阶段提速。20%/50%是旧完整兼容包建议，非 A1 硬门；wire减幅为0。

两侧 profile 的65次大hex窗口 phase/长度/顺序完全相同，最大118,841,892字符。归一 codec 两行位移后2333项可定位 runtime 函数计数逐阶段一致，含 constructor/认证/公开 codec；无减少重建或认证的迹象。旧窗口刷新 HWM 5次，新0次；最大窗口旧 HWM 3,604,172→7,326,636KiB，新501,568→501,568KiB，支持消除已定位的重复分组 matcher 瞬时峰值。

HWM不是净分配，不相加窗口或 inclusive 秒。新 profile 整进程仍720,336KiB（约703MiB），高于窗口上限648,896KiB；窗口后还有 decode 收尾、结果比较及 profile 收集，未做 allocator/逐函数分配归因。单次 profile decode 221.043995→222.849795s（+0.82%）如实保留，不能混成无插桩结果。136.5MB完整wire及重复序列化/重建仍是残余成本，不作生产/最大输入保证。

## I6：工程闭合、原中断与本次新证据

[工程独立专项](premerge-review-evidence/engineering/report.md)实际核263源/100runtime及 tar263成员；四个真实 before/after wheel/sdist 各100runtime，同侧格式 payload 相同，before 对 main、after 对冻结源；跨侧唯一 runtime payload 差异是 codec。不是只读包比较摘要或包名。最终21条内部命令与42份原 stdout/stderr hash、78项附件 manifest闭合；双解释器各1656、原1605 node ID全部保留且恰新增51，双 typing各54源文件通过。

after 两套安装原命令创建 fresh 环境，3.10 sdist/3.12 wheel，原100成员身份等于冻结源；两条 `-I -B` smoke 的 cwd 在源码/snapshot外，完整三路径与 readback 边界通过。本机原安装树缺失，因此原安装实读和完整 smoke 按同源、原输出及原独立 review 采信，本次未重装或重新读取旧安装树。smoke 输入 URI 指向snapshot，mismatch临时URI跨解释器不同，不能与固定 URI 的性能wire hash混比。

首轮26项 partial/原runner/snapshot、恢复计划和轮询断连均保留。约39%/43%不计通过；r2外层 wrapper 仍为started、无退出码，最终完成依据是内部21命令和闭合receipt，不补造wrapper exit0。第二次重连存活的detached子进程未重启；OOM=0不被当作原因证明。

原 A1-R01（中断重跑覆写证据）finding、buggy runner、隔离复现、正式样本前修复和原独立关闭均保留。本次另对实际当前runner独立运行四种非空stage探针，均在 Popen 前拒绝、旧字节不变；只替换身份/preflight以到达guard，不冒称完整runner新测。

本次独立探针前两次 checker 失败也保留：首轮共用 matcher/canonical 观察列表，次轮结果 JSON 含 bytes 未序列化；分别修正观察隔离/结果展示后第三轮通过。原 checker 快照与每轮原命令/stdout/stderr在 `premerge-review-evidence/`，不是产品finding。P1/P2补查的旧任务版本/旧 HWM 字段误读也保留失败原输出，按历史层级/字段修正后188项通过；未修改历史证据。

本次使用已有 `/workspace/.venvs/layauto/bin/python`（3.12.14），pip check通过、导入实际在本checkout，未安装依赖。正式检查禁用第三方pytest自动插件、字节码/cache写入，命令/环境与原输出完整保存。启动完整codec/readback代表回归前已核约17GiB可用内存且无其他测试/benchmark，全部串行。[环境/范围](premerge-review-evidence/scope.json)不冒认历史benchmark依赖/主机计时相同。

对原main→head运行 `git diff --check` 仅报两份原build stderr的EOF空行（`before-package/build.stderr.txt:9`、`verification-r2/build.stderr.txt:19`），原exit2/输出见[回执](premerge-review-evidence/reviewed-diff-check.command.json)。保留原输出及hash，不修剪历史stderr；此观察不属于产品或手写文档缺陷。本次新增手写内容另行检查。

## Findings、限制与交 PM

| 记录 | 版本、影响与处置 |
| --- | --- |
| 本次新增必须 finding | **0，剩余必须项0。** 未发现需要产品修复或补齐关键证据的可复现问题 |
| 原 A1-R01 | 正式样本前修复、原独立关闭；本次四种隔离guard见证支持继续关闭 |
| 已知非阻断边界 | 私调恶意str子类的len副作用、两索引末条字段缺失但单条/receipt闭合、约700MiB残余及六处阶段增幅，均保留原限制，不据此扩大承诺 |

本次实际读取/运行：真实源码/diff/规则、包与tar、原命令/输出、manifest、18样本和profile记录重算/计数、独立有限语言及异常探针、新正式89项及22项代表回归、R01隔离guard。未变双全量/typing/包安装/18次完整产品测量按版本证据采信；原大wire全长实比及原安装树实读依据来自原独立review。本次未重跑双解释器全量/完整前后benchmark、未本机重比全部原大wire/重新安装，也未验证生产或最大输入上界。

原before运行树及固定mismatch目标目录本机也不存在；本次旧codec来自已核Git blob，35项mismatch核的是可访问origin bytes及原运行记录，未冒称已在原固定URI重建/重测。本次代表回归用其正式synthetic fixture/临时目录，不拿其hash冒充固定URI性能身份。

本次证据核验数量与150,728有限候选均不冒充正式测试数。更广partial/unknown、来源/错型等值/alias负例按同一新源双1656及原受影响273项采信；本次22项按风险补充，不声称新增覆盖整个生产输入域。

PM可接收此 review，安排 main 实际合并版本的组合验证，并确认最终集成/验收。此次只提交推送原 A1 分支；main、PM阶段及current-work未由本 reviewer更改，不启动writer/reader/memo/B。交付最终SHA在提交后远端实核，不要求本报告包含自身最终hash。
