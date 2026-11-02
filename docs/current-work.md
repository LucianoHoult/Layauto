# 当前工作入口

更新：2026-11-02。详细决定、证据与review结论归任务文件。

## 当前节点

**当前任务为[W006 — 运行入口与输入失败记录](tasks/W006-precontext-run-audit.md)，阶段可执行（局部补修），W006 IPMR-01为P2必须修正项，阻止合并。** 独立合并前review发现：parser异常后若ToolRun诊断冻结再失败，原始异常及cause chain丢失。PM已复现，暂停原技术接收及合并建议；当前1项开放，修复和独立复核交接见[W006 PM2](tasks/W006-precontext-run-audit.md#pm2-ipmr01-20261102)。原PM1的389项/21模块检查保持历史事实，不能覆盖该新增反例。

**W005已验收，并通过[PR #59](https://github.com/LucianoHoult/Layauto/pull/59)合入main `4db3aa81d6f01496a680bdcb264afe99cd80f3f3`。** 合并内容与已审head完全相同，实际集成21项通过，原284项/typing/独立review证据保持适用，见[PM4](tasks/W005-input-reading-binding.md#pm4-integration-20261102)。IPMR-01/FR1均关闭；W003/W004样本及最小合同的验收和[PR #58](https://github.com/LucianoHoult/Layauto/pull/58)集成事实保留。

- 收口依据：[W003 P10](tasks/W003-m1-fixture-contracts.md#p10-w003-accepted)、[MR-078](tasks/W003/manual-verification.md#mr-078)；原MR答复不改写为用户逐项确认。
- 样本验收：[W004 PM3](tasks/W004-fixture-revision.md#pm3-20261031)，633e3fe实物与完整review/交付身份已核验；D1=A已落实，D2后置，D3身份映射分项保留。
- 独立要求复核与补修：[W004 PM5](tasks/W004-fixture-revision.md#pm5-20261102)接收06821ef的原要求复核；REQ-01的body rail整数截断已改为精确比较，并经定向回归及独立复核关闭。原fixture/答案/交付包与W005范围不变，不重开全量样本修订。
- 已后置：MR-040的配置机制精简；旧Virtuoso readback具体生产scope，分别在对应实现前处理。真实准入G1–G4仍阻塞真实M2，G5最迟M3；不阻塞W005的synthetic读取组件。
- 读取范围：MR-033-Q1/038-Q1所属parser/schema/safe-load检查已在W005组件中验证；完整运行审计、Stage2状态/坐标、CAS及Stage6交付继续按W005后续组合表保留。

## 恢复与版本身份

先读根[AGENTS](../AGENTS.md)、[README](../README.md)、[协作规则](collaboration/rules.md)及W006 PM2；回查原报告、复现及任务引用的架构、W003 F1/F2和W005组件合同。不要从旧W004实施、W005补修或已完成的W006执行prompt重新开始；W006 IPMR-01与已关闭的W005同名finding属于不同任务。

| 用途 | 恢复依据 |
| --- | --- |
| 原已验收实物 | `633e3feef8062565019838f2d270e89b7f81c4ed`，原路径fixture/support/合同/报告及[交付附件](tasks/W003/delivery/w004-20261031/)齐全；helper后续补修见下行 |
| REQ-01补修 | 在`06821ef64ac710963dcc947861a374cd0fe9dd6d`上修复body helper并新增持久回归；[独立定向复核](tasks/W003/reviews/w004-req01-fix-review.md)绑定修复文件身份。原633e3fe包保留，不冒记其已含本补修 |
| 原始包身份 | SHA-256 `3cd7bc497391d76656e0327b415ec5c77ce26aa827423dc2b054654977173b39`；8,988项manifest、149路径重建、155文件snapshot及145项r3受审身份已核对 |
| W004历史集成 | `87fe5a5a87d0cbb1f97952f1485dac9a71416369`，PR #58保留原提交历史；合并tree与已审`f82ad14`相同，含REQ-01补修。接收见[W004 PM6](tasks/W004-fixture-revision.md#pm6-20261102) |
| W005产品交付 | `codex/w005-input-reading-binding@51d4d9d7b0d2715a5a2f3fe578615be4c59e74cb`；受审产品发布等价提交`cf35d97478cd78aa7ad707d18c9e37ceda10eafb`，源码/证据清单及发布映射随Git保存 |
| 原PM技术接收 | [PM接收回执](tasks/W005/pm-receipt.json)保存PM1对原交付的3.12测试、typing、重建/干净安装及身份核验；不能覆盖后续补修版本 |
| 当前补修交付 | `c69018dfd1b8eb67705753bb170ec3dcebb88e8f`；最终产品/回归提交`0a6de39e02947e3ae8af64a4dca9487ee8898ca3`，见[补修独立review](tasks/W005/ipmr01-fix-review.md)。原finding及复现保存在[原报告](tasks/W005/independent-premerge-review.md) |
| W005当前集成 | main `4db3aa81d6f01496a680bdcb264afe99cd80f3f3`，合并head `ef31139465d01c170ccaf081484d3bd7cf5ff858`；[集成回执](tasks/W005/integration-receipt.json)与[PM4](tasks/W005-input-reading-binding.md#pm4-integration-20261102)记录最终验收，原[补修接收回执](tasks/W005/ipmr01-pm-receipt.json)保留实际复跑及采用边界 |
| W006恢复入口 | `codex/w006-precontext-run-audit`；独立review交付`ccd157fe1a3dee4267d4f0b119a4eda53cfdcf9f`，产品/回归仍为`cc42ae62585755b0b914d4dbec43324941bfe7c6`。接手包含[PM2](tasks/W006-precontext-run-audit.md#pm2-ipmr01-20261102)及[PM复现回执](tasks/W006/ipmr01-pm-reproduction.json)的后续文档提交，完整SHA见Git/回复；IPMR-01尚未修复，尚未合入main |
| 历史材料 | 准备基线9f6735d，原技术实物0153505；MR-001–077、执行/review和旧PM记录保留各自历史事实。原包与既有受审实物不随PM状态整理改写 |

本机PM复核材料原位于`/workspace/work/w004-pm-receipt-kryfgf84/`，关键结果与身份另汇入[PM接收摘要](tasks/W003/delivery/w004-pm-20261031/receipt.json)随Git交接；临时全量目录不自动跨实例共享。W004/W005分支均已合入main并保留，W006原技术接收因新反例暂停，当前从该分支PM2的局部补修继续。

## 下一步：W006 IPMR-01局部补修与独立复核

沿用独立执行session，按[PM2补修prompt](tasks/W006-precontext-run-audit.md#pm2-ipmr01-20261102)保留原失败及二次诊断原因，补回归并交未参与实现者复核。当前不具备合并条件；finding关闭后由PM核对补修版本，再恢复集成验收及后续Stage2任务收敛。本轮只接收问题和准备交接，未修改产品或main，未启动下一产品任务。

正常输入在W006仅交接unsealed attempt，不产生成功terminal。后续Stage2/baseline/no_change与Stage6完整文件闭环仍是M1硬门；真实工具与配置机制后置项保持，新增关键预期带实例交PM/用户。分支技术接收不等同main集成、W006最终验收或完整M1通过。

## 生产 parser 测试与真实缺项

W005已实现声明的synthetic文件读取组件，尚未验证真实生产方言或平台。后续可按实际支持范围准备由用户单向上传隔离服务器的测试包；无需等M1全闭环完成，也不将synthetic通过当正式生产准入。解析已有raw与实际调用Calibre获取query证据分别记录，前者不证明后者。

用户确认的隔离边界见 [环境记录](environment/remote-development.md#隔离生产服务器用户确认的边界)：向内只能上传代码，向外只能描述数值脱敏格式。目标机平台/Python/离线依赖、能否携带样本、允许反馈字段及内网真实验收回执尚未明确；PM可继续准备这些条件，不能默认为允许回传raw、结果、日志、hash或pass/fail。未决定公开PDK/VM投入，也未改变真实验收方式。

W002 E3 G1–G4仍阻塞真实M2；G5本系统live acquisition证据最迟M3齐备。Stage6 signoff延期不能消除这些门。真实证据可留内网，但PM不从脱敏格式或本地synthetic通过推断真实matched/live或生产准入。

## 历史验收入口

[W001](tasks/W001-v2-global-plan.md#6-pm-验收与交接pm) 保存独立规划review、PM验收和Git集成事实；[W002](tasks/W002-first-input-admission.md#pm-验收与交接pm) 保存已验收调查方案与后续条件。最小协作规范原稿为 `e57f2ddd3122892ad73f473803f2d16d2f632e87`，其完整验收入口保存在 `6eccdff99a4da64e46921d16a4c339198813bc78:docs/current-work.md`。

现行架构、协作规则、环境文档和任务记录各自承担唯一职责。W005组件证据只覆盖声明的读取范围；完整产品组合、真实工具/PDK及生产正确性仍待实际验证。
