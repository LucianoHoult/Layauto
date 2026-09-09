# W002 — 首个输入证据与闭环准入准备

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| ID / 目标 | W002；给出第一套输入的可核查准入结论、真实资料缺口，以及可直接拆出 M1 实现包的共享合同/失败流方案 |
| 里程碑 / 依赖 | [roadmap](../roadmap.md) M0；依赖 [W001](W001-v2-global-plan.md) 规划 review 接收（2026-09-09 已满足）。U01–U05 可并行调查，真实资料不足不阻止仓库可做部分 |
| 授权与当前阶段 | **可执行（2026-09-09 PM 确认），尚未启动**；W001 已验收，规划前置满足。本轮仅接收 review 并判断能否继续；本任务可继续范围仍为只读调查/文档准备，产品实现另在近期包明确，状态不扩大授权 |
| 范围 | 定向调查现有输入、legacy 可取用材料、真实资料/工具可得性；形成准入矩阵、最小样本说明、共享中立合同与 M1/M2 验收方案；本任务阶段仅文档/只读调查 |
| 非目标 | 不实现 runtime/parser/fixture generator，不安装部署 EDA、不跑完整 legacy audit、不修旧 fixture、不从零选定/假定 PDK，不拆分架构正文、不 commit |
| 写入归属 | 执行写本文件“方案与证据”段；需要独立附件才在本任务下明确链接；PM 维护阶段/要求/决定/验收；reviewer 独写 reviewer 段。修改路径前重查适用 AGENTS |
| 架构版本与必读 | `6eccdff99a4da64e46921d16a4c339198813bc78` 的 [architecture.md](../architecture.md) §1.4、§2、§3–5、§6–10 的上下游消费条件、§11.1/11.14/11.15、§12–13；共享接口需读双方 owner 原文，不靠 roadmap 摘要定义语义 |
| 负责人 / 阻塞 | PM 待分配执行与独立方案 reviewer；真实输入/PDK/query 材料本仓库不足。先定向检索并列外部缺项，不等待空泛产品决策 |

### 可直接开始的输入与顺序

1. 核对 checkout/HEAD/工作区和 W001 接收版本，读 [协作规则](../collaboration/rules.md)、[本地环境](../environment/local-setup.md)、[W001 盘点](W001-v2-global-plan.md#2-现状与证据盘点)；从已定位路径复核与首个切片直接有关的资料，不重新遍历全部历史。
2. 以仓库 inverter source/target CDL、GDS、dummy raw+YAML 为**场景来源**，列清 provenance、缺 header/closure/真实验证之处；核对已有真实 sample/capture 的可访问位置。没有资料则给最小索取清单（文件/版本/单位/model/query/status/closure），明确持有人/获得方式待谁补充，不伪造输入。
3. 对一套具名候选 profile 填准入表：真实出处、canonical size axes/model token/terminal、finger/mapping/reduction、geometry/CDL subset、exact units、layer/derived registries、rules/extractor/repair、body/frame/halo、query dialect/acquisition。逐项标“有证据/需补证/不匹配”，区分 synthetic/真实；profile 候选不是默认选择。
4. 列最小输入→输出示例说明和反例；对 CDL、报告/fixture 尚未定义的关键使用预期，先调查现有样本，再呈具体差异、影响和推荐项。普通技术保真由 agent 核验；只有关键对外预期/合同变化提交用户决定。
5. 形成 M1/M2 共享接口方案：evidence/tech/result/canonical codec；ProposedInitialState→InitializationTransaction→repository；immutable state/annotation/connectivity；candidate/mandatory scope/finalization；RunAttempt→RunRecord→Manifest→Validation/Reporting→terminal PipelineResult。标中立 owner、producer/consumer、版本/单位/身份、失败 variant、最小组合验证；不先定义全部 helper 或远期模块细节。
6. 给出 M1 的一项近期实现包草案（目标、入口样本、允许范围、验证命令计划、错误路径、依赖），以及 M2 真实准入剩余门。共享语义/物理解释/publication 方案交独立 reviewer 后 PM 接收；未解决的证据问题不静默转成延期或“可实现”。

### 验收与限制

| 验收项 | 输入/条件 → 预期结果 | 依据 / 验证方式 |
| --- | --- | --- |
| 来源可核查 | 原始文件或确实缺失 → file/hash/version/profile/source/limitation 清单，区分 raw 与 normalized | 检查两者同源路径与 closure；dummy/mock 不当真实工具事实。没有实际执行工具就写未执行 |
| 首版准入 | model/query/tech → 单指/一对一/无归并、shrink、精确单位与 geometry/CDL 子集有证据；不匹配/缺项有 typed admission 后果 | 对照 §1.4/§12；不得从 NFIN/NF/M 名或 legacy 方位猜物理语义 |
| Stage 1 获取方式 | `calibre` 与 `dummy_fixture` → 各自 template/dialect/unit/terminator/tool-version/raw-capture 测试需求和可用性清楚 | §12.6–12.7；Stage 6 signoff 延期不能当 Stage 1 live acquisition 延期依据；实机不可得明确影响 M3，必要时附具体延期/范围请求交用户，不能自行放宽 |
| 物理依赖 | 首个候选 footprint → 必需 extractor/rule/LI-VIA-M1 repair/marking/body/halo 及出处可列表核对 | 缺 mandatory operator 时不允许 shrink；若不触及/冻结域，给可复核条件及证明，不以口头承诺豁免 |
| 最早闭环 | M1/M2 场景 → 各范围内正常/拒绝/失败结果、immutable/atomic/no-mutation 条件完整 | M1 semantic/extraction-aware no_change；M2 first changed shrink 已包含全部必要 repair/gates；synthetic 工程成功不冒充真实 profile 通过 |
| 首项依赖可执行 | 共享接口方案 → M1 近期包可直接分派，M2 未解门与可继续工作明确 | 独立方案 review；若真实资料仍缺，工程出口可部分接收，真实准入出口保持未满足。两者不得合写“已完成 M0” |

如果缺真实资料，任务允许交付有证据的缺项清单、最小索取内容与不依赖该资料的工程方案；这不是“真实准入通过”。涉及外部费用、资料权限或新的关键使用预期时，先形成可审阅内容再按协作规则上报。

## 方案与证据（执行）

未执行。执行时记录工作位置/基线、输入版本和来源、定向 legacy 取用理由、共享合同方案、实际调查方法/结果/未查范围、尚需用户判断的具体事项；不代填 reviewer 结论。

## Review 结论（reviewer）

未执行。重点独立核对物理/输入证据、共享 owner/publication/失败流、M1 实现包和真实准入门；绑定被审版本并保留 findings 与复核。

## PM 验收与交接（PM）

2026-09-09 PM 已接收 W001 的独立规划 review，确认本任务要求与仓库可启动部分具备执行条件，阶段转为可执行。**尚未启动、未验收、未集成**；本轮没有执行资料调查或编写共享方案。继续时先做上述只读定向调查与文档准备；真实准入尚未通过，M1 产品实现仍需明确任务范围和共享合同 review 结果。
