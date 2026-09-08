# v2 架构分解与 Codex 开发工作流（提案）

状态：历史工作流提案，本文不作为当前运行指令。2026-09-08 已按用户确认的最小范围编写 [协作规则](../collaboration/rules.md)、[任务模板](../collaboration/task-template.md) 和 [当前入口](../current-work.md)，第一版待独立 review。

已吸收的方向：角色分工、按需读取、滚动细化、版本化证据和跨会话交接，以新文件中的具体约定为准。本文中的旧目录布局、一次性合同迁移、首批切片和第 14 节“下一步”仍是候选，不构成本轮授权、排期或已实现能力；后续如采纳需在相应现行文件落位。

依据：2026-09-04 本地 `HEAD=a25a011d8b4c48bfb4e4ce79d288ce7eefa12e77`；
`docs/architecture.md` Git blob 为 `811a9b1c9df0ce4e69b649183f71921a541ea5bd`。
文档共 2,442 行、263,426 bytes。本次未重新执行架构事实审计或测试；工作区已有开发环境相关修改。

## 1. 建议采用的整体结构

建立四种各有归属的材料：**持续生效的工作规则、按需读取的架构合同、随任务展开的执行方案、绑定版本的验证证据**。
先做读取路由和一个真实开发工作包，再逐批迁移架构正文。文档拆分成功的标准，是新会话能找到适用合同、完成边界清楚的变更，并留下可复核证据。

空间、角色、时间分别处理：

| 维度 | 承载方式 | 主要回答 |
| --- | --- | --- |
| 目录与代码边界 | 分层 `AGENTS.md` + 架构读取路由 | 修改这里时必须守什么、读什么？ |
| 执行职责 | 按需读取的角色约定与模板 | 本轮应产出什么，交给谁，如何检查？ |
| 开发进度 | 工作包、依赖、验收和交接记录 | 下一步能做什么，什么证据表明已完成？ |
| 长期设计 | 有唯一归属的架构合同 + 少量决策记录 | 系统必须如何表现，为什么？ |

这些是开发组织方式。Layauto runtime 的 Stage 1–6 继续表示程序数据流；不与 Codex 的 plan/build/review/verify 阶段混用。

最值得先确认的四项选择：

1. 用仓库中的版本化工作包作为跨会话恢复入口；对话、PR、Issue 作为链接和协作界面。
2. 先保留 `architecture.md` 的权威地位并建立索引，再按合同逐批迁移，避免同时维护两套完整正文。
3. 只为近期工作包展开实现细节；首版采用已确认输入子集，明确候选 profile、工具验证与 durability 的范围。
4. 常规实现持续推进；影响架构、能力范围或跨模块合同的变更单独 review。人的主要 review 对象是设计差异和完成证据。

## 2. 当前仓库对方案的约束

- [架构文档开头及 §1.3](../architecture.md) 已要求开发顺序、任务拆分与验收安排另行维护，但执行计划不得覆盖架构合同。
- 架构 §13.3 和 [docs 入口](../README.md) 要求新发现的问题回到对应架构归属。执行工作包记录落实工作，不重新建立平行的需求 backlog 或 audit 规范。
- [README](../../README.md) 与实际源码表明 v2 仍是骨架；§11.1 中的 `tech/`、`repository/`、`normalization/`、`tooling/`、`reporting/` 等规划 owner 尚未完整落入目录。不能照现有目录机械分文档。
- §1.4 已确认首版 single-finger、one-to-one device mapping、no-device-reduction。Single-finger 不等于 single-fin，也不限制为单 device 或单 delta。
- 同节明确真实 PDK/profile 尚未验证。`explicit_static_fin_plus_active_window` 是候选，不能在摘要或任务模板中升级为通用事实。
- §2.6、§9.2 允许 process-local MVP；§10.5 允许真实 Calibre/SKILL 验证明确 deferred。详细描述的未来合同不自动成为首版实现清单。
- [开发环境文档](../environment/local-setup.md) 记录初始环境与测试基线。历史 legacy 测试结果不构成 v2 验收证据。

## 3. 文档归属：每项规则只在一处定义

建议的目标目录如下；这是逐步形成的结构，不是本轮要批量创建的空目录清单。

```text
AGENTS.md                         # 仓库工作规则、读取入口、环境链接
layauto_v2/AGENTS.md              # v2 通用边界与模块路由
layauto_v2/<boundary>/AGENTS.md   # 确有局部规则时才增加
tests/AGENTS.md                   # 有 v2 tests 后按需增加
docs/AGENTS.md                    # 迁移、摘要与文档归属规则
docs/architecture.md             # 迁移前完整权威；迁移后总览与合同索引
docs/architecture/               # 逐批迁入的规范正文，见下一节
docs/development.md              # 安装、环境、可执行命令
docs/development-workflow.md     # 阶段、角色、恢复协议、模板
docs/work/README.md              # 工作包 ID、依赖、链接；不复制详细状态
docs/work/Wxxx-<name>.md          # 一项工作从规划到集成的唯一执行记录
docs/decisions/                  # 仅保存重要的新决策及理由，按需创建
```

各类内容的边界：

| 材料 | 应包含 | 不应持续堆入 |
| --- | --- | --- |
| AGENTS | 适用范围、少数硬边界、读取触发条件、验证入口 | 长篇设计、任务进度、通用人格说明 |
| 架构合同 | 责任、输入输出语义、状态所有权、不变量、失败语义、能力边界 | 每个 PR 的施工步骤和调试日志 |
| 架构摘要/路由 | 核心约束提示、模块与合同的对应关系、源链接 | 改写后的第二套详细要求 |
| 工作包 | 目标、依赖、实施选择、验收、当前状态、交接 | 全文粘贴架构、永久保存每轮思考 |
| 决策记录 | 问题、选项、取舍、决定及受影响合同 | 把既有合同全部补写成虚构历史 ADR |
| 代码与测试 | 当前实现、可运行的行为与边界证明 | 将尚未实现的计划标成现有能力 |

发现代码与合同不符时，记录具体差异：代码说明“目前做了什么”，合同说明“应该做什么”，不能互相静默覆盖。
新决策生效时在同一变更中更新规范正文；后续任务无需遍历全部历史决策才能知道现行要求。

## 4. 按合同面拆解架构，而非一章一文件

下表是建议迁移归属。现有章节含交叉合同，因此迁移单位应是具体条款；表中的章节允许出现在多行，但每条规范最终只有一个正文归属。

| 目标正文 | 当前主要来源 | 主要消费模块 |
| --- | --- | --- |
| `architecture.md`：目标、首版范围、Stage 总图、读取路由 | §1、§2 的阶段概览、§11.1 | 所有任务 |
| `architecture/evidence-capabilities.md` | §2.2–2.4、§3.1–3.2、§4、§5 的输入部分、§12.1–12.7 | domain、tech、tooling、importers、normalization |
| `architecture/state-views.md` | §3、§4 的状态抽象、§11.3 | state、normalization、annotation、derive、constraints |
| `architecture/annotation-connectivity.md` | §3.3、§3.6–3.7、§4.6–4.7、§5 | annotation、state、constraints、planning |
| `architecture/planning.md` | §2.5、§6、§7 | planning、domain、pipeline |
| `architecture/constraints.md` | §2.4/2.6 的检查合同、§8 | constraints、tech、transactions |
| `architecture/publication.md` | §2.6–2.7 的 publication/closure 合同、§3.8、§9、§11.4 | domain、repository、transactions、derive、pipeline |
| `architecture/artifacts-validation.md` | §2.7、§10、§11.11–11.13 的相关合同 | export、validation、reporting、tooling、pipeline |
| `architecture/verification.md` | §11.15、§12.8、§13 的追溯映射 | tests、fixtures、集成/review 任务 |

§11 的模块职责分别放入相关合同的 owner 表；没有必要再为每个 Python 文件或 class 创建同义指南。
某一模块确有独立复杂算法、扩展点或运行约束时，再增加模块设计说明，并从对应 AGENTS 链接。

模块读取路由需要覆盖“跨边界问题”。例如：

- 修改 `planning/resize.py`：读首版范围、物理修改/profile、规划合同；另读 Stage 5 的接收条件和相关 mandatory checks。
- 修改 `transactions/`：读 publication 主合同，并读 state、annotation/derive 依赖失效及 constraints 的 query-only 接口。
- 修改 `export/`：读 artifacts-validation 主合同，并读 snapshot/codec 与 publication 的只读消费边界。
- 修改中立 DTO：读其 owner 合同和所有受影响生产者/消费者；文件位于 `domain/` 不代表只有 domain 任务受影响。

Legacy 问题中已经吸收为现行合同的要求继续放在合同里；原因、原始证据和归属关系留在精简追溯表。
例如“Stage 6 曾补写几何”应指向只读导出合同及其测试，不必在每个模块反复讲一次 legacy 历史。

## 5. AGENTS 层级与加载方式

根 AGENTS 保留现有环境、legacy 和工作区约定，增加读取路由和恢复入口。
`layauto_v2/AGENTS.md` 仅承载全 v2 都适用的边界；最初通常两级足够。
第三层只用于真实局部约束，例如 publication owner、query-only constraints 或禁止 exporter 写状态；没有差异就不创建。

OpenAI 官方说明中，指令按项目根到启动工作目录形成链，较近目录的指导覆盖较早指导；默认合计大小限制为 32 KiB，`AGENTS.override.md` 优先于同目录 `AGENTS.md`。
不能假设从仓库根启动会自动递归装载全部子目录规则。[官方 AGENTS 文档](https://learn.chatgpt.com/docs/agent-configuration/agents-md)

因此建议根指令明确：开始修改前，定位目标路径并读取适用的祖先/局部 AGENTS，再按路由读取合同；扩大修改范围时补读新增边界。
任务卡写明必读路径和条件读取路径。文件已经在工作区中，不代表当前会话已读取；会话里修改指令后，也应显式重读，验证下次启动的加载情况。

可以用以下内容作为局部 AGENTS 的样例，实施时链接到已经存在的规范页面：

```text
适用：本目录及子目录。
修改前读取：<合同路径与稳定锚点>；涉及共享 DTO 时补读其消费者合同。
本目录的特殊边界：<2–4 条本地约束或关键约束提示，并附源链接>。
验证入口：<当前已存在的测试路径/命令>。
若改动公共合同：列出影响的调用方，更新合同、任务记录和相关边界验证。
```

局部指令不得将已确认的全局架构约束放宽。需要例外时修改真正的合同归属，并让例外的范围、理由和验收可见。
角色文档中的文字不会自动创建 agent；编排由当轮任务决定。

## 6. 摘要、详略与 Codex 自主空间

区分两条相互独立的信息：**条款性质**与**实现状态**。
前者为规范要求、建议方案、示例或背景；后者为未实现、已实现待验证、已验证或明确 deferred。
“架构已确认”不等于“实现已验证”，“候选 profile”不等于“已选择真实工艺”。

摘要必须保留五件事：适用范围、状态 owner、关键不变量、失败/unsupported 分支、原文链接。
特别不能压掉这些限定：process-local/durable、single-finger/multi-finger、known/unknown annotation、whole-intent/partial、no-change、deferred/required tool failure。
摘要负责找路；即将修改某合同的行为时，读取完整条款与相关测试。

建议起始规模如下，仅用于识别膨胀，不作为格式门禁：

| 内容 | 建议规模 |
| --- | --- |
| 根 AGENTS | 约 40–80 行 |
| v2 AGENTS | 约 30–60 行 |
| 局部 AGENTS | 约 15–35 行，且只写差异 |
| 任务启动包 | AGENTS、总览摘要、一张任务卡、相关合同和源码 |
| 普通任务计划 | 半页到两页；复杂协议允许更长 |
| 会话交接 | 当前状态 + 下一步 + 风险/证据链接，约 10–20 行 |

实际维护时统计字节/读取量，不能只用行数估算中文文档的上下文占用。预算不足时继续按需展开，不能为压缩而删掉关键合同。
起步不建立每目录 SUMMARY、每角色 MEMORY、每日流水账或多级摘要树。

应约束外部可观察的行为与责任：输入输出、不可变性、错误语义、兼容范围、验收证据。
函数拆分、局部算法、私有 helper、内部数据结构和无需改变合同的重构由实施者选择。
只有影响跨模块接口、性能约束或正确性证明的算法选择，才需要预先细化设计。

## 7. 角色约定：定义产物，不设固定组织层级

角色模板先集中放在 `development-workflow.md`；重复使用且确有收益后再提炼为仓库共享 skill。
同一 agent 可承担多个阶段；关键变更优先由独立 reviewer 检查。独立 review 仍需要测试证据，不能用多个 agent 的一致意见替代验证。

| 角色 | 输入与职责 | 最小产物 |
| --- | --- | --- |
| 协调/规划 | 架构范围、依赖、现有代码；选择一个可验收工作包 | 任务卡、范围、验收、可并行边界 |
| 设计 | 解决近期任务尚未确定的合同/算法选择 | 有依据的方案差异、接口影响、失败路径、必要决策 |
| 实施 | 按任务卡和合同完成代码、测试、相关文档 | 可 review 的 diff、执行证据、偏差说明 |
| Review | 检查目标与合同、错误路径、测试区分能力 | 绑定版本的具体 findings、严重性、依据与处理结果 |
| 集成 | 检查共享合同、依赖与组合行为 | 集成版本、必要回归证据、可恢复的下一步 |

多 agent 只拆能够独立交付的工作。共享 schema 和调用方尚未明确时，先收敛合同。
每个可写子任务指定文件范围、输入合同、交付接口、验证方式和一个集成负责人；只读 review 可广泛并行。
修改共享 schema、主索引或 pipeline 接线时应明确单一负责者，减少并发冲突。不要让多个写任务操作同一个 checkout 的同一文件。

## 8. 时间顺序：滚动细化，按风险 review

远期保留里程碑、依赖和可观察产出；近期工作包补上验收与接口；开始编码前再解决必要实现细节。
每个工作包经历以下过程，小任务可在同一会话完成：

| 阶段 | 本阶段应回答的问题 | 完成条件 |
| --- | --- | --- |
| 定义 | 解决什么问题，属于哪条合同？ | 有范围、非目标、依赖和可验证验收 |
| 设计/计划 | 哪些选择尚未确定，会影响谁？ | 接口/失败路径可实现，重要决策明确 |
| 方案 review | 计划是否漏掉约束、抬高范围或无法验收？ | 相关问题已有处理结论；仅在风险需要时单独进行 |
| 实施 | 如何让验收成立？ | 代码、相关测试和必要文档一起完成 |
| 代码 review/验证 | 当前 diff 是否满足合同，失败路径是否可信？ | findings 有处置，证据与代码版本对应 |
| 集成/交接 | 与其他已完成部分组合后能否成立？ | 集成版本可定位、必要验证通过、后续状态已更新 |

建议三档 review 深度：

- **小变更**：文字修正、既定合同内的局部修复，使用简短计划和相关验证；不强制单独设计文件或人工停顿。
- **普通功能**：工作包、接口/验收、实施后 review；已有明确合同即可推进。
- **关键边界变更**：首版范围、shared DTO、publication/rollback、物理解释、validation acceptance policy，先有具体方案及影响分析，再进入独立方案 review；改变用户已确认目标时由用户决定。

Review 关口表示需要证据和结论，不表示每一步都必须等待用户确认。已授权范围内的问题修复、测试与常规实现应持续完成。
你的 review 摘要主要看：本次行为变化、合同/范围是否改变、关键证据、未解决风险、确需你决定的问题；详细 diff 和日志按链接展开。

## 9. 一个工作包贯穿多次会话

建议先采用 repository-first：一个工作包 ID 对应一张版本化 Markdown 记录。
`docs/work/README.md` 仅列 ID、目标、依赖和链接；详细状态由工作包拥有。规模增长后可生成状态表，避免人工维护两份状态。
Issue/PR 如需引入，链接同一 ID；若未来改由 Issue 作为进度权威，明确迁移归属，不同时维护两套精细台账。

推荐状态为 `queued → ready → active → in_review → integrated`；阻塞原因另列字段。
`ready` 表示验收与依赖已经足够明确；`in_review` 不等于已完成；`integrated` 要引用约定目标分支上的集成版本和相应验证证据。

每张工作包至少包含：

```yaml
id: Wxxx
status: queued
objective: 一句可观察的行为目标
scope: [负责的模块/边界]
non_goals: [本工作包明确不承诺的能力]
depends_on: [工作包 ID 或既有接口/fixture]
contracts: [规范路径及稳定锚点]
acceptance: [可判断成立或失败的行为]
```

下面的字段随推进才补充，不要求新建任务时填完：

```text
计划与决策：必要实现步骤；重要选择及合同变更链接。
工作位置：branch/worktree；一个当前负责人；可选会话链接。
恢复点：实现 commit；尚未提交的文件及保存方式；下一项具体动作。
验证：被测代码版本/差异、环境/profile、命令、结果、artifact/日志链接。
Review：base/head 或明确 diff 身份；reviewer；findings 及处理结论。
集成：PR/目标分支的最终 commit；组合验证结果。
剩余问题：真正的阻塞、范围变化、尚待验证的假设。
```

不能仅记录“tests passed”：至少能知道哪个版本、哪些测试、使用何种 fixture/profile，以及未执行的必要检查。
只保留当前短交接和重要决定；历史细节由 Git、PR、测试产物承担。
任务完成后保留文件及链接，通常无需搬目录；索引把 active 与 completed 分组即可。

## 10. 跨会话恢复、并行与 review 有效性

新会话的恢复顺序：

1. 验证仓库、branch、HEAD 和工作区修改；区分原有改动与当前工作包产物。
2. 读取适用 AGENTS、工作包、相关合同和现有测试，不要求先阅读全部历史对话。
3. 比较任务记录中的恢复点与当前代码；检查依赖接口及架构是否已发生相关变化。
4. 明确哪些证据仍适用，哪些必须补验；从记录的下一项动作继续。

会话结束、交给其他任务或准备切换机器时，更新同一工作包的恢复点、未提交状态、证据和下一步。
不要求每条回复都写文件。每次具有独立意义的实施、review 或集成完成后更新即可。
记录引用最后一个实现 commit；提交该记录产生新的文档 commit 是正常的，不追求记录“包含自身 SHA”。

Review 应绑定 `base/head` 或工作区 diff 身份。Fix 或 rebase 后针对变更重新评估受影响 findings 与测试；原有 review 不自动覆盖新增代码。
需要跨会话复用未提交代码的证据时，优先保存为实现 commit；否则保存带基线和内容标识的可重建补丁/快照，覆盖相关 staged、unstaged 及 untracked 文件。未保存完整被测/被审内容的记录只算临时证据，不能在另一会话直接继承为已验证。
仅修改交接文档也不应无理由触发全套功能测试。最终集成变更若影响接口或行为，补相关组合验证。
PR 合并状态、会话标题或“已完成”文字都不能单独证明目标行为成立。

并行写入可用独立 Git worktree/分支和明确集成负责人。云端恢复所需代码、合同、工作包必须已经通过 Git 可获取。
本地未提交变更、虚拟环境和对话上下文不能假设在云端存在；具体环境操作沿用 [remote-development.md](../environment/remote-development.md)。
不要把项目开发状态依赖于个人 Codex 记忆；仓库材料应能让另一台机器上的新会话恢复工作。

## 11. 验收与追溯：让架构义务逐步变成证据

对高风险、跨模块、容易在摘要中丢失的合同分配少量稳定 ID；不必给每段文字编号。
每项义务记录唯一规范归属、实现工作包、测试/证据与范围。其余细节直接使用路径与锚点。
以下 ID 和测试名仅作提案示例，尚未创建或执行：

| 示例 ID / 合同义务 | 当前规范归属 | 应出现的验证 |
| --- | --- | --- |
| `PUB-01`：失败组不发布部分状态 | §9.1–9.3 | 向 materialization/finalization/发布前失败点注入异常，对比所有权威组件与 parent snapshot |
| `STATE-01`：旧 snapshot 无可写别名 | §2.6、§3.8、§11.15 | 修改嵌套输入/后续版本后，旧 snapshot 内容和 digest 保持 |
| `PLAN-01`：规划不写 committed state | §7.2、§9.1 | planning 前后 snapshot 不变；candidate 仍由 Stage 5 验证 |
| `EXPORT-01`：Stage 6 不补写状态 | §10.1、§11.15 | 导出前后 snapshot 一致，缺失 final state 时 typed failure |
| `SCOPE-01`：首版子集之外明确拒绝 | §1.4、§12.8 | multi-finger、非 one-to-one、需要 reduction 的输入 admission 拒绝，无 ECO mutation |

验证分为三组，按任务需要选择：

- 合同与行为：runtime schema、exact geometry、annotation/connectivity、constraint、transaction 的单元/集成测试与关键 architecture tests。
- 端到端：小 fixture 的 success、no-change、unsupported、失败回滚、导出/validation 失败和 required artifact 一致性。
- 工具与生产证据：tool-captured fixtures、独立工具检查和真实 signoff，明确哪些当前已覆盖，哪些 deferred。

Fixture 应标注来源、profile、generator/version 和 limitation。借用 legacy 纯逻辑时在 v2 owner 内重建测试，runtime 与 production tests 不 import legacy。
Golden 比对要与不变量、语义一致性和错误路径组合；旧 fixture、同源读写器与实现代码不能形成自我证明的闭环。
测试强度随风险增加；文档小修和局部低风险重构不要求新增镜像实现的测试。

后续有真实工作包后，再补小型自动检查：链接/锚点、规范 ID 唯一性、工作包字段、import 边界和相应合同测试。
机器检查能发现悬空引用和结构违规；摘要是否改变语义、验收是否误抬为生产保证仍需 review。

## 12. 建议的首批开发切片

以下是可调整的实施顺序建议，不是已批准排期。每个切片有可观察产物，涉及多个模块；避免以“写完所有 domain，再写完所有 state”作为完成标准。

| 切片 | 可观察的结束状态 | 主要依赖与范围 |
| --- | --- | --- |
| A：范围、fixture 与合同种子 | 有具名 synthetic profile 的正例/拒绝样例，最少中立 DTO/codec 校验可运行；fixture limitation 清楚 | §1.4、§11.2、§12.8；不声称真实 PDK 已支持 |
| B：证据到 baseline | 输入 GDS/CDL/query/tech，完成归一化、annotation/物理解释；经 InitializationTransaction 发布可查询 immutable baseline | A；验证 ownership、create-if-absent、初始化失败无泄漏和旧 snapshot 不变 |
| C：baseline/no-change 到可检查产物 | 无 ECO commit 的合法 run 能导出 GDS/CDL/JSON/report 与结构化 validation；必需 artifact 失败能正确结束 | B；提前贯通 Stage 6，deferred 工具状态明确 |
| D：候选及 mandatory checks | 首版 shrink 的 fully-ground candidate 含必要 repair；支持拒绝样例、检查失败和规划只读验证 | B，可与 C 在合同明确后并行；profile 与约束缺失不能伪装可执行 |
| E：完整 shrink 提交与导出 | whole-intent 修改、所有派生闭包和检查、原子 publication、失败回滚、完整产物/报告链成立 | C + D；process-local，覆盖多 device/required delta 正例、same-parent 竞争、同 key 同 digest 响应丢失重试、同 key 异 digest conflict |
| F：首版验收与环境适配 | 复跑各切片已落地的合同测试；补足输入漂移、失败路径的组合场景，包安装与演示可复现；能力和 limitation 可审计 | A–E；真实 captured dialect/PDK证据可尽早并行准备 |

各不变量及必要失败测试在对应接口首次实现时交付；F 负责复跑与组合验收，不能用后续切片承诺替代当前接口的正确性门槛。

真实 Calibre/Virtuoso 与真实 PDK 接入的具体时机取决于可用证据和选定验收 profile。
在其缺失时可以推进 synthetic 合同验证，但不能因此宣称生产 signoff 已完成。
Crash-durable backend、多指/reduction、grow 等扩展另列依赖明确的后续工作包，不隐式纳入 E/F。

## 13. 将超大文档迁移为上述体系的步骤

1. **确定基线和路由。** 以当前已审阅架构版本为起点，建立条款归属表和精简总览。先把所有旧章节映射到规范、示例、背景或追溯材料，避免遗漏。
2. **试行最小执行体系。** 落地精简工作流、一个工作包模板、第一张具体工作包和必要 AGENTS 路由。此时完整规范仍在原文，摘要使用源链接。
3. **选择一个边界试拆。** 建议优先 publication/rollback，或配合首个工作包的 evidence/admission。将规范原文迁入唯一归属，更新入口和引用，旧位置留下索引；迁移与改变语义分开 review。
4. **逐批迁移其余合同。** 每批检查限定条件、失败分支、类型字段和跨模块责任是否保留；§13 中已吸收问题保留追溯关系。旧全文由 Git 历史保存，不再保留另一份 active 镜像。
5. **用一次完整工作包校验体系。** 从新会话开始规划、实现、review、验证并交接，记录找不到的合同、重复读取、交接遗漏和 review 负担，再调整模板。

迁移生效时，同步更新 architecture 开头“唯一 source of truth”的说明、docs/README 的全文必读要求与 §13.3 的归属路径。
用新合同集替代旧的单文件归属，继续保持一项要求只有一个规范定义；这不是创建第二套需求池。

首轮 review 应重点检查：是否有条款无归属、同一要求重复规范化、例子被提升为必须实现、重要限定被摘要丢失，以及未验证实现被表述为完成。
评估体系是否有效，可观察新会话完成定位所需读取量、交接后重复分析量、review 中的范围偏移和集成返工；有具体问题再增加流程。

## 14. 下一步的具体交付建议

下一项工作可以限定为：**建立路由、工作流和一个可执行工作包，并试拆一个合同面**。
产物应包含：精简的 AGENTS 变更、合同归属映射、工作包模板、首个工作包的验收及必要细节、一个已迁移且无语义漂移的合同页面。
完成标准是另一会话仅凭这些入口即可明确工作范围、适用合同、实现自由度和验收方式；不以文档数量或目录完整度计完成。

真实 PDK/profile 选择、可用 captured query evidence 和最终验收工具环境需要在对应工作包开始前落定。
这些外部条件不会阻止先完成文档路由与 synthetic 验证体系，也不会被模板中的默认值替代。
