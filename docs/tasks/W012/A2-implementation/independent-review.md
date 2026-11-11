# W012 A2 实施独立 review

日期：2026-11-11（Asia/Shanghai）。Reviewer `/root/independent_review`，未承担本轮实现、正式测试或测量工具设计。独立 worktree `/workspace/work/w012-a2/review`，起点 detached `0213c346ac03b7b7282aae522c299155958ac8f6`；初始工作区干净。只写本报告与新的 `review-evidence/`，不修改受审实现或原证据。

## 最终结论

**有限实施、受影响正确性证据和完整三路筛选的独立复核通过；建议按 AI4 停止并保留候选/实测交 PM，不推荐进入 AI5 最终工程或产品验收。** 新增必须项2（A2-I-R01 封存自身输出身份、A2-I-R02 工具错误 URI 假设）均已修正并独立复核关闭，原 finding/反例/失败保留，剩余必须项0。未发现需要改产品源码的必须项；这不等于已完成产品交付或已证明性能收益。

受审产品/正式测试/配置冻结为 `c0a9a2e4c292255202a0ec82b6277cd8a8dd6b78` 的264项，before 为本机 A1 验收 `2489b4609ae97d8211bf450d55cac9392492ac71` 的263项。初冻与修正工具后的新冻产品字节相同；本轮没有用 A1 旧异机耗时作 before。新工具最终冻结 `0589e73f0425583c8c9d079ad8909c225331c7c18dbc4274af5ff471ff5fa398`，六条完整 fresh 串行样本均 exit0，实际全部 wire 逐块、SHA/所有已存 typed refs、来源和值不变量一致。开发双82/双typing54和185受影响正式回归可采信，全部原1656正式节点保留。

收益依据不足：每侧每路仅1次，direct/mismatch 总耗时分别少6.08%/3.64%，readback 整路多24.18%；direct decode、mismatch build亦退化，峰值差异仅0.02%–0.48%。未改上游阶段也明显波动，不能从这一组数据证明稳定净收益，更不能将所有阶段变化归因于私有包装减少。此停止建议没有使用旧20%/50%硬门，也没有推定候选在所有环境一定退化。

**最终双3.10/3.12全量、构建、双干净安装源码外完整组合 smoke、两侧各3次最终性能矩阵未执行，未获产品验收；工程环境/工具只是准备。** 未另跑 profile、扩大 owner 或自动启动 B/M1 下一节点。建议将候选代码和真实结果提交原实施分支交 PM 决定，不自行验收、合 main、删分支或改 PM/current-work。下列初审记录保留当时事实；最终判断以本段和完整筛选复核为准。

## 初始受影响合同复核

已核任务最新 PM6 和 AI1–AI6，当前阶段为“可执行：A2两encoder最小私有typed pack”。父级方案交付为 `71488d6034b40cb67970466b082298a8dc0d5eee`，main 为 `2489b4609ae97d8211bf450d55cac9392492ac71`。本次不重做 AP1–AP5，也不将旧方案 review 当成本轮产品通过。

已读根 AGENTS、README、协作规则、本地与远端环境说明、current-work 相关入口，目标目录只有根 AGENTS；A2 plan/independent-review/delivery 与 PM 接收报告、技术判断和回执；架构 §2.2–2.3、§2.6、§3.7–3.8、§11.2/11.9/11.15；实际两 codec、domain.codec、validate_closed_graph、W010/W011 builder 与 Result constructor、W009 ChangingList 单次快照及 W011 公开异常/closed/exact/来源/alias 正式用例。另读原 measurement-plan 和 A1 完整 probe/runner 的保留根、计时、wire、功能及 readback 检查。Cloud runtime 技能与状态已核：本轮环境 running、observations_current=true、网络 enforced；没有安装依赖。

初始复核没有发现阻止此最小候选实施的方案矛盾。必要边界是：原图 exact closed 检查先于复制；map/scalar 在原分支即时 freeze；tuple 按序物化；nested encoder 仍输出完整原 bytes；原 canonical 全树 freeze/_wire/JSON/UTF-8 保留。原 `_pack`、`_unpack`/decode、所有公开 DTO 和完整来源认证均保留。W011 第二次 `_require_input`、`replace(value)`、`_evaluate` 及完整字段比较不是可删成本，W009 验证并保存同次迭代的合同也不受候选影响。

这是实施前的一致性检查，**最终产品 diff、正式回归及完整性能证据尚待受审**；当前没有产品通过或收益结论。完整筛选若不能支持继续，可按 AI4 交有依据的停止结论；若继续推荐产品交付，AI5 的新冻结工程矩阵和三次同条件完整对照仍须完成。

## 候选代码与新增正式测试局部 review

实际候选两 runtime 文件各增加私有 helper，共44行增加、两处 envelope pack 调用切换。逐分支读后确认 exact `_SPEC` 类与字段次序、原 delegate classes/tag/函数次序相同；map/scalar 即时 freeze、tuple 物化与完整 delegate bytes 保留。无新 catch、上限、缓存或 trusted 路径。独立 [runtime_check.py](review-evidence/runtime_check.py) 对100个原 runtime 文件逐项比较；对两个 owner 仅删除新 helper 文本、还原 envelope 调用后，**其余原文件完整字节与 PM 准备版本相同**。因此原 `_pack`、所有 decoder 及 public DTO、两次认证/`_evaluate`、domain/lower codec 全部保持。实测候选 runtime 身份见 [runtime-check.json](review-evidence/runtime-check.json)，命令与真实输出见 [command](review-evidence/runtime-check.command.json)、[stdout](review-evidence/runtime-check.stdout.txt)、[stderr](review-evidence/runtime-check.stderr.txt)。这是范围/小值复核，不是性能样本。

独立小值对两 helper 各17个子值作旧 `_pack`/canonical 完整字节比较；明确断言 bool/int/Fraction 三个不同 wire，opaque map/Unicode/rational/bytes/`10**300` 整数保持，原 exact map 被恶意改存储后已打包快照仍不变；surrogate 与5001位整数的首个 canonical 异常类型、文本、Unicode object/start/end/reason 和 cause/context/suppression 相同。另三个真实公开 root 走旧 pack 期望 bytes及原 decoder 重建。此有限见证不替代真实完整 Result/来源/异常链或正式回归。

已独立实读新增 `tests/contracts/test_w012_typed_pack.py`，SHA-256 `8749d731c2525313b33583bbb0ce170f9d7e58930e2e5ef1f42d115112d5c9d5`。21个 registry 类型按 dataclass 字段交叉核全字段与读取次序，显式 wire DOM 和未变 accepted pack/canonical 同时作判据；所有 delegate 成员/标签/顺序/完整返回 bytes 的 spy 只声称分派机制，不冒称其 shell 是有效 capture。另七个真实小 root、公开 root/closed 拒绝、scalar 类型/canonical/decoder 拒绝和真公开 encoder 故障历史；这些与既有受影响的公开 owner/run/来源、W009 单次快照、W011 第二次认证回归组合使用，设计范围合理。

集成原命令 `development/new-tests-integrated.command.json` 的实际候选/测试 SHA 匹配上述内容；stdout 为 `82 passed in 0.40s`、exit0、stderr空。测试作者最初80项及后增 delegated decoder 控制的82项原源/原输出均保存。当前局部代码/测试复核新增必须项0；**完整筛选及受影响原回归结果仍待审，不能把本段当最终产品推荐。**

## 完整筛选前置身份与工具复核

产品/正式测试冻结提交 `c0a9a2e4c292255202a0ec82b6277cd8a8dd6b78`；baseline 为本机 detached A1 验收 `2489b4609ae97d8211bf450d55cac9392492ac71`。独立 [freeze_check.py](review-evidence/freeze_check.py) 与实际 [command](review-evidence/freeze-check.command.json)/[stdout](review-evidence/freeze-check.stdout.txt)/[stderr](review-evidence/freeze-check.stderr.txt)/[result](review-evidence/freeze-check.json) 确认：两侧263/264项源码、测试、配置的全部磁盘 hash、指定 Git blobs、snapshot 全成员及完整 bytes 相同；差异恰为两 codec 和新增正式测试，原文件未删除。

原 A1 清单35项 origin/target bytes 及正常 counterpart 全部与 A1 Git tree一致，五 overlay 恰为原 source.gds/header/device_info/device_regions/body。输入 URI、RunRequest 与空 selections 固定；原 normalized cache 不被去除。全部六个新测量脚本 hash 与 freeze/selfcheck 一致，真实集成 selfcheck 为 passed。冻结环境为同一个 Python3.12.14、依赖集合、platform、4CPU/16GiB cgroup；不是将旧异机样本用作 before。

独立实读 common/prepare/probe/run/analyze/selfcheck 全源，未发现影响此筛选有效性的必须项。导入树与输入路径分离并核包路径；fresh child/repository、原阶段调用、保留根、获取前一次 GC 与默认自动 GC 保持；无 hook/profile/额外巨大 encode。来源/target/ref 检查和 wire IO/hash/完整逐块比较都在产品阶段计时与固定峰值之后。runner 在启动前检查所有计划样本/receipt/wire，exclusive create 保存原启动记录、失败和输出，未放宽 A1-R01 防覆写 finding。分析按各次阶段和再取中位，披露 all-build/W011-build/encode/decode/总耗时/峰值和分阶段变化，不设任意百分比门。

此前置复核支持按 AI4 开始一次有限三路 before/after 筛选，**尚无完整样本或收益结论**。收益若不足可以保留候选交 PM；继续推荐产品则仍须 AI5 的新冻结工程矩阵与每侧三次完整对照。

## 完成的开发正确性证据

独立 [correctness_check.py](review-evidence/correctness_check.py) 读取六条完成命令，实核其原 stdout/stderr 的 SHA、exit0 与 source map 对冻结候选相同；[command](review-evidence/correctness-check.command.json)、[stdout](review-evidence/correctness-check.stdout.txt)、[stderr](review-evidence/correctness-check.stderr.txt)、[result](review-evidence/correctness-check.json) 均保存。新增正式测试双3.10/3.12各82通过，双开发 strict typing54通过；原受影响回归为185 passed/2269.37s，覆盖 W011 exceptions53、contracts44、W010 contracts80及 W009 ChangingList 单次快照8，stderr均空。独立用真实 formal collection 的 node IDs 复核上述185选择数量，所有原1656节点仍在，且仅新增82，正式合计1738。

W011原文件完整执行，因而旧 second-authentication、nested W007–W010/Parameter、expected error 后诊断故障的原 object/cause/context/suppression 正式断言仍在；W010原全部contract、原alias/closed/exact/来源与 owner 防线仍在。新测试的私有 shell/spy 没有替代这些真实公开路径。185回归开始时尚无新增测试文件，其实际所选原源与runtime字节均匹配最终冻结；不是凭当时 HEAD 推定同源。原未装mypy的首次 exit1、初始无路径1742 collection及后来明确1738正式范围的修正/原日志均保留。

这些是开发与受影响范围证据，**不是新源码双全量、构建/干净安装或最终产品验收**。本 reviewer 未重复重型回归，没有从 collection 推定测试通过。

## 六条完整筛选的最终独立核验

[performance_check.py](review-evidence/performance_check.py) 在全部重型进程结束后实际运行，exit0；[command](review-evidence/performance-check.command.json)、[stdout](review-evidence/performance-check.stdout.txt)、[stderr](review-evidence/performance-check.stderr.txt)、[result](review-evidence/performance-check.json) 保存逐项核验与重新计算。不是仅阅读执行者摘要：

- 六条原 command/started/stdout/stderr/result/comparison 与 receipt 按 before/after 每路顺序闭合，完成时间无并发；全部 source/test/config、environment、固定输入 URI/35项 bytes、六工具 hash 与新freeze匹配，产品两侧导入包路径正确。工具修正前后 `run` 和原功能 `check_result` AST 相同，未移动阶段包围/保留根/GC、插桩或增加额外编码。
- 真正读取六个本机 wire 文件，三对所有块逐字节相等，并流式重算双方完整 SHA与长度：direct 54,050,313B、readback 136,471,701B、mismatch 54,045,042B，wire降幅0。所有已存 typed refs 数量分别171/183/171且逐项相同；不是以 hash 相同代替实际 bytes 或公开认证。
- 原完整 Result 的 build/encode/decode、原 DTO roundtrip、31份 captured bytes/hash、completed来源解析、query seed provenance、独立 source/target、局部14节点/8edge/6component/16项T05 pass、6个body shapes保持。正常5/7，mismatch实算4对source5恰一差异、36 evaluations/crossings和touch保留；readback unsealed、attempt/checkpoint不变、无terminal。三条固定输入不声称覆盖所有partial/unknown/生产缺项，相关旧正式合同由开发回归覆盖。
- 独立由原各阶段求和重算总耗时、all-build、W011 build、encode、decode、RSS与百分比，逐项等于真实汇总；原失败before及outer传播exit1保持，没有成功JSON/wire，未计为有效baseline。summary同时扫描原失败和attempt02，恰保留这一条原失败样本。原失败部分计时仍在原stdout，不冒记产品成功。

以下仅本轮单次筛选，秒为 before → after；W011 build是all-build子阶段，两者不能相加：

| 路径 | all-build / W011 build | encode | decode | 阶段总和 | 峰值 KiB |
| --- | ---: | ---: | ---: | ---: | ---: |
| direct | 98.536→77.204 / 70.222→50.577 | 6.290→2.106 | 75.938→90.460 | 180.764→169.770 | 327444→325876 |
| readback | 149.994→185.268 / 101.479→141.366 | 3.987→10.439 | 130.609→157.685 | 284.590→353.392 | 711056→709204 |
| mismatch | 84.284→90.872 / 60.065→71.960 | 2.818→2.943 | 69.075→56.681 | 156.178→150.496 | 326396→326316 |

direct decode +19.124%、readback W011 build +39.306%/decode +20.731%、mismatch W011 build +19.804%均未剔除。各路峰值少0.4789%/0.2605%/0.0245%，不足以抵消收益不清。相同源码的上游 W010 build也从24.860→21.137、42.360→35.843、20.333→16.162s变化，故不把单次phase差异讲成已确定的allocator/逐函数因果。静态与小值证据只支持“删除纯编码包装且保留认证”的机制，不能替代完整可重复收益；选择在此停止可免于没有依据地扩大验证/优化包。

已实读执行者 `performance-analysis.md`、执行记录和 task 新增 marked execution段，数据、单组限制、失败及STOP/未最终工程边界与原证据一致。独立[document-scope-check.json](review-evidence/document-scope-check.json)确认剔除唯一执行标记块后，task全部原字节等于 PM 准备 `0213c346…`；PM阶段/要求/历史、current-work、旧P1/A1/A2记录和其他受保护路径未改。当前差异只在授权的两runtime、新正式测试、新实施附件和执行块。

本报告交接后最终delivery/seal属于文件/证据封存，不能冒记新受测产品。A2-I-R01的四个同次生成输出须由完成后检查与最终Git绑定；若仅补文档/hash可局部复核，不需要重跑产品矩阵。

## Finding 原文与处置

| ID | 原 finding、影响与依据 | 处置与独立复核 |
| --- | --- | --- |
| A2-I-R01（必须，最终封存前） | 新 `delivery_check.py` 的 material map 只排除 result 本身，会读取其同次 wrapper 尚未完成的 command/stdout/stderr。`run_command.py` 先写初始 command，checker 读取 hash 后才 print，wrapper 退出后再补 exit/hash 并覆盖 command。因此即使之后不改任何材料，同次封存 map 也不可能匹配其最终 command/stdout。真实 `development/scope-selfcheck-result.json` 中 command 记录 `c33ae3…`、stdout 为 empty `e3b0…`，而完成后实际分别为 `637162…`/`766b03…`。这不是产品或 benchmark 错误，但若原样用于最终交付会产生失真的封存身份。原工具与三输出/result 原样复制保存在 [I-R01 observation](review-evidence/I-R01-observation.json) 和相邻 `I-R01-original-*` 文件；原工具见 [source](review-evidence/delivery-check-before-I-R01.py.txt)。 | 执行者保留原件，仅新增 `--pending-command-prefix`，明确列出并排除同次 result/command/stdout/stderr 四个生成路径；要求后三项 active outputs 实际存在，其他材料仍核 hash。Reviewer在隔离 worktree checkout c0a9，执行[实际修后完整 checker](review-evidence/fixed-delivery_check.py)，future result 未预造且 active 三输出存在时 exit0；wrapper 完成后所有其余 material hashes 全匹配，恰四个生成路径完整存在并另记最终hash，见[command](review-evidence/I-R01-reproduction-fixed.command.json)、[stdout](review-evidence/I-R01-reproduction-fixed.stdout.txt)、[stderr](review-evidence/I-R01-reproduction-fixed.stderr.txt)、[result](review-evidence/I-R01-reproduction-fixed-result.json)、[post-completion核验](review-evidence/I-R01-fix-verification.json)。**已关闭。** 执行者 `scope-r01-fixed` 是仍有另一个回归输出在写的修正快照，不能冒充最终seal；最终待全部输出静止后生成，再由真实Git及post-completion核验绑定四输出。 |
| A2-I-R02（必须，完整筛选重跑前） | 首个 before-direct 已完成公开 build/encode/decode 与原功能/DTO roundtrip 后，新 probe 的来源检查错误要求 target SourceRef.uri 以 `/target.cdl` 结尾；合法保留 spelling 实际是 `target.cdl`。因此该 sample/outer runner exit1，没有成功 JSON/wire，不能将已输出部分计时混作成功 before。原 probe及失败 sample 原输出保存于 [original observation](review-evidence/I-R02-original-observation.json) 与相邻 `I-R02-original-*`；[独立 W005/W007 witness](review-evidence/I_R02_uri_witness.py) 以原正常 URI 实读，成功语义的完整 source/target preservation 分别等于 parsed.completed 记录、URI 为 source.cdl/target.cdl，原 suffix predicate确实为false，见 [command](review-evidence/I-R02-uri-witness.command.json)/[stdout](review-evidence/I-R02-uri-witness.stdout.txt)/[result](review-evidence/I-R02-uri-witness.json)。 | 执行者保留原 probe/selfcheck/analyze、失败 sample和诊断原输出，仅修正 post-peak preservation核验并扩展工具自检/失败历史汇总。Reviewer实际运行修后完整轻量自检（[command](review-evidence/I-R02-selfcheck.command.json)/[stdout](review-evidence/I-R02-selfcheck.stdout.txt)/[stderr](review-evidence/I-R02-selfcheck.stderr.txt)/[result](review-evidence/I-R02-selfcheck-result.json)）exit0，正常+mismatch合法相对URI通过、调换 exact-class preservation被拒绝，失败汇总/guards见证通过。独立[新freeze检查](review-evidence/freeze_check_attempt02.py)及[command](review-evidence/freeze-check-attempt02.command.json)/[result](review-evidence/freeze-check-attempt02.json)确认所有263/264 Git/磁盘/tar完整bytes、35/5输入、request/environment等于首冻；仅probe/selfcheck/analyze改变，common/prepare/run保持，六工具hash与真实自检及新freeze一致。**已关闭，允许全六条fresh attempt02重跑。** 原失败不覆盖、不充作成功before，runtime/正式测试/输入URI未变。 |
