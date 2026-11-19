# W016 资源复核后的继续执行prompt

```text
继续执行W016。恢复codex/w016-single-cell-analysis最新远端PM补记提交，核HEAD、工作区、
AGENTS和docs/tasks/W016-single-cell-analysis.md。实现检查点为
2608d84b94f1a5a3011855f2839c7407c65cc3fd，不从main重新实现，不覆盖无关改动。

先读docs/tasks/W016/pm-resource-decision.md；它是当前有效的资源门处置。
PM已核当前报告235613 bytes、原单次报告阶段约0.026秒、内部链阶段合计约2.06秒、
进程峰值约24.15MiB，决定把纯报告体积优化后置，解除仅由>2倍capture触发的暂停。
这些是内部无body小样本旧观测，不是完整API或生产性能通过。

不要先做第三轮专用字段表/字符串字典/地址压缩，不复活W012 A2，也不能删来源/完整诊断
或跳认证。继续A1–A8剩余API、端子、body/manual、facet/status/错误聚合和兼容验证。
旧resource-checkpoint末尾“先报告专用投影”的建议以PM新决定为准，原证据保留。

API连通时串行测无body正常/有body正常/无body FIN mismatch，补公开调用整体墙钟和
分阶段耗时、HWM、去重capture/未压缩完整report bytes及认证/neutral构造次数。
保留倍率，但同一已解释>2倍率不再阻止扩包或最终矩阵；发现新绝对成本/增长问题才再报PM。
1GiB/120秒及完整capture重复、认证重建无界增长的原复核门继续适用；倍率时间比较必须同口径。
旧七阶段wire parity是另一工作负载，串行执行、复用已有冻结baseline，不误套新API成本比较。

58项定向测试、typing及R01/R02只覆盖其原源码/反例；源改后验证受影响范围，不当最终验收。
完成独立实现review和修正复核、双侧旧DTO/wire/ref兼容及原要求的最终双版本矩阵/build/
双clean安装smoke。按verification-reuse保留真实身份、原失败和证据，不重复无关全量。

仅改原任务授权产品/测试和执行材料，不修改PM要求/阶段/current-work，不自行放宽正确性
或其他资源门。完成后以项目noreply身份提交推送原分支，核远端完整SHA交PM；未完成时给
具体恢复点与剩余项，不合main、不自行验收、不删除分支。
```
