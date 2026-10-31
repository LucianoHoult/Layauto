# Layauto 文档导航

本页只说明文档归属与读取入口。当前工作见 [current-work.md](current-work.md)，agent 从根 [AGENTS.md](../AGENTS.md) 开始。

## 按问题找文件

| 问题 | 文件与职责 |
| --- | --- |
| Layauto 应该怎样工作？ | [architecture.md](architecture.md)：当前唯一 active v2 产品架构 |
| PM、执行、review 怎样协作？ | [collaboration/rules.md](collaboration/rules.md)：角色、读取、推进、验收、上报和交接 |
| 一项任务记录哪些内容？ | [collaboration/task-template.md](collaboration/task-template.md)：模板；真实记录位于 `docs/tasks/Wxxx-目标.md`，当前任务由 current-work 定位 |
| 项目现在从哪里继续？ | [current-work.md](current-work.md)：当前节点与任务入口；详细任务状态归任务文件 |
| 如何查看样本意见的最终处理？ | [MR-078](tasks/W003/manual-verification.md#mr-078)：本轮已落实、已后置及后续开发归属；原人工答复与独立技术证据各保留来源 |
| 如何查看已修订样本及接收依据？ | [W004 PM3](tasks/W004-fixture-revision.md#pm3-20261031)：633e3fe的synthetic修订已验收；[W003 P10](tasks/W003-m1-fixture-contracts.md#p10-w003-accepted)完成样本范围收口 |
| 下一项产品开发是什么？ | [W005](tasks/W005-input-reading-binding.md)：正式读取实际GDS/CDL/raw/config并核对输入绑定，交可组合的evidence/错误结果；完整运行流程另行组合 |
| 整体开发顺序怎样安排？ | [roadmap.md](roadmap.md)：首版里程碑、依赖、架构要求到验收的覆盖；规划已 review 并由 PM 接收，产品能力未验收 |
| 如何准备与运行环境？ | [environment/local-setup.md](environment/local-setup.md)：Python、安装、测试及历史环境记录 |
| 如何跨机器工作？ | [environment/remote-development.md](environment/remote-development.md)：运行位置、环境准备与代码交接 |
| 以前讨论过什么？ | [旧工作流提案](proposals/v2-codex-development-workflow.md)：未采纳部分保留作候选；[历史 changelog](archive/changelog.md)：归档记录 |

## 读取架构的起点

以下是原文导航，不重新定义要求。普通任务按相关行读取；跨模块时补读生产者、消费者和约束。PM 首次全局规划需梳理完整架构和首版覆盖，恢复任务时查阅受影响部分。

| 工作内容 | `architecture.md` 起点 |
| --- | --- |
| 目标、首版范围和阶段关系 | §1、§2 |
| 输入、归一化、annotation、tech 与 fixture | §3–5、§11 对应职责、§12；fixture 特别读 §12.8 |
| 规划与物理修改 | §1.4、§6–7，并读 §8–9 的接收和提交条件 |
| 状态、约束、事务和派生刷新 | §3–5、§8–9、§11 对应职责 |
| 导出、报告、绘图和验证 | §2.7、§10、§11 对应职责，以及相关 publication/fixture 合同 |
| legacy 取用和测试边界 | §11.14–11.15、§12.8、§13 的来源与义务映射 |

新发现的产品架构问题仍按 §13.3 回到对应正文；任务文件负责落实和证据，不另建平行需求源。新 v2 代码位于 `layauto_v2/`，`legacy_mvp/` 是参考与回归种子。

首版规划 review 与 PM 接收见 [W001](tasks/W001-v2-global-plan.md)，首个准入调查/方案见 [W002](tasks/W002-first-input-admission.md)，M1 样本与格式交付、技术review及人工验收入口见 [W003](tasks/W003-m1-fixture-contracts.md)；详细任务状态由任务文件维护。尚未迁移架构正文或批量创建局部 AGENTS。新增文档时更新本页入口及其引用；概要不能把建议、示例或尚未验证的能力写成已确认事实。
