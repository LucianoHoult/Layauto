# A1 执行记录

本轮仅实施既有hex matcher最小兼容优化。PM恢复 `7f7c1304bdafd941791421cef64864fb1616303c`，产品/测试冻结 `ca1f810c3c97376f71089d8b4054760ff198012f`；最终运行编排冻结 `d9d68475fefbeb420e738ad2ee5c2b6e92e7c5ec`。后续分析/证据记录不改变受测产品源码。方案先经未参与设计的reviewer通过，见[plan-review.md](plan-review.md)。

实际产品diff只替换 `domain.codec._decode` bytes分支的重复分组hex条件，保留原matcher先执行、fromhex准入、公开类型、canonical重编码与全部认证边界；未实现writer/reader重构、memo/cache或新格式。新增51项直接合同测试，原1605个node ID全部保留，双解释器实际收集1656项。

开发实际结果见[development-commands.json](development-commands.json)：3.12新增及W005合同89 passed / 0.64s；3.10新增51 passed / 0.45s；W008/W009嵌套和W011异常/来源/错型等值受影响范围273 passed / 1066.57s。原测试未改。开发命令起始UTC未捕获，记录采用pytest原输出的耗时，不冒充独立性能计时。

固定mismatch35项已按原origin/hash逐字节重建核对，见[preflight.json](preflight.json)。before从 `/workspace/w012-a1-before` 导入，after从本checkout导入；输入URI/RunRequest/cache/GC及对象保留仍相同。原性能venv未改；独立双dev环境和安装原输出（含失败重试）保存于 `environment/`。

当前长流程由 `run_all.py` 执行：18个fresh串行无插桩样本→新旧readback独立profile→双1656全量/typing→构建/双干净安装源码外smoke。基准与profile/矩阵不重叠。首轮矩阵使用原W011 gate，但环境starting→ready中断后Python进程全消失，partial39%/43%不计通过；首轮26文件及原runner/快照完整归档verification-attempt-01。恢复检查源hash/双pipcheck保持，OOM计数0，不能据此推断中断为产品问题。新verification-r2仅改变测试调度：依据完整样本的新峰值，显式允许两个无gate工程worker，监测实际process/cgroup内存；全部1656/1605原ID/typing/构建/双安装检查不变，不把调度收益计为产品性能。详见interruption-01.json及recovery-plan.json。日志入口 `orchestrator.stdout.txt`、`run-final-01/`；实际巨大wire保留在Git外 `/workspace/w012-a1-performance/wires/`，父进程在样本结束后逐块比较原bytes，证据随每个command保存。

恢复时先检查现有进程/日志，不能重新调用runner覆盖stage。独立早期review发现A1-R01中断输出覆盖风险，已在性能开始前修复、reviewer隔离复核关闭；最终报告将保留原finding/复现/关闭。旧P1/P2 finding和附件不改。

尚在运行的结果不称为完成或验收。全部新冻结工程与性能证据完成后，交独立代码/正确性/性能review并关闭必须项，再推送原A1分支核远端SHA，交PM停止；不自行验收、合main、改current-work、删分支或启动下一子项。
