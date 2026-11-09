# 当前工作入口

更新：2026-11-09。详细决定、证据与review结论归任务文件。

## 当前节点

**[W011 — 沟道身份匹配与 FIN 计数草稿](tasks/W011-channel-identity-fin-count.md)已准备为可执行。** 从已验收 main `61775e8fde6e9ea247ec08a32067c44c3be48ff8` 建立 `codex/w011-channel-identity-fin-count`；[派发要求独立复核](tasks/W011/handoff-review.md)必须修正项 0，交独立执行 session 先方案 review 后实现。目标是将实际 channel 与 query 器件身份对应，从精确几何计算有效 FIN 并核对 source CDL；正常 MN0=5、MP0=7。没有 W011 产品实现或验证结论，完整 net/body/模型匹配和运行闭环继续保留。

**[W010 — 局部接触与物理连通草稿](tasks/W010-local-contact-connectivity.md)已验收，并通过[PR #64](https://github.com/LucianoHoult/Layauto/pull/64)合入main `84c54857a1b20b9fb29c9b5a73e7b8d686b6e736`。** 合并tree与已审head一致，PM实际15项定向组合及direct/readback主probe通过，剩余必须修正项0，见[PM2](tasks/W010-local-contact-connectivity.md#pm2-integration-20261106)。原双1465/typing48、包及独立review证据继续适用；P3资源摘要已[澄清](tasks/W010/resource-summary.md)。下一开发任务为上方W011；完整坐标、外部body/完整器件标注与运行发布继续后置。

**[W009 — 有效几何与沟道、端区草稿](tasks/W009-effective-geometry-terminals.md)已验收，并通过[PR #63](https://github.com/LucianoHoult/Layauto/pull/63)合入main `8c60f6c6183aed79a08ec8bb232a31f918837f68`。** 合并tree与已审head一致，PM实际63项组合验证通过，IPMR-01/FXR-01关闭，剩余必须修正项0；原最终矩阵/包及PM补修证据继续适用，见[PM4](tasks/W009-effective-geometry-terminals.md#pm4-integration-20261104)。局部精确接触及物理连通草稿现已由W010验收集成；完整坐标、body/完整提取、标注、规则与发布继续后置。

**[W008 — 几何事实与基础占用](tasks/W008-geometry-base-occupancy.md)已验收，并通过[PR #62](https://github.com/LucianoHoult/Layauto/pull/62)合入main `16159c7edb2d085ab4987bff27ec11c5b5f53294`。** 合并tree与已审head一致，PM实际集成61项通过；原730项/40模块及包证据保持适用，见[W008 PM2](tasks/W008-geometry-base-occupancy.md#pm2-integration-20261103)。独立合并前review新增finding 0，剩余必须修正项0。内部索引不等于完整工艺坐标空间、物理连通或baseline。

**W007已验收并通过[PR #61](https://github.com/LucianoHoult/Layauto/pull/61)合入main `765ff864f4341b91996f70f25723411eebc0d6c2`。** 合并tree与已审head完全一致，PM实际集成39项通过；原553项/33模块、最终包及独立review证据保持适用，见[W007 PM2](tasks/W007-semantic-identity-normalization.md#pm2-integration-20261102)。已能形成器件/网络语义、独立目标差异与query身份/seeds，语义相同仍不代表整轮成功。

**W006已验收并通过[PR #60](https://github.com/LucianoHoult/Layauto/pull/60)合入main `221492eb72e10cf2e46f1d9c76cb992087806a97`。** 合并tree与已审head一致，实际集成25项通过；IPMR-01已独立关闭，原PM3的405项/21模块及新包证据保持适用，见[W006 PM4](tasks/W006-precontext-run-audit.md#pm4-integration-20261102)。正常输入仍只交接unsealed attempt，未把读取成功变成整轮成功。

**W005已验收，并通过[PR #59](https://github.com/LucianoHoult/Layauto/pull/59)合入main `4db3aa81d6f01496a680bdcb264afe99cd80f3f3`。** 合并内容与已审head完全相同，实际集成21项通过，原284项/typing/独立review证据保持适用，见[PM4](tasks/W005-input-reading-binding.md#pm4-integration-20261102)。IPMR-01/FR1均关闭；W003/W004样本及最小合同的验收和[PR #58](https://github.com/LucianoHoult/Layauto/pull/58)集成事实保留。

- 收口依据：[W003 P10](tasks/W003-m1-fixture-contracts.md#p10-w003-accepted)、[MR-078](tasks/W003/manual-verification.md#mr-078)；原MR答复不改写为用户逐项确认。
- 样本验收：[W004 PM3](tasks/W004-fixture-revision.md#pm3-20261031)，633e3fe实物与完整review/交付身份已核验；D1=A已落实，D2后置，D3身份映射分项保留。
- 独立要求复核与补修：[W004 PM5](tasks/W004-fixture-revision.md#pm5-20261102)接收06821ef的原要求复核；REQ-01的body rail整数截断已改为精确比较，并经定向回归及独立复核关闭。原fixture/答案/交付包与W005范围不变，不重开全量样本修订。
- 已后置：MR-040的配置机制精简；旧Virtuoso readback具体生产scope，分别在对应实现前处理。真实准入G1–G4仍阻塞真实M2，G5最迟M3；不阻塞W005的synthetic读取组件。
- 读取范围：MR-033-Q1/038-Q1所属parser/schema/safe-load检查已在W005组件中验证；完整运行审计、Stage2状态/坐标、CAS及Stage6交付继续按W005后续组合表保留。

## 恢复与版本身份

先读根[AGENTS](../AGENTS.md)、[README](../README.md)、[协作规则](collaboration/rules.md)及W011，回查W010 PM2、W007–W009组件合同、W003/W004现行判据和任务引用的架构原文。不要从已完成的W004–W010实施或补修prompt重新开始；各任务历史finding保留各自关闭依据。

| 用途 | 恢复依据 |
| --- | --- |
| W011 准备 | `codex/w011-channel-identity-fin-count`，基于已验收 main `61775e8fde6e9ea247ec08a32067c44c3be48ff8`；准备要求/交接与review身份见 [W011](tasks/W011-channel-identity-fin-count.md)，无产品交付 |
| 原已验收实物 | `633e3feef8062565019838f2d270e89b7f81c4ed`，原路径fixture/support/合同/报告及[交付附件](tasks/W003/delivery/w004-20261031/)齐全；helper后续补修见下行 |
| REQ-01补修 | 在`06821ef64ac710963dcc947861a374cd0fe9dd6d`上修复body helper并新增持久回归；[独立定向复核](tasks/W003/reviews/w004-req01-fix-review.md)绑定修复文件身份。原633e3fe包保留，不冒记其已含本补修 |
| 原始包身份 | SHA-256 `3cd7bc497391d76656e0327b415ec5c77ce26aa827423dc2b054654977173b39`；8,988项manifest、149路径重建、155文件snapshot及145项r3受审身份已核对 |
| W004历史集成 | `87fe5a5a87d0cbb1f97952f1485dac9a71416369`，PR #58保留原提交历史；合并tree与已审`f82ad14`相同，含REQ-01补修。接收见[W004 PM6](tasks/W004-fixture-revision.md#pm6-20261102) |
| W005产品交付 | `codex/w005-input-reading-binding@51d4d9d7b0d2715a5a2f3fe578615be4c59e74cb`；受审产品发布等价提交`cf35d97478cd78aa7ad707d18c9e37ceda10eafb`，源码/证据清单及发布映射随Git保存 |
| 原PM技术接收 | [PM接收回执](tasks/W005/pm-receipt.json)保存PM1对原交付的3.12测试、typing、重建/干净安装及身份核验；不能覆盖后续补修版本 |
| 当前补修交付 | `c69018dfd1b8eb67705753bb170ec3dcebb88e8f`；最终产品/回归提交`0a6de39e02947e3ae8af64a4dca9487ee8898ca3`，见[补修独立review](tasks/W005/ipmr01-fix-review.md)。原finding及复现保存在[原报告](tasks/W005/independent-premerge-review.md) |
| W005当前集成 | main `4db3aa81d6f01496a680bdcb264afe99cd80f3f3`，合并head `ef31139465d01c170ccaf081484d3bd7cf5ff858`；[集成回执](tasks/W005/integration-receipt.json)与[PM4](tasks/W005-input-reading-binding.md#pm4-integration-20261102)记录最终验收，原[补修接收回执](tasks/W005/ipmr01-pm-receipt.json)保留实际复跑及采用边界 |
| W006当前集成 | main `221492eb72e10cf2e46f1d9c76cb992087806a97`，已审head `2bdf5fa0b0a1004623ab90cf31ba04eca3c6abf5`，产品`f19ac0448a5d0111f799660bd7be043ebfd16e41`；[PM4](tasks/W006-precontext-run-audit.md#pm4-integration-20261102)及[集成回执](tasks/W006/integration-receipt.json)记录最终验收，原[补修接收](tasks/W006/ipmr01-pm-receipt.json)保留验证边界 |
| W007当前集成 | main `765ff864f4341b91996f70f25723411eebc0d6c2`，已审head `26dc70ce5dee76f275530f33ad585b459b2b8b5a`，产品/测试 `0f879f01acbeac033173d0b6c6257c376bb9272a`；[PM2](tasks/W007-semantic-identity-normalization.md#pm2-integration-20261102)与[集成回执](tasks/W007/integration-receipt.json)记录最终验收；原[PM接收回执](tasks/W007/pm-receipt.json)保留实际复跑与采用边界 |
| W008当前集成 | main `16159c7edb2d085ab4987bff27ec11c5b5f53294`，合并head `eb15a666010cf7f5fa82c97880a4d0e8f023fa8f`，产品`aced62b0adda35fe7bcd8284a7354badc5b03649`；[PM2](tasks/W008-geometry-base-occupancy.md#pm2-integration-20261103)与[集成回执](tasks/W008/integration-receipt.json)记录最终验收。接手包含这些合并后补记的最新main；原[PM1接收](tasks/W008/pm-receipt.json)和独立review保留历史事实 |
| W009当前集成 | main `8c60f6c6183aed79a08ec8bb232a31f918837f68`，已审head `218a1b833451d34a5db6cd8b3c6f3089cc9c3dd0`，产品`73e38df8f932bbb5bd9caf074b442ad2f5c286e9`；[PM4](tasks/W009-effective-geometry-terminals.md#pm4-integration-20261104)与[集成回执](tasks/W009/integration-receipt.json)记录最终验收及实际组合验证。接手包含集成补记的最新main；原PM1–PM3与失败材料保留各自历史事实 |
| W010当前集成 | main `84c54857a1b20b9fb29c9b5a73e7b8d686b6e736`，已审head `f99b59abc88305133661dd2a510fbcaf36a9c6c6`，产品`0f5029df935bc0acd106aad1bc2be81304d4f442`；[PM2](tasks/W010-local-contact-connectivity.md#pm2-integration-20261106)与[集成回执](tasks/W010/integration-receipt.json)记录最终验收和实际组合验证。接手包含验收补记的最新main；原PM1及交付/失败材料保留历史身份 |
| 历史材料 | 准备基线9f6735d，原技术实物0153505；MR-001–077、执行/review和旧PM记录保留各自历史事实。原包与既有受审实物不随PM状态整理改写 |

本机PM复核材料原位于`/workspace/work/w004-pm-receipt-kryfgf84/`，关键结果与身份另汇入[PM接收摘要](tasks/W003/delivery/w004-pm-20261031/receipt.json)随Git交接；临时全量目录不自动跨实例共享。W004–W009分支均已合入main并保留；W010亦已验收集成并保留分支；下一任务另建分支。

## 整体进度与下一步

主线仍是M0准入准备→M1保真无变化闭环→M2首次实际shrink→M3多器件整轮覆盖→M4可复现首版验收。**当前在M1内部，样本、读取、运行身份、输入失败记录、语义/目标差异及几何事实/基础占用、有效区域及局部物理图均已集成；接下来补齐物理状态及后续运行组合，尚未完成第一个完整输入到产物闭环。** 不按任务编号或测试数量推算百分比。

| M1内的能力 | 当前结果 / 后续归属 |
| --- | --- |
| 可信样本与独立判据 | W003/W004已在synthetic范围验收 |
| 实际文件读取及来源绑定 | W005已集成 |
| run身份、读取审计与输入失败终结 | W006已集成 |
| 器件/网络语义、目标差异与query身份关联 | W007已集成 |
| 几何事实与基础占用索引 | W008已验收并集成 |
| CUT有效几何与channel/端区 | W009已验收集成，63项组合验证通过 |
| 局部接触/connector/component及局部T05 | W010已验收集成；实际15项定向组合及direct/readback通过；外部body与完整mandatory规则未完成 |
| channel 器件定位与 FIN 实测/有限参数核对 | W011 可执行；将 query 身份线索关联到真实 channel，FIN count/L/width 从几何计算，尚未实现 |
| 完整工艺坐标/annotation/连通/body/提取状态与原子baseline | 后续Stage2任务保留；W008索引及W009区域草稿不替代这些义务 |
| 无变化的完整判定、只读GDS/CDL/JSON及报告/terminal | 后续Stage3–6组合；通过后才验收M1 |

W010已验收集成，具有明确scope的局部物理图及独立包围事实；示例coordinate与32×16见证仍不能充当完整运行坐标。下一步 W011 先完成 channel 身份与 FIN 计量这一可核对切片，再收敛剩余标注/外部body、完整坐标与规则、原子baseline及运行输出的组合任务；W011不把计数相等提升为完整提取相等或no_change。原drawn及W008 raw occupancy保持，外部body图形独立；生产输入/body任务派发前必须回查U06。

正常输入在W006仅交接unsealed attempt，不产生成功terminal；W007组件也不推进attempt或宣称整轮成功。C08/09/10和C13的正式终结阶段仍需后续组合验证。完整Stage2/baseline/no_change与Stage6文件闭环仍是M1硬门；真实工具与配置机制后置项保持，新增关键预期带实例交PM/用户。W007验收不等同完整Stage2/M1通过。

## 生产 parser 测试与真实缺项

W005已实现声明的synthetic文件读取组件，尚未验证真实生产方言或平台。后续可按实际支持范围准备由用户单向上传隔离服务器的测试包；无需等M1全闭环完成，也不将synthetic通过当正式生产准入。解析已有raw与实际调用Calibre获取query证据分别记录，前者不证明后者。

用户2026-11-02新增的“生产环境不提供body tapcell时应正确处理”已登记为[U06需求](roadmap.md#production-body-evidence)。生产读取测试与body能力任务须区分无本地tap、无外部上下文、可信替代证据、完全缺证明及已提供但错误的资料，明确可继续范围和缺项。具体测试入口/profile尚待设计；当前统一入口仍要求body_context，W008继续既定synthetic几何范围。首次生产测试准备和后续body任务派发前必须回查U06。

2026-11-03用户进一步明确：只提供待修改底层cell、tapcell与全局power rail定义在范围之外是实际使用场景。U06已补充本地已知端口/连接、上层net/电源关联与外部物理路径的区别，以及最小上下文和人工标注的证明边界；后续须考虑单cell分析/修改，不能仅用读取smoke覆盖此需求。开发负责先给出具体方案，当前无需用户逐项决策。

用户确认的隔离边界见 [环境记录](environment/remote-development.md#隔离生产服务器用户确认的边界)：向内只能上传代码，向外只能描述数值脱敏格式。目标机平台/Python/离线依赖、能否携带样本、允许反馈字段及内网真实验收回执尚未明确；PM可继续准备这些条件，不能默认为允许回传raw、结果、日志、hash或pass/fail。未决定公开PDK/VM投入，也未改变真实验收方式。

W002 E3 G1–G4仍阻塞真实M2；G5本系统live acquisition证据最迟M3齐备。Stage6 signoff延期不能消除这些门。真实证据可留内网，但PM不从脱敏格式或本地synthetic通过推断真实matched/live或生产准入。

## 历史验收入口

[W001](tasks/W001-v2-global-plan.md#6-pm-验收与交接pm) 保存独立规划review、PM验收和Git集成事实；[W002](tasks/W002-first-input-admission.md#pm-验收与交接pm) 保存已验收调查方案与后续条件。最小协作规范原稿为 `e57f2ddd3122892ad73f473803f2d16d2f632e87`，其完整验收入口保存在 `6eccdff99a4da64e46921d16a4c339198813bc78:docs/current-work.md`。

现行架构、协作规则、环境文档和任务记录各自承担唯一职责。W005组件证据只覆盖声明的读取范围；完整产品组合、真实工具/PDK及生产正确性仍待实际验证。
