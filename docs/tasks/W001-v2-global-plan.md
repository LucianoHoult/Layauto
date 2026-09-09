# W001 — Layauto v2 首版全局规划

## 1. 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| ID / 目标 | W001；让下一会话能按首版路线图核对要求、依赖、验收与首项准备工作 |
| 里程碑 / 依赖 | 全局规划；依赖已验收的最小协作规范、当前完整架构与源文件盘点 |
| 授权 | 2026-09-08 用户指定 PM 恢复，交付可 review 的规划及导航；2026-09-09 用户先要求核对 review、判断能否继续，PM 接收；随后明确授权将现有内容 commit，取代 W001 先前的“不 commit”。授权仅含现有已验收文档及集成记录；仍不产品实现、不架构正文拆分 |
| 范围 / 非目标 | 写 roadmap/current-work/导航及本任务、W002 近期要求；不配置 EDA、不重审全部 legacy、不改变已确认输入范围或产品合同 |
| 架构 / 规则 | [architecture.md](../architecture.md) §1–13，基线 `6eccdff99a4da64e46921d16a4c339198813bc78`；[协作规则](../collaboration/rules.md) §2–6；只有根 [AGENTS](../../AGENTS.md)，本轮检查未发现适用的更近局部规则 |
| 当前阶段 / 阻塞 | **已验收（2026-09-09，规划文档）**；无未处理 finding。真实 profile 尚待 W002 调查，产品里程碑未验收；已验收原稿已提交本地 `main@8482b68`，未 push |
| 负责人 | PM：2026-09-08 本次 Codex 会话；只读专项协助 `/root/inventory`、`/root/coverage_audit`；后续独立规划 reviewer 待分配 |

| 验收项 | 条件 → 预期结果 | 正确性依据与核验方式 |
| --- | --- | --- |
| 全局覆盖 | 完整现行架构 → 首版必需、允许延期、待查明各有归属 | roadmap R01–R29、§13 落点及 D/U 表直接回原文，不由旧提案/legacy 测试定义首版 |
| 路线与首项 | 纯骨架/真实证据缺口 → 有依赖的可观察里程碑、M1/M2 两类首次闭环与近期任务 | 核对不把运行 Stage 当开发阶段，不绕过切片内失败/不变量；W002 可从仓库开展定向调查 |
| 恢复与证据 | 未提交工作区 → 准确当前入口、完整相关快照/内容身份、下一角色和授权限制 | 全部 tracked/untracked 文档纳入检查；同 checkout 可恢复，跨主机需另行保存可访问版本 |
| 范围保护 | 规划授权 → 仅规划/导航文档变更 | `git diff`/status/HEAD 核对；无产品测试、实现、架构正文或 Git 提交变更 |

## 2. 现状与证据盘点

本节记录本轮定向源文件检查；不是已实现能力表。全部源代码事实绑定上述 HEAD，未来复用前重查受影响代码。旧提案只用于辨认历史状态，不作为采用的新规则。

### v2 与验证环境

- 启动 checkout：`/Users/luciano/Library/Mobile Documents/com~apple~CloudDocs/Work/个人项目/Layauto`，branch `main`，HEAD `6eccdff99a4da64e46921d16a4c339198813bc78`；staged/unstaged/untracked 均空。只读专项及 PM 直接抽样 [pipeline](../../layauto_v2/pipeline.py)、[snapshot](../../layauto_v2/state/snapshot.py)，并用 AST 检查全部 58 个 Python 文件：去掉模块 docstring 后无其它节点。排除 legacy 后无 v2 tests。
- [pyproject.toml](../../pyproject.toml) 明确 `requires-python >=3.10`、只发现 `layauto_v2*`、pytest 排除 legacy。现有 skeleton 缺完整 architecture owner（如 repository/tech/normalization/reporting）的运行实现；不按文件数量验收能力。
- 先读 [本地环境](../environment/local-setup.md)。只读专项现场调用指定 Python：3.11.5，`pip check` 为 `No broken requirements found`；`layauto_v2` 定位本 checkout；pytest/numpy/matplotlib/PyYAML/gdstk/klayout/plotly 可定位。`wheel` 不存在；未尝试安装、wheel 构建或真实工具运行。
- 环境文档的 2026-09-02 legacy **366 pass / 1 fail** 仍是历史记录。本轮仅见 `legacy_mvp/output/annotation_coverage.txt` 缺失，不能推断当前回归结果。没有运行 pytest、fixture regen、Calibre/Virtuoso/PDK/license/signoff 或跨主机部署。

### legacy 定向取用清单

| 材料 / 精确来源 | 可取用与需改造的依据 | 计划归属 |
| --- | --- | --- |
| [calibre_query.py](../../legacy_mvp/io_adapters/calibre_query.py)、[query 单测](../../legacy_mvp/tests/unit/test_calibre_query.py) | xref/NET NAMES parsing、header/terminator/error case 是候选；单测真实模式使用 mocked subprocess，不能证明真实 dialect。整数坐标除 precision 得 float、隐含单位需改为 exact decode、显式单位与 header/provenance | M0 调查 dialect/source，M1 parser，M3 Stage 1 acquisition 验证；R03/R05/R29 |
| [cdl_parser.py](../../legacy_mvp/io_adapters/cdl_parser.py) | tokenizer/简单案例可参考；float 值、简化 M 行、只比较同名器件参数不满足 dialect/expression/include 闭包与 all-delta completeness，不能整段当作合格 v2 importer | M0 方言样本，M1/M2/M3 R04/R14 |
| [gds_io.py](../../legacy_mvp/io_adapters/gds_io.py) | IO harness 可参考；按参数拼 INV 名、polygon→bbox+round 路径缺 hierarchy/element/property/exact DBU 保真。须由 capability 逐 record 检查，不能默认 bbox-safe | M1/M2 R02/R03/R23 |
| [config_loader.py](../../legacy_mvp/tech/config_loader.py)、[drc_rules.yaml](../../legacy_mvp/tech/drc_rules.yaml)、[calibre_layer_map.yaml](../../legacy_mvp/tech/calibre_layer_map.yaml) | safe load、路径定位和规则索引思路可取用；默认路径/cache/旧 mode 要替换。规则自称 ASAP7-style、`dummy_7nm_finfet`；layer map 有 VERIFY，不能称真实 PDK/extraction fact | M0/M1 R08/R09/R16，U01/U03 |
| [dummy fixtures](../../legacy_mvp/dummy/fixtures/)、[gen_buffer_layout.py](../../legacy_mvp/dummy/gen_buffer_layout.py) | raw `iXref.temp`、`nXref.temp`、`net_names.txt`、device/net shape txt 和配套四类 YAML 已存在，但来源是 generator、header 明示 dummy；无可证明真实工具来源的完整 bundle/header closure。INV_N5_P7→INV_N4_P6、MN0/MP0 双 shrink 可作场景种子 | M0 只辨来源；M1/M3 在 `tests/fixtures`/`tests/support` 重建合规输入，不 import legacy；R29 |
| [test_dummy_roundtrip.py](../../legacy_mvp/tests/integration/test_dummy_roundtrip.py) | harness 组织可参考；convenience JSON 主输入、恰好两次 FIN remove 等旧断言必须废弃，现成 target GDS/JSON 不是唯一正确性 oracle | R15/R25/R27；不以 legacy parity 保留错误语义 |

禁止复用 legacy resize/decoder 的 FIN 编辑、pre-commit mutation、多 owner、output replay 和 stdout-only/placeholder 成功判断；理由已经由架构 §6.7、§11.14、§13 吸收。本次只抽样定位上述材料，不再次做全面 correctness audit。任何取用均迁入 v2 职责并有适用的 parity/纠错回归；v2 runtime/production tests 不依赖归档。

## 3. 方案与决定（PM）

- [roadmap](../roadmap.md) 采用 M0→M1→M2→M3→M4：准入资料→no_change 文件闭环→首个实际 shrink→多器件/多 delta 覆盖→首版复现验收。先做可观察小闭环；不先铺完所有骨架再集成。
- 沿用首版单指/一对一/无归并及 shrink-only 最低能力；whole-intent 多 delta 与必要 repair 不缩减。Process-local publication、禁用 partial、Stage 6 signoff/SKILL 延期均有架构依据，不代表原子性、Stage 1 evidence/acquisition 或 mandatory rules 可延期。
- 真实 tech/model/query profile 仍待查明；synthetic 工程工作与真实准入分开。body 冻结、flat rectangle/dialect subset 等只有具体证据/拒绝边界成立才可采用，不默认填补关键语义。
- 未新增需要用户立即决定的产品范围。W002 先形成实际资料缺口和最小输入/输出分叉，再按协作规则上报新的使用预期。未执行产品实现、架构正文迁移或远期全部任务细化。
- 内部专项检查用于 PM 查漏，不写成另一独立会话 review 已通过。覆盖专项指出初稿 R05 未显式分配 Stage 1 calibre/dummy_fixture 两类 acquisition、D01 runner 延期可能被误读为包括 Stage 1；PM 已在 R05/M3/U01 明确交付/阻塞门并将 D01 限定于 Stage 6。盘点专项直接复核 W001/W002，无实质问题；快照/最终检查不在其专项结论内。后续 reviewer 结论只由 reviewer 填写第 5 节。

## 4. 文档交付与验证（PM）

本轮新增 `docs/roadmap.md`、本任务及 `docs/tasks/W002-first-input-admission.md`；修改 `docs/current-work.md`、`docs/README.md`、根 `README.md`，并将 `docs/collaboration/rules.md` 的路线图占位替换为实际链接（仅导航，不改协作行为）。无移除文件，起始无已有未提交变更。

| 检查 | 命令 / 方法与环境 | 结果与限制 |
| --- | --- | --- |
| 基线/范围 | `git status --short`、`git branch --show-current`、`git rev-parse HEAD`、`git diff --stat`、`git diff --cached --stat` | 初始 main@6eccdff 干净；最终须仅上述 7 个文档、暂存区为空、HEAD 不变 |
| 全局覆盖 | PM 完整架构路由与正文检查、只读专项 `/root/coverage_audit` 对照 §1–13；R/D/U 和 §13 落点表逐项核验 | 规划覆盖检查；不等于已有产品测试/独立会话 review 通过 |
| 实现/环境 | 指定 Python 的 AST、`importlib.util.find_spec`、`--version`、`-m pip check`；按需读 legacy 源文件，未执行其 runtime | 结果见第 2 节；仅环境可用性/源码证据，未跑产品回归或 EDA |
| 文档一致性 | 指定 Python 检查七文件相对链接/架构锚点、fence 闭合、覆盖编号；`git diff --check` 与新增文件 whitespace 检查 | 完成后的计数和结果见下方核验记录；不把文档 lint 当作产品正确性 |
| 未提交身份 | 完整七文件副本、SHA-256 清单、包含 untracked 的 full.patch、baseline/source metadata 保存到下述 snapshot | 本机短期交接；不依赖只列文件名或 HEAD 来声称同一未提交内容 |

核验记录：2026-09-08，指定 Python 检查七文件的 **131 个本地链接、63 个锚点目标（其中 58 个架构引用定义）**、代码块闭合、空白及 R01–R29 编号，均通过；`git diff --check` 通过，HEAD 未变、暂存区为空，仅上述七文件改动。完整七文件副本 hash 一致；从 Git baseline + 含 untracked 的 full.patch 在临时目录重建后，七文件 SHA-256 全部一致。方法脚本为快照目录的 `verify_and_snapshot.py`，机器结果为 `checks.json`；本段结果不依赖产品测试。未运行产品回归、构建或 EDA。

### 待审快照与恢复

- 本机交接目录：`/tmp/layauto-w001-plan.x6T5rw`。最终七文件完整副本在 `snapshot/`，内容身份见 `SHA256SUMS`，完整变更在 `full.patch`，输入基线/范围/检查输出见 `metadata.json`、`checks.json`。所有 staged/unstaged/untracked 相关文件均纳入，未提交、不集成。
- 此目录仅为本机短期保全；详细规划/盘点/决定与结果归本任务及 roadmap。Reviewer 先比较 checkout 的七文件与副本 hash，再检查实际 diff 和新增文件。记录自身最终 hash 不嵌入本文，以外部清单核对完整快照。
- 目录丢失或内容有变则不能沿用“同一已检查快照”；先以当前 diff 重建身份并重查受影响项。同一 checkout 的另一会话可直接恢复。跨主机前按用户授权保存可访问版本/完整补丁，不能假设 cloud 拥有这里的未提交文件。

## 5. Review 结论（reviewer）

### 被审身份与直接核对

- Reviewer：2026-09-09 本次独立 Codex review 会话，主审 `/root`；只读专项 `/root/coverage_review`（首版覆盖/延期）、`/root/admission_review`（输入依赖/W002）、`/root/transaction_review`（首次闭环/事务）。主审核对快照、直接复核关键原条款并汇总；未沿用前一 PM 会话的内部检查作为本次 review 结论。
- Checkout：`/Users/luciano/Library/Mobile Documents/com~apple~CloudDocs/Work/个人项目/Layauto`；branch `main`，base/HEAD 均为 `6eccdff99a4da64e46921d16a4c339198813bc78`。恢复时暂存区为空，已有 4 个 tracked 修改与 3 个 untracked 新文件，无移除；均为前一交付，本轮保留。
- 被审范围：根 `README.md`、`docs/README.md`、`docs/current-work.md`、`docs/collaboration/rules.md` 的导航 diff，以及完整 `docs/roadmap.md`、W001、W002。写入 reviewer 段前，七文件与 `/tmp/layauto-w001-plan.x6T5rw/snapshot/`、`SHA256SUMS`、`metadata.json` 逐项一致；metadata 中六份规范/配置输入 hash 也一致。
- 清单身份：`SHA256SUMS` 的 SHA-256 为 `4126a880b64e5c0bdde6ee5fa57f064302a1b1a7e6fafcda355bbc6957fd4915`；完整 `full.patch` 的 SHA-256 为 `176cc08ac39114c2d1b7748680f9b1c7b24ff871b4549e64b86af04cd32fc226`。主审从上述 Git base 的原文件加该补丁在独立临时目录重建，七文件 hash 全部一致，覆盖 untracked 内容。
- 规范身份：`docs/architecture.md` 的 SHA-256 为 `0a3ca52fed12af500d973deb3bddebac9a8f7f8f697769dc86827a59c07196c9`，未修改。按 README → 协作规则 → W001/roadmap/W002 恢复，检查目标路径全部祖先，仅根 AGENTS 适用。主审与只读专项对照现行架构 §1–13、接口两侧合同及 §13 覆盖表。
- 核对方法：`git status --short --branch`、`git rev-parse HEAD`、tracked/cached diff、`git ls-files --others --exclude-standard`；先读本地环境说明，使用 `$HOME/.virtualenvs/layauto/bin/python -B`（3.11.5）独立计算 SHA-256、检查本地链接/锚点/空白/fence/覆盖编号及 AST，临时目录运行 `git apply --check` / `git apply` 重建。原七文件 **131 个本地链接、63 个锚点、R01–R29** 检查通过，`git diff --check` 通过；58 个 v2 Python 文件去掉模块 docstring 后仍无其它 AST 节点。未执行会覆盖原快照的 PM 快照生成脚本。

### Findings

**0 项实质 findings。** 在上述快照与本次规划审查范围内，未发现需修改的首版遗漏、无依据延期、合同冲突或 W002 调查不可执行问题。具体核验落点如下；这是规划覆盖结论，不是产品验收。

| 核验点 | 本快照结论与依据 |
| --- | --- |
| 首版覆盖 | [roadmap](../roadmap.md) 第 9–12、56–84、90–107 行保留 single-finger/one-to-one/no-reduction、shrink 最低能力、全 delta 准入与各事实/状态/产物 owner；§13 的 6 项 backlog、10 项 audit 条目均有 R 编号与验收归属。对照架构 §1.4、§3–5、§11、§13，未把单指解释为单器件/单 delta，也未把 legacy parity 当作 v2 正确性。 |
| 延期依据 | roadmap 第 115–122 行的 D01–D08 有架构 §1.4、§2.6–2.7、§3.1–3.2/3.6、§6.3、§7.1/7.4–7.5、§8.7、§10.3–10.6、§12.2 依据。Process-local 仍保留原子可见/CAS/幂等；禁用 partial 不取消 whole-intent；body 冻结仍需 baseline LVS 与 body/boundary invariant 证明；通用 routing/signoff 延期不豁免必要 repair 或 touched mandatory rules。 |
| 真实 profile 与 Stage 1 | roadmap 第 30、34、36–37、60、115、132 行及 [W002](W002-first-input-admission.md) 第 29–34 行区分 M0 工程出口与真实准入：M2 依赖真实 tech/model/query evidence；M3 另需所选真实 acquisition adapter 的运行与 captured 方言证据。外部 captures 不自动证明 live adapter 已执行，D01 仅延期 Stage 6。符合架构 §1.4、§2.2、§12.6–12.8；资料不足保持阻塞，未被改写为 dummy 成功。 |
| M1 首次无变更闭环 | roadmap 第 35、44–47、65、73、75–81 行覆盖原始输入/parser、baseline-only 初始化及 layer lifecycle、immutable state、semantic/extraction-aware no_change、空 ECO chain 与 closure head CAS、只读 export/validation/report/terminal result。R22 区分 pre-context failure、RunRecord freeze 唯一例外及 Stage 6 failure；符合架构 §2.1–2.3、§2.6–2.7、§7.1、§11.13，未将 baseline publication 当作 ECO commit。 |
| M2 首次修改与多 delta 原子性 | roadmap 第 36–37、69–79 行要求首个 shrink 即有 fully-ground repair、old∪new mandatory scope、extractor/未改轴及其它器件/frame/body/halo 不变量、finalization 后重检与 RunRecord/state 同次发布。M3 扩大跨器件组合覆盖，明确 supported+unsupported 全拒绝、后一 delta 检查/finalization 失败整组无 ECO commit、多 delta 单 envelope；没有允许 M2 先逐 delta 发布。符合架构 §6–9，Stage 6 失败仍保持已发布 state 与 frozen RunRecord。 |
| W002 可执行性 | W002 第 18–23、29–36、48 行给出仓库输入路由、缺证/不匹配矩阵、物理依赖与 typed 后果、共享 owner/失败 variant 方案及 M1 近期包草案要求。专项实查 legacy 源/目标 CDL、GDS、dummy raw+YAML 路径存在，dummy/VERIFY 标志属实；仅可作为调查入口。缺真实资料时可交工程部分及具体索取清单，真实准入出口继续未满足；启动仍以 W001 接收及后续授权为条件。 |

### 限制与本轮写入边界

- 本次只核验规划合同、覆盖归属、同 checkout 恢复与文档身份；未证明真实 profile/operator 可用或可实现、真实工具/PDK/license 可获得，也未给 M2/M3 排期保证。W002 尚未执行，共享 schema、具体 fixture/operator/rule proof 与实现包仍需该任务交付和独立方案 review。
- 未运行产品/legacy 测试、parser/GDS readback、fixture 再生成、构建/安装、EDA/query/signoff 或跨主机复现。Legacy 仅定向核对输入来源与路径，未全面重审其 correctness；W001 的 pip/依赖/wheel 环境盘点没有在本次重跑。链接、AST 与快照重建通过不能替代这些验证。
- 本轮仅填写 W001 第 5 节；未修改被审方案、架构、任务要求/阶段、PM 验收段或其它六个交付文件，未实现、commit、push 或 merge。原七文件快照保留不变；被审 W001 原稿 SHA-256 为 `16b0bb39c849b0888f2406bc2df83bb34f92074dc86485e8718803befe704933`，加入本 reviewer 段后其完整文件 hash 必然不同。恢复时应对照原副本确认 W001 差异仅在本段，其余六文件仍按原清单核对；不能把新增 reviewer 文字误称原快照内容。
- 临时快照只支持本机短期交接；本次恢复成功不等于已演练执行→修复→PM 验收完整周期。规划内容后续变化须重新绑定身份并重查受影响结论；本 review 不推进 PM 阶段、不自动启动 W002，也不构成产品里程碑已验收。

## 6. PM 验收与交接（PM）

### 2026-09-09 接收结论

**W001 已验收，可继续 W002 的只读资料调查与方案准备；本轮未启动 W002。** 验收对象是首版规划文档，全部产品里程碑仍未实现或验收。无未处理 finding，无新的产品范围/合同/使用预期待决项；真实资料与工具可用性继续由 W002 查明。

- PM 直接读取第 5 节独立 reviewer 记录、原快照/metadata、实际 diff 与 roadmap/W002，重点回到架构 §1.4、§2.6–2.7、§6.5–6.6、§12.6–12.8 核对首版范围、whole-intent/失败语义、必要 repair、真实 profile 和 Stage 1 acquisition 依赖。第 5 节为 0 项实质 findings，无需修复/再次 review；本轮不把内部专项替代已完成的独立会话 review。
- 版本核对：`main@6eccdff99a4da64e46921d16a4c339198813bc78`，暂存区空，仍仅原 4 tracked + 3 untracked 文档。原快照七文件、清单/补丁和六份规范配置输入的 SHA-256 均与 reviewer 记录一致；PM 接收前其它六文档完全未变，W001 对原稿的差异仅在第 5 节。只读专项 `/root/inventory` 独立复核同一身份与差异，结果一致。
- 接收时 W001（已含 reviewer 记录）SHA-256：`9e5c6d4c41a3b4780474ad0fb4649e67b541bed1891ee4c26fabdc8a0e2ff382`；reviewer 第 5 节正文 SHA-256：`ee119540878c68b663bc27248da5a186f040c8300007732e012d5f7a5aa4d6dc`。本轮完整保留该段，不代写或改动 reviewer 结论。
- 要求核对：R01–R29、§13 落点、D01–D08 及 U01–U05 的实质规划保持已审内容；W002 有仓库可启动的输入路由、调查输出、拒绝/缺证后果和验收。真实 PDK/model/query 资料不足阻止真实准入，不阻止形成证据清单、具体索取材料和工程接口方案；W002 不能以 dummy 成功宣称真实准入通过。
- 状态更新仅涉及本任务 PM 段/阶段、W002 的就绪状态、current-work、roadmap 和 docs 导航的审阅状态；不改变已审能力、依赖、验收或协作行为。使用指定 Python 完成 133 个本地链接、63 个锚点、空白与范围检查，`git diff --check` 通过；reviewer 段 hash 保持，roadmap 实质规划段无改动。新七文件快照从 Git baseline + 完整补丁重建后逐项 SHA-256 一致，结果在新目录 `checks.json`。没有重跑产品/legacy/EDA/构建/环境依赖检查。

### 验收版本、集成与恢复

- **验收状态：已验收；当前已提交本地 main，未 push，见下方集成记录。** 第 5 节及上述 PM 接收检查绑定提交前身份；当时 HEAD 未变、未提交。随后用户明确授权 commit，取代现有已验收文档的提交限制；不改变产品实现/架构拆分边界。原规划、review 与 PM 新增文字的版本保持可区分。
- 原 `/tmp/layauto-w001-plan.x6T5rw` 保留不变，不运行会覆盖它的旧快照脚本。PM 接收证据另存本机 `/var/folders/7p/py58pz81089d2h4vn7nrf3h00000gn/T/layauto-w001-accept-t_87w51m`：`before_pm/` 是含独立 review 的七文件，`receipt.json` 记录接收身份；`snapshot/`、`SHA256SUMS`、`full.patch`、`metadata.json`、`checks.json` 是最终含 PM 状态的完整七文件交接。原稿、review 与 PM 状态变化可分别对照。
- 这些临时目录保留为历史审阅证据；**当前恢复改用下方 Git 提交和 current-work**，不再要求下一执行会话依赖临时目录。跨主机须先取得相同提交；本次未 push。内容变化时核对新身份并重查受影响结论。
- **下一角色：执行 W002（仅只读调查与文档准备）。** PM 已确认规划前置满足、任务可执行；本轮按用户要求止于 review 接收与能否继续的判断，不预先执行 W002 或 M1 实现。W002 的实际 shared schema/fixture/operator/rule proof 与 M1 实现包仍需产出并独立 review，不能用 W001 验收替代。

### 提交授权与 Git 恢复（2026-09-09）

- 用户在接收之后明确要求现有内容 commit。提交前逐项核对当前七文件与 PM 接收快照完全一致，reviewer 第 5 节保持原文，规范/配置输入 hash 不变，无额外 staged/untracked 路径；`git diff --cached --check` 通过。
- **已验收文档原稿提交：`8482b68f6b2b0958f1ac501b15cd393a66782c4a`，本地 main。** 包含七个规划/导航文件及独立 review/PM 接收记录；与提交前已验收快照逐文件相同，产品代码和架构正文没有改动。未 push、未开始 W002。
- 本节、roadmap/current-work 与 W002 的 Git 恢复/授权说明作为后续状态记录提交；仅更新集成身份，不改已审实质规划或 reviewer 结论。 状态记录的文档检查覆盖 131 个本地链接、63 个锚点与 R01–R29，均通过；原稿提交与已验收快照逐文件 SHA-256 一致，reviewer 段、roadmap 实质规划及规范输入保持不变，`git diff --check` 通过。当前恢复版本可用 `git log -1 --format=%H -- docs/current-work.md` 定位；核对该提交包含上述原稿提交后读取 W002。
- 建议 W002 由另一执行会话负责定向调查和方案文档，本 PM 会话保留全局覆盖、问题上报、独立方案 review 组织和验收。默认串行写入同一 checkout；需要并行或换主机时按既有规则准备 checkout/worktree 与可访问提交。尚未创建或启动另一执行会话，不把建议当作已派发。
- W002 的要求已随原稿提交保存；新增执行产物仍遵守该任务“不 commit”的范围。完成后先交 PM 核验与必要独立方案 review，不由执行者改写 PM/Reviewer 结论或自行进入 M1 产品实现。

后续启动 prompt：

> 按项目规范，执行 W002 的资料调查与方案准备。先核对当前 checkout 包含 `8482b68f6b2b0958f1ac501b15cd393a66782c4a` 及最新 current-work 的集成记录，从已定位资料形成准入矩阵、真实证据缺项、共享合同/失败流和 M1 近期实现包草案。未知项保留证据与上报出口；不启动产品实现，不安装部署 EDA，不全面重审 legacy，不拆架构、不 commit。结果写入 W002 执行段，交 PM 接收。
