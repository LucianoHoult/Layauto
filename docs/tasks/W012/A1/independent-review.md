# A1 代码、正确性与性能独立 review

**最小 A1 复核通过，可交 PM 核验；本轮必须项 1，已关闭 1，剩余 0。** 最终交付没有新增必须项。本结论不代替 PM 验收，不批准 main 集成、下一子项或新 wire 格式。

Reviewer：`/root/a1_plan_review`，未参与算法、正式测试、测量工具或执行方案设计。独立 worktree `/workspace/w012-a1-review`。受审 base 为 PM 准备 `7f7c1304bdafd941791421cef64864fb1616303c`，最终受审提交为 `44a91c472fdeba5bb4b8a6071c0580313336c379`；产品/测试冻结 `ca1f810c3c97376f71089d8b4054760ff198012f`，性能编排冻结 `d9d68475fefbeb420e738ad2ee5c2b6e92e7c5ec`。最终提交的 263 源/测试/配置字节与受测 after 和工程快照相同。所审 372 个提交文件的实际字节及 SHA-256 见[受审清单](final-review-evidence/reviewed-manifest.json)。

已读 AGENTS、README、协作/环境规则、W012 PM1/PM2 与 I1–I6、P1/P2 成本/方案/独立 review 及 PM 接收证据；直接回查架构 canonical/不可变/领域与依赖边界、公共及嵌套 codec、来源和异常合同。方案先经本 reviewer 在 `3b341b7420221599f5ff0eac7d945f57b98a19e3` 独立核对，通过后执行者才修改产品，见[方案 review](plan-review.md)（提交 `d8e7672a2b51082da1fef6f3752340fb2074f97c`）。只读辅助专项 `a1_exception_check` 核对异常合同与最终工程叙述，未设计实现、写文件或运行产品/性能样本。

## Finding 与处置

| ID / 级别 | 原问题及影响 | 独立复核结论 |
| --- | --- | --- |
| A1-R01 / 必须 | 初版 runner 在中断留下 stdout/stderr、但尚无 command 回执时，重跑会覆盖原输出和 frozen-identity。原 finding、原 runner、实际隔离复现及输出保留于[早期报告](early-review.md)和[原复现结果](early-review-evidence/runner-R01-reproduction.json)。 | 执行者在任何性能样本开始前改为先拒绝非空 stage，selfcheck 不创建 stage，并拒绝已有 wire 文件。独立运行新 guard，证实旧文件逐字节保留且未启动进程，见[关闭依据](early-review-evidence/runner-R01-fix-verification.json)。**已关闭**，没有样本被覆写或据此删样本。 |
| A1-O01 / 非阻断 | 新 probe 沿用旧 P1 “同源 W011 采信”的 partial/未知文案，与 A1 已改变 codec 的身份不符。 | 新 A1 副本已明确三条样本的覆盖边界，另以选定回归和最终新源双全量核验。旧 P1 文件不改，已处理。 |

原 P1/P2 的 R01 及原失败 stderr 保持原位，与 A1-R01 分别记录。reviewer guard 检查初稿捕获类型不完整导致的退出 1 也保留为 `early-review-evidence/fix-attempt01-*`，修正检查器后通过；它不是产品故障。未重写原 finding、删除测试或缩小最终集合来关闭问题。

## I1–I3：实现和公开合同

唯一产品 diff 为 `domain.codec._decode` 的 bytes 分支：原 `(?:[0-9a-f]{2})*` 换为 `[0-9a-f]*` 的完整匹配，再检查长度为偶数。matcher 仍先执行一次，原 `isinstance(..., str)`、`bytes.fromhex`、失败 raise、异常传播和最终 canonical 重编码未改。其余 runtime 不变；原有测试未改，只新增 51 个直接合同用例。

令 H 为小写 ASCII 十六进制字符集合，原语言 `(HH)*` 与 `H*` 且偶数长度相同，包含空串。字符类仍排除大写、空白、换行和 Unicode 近似字符；没有用宽松 `fromhex` 扩大准入。方案 review 的 153,658 个有限候选/307,773 项断言、全部 ASCII 对/256 字节及边界见证，与新增正式测试共同支持等价性。数学语言结论与有限见证分开，未把枚举数量冒充全量产品测试。

新增测试及受影响/最终回归保留空/奇数/大小写/空白/Unicode/长尾、畸形 tag/JSON 和 canonical 拒绝，matcher/fromhex 五类异常及两种 suppression 的原 object/cause/context，嵌套公开 codec 和 W011 预期错误后二次认证故障。没有新增 catch/rethrow 或改变 constructor/认证边界。私调 `_decode` 传入恶意 `str` 子类时新增 `len` 的副作用属于[方案报告已保留的非阻断私有边界](plan-review.md)；公开 JSON decode 生成原生字符串，未宣称任意私有子类副作用完全等价，也未顺手收紧公开类型。

encoder、schema `/1`、公开签名及 digest/ref 算法没有改动；没有新 `/2`、writer/reader 重构、memo/cache、trusted 标志、减捕获或跳过认证。18 个完整公开结果样本实比所有 wire bytes；新旧 profile 逐阶段明确 constructor（含 `__init__`/`__post_init__`）、认证、分析/normalize 和公开 encode/decode 调用次数相同。进一步归一 codec 两行位移后，所有可定位 runtime 函数 calls 相同；不把 stdlib 或 `<string>` 生成方法误述为逐类独立计数。

## I4–I5：完整路径与归因

独立检查 18 个 fresh 子进程的实际导入路径、源/工具/解释器/依赖身份、执行次序和起止时间。before 是本机本轮原 runtime，非 P1/W011 历史计时。固定输入 URI、RunRequest/cache、完整保留 roots、GC 开关/阈值/先 collect 顺序相同；35 项 mismatch 依原清单的 origin/hash 重建核对。所有无插桩样本串行，随后才运行两侧 profile，再启动工程矩阵。

各样本完整 36 项 FIN evaluation/crossing、正常 5/7、mismatch 实际 4 对 source 5/一项差异和 touch、原图/来源/局部图/T05/body 保持；readback attempt/checkpoint 不变、unsealed 且无 terminal。target/source 独立，没有把三条固定输入扩写为所有负例；更广来源/错型等值/别名/异常范围由本轮受影响及最终新源矩阵检查。

独立重新读取 18 份实际巨大 wire，以 1 MiB 块与各路径 before-r1 逐字节比较并重算存储 SHA-256，全部相同；两份 profile wire 也实比相同。三路径各次长度分别为 54,050,313 / 136,471,701 / 54,045,042 B，hash、content refs 和 canonical bytes 不变，wire 减幅为 0。实际大 wire 位于 `/workspace/w012-a1-performance/wires/baseline/`，未提交约 1.47 GB；原命令/比较记录和冻结输入工具随 Git 保存，可据此重建。

| 路径 | 阶段总耗时中位秒 before → after | 峰值中位 KiB before → after | 耗时 / 峰值降幅 |
| --- | --- | --- | --- |
| normal direct | 94.418923 → 75.799891 | 2,851,076 → 325,436 | 19.72% / 88.59% |
| normal readback | 186.625165 → 144.066817 | 7,344,896 → 708,536 | 22.80% / 90.35% |
| extraction_mismatch | 93.170488 → 79.514097 | 2,860,516 → 324,668 | 14.66% / 88.65% |

已从原次独立重算各次/中位数、各次峰值及逐阶段统计，与[完整分析](performance-analysis.md)和 summary 一致。总耗时是每次各阶段之和的中位数，不是阶段中位数之和；不混用含启动/轮询/写 wire 的 runner elapsed。六个小阶段观测增幅原样披露：direct W005 +3.61%/W008 +2.46%，readback prepare +4.74%/W009 +0.65%，mismatch W008 +0.84%/encode +0.82%。三次样本不够指定噪声或算法因果，也不证明所有阶段普遍提速、生产上界或统计置信保证。20%/50%是完整兼容包建议，不是 A1 硬门。

profile 的 65 个大 hex 调用长度/顺序相同。原 matcher 窗口刷新 HWM 5 次，新版 0 次；最大 118,841,892 字符窗口旧 HWM 3,604,172 → 7,326,636 KiB，新为 501,568 → 501,568 KiB，RSS 亦未增长。CPython regex 结构与该窗口证据、无插桩峰值共同支持此次定位的重复分组瞬时峰值已消除。hook 只观察既有调用，没有额外编码巨大对象；另有 69 项小值透明性/异常/恢复检查。

HWM 是高水位，不是净分配；不累加各窗口或 inclusive 时间。新 profile 整进程仍为 720,336 KiB，高于全部 matcher 窗口上限 648,896 KiB，最后观测窗口后仍含 decode 收尾、比较及 profile 收集，未逐 allocator/函数归因。单次 profile decode wall 221.044 → 222.850 秒（+0.82%）已披露，不能替代无插桩三次结论。残余峰值和重复序列化留给 PM 另派，A1 没有自行扩大范围。

## I6：最终工程与可访问身份

独立读取 r2 的 21 条完整命令/原 stdout/stderr 和 SHA-256、263 项实际源与 tar 快照、100 项 runtime、原 1605 node ID 子集和全部 1656 收集项。Python 3.10.22 全量 1656 passed / 7939.88s，3.12.14 全量 1656 passed / 5716.06s；新增仅 51 个 hex 合同用例。双 strict typing 各 54 源文件无问题、双 dev pipcheck、构建及双全新安装完整组合 smoke 均 exit 0，最终 receipt 与 78 项附件 manifest 的实际覆盖和 hash 闭合。

四份真实 before/after wheel/sdist 已在受审提交中。独立读取每包 100 个 runtime 成员：各侧 wheel/sdist payload 相同，两侧唯一 payload 差异是 `domain/codec.py`。before 是从原受测源本轮重建的包，不是 W011 历史 blob；不冒称本轮 before 安装/smoke。after 由最终冻结 snapshot 构建，3.10 安装 sdist、3.12 安装 wheel；实际两套安装 100 成员逐 hash 等于冻结源。两条 smoke 命令均为 `-I -B`、cwd 在源码/snapshot 外，真实读取已核安装，完整三路径及 readback 边界通过。安装 smoke 的输入 URI 指向 snapshot，未与固定 URI 性能 hash 混比。

首轮环境恢复后进程消失，26 项 partial 输出/原 runner/snapshot 保留，不把约 39%/43% 当通过。恢复的新 r2 只显式选择两个无 gate 工程 worker；默认双 worker 仍要求 gate，新增 flag/原保护已独立轻量验证。产品、测试集合及最终检查未变，性能已先结束，不将工程调度当产品收益。第二次重连时 detached 子进程存活且未重启；最终完成依据是内部 21 命令及 receipt，没有补造外层 wrapper 的退出码。OOM=0 不作为中断原因证明。

独立轻量证据分别为：[语言/异常方案](plan-review-evidence/result.json)307,773 项、[baseline/实际 wire](baseline-review-evidence/result.json)2,642 项、[观测器](baseline-review-evidence/hook-result.json)69 项、[profile/原版包](profile-package-review-evidence/result.json)498 项、[恢复保护](recovery-review-evidence/result.json)305 项、[最终工程](engineering-review-evidence/result.json)525 项，以及[最终提交范围/身份](final-review-evidence/result.json)645 项；各检查器/原命令/原输出均保留。这些是 review 证据核验，不能相加冒充正式测试数。reviewer 未重跑重型性能、全量或安装 smoke。

最终 `git diff --check base..head` 仅报告两个原 build stderr 的 EOF 空行（`before-package/build.stderr.txt:9`、`verification-r2/build.stderr.txt:19`）；为保留原输出 hash 未修剪，原输出警告不属于产品或手写文档空白缺陷。未改正式 fixture/答案、架构、current-work、原 P1/P2 工具/输出或 PM 要求。reviewer 仅新增独立资料及任务 A1 reviewer 段，不代改任务阶段或 PM 验收。

交执行者以项目 noreply 身份保存到原 A1 分支、推送并核远端完整 SHA，再交 PM 核验。本 review 不自行推送/合 main/删分支或启动下一子项。新 wire 的公开范围、默认兼容、digest/ref 和历史迁移仍需独立具体决定材料，本次没有推定批准。
