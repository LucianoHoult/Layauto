# W003 — M1 最小样本、文件合同与独立判据

先做一套人能核对的输入和答案，再让程序证明自己读对、算对、导出对。例如两器件的有效 fin 数为 5/7，目标仍为 5/7；样本同时说明连接关系、适用规则与失败条件，不能只用数字相等判成功。

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| ID / 目标 | W003；提供可独立审查的 M1 最小样本、经过的文件/共享记录合同、正确答案与反例，使后续 no_change 文件闭环实现有明确输入和验收依据 |
| 里程碑 / 依赖 | M0 工程准备→M1；[W002](W002-first-input-admission.md) 已验收，特别落实 E5/E7 与 reviewer R4。真实材料不作为本地 synthetic 样本准备的前置 |
| 授权依据 / 阶段 | **待验收，修订由[W004](W004-fixture-revision.md)承接。** 2026-10-31用户接受单独W004并要求执行交接；原版技术review及MR-076已接收，样本修订尚未实施。P4–P7保留历史发布/接收/方案准备；P8记录转交，不开始runtime/EDA/生产上传 |
| 范围 | 执行交付独立样本说明、schema/字段/最小样张、可再生 synthetic 输入、手算/独立 reader 判据及失败实例。允许写本任务执行段、docs/tasks/W003/ 附件、tests/fixtures/ 的专用样本与 tests/support/ 的专用生成/核对辅助；辅助仅服务样本准备，不提前实现产品 parser/extractor |
| 非目标 | 不重做全局/legacy 审计，不改架构正文，不实现 layauto_v2/ 产品 runtime 或 Stage 1–6 模块，不部署 VM/EDA、不选定生产 PDK、不将 public/dummy 运行当真实准入；不上传生产输入/PDK/许可证 |
| 架构依据 | [architecture.md](../architecture.md)（与 `6eccdff` 相同）§1.4、§2.1–2.7、§3–5、§7.1、§8.1、§10、§11.14–11.15、§12.5–12.8；格式的上下游 owner 以原文为准 |
| 负责人 / 未决 | 原版执行/reviewer已停止写入；总PM已接收[人工核验MR-076](W003/manual-verification.md#mr-076)。后续执行/新版review统一记入W004；本任务保留原版证据与最终闭合记录。生产回传权限、平台与真实验收安排仍由PM协调 |

### 交互分工与非阻塞依赖

- **立即可做：**读取 W002 已审结论、定向使用 legacy 种子，定义并制作明确 synthetic dialect 下的小样本、格式样张、独立答案和反例。没有生产版本/反馈权限时继续这部分，不假装生产格式已确认。
- **PM 与用户确认：**生产环境可外传什么、谁在内网检查真实证据、PM 可依据何种回执验收，以及是否投入 VM/EDA。这些只控制对应真实验证工作，不阻塞本地样本准备。
- **执行者与用户的技术交互：**遇到具体语法歧义时，先给可脱敏的最小模板/选项（如字段顺序、转义、结束标记），可以直接请用户澄清，并写回任务事实。无法确认则保留缺项；不自行扩大外传权限或把 synthetic 例称 tool-captured。
- **回 PM 的情形：**新关键输入解释/输出格式/使用预期、生产准入或验收方式变化，附样本、影响和建议。普通样本实现/核对由执行者自主处理；交付后再做独立 review，不要求用户先回答全部生产问题。

### 文件范围：覆盖 M1 的全部边界，逐项声明支持子集

“全部”指这个切片会消费/产生的文件和跨模块记录均有合同，不要求一次实现 GDS/CDL 的全部语法、全部生产工艺或远期工具。已有标准只声明所选子集与拒绝条件，不重新发明标准。

| 类别 | 本任务须给出的具体材料 | 正确性/限制 |
| --- | --- | --- |
| Source geometry / semantic / target | 小 cell GDS、source CDL、同语义 target CDL；精确 tick/REAL8 与 nominal unit 对照、cell/pin/model/terminal/参数定义、closure 清单 | 沿 W002 的 flat rectangle/literal CDL 子集；不支持的 hierarchy/property/表达式等逐项声明拒绝。保真按语义，不默认 byte 相同 |
| Query 输入 | 四类 capability 的 raw 样例（instance/net xref、device/net region）；QueryBundleHeader 与 normalized YAML 期望；选定 synthetic dialect 的字段、坐标顺序、单位、count/terminator/可选段/错误例 | raw 为正式 parser 的输入；header 绑定 input/closure/版本。Normalized 是可重解析结果或期望，不能替代 raw；旧示例命令/文件名不是通用 Calibre 格式 |
| Tech / site / test profile | layer 与 derived registry、Geometry/CDL/FinCount/DeviceExtraction/body、单位合同、toy rules/operator/lifecycle、machine-readable limitation；最小 site_config.yaml、ExportPolicy/validation policy，涵盖 inputs/outputs、相对路径基准、mode/tech refs、产物 requiredness/命名与输出精度/不可表示拒绝条件 | Toy 物理定义可手算；明确 single-finger、一对一、无归并。不得把生产 token、规则数值或 model 默认值推出来；site 不修改物理事实。Policy 不允许放宽 mandatory checks |
| 共享中间记录 | Evidence/ToolRun/Parse、ProposedInitialState/PreparedBaseline、immutable snapshot/context、RunAttempt/RunRecord、StageFailure 的版本化中立合同与最小实例 | 标 producer/consumer、id/ref、exact encoding、必需/可选字段和非法组合；不是预制最终 snapshot 绕过实际输入链；不先展开全部 helper |
| 正常产物 | GDS/CDL/JSON 的独立期望；ArtifactManifest、ValidationResult、ReportingResult、terminal PipelineResult、人/机器报告最小样张 | baseline/no_change 空 ECO chain；actual-byte hash 与 semantic equality 分开；报告均标“预期样张”，无真实 run，不伪造成功记录 |
| 失败产物 | pre-context、sealed no-publication、freeze、export/check/report/terminal failure 的代表记录和有/无 artifact 断言 | 按阶段分 variant；缺资料、违例、执行 error 不汇总通过；正常 synthetic 可建议 requires_review，required failure 仍 reject |
| 样本与答案自身 | 逐形状坐标表/图、FIN∩active∩channel 计数表、S/D/body/terminal/连通图、规则适用集合与每例结果、来源/版本/生成方式/限制 | 手写推导与独立检查路径；generator、runtime parser/extractor 或 writer 不能自行提供唯一答案。可再生一致性另验证 |

SKILL/Virtuoso、Stage 6 signoff 报告仅保留已批准扩展边界；本包不实现或冻结全部远期格式。Stage 1 live query 的 runtime/dialect 义务仍归真实输入路径，不因 signoff 延期被删除。

### Legacy 定向复用入口

沿用 W002 E1 的证据和限制；下表补充到具体函数，后续迁入 `tests/support/`、`tests/fixtures/` 或正确 v2 owner，保持 archive 原件。本轮只读源码，没有运行 generator 或改旧 fixture。

| 材料 | 使用方式 |
| --- | --- |
| [旧 dummy fixtures](../../legacy_mvp/dummy/fixtures/) 的 CDL、GDS、raw xref/device/net 与 YAML | 直接作离线格式观察/拒绝例种子；作为新正例前必须重新绑定 header、单位/profile/closure 与独立几何判据，不能原封不动宣称 v2 准入通过 |
| [gen_buffer_layout.py](../../legacy_mvp/dummy/gen_buffer_layout.py) 的 `generate_calibre_ixref/nxref/net_names/device_info/net_shapes` | 参考文本 record、count/terminator 与文件组织，改为从已审 synthetic spec 生成；替换隐式精度/模型/swap/未 trim bbox 假设，版本和 provenance 如实标 synthetic |
| 同文件 `generate_cdl`、GDS 写入与 geometry helper | 可取纯格式/矩形序列化思路；cell 身份、层 key、exact units、未知 record 处理重新按合同实现。不能保留按 fin 参数重命名 top、忽略未知层或浮点取整 |
| 同文件 `generate_all_fixtures`、target GDS/JSON | 不整体复用：它 import legacy IO，输出 convenience JSON，按参数重新生成 FIN/frame/rails；不能给固定边界 ECO 提供正确答案 |
| [query 单测](../../legacy_mvp/tests/unit/test_calibre_query.py)、[roundtrip harness](../../legacy_mvp/tests/integration/test_dummy_roundtrip.py) | 参考解析失败、超时/mock 与组合测试组织；替换浮点/旧状态流和 FIN remove/旧 golden 断言。Mock 不是 live 工具证明 |

### 隔离生产环境：已知事实与建议分开

用户说明：生产服务器隔离，包含实际 Calibre 版本与保密 PDK；仅能向内上传代码，向外只能描述数值脱敏后的文件格式。事实归属与工具条件见 [remote-development](../environment/remote-development.md#隔离生产服务器用户确认的边界)；未假定可以导出 raw、PDK、日志、结果、哈希或通过/失败摘要。

**推荐路线，尚未完成真实验收协议确认：**本地 synthetic 样本/合同开发 → 将版本固定的代码与检查入口单向传入 → 用户在目标机运行，完整真实输入、raw/header/closure、tool/deck/profile 版本和审计结果留在内网。外侧材料注明本地独立验证或目标机用户转述的范围，不能把格式反馈当 matched evidence/live 执行证明。

向内是否能携带测试样本、依赖 wheel/离线包，以及目标机 Python/OS/CPU/tool build 条件也需确认；“允许上传代码”不自动等于能从公网安装依赖。当前没有设计或部署真实 runner。

可反馈字段的候选仅为公共代码版本、公共 testcase id、pass/fail/错误类别；是否能反馈由用户按其环境规定确认，默认未允许。私有 input hash、路径、数量、工具/工艺标识不自动视为可外传。如果确实只能反馈格式，本地仍可完成 M1，但 PM 对真实 M0/M2/M3 保留“未核验”，后续由谁在内网 review/验收、能依赖何种回执，须给具体协议再由用户决定，不静默降低原验收门。

数值/标识符替换后的材料在本地标“按描述重建/合成”。保留允许披露的语法特征：字段顺序、分隔/引用/转义、记录种类、可选段、结束标记及 numeric lexeme 形态；单位含义不明就标未知。任意替换数值会破坏几何/连通/规则关系，因此格式例与几何正例分别定义；完整合成正例的 GDS/CDL/raw/header/规则和答案必须重新构造成同源自洽，不能沿用原生产 hash/status。

| 可选路径 | 建议与证据边界 |
| --- | --- |
| 本地 synthetic + 目标机验证 | 首选。直接推进 M1，真实工具/PDK 行为留目标机检验；需补目标机执行和回执协议 |
| 公开 PDK 辅助 | ASAP7 是可参考的 FinFET 教研材料，但不是目标工艺或制造验证；公开模型/deck/单位必须独立核验，不自动满足本项目候选 profile。可择需参考，不设为 M1 前置 |
| 本地 VM + 同版本 EDA + 公开 PDK | 暂不作为前置。只有实际 tool build 支持的 OS/CPU、安装介质/授权、许可证可达、资源与 deck 组合可运行时，才能帮助迭代 runner/parser；仍不验证保密 PDK |

2026-09-09 一手资料：ASU 将 [ASAP7](https://asap.asu.edu/) 定位为 predictive FinFET 教研 PDK、不可制造；其 Calibre decks 加密且另行获取。[官方发布仓库使用说明](https://github.com/The-OpenROAD-Project/asap7_pdk_r1p7/blob/main/Calibre_Usage_Instructions.txt) 记录特定旧 tool build 的测试与 xACT 不兼容例，只说明版本组合需要验证，不能预测用户版本。[SKY130 known issues](https://skywater-pdk.readthedocs.io/en/main/known_issues.html#mentor-calibre-support) 也披露公开材料缺 Calibre 验证文件，故“公开 PDK”不等于可立即运行 Calibre。[Siemens 虚拟云说明](https://www.siemens.com/en-us/products/eda-cloud-solutions/calibre-cloud/) 支持虚拟环境及许可证服务器路径，但不证明任意桌面 VM/CPU/旧版本均受支持。本轮未下载 PDK、安装工具或访问生产服务器。

### 验收与分派前核对

| 验收项 | 预期可观察结果 | 方法与限制 |
| --- | --- | --- |
| 覆盖所有 M1 文件边界 | 上表每项有最小样例、版本/来源、双方 owner、单位/id/ref、支持/拒绝子集 | 文件清单→合同→样例→正常/失败断言逐项映射；内部记录不被误当用户输入 |
| 正例与独立答案 | 具体 5/7 坐标、端子图、规则适用表相互一致 | 独立手算/reader 审查；不以 future runtime 的输出作唯一答案 |
| 反例与不变量 | count 正确但规则错、单位错、raw 缺项/漂移、mapping不合规、不可表示/越界输入有明确结果 | 检查失败记录与 publication 后果；本阶段样张不冒充运行结果 |
| 复用与生产分界 | 每项 legacy 取用有保留/替换理由；synthetic/按描述重建/真实 evidence 明示 | 无 v2 runtime 或 production test import legacy；不宣称私有工艺或 live 已通过 |
| 后续可执行 | 样本经独立 review 后，M1 有明确输入、oracle、首交失败测试及 build/type/环境要求 | 后续实现另行派发；真实门不被样本审查消除 |

## 方案与决定（执行准备，PM 接收）

以下是原版执行决定，保留其历史身份。修订轮以[W004](W004-fixture-revision.md)及[人工清单MR-076](W003/manual-verification.md#mr-076)所引用的用户决定为执行入口；尤其MR-034已替代旧raw方言方向，MR-046要求修订本地BTAP假设，不能继续照旧生成后声称修订完成。

2026-09-09 按用户本轮明确指令执行。选择本地 `synthetic_static_fin_no_change_v1`，只支持已声明 flat BOUNDARY/literal CDL/toy query 子集；具体字段、独立答案和反例见 [交付入口](W003/README.md)。这是审查用 fixture 合同，不发布产品 wire API，不改变架构或真实准入门。

- `INV_M1_SYNTH` 保持同一 top、source/target 5/7；完整固定 pitch FIN 背景为 18 根，其中 12 根 qualified、6 根不参与器件 crossing；不复用旧按目标参数重建 FIN/frame 的 target。
- 采用完整 toy body/CONTACT/VIA0/GCONTACT/BTAP/CUT 定义，不借真实 frozen-body 豁免；source/target 全量语义、geometry、terminal graph、10 条 mandatory toy rules 一起判定。正常工程样张 requires_review，required violation/error/export/report failure reject；生产模型/规则不作推断。
- `UnitScaleContract` 固定 nearest/ties-even 56-bit REAL8、各字段 nominal 唯一候选的 half-ULP 判据。独立 KLayout writer 的原 1 nm 编码多 1 mantissa ULP，超过本包界；只将 expected GDS 的 UNITS 规范化，保留原 bytes/hash/range 和 exact 差异，XY 不变。独立性为几何 writer/reader + 手写 oracle；不声称 expected 单位 writer 独立，不新增容差路径。
- 19 个语义/格式反例提供自动重绑定 overlay，含必要 raw/cache 更改；另 3 个故意保留 binding/header/cache 错误。避免所有负例先被同一个 hash failure 遮住；具体产品 StageFailure/终态仍是未来断言。
- 未遇必须向用户索取生产语法才能完成本地 dialect 的阻塞。生产反馈权限、平台版本、离线条件和真实验收回执仍保留缺项，归 PM 协调。执行期间 PM 在 current-work 增补人工核验安排，已读取并保留，不并发改写该入口。

## 执行结果（执行）

### E0. 交付范围与启动核对

**本地样本/合同准备已完成，完整证据交 PM，随后安排独立 review；未作 PM 验收声明。** 本包不是 M1 产品闭环通过，不包含 layauto_v2 runtime/parser、EDA 部署或真实 signoff。未 commit/push。

启动与交付基线均为 `main@b1f0301cf76b2e1808cb293cfdb4e1bfededde73`。已读根 AGENTS/README、协作规则、current-work、W003 全文、W002 E1/E5–E7/R4/PM 接收、local-setup，及 architecture §1.4、§2.1–2.7、§3–5、§7.1、§8.1、§10、§11 对应 owner/11.14–11.15、§12.1–12.8。仓库仅根 AGENTS 适用。架构 SHA-256 仍为 `0a3ca52fed12af500d973deb3bddebac9a8f7f8f697769dc86827a59c07196c9`。

启动时 staged 为空；已有 `docs/README.md`、`docs/current-work.md`、`docs/environment/remote-development.md` 修改及 untracked 本任务。已逐项校验 `/private/tmp/layauto-w003-ready-pzibrdp0/SHA256SUMS`，四份 snapshot 与启动 checkout 全部逐字节一致。执行期间 current-work 由 PM 新增 W003 运行/人工核验/后续 parser 上传路线，HEAD 未变；该变更单独保留为外部 PM 工作，执行者不改其 owner 文件。

执行主 agent 负责合同样张/证据；只读 contract_audit 只提供原文义务核对，fixture_builder 在 `/private/tmp/layauto-w003-fixtures` detached worktree 独立制作 fixture/support，完成并停止写入后由主执行逐 hash 集成。两者参与准备，均不作独立 reviewer。没有并发编辑任务文件；隔离 worktree 无提交。

### E1. 产物与独立判据

| 产物 | 入口 / 本轮结果 |
| --- | --- |
| 全部文件/双方 owner/字段与非法组合 | [contracts.md](W003/contracts.md)、[schema.json](W003/examples/schema.json)；schema version `w003-example/1` 是审查样张，产品 wire 后续实现 |
| 可再生输入与具体 toy 定义 | [fixture README](../../tests/fixtures/w003_m1/README.md)、spec/oracle、source GDS/CDL、target CDL、四 raw/header/normalized、tech/site/export/validation/limitations；共 75 文件（包括 22 个负例 overlay） |
| 人工几何/连接核验 | [坐标图](W003/fixture-layout.png)、fixture README 的逐图形表、FIN crossing/端子/规则表、oracle.json；44 drawn shapes、18 FIN、5/7 qualified crossings、8 terminals、6 components、10 connector edges |
| 正常共享记录 / 输出 | [20 条记录样张](W003/examples/records.json)，fixture expected GDS/CDL/layout JSON；baseline version 0 + InitializationEvent，no_change 空 ECO chain |
| 报告与失败 | [人读报告](W003/examples/report.expected.md)、[机器报告](W003/examples/report.expected.json)、[8 类失败组合](W003/examples/failures.json)、fixture failures/cases.json；均显式 expected/example，未执行产品 run |
| 复用与下一实施包 | [handoff.md](W003/handoff.md) 映射要求/legacy保留替换理由、首交错误路径、strict typing/build/环境要求及生产缺项 |

Oracle 从手写坐标/graph/全参数语义表出发。生成器不提供唯一答案：独立 KLayout 整数 readback 与 shape multiset 对比、独立 Boolean/graph/spacing/enclosure 核对手写预期；CDL/raw 文本有独立固定样本 reader。全部 draw records 保真，source/expected GDS bytes 不同但语义相同。再生成一致性是额外的存档检查。

`expected/layout.json` 是字段/fragment 最小样张，明确不是完整 runtime snapshot；geometry/semantic/terminal graph 有本例完整期望，但 occupancy 只展示相关 region 和同 cell 多 fragment witness。后续实现须从真实输入链构建全部 components，并对完整输出与这些独立期望和投影不变量核对，不能直接加载此样张绕过 Stage 1/2，也不能只验证已列字段就声称完整 snapshot 保真。

### E2. 本轮实测

环境：指定 `$HOME/.virtualenvs/layauto/bin/python`，Python 3.11.5、KLayout 0.30.12、Matplotlib 3.11.1、PyYAML 6.0.3；所有辅助以 `-B` 运行。未安装依赖。`pip check` 返回 No broken requirements found。绘图仅可视化手写 spec，不进入 canonical rule/hash 路径，已检查图中标签与边界。

| 实际检查 | 结果 / 证据边界 |
| --- | --- |
| Source/expected GDS | 独立读取 44 records；原 XY/element/layer/top 与手写表一致，REAL8 exact rational/nominal/delta/half-ULP 分列；KLayout 原单位 bytes 可由 provenance 重建 |
| CDL / raw / closure | source、target、expected CDL 全语义相等；四 raw record 数 2/4/2/10，与 normalized/spec 同源；header/top/unit/layout/netlist/closure/hash 一致；无真实 query run |
| Toy 正确性 | N/P crossing 5/7、面积40/56 nm²；6 physical components、10 connector edges、10 net annotations+2 device joins；contact 最小 enclosure 1 nm；LI 10对最小距离平方4 nm²，M1 6对最小25 nm²；mandatory toy rule failures 为空 |
| 反例 | 22/22 局部错误见证；包含 count仍为5/7但M1 spacing不足、via enclosure、extraction mismatch、单位/格式/映射/多指/归并/输出精度越界。19例overlay bindings一致，3例故意缺陷；没有实际产品 failure/publication 测试 |
| 再生成 | 主执行新目录 `/private/tmp/layauto-w003-root-regen-v2`，75/75 files byte-clean；不把 writer相同的byte结果当独立正确性 |
| 记录样张（首次冻结版） | 20 records、8 failure variants；66 fixture refs/hash/JSON pointers 与3个实际样本artifact bytes核对；拒4种非法组合（unsealed带context、no_change带commit、ToolRun反向parse、required error被accept）。review 后修复与新增检查见 E4；仅为样张检查，不证明产品codec/deep-freeze |

可在仓库根复查（再生成目录须为新的独立路径，不覆盖现有证据）：

```bash
"$HOME/.virtualenvs/layauto/bin/python" -B tests/support/w003_generate.py --output /private/tmp/layauto-w003-recheck-new
"$HOME/.virtualenvs/layauto/bin/python" -B tests/support/w003_verify.py --fixture tests/fixtures/w003_m1 --regenerated /private/tmp/layauto-w003-recheck-new
"$HOME/.virtualenvs/layauto/bin/python" -B tests/support/w003_record_examples.py
MPLCONFIGDIR=/private/tmp/layauto-w003-mpl "$HOME/.virtualenvs/layauto/bin/python" -B tests/support/w003_plot.py --fixture tests/fixtures/w003_m1 --output /private/tmp/layauto-w003-figure.png
```

`w003_generate.py` 和 `w003_record_examples.py --write` 是本包再生成入口；默认记录校验不写文件。future runtime 不 import 这些 helpers。没有运行 v2/legacy pytest、legacy generator、runtime Stage 1–6、repository CAS/recovery、真实 Calibre/Virtuoso/PDK/model/signoff、strict typing/wheel/CI/其它解释器或目标机验证。

### E3. 版本证据与 PM 交接

完整本机交付包：`/private/tmp/layauto-w003-delivery-uzpc4aed`。保存当前相关 staged/unstaged/untracked 的完整 `snapshot/`、相对 `b1f0301` 的 binary `full.patch`、逐文件 `SHA256SUMS`/`checks.json`、`commands.json`、`verification/` 原始 stdout/stderr、fixture-builder hash清单与原接收包副本。证据 hash 在外部 manifest，不要求本段自含最终 hash。包的 patch 可在独立临时目录从基线重建全部相关改动；恢复只核对，不重跑历史快照脚本覆盖证据。

PM 先核对版本和本轮实际 diff，再使用 [handoff](W003/handoff.md) 按全部正反 fixture 组织人工正确性/使用预期核验。独立 reviewer 针对此冻结包核对文件覆盖、toy 物理解释、独立 oracle、exact units、raw绑定/负例、共享失败流与证据边界；不重新全量审 W002、不改架构或放宽验收。执行者负责 findings 修复后回交 reviewer 复核，review 原文由 reviewer 维护。

当前入口的新增人工核验要求属于 PM 后续接收工作，尚未执行用户确认；本轮执行和独立 review 都不能代替用户确认。生产反馈/平台/真实回执仍未明确，G1–G4/G5 真实门不变。本执行不代填 PM 阶段/验收，不自行开始下一 parser/runtime 任务。

### E4. 独立 review findings 的执行处理

独立 reviewer 指出两项样张自洽问题（原 finding 和复核结论归下方 reviewer 段），已在既定本地合同范围内修复：

| Finding | 执行处理与复查 |
| --- | --- |
| F1：create-attempt 摘要漏绑定 run/head/输入选择 | raw_request_descriptor 现在展示完整 pre-context request：operation、proposed run/lineage、starting head、idempotency key、原始输入/raw/config/policy 路径与实际 byte hashes；SHA-256 对完整 payload。没有提前填入 canonical TargetIntent/tech/evidence ids。增加 run/head/selected byte hash 改变但沿用旧 digest 的3个拒绝检查 |
| F2：缺 terminator 失败样张却引用正常 raw | pre-context ParseResult 改指真实 missing_terminator overlay raw 与其重绑定 header，附独立 fixture-read ToolRun；StageFailure/failure RunRecord 的 completed/localized refs 跟随同源输入。辅助核对该 raw 缺 END，且实际 byte hash 与坏例 header 一致 |

修复后样张检查通过：20正常 records、8 failure variants、79 fixture refs/hash/pointers、3 artifact byte hashes、7非法组合拒绝。fixture几何/tech/raw输入及75文件再生成结果未改变；不重跑无关产品/legacy测试。首个冻结包保持不变；修复版另建完整包交 reviewer，不用新内容覆盖原审查证据。修复是否关闭由 reviewer 独立复核，执行者不代写其结论。

## Review 结论（reviewer）

### R0. 独立范围与受审身份

2026-09-09，独立 reviewer 子 agent 执行；未参与主执行、fixture-builder 或 contract-audit 的准备。**原冻结版发现 2 项 P2 样张问题，执行者修复后已独立复核关闭；当前无未关闭实质 findings。** 本结论仅覆盖 W003 本地 synthetic 样本/合同交付，不代替用户人工正确性/使用预期确认、PM 验收或 M1 产品闭环验收。

启动及复核基线均为 `main@b1f0301cf76b2e1808cb293cfdb4e1bfededde73`，staged 为空。已读根 AGENTS/README、协作规则 review 角色、current-work、W003 要求/附件、W002 E5–E7/R4、local-setup 与相关 architecture 原文（§1.4、§2.1–2.7、§3–5、§7.1、§8.1、§10、§11 owner/依赖边界、§12.5–12.8）。修改路径仅根 AGENTS 适用；architecture SHA-256 为 `0a3ca52fed12af500d973deb3bddebac9a8f7f8f697769dc86827a59c07196c9`。

| 受审版本 | 独立身份核验 |
| --- | --- |
| 首次冻结 `/private/tmp/layauto-w003-delivery-uzpc4aed` | `full.patch` SHA-256 `c91b51e4b21c7fc01921930ab5dd6db04ccbe908acce06d60bba12745c4a5c07`；`SHA256SUMS` SHA-256 `054e19dc61d9538720ec079a7005f3352c3041f0517e1886e220054a8eb1d9b8`。130 manifest 项核对、92 snapshot 文件与当时 checkout 逐字节一致；从基线独立应用 binary patch 后全部匹配 |
| 修复版 `/private/tmp/layauto-w003-fix1-5ucqaesx` | `full.patch` SHA-256 `107c2dce6555fa175a634b28c74b229f8df50ba2e3dbb87d4cb14018426777c3`；`SHA256SUMS` SHA-256 `1af82f3ab9c731967f67fd87a865e11b7670674e1be0a2eb1818bca250f94c43`。233 manifest 项核对、92 文件与 checkout/再次独立重建全部匹配；相对原包仅本任务执行 E2/E4、record helper、records/failures 两样张变化 |

受审执行材料为 75 个 fixture 文件、4 个专用 support helpers、W003 附件及执行记录。原有 `docs/README.md`、`docs/current-work.md`、`docs/environment/remote-development.md` 为 PM 工作，纳入完整交接身份但不归本次执行产物，也未被 reviewer 修改。

### R1. Findings 原文、影响与复核

| ID / 严重性 | 原 finding 与依据（首次冻结版） | 执行处理与 reviewer 复核 |
| --- | --- | --- |
| F1 / P2 | `w003_record_examples.py:104–107,132–134` 的 create-attempt `request_digest` 只哈希 `{source: site_config.yaml, selection: synthetic_no_change}`，没有绑定 proposed run、starting head 或入口 input/config/policy byte identities。同一描述换 run/head/文件 bytes 后摘要不变，与 architecture §2.1/§2.6 的 pre-context request binding 及 create digest 包含 proposed_run_id 的明确要求不符。作为下一实施依据会给幂等冲突检查提供错误样张；不要求本轮实现产品 codec/repository。 | 执行 E4 已补完整 raw request payload。Reviewer 对修复 snapshot 独立重算 SHA-256，得到 `84e36391569347080e5c4d57dd66fd385b278b23c853d2d0e0da63b4be585fcb`；核对 run/lineage/head、13 个输入/raw/config/policy file refs 实际 hash。分别改变 run、head、lineage、selected file hash 均改变摘要。样张 helper 新增 stale 摘要拒绝检查。**已关闭。** |
| F2 / P2 | `w003_record_examples.py:208–212` 的 pre-context `RAW_TERMINATOR_MISSING` 失败 ParseResult 与 ToolRun 指向正常四份 raw 及其真实 hash；这些输入均含正确 terminator，故该失败样张与其证据不自洽。W003 要求失败记录/来源可追溯；不能用正常输入的确切 refs 示范不存在的格式错误。 | 执行 E4 改为已存在的 missing_terminator overlay、对应重绑定 header 和独立 fixture-read ToolRun。Reviewer 独立读坏 raw（SHA-256 `2eb4b99046e910c8b7d1ec5d0e1d20dc20cb766b88abfb723d1a87fc1824a9ff`），确认缺 END，header/raw hash 与 ToolRun→ParseResult→StageFailure/localized→failure RunRecord 完成记录一致。**已关闭。** |

复核没有扩大 toy 物理语义或产品范围；没有发现需要新增使用预期或修改架构的事项。F1/F2 原文保留，不能用修复版覆盖原受审身份。

### R2. 实际检查与独立判据

环境为指定 `$HOME/.virtualenvs/layauto/bin/python`，Python 3.11.5、KLayout 0.30.12、PyYAML 6.0.3、Matplotlib 3.11.1；使用 `-B`，未安装依赖，`pip check` 通过。全部 helper 在 reviewer 从补丁重建的临时目录执行；生成、绘图及额外复核材料只写独立证据目录。

| 检查 | 实际结果与边界 |
| --- | --- |
| 源/期望 GDS 与精确单位 | Source/expected 均独立读回 44 个 BOUNDARY 矩形，top、element/layer/datatype、XY 与手写表一致；bytes 不同且语义相同。Reviewer 另用 stdlib `struct`/`Fraction` 解码全部 records/REAL8，核对 nearest56 half-ULP；原 KLayout GDS 可由 UNITS provenance 复原，除该 payload 外 bytes 不变。单位 writer 的独立范围如实限于几何 serialization/readback，不声称单位 writer 独立 |
| 全部 toy 规则 | 复跑 helper 之外，reviewer 自写只依赖 stdlib 的 integer unit-square subtraction、flood traversal 和 graph 检查，不 import W003 helpers、产品或 KLayout。18 根完整 FIN、N/P qualified crossings=5/7、交面积40/56 nm²；gate 分隔 S/D、CUT 分成两岛；8 terminals、10 connector edges、6 physical components；body 最小 active enclosure 10 nm，全部20个 connector-side enclosure 最小1 nm；LI10对距离平方最小4、M1 6对最小25。T01–T10 的集合/阈值与独立手写 oracle 相符，annotation 未创建物理边；图与坐标表目视一致 |
| 文本/同源闭包 | Source/target/expected CDL 的 top/pins/model/有序端子及全部参数相等；四类 raw 数量2/4/2/10，与 normalized/spec 一致。Header、实际 source/raw/tech/policy hashes、空 CDL include/library/preprocess closure及 query closure绑定自洽；synthetic/not-run/版本和限制未冒充 Calibre captures |
| 22 个反例 | helper 确认22个局部错误见证；reviewer 另实际复制正例、应用全部 replacement/removal，得到19个绑定闭合 overlay与3个故意保留的 hash/cache/header 错误。Count仍5/7而M1 spacing=4nm、VIA enclosure不足、物理4/7与声明5/7不一致、格式/单位/映射/输出精度错误均有具体见证。这不是产品 StageFailure/terminal publication 的实际运行 |
| Source/output 单位边界 | `unit_scale_contract.output_nominal_selection` 已明确 source nominal固定1nm、输出选定 nominal及scale binding独立；输出2nm/1e-9nm tick例分别触发不可表示/32-bit越界，不因固定 source nominal先判 config冲突。未增加 geometry rounding、annotation tolerance 或额外单位容差 |
| 共享记录/正常失败流 | 修复后20正常 records、8 failure variants、79 fixture refs/hash/JSON pointers、3个实际样本 artifact byte hashes和7种非法组合检查通过。Pre-context 有最小 failure RunRecord；sealed失败无ECO；freeze为唯一可无RunRecord例外；Stage6失败保留原no_change RunRecord；required fail/error/report failure reject；terminal storage failure不伪造terminal pointer |
| 再生成/文档边界 | 初轮75/75 fixture文件 byte-clean；修复未动这些文件，故不重复无关几何再生成。42个本地文档链接可解析；`git diff --check`通过。schema/codec/JSON components为明确的审查样张，`expected/layout.json`是最小component/fragment witness，不是完整runtime snapshot或可直接加载的Stage2事实源 |

实际命令与 stdout/stderr 见证据包 `commands.json`、`fix1-findings-recheck.json`；主要入口为 `w003_generate.py --output <review-bundle>/regenerated`、`w003_verify.py --fixture tests/fixtures/w003_m1 --regenerated <review-bundle>/regenerated`、`w003_record_examples.py`（修复版定向复跑）、`w003_plot.py --fixture tests/fixtures/w003_m1 --output <review-bundle>/figure.png`，均由上述 Python 加 `-B` 执行。额外几何算法在 `independent_geometry.py`，计算结果在同名 stdout；overlay实物和清单在 `applied-overlays/`、`overlay-application.json`。

### R3. 未执行范围与下一关口

未执行产品 parser/Stage1–6、完整 runtime schema/codec/deep-freeze、CAS/原子 publication/recovery、v2或legacy pytest、strict typing、wheel/CI/其它解释器、Calibre/Virtuoso/真实PDK/model/body/abutment/live query/signoff、目标机或断电恢复。本轮不要求把这些未来实现义务塞入固定fixture helper；它们仍在 W002 E7/R4 与 W003 handoff 的首交验收要求中。没有提交、推送、改架构或写入 `layauto_v2/`。

可交 PM 接收本地样本/合同 review 结果；PM应按同一版本组织正常例及22个反例的用户人工正确性/使用预期核验，并另行验收/派发后续实现。独立技术 review 不消除生产事实/反馈权限/平台条件/真实回执缺项，不授权把本包辅助作为产品 parser 上传，也不宣称 M0真实门或M1产品能力已通过。

### R4. Reviewer 完整交接

独立本机证据包：`/private/tmp/layauto-w003-independent-review-i8gqzwtw`。包含原始/修复身份校验、从base重建目录、helper原始stdout/stderr、reviewer自有几何计算/22 overlay实物、F1/F2定向复核、原/修复待审包副本，以及加入本review段后的92文件 `snapshot/`、相对基线的 `full.patch`、`reviewer.patch`、`checks.json` 与 `SHA256SUMS`。最终hash保存在外部manifest，不要求本段自含自身hash。

写入后核验只有本文件reviewer段由reviewer改变，任务要求/执行/PM段及另91个受审文件保持修复版原bytes；完整patch及reviewer-only patch均可独立重建。恢复先校验manifest，再按记录重建，不重跑旧交付快照脚本覆盖证据。本包仅供本机短期交接；跨主机复用需保存可访问的完整版本，临时路径失效不能继续声称附件已核验。

## PM 验收与交接（PM）

### P0. 技术交付接收，人工验收待进行

2026-09-09，PM 接收执行及独立 reviewer 的最终交付，核对任务要求、相关架构原文、实际差异、可重建版本和 review 修复证据。**接收本地 synthetic 样本/合同的技术 review 结论；任务阶段为待验收，尚未由用户逐项确认，故不标 W003 已验收。** 原有执行 E0–E4、review R0–R4 原文保留；不把 reader/helper 变为产品 parser，不发布产品 wire API，不修改 M0 真实门或声明 M1 产品能力。

最终受审包：`/private/tmp/layauto-w003-independent-review-i8gqzwtw`，base 为 `main@b1f0301cf76b2e1808cb293cfdb4e1bfededde73`。

| 身份 | SHA-256 |
| --- | --- |
| `SHA256SUMS` 自身 | `473705b7b9d9bdbde41580e650c0f33e62a9816c0abf86e9a1e24977ae85345e` |
| `full.patch` | `c03a90b4f49c51a2343d54ad110420801d7b39966f6f5b6ec34c7b5b8fd1178f` |
| `reviewer.patch` | `a3cb961e718638cc4bf8a1ecb8434fef356daab2b2085cfdffd234a53cf0582f` |
| reviewer 段（`## Review 结论（reviewer）\n` 之后至 PM 标题前的原始字节） | `7ce7674c44e59753578ba57e8aaedbbceaa5159bceb0791ccad4f0d0d7ace319` |

PM 委派只读身份核验：最终包1938条 manifest、修复包233条全部匹配；接收时92份snapshot与checkout逐字节一致（3 tracked修改、89 untracked，staged为空）。从完整基线应用补丁重建后92份一致、189份未改基线文件不变；reviewer-only patch独立重建通过，相对修复版只修改reviewer段，另91文件不变，9份规范输入hash一致。核验原始记录在 `/private/tmp/layauto-w003-pm-final-verified-gtj8a101/pm-final-identity-result.json`。本次 PM 后续修改仅阶段/PM段、当前入口、文档导航和新增人工核验附件，不能再要求这几份 PM 文档与上述旧快照相等；受审执行材料及 reviewer 段应保持原身份。

### P1. 要求覆盖与 findings 接收

| 本任务交付要求 | PM 核对结果 / 证据 |
| --- | --- |
| 全部 M1 输入/输出边界与双方 owner | E1、contracts/schema、真实文件清单与handoff逐项对应；source/target、4 raw、header/normalized、tech/site/policy、GDS/CDL/JSON、记录/报告均有样张。JSON是最小component展示，完整runtime snapshot仍为后续义务 |
| 具体正例与独立判据 | 44形状、18 FIN、5/7 crossing、8 terminals、10 edges、6 components及T01–T10有手写来源；R2另用stdlib整数几何/连通算法核对，未只依赖generator或golden |
| 反例、单位与失败语义 | 全22 overlay实际应用，19绑定闭合、3故意错误；REAL8原字节/nominal界、输出不可表示/越界有独立证据。20记录/8失败组合均明确expected，不能称产品失败管线已测试 |
| F1 / F2 | create-attempt摘要已完整绑定run/head/输入选择；缺terminator样张已引用真实坏raw及其header。R1独立重算/追溯后均关闭；0未关闭实质findings |
| Legacy/生产分界与后续条件 | 没有legacy runtime依赖、产品实现或EDA运行；保留G1–G5和生产权限/平台/回执缺项。技术review通过后仍须用户确认，再准备具体parser任务 |

PM 本轮不重复运行已经被独立 review 且未改的 fixture helper 或产品/legacy tests；只检查本轮文档的链接、覆盖、写入归属、版本和补丁恢复。受审75个fixture文件、4个helper及原执行附件未改。

### P2. 全部 fixture 的人工核验入口

以下保留2026-09-09接收时的起始状态；最新进度见[P6](#p6)及人工清单MR-076，P5为迁移时历史，不再据此从A1或MR-054重启。

[人工核验清单](W003/manual-verification.md) 按 A 版图/电路/规则 → B 全部文件格式 → C 全22负例 → D 20条共享记录/8类失败/报告组织，包含全部44形状坐标、10条连接、8个端子和6个连通分量的可读表；B/C文件映射去重覆盖75个fixture。每项均为待确认，用户确认记录不由技术通过自动填入。

首先确认A的具体toy是否符合预期；其中同标签A孤岛是刻意测试，B的raw语法为具名synthetic而非已核实Calibre dialect。这两个使用预期必须按具体样本讨论，不因review未发现技术冲突而自动批准。后续若修改样本，由执行者串行处理，reviewer复核受影响项，PM更新版本与确认范围。

### P3. 恢复与后续授权

当前入口见 [current-work](../current-work.md)。用户人工确认及必要修正闭合后，PM决定本任务最终验收，再明确M1内最小Stage1 parser/输入绑定实现包；2026-09-09接收时未创建或启动实现任务、未上传辅助reader、未commit/push。2026-09-10审核分支的新增发布授权见P4，不扩大产品/生产范围。实际raw解析与本系统调用Calibre获取证据分别验证；可运行包经本地正负例和针对性review后，才在具体授权/平台条件下交用户向内上传。生产只能反馈脱敏格式时，真实准入仍标未核验。

本次 PM 恢复包：`/private/tmp/layauto-w003-pm-received-ew822nhg`。包含加入本次阶段/人工清单后的完整93文件snapshot、相对同一base的staged/unstaged/untracked/full patch及清单、最终独立review包完整副本、接收身份记录和文档覆盖/链接/归属/重建检查。`SHA256SUMS`绑定各文件，hash不要求写入本段自身。该包表示“技术交付已接收、用户待验收”，不是已验收包。

历史草案 `/private/tmp/layauto-w003-plan-gyzo3gkn`、执行准备 `/private/tmp/layauto-w003-ready-pzibrdp0`、初次交付 `/private/tmp/layauto-w003-delivery-uzpc4aed` 均只作历史身份，不再作为当前恢复输入。最终独立review包保留原/修复版及命令输出；临时路径只适合本机短期交接，跨主机须另保存完整可访问版本，不重跑旧快照脚本覆盖证据。

### P4. 人工审核分支发布（2026-09-10）

用户要求将需要人工审核的材料推送到新分支，方便另一平台查看。已从 `b1f0301cf76b2e1808cb293cfdb4e1bfededde73` 新建 `codex/w003-manual-review`，提交并推送材料为 `01535055f5d661a2964443dec76fc7f7f305e3e0`；推送后用 `git ls-remote --heads origin refs/heads/codex/w003-manual-review refs/heads/main` 核对，审核分支为该SHA，main仍为原基线。

发布前93文件与P3的PM接收snapshot逐字节一致，暂存区逐文件核对且 `git diff --cached --check` 通过；包含75个fixture、4个辅助与14份文档/图/记录/报告。既有执行/review原文和技术样本不变，未改 `layauto_v2/`、legacy或架构，不因commit/push标已验收。之后仅补本任务/当前入口/人工清单的发布说明，随同一分支保存。

人工核验材料及所有仓库内相对链接随分支可访问；不需要先复制本机临时包或安装环境才能阅读。临时完整执行/review日志包仍只在本机，本文已有技术结论不等于另一主机已复跑检查。下一步继续清单A–D的用户确认；未创建PR、合入main或开始后续实现。

### P5. 网页续接与人工记录同步（2026-10-26）

用户要求梳理总体进度、本地角色、GitHub 同步需要，并提供工作时间在网页 Codex 继续的 prompt 与 mental checkpoint。本次按该迁移范围同步累积人工记录与 PM 交接文档，仍使用 `codex/w003-manual-review`。

启动核对：本地 HEAD 和远端审核分支均为 `6d29b511ac415a9ea198d1e5c8978313c5abb6e3`，远端 main 为 `b1f0301cf76b2e1808cb293cfdb4e1bfededde73`；staged/untracked 为空，既有未提交文件仅 `.DS_Store` 与 `W003/manual-verification.md`。人工清单已有 MR-001–MR-054（相对 HEAD 增1599/删13行），与当前子 PM 会话最新答复一致。同步只含清单、当前入口、本任务 PM 段、附件导航及新增 [网页交接](W003/web-codex-handoff.md)；`.DS_Store` 保留本地，不纳入提交。没有修改原执行/reviewer 段、fixture、辅助、架构或产品代码。

当前人工状态：A/B 有局部确认与待改，C 全22例、D 明细未完成覆盖；恢复在 **MR-054 / B4.03d 文件 DBU 与网格精度关系追问**，未获通过答复。下一小主题为 B4.04a。MR-002、MR-004、MR-020、MR-030.2、MR-034、MR-046 及经 MR-052 收窄的 MR-051 修改要求保持，MR-040 方案仍未采纳；详细答复与版本只在人工清单维护。本次收到并整理这些记录，不表示修改已执行、方案已派发或 W003 已验收。

原版技术实物继续绑定 `6d29b51` / 材料提交 `0153505`；本次文档提交由 Git 绑定人工记录。启动时核对远端与本地 HEAD，并用 `git log -1 --format='%H' -- docs/tasks/W003/web-codex-handoff.md` 定位迁移提交。不能只检出旧技术 SHA 后假定累积人工记录也存在。

历史 `/private/tmp/` 执行/review/接收包未在本轮转存或重新验证；它们不是网页人工核验的必需输入，仓库内的样本、结论及版本身份可供续接。如需附件级复审，再单独取得完整证据。纯文档交接检查链接、写入范围、记录保留及身份，不重跑未改变的 fixture/产品/legacy 测试。云环境、账号访问和实际新会话恢复尚未演练；推送不等于整套本地环境或聊天历史迁移，也不代表用户验收、产品实现或生产验证。


<a id="p6"></a>

### P6. 网页人工核验收尾交接（子PM事实，2026-10-30）

本段记录子PM交付事实，尚非总PM接收或最终验收。用户确认D4八类总览预期后，本轮从MR-054续接的B后段/C/D核验话题转入修订交接；新增记录MR-055–MR-076，详细确认、待修订/未决及下一步唯一入口为[人工清单MR-076](W003/manual-verification.md#mr-076)。

- 已确认MR-054理解、B4后段/B5/B6及D1/D3/D4；C按用户要求概览22例，D2按委托总览20条。不得写成C/D2逐项亲自确认、A/B全部旧未决已通过或产品运行已验证。
- MR-002/004/020/030.2/034/046、经MR-052收窄的MR-051仍待修订；MR-074-Q1需明确Virtuoso检查身份映射。MR-040精简候选未采纳，B4.03c.2及A/B旧未确认范围保留；措辞建议/实现覆盖提示与用户决定分别记录。
- 总PM下一步接收清单，在既定范围组织样本修订及受影响独立复核，必要时回交新版使用预期；之后才决定W003最终验收和具体M1 parser任务。本轮没有派发样本或产品实现。

云端起点为迁移提交765ae5ef4ebf50e6870c5a978795525261d89ff6；收尾前fetch核对远端审核分支仍为该SHA，main仍为b1f0301cf76b2e1808cb293cfdb4e1bfededde73。用户在MR-060已授权本对话目的结束/交接时整理并提交推送codex/w003-manual-review，本轮保存人工清单、网页交接、本任务PM事实/阶段入口、当前入口及附件导航共5份文档；提交身份以Git及最终交接回复为准。未创建PR或合入main。

只做文档diff/链接/归属/恢复路径检查，并保留本轮静态文件、精确值和引用核对的明确范围；没有重跑历史完整回归、产品失败管线或生成器。原fixture/support/合同样张、架构、产品、legacy及本任务执行/reviewer正文保持原技术版本。旧Mac临时证据包未上传/重新验证；本轮用Git保存结论与恢复点，不提供完整聊天存档，旧逐轮patch无需叠加应用。网页角色与最新接续模板见[交接页](W003/web-codex-handoff.md)。

提交前5份交接文档相对765ae5e的实际diff经只读子agent独立复核，无必须修正的问题；diff/链接/恢复点、MR编号连续性及原执行/reviewer正文保留检查通过。此结论仅针对本轮文档，不替代样本修订后的技术review或后续推送结果核对。

<a id="p7"></a>

### P7. 总PM接收与修订轮安排（2026-10-31）

后续决定：用户接受单列W004，本节“继续W003”及执行prompt已由[W004](W004-fixture-revision.md)接替。以下保留接收与候选准备历史，不再平行维护执行要求；候选未因此获批准。

用户要求以PM角色继续，明确项目为环境中的Layauto v2。总PM已接收MR-076交接，并对照原MR、架构及实际样本核对修订范围。**下一节点是完成W003样本修订；产品parser仍以W003最终验收为前置。** 原技术review结论保留其原版范围，人工C为概览、D2为委托核对，不升级为用户逐项亲审。

启动位于干净的`work@b1f0301`，核查全部本地分支后切换到`codex/w003-manual-review@b41ba92940516ecadd26c64fc9fcb6829d21cbe1`；该提交包含MR-076、P6及最新网页交接。原fixture/support/合同实物相对原技术版未修订。`git ls-remote --heads origin`因无法连接代理端口8080失败，本轮未确认远端最新HEAD；不把本地可达版本称作远端最新。旧`/workspace/w003-handoff`是历史累积备份，不叠加应用；Mac临时review包未在本轮复验。

#### 修订范围与顺序

本轮继续W003，不另造一个产品任务编号。以下是修订执行范围，原E0–E4/R0–R4仍作为历史证据；后续执行、review各新增修订轮段落，不覆盖原结论。

| 包 / 优先级 | 输入决定与交付 | 依赖及完成条件 |
| --- | --- | --- |
| S0 / 先处理语义缺口 | MR-046的tapcell/body最小图、坐标/端子/连接答案、输入来源与失败条件；MR-004/040旧字段到唯一owner及候选配置面；MR-074-Q1检查身份/范围表 | 先给具体样张及影响，再独立核查。tapcell方向已定，新增上下文表达未定；配置精简未采纳。两者不以“等待用户”阻塞无关已定修订 |
| S1 / 来源与可读分类 | MR-002单位来源链、关键尺寸—规则—出处—适用对象—独立判据表；MR-004实际被消费的tech分类；MR-051/052的32×16测试假设和样张引用澄清；MR-001-Q1/MR-039措辞修正 | 保留现有policy输入边界即可推进分类；文件名/数量由职责与实际依赖决定，不机械拆八份。缺规则不杜撰生产数值；完整网格/CSP/DTO/codec/CAS留后续 |
| S2 / 场景与文件链 | MR-020主例移除LB/CUTB及R08/R09，孤岛/CUT/同格多片段移专例；按已确认的body具体方案修订；MR-034单一Calibre-like raw及MR-030.2可读normalized | raw格式调查、独立答案准备可立即进行；最终组合依赖body及分类来源。撤下W003_QUERY的active入口，不保留转toy中间层；四capability不固定为四文件，继续标synthetic |
| S3 / 组合证据与复核 | 对C01–C22逐项列旧目的→新见证→预期阶段/结果→重绑方式；同步header/closure/cache、records/failures/report、图表/helper/hash；处理MR-074-Q1 | 正常及坏raw均绑定实际文件，故意binding错误与语义负例区分；记录/报告所有结果仍为expected。新数量重算，旧44图形/10边/6分量等不是答案。完成受影响独立review后再回PM |

调查可并行，样本集成由一名执行者串行写入`tests/fixtures/w003_m1/`、`tests/support/w003_*`及`docs/tasks/W003/`受影响附件；新增专例位置由执行者说明。PM维护任务要求/阶段、当前入口和人工决定；reviewer维护新增review段。保持架构、`layauto_v2/`、legacy和历史review正文不变；若方案确需修改架构，先将具体差异交PM，不静默通过fixture引入产品合同。

#### 已完成的方案准备：候选与尚需决定之处

以下来自本轮只读调查，是可审查候选，不是用户已经批准的输入合同或已实现样本。

**Body候选：逻辑cell与外部tapcell见证分别展示。** 主source GDS继续flat单cell，移除本地TN/TP；BN/BP在本地物理图中不凭VSS/VDD名称与rail合并。另以synthetic上下文坐标表证明body与外部tap/rail的关系，并绑定source/body/frame/rail身份、profile/version和实际文件。架构§3.6允许有证据的scope外relation policy，但这新增fixture上下文输入；独立review需核对闭包与T04等影响，再将具体表达交用户判断。不能以未运行的baseline LVS声称满足冻结例外。

| 外部候选对象 | N侧bbox / nm | P侧bbox / nm | 待核对条件 |
| --- | --- | --- | --- |
| body延伸 | [-20,0,0,90] | [-20,100,0,200] | 与本地BN/BP在x=0的同类型边接触须由明确toy规则支持 |
| M1 rail延伸 | [-20,48,0,58] | [-20,148,0,158] | 与本地rail的边界接续、body到正确rail的关系须由几何证明 |
| tap | [-12,50,-8,54] | [-12,150,-8,154] | 类型与body/rail包围条件逐项给出，不从标签建立连接 |

这组坐标只用于方案审查，不写入现行fixture、不代表真实tapcell/PDK。执行准备须给“本地physical components”和“外部context支持的body association”两张答案表，并给缺context、绑定错误、错误body类型、tap包围不足、接错rail等失败见证；C22迁移为缺所选必需证据/支持，不能以无本地BTAP为错误。主例最终计数待组合修订和独立核对，不预先冻结。

**配置分两步处理。** 已授权MR-004先完成实际分类：候选为bundle引用入口、drc_rules、layer_map、calibre_layer_map、physical_profiles、format_profiles。这六项是职责映射示意，不冻结六个文件。比如T05 enclosure/T06–T07 spacing归尺寸规则；T03识别、T08连通、T09保真、T10覆盖分别归其profile/合同，仍保留mandatory要求；derived映射与annotation tolerance只保留一个来源。辅助须读取分类材料，不能另保留隐藏的tech.json权威。

MR-040的进一步精简建议仍待采纳：操作者只改site的输入、tech/profile、工具环境及输出根目录；`site.outputs.directory`作为单一选择，生效ExportPolicy据此派生；core artifact集合由版本化profile给出；required error→reject等固定约束不设用户开关。生效策略仍有可审查样张、来源/版本及完整校验，limitations保留一次性fixture来源，实际coverage等由未来运行采集。**本轮没有删除export/validation/limitations输入文件，也没有批准新默认行为。** 精简不影响分类及其它已定工作；采纳前继续现有边界。

**Virtuoso修订先明确范围。** 实物policy/report使用`virtuoso_readback`，ValidationResult/helper使用`virtuoso_dry_run`，现有合同不证明同义。建议以架构§10.3/10.5的“SKILL/ExportEdit在Virtuoso中的dry-run集成检查”给出明确范围和统一ID；若需要下游工具打开GDS/readback，另列范围，不能只改名后宣称覆盖相同。独立review核对policy→check→报告的完整映射及相关Calibre ID映射，保留deferred、coverage none、requires_review和未执行状态。新检查范围/能力承诺仍回PM处理。

#### 修订轮验收与下一角色

1. 执行者交MR覆盖/文件依赖矩阵、source/spec/oracle、分类来源及raw方言的具体方案；S0的新关键语义经独立review并取得必要用户决定后才集成对应部分。已定且无该依赖的修订可继续，不重新询问孤岛拆分、单一raw、分类或tapcell方向。
2. 样本完成后，独立review绑定同一完整新版本，核对精确单位、几何/端子/body/连通和全部适用toy规则；独立答案不只来自generator。实际应用所有受影响overlay，检查各自拒绝原因未被意外hash失败遮蔽；原F1/F2保证仍有效。
3. 组合检查覆盖再生成一致性、source/expected语义readback、raw与normalized同源、closure/typed refs/actual-byte hashes、正常与8类失败样张及人机报告。检查命令、环境、结果、未跑范围和完整snapshot/patch身份一并交回；不把helper成功写作产品Stage1–6已运行。
4. PM只展示发生变化或仍未决的使用预期：新版主图/body关系、raw→normalized示例、配置取舍及受影响拒绝例；保留A/B旧未确认范围、B4.03c.2样张澄清与MR-040状态，未改变的确认不从A1重来。必要修订、独立review、人工结论闭合后，PM才最终验收W003并创建M1最小parser/输入绑定任务。

本轮PM完成交接接收、修订范围及两项具体候选准备；只读协作角色为`pm_review`（交接/依赖核查）、`body_scope`、`config_scope`，它们不承担未来样本的独立技术review。尚未派发fixture写入、尚无新版运行结果。下一执行入口：

```text
按Layauto项目规范，执行W003修订准备，从任务P7和人工清单MR-076继续。
以包含P7的当前工作区/完整交接快照为准，先核对branch、HEAD、差异和身份。
先交body/tapcell最小样张、旧字段归属及raw格式/依赖矩阵；保留synthetic边界。
按P7区分已定修订与候选，不采纳MR-040、不静默增加外部body输入合同。
实际样本串行集成，保留原执行/reviewer历史，完成后交独立review。
不启动产品parser/runtime、完整坐标设计、EDA或生产上传。
```

Git保存：本轮PM记录留在审核分支工作区，未提交/推送/合并。恢复时同时带本轮相关文件snapshot/full.patch及SHA-256清单；仅检出b41ba92不会包含P7。本轮仅做文档与方案静态核对，无需重跑未变化的旧fixture或legacy回归；完整历史日志包的缺失不阻塞这次PM任务准备，但不复用附件级“已核验”声明。

本轮三文档的独立只读复核由`pm_review`完成，无必须修正的问题；受审diff SHA-256为`b636f302325e67fb55dc8c59a1f825d00751d3e2ce2d56e45c1fb35fc839c1e4`。PM另核对49个相对链接、diff格式、写入范围及原E/R段逐字节保留。该结论仅是PM文档/任务准备复核，不是body候选或新版fixture技术通过。追加本段后保存最终三文件snapshot、完整patch、清单与检查记录于`/workspace/work/layauto-pm-20261031-m1wo0qrt`；最终hash由该包manifest绑定，不要求本段自含自身hash。

### P8. 修订转交W004（2026-10-31）

用户接受独立修订任务，随后明确要求实际修改前先收敛任务。PM建立[W004 — 样本修订与验证](W004-fixture-revision.md)，以R1–R5承接MR-076；下一session仅收敛范围、依赖、待决及验收，不开始样本修改。W003保持待验收；W004经准备接收、明确启动、实际修订与独立review/人工结论闭合后，PM用同一新版证据接收W004并补本任务闭合结论，不重复两轮技术验收。原E/R与人工记录不变；用户已授权本轮PM文档推送审核分支，最新发布入口见W004。
