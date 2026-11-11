# W012 A1 专门合并前 review prompt

```text
按 Layauto 项目规范，以未参与 A1 设计、实现、正式测试或性能工具的独立 session reviewer 身份，复核 W012 A1 是否具备 main 集成条件。

恢复 codex/w012-compatible-hex-validation 最新含PM接收记录的head，先核远端完整SHA、工作区和适用AGENTS，必要时独立worktree。main起点0a3326aa363477724465886cd05874d0997fba3e；A1准备7f7c1304bdafd941791421cef64864fb1616303c；执行交付db07a16fb7cbbac030adae84a9eb88cc0c8aa650；产品/测试冻结ca1f810c3c97376f71089d8b4054760ff198012f，性能编排d9d68475fefbeb420e738ad2ee5c2b6e92e7c5ec，最终工程source-manifest记录起点212554cdc402f6b86e92b8b81cd43752a01ff858。独立原review审44a91c472fdeba5bb4b8a6071c0580313336c379，后续只有交付/证据封包；需实际核源等价，不只核提交名称。

读根/协作/环境规则、W012任务I1–I6与PM接收、A1执行/性能报告、方案与独立review及原A1-R01，回查architecture和公共/嵌套codec、来源、不可变和异常合同。审main→待审head整个交付，区分前序P1/P2调查与本次唯一产品改动，不能把未合main的调查材料漏出范围。

重点及独立验证：
1. 产品只改domain.codec._decode的hex校验；原(HH)*与H*且偶数长度语言等价，包含空串，只接受小写ASCII hex。核大小写/空白/换行/奇数/Unicode/长尾、畸形tag/JSON/重复key及最终canonical字节检查，matcher先执行一次，fromhex只对合法语言执行。做独立有限语言/错误对照，不只复述数学文字或镜像实现。
2. 公开decode内部的json.loads为$bytes字段生成原生str；私调恶意str子类新增len副作用的既有非阻断边界要如实保留。检查公开类型准入、matcher/fromhex意外异常object/cause/context/suppression、所有嵌套codec及预期错误后二次认证故障；不新增宽catch/trusted、encoder改版或减少constructor/认证次数。
3. wire /1、全部canonical bytes/完整捕获/schema/签名/hash/content refs保持。正常5/7、原mismatch4对source5/一项差异、FIN/crossing/来源、T05/body/图及readback attempt/checkpoint unsealed不变/无terminal保持；目标与source分开。
4. 性能数据按真实18条fresh无插桩样本重算：每路径before/after各3、同机依赖、固定输入URI/RunRequest/cache/roots/GC、实际导入来源、串行时序；中位是每次阶段总和的中位，不是阶段中位数相加。核完整bytecmp原回执及baseline/profile的wire/capture身份、逐阶段增幅和残余成本，不把新profiledecode单次+0.82%混成无插桩结果。三路耗时中位降14.66%–22.80%、峰值降88.59%–90.35%，20%/50%是旧建议而非A1硬门。
5. 原最大118,841,892字符窗口与65次调用顺序/长度、constructor/认证profile计数相同。旧5次窗口刷新HWM，新0次；新整进程仍约700MiB，未做allocator逐项归因。HWM不是净分配，profile秒数不是baseline。确认没有少测、热缓存、漏捕获、新短wire或并发调度冒作产品改善。
6. 核263源/100runtime、原1605+新51=双1656、双typing54、21条最终命令及原输出、snapshot、四个实际before/after wheel/sdist payload仅codec差异、after双fresh安装/源码外完整smoke。首轮中断、r2恢复/轮询断连、原stdout/stderr和A1-R01非空stage防覆写修复/独立关闭保留；不能把partial或未闭合wrapper当通过。
7. 原大wire与安装树可能不在本机。分别声明本次实际读取/运行、按版本采信原独立实比的证据、静态检查和未验证，不声称本机重新实比全部1.47GB。原performance/commands.json和profile/commands.json的最后记录可能缺bytecmp字段，而每条.command.json及最终receipt包含完整比较；按实际层级核对，不改写历史索引。若这些对应关系存在真实缺口，给可复现finding。

按风险选择新增/受影响正式回归和独立探针，可采信未变的双全量/包安装/18样本；不要机械重复小时级矩阵或全部前后benchmark。任何完整codec/readback/旧版高峰命令串行，先检查本机内存和已有进程。若需补测，保留完整结果/源和原始输出，说明有限synthetic范围；不扩成生产/最大输入保证。

只写 docs/tasks/W012/A1/independent-premerge-review.md、必要独立证据及W012任务reviewer区追加；不改产品/正式测试/fixture/历史报告/PM阶段/current-work，不自行修复/验收/合main/删分支或启动writer/memo/B。Finding给版本、复现、影响/严重性/是否必须及依据；没有问题则明确剩余必须项0和检查限制。以项目noreply身份提交推送原A1分支，核远端完整SHA交PM。通过后由PM安排main实际合并版本组合验证。
```
