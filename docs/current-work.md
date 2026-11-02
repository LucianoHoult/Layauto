# 当前工作入口

更新：2026-11-02。详细决定、证据与review结论归任务文件。

## 当前节点

**当前任务为[W005 — 输入读取与绑定组件](tasks/W005-input-reading-binding.md)，阶段可执行，正在派发IPMR-01局部补修，暂不具备合并条件。** 新独立review发现转义surrogate字符可绕过typed错误或产生无法digest的成功结果；PM已复现并接收，修复范围和关闭条件见[PM2](tasks/W005-input-reading-binding.md#pm2-ipmr01-20261102)。原交付51d4d9d及[PM1](tasks/W005-input-reading-binding.md#pm1-receipt-20261102)保留历史事实。产品组件已经实现，不从旧prompt重做；完整M1仍待后续组合。

**W003/W004样本及最小合同已验收；W004已通过[PR #58](https://github.com/LucianoHoult/Layauto/pull/58)合入main。** W005补修沿用独立执行session，修复后由未参与实现者定向复核，再交PM；本轮不合并main或启动下一产品任务。

- 收口依据：[W003 P10](tasks/W003-m1-fixture-contracts.md#p10-w003-accepted)、[MR-078](tasks/W003/manual-verification.md#mr-078)；原MR答复不改写为用户逐项确认。
- 样本验收：[W004 PM3](tasks/W004-fixture-revision.md#pm3-20261031)，633e3fe实物与完整review/交付身份已核验；D1=A已落实，D2后置，D3身份映射分项保留。
- 独立要求复核与补修：[W004 PM5](tasks/W004-fixture-revision.md#pm5-20261102)接收06821ef的原要求复核；REQ-01的body rail整数截断已改为精确比较，并经定向回归及独立复核关闭。原fixture/答案/交付包与W005范围不变，不重开全量样本修订。
- 已后置：MR-040的配置机制精简；旧Virtuoso readback具体生产scope，分别在对应实现前处理。真实准入G1–G4仍阻塞真实M2，G5最迟M3；不阻塞W005的synthetic读取组件。
- 读取范围：MR-033-Q1/038-Q1所属parser/schema/safe-load检查已在W005组件中验证；完整运行审计、Stage2状态/坐标、CAS及Stage6交付继续按W005后续组合表保留。

## 恢复与版本身份

先读根[AGENTS](../AGENTS.md)、[README](../README.md)、[协作规则](collaboration/rules.md)及W005；根据任务回查架构和W004输入合同，不从MR-001、旧准备或W004实施prompt重新开始。

| 用途 | 恢复依据 |
| --- | --- |
| 原已验收实物 | `633e3feef8062565019838f2d270e89b7f81c4ed`，原路径fixture/support/合同/报告及[交付附件](tasks/W003/delivery/w004-20261031/)齐全；helper后续补修见下行 |
| REQ-01补修 | 在`06821ef64ac710963dcc947861a374cd0fe9dd6d`上修复body helper并新增持久回归；[独立定向复核](tasks/W003/reviews/w004-req01-fix-review.md)绑定修复文件身份。原633e3fe包保留，不冒记其已含本补修 |
| 原始包身份 | SHA-256 `3cd7bc497391d76656e0327b415ec5c77ce26aa827423dc2b054654977173b39`；8,988项manifest、149路径重建、155文件snapshot及145项r3受审身份已核对 |
| main集成版本 | `87fe5a5a87d0cbb1f97952f1485dac9a71416369`，PR #58保留原提交历史；合并tree与已审`f82ad14`相同，含REQ-01补修。接收见[W004 PM6](tasks/W004-fixture-revision.md#pm6-20261102) |
| W005产品交付 | `codex/w005-input-reading-binding@51d4d9d7b0d2715a5a2f3fe578615be4c59e74cb`；受审产品发布等价提交`cf35d97478cd78aa7ad707d18c9e37ceda10eafb`，源码/证据清单及发布映射随Git保存 |
| 原PM技术接收 | [PM接收回执](tasks/W005/pm-receipt.json)保存PM1对原交付的3.12测试、typing、重建/干净安装及身份核验；不能覆盖后续补修版本 |
| 当前补修入口 | 独立review交付`cec15f7e3cd74f8cc439f9a5ab654597a113da78`，原finding与复现见[报告](tasks/W005/independent-premerge-review.md)。接手同分支包含[PM2](tasks/W005-input-reading-binding.md#pm2-ipmr01-20261102)的后续PM交接提交，准确SHA见Git/回复；main仍是上述W004集成版本 |
| 历史材料 | 准备基线9f6735d，原技术实物0153505；MR-001–077、执行/review和旧PM记录保留各自历史事实。原包与既有受审实物不随PM状态整理改写 |

本机PM复核材料原位于`/workspace/work/w004-pm-receipt-kryfgf84/`，关键结果与身份另汇入[PM接收摘要](tasks/W003/delivery/w004-pm-20261031/receipt.json)随Git交接；临时全量目录不自动跨实例共享。W004分支已合入main并保留，后续实现使用新的W005分支。

## 下一步：W005局部补修与定向复核

独立执行session按W005 PM2修复IPMR-01并补持久回归，独立reviewer核查修复及受影响结论。只有该必须修正项关闭并由PM核对新交付后，才恢复main集成及最终验收判断。其后准备输入组件接入正式运行审计的近期任务；本轮未建立或派发下一产品任务。

W005交付是组件API。正式pipeline入口的unsealed attempt、失败RunRecord/terminal及后续Stage2/6组合仍是硬门，不能用组件测试冒充完整run或M1完成；新关键预期再带实例上报。

## 生产 parser 测试与真实缺项

W005已实现声明的synthetic文件读取组件，尚未验证真实生产方言或平台。后续可按实际支持范围准备由用户单向上传隔离服务器的测试包；无需等M1全闭环完成，也不将synthetic通过当正式生产准入。解析已有raw与实际调用Calibre获取query证据分别记录，前者不证明后者。

用户确认的隔离边界见 [环境记录](environment/remote-development.md#隔离生产服务器用户确认的边界)：向内只能上传代码，向外只能描述数值脱敏格式。目标机平台/Python/离线依赖、能否携带样本、允许反馈字段及内网真实验收回执尚未明确；PM可继续准备这些条件，不能默认为允许回传raw、结果、日志、hash或pass/fail。未决定公开PDK/VM投入，也未改变真实验收方式。

W002 E3 G1–G4仍阻塞真实M2；G5本系统live acquisition证据最迟M3齐备。Stage6 signoff延期不能消除这些门。真实证据可留内网，但PM不从脱敏格式或本地synthetic通过推断真实matched/live或生产准入。

## 历史验收入口

[W001](tasks/W001-v2-global-plan.md#6-pm-验收与交接pm) 保存独立规划review、PM验收和Git集成事实；[W002](tasks/W002-first-input-admission.md#pm-验收与交接pm) 保存已验收调查方案与后续条件。最小协作规范原稿为 `e57f2ddd3122892ad73f473803f2d16d2f632e87`，其完整验收入口保存在 `6eccdff99a4da64e46921d16a4c339198813bc78:docs/current-work.md`。

现行架构、协作规则、环境文档和任务记录各自承担唯一职责。W005组件证据只覆盖声明的读取范围；完整产品组合、真实工具/PDK及生产正确性仍待实际验证。
