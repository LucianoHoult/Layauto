# 当前工作入口

更新：2026-10-31。详细决定、证据与review结论归任务文件。

## 当前节点

**W003/W004样本及最小合同范围已验收；当前任务为[W005 — 输入读取与绑定组件](tasks/W005-input-reading-binding.md)，阶段可执行，产品代码尚未开始。** 用户同意PM将清单按已落实、已后置与后续开发归位并继续推进；不再将旧A/B的历史未确认状态视为额外审批门。

- 收口依据：[W003 P10](tasks/W003-m1-fixture-contracts.md#p10-w003-accepted)、[MR-078](tasks/W003/manual-verification.md#mr-078)；原MR答复不改写为用户逐项确认。
- 样本验收：[W004 PM3](tasks/W004-fixture-revision.md#pm3-20261031)，633e3fe实物与完整review/交付身份已核验；D1=A已落实，D2后置，D3身份映射分项保留。
- 已后置：MR-040的配置机制精简；旧Virtuoso readback具体生产scope，分别在对应实现前处理。真实准入G1–G4仍阻塞真实M2，G5最迟M3；不阻塞W005的synthetic读取组件。
- 后续开发：MR-033-Q1/038-Q1所属parser/schema/safe-load错误检查进入W005；完整运行审计、Stage2状态/坐标、CAS及Stage6交付另按W005后续组合表保留。

## 恢复与版本身份

先读根[AGENTS](../AGENTS.md)、[README](../README.md)、[协作规则](collaboration/rules.md)及W005；根据任务回查架构和W004输入合同，不从MR-001、旧准备或W004实施prompt重新开始。

| 用途 | 恢复依据 |
| --- | --- |
| 已验收实物 | `633e3feef8062565019838f2d270e89b7f81c4ed`，原路径fixture/support/合同/报告及[交付附件](tasks/W003/delivery/w004-20261031/)齐全 |
| 原始包身份 | SHA-256 `3cd7bc497391d76656e0327b415ec5c77ce26aa827423dc2b054654977173b39`；8,988项manifest、149路径重建、155文件snapshot及145项r3受审身份已核对 |
| 本轮PM与W005交接 | 用户同意同步至`codex/w004-task-convergence`；接手使用包含W003 P10/MR-078和W005的发布提交，最终SHA见Git/交接回复。仅633e3fe不含这些后续记录 |
| 历史材料 | 准备基线9f6735d，原技术实物0153505；MR-001–077、执行/review和旧PM记录保留各自历史事实。原包与既有受审实物不随PM状态整理改写 |

本机PM复核材料原位于`/workspace/work/w004-pm-receipt-kryfgf84/`，关键结果与身份另汇入[PM接收摘要](tasks/W003/delivery/w004-pm-20261031/receipt.json)随Git交接；临时全量目录不自动跨实例共享。样本分支已发布，main尚未合入本轮修订。

## 下一步：执行W005

W005先补一页API/DTO/错误归属方案并做独立接口review，再在既定范围内直接实现；无需用户重复批准普通内部设计。真正读取GDS/CDL/raw/config及body context，检查精确单位、格式、来源和绑定，输出evidence与明确错误。spec/oracle/expected只作独立答案，normalized不能绕过raw。

本次任务是组件API。正式pipeline入口的unsealed attempt、失败RunRecord/terminal及后续Stage2/6组合仍是硬门，不能用组件测试冒充完整run或M1完成。执行完成按W005 A1–A7交独立review及PM验收，新的关键预期再带实例上报；不自动进入下一产品包。

## 生产 parser 测试与真实缺项

W003只交样本/合同/辅助，产品parser未实现。推荐后续Stage1 parser/输入绑定包经本地正常/失败检查与针对性review后，由用户单向上传隔离服务器测试；无需等M1全闭环完成，也不将本包reader或legacy parser当正式准入交付。先解析已有raw与实际调用Calibre获取query证据分别记录，前者不证明后者。

用户确认的隔离边界见 [环境记录](environment/remote-development.md#隔离生产服务器用户确认的边界)：向内只能上传代码，向外只能描述数值脱敏格式。目标机平台/Python/离线依赖、能否携带样本、允许反馈字段及内网真实验收回执尚未明确；PM可继续准备这些条件，不能默认为允许回传raw、结果、日志、hash或pass/fail。未决定公开PDK/VM投入，也未改变真实验收方式。

W002 E3 G1–G4仍阻塞真实M2；G5本系统live acquisition证据最迟M3齐备。Stage6 signoff延期不能消除这些门。真实证据可留内网，但PM不从脱敏格式或本地synthetic通过推断真实matched/live或生产准入。

## 历史验收入口

[W001](tasks/W001-v2-global-plan.md#6-pm-验收与交接pm) 保存独立规划review、PM验收和Git集成事实；[W002](tasks/W002-first-input-admission.md#pm-验收与交接pm) 保存已验收调查方案与后续条件。最小协作规范原稿为 `e57f2ddd3122892ad73f473803f2d16d2f632e87`，其完整验收入口保存在 `6eccdff99a4da64e46921d16a4c339198813bc78:docs/current-work.md`。

现行架构、协作规则、环境文档和任务记录各自承担唯一职责。已完成的规划、样本准备和技术review均不证明v2产品、真实工具/PDK或生产正确性；产品执行→修复→组合验收周期仍待实际运行。
