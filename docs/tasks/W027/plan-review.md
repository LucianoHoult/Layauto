# W027 方案独立复核

复核了起点 `b94c03e83fe16b7037a103e1c76e24e14a5a2f56` 上的产品代码、历史合同和反例，并逐项对照实施方案 `da99c514465048dac98041aa4a0a1ea6bdf2e57e`。方案可以实施。以下条件进入代码复核和定向验收。

| 环节 | 现有依据与复核条件 |
| --- | --- |
| 打开输入 | `pipeline.open_constraint_context` 已验证 context、初始化事件、head、snapshot、target 及封存输入。复用 head 时，应保留本次 run 的工具及 checkpoint 引用，以及初始化 run 的 snapshot 和原 checkpoint。核对错配引用和合法跨 run 复用两个方向。 |
| Stage 4 | `domain.intent.build_differences` 保留每项差异及来源，`state.snapshot` 保存 current、独立 target、channel 关联及 measurement。按选中 cell 核对语义，保留所有差异，再利用已发布几何与归属核对有物理依据的参数。缺测、归属缺失或多义均应阻止成功。C13 提供双方 CDL 的长度位置；多差异样本可检查有无遗漏。C16 的两份声明都为 5，MN0 实测 4，应在 Stage 4 留下几何和双方第 3 行的证据。 |
| Stage 5 | `constraints.engine.check_rules` 已有独立求值、缺规则占位及每项异常处理。它只在 Stage 4 放行后在同一版本显式调用一次。安全放行需同时核对十条规则身份完整、没有重复及逐项 pass，持久化时保留规则目录位置、策略、观测和图形。C14/C15 组合应读回同次运行的两处违规，缺 T07 和求值异常应能读回其他规则的结果。 |
| 原子关闭 | `repository.publication` 的 `_replay`、`_commit` 与 W023 的绑定校验提供了仓库内惯例。新写入需在同一锁内验证请求、受检引用、phase、mode 和 revision。成功额外核对实时 head、空 ECO 链。其他 run-only 失败关闭按架构 §2.6 保留稳定快照，记录收口时 head 为 `current` 或 `superseded`。同键同内容先重放，再进行新写入的 CAS，覆盖响应丢失、同键异内容、错版以及 root 切换前后中断。 |
| 冻结与交付 | W006 的 `run_record_freeze_failure` 保留构造失败、已完成审计以及可用的原始失败原因。Stage 5 写审计、校验或持久化出错应按实际位置表达。保持 W006/W023 旧 wire 可读，并用两个独立仓库核对进程内边界。示例通过仓库指针回读，分别计时目标判断、规则计算、关闭；PM 在实际合并版负责双解释器全量。 |

本次为实施前静态复核，核阅范围包括[架构 §2.5–2.7](../../architecture.md#stage5-rule-invocation)、[W003 失败记录合同](../W003/contracts.md)、[W006 失败发布](../W006-precontext-run-audit.md)、[W023 身份与重放](../W023-atomic-baseline-publication.md)、[W026 缺项与执行错误合同](../../../tests/contracts/test_w026_policy.py)和 [PM 的 C16 读回探针](pm_c16.py)。运行结果和实现审查由后续交付记录给出。
