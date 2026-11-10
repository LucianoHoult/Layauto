# A1 实施/工具早期独立复核记录

Reviewer `/root/a1_plan_review`，在产品/测试冻结 `ca1f810c3c97376f71089d8b4054760ff198012f` 后，只读检查主工作区实际diff及新的A1工具；未设计/修改实现，未运行重型产品或性能组合。此记录等待最终工程/性能证据后与最终review一并交付，不代替最终验收。

唯一产品diff是原hex条件换为所审候选及两行说明。新增 `test_w012_hex_validation.py` 覆盖全部ASCII对/256字节、有限混合语言/Unicode/奇数/空/长尾、JSON/canonical拒绝、matcher/fromhex五类异常和两种suppression、入口调用顺序；未删改原测试。runtime SHA256 `498efd7d2cd8367bb660883b6e23cc302776d27cfbe487687ef6eab37773b1c7`，新增测试 `761f007ce04b7775cb8c8cbcde708a300099f967a8e8814544d6cad868f8fb89`。

`probe.check_result` 与P1原版AST逐字等价；runtime路径实际校验、固定输入/RunRequest/cache/GC/完整roots、baseline不插桩、完整wire父进程逐块比对及profile不额外编码大对象均成立。阶段 `wall_seconds` 应与含启动/轮询/写wire的runner `elapsed_seconds` 分开报告。只读辅助异常专项独立核对同样边界，未发现额外必须项。

| ID | 原finding / 实际影响 | 执行处置 | Reviewer复核 |
| --- | --- | --- | --- |
| A1-R01 / 必须，已关闭 | 原runner仅检查`.command.json`，先覆写stage/frozen-identity并以wb开stdout/stderr；若前次中断无command但有输出，重跑会丢原失败证据。原SHA `1bb7a0d182fde14a799eb703d81443b0376e18cf92ccf1d8f3f23a2a67ab37f2`。隔离[复现](early-review-evidence/reproduce_runner.py)实际运行原main，以轻量Process替身在临时路径证实两种覆盖；原[runner快照](early-review-evidence/run_performance-before-R01.py.txt)/[结果](early-review-evidence/runner-R01-reproduction.json)/stdout/stderr保留。 | 正式样本前改为写任何stage文件前拒绝非空stage；selfcheck不创建stage，另禁止已有完整wire覆盖。无性能样本被覆盖或需重测。 | 新runner SHA `aca026ad28711ec161d848b7f249c33ac723de7da7f821ec0c8c66643b77627c`，独立[guard检查](early-review-evidence/verify_runner_fix.py)证实旧stdout/stderr/frozen-identity逐字节保持、未启动进程即拒绝，见[结果](early-review-evidence/runner-R01-fix-verification.json)。关闭。 |
| A1-O01 / 非阻断，已处理 | 新probe沿用原P1 `partial_unknown` 文案中的“同源W011采信”，A1已改公共codec，不宜误述可采信旧最终矩阵。 | 新A1副本改为三条固定输入不覆盖该范围，selected/final新源验证另见记录；原P1附件不改。 | 已核新文案和新最终矩阵要求未放宽。 |

独立guard检查脚本初稿只捕获AssertionError，新实现按预期抛RuntimeError，造成review检查本身退出1；原脚本/输出保留为 `fix-attempt01-*`，随后修正checker捕获类型后通过。这不是新的产品/工具finding，未掩盖原A1-R01。

## 最终工程工具预审

已直接对照两个新副本与W011原版diff，并按Python3.10语法解析：`prepare_final.py` SHA `2a796148c68616894d1fafbfb5832765121e3bb7873a08f2e3cd10d0df641e53`、`installed_smoke.py` SHA `471401c6f64d78c236d640bf15dbdeaed23dee5a62fc6a325e8192e480361960`。未见必须项。前者保留快照、原1605节点集合、双全量/typing、runtime100包/安装身份及源码外-I smoke；后者增源31/实际hash/ref、body identity、18FIN集合、图14/8/6与16T05 pass、checkpoint/无terminal，原完整三路/codec重建和负例保留。最终仍须核实际完整命令、source/tool/package身份和真实结果，预审不是实际通过。

## 环境中断后的工程恢复预审

环境starting→ready后，原长流程进程消失且无双pytest完成回执，执行者保留26项原输出/旧runner/源snapshot于`verification-attempt-01`和`interruption-01.json`，没有将约39%/43%的partial输出冒记为通过，也未将OOM=0当作原因证明。18个baseline和两侧profile已完成，恢复仅重跑最终工程，不将新的调度选择混入性能改善。

新runner SHA `399dd249a9225c3b1425fb7c92f9b1cc79948502b466a9467e363fc3127443ad` 仅增显式 `--allow-parallel-without-gate` 及guard条件；默认双worker仍要求原gate，显式选择后可在新`verification-r2`/新work路径并发两个完整工程worker。测试集合/1656计数/原1605节点、typing/build/双安装/smoke及原输出保留逻辑不变，产品与测试仍为ca1冻结字节。实际组件峰值的下降支持这一工程调度选择，但不是完整矩阵资源上界；须监测真实内存，遇失败保留输出，仅调整测试调度，不改产品/测试凑通过。

独立[恢复核验](recovery-review-evidence/check.py)305项通过，包含26项archive hash、263源逐hash不变、恢复命名/工具身份和三项实际CLI guard。无flag的双worker仍由parser拒绝；有显式flag才越过该guard，随后由故意已存在的临时work目录拒绝；默认单worker也保留fresh-work保护。三个CLI均在任何矩阵或包工作前结束，原stdout/stderr/命令保存，非产品失败。未见新增必须项，可启动新的完整工程attempt；最终是否通过仍以新的完整回执为准。
