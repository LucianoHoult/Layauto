# A1 执行记录

本轮仅实施既有hex matcher最小兼容优化。PM恢复 `7f7c1304bdafd941791421cef64864fb1616303c`，产品/测试冻结 `ca1f810c3c97376f71089d8b4054760ff198012f`；性能运行编排冻结 `d9d68475fefbeb420e738ad2ee5c2b6e92e7c5ec`。后续分析/证据记录不改变受测产品源码。方案先经未参与设计的reviewer通过，见[plan-review.md](plan-review.md)。

实际产品diff只替换 `domain.codec._decode` bytes分支的重复分组hex条件，保留原matcher先执行、fromhex准入、公开类型、canonical重编码与全部认证边界；未实现writer/reader重构、memo/cache或新格式。新增51项直接合同测试，原1605个node ID全部保留，双解释器实际收集1656项。

开发实际结果见[development-commands.json](development-commands.json)：3.12新增及W005合同89 passed / 0.64s；3.10新增51 passed / 0.45s；W008/W009嵌套和W011异常/来源/错型等值受影响范围273 passed / 1066.57s。原测试未改。开发命令起始UTC未捕获，记录采用pytest原输出的耗时，不冒充独立性能计时。

固定mismatch35项已按原origin/hash逐字节重建核对，见[preflight.json](preflight.json)。before从 `/workspace/w012-a1-before` 导入，after从本checkout导入；输入URI/RunRequest/cache/GC及对象保留仍相同。原性能venv未改；独立双dev环境和安装原输出（含失败重试）保存于 `environment/`。

18个fresh串行无插桩样本和新旧readback独立profile已完成，详见[完整性能分析](performance-analysis.md)。基准与profile/矩阵不重叠。实际巨大wire保留在Git外 `/workspace/w012-a1-performance/wires/`，父进程在样本结束后逐块比较原bytes；逐样本命令与回执保留核对证据。

首轮矩阵使用原W011 gate，但环境starting→ready中断后Python进程消失，partial39%/43%不计通过；首轮26文件及原runner/快照完整归档[verification-attempt-01](verification-attempt-01/)，身份见[interruption-01.json](interruption-01.json)。恢复时核源hash/双pipcheck不变，OOM计数0，不能据此推断中断为产品问题。新[verification-r2](verification-r2/)仅改变工程调度：依据完整样本的新峰值，显式允许两个无gate工程worker；全部1656项、原1605个ID、typing、构建及双安装检查不变，不把调度收益计为产品性能，详见[recovery-plan.json](recovery-plan.json)。

第二次环境重连使外层轮询wrapper退出状态不可得，但detached prepare_final和两pytest进程实际存活；未重新启动或覆盖r2输出，见[reconnect-02.json](reconnect-02.json)。因此不把外层 `final-r2-runner.command.json` 的started冒记为exit0；内部各命令JSON及最终receipt才是完成依据。原连续采样保留，重连后的[独立离散观测](post-reconnect-samples.jsonl)明确不是连续峰值采样。性能18次和profile两次在此之前已完整收口，不受工程轮询中断影响。

恢复时先检查现有进程/日志，不能重新调用runner覆盖stage。独立早期review发现A1-R01中断输出覆盖风险，已在性能开始前修复、reviewer隔离复核关闭；最终报告将保留原finding/复现/关闭。旧P1/P2 finding和附件不改。

最终[verification-r2/receipt.json](verification-r2/receipt.json)已完整闭合：21条命令全部exit0；Python3.10.22/3.12.14分别1656 passed（7939.88s/5716.06s），原1605个node ID全部保留；双strict typing均54源文件无问题、双dev pipcheck、构建、sdist3.10和wheel3.12两套全新安装的`-I -B`源码外完整组合smoke全部通过。最终重核263源/测试/配置及100runtime未变；实际78项工程附件hash清单闭合。见[完成观测](completion-observation.json)，不补造外层wrapper退出码。

四份真实before/after包随Git交付；[实际包比较](package-comparison.json)读取每份wheel/sdist，均100runtime成员，各侧格式payload一致，两侧仅`domain/codec.py`成员hash不同。before是本轮从原受测源重建的包，不冒充W011历史blob；after从最终冻结快照构建。安装smoke使用自身冻结snapshot的fixture URI，hash在原stdout中保留，不与固定URI性能基准混比。

独立方案review和代码/正确性/性能review由未参与设计的reviewer维护，见[最终独立报告](independent-review.md)及任务review段；原finding/复现和关闭依据保留。以项目noreply提交推送原A1分支、核远端完整SHA后，仅交PM核验；不自行验收、合main、改current-work、删分支或启动下一子项。
