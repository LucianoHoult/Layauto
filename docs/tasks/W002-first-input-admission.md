# W002 — 首个输入证据与闭环准入准备

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| ID / 目标 | W002；给出第一套输入的可核查准入结论、真实资料缺口，以及可直接拆出 M1 实现包的共享合同/失败流方案 |
| 里程碑 / 依赖 | [roadmap](../roadmap.md) M0；依赖 [W001](W001-v2-global-plan.md) 规划 review 接收（2026-09-09 已满足）。U01–U05 可并行调查，真实资料不足不阻止仓库可做部分 |
| 授权与当前阶段 | **已验收（2026-09-09，调查与工程方案文档）**；独立 review 为 0 项实质 findings，PM 已核对版本、要求覆盖与限制。M0 真实准入出口仍未满足；M1 样本审查与实现尚未进行。已验收交付已推送 `main@f141af9`，本次集成记录另存；不开始产品实现或拆架构正文 |
| 范围 | 定向调查现有输入、legacy 可取用材料、真实资料/工具可得性；形成准入矩阵、最小样本说明、共享中立合同与 M1/M2 验收方案；本任务阶段仅文档/只读调查 |
| 非目标 | 不实现 runtime/parser/fixture generator，不安装部署 EDA、不跑完整 legacy audit、不修旧 fixture、不从零选定/假定 PDK，不拆分架构正文、不 commit |
| 写入归属 | 执行写本文件“方案与证据”段；需要独立附件才在本任务下明确链接；PM 维护阶段/要求/决定/验收；reviewer 独写 reviewer 段。修改路径前重查适用 AGENTS |
| 架构版本与必读 | `6eccdff99a4da64e46921d16a4c339198813bc78` 的 [architecture.md](../architecture.md) §1.4、§2、§3–5、§6–10 的上下游消费条件、§11.1/11.14/11.15、§12–13；共享接口需读双方 owner 原文，不靠 roadmap 摘要定义语义 |
| 负责人 / 阻塞 | 执行、独立 review 与本任务 PM 验收已完成；下一步由 PM 准备 M1 具体样本与独立判据任务。E3 G1–G5 的真实材料/工具位置与持有人待协调，M2/M3 对应门保留 |

### 可直接开始的输入与顺序

1. 核对 checkout/HEAD/工作区已包含 W001 原稿提交 `8482b68f6b2b0958f1ac501b15cd393a66782c4a` 及最新 current-work 集成记录，不从旧 `6eccdff` 单独启动（该版本尚无任务文件）；读 [协作规则](../collaboration/rules.md)、[本地环境](../environment/local-setup.md)、[W001 盘点](W001-v2-global-plan.md#2-现状与证据盘点)；从已定位路径复核与首个切片直接有关的资料，不重新遍历全部历史。
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

### E0. 本次交付与版本

先证明输入是什么、哪里可信，再允许它进入闭环。例如现有 `MN0: 5→4 / MP0: 7→6` 可以说明双 shrink 场景，但随之重新生成的 FIN、边界和电源轨不能充当 fixed-frame ECO 的正确目标。

**2026-09-09 执行交付：调查与方案已整理，交 PM 核对并组织独立方案 review；真实准入未通过。** M0 工程出口提交待接收材料，M0 真实准入出口保持未满足；M1/M2 均未实现、未验收。以下“拟定/建议/预期”是待审实现包设计，不是新增架构合同、已创建 fixture 或运行结果。任务阶段、上方要求和下方 PM/reviewer 原文由其 owner 后续更新。

- 执行位置：`/Users/luciano/Library/Mobile Documents/com~apple~CloudDocs/Work/个人项目/Layauto`，`main`，同一 checkout 串行写入；主执行 `/root`，只读协助 `/root/input_evidence`、`/root/contracts`，均未承担正式 reviewer。
- 启动 HEAD 为 `156e62d150349ac127476074f73524677f6d7760`；`git cat-file -t 156e62d` 为 commit，`git merge-base --is-ancestor 156e62d HEAD` 成功；起始 staged/unstaged/untracked 均为空。调查期间另一个 PM 会话提交 `2775e5945ff10353a7b35f1f997e6927668f4416`，只改 current-work、roadmap、W001 的发布/派发记录；已读实际 diff 并保留。**本执行交付基线为 `2775e59`，只修改本文件执行段，无本轮 Git 提交。**
- 已读 README、根 AGENTS、协作规则、current-work、W002、W001 盘点、环境说明及架构 §1.4、§2–10 上下游、§11 owner/边界、§12–13。检查路径祖先与仓库局部规则，仅根 AGENTS 适用。架构相对 `6eccdff` 未变，SHA-256 为 `0a3ca52fed12af500d973deb3bddebac9a8f7f8f697769dc86827a59c07196c9`。
- 本文全部产品判断回到 [architecture.md](../architecture.md)；E6 仅把现有合同落实到近期 producer/consumer，不拆架构、不新增并行规范源。没有运行产品/legacy 回归、generator、EDA/query/signoff、安装或部署；没有全面重审 legacy。

### E1. 已有输入、来源与可取用材料

调查范围限于 [W001 盘点](W001-v2-global-plan.md#2-现状与证据盘点) 已定位的 inverter、raw/YAML、相关 importer/配置/生成器/测试及报告。文件存在和源码可读不表示它已通过 v2 parser、真实工具或物理检查。

| 材料 / 定位 | 实际观察与来源级别 | 对近期工作的影响 |
| --- | --- | --- |
| [source CDL](../../legacy_mvp/dummy/fixtures/buffer_original.cdl)、[target CDL](../../legacy_mvp/dummy/fixtures/buffer_target.cdl)，各第 1–5 行 | `INV_N5_P7`→`INV_N4_P6`；pins `VDD VSS IN OUT`；MN0/MP0 的 D/G/S/B 文本分别为 `OUT IN VSS VSS` / `OUT IN VDD VDD`；`nmos_finfet/pmos_finfet`，`nfin=5/7→4/6`、`l=20n`。生成的 synthetic inverter，未提供真实 model 定义 | 证明文本及场景；不证明 token 物理轴、默认 finger/multiplicity、S/D symmetry 或真实 extraction。Top 名差异也必须解释，不能只挑 nfin diff |
| [source GDS](../../legacy_mvp/dummy/fixtures/buffer_original.gds)、[target GDS](../../legacy_mvp/dummy/fixtures/buffer_target.gds) 与 [generator](../../legacy_mvp/dummy/gen_buffer_layout.py) | 生成器随参数重建布局；target 不是在 source 固定 frame 上完成受检 ECO 的记录。精确 record 盘点见下方 E1 补充及 E8 原始结果 | 可作 stream 格式/拒绝场景种子；不能把 target 当 fixed-frame、static-FIN 或 DRC golden。GDS 与 convenience JSON 的存在不能替代逐 record losslessness |
| [raw xref](../../legacy_mvp/dummy/fixtures/iXref.temp)、[raw net xref](../../legacy_mvp/dummy/fixtures/nXref.temp)、[NET NAMES](../../legacy_mvp/dummy/fixtures/net_names.txt) | raw header 明示 dummy；另有两份 device info、四份 net shapes 及对应四类 YAML。存在的是旧 dialect 记录，不是 versioned QueryBundleHeader | 保留 raw 作为输入，未来同一 parser 产生/核对 normalized；不得 normalized-only 或回退 legacy JSON |
| [device_info.yaml](../../legacy_mvp/dummy/fixtures/device_info.yaml)、[net_shapes.yaml](../../legacy_mvp/dummy/fixtures/net_shapes.yaml)、[ixref.yaml](../../legacy_mvp/dummy/fixtures/ixref.yaml)、[net_xref.yaml](../../legacy_mvp/dummy/fixtures/net_xref.yaml) | `precision=20000`、bbox 数值和 identity 表可调查；缺 v2 header/content linkage、original numeric encoding、quality/closure/status。Generator 的 net shapes 来源是 raw drawn bbox，device info 是 synthetic seed | 抽验同值不等于证明完整同源、trimmed effective geometry 或 production dialect；bbox 标 `approximate_bbox/untrimmed`，不能升格 exact device/conductor truth |
| [旧 layer map](../../legacy_mvp/tech/layer_map.yaml)、[derived registry](../../legacy_mvp/tech/calibre_layer_map.yaml)、[rules](../../legacy_mvp/tech/drc_rules.yaml) | rules 第 34–36 行自称 `dummy_7nm_finfet`；derived registry 开头说明按公开资料/惯例构造，含 VERIFY；旧配置未具备完整 v2 profile/owner/schema | 仅保留待查字段与反例；不借 ASAP7-style 名称选定真实 PDK。需要按 §12 拆清 drawn 与 derived authority 后验证 |
| [site config](../../legacy_mvp/tech/site_config.yaml) 第 22–92 行、[query shell](../../legacy_mvp/scripts/calibre_query_extract.sh) | 默认 dummy，SVDB 路径是 placeholder；输入仍含 convenience JSON。Shell 是 TODO/注释命令示意 | 没有实际 query DB、可运行部署入口或真实 captures 的证明；不能照抄为 v2 config/adapter |
| [query parser](../../legacy_mvp/io_adapters/calibre_query.py) 与 [单测](../../legacy_mvp/tests/unit/test_calibre_query.py) | 可参考 xref/count/header/terminator、missing-output/timeout 组织；单测第 7–9 行明示 real-mode 为 mocked subprocess。Device/net parser 以除法得到 float bbox | 迁入 v2 importer 后换为 exact records/units/header linkage/typed result；tool runner 独立。旧 mocked 成功不能证明 live command/dialect |
| [CDL parser](../../legacy_mvp/io_adapters/cdl_parser.py) 第 12–110 行、[writer](../../legacy_mvp/io_adapters/writer_cdl.py) 第 8–16 行 | tokenization 可参考；值先 float，writer 硬编码 inverter 的 pins/models/参数 | 只取用合适的纯逻辑/案例并加纠错回归；不保留有限参数白名单、隐式默认或忽略未知 diff |
| [GDS IO](../../legacy_mvp/io_adapters/gds_io.py) 第 148–198 行、[roundtrip harness](../../legacy_mvp/tests/integration/test_dummy_roundtrip.py) | writer 由 fin 参数拼 cell 名，reader 从 polygon min/max+round 构 bbox；harness 有组织参考价值 | 不能整体复用为 semantic-lossless reader/writer，不继承 FIN remove/输出 replay 断言；纯逻辑迁入对应 owner，不 import legacy |
| [历史报告](../../legacy_mvp/output/resize_report.txt)、[报告源码](../../legacy_mvp/pipeline/run_mvp.py) 第 378–422 行 | `BUFFER FIN RESIZE REPORT`、7 个 edit ops，包含 REMOVE FIN；coverage 报告逻辑为 layer 总量/已标/未标 | 可参考人读信息层次，不作为 v2 输出合同/正确性 oracle；新报告按真实 semantic cell 身份与 frozen run/chain/checks 生成 |

**E1 补充：本轮只读实测。** 一次性调查脚本 `investigation/evidence_probe.py` 与完整输出 `evidence_probe.json` 在 E8 交接目录；主执行检查脚本并重复运行，输出逐字节一致。它没有调用 legacy parser/generator，也不是已实现的 v2 importer。

- Source GDS 为 2164 bytes、一个 `INV_N5_P7` cell、32 个 BOUNDARY；target 为 2036 bytes、一个 `INV_N4_P6` cell、30 个 BOUNDARY。逐 record 检查均是闭合轴对齐矩形；记录集中无其它 element、hierarchy、property/text。只证明这两个输入的 record 子集，未做产品 export/readback。
- 两份 GDS 的 UNITS payload：offset 50，`3e4189374bc6a7f0`，exact `1152921504606847/1152921504606846976`（DBU/user-unit 比）；offset 58，`37119799812dea11`，exact `4951760157141521/4951760157141521099596496896` m，约 1 pm。[gds_io.py](../../legacy_mvp/io_adapters/gds_io.py) 第 143–146 行声明 gdstk user unit 1 nm、precision 1 pm；不应误用另一个 writer 的默认 DBU。Nominal 近似比较仅供调查，**未验证 UnitScaleContract 或授权 coordinate snap**。
- 以原始 XY ticks 比较，FIN 12→10；BOUNDARY `[0,0,108000,430000]`→`[0,0,108000,380000]`，NWELL、POLY 高度、VDD rail 也变。生成器第 94–109、151–187、841–846 行解释其逐参数重建来源；旧 target 不能证明 fixed-frame shrink。
- 按生成器第 574–576、645–672、723–752 行声明的 **synthetic `(y,x)`、µm/20000** 约定，2 个 device bbox、13 个 net bbox、xref pairs/swap flag、net names/index 与配套 YAML 数值一致。例如 `device_info_M0.txt` 第 17 行 `(550,880)` 对应 `(x=0.044µm,y=0.0275µm)`。这不是 v2 schema/完整 header closure/真实 query 方言或有效区域 trimming 验证。探针初版曾误读 YAML key，修正后通过；未修改 fixture。
- 两 registry 具体不匹配：derived registry 无 `LI`/`VIA0` entry；`ngate_lvt/pgate_lvt` 第 133–155 行关联 `GATE/ACTIVE/LVT`，而当前 canonical 是 `POLY/OD` 且无 `LVT`，缺显式 alias/derived refs。M1 注释 stream key `19/0` 与本样本 `5/0` 也不能视为版本匹配。Body 的 CDL VSS/VDD 文本与一个 NWELL rectangle 不足以证明 body/tap/PSUB extraction。

| 关键文件（目录均为 `legacy_mvp/dummy/fixtures/`） | SHA-256（其余 raw/YAML/关联源码完整清单见调查 JSON） |
| --- | --- |
| `buffer_original.cdl` | `4f7c0878bf5ad094c36093595d6edfc149616013e69c55e25df5e14031aa88de` |
| `buffer_target.cdl` | `06e13d6fac8568d36a4361aa47a36d8000434b69430039541eeed3a977940913` |
| `buffer_original.gds` | `efd4628f2a1f85be3c5ab4e4a43895990088e00d3c06727d26b5e3b044c1c364` |
| `buffer_target.gds` | `7f21e84736d0d8552e2e2f452f04e057a653ead41d3231a865d69f3453a79efa` |

Stage 1 两类 acquisition 的首批需求分列如下；命令名只是现有 adapter 示例，不能据此宣称通用 Calibre 格式。

| 获取方式 | 当前可用性 | 必需测试/证据，待后续包执行 |
| --- | --- | --- |
| `dummy_fixture` | 旧 raw/YAML 可读，但缺完整合规 header；E5 正例尚待重建 | Versioned synthetic dialect/template identity、unit/coordinate order、precision、每类 terminator/count、raw hash、完整 header/closure、generator/parser provenance；正常/缺输出/截断/同源漂移均走正式 parser，tool-version 标 synthetic/not-applicable，不伪造 binary run |
| `calibre` | 只有模板源码和 mocked tests；未取得真实 DB/capture 或 PATH binary | Tool/version+query DB kind、参数化 command/script template、escaping、unit、terminator、raw capture hash；真实四类能力的 capture→同一 parser 测试和本系统 live acquisition execution refs。Missing binary/license/DB/deck、timeout/nonzero、格式漂移分别验证 ToolRunResult/ParseResult/StageFailure；实例/net 名不直接拼 shell |

**真实资料搜索结论的边界：**在上述仓库材料与配置指向范围内，未找到能证明真实工具来源且具完整绑定的 captured bundle/model/deck/query DB；本机当前 PATH 未定位 `calibre`、`virtuoso`。未扫描用户其它项目、远端主机、私有 PDK 目录或许可证服务，因此结论是“本任务可访问材料不足”，不是“用户没有工具/资料”。外部持有人和合法可共享位置待 PM 协调。

### E2. 具名候选准入矩阵

候选为架构已有的 **`explicit_static_fin_plus_active_window`**，待核验对象为现有 `INV_N5_P7` 场景，不是选定的生产 profile。下表“有证据”只证明对应文件事实；所有失败是**未来实现应返回的合同后果，未在本轮执行**。Required binding/缺 operator 不转为 warning；只有另行明确的 synthetic/degraded policy 才能保留 suspect，且不启用真实 resize。[§1.4](../architecture.md#14-支持范围与暂不覆盖范围)、[§12.6](../architecture.md#126-calibre--lvs-query-evidence-获取与结构化输入)。

| 准入维度 | 当前证据等级 / 缺项 | 准入后果 |
| --- | --- | --- |
| 真实 provenance / baseline | **需补证**：只有 dummy 来源；无 matched source GDS/CDL+model/deck/closure/query run/status bundle | 不得标 `lvs_matched`；M0 真实出口、M2 真实输入不通过 |
| canonical size axes / model token | **有证据：synthetic 文本** `nfin`、`l`；**需补证** model 对 `fins_per_finger/finger_count/multiplicity` 与其它参数轴的定义、默认值与重写规则 | 不从 NFIN/NF/M 名推断；不能解释的轴/表达式 typed-unsupported |
| terminals / body / S-D swap | **有证据：文本 pins**；**需补证** model terminal order、body tie 与 symmetry。未证明真实 MOS 的自由 swap | 有序 terminals 保留；未授权 swap、body 无法解释则拒绝/缺证 |
| single-finger | **需补证**：没有 canonical `finger_count=1` 的可信 extraction/model binding；CDL 未写 finger token 不等于单指 | 多指或无法证明所选子集，admission unsupported；不拆指 |
| one-to-one / no reduction | **有证据：dummy xref 表**；**需补证** extraction cardinality、reduction settings/结果 | 名字对应不证明无归并；非一对一/依赖归并则 unsupported |
| geometry / top identity | **有证据：具名 GDS 与 record 盘点**；**需补证** frozen GeometryCapability、comparator、source/output top binding。源目标 top 不同 | 每个 reachable record 保真或 baseline 前 typed-unsupported；无显式合同不静默改名、不 bbox 包络 |
| CDL subset / all-delta closure | **有证据：简单两 M 行且无 include/expression**；**需补证** model closure、dialect case/escape/suffix/directive 规则、top 差异解释 | 最小测试 subset 可另定义；未知 directive、include、参数/top/拓扑差异不得被忽略成 no_change |
| exact units / scale binding | **有证据：GDS REAL8 原 bytes、XY ticks、raw precision**；**需补证** nominal DBU/UnitScaleContract、query unit、model/rule exact scale | 原 tick 不 snap；单位冲突、等价界缺失、非唯一 scale、输出不可表示均 typed-fail |
| drawn / derived registries | **不匹配当前 v2 合同**：旧 schema/别名/VERIFY，缺唯一引用解析与完整 element-tagged key、quality/trim/颜色对账 | 重复/未知/冲突 mapping fatal；不能按名字相等 fallback；未知 geometry 保留或拒绝 |
| FIN representation / extractor | **不匹配现成 target oracle**：按每 device 参数生成 FIN；**需补证**真实 static backdrop、effective FIN∩active∩channel 与 grouping extractor | 不启用 real resize；不删 FIN、不从 per-device fin 列表/Y 轴计数代替 extraction |
| resize / LI–VIA0–M1 repair | **需补证**：无可信 profile-bound operator；旧 target 会改变 frame，旧 repair 有架构已记录缺项 | required repair 不具体、operator 缺失均 non-executable/unsupported；不能推到 signoff |
| mandatory rules / relation context | **有证据：dummy rule numbers**；**需补证** source/version、closed variants、exact evaluator、relation assurance 与作用域闭包 | 无 mandatory predicate/有效 relation 则 fail closed；不以同名 net 或未知 net 放宽 |
| layer lifecycle / finalization | **需补证**逐层 preserve/frame/derive、derivator/version/dependencies/comparator、DAG closure | baseline 也不许缺 operator/comparator；不能按 NWELL/BOUNDARY 名字自动 derive |
| body / frame / halo | **不匹配现成 source→target 的 fixed-frame 用途**；**需补证** baseline body/extraction、halo 参数/signature、邻居完整等价类或不触及证明 | frozen body 需 baseline LVS+invariant；触 halo 无完整合同即 capability fail |
| query dialect / acquisition | **有证据：dummy raw 格式及 terminator**；**需补证** tool/version/DB/template/unit/escaping、raw capture hash、live adapter 运行 | M1 可规划 dummy_fixture；M3 前 calibre acquisition 门保持。Stage 6 signoff 延期不免除此门 |

**结论：现成材料可作为调查/拒绝用例与重建 synthetic fixture 的来源，不能直接当 v2 准入正例；真实候选 profile 尚未获准。** E5 的新 synthetic profile 是建议建立的工程测试对象，不能继承这套旧材料的未验证物理声称。

### E3. 真实证据缺项与最小索取包

由 PM 向设计/PDK/EDA 资料持有人协调，具体姓名、主机、权限与获取时间目前未知。本执行未联系他人、未申请许可证或费用、未改变输入解释。优先取得“一套同源小 cell 的完整材料”，再决定是否匹配候选；不要求用户凭空选 PDK。[roadmap U01–U05](../roadmap.md#6-待查明事项与上报点)。

| 包 / 建议持有人（待 PM 确认） | 最小索取内容与获取方式 | 消除条件 / 阻塞范围 |
| --- | --- | --- |
| G1 设计 baseline；cell 设计持有人 | 可合法共享的 source GDS、source CDL、目标意图/target CDL、top/hierarchy 信息；每项版本、byte hash、来源。Include/library/model/preprocess 完整递归清单，immutable URI/hash；没有依赖也明确空 closure | 逐项 hash/top 同源、闭包可解析；阻塞真实 M0/M2。仅缺目标几何 golden 不阻塞，不能替代 source |
| G2 model / tech；工艺或 deck 持有人 | process/model/deck 名和确切版本；size axes/token/default/unit/terminal/symmetry，finger/reduction settings；drawn layer key、derived aliases/trim、rule source、nominal DBU、UnitScaleContract | 将 E2 每个假设映射到证据页/记录并完成 runtime schema/operator 对账；无法说明则对应 capability 拒绝 |
| G3 matched query capture；LVS 运行者 | 同一 G1 的 query DB/run id、tool/version、deck/map/runset/include/options/preprocess closure、completion/match 日志；四类 raw 输出（instance/net xref、device/net region）与 header、单位/precision/quality、命令/template/dialect/terminator/escaping；normalized 仅作可重解析缓存 | Raw/header/input 绑定一致、matched/complete、parser provenance 和失败样本齐全；外部 capture 可以补真实来源，但不证明本系统 live adapter 已跑 |
| G4 物理操作条件；PDK/单元设计者 | effective fin/active/channel/device/body recipe、canonical count extractor 与独立 oracle；LI/VIA0/M1 repair 可行域、rules/relations/enclosure/extension；逐层 lifecycle、body/frame/halo 与完整 neighbour contract（或可核查不触 halo 条件） | E4 每个 mandatory 消费者有 operator/来源与验证；缺一项阻塞其 M2 candidate，不能靠延期 signoff 消除 |
| G5 Stage 1 执行位置；EDA 环境维护者 | 已有授权主机/工作目录与可读 DB、binary/tool version、license 可用性、runner template 和脱敏 execution/raw refs；由持有人运行或后续明确授权在该环境执行 | 本系统所选 calibre adapter 取得 raw 并完成 captured/错误路径组合验证；M3 门。当前 PATH 结果不足以判断远端可用性 |
| G6 输出消费预期；PM/下游使用者 | 若真实样本出现 top rename、include/opaque directives 或特殊输出格式，提供最小输入及消费命令；确认需要自包含 CDL 还是 immutable dependency bundle、是否要求 byte 稳定/工具入口命名 | 先给技术保真方案；只有新增关键格式/使用预期/验收变化才交用户决定。不以空泛 UI/图风格问题阻塞 M1 |

可继续的独立工作是 E7 的 synthetic 合同/错误路径开发准备，仍需共享方案 review 和 M1 任务授权。本轮没有新的产品范围决议；G1–G5 是具体事实缺口。若 G5 不可得，PM 应记录 M3 阻塞，只有用户明确决定才可另改范围/验收，不能自行把 Stage 1 live acquisition 标为 post-MVP。

### E4. M2 物理依赖与可复核边界

首个真实 M2 包建议只选一个 required `fins_per_finger: 5→4`，保持另一器件及全部未改轴；这是调查优先方向，未确定真实样本、方向或尺寸。下表来自 [§6](../architecture.md#6-基于物理事实的修改语义)、[§8.1](../architecture.md#81-constraint-engine)、[§9.4](../architecture.md#94-policy-controlled-geometry-finalization)，不是旧 fixture 的豁免列表。

| footprint / 消费者 | 必需的证据、operator 与验证 | 当前出口 |
| --- | --- | --- |
| effective FIN/active/channel/device | Parent/candidate exact extractor、model axes、gate grouping/cardinality；计数分别等于 before/after，未变 finger/multiplicity/其它轴与未触 device count/topology 保持 | 缺真实 recipe/oracle；raw FIN/gate-targeting CUT 不获编辑许可 |
| OD 与 S/D/body 拆分 | Exact active 减 channel separator、S/D attribution/sharing、body operator、touched device/pin reachability；transistor S↔D 不建 conductor edge | 不能从 bbox 或 device label 证明；body 冻结需 matched baseline+不变量 |
| LI/VIA0/M1 access | Fully-ground old/new repair；qualified via contact、exact width/spacing/enclosure/extension、pin access/rail topology；VIA0 不 double-stamp 成 wire | 旧 rule/repair 不足以准入；不能先提交 OD 再补接触 |
| raw/effective cut、unknown/dummy geometry | 声明 cut target/Boolean operator，unknown 几何保留并按实际角色参与 topology/blockage；relation-dependent predicate 检查 assurance | 未触 cut 的结论也需 old∪new footprint+依赖闭包证明；不能靠“没计划改 cut”豁免 |
| marking lifecycle | 逐层 preserve exact compare、frame signature、或 certified derive（generator/version/deps/context/dirty-scope/comparator）；actual delta 触发消费者重检 | 无证据时不自动 derive；M1 baseline 同样受此约束 |
| boundary / rails / halo | Parent→candidate `boundary_halo_signature` 覆盖 raw/effective geometry、mask、well/body、ports；expanded affected scope 与 halo 不相交且所有相关依赖不变，才可证明不触及 | 缺 halo/context 参数，当前未证明“不触 halo”。触及时需完备 neighbour classes（方向/镜像/row transform）或实际完整 tiled context 的 required signoff |
| mandatory rule closure | old∪new footprint 扩张 rule halo、whole entity、via/cut partners、pre/post components、body/frame 与派生 DAG；candidate hints 只加不减；缺有限闭包则 full-check 或 unsupported | 不把 LI spacing、VIA0 enclosure、intent invariants 交给未来 signoff |
| finalization 与 publication | Dirty dependency 就绪后再判；actual final delta 重算 extraction/connectivity/relation/规则，直到无 dirty/pending；cycle 仅可用具终止/唯一性证明的 bounded fixed point | 无闭包/required operator 或任一有效检查失败，无 ECO publication；Stage 6 不补图 |

M2 正例未来须证明 fully-ground repair→exact mandatory feasible→finalization/post-check→一次 whole-intent envelope，并 readback GDS/CDL/JSON；反例至少含 grow、多指、非一对一/reduction、raw FIN edit、缺 repair/predicate、stale precondition、finalizer 失败。混合 supported+unsupported 全拒绝，多器件/多 delta 的完整成功覆盖仍归 M3，不能误把首版限制成单器件。

### E5. 最小输入→输出与使用预期草案

**现成资料的预期路径是拒绝诊断。** 将旧 source CDL/GDS 与旧 raw/YAML 按 v2 required profile 提交，缺 header/unit/profile binding 应在 Stage 1/2 typed-fail；只能产生带 source refs 的 diagnostic report。即使补齐 parser 格式，target top 改名及 frame/FIN 差异仍需完整 delta 解释，不能被两项 nfin diff 掩盖。本轮未实现或运行此拒绝路径。

**M1 正例建议新建 `synthetic_static_fin_no_change_v1` 测试 profile（尚无文件）。** 从两器件 inverter 场景重建可手算的 toy geometry、独立 spec/期望表和 raw captures；source/target 使用相同 cell 身份（示例 `INV_M1_SYNTH`），5/7 个 qualified crossings、单 gate stripe/单指、一对一、无归并。Toy model 明确各参数轴/terminal/body 语义，不能沿用 `nmos_finfet` 名称推断真实模型。其 body/terminal/conductor exact operator 必须有完整 toy 定义与独立手算预期，不借“no_change”冒充真实 frozen-body 豁免。

- 输入是同源 **GDS + source CDL + target CDL + QueryBundleHeader + 四类 raw + 可重解析 normalized YAML + tech/site profile + machine-readable limitation**；全部为新建计划，不复制 final snapshot。拟选 flat axis-aligned BOUNDARY/BOX 子集、明确 integer ticks/REAL8 scale binding；不支持的 PATH/TEXT/hierarchy/transform/property/repetition/unknown stream key 在 baseline 前拒绝，后续只有具保真合同才扩展。未 annotation 的允许类型仍原样保留并披露。
- Toy CDL subset 拟支持单 top、明确 pins/model/terminal order、显式 literal size axes 与 exact suffix。Source/target 可有空白/注释差异但全量语义相同；未支持的 expressions/includes/library/preprocess/opaque directives 明确拒绝，不吞掉。无 include 的测试也记录空依赖 closure。模型默认值只能来自该测试 profile 的显式定义。
- Raw query 由测试 spec 定义；header 的 `mode=dummy_fixture`、assurance、raw hash、units、closure、dialect/parser versions、synthetic status 均如实记录，不伪造 Calibre 版本或 matched status。所有 raw 都通过正式 importer；normalized cache mismatch 是失败，不读取 convenience JSON。
- 输出为 baseline snapshot（version 0、InitializationEvent）→semantic/extraction-aware `NoChangePlanningResult`→frozen no_change RunRecord（`ordered_commit_ids=[]`）→GDS/CDL/JSON Manifest→ValidationResult→人/机器报告与 ReportingResult→terminal PipelineResult。**Baseline publication 不是 ECO commit，no_change 不生成 empty commit。** 建议 synthetic policy 将 terminal disposition 设为 `requires_review` 并说明仅工程测试；此 policy 待 review 冻结，不声称 production accept。
- 正确性 oracle 拟由手写 exact coordinates/terminal graph/count 表、原始 integer tick record、source semantic preservation assertions及独立 reader交叉核对组成；generator/writer 自生 golden 只作回归。可用 KLayout 作额外 downstream readback，但生产工具/PDK syntax/closure 仍另行验证。

| 代表反例 | 未来应观察的结果 |
| --- | --- |
| CDL 文本相等但 extractor 得 4/7，target 为 5/7；或多 target source 冲突 | 不能 no_change；typed semantic/extraction mismatch，列全 delta，拒绝 ECO |
| Source=target、extractor count 相同，但 toy baseline 适用的 mandatory rule 违例/不可执行 | 不能以空 delta 或已初始化成功关闭 no_change；记录 rule fail/indeterminate/error，无正常成功导出 |
| Source/target pins、model、L/W/VT、net topology 或 top identity 不同 | 全量 ledger 明示；未支持变化 unsupported，不忽略成空 diff |
| 多指、非一对一、需 reduction | Admission typed-unsupported；无 candidate/ECO envelope |
| 非矩形正交 polygon、metadata/未知 key、不可表示 DBU 或 unit mismatch | 无 semantic-lossless capability 时 baseline 前拒绝；不 bbox 包络、不 int 截断 |
| Raw 缺 terminator、unit/header/closure mismatch、YAML cache 与 raw 不同 | EvidenceIssue + linked ParseResult/StageFailure；没有 Stage 6 ValidationResult |
| 同 cell 两不连通 fragment、bbox tolerance 多解、untrimmed seed 跨 channel | 保留 exact geometry/topology，细分或 ambiguous；annotation 不制造 edge，不因相邻 cell/同 net label 导通 |

**CDL/报告差异与推荐：**现有 writer 会重建固定 inverter 五行、改 top 名且只写 nfin/l；建议 v2 从 current semantic+source preservation refs 输出，保持已声明 pins/globals/models/terminal/未改参数，按语义 comparator 验收。架构不要求 byte/record order/timestamp 一致；若用户未来要求 byte 稳定，这是额外使用预期，PM 应先附真实样本评估。现有 BUFFER/edit-op 报告改为 cell/run 语义报告属于既定保真义务，不需重问单指/shrink 范围。

人/机器报告的**样张提纲（非运行结果）**：`cell/run/profile/assurance` → 输入文件/closure/hash 与 tool mode → 全 target delta 及 supported/unsupported/no_change 理由 → 初始化/候选/规则/传播摘要（未执行项写 not-run，不造统计）→ snapshot/ordered chain 与 base/derived/annotation/connectivity changes → coverage/validity/unknown/blockage/limitations → 每 check 的 status/coverage/severity/disposition/reason → manifest byte hashes 与 validation refs。人读正文显示 schematic name，保留 LVS opaque id 作为 backlink；失败样张只显示已完成 audit、失败阶段与 optional stable refs。Machine report 与人读报告同源，不要求本轮确定图表样式。

### E6. M1/M2 共享合同、owner 与失败流草案

下表是 [§11.1](../architecture.md#111-建议-package-layout) 与各 producer/consumer 原条款的实现分工建议。所有持久 DTO 需 versioned wire schema、runtime validation、recursive freeze；字段使用 discriminated variants，不以一堆 Optional 拼非法组合。具体 schema version 初值/字段拼写由近期包在 review 后确定，不能先发布未冻结的对外格式。

| 合同 / 中立 owner | producer → consumer | 首批字段、绑定与拒绝条件 |
| --- | --- | --- |
| Evidence / ToolRun / Parse；`domain/evidence.py`、`domain/results.py` | `tooling` 获取 raw，pipeline 将 raw refs 交 `importers`；`normalization` 消费 schema evidence | header id、mode、raw URI/hash、layout/netlist/top/deck/options closure、tool/dialect/parser versions、status/assurance、original lexeme/bytes+exact unit。ToolRun 只存执行事实；ParseResult 单向引用 tool_run_id。Missing/output/timeout/license 与 format/terminator/binding failure 分层；tooling/importers 互不 import（§12.6–12.7） |
| Tech / UnitScale；`tech/` | config importer safe-load → immutable tech DTO → normalization/annotation/planning/constraints/transactions/export | profile/schema/content ids、Geometry/CDL/FinCount/DeviceExtraction、drawn/derived registries、rules/operators/lifecycle/DAG。拒 duplicate/unknown keys、可执行 tag、size/depth 超限、非法 variant/单位/reference；site 只选择/收紧，不改事实（§4.8、§12.1–12.5） |
| Canonical codec / IDs；`domain/codec.py`、`identifiers.py` | 全部持久 record producer → repository/artifact/audit consumer | 显式 typed id/Enum/Path/Decimal/rational/tuple/frozenset/table 编码、规范排序、UTF-8、拒 binary float 进入几何/规则/hash，拒 NaN/Inf。内容 hash 建议 SHA-256(canonical bytes)，Manifest byte hash 对实际输出字节另算；不得用 Python hash；时间戳与语义 identity 隔离（§2.6、§9.6、§11.15） |
| ProposedInitialState / PreparedBaseline；`state/mutation.py`、`domain/publication.py` | normalization builder → InitializationTransaction → repository initialize | evidence/tech/coordinate/capability refs，current/target 分开，proposed geometry/occupancy/annotation/connectivity 与逐层 lifecycle 结果；PreparedPublication(kind=baseline)、expected absent head/attempt revision、sealed context。Builder/transaction 互不 import；pipeline 只串 facade。缺 lifecycle operator/comparator、join/scale 失败不得发布 baseline（§2.3、§11.8） |
| Immutable state / annotation / connectivity；`state/` | 初始化或 ECO transaction 准备，repository 发布 → read-only consumers | 单一 AuthoritativeState，fragment/region AnnotationTargetId、source-validity/conflict、exact connectivity；tech/evidence/coordinate binding baseline 后不改。ComponentId snapshot-scoped；M2 ChangeSet 记录 unchanged/merge/split/removed/created lineage。Target 独立不可变，cache 在 snapshot 外（§3–5、§11.3/11.5） |
| Candidate / mandatory scope；`planning/`、`state/mutation.py` neutral protocols | typed TargetIntent+snapshot → PlanningResult/ProposedMutationSpec → transaction → constraints query-only view | all-delta admission、lineage/base/read-set/preconditions/idempotency/apply_atomicity、deterministic alternatives、fully-ground repair。Constraints 独立扩张 E4 mandatory scope，只返回 feasible/infeasible/indeterminate/error；仅 feasible 且 final closure 完成可提交。NoChangePlanningResult 无 mutation spec（§7–9） |
| Finalization / delta；`state/mutation.py`、neutral audit DTO | transaction 内 annotation/derive/operator → final state+neutral audits → publication DTO | StateDelta/AffectedScope，preserve/frame/derive、versioned dependency DAG、dirty/pending→重算/重检。Annotation 只改 identity/relation，topology 只依几何/operator；derive 不读 ChangeSet 实现。缺闭包 full-check 或 unsupported（§2.6、§9.4、§11.8–11.9） |
| Publication / RunAttempt / RunRecord；`domain/publication.py`、`domain/results.py`，唯一发布 owner `repository/` | transaction 构造 neutral prepared siblings；pipeline 调 attempt/seal/close/finalize facade → repository composite root | stable proposed_run_id、raw descriptor digest、sealed immutable context、phase/revision/execution mode、state-head CAS、operation-scoped idempotency digest/result refs。RunRecord 冻结中立 audit，绑定 final snapshot、全 delta 与 ordered chain；repository 不 import transaction/planner/constraints（§2.1/2.6、§11.4/11.13） |
| Artifact / Validation / Reporting / PipelineResult；`domain/artifacts.py`、中立 results schema | frozen snapshot+chain+RunRecord→export→validation→reporting→repository terminal | Manifest URI/type/requiredness/size/actual-byte-hash；ValidationResult run/snapshot/chain/manifest、四维 CheckResult；ReportingResult 独立报告结果；TerminalPipelineBundle 聚合 refs/disposition。Export/validation 互不 import，reporting 只读结果；不回填 RunRecord/Manifest，不写 snapshot（§2.7、§10、§11.11–11.13） |

**正常流与 repository guards：**

1. `create_attempt` 在 parser 前创建 unsealed revision 0，使用 caller 保留的 proposed_run_id/idempotency key，绑定 starting-head CAS/raw descriptor，尚不声称 canonical context。Stage 1 获取/解析后 Stage 2 normalization 构造 proposed state。
2. 新 lineage：InitializationTransaction 完成 baseline layer lifecycle 并冻结 neutral PreparedBaseline，`initialize` 原子 create-if-absent + context seal + attempt revision advance。已有 lineage：只加载请求 snapshot 并 `seal_context`，验证 evidence/tech/coordinate binding 相容，不重复 initialize；新绑定需新 lineage或未来显式 rebase。
3. Stage 3 query-only context；Stage 4 全量 capability/semantic/extraction 检查。M1 在 close 前实际执行 toy profile 的 baseline/whole-cell exact mandatory checks；无 evaluator/context、有效 violation、indeterminate/error 都不能以“无 delta”成功关闭。Baseline lifecycle 在 initialize 前完成，其它适用检查不能晚于 no_change closure。通过后 `close_stage5` **CAS 作结论时观察的 state head**，冻结 RunRecord、空 ECO chain，state head 不变。M2 whole-intent 经 private overlay/mandatory/finalization，先冻结 deterministic state/commit ids 与 RunRecord，再一次 `publish_whole_and_close_stage5`。
4. Process-local backend 建议 single-writer mutex+single immutable composite-root CAS；同事务切换 lineage head 与 attempt revision/closure，不能先后写两个 head。先查 `(operation, run_id, idempotency_key)`：same digest 直接返回旧 refs（即使 head 已前进），different digest typed conflict；首次执行再核 phase+revision+mode。Seal twice、unsealed Stage 5、whole/partial 混用、terminal 后新 mutation 均冲突。M1 不启用 partial，不承诺断电恢复。
5. Stage5-closed 后只读 export，unique immutable/versioned core objects 完整才发布 Manifest；validation（含 report 前 audit-readiness）→reporting→`finalize_pipeline` 原子 terminal root。Run-only finalize 绑定 immutable snapshot，允许记录 superseded 而不错误卡死；accept 规则由 frozen policy决定。Latest consumer 需当场原子重验 live head，不能信任历史 `head_status_at_finalization`。Manifest 只说明 export set 完整，不是生产接收信号。

| 失败点 / variant | 必需记录与 publication 后果 | 最小组合断言（计划） |
| --- | --- | --- |
| Config/acquisition/parse/normalization，context seal 前 | `EvidenceIssue/ParseResult` 或 config result→typed StageFailure；`finalize_precontext_failure` 冻结最小 failure RunRecord 并 terminalize；无 canonical refs、envelope/post-change artifact | Run id 可追踪；故障前 state 不变；不得伪造 ValidationResult；diagnostic 仅已完成 audit |
| Baseline operator/lifecycle/initialize CAS 失败 | 不发布半 baseline；unsealed 路径同上；同 lineage create-if-absent 只一方成功 | 所有 state components 一起不存在/一起可见，竞争 loser 不 seal 成功 |
| Sealed all-delta unsupported、incomplete repair、constraint/finalizer/stale CAS failure | 丢弃私有 overlay，无 ECO envelope；冻结 no-publication failure RunRecord（可有 stable baseline ref），close 后 diagnostic/terminal | 全 component digest 与 parent 一致；baseline 已存在不等于 ECO 成功；未知 delta 不遗漏 |
| No_change 作结论后 head 已推进 | close_stage5 typed conflict，不能以旧 no_change 结论成功关闭；重读/replan 或记录失败 | state-head CAS 生效；failure close/finalize 不以 stale no_change 重试伪装成功 |
| `run_record_freeze` 失败 | 唯一可无 RunRecord 的 `Stage5Closure(run_record_freeze_failure)`；StageFailure+已完成 neutral audit refs，terminal reject，无正常 export/ValidationResult | whole-intent 不发布新 state；不虚构 success/failure RunRecord；diagnostic reporting 可选 |
| Required core export 失败/不可表示 | 保留已冻结 RunRecord 与已发布 snapshot；linked StageFailure，未完成 files 不进 success Manifest，阻止正常 validation | staging/orphan 不成为可消费 set；重跑 Stage 6 不 mutate 任何 snapshot metadata |
| Validation completed violation / 执行失败 | 分别 `fail` / `error`；独立 coverage、severity、disposition。Required tool/license/timeout/parser error→reject | golden match 不覆盖 self-consistency failure；deferred/skipped coverage=none，不汇总成 pass |
| Required reporting 失败 | ReportingResult+StageFailure，保留已有 Manifest/ValidationResult，terminal reject | 不改 ValidationResult 以隐藏报告失败；failure reporting 再失败仍 best-effort 保留原失败 |
| Stage 6 failure（包括 no_change） | 使用已有 frozen RunRecord，不重写为 pre-export failure、不回滚 baseline/ECO；pipeline frozen policy 聚合终态 | 空 chain 也区分发生阶段；所有 refs 指向同 run/snapshot/closure |
| 幂等/transition/terminal storage 异常 | 同 key异 digest 或非法 phase typed conflict；正常 terminal publication 失败不可声称 terminal accept，process-local 存储不可用只 best effort | 响应丢失同 digest 重试返回既有 refs；不重复 mutation、不伪造 durability/recovery |
| Programmer bug / unexpected infrastructure | Pipeline boundary 转 `InternalStageFailure`；不捕获 `KeyboardInterrupt/SystemExit`，crash/OOM/断电时不保证有 terminal record | Expected failure 使用 tagged variants；unexpected failure 不被吞成成功 |

M2 的 ChangeSet/CommitEvent 不在 M1 伪造实现；但中立 publication/empty-chain/no-publication variants 必须从首交就兼容后续 whole-intent。未来 partial failure 仍需保留 earlier commits 并标非生产，本包只验证 explicit-partial request 被拒绝，不启用其 API 路径。

### E7. M1 近期实现包草案（待 PM 定号与授权）

**建议一项包：M1-P1「synthetic no_change 文件闭环」**。目标是 E5 新输入经实际 Stage 1 parser→Stage 2 initialization→no_change closure→GDS/CDL/JSON/readback/人机报告/terminal result。不能以只交 DTO、mock Stage 2 snapshot 或 CLI 打印成功算整包完成。依赖为 W002 工程方案独立 review/PM 接收及首批 toy profile/手写 oracle 审查；不依赖 G1–G5 到齐，不解除 M2/M3 真实门。

| 实施内容 / owner | 允许范围与出口 | 必须同批验证 |
| --- | --- | --- |
| 工程入口、neutral schema/codec/tech | 补齐 §11 缺失的中立 owner、validated immutable config、stable ids；保持 Python ≥3.10 | runtime validation 与 strict typing 分开；typed ids/非字符串 key/Decimal/Enum/Path/sets/NaN/Inf、跨进程 digest、无 legacy import |
| 首个 fixture + Stage 1 | `tests/fixtures/` 与 `tests/support/` 新建 E5 toy raw/GDS/CDL/header/tech/limitation；显式 parser 子集、exact units 与 losslessness；generator 仅作测试支持 | Raw-normalized 同源、regen-clean 或明确 machine-readable limitation；缺 header/terminator/units/closure、多 target 冲突、geometry/CDL 能力外拒绝；至少三种输入子集拒绝例 |
| Stage 2 baseline 与 process-local repository | ProposedInitialState→InitializationTransaction；完整 state/annotation/connectivity/lifecycle；empty ECO chain 和 context bindings | Nested alias mutation、baseline finalizer/operator failure、initialize race、create/close/finalize response-loss replay、same-key different-digest、phase+mode guards、no_change head CAS |
| No_change planner + Stage 3 context | 全量 semantic/extraction-aware equality；close 前实际执行 baseline/whole-cell exact mandatory checks，缺 evaluator/context、有效 violation、indeterminate/error 均失败；不产生 resize candidate、不实现 routing/search/ECO applier | 相同文字但 extraction mismatch；source=target/count 相同但 mandatory rule 失败；未改参数/拓扑/top 差异、unsupported 混合 intent、annotation 不影响 physical edges、multi-fragment/via/cut/gate separation |
| Stage 6 完整只读闭环 | Frozen snapshot/current semantic/source preservation refs→immutable core artifacts/Manifest→self-consistency+fixture+audit-readiness→reporting→terminal；声明的 signoff deferred | GDS exact semantic readback、CDL reparse/JSON equality、独立 oracle；缺 core object、output unit overflow、validation fail/error、report failure、RunRecord freeze failure、unexpected failure 映射与 interrupt 不被吞、重复 export snapshot digest 不变 |

**工程现状（本轮只读复核）：**`layauto_v2/` 58 个 Python 文件去掉模块 docstring 后仍无实现；没有根 `tests/` 或 `.github/` workflow。现 skeleton 尚缺 domain evidence/results/artifacts/codec/publication、tech/repository/normalization/reporting、state semantic/annotation 与 initialization 等 owner；现 `export/reports.py`、`export/visualization.py` 也只是骨架，后续按架构 owner落实，不把旧目录位置当合同。`pyproject.toml` 仅声明 Python ≥3.10、依赖/extra 与 pytest 排除 legacy，尚无 strict checker/CI matrix。

本机 Python 3.11.5；pytest 9.1.1、gdstk 1.0.1、KLayout Python package 0.30.12、PyYAML 6.0.3 可定位，`pip check` 无 broken requirements。wheel/mypy/pyright 未定位；PATH 无 calibre/virtuoso/klayout 命令。建议后续选择 mypy strict，并在 CI 明确 Python 3.10/3.11 作为初始验收矩阵，约束未验证的其它组合；不提高最低 Python、不把此建议或当前 package 安装当新机/构建通过。安装构建依赖与 CI 配置属于未来包，本轮未执行。

**验证命令计划（路径/模块均待实现，不是已存在命令或本轮结果）：**

```bash
"$HOME/.virtualenvs/layauto/bin/python" -B -m pytest -p no:cacheprovider tests/contracts tests/unit tests/integration/test_m1_no_change.py -q
"$HOME/.virtualenvs/layauto/bin/python" -B -m mypy --strict layauto_v2
"$HOME/.virtualenvs/layauto/bin/python" -B -m tests.support.regenerate --fixture synthetic_static_fin_no_change_v1 --output /private/tmp/layauto-m1-regen
"$HOME/.virtualenvs/layauto/bin/python" -B -m pip wheel --no-deps --wheel-dir /private/tmp/layauto-m1-wheel .
```

近期包先落实对应 public entry/test helper，CI 在干净环境安装后运行；regen 输出与 committed fixture 按 canonical manifest 比较，构建后另检查安装/包内容/import isolation。项目尚无 CLI，本草案不擅自冻结对外 CLI 参数；组合测试通过 pipeline public facade 驱动完整文件链。M1 验收必须附代码版本、fixture/profile/schema/operator版本、命令环境、独立 oracle/失败结果、未执行范围与完整未提交身份，不能只报测试数。

**M2 剩余门：**G1–G4 真实同源 matched bundle、model/finger/cardinality/units/registries、E4 物理 operator/rules/repair/halo 证明齐备后，再形成一个真实 shrink 包并独立 review。G5 的所选 live acquisition 运行证据最迟 M3 完整覆盖前取得；不能把外部 capture 当成本系统已跑 live。当前没有 M2 日期承诺或已通过准入项。

### E8. 核验记录、未提交身份与 PM 交接

本机短期交接目录：`/private/tmp/layauto-w002-xttkvlck`。`metadata.before.json` 保存起始/交付基线及规范输入 hash，`W002.before.md` 是写入前原文；最终 `snapshot/`、`SHA256SUMS`、`full.patch`、`checks.json` 与调查原始记录用于恢复。完整源码输入可从 `2775e59` 获取；补丁只含本文件执行段。临时目录不是跨主机长期存储，换主机前由 PM 按授权转存完整材料；路径失效不能继续声称同一已核验快照。

本机附件：[调查脚本](/private/tmp/layauto-w002-xttkvlck/investigation/evidence_probe.py)、[调查结果与逐文件 hash](/private/tmp/layauto-w002-xttkvlck/investigation/evidence_probe.json)。脚本 SHA-256 为 `0f408479f3a8e76bca492ae89472f4c4f754edf67acd83f6094f3271447b42db`，结果为 `869ef663d03234f201043a0c6c0b82c0d873e8debd8c5db6bc3cf399c8e037ce`。复查命令：`"$HOME/.virtualenvs/layauto/bin/python" -B /private/tmp/layauto-w002-xttkvlck/investigation/evidence_probe.py`；stdout 应与 JSON 一致。最终快照检查脚本为同目录 `verify_and_snapshot.py`，不是产品测试或 fixture generator。

| 实际检查 | 方法 / 结果 / 限制 |
| --- | --- |
| Checkout、已有改动与版本漂移 | `pwd`、`git branch --show-current`、`git rev-parse HEAD`、`git status --short`、cached/unstaged/untracked、worktree list；启动与写入前均干净。逐项读 `156e62d..2775e59` 的三文档 diff，架构、输入、W002 要求均未变 |
| 资料/源码定向核对 | `rg --files`、`rg -n`、`sed`；source/target CDL、GDS/raw/YAML、generator、配置/importer/相关 tests/report。只读二进制 record、精确 REAL8/Fraction 与 raw/YAML 抽验另存；不执行 legacy pipeline/generator，不冒充 v2 parser/物理验证 |
| 环境和实现盘点 | 先读 local-setup，使用指定 Python `-B`、AST、importlib metadata/spec、shutil.which、`pip check`；结果见 E7。无网络安装或 tool invocation；PATH 查不到不证明其它主机无安装 |
| 文档与身份检查 | 本地链接/锚点、fence/空白、任务写入 owner、Git diff、source hashes 与 baseline+patch 重建；最终结果以同目录 `checks.json` 为准。纯文档检查不代替独立方案 review |

执行内部合同自检补齐了 baseline 适用 mandatory checks 必须实际通过才能 no_change closure 的条件及反例；同时核对 unexpected failure/interrupt 边界。该自检参与了方案准备，不当作 PM 要求的独立 reviewer 结论。

最终文档核验通过：43 个本地链接、9 个锚点、代码块闭合/空白、`git diff --check`；44 个调查/规范输入逐项与 `2775e59` 相同。完整 W002 副本与 checkout 一致，从基线原文应用 `full.patch` 重建后逐字节相同；staged/untracked 为空，仅本文件执行段有变。最终内容标识保存在外部 `SHA256SUMS` 与 `checks.json`，不要求交接文字包含自身 hash。

未执行：v2/legacy pytest、生成/修复 fixture、全量 raw-normalized parser 回归、真实 CDL model 求值/closure/LVS、真实 GDS downstream open、PDK rule/extractor/repair/body/halo 验证、Calibre/Virtuoso/live adapter/signoff、strict type check、wheel build/CI/跨环境复现。E5/E7 的正反例与命令都是计划；本轮没有产生产品 run、ArtifactManifest、ValidationResult 或产品成功状态。

**PM 接收入口：**先核对 `2775e59` 与完整快照身份、实际 diff 仅在执行段；按 E1–E4 接收事实/缺证边界，按 E5–E7 检查样本与实现包可执行性，再针对本次冻结材料安排独立 reviewer 检查 shared owner、baseline/no_change、失败流、physical/real-admission 门。执行者不代填 review/PM 结论，不改 current-work，不自行进入 M1 实现。建议接收时将“M0 工程方案可否接收”“M0 真实准入仍缺证”分列，并协调 G1–G5 持有人；需要改关键预期时附最小样本与影响交用户决定。

## Review 结论（reviewer）

### R0. 独立审查结论

**2026-09-09：E0–E8 未发现需修正的实质 findings；W002 工程调查与共享方案可交 PM 接收。** 本次是方案 review，不是 PM 验收或 M1 实现授权。M1-P1 可进入正式任务准备，但 E7 第 216 行已有的“首批 toy profile/手写 oracle 审查”依赖尚未满足：必须先交具体样本及判据，再允许依赖其物理解释的实现。样本尚未创建是已披露的关口，不能重复记为方案缺陷，也不能被本次通过消除。

**真实准入仍未满足，E2–E4 的门准确。** G1–G4 的同源设计、model/tech、matched capture、物理 operator/rule/body/halo 证据仍阻塞真实 M0 出口及相应 M2 candidate；G5 的本系统所选 `calibre` live acquisition 运行与错误路径证据最迟 M3 齐备。外部 captured bundle 不证明本系统已跑 live，Stage 6 signoff deferred 不解除 Stage 1 门。没有需要本 reviewer 另行放宽的范围或提交用户重决的关键预期。

主审 `/root` 未参与本次执行方案或 PM 接收；只读专项 `/root/toy_oracle_review` 检查 E5/E7，`/root/admission_evidence_review` 检查 E1–E4/E8。主审独立验证完整包、对照共享合同双方 owner 与失败分支并综合结论；两专项均未写仓库。仅本 reviewer 段由主审写入，执行、PM、current-work、roadmap 保留原文。

### R1. 被审版本与恢复验证

- 基线为本机 `main@2775e5945ff10353a7b35f1f997e6927668f4416`；开始审查时 staged/untracked 为空，unstaged 仅 W002、current-work、roadmap 三文件，与 PM 交接一致。已读根 AGENTS、README、协作规则、current-work、任务要求及两段 PM 交接；逐级检查路径祖先，仅根 AGENTS 适用。
- 完整待审包 `/private/tmp/layauto-w002-review-5gdqqffz`；其 `SHA256SUMS` 自身 SHA-256 为 `bcd5cb8b8638f2138fa91193df33f4f3c71b1125ce9e1ce5ddcaa07487f562a6`，`full.patch` 为 `2718abac28e204add3c610058005f38eefb64c8359f4bac2b1b20392f3e201e4`，待审 W002 为 `81020df18c92f45a9ae4dd5c56a8141ac689ba25e65318053f6e663e6f071ffc`。
- 先独立核对主 manifest 18 项、原执行 manifest 10 项、44 个 source 与 12 个 metadata 输入 hash；source/metadata 与基线逐项相同，current-work/roadmap 的现工作区差异属于已记录 PM 更新。原执行及 PM 两份 patch 分别在临时目录重建，与各自 snapshot 逐字节一致；PM 三文件 snapshot、实际 `git diff --binary HEAD` 与工作区一致。
- E0–E8 section SHA-256 为 `58029c735fc3bf3abcbeb3e4c9501444c2a6bb24e8044bd02d565c34ef9564a6`，与原执行交付相同。架构 SHA-256 为 `0a3ca52fed12af500d973deb3bddebac9a8f7f8f697769dc86827a59c07196c9`，已核对与任务指定 `6eccdff` 版本及当前基线逐字节相同。身份结果见 [intake-verification.json](/private/tmp/layauto-w002-independent-review-sat96r1m/intake-verification.json)。

### R2. Findings、依据与覆盖

**Findings：0 项实质问题，无待执行者修正或 reviewer 复核的 finding。** 以下是对待审方案及证据力度的判断；位置使用上述待审副本行号，未把未来测试计划当作通过结果。

| 范围 / 位置 | 独立检查与判断 | 架构依据 |
| --- | --- | --- |
| E0/E8，40–49、243–262 | 版本漂移、写入归属、历史附件和未执行范围可追溯；PM 接收与执行证据可分开重建。未见把源码调查写成 v2/EDA 运行结果 | [协作规则 §3、§5–6](../collaboration/rules.md#6-证据与交接) |
| E1，57–74、84–90 | CDL、GDS REAL8/XY 与 raw/YAML 抽验可复核；32/30 个矩形、FIN 12→10 及 frame/rail 变化只证明旧输入事实。Registry 缺 LI/VIA0、GATE/ACTIVE/LVT 错配及 mocked query 有源依据；旧 target 被正确排除为 fixed-frame golden | [§2.2](../architecture.md#22-stage-1输入证据获取)、[§4.8](../architecture.md#48-layer-map-与-tech-bundle)、[§12.8](../architecture.md#128-fixture-策略基于真实-query-事实构建-synthetic-cases) |
| E2/E3，94–129 | 文件文本、synthetic xref、真实 matched evidence 与 live execution 分开；模型 token/finger/cardinality/unit/registry 缺证没有转成默认值或 warning。G1–G5 消除条件对应真实门，资料搜索没有越界推断“用户没有工具” | [§1.4](../architecture.md#14-支持范围与暂不覆盖范围)、[§12.5–12.7](../architecture.md#125-配置边界哪些信息不进入-config)；roadmap R01/R05、U01 |
| E4，135–146 | Parent/candidate extractor、未改轴/器件、fully-ground repair、old∪new scope、body/frame/halo 与 finalization 消费者闭包均保留。未触 halo 需要扩张 scope 不相交且依赖不变；触 halo 要完整邻居合同/覆盖证明或完整 tiled required signoff，不能凭代表样本豁免 | [§3.6](../architecture.md#36-connectivity-state-作为拓扑解释层)、[§6.3–6.5](../architecture.md#63-固定-cell-frame-下的-resize-placement-model)、[§8.1/8.3](../architecture.md#81-constraint-engine)、[§9.4](../architecture.md#94-policy-controlled-geometry-finalization) |
| E5/E7，152–168、216–224 | Toy 的 exact geometry、CDL/query 子集、model/body/terminal operator 与手算 graph/count oracle 均列为前置输入；generator/writer golden 只作回归。Count 相等但 mandatory rule 失败/不可执行已明确拒绝；没有以 no_change 使用真实 frozen-body 豁免 | [§3.1–3.2](../architecture.md#31-几何事实源)、[§3.6](../architecture.md#36-connectivity-state-作为拓扑解释层)、[§4.5](../architecture.md#45-profile-scoped-fin--gate-representation)、[§7.1](../architecture.md#71-target-intent--diff-model)、[§10.5](../architecture.md#105-validation-model)、[§12.8](../architecture.md#128-fixture-策略基于真实-query-事实构建-synthetic-cases) |
| E6，176–187 | Evidence/results/artifacts/codec/publication 的中立落点、normalization→neutral ProposedInitialState→InitializationTransaction、唯一 repository 与 query-only constraints 均与双方依赖一致；递归 freeze、外置 cache、canonical content hash 和实际 artifact byte hash 分开。没有把骨架目录当已实现 owner | [§2.3/2.6](../architecture.md#23-stage-2事实归一化与-layout-state-构建)、[§11.2–11.4](../architecture.md#112-domain)、[§11.7–11.15](../architecture.md#117-constraints) |
| E5–E7，157、170–172、196–209、224 | 成功/失败报告与输出保真方案落实现有合同；synthetic `requires_review` 是非生产测试 policy 建议，不能覆盖 required failure 的 reject。CDL 从 current semantic+source preservation 输出，Stage 6 不补几何、不回写 RunRecord/Manifest/snapshot；无需另行确认图表或 byte 稳定性 | [§2.7](../architecture.md#27-stage-6artifact-export-与-validation)、[§10.1–10.6](../architecture.md#101-stage-6-no-mutation-boundary)、[§11.11–11.13](../architecture.md#1111-export) |
| E7，216–241 | 草案有文件链路、public facade、首交正常/错误/不变量检查和环境补齐计划，可供 PM 定正式任务；不是只交 DTO/mock snapshot。Typing/build/CI 命令标为待实现，未虚报本机安装即可复现；M2–M4 未扩大实现范围 | [§11.1](../architecture.md#111-建议-package-layout)、[§11.15](../architecture.md#1115-模块依赖方向与边界测试)；roadmap M0/M1、R01–R14/R16/R18/R20–R29 |

### R3. 发布与失败组合反例核对

下表为对 E6 第 191–212 行进行的**方案桌面推演，不是已运行的合同测试**。各反例已有对应 guard/variant，未发现需要补改的状态流。

| 触发组合 | 方案要求的可观察结果 / refs 边界 | 依据 |
| --- | --- | --- |
| 同 starting head 创建 attempt 后响应丢失；initialize 后响应丢失；两个 run 竞争 absent lineage | Stable proposed_run_id 与 operation/run/key/digest 使同请求返回旧 refs；initialize 的 state create-if-absent、seal、revision 同 root 可见，竞争仅一方成功，loser 不留下半 baseline | §2.1、§2.3、§2.6、§11.4/11.8 |
| Head/revision 已前进后 replay close/finalize；同 key 换 digest；再次 seal、unsealed close、未 close finalize、terminal 后新 mutation、whole/partial 混用 | 同 digest 先命中幂等记录并返回原 refs；异 digest 与首次非法 transition typed conflict。幂等记录与 composite-root 切换同原子域，不能先通过旧 revision 检查再决定 replay | §2.6，尤其 214–230 行 |
| Semantic/extraction 相同但 baseline mandatory rule fail、context/evaluator 缺失；或检查后 head 推进 | 前者不能正常 no_change closure；后者 close 的 state-head CAS conflict，须 replan 或 failure close。Baseline lifecycle 已成功不等于其余适用检查通过；正常 no_change 保留当前 snapshot、空 ECO chain、无 empty commit | §2.3/2.6–2.7、§7.1、§8.1；roadmap R16/R21 |
| Config/acquisition/parse/normalization 或 baseline lifecycle/CAS 在 seal 前失败 | Unsealed attempt 冻结最小 failure RunRecord 和 completed audit/StageFailure；canonical refs 缺省，无 ECO/post-change artifact。原 state 保持，不能虚构 Stage 6 ValidationResult | §2.1、§2.6–2.7、§11.13 |
| Seal 后 all-delta/constraint/finalizer/stale failure，尚无 ECO envelope | 冻结 no-publication failure RunRecord；stable snapshot/planning/constraint refs 仅按到达阶段可选；只有 diagnostic report，不导出失败 candidate 几何。已发布 baseline 保留 | §2.7、§9.3、§10、§11.11 |
| `run_record_freeze` 本身失败 | 唯一允许无 RunRecord 的 Stage5Closure variant；必须 StageFailure+completed neutral audits，optional earlier chain；whole-intent 不发布新 state，terminal reject，不正常 export/validation，diagnostic 可选 | §2.6–2.7、§11.11/11.13 |
| Required core export 失败；validation 完成后违例或执行 error；required reporting 失败 | Export 不发布完整 success Manifest、不正常 validation；check 的 fail/error 与 coverage/severity/disposition 分开；report failure 有独立 ReportingResult/StageFailure。保留已有 RunRecord、snapshot 和已完成 refs，required failure 阻止 acceptance | §2.7、§10.2/10.5、§11.11–11.13 |
| No_change 在 Stage 6 失败；finalize 时 snapshot 已 superseded；terminal storage 不可用 | 不因空 chain 改写为 pre-export failure，不回滚 baseline。Run-only finalize 可绑定旧 immutable snapshot并记录 head observation；latest consumer 当场原子重验。存储失败不可声称 terminal accept，process-local 只 best effort | §2.6–2.7、§10.1、§11.13 |
| Unexpected bug/infrastructure failure；KeyboardInterrupt/SystemExit | Pipeline boundary 将前者记为 InternalStageFailure；不吞后两者；不声称 crash/OOM/断电时必有 terminal record。M1 显式拒绝 partial request，不伪造 M2 ChangeSet/CommitEvent | §11.6/11.13；§2.6 process-local 边界 |

### R4. M1 前置关口与覆盖限制

PM 准备正式 M1 任务时，应把 E7 已有依赖落成可交接的先后关口：**先审具体 toy spec/profile/oracle，后做依赖它的 parser、状态、extractor 与规则闭环。** 中立合同和环境准备可按后续任务授权推进；本轮没有启动它们。样本关口至少应能独立核对：

1. Exact 坐标/图、原始 integer ticks、REAL8/nominal unit binding、逐 record capability；FIN∩active∩channel 的逐器件 qualified-crossing 表证明 5/7、单指、一对一及无归并，不能只写目标计数。
2. S/D、gate、body、conductor、via/cut 的独立 topology/terminal graph；逐条 toy rule 的阈值、适用集合、pass/violation/不可执行期望。Synthetic body 使用自身完整 operator，不借真实 baseline LVS 的冻结豁免；不要求把所有 production rule 塞进 toy，但适用集合不能为空或漏掉实际消费者。
3. GDS/CDL/raw/header/normalized/profile/operator/spec 版本与 hash、空或非空 closure、machine-readable limitation；手写期望和独立 reader 不复用 runtime extractor 的输出作为答案。Generator 的 regen-clean/限制与 parser 同源检查另行保留，不能取代 oracle。
4. 冻结 synthetic policy 与最小报告实例，正常工程链可为 `requires_review`，required violation/error 仍 reject；正式任务包含 E7 的首交错误路径、strict typing、构建/干净环境及支持解释器检查，不延至 M4 才首次验证。

**本次已执行的核验：**使用 `$HOME/.virtualenvs/layauto/bin/python`（3.11.5）、`-B`、Git 只读命令及独立 SHA-256/临时 patch 重建；只读专项完整阅读原 `evidence_probe.py` 后重跑，stdout 与包内 JSON 逐字节一致，SHA-256 仍为 `869ef663d03234f201043a0c6c0b82c0d873e8debd8c5db6bc3cf399c8e037ce`。该 probe 只盘点旧文件，不是 v2 importer、UnitScaleContract 或物理验证。执行附件的 pip/package/PATH 结果作为该版本的调查记录审查，本 reviewer 未重跑 pip、安装或扫描其它主机；不把 PATH 无 binary 推为全局不可用。

**未覆盖/未执行：**具体 toy 数值/几何正确性、oracle 实际独立性、runtime schema/codec/repository 的行为、v2/legacy pytest、fixture generation/修复、完整 parser 回归、strict typing、wheel/CI、真实 model/extraction/rule/body/halo、Calibre/Virtuoso/live acquisition/signoff、生产 downstream open/syntax、durability/跨环境复现。未重做全量 legacy 或路线图审计。上述限制不由“0 findings”转为通过；没有产品 run、Manifest、ValidationResult 或生产 acceptance 证据。

### R5. 本轮交付快照与下一步

更新后的完整本机包为 `/private/tmp/layauto-w002-independent-review-sat96r1m`：`snapshot/` 保存 W002/current-work/roadmap 三文件全文，`full.patch` 相对 `2775e59` 重建全部未提交内容；`reviewer.patch` 单独绑定本轮 reviewer 增补；`staged.patch`、`unstaged.patch`、`untracked.json` 记录三个层次。`reviewed-input/` 完整复制原 PM 待审包及执行附件，不覆盖历史证据；[checks.json](/private/tmp/layauto-w002-independent-review-sat96r1m/checks.json) 与 [SHA256SUMS](/private/tmp/layauto-w002-independent-review-sat96r1m/SHA256SUMS) 保存最终核验、文件/patch 身份和范围。

写入后复核仅 reviewer 段变化，E0–E8、要求/PM 原文及另两文档保持；重新核对所有 manifest、三文件完整 patch 与 reviewer-only patch 重建、链接/锚点/空白和 `git diff --check`，具体结果见 checks。最终 hash 留在外部 manifest，不追求本段包含自身 hash。恢复时先校验 manifest，再以基线+full.patch 在独立临时目录重建比较；历史/本轮一次性快照生成脚本均不应作为恢复命令重跑。临时目录仅供短期同机交接，跨主机须先转存完整包。

下一步由 PM 核对本 review 与版本后决定 W002 工程出口验收，并在正式 M1 任务落实 R4 关口；真实出口继续补 G1–G5。本 reviewer 不推进任务阶段或代写 PM 状态；本轮无方案修改、实现、commit/push。

## PM 验收与交接（PM）

### Git 集成（2026-09-09）

用户本轮授权现有改动 commit/push。已验收三文件与 `/private/tmp/layauto-w002-accepted-xvwblftq` 逐字节一致后提交为 `f141af99525c48819aa97416e8cb81e9091d6c0e`（`docs: accept reviewed W002 input admission plan`），已 push 并核对 GitHub main hash。执行 E0–E8、review R0–R5 原文保持；产品/架构未变，未运行产品测试。下方“未提交”描述均对应当时验收快照；本次仅更新 Git 恢复状态。

仓库 Git 版本含可读方案/review/验收正文；历史临时调查、patch 与校验附件未随 Git 上传。附件级复核仍需相应原包，不能把 GitHub 页面视为全部本机证据均可访问。

### 最终验收与下一步（2026-09-09）

**接收 W002 的调查与工程方案文档，阶段为已验收；M0 真实准入出口继续未满足。** 独立 review R0–R5 为 0 项实质 findings，无待修复或复核 finding。PM 对照任务六项验收要求、E1–E8、review 覆盖与架构 §1.4、§2、§11、§12.8 核对：来源/准入/两类 acquisition/物理依赖/闭环方案/近期包均有对应交付；缺真实材料按任务既有许可交付缺项和工程方案，不构成真实准入成功。

本次接收基线 `2775e5945ff10353a7b35f1f997e6927668f4416`；独立 review 后 W002 SHA-256 为 `10a3afbc509105ff615acb8b571e15cfede1179b4f5f6acffcc3d5e9d2c266b9`，review 包 `SHA256SUMS` 自身为 `c941043569d624659d3e4026cedad9e90df0ae2aa430c20c2eb78ab2f181b2ae`，完整补丁为 `4d544eacf8710284bd85a3e845820e859ae8dd0d30cdecb5d1ae5e7f8fcf081e`。已核对完整包、原待审身份及 reviewer-only 改动；执行和 reviewer 原文保持不变，reviewer section SHA-256 为 `d04ed2717cb09c5b09a38e28b709dd33c2945216250f97a9a37f29ae1c760a7d`。

本任务完成的是开工前的调查与方案准备：旧 demo 可作参考，但旧 target 重画 FIN/frame，不能作 fixed-frame 正确答案。M1 正式实施前仍须先审具体 toy spec/profile/独立 oracle；这是 E7 原有、R4 细化的前置关口，不是未修 finding，也不因 W002 验收自动通过。

**推荐下一任务先交“最小样本与独立正确性判据”**，内容按 R4：精确坐标/单位、5/7 qualified crossings 表、端子/连通图、适用规则及失败反例、同源输入记录和限制、最小报告样张。由执行者准备、独立 reviewer 验证，PM 接收后再推进依赖这些物理解释的 M1 no_change 文件闭环实现。中立合同/环境准备可在后续明确授权范围内安排，本轮没有创建或启动实现任务。

可观察的 M1 目标是同一个小单元 source/target 均为 5/7：实际读取 GDS/CDL/raw query，确认几何与语义满足目标且适用检查通过，输出一致 GDS/CDL/JSON/报告和检查结果，空 ECO chain；换入单位冲突、连通错误或规则违例时必须按失败语义拒绝。实现和实际测试尚未运行。

真实材料并行协调 E3 G1–G5 的持有人和可访问位置；G1–G4 阻塞真实 M2，G5 最迟 M3，不能用 synthetic 成功替代。不需要重新决定单指/一对一/无归并范围；新的关键使用预期按原规则带样本上报。

本次 PM 只更新任务阶段/本验收段及 current-work/roadmap 状态。新完整接收包 `/private/tmp/layauto-w002-accepted-xvwblftq` 保存 `snapshot/`、相对基线的 `full.patch`、接收 `receipt.json`、`checks.json`/`SHA256SUMS` 与独立 review 包完整副本；下方旧接收与审查交接均为历史记录。未 commit/push，未运行产品/legacy/EDA/构建/CI。跨主机先按授权转存完整未提交包；仅远端 main 不含本次交付。

### 接收事实与限制（独立 review 前记录）

2026-09-09 先前 PM 接收 W001 后将本任务转为可执行，要求随 `main@8482b68` 保存；用户随后派发执行会话。本次用户通知执行结束，PM 已核对实际交付，**阶段转为待 review，仅接收待审材料，不代表工程方案或真实准入已验收**。

- 接收时 `main@2775e5945ff10353a7b35f1f997e6927668f4416`，只有本文件执行段未提交修改，staged/untracked 为空；执行者未改要求、reviewer 或原 PM 段。没有 runtime、fixture、架构或环境配置变更。
- 原执行快照 W002 SHA-256：`e8fcb8900cbf09fa03b76423ff4fb70ee0cf678a22193b5f9b060c0132d6eb19`；`full.patch`：`a91e151ac469acf30bdc7d7a2d685b27d4f2f5a82e0447fd4c0d9700dfe81584`；`SHA256SUMS` 自身：`cdb2660a74dd67a7fd07c01aaae5ba22427a1bf4179a5079119fe6220aa20a9e`。核对 10 个附件、44 个源码/规范输入及 12 个 metadata 输入 hash；补丁与实际 diff 一致并可重建原交付。只读 probe 重跑 stdout 与调查 JSON 逐字节一致。
- E1–E4 提供来源盘点、准入矩阵、G1–G6 缺项和物理依赖；E5–E7 提供样本说明、共享合同/失败流与 M1-P1 草案，足以开展针对性方案审查。抽验旧 target 重建 FIN/frame、exact unit、registry 错配、mocked query 的源事实，并核对 baseline/no_change、repository、terminal 与 Stage 1/6 的架构出处。PM 与只读专项协助 `/root/w002_evidence_intake` 属接收检查，不能替代独立 reviewer。
- **M0 工程出口待 review/验收；M0 真实准入出口未满足。** E5 的 toy geometry/model/operator/手写 oracle 仍未创建或审查；E7 是实现包草案及命令计划，不是运行结果。M1 实施前须明确首批样本/合同审查门和任务范围，不能把 W002 文档通过当作这些门已经通过。
- 没有新增产品范围决议。E3 G1–G4 缺证继续阻塞真实 M2；G5 的本系统 live acquisition 证据最迟 M3 满足。G6 只在具体样本暴露新关键消费预期时交用户决定。未执行产品/legacy/EDA/构建/CI 验证；本次未 commit/push。

### 待审版本与恢复（历史）

本次 PM 更新仅涉及本文件 PM 字段/段落、[current-work](../current-work.md) 与 [roadmap](../roadmap.md) 的恢复入口。**E0–E8 保持原字节**，section SHA-256 为 `58029c735fc3bf3abcbeb3e4c9501444c2a6bb24e8044bd02d565c34ef9564a6`（执行 heading 后至 reviewer heading 前，包含原空行）。Reviewer 段仍为未执行，PM 不代写 findings。

完整待审包：`/private/tmp/layauto-w002-review-5gdqqffz`。`snapshot/` 保存上述三文件完整副本；`full.patch` 相对 `2775e59` 可重建全部未提交修改；`SHA256SUMS`/`checks.json` 保存最终身份与文档核验；`execution-evidence/` 完整保留 E8 附件，`receipt.json` 绑定原执行版本。Reviewer 先核对 manifest/hash、patch、工作区和规范输入；PM 状态变化须与执行证据区分。不要重跑原交付 `verify_and_snapshot.py` 覆盖历史材料。

默认同一 checkout 串行 review；临时目录仅用于短期同机交接。其它主机或 GitHub 会话需先取得完整未提交包及调查附件，仅 `main@2775e59` 没有本次交付。包失效/内容漂移先报告身份缺口，不沿用旧结论。Reviewer 写入后另留完整新快照与 hash，不覆盖本待审包。

### 独立方案 review 交接（历史，已完成）

以 review 角色检查 E0–E8、实际 diff 与附件；读取根 AGENTS、协作规则、任务要求及相关架构原文。范围是 W002 方案正确性与近期包可执行性，不重做全局路线图或全量 legacy 审计。重点：

1. **输入与真实准入（E1–E4；架构 §1.4、§4–5、§12）。** 定向核对 GDS/REAL8、raw/YAML 抽验与 registry 不匹配的证据力度；旧 target 不作 fixed-frame golden。核对 synthetic/tool-captured/matched/live 分界及 G1–G5 是否足够消除对应门；缺 required operator/rule/body/halo 条件必须拒绝。Stage 6 signoff 延期不免除 Stage 1 acquisition。
2. **Toy 闭环和独立判据（E5/E7；§2.2–2.4、§3–5、§10.5、§12.8）。** 几何/CDL/query 子集、toy extraction/body/terminal/rule 定义是否有可落实输入、拒绝条件与独立 oracle；判断 M1-P1 是否需先交具体坐标/图/计数表和 profile，再允许依赖它的实现。不要把样本方案当样本已审，不让 generator/parser 自证或以 no_change 省掉适用 mandatory checks。
3. **共享 owner 与发布（E6；§2.1/2.3/2.6、§11）。** 核对中立 DTO 的双方 owner、recursive freeze、canonical codec、InitializationTransaction/唯一 repository；以组合反例检查 create/initialize/close/finalize 的 head/revision/phase/mode、响应丢失 replay 和异 digest 冲突。No_change 须完成适用检查并 CAS 对应 head，空 ECO chain，baseline 不是 ECO。
4. **失败与产物（E5–E7；§2.7、§10、§11.11–11.13）。** 逐分支核对 pre-context、sealed no-publication、run_record_freeze、export/validation/reporting/terminal 失败的必需/可选 refs、无修改或已发布状态保留与 disposition；Stage 6 不回写。检查 synthetic `requires_review` 建议、CDL 保真和报告提纲是否落实既定合同，或含需用户决定的新关键预期。
5. **近期包与依赖（E7；roadmap M0/M1、R01–R14/R16/R21–R29）。** 评估能否在窄输入上贯通文件→状态→产物，正反例与 typing/build/环境条件是否足以分派；必要时建议范围内先后关口，不删不变量或把首交失败检查推到 M4。M2–M4 保留依赖，不展开实现。

只写本文件 reviewer 段，保留执行/PM 内容，不实现、不修 fixture、不安装 EDA、不 commit/push。Findings 给严重性、准确位置、架构出处、触发样例/影响和修正方向；无 findings 则写覆盖及限制。分别回答“工程方案是否可接收、M1 前还需什么”和“真实准入未满足的门是否准确”；绑定待审身份，另留写入后快照。后续顺序为必要修复→reviewer 复核→PM 验收→正式准备 M1 任务。本轮未自动创建或发送审查任务。
