# 当前工作入口

更新：2026-10-26。PM 维护当前节点和恢复入口；详细状态、决定、证据与 reviewer 结论归任务文件。

## 当前节点

**W003 原版 synthetic 样本/合同已完成执行和独立 review；当前正在用户人工核验，恢复于 MR-054 / B4.03d。** 原技术 review 的两项 P2 已独立复核关闭；之后人工核验提出的修改要求尚未实施，不能把旧版的技术通过当作新版已通过或用户验收完成。M0 真实准入出口仍未满足，M1 产品尚未实现。

- [路线图](roadmap.md)：M0 准入准备 → M1 no_change 保真文件闭环 → M2 首个实际 shrink 闭环 → M3 多器件/多 delta 首版覆盖 → M4 可复现验收；能力目标和实质验收要求保持已审内容。
- [W001 — 首版全局规划](tasks/W001-v2-global-plan.md) 与 [W002 — 首个准入调查/方案](tasks/W002-first-input-admission.md) 已验收、提交并推送；它们不证明 v2 产品能力。
- **当前任务：[W003 — M1 最小样本、文件合同与独立判据](tasks/W003-m1-fixture-contracts.md)**，阶段为待验收；执行/reviewer 已停止写入并交回固定版本，详细接收见任务 P0–P3。
- **当前人工入口：[W003 人工核验清单](tasks/W003/manual-verification.md)**。A/B 已有局部确认、需修改与未决，C 全部22负例和 D 明细尚待覆盖；不从 A1 重新开始。当前处理文件 DBU 与网格精度的关系，之后按用户指示进入 B4.04a。
- 2026-09-10 用户授权新建审核分支并提交/推送，方便在另一平台查看。W003材料已发布到 `codex/w003-manual-review`，仍待用户验收、未合入main；不开始产品实现、架构拆分、EDA/VM或生产上传。
- 2026-10-26 网页续接入口：[mental checkpoint 与启动 prompt](tasks/W003/web-codex-handoff.md)。本次同步人工记录和 PM 恢复文档；范围、身份与未上传的历史附件见 [W003 P5](tasks/W003-m1-fixture-contracts.md#p5-网页续接与人工记录同步2026-10-26)。

## 恢复与版本身份

先读根 [AGENTS](../AGENTS.md)、[README](../README.md)、[协作规则](collaboration/rules.md)，再读 W003 要求、E0–E4、R0–R4、[PM 接收](tasks/W003-m1-fixture-contracts.md#pm-验收与交接pm) 和本次人工清单；按问题补读W002与相关架构原文。用户人工核验由PM统筹，执行者负责解释/修正，reviewer复核受影响项；不重复派发已经完成的技术review。

**审核分支：`codex/w003-manual-review`。** 原技术材料提交为 `01535055f5d661a2964443dec76fc7f7f305e3e0`，其发布说明提交为 `6d29b511ac415a9ea198d1e5c8978313c5abb6e3`；人工记录 MR-001–MR-054 仍绑定该版实物。本次迁移文档为其后续提交，实际启动须核对 branch/HEAD、工作区及远端分支，并确认已包含 MR-054 和网页交接文件。从审核分支恢复，不从 main 寻找尚未合入的 W003。

**Git基线：`main@b1f0301cf76b2e1808cb293cfdb4e1bfededde73`**，为W002发布记录；W002已验收正文提交为 `f141af99525c48819aa97416e8cb81e9091d6c0e`。2026-09-10推送后同时核对远端main仍为b1f0301。本次未创建PR或合并。

**当前受审执行材料：**`/private/tmp/layauto-w003-independent-review-i8gqzwtw`。PM核对其1938条manifest和接收时92份snapshot，完整补丁可从上述基线重建；`full.patch` SHA-256为 `c03a90b4f49c51a2343d54ad110420801d7b39966f6f5b6ec34c7b5b8fd1178f`，其余身份/原始记录见W003 P0。PM随后仅改任务阶段/PM段、当前入口、导航并新增人工清单；这些PM文档不再与受审包逐字节相同，执行材料和reviewer原文保持该身份。

**加入PM记录后的恢复包：**`/private/tmp/layauto-w003-pm-received-ew822nhg`，包含93文件完整snapshot/patch、独立review包副本和本轮文档检查；表示待用户验收，详情见W003 P3。

本机历史W002完整接收包为 `/private/tmp/layauto-w002-accepted-xvwblftq`；旧W003草案/准备/初审包只作历史，不作为当前恢复输入。临时路径不随Git上传，跨主机复用附件证据必须另保存完整可访问版本；路径失效不能继续声称附件已核验。不要重跑历史快照生成脚本覆盖证据。

跨平台人工查看直接从[清单](tasks/W003/manual-verification.md)展开全部图、坐标、输入/期望文件与正反例，不依赖本机临时包或Python环境。完整临时执行/review日志包本次没有上传，Git中的执行/review结论与人工材料已包含；若要在另一主机复用附件级审查证据，再单独转存对应完整包。

## 下一步：从 MR-054 继续人工核验

先读[清单恢复点及 MR-052–MR-054](tasks/W003/manual-verification.md)，处理 B4.03d 的 DBU 疑问；之后按用户指示进入 B4.04a 的三项必需导出产物与缺项预期。剩余 export 字段、validation、limitations、B5/B6、全部 C/D 继续按清单覆盖。旧版一个正常小单元及22个负例共75个fixture文件，A有44个矩形，D有20条记录/8类失败；这些是原版数量，修订样本后须重新核对。

已定待改方向包括单位/规则来源、tech 分类、孤岛拆为专门案例、normalized 可读性、单一 Calibre-like raw 方言及 tapcell/body 场景；具体要求以清单 MR 编号为准。MR-040 配置精简方案仍未采纳。MR-052 已收回本阶段完整 grid/CSP/registry 实现设计的扩展；32×16 仅需说明测试假设、用途与引用，完整坐标系统留后续 Stage 2。用户说“继续”允许换主题，不自动记通过，也不反复要求确认既有决定。

顺序：**用户核验/必要修正 → W003最终验收 → 明确并派发M1最小parser/输入绑定任务**。本轮尚未创建或启动下一实现包。远期M1完整文件闭环的初始化/不可变性/CAS/约束/导出失败等义务仍保留在W002 E7/R4与W003 handoff，不因先拆parser而省略。

## 生产 parser 测试与真实缺项

W003只交样本/合同/辅助，产品parser未实现。推荐后续Stage1 parser/输入绑定包经本地正常/失败检查与针对性review后，由用户单向上传隔离服务器测试；无需等M1全闭环完成，也不将本包reader或legacy parser当正式准入交付。先解析已有raw与实际调用Calibre获取query证据分别记录，前者不证明后者。

用户确认的隔离边界见 [环境记录](environment/remote-development.md#隔离生产服务器用户确认的边界)：向内只能上传代码，向外只能描述数值脱敏格式。目标机平台/Python/离线依赖、能否携带样本、允许反馈字段及内网真实验收回执尚未明确；PM可继续准备这些条件，不能默认为允许回传raw、结果、日志、hash或pass/fail。未决定公开PDK/VM投入，也未改变真实验收方式。

W002 E3 G1–G4仍阻塞真实M2；G5本系统live acquisition证据最迟M3齐备。Stage6 signoff延期不能消除这些门。真实证据可留内网，但PM不从脱敏格式或本地synthetic通过推断真实matched/live或生产准入。

## 历史验收入口

[W001](tasks/W001-v2-global-plan.md#6-pm-验收与交接pm) 保存独立规划review、PM验收和Git集成事实；[W002](tasks/W002-first-input-admission.md#pm-验收与交接pm) 保存已验收调查方案与后续条件。最小协作规范原稿为 `e57f2ddd3122892ad73f473803f2d16d2f632e87`，其完整验收入口保存在 `6eccdff99a4da64e46921d16a4c339198813bc78:docs/current-work.md`。

现行架构、协作规则、环境文档和任务记录各自承担唯一职责。已完成的规划、样本准备和技术review均不证明v2产品、真实工具/PDK或生产正确性；产品执行→修复→组合验收周期仍待实际运行。
