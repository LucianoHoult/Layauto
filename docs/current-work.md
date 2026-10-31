# 当前工作入口

更新：2026-10-31。PM 维护当前节点和恢复入口；详细状态、决定、证据与 reviewer 结论归任务文件。

## 当前节点

**当前节点为W004任务收敛，阶段待准备；下一session只做执行准备，不开始实际样本修改。** 按用户最新指令，先交精简要求、文件依赖、待决项、验收清单和实施顺序，回PM接收后再明确启动。W003保持待验收；M0真实准入出口仍未满足，M1产品尚未实现。

- [路线图](roadmap.md)：M0 准入准备 → M1 no_change 保真文件闭环 → M2 首个实际 shrink 闭环 → M3 多器件/多 delta 首版覆盖 → M4 可复现验收；能力目标和实质验收要求保持已审内容。
- [W001 — 首版全局规划](tasks/W001-v2-global-plan.md) 与 [W002 — 首个准入调查/方案](tasks/W002-first-input-admission.md) 已验收、提交并推送；它们不证明 v2 产品能力。
- **当前任务：[W004 — W003样本修订与验证](tasks/W004-fixture-revision.md)**：R1–R5是待收敛的修订输入，本阶段只读实物、修改任务准备文档；原版交付/review与决定留在W003，P7仅作历史候选参考。
- **当前人工入口：[W003 人工核验清单](tasks/W003/manual-verification.md)**。B4后段/B5/B6与D1/D3/D4已确认；C为22例用户概览，D2为20条委托总览并保留检查身份修订。A/B旧需改与未决仍在；[MR-076汇总](tasks/W003/manual-verification.md#mr-076)是当前恢复点，不从A1或MR-054重讲。
- 2026-09-10 用户授权新建审核分支并提交/推送，方便在另一平台查看。W003材料已发布到 `codex/w003-manual-review`，仍待用户验收、未合入main；不开始产品实现、架构拆分、EDA/VM或生产上传。
- 网页子PM历史交接见[交接页](tasks/W003/web-codex-handoff.md)、P5/P6；总PM接收见P7、转交见P8。后续从W004任务收敛开始；用户已授权本轮文档提交推送，未要求执行main合并或删除分支。

## 恢复与版本身份

先读根 [AGENTS](../AGENTS.md)、[README](../README.md)、[协作规则](collaboration/rules.md)、[W004](tasks/W004-fixture-revision.md)和人工MR-076；按R1–R5只读回查原MR、架构、样本及W003 E/R证据。下一session收敛任务并做准备review，不重新讲解全部历史，不把准备review或旧review当新版样本证据。

**审核分支：`codex/w003-manual-review`。** 原技术材料提交为 `01535055f5d661a2964443dec76fc7f7f305e3e0`，其发布说明提交为 `6d29b511ac415a9ea198d1e5c8978313c5abb6e3`；人工记录MR-001–MR-076仍针对该版实物。网页续接基线为765ae5ef4ebf50e6870c5a978795525261d89ff6，本轮文档保存于其后续提交；实际启动须核对branch/HEAD、工作区及远端，确认已包含MR-076与最新网页交接。从审核分支恢复，不从 main 寻找尚未合入的 W003。

2026-10-31提交准备时，本地及远端审核分支均为`b41ba92940516ecadd26c64fc9fcb6829d21cbe1`，main为b1f0301；`git fetch/ls-remote`成功。W004与本轮PM入口随本次文档提交保存，使用交接回复中的最终发布SHA，并核对本文件含“任务收敛”；旧b41ba92不含W004。共享环境配置不保证共享磁盘，以Git实际版本/文件为准，具体推送成功事实由远端核验及交接回复记录。

**Git基线：`main@b1f0301cf76b2e1808cb293cfdb4e1bfededde73`**，为W002发布记录；W002已验收正文提交为 `f141af99525c48819aa97416e8cb81e9091d6c0e`。2026-09-10推送后同时核对远端main仍为b1f0301。本次未创建PR或合并。

**当前受审执行材料：**`/private/tmp/layauto-w003-independent-review-i8gqzwtw`。PM核对其1938条manifest和接收时92份snapshot，完整补丁可从上述基线重建；`full.patch` SHA-256为 `c03a90b4f49c51a2343d54ad110420801d7b39966f6f5b6ec34c7b5b8fd1178f`，其余身份/原始记录见W003 P0。PM随后仅改任务阶段/PM段、当前入口、导航并新增人工清单；这些PM文档不再与受审包逐字节相同，执行材料和reviewer原文保持该身份。

**加入PM记录后的恢复包：**`/private/tmp/layauto-w003-pm-received-ew822nhg`，包含93文件完整snapshot/patch、独立review包副本和本轮文档检查；表示待用户验收，详情见W003 P3。

本机历史W002完整接收包为 `/private/tmp/layauto-w002-accepted-xvwblftq`；旧W003草案/准备/初审包只作历史，不作为当前恢复输入。临时路径不随Git上传，跨主机复用附件证据必须另保存完整可访问版本；路径失效不能继续声称附件已核验。不要重跑历史快照生成脚本覆盖证据。

跨平台人工查看直接从[清单](tasks/W003/manual-verification.md)展开全部图、坐标、输入/期望文件与正反例，不依赖本机临时包或Python环境。完整临时执行/review日志包本次没有上传，Git中的执行/review结论与人工材料已包含；若要在另一主机复用附件级审查证据，再单独转存对应完整包。

## 下一步：收敛W004，交PM接收

按[W004](tasks/W004-fixture-revision.md)形成精简要求、实际文件/数据依赖、最少待决及推荐、后续验收和实施顺序。body候选只能在准备文档中表达，不写入正式fixture；P7坐标不是已批准要求。只读调查可并行，准备文档统一集成，交独立准备review后回PM；已定方向不重复询问。

MR-040配置精简候选仍未采纳；B4.03c.2按MR-051/052只处理样张解释/引用，完整坐标/CSP/DTO/codec/CAS留后续。原版44图形、75个fixture文件、20条记录/8类失败等数量不是新版验收答案；旧版技术review与本轮确认不自动覆盖修订后材料。

顺序为**任务收敛/准备review → PM接收并明确启动 → 实际修订及新版独立review/人工结论闭合 → PM接收W004并关闭W003遗留 → M1 parser任务**。收敛完成不代表W004最终验收；本轮及下一准备session均不开始fixture写入或产品实现。

## 生产 parser 测试与真实缺项

W003只交样本/合同/辅助，产品parser未实现。推荐后续Stage1 parser/输入绑定包经本地正常/失败检查与针对性review后，由用户单向上传隔离服务器测试；无需等M1全闭环完成，也不将本包reader或legacy parser当正式准入交付。先解析已有raw与实际调用Calibre获取query证据分别记录，前者不证明后者。

用户确认的隔离边界见 [环境记录](environment/remote-development.md#隔离生产服务器用户确认的边界)：向内只能上传代码，向外只能描述数值脱敏格式。目标机平台/Python/离线依赖、能否携带样本、允许反馈字段及内网真实验收回执尚未明确；PM可继续准备这些条件，不能默认为允许回传raw、结果、日志、hash或pass/fail。未决定公开PDK/VM投入，也未改变真实验收方式。

W002 E3 G1–G4仍阻塞真实M2；G5本系统live acquisition证据最迟M3齐备。Stage6 signoff延期不能消除这些门。真实证据可留内网，但PM不从脱敏格式或本地synthetic通过推断真实matched/live或生产准入。

## 历史验收入口

[W001](tasks/W001-v2-global-plan.md#6-pm-验收与交接pm) 保存独立规划review、PM验收和Git集成事实；[W002](tasks/W002-first-input-admission.md#pm-验收与交接pm) 保存已验收调查方案与后续条件。最小协作规范原稿为 `e57f2ddd3122892ad73f473803f2d16d2f632e87`，其完整验收入口保存在 `6eccdff99a4da64e46921d16a4c339198813bc78:docs/current-work.md`。

现行架构、协作规则、环境文档和任务记录各自承担唯一职责。已完成的规划、样本准备和技术review均不证明v2产品、真实工具/PDK或生产正确性；产品执行→修复→组合验收周期仍待实际运行。
