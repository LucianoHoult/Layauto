# W007 — 语义身份与目标归一化

把已经读入的CDL和query证据整理成可供后续状态构建使用的器件、网络和目标差异：明确“当前有哪些器件、各端子连到哪里、目标要求改变什么”，保留身份与原始证据的对应关系。

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| ID / 目标 | W007；交付Stage2首个纯归一化组件：source semantic draft、独立immutable target/typed differences、query identity关联及annotation seeds |
| 里程碑 / 依赖 | M1第三个产品切片；依赖W003/W004已验收synthetic输入、W005读取组件及W006运行审计。W006已通过[PR #60](https://github.com/LucianoHoult/Layauto/pull/60)合入main `221492eb72e10cf2e46f1d9c76cb992087806a97`，接收见[W006 PM4](W006-precontext-run-audit.md#pm4-integration-20261102)。本任务不是完整Stage2或M1 |
| 授权依据 / 阶段 | 用户2026-11-02派发独立执行任务并交回实现与review结果。**待验收：分支技术接收通过，剩余必须修正项0；main集成及组合验证后再作最终验收。** 依据见[PM1](#pm1-technical-receipt-20261102) |
| 恢复位置 | `codex/w007-semantic-identity-normalization`；实现交付 `5e874e5e60bb74f58903080bf079796061454962`，产品/测试 `0f879f01acbeac033173d0b6c6257c376bb9272a`。从包含PM1及current-work更新的本分支提交继续，完整SHA见Git/回复；main仍为上述W006集成版本。临时环境不假定跨session存在 |
| 允许修改 | 新建职责明确的`layauto_v2/normalization/`；`domain/circuit.py`、`intent.py`、`identifiers.py`及必要中立DTO/codec；必要的纯identity/seed构建模块；相应unit/contracts/真实读取组合测试、typing/build配置、README与本任务附件。内部类型/文件组织留执行方案，不为目录名强造对象 |
| 非目标 | 不实现geometry store、coordinate/occupancy、spatial overlay、physical connectivity/body/extraction/mandatory规则、完整ProposedInitialState、initialize/seal或state publication；不扩展W006正式pipeline/repository协议，不产生StageFailure终结链、baseline、no_change、ECO或导出；不扩外部输入格式、真实PDK/EDA或方言，不改已验收fixture/答案 |
| 架构依据 | 上述main的[architecture](../architecture.md) §1.4、§2.2–2.3、§3.2–3.3、§5.3–5.4、§7.1/7.3/7.5、§11.2/11.5/11.10/11.13–11.15；读原文及[W002 E6/E7/R4](W002-first-input-admission.md)、[W003合同](W003/contracts.md)、[W005拆分](W005-input-reading-binding.md#pm已确定的任务拆分)、W006 InputsReady与其[接口方案](W006/interface-plan.md) |
| 分工 / 阻塞 | 一名执行者集成；未参与该变更者独立检查接口和最终代码；PM接收并维护阶段。无新的用户预期待决；现有synthetic profile足够本切片，真实准入缺项仍保留 |

### 行为要求与边界

1. **只消费已经捕获的证据。** 定义中立、冻结且验证过的内部输入合同，从W005成功ParseResult的value/completed/sources等已有事实构造；W006调用方可用InputsReady及repository读回的Parse/evidence构造同一输入。归一化组件不import pipeline、tooling、repository或transactions，不重新读取磁盘，不调用parser另读一份文件，不加载spec/oracle/expected/records样张充当输入。保持来源hash、字段定位、profile和同次输入关联；不把任意拼装的不同run/source证据默认为同源。适配入口及必需字段由接口方案明确，不新增用户必须提供的manifest。
2. **Source语义完整、target独立。** 从source CDL形成后续初始化用的不可变语义草稿：cell/subckt、有序端口、globals、Device/Net identities、模型、按声明terminal order解释的端子和完整net membership、全部参数轴及preservation refs。目标CDL单独形成immutable target reference，不与current共享可写alias，不把target替换source。当前组件产物不是已提交CurrentCircuitState或AuthoritativeState。
3. **参数和比较服从profile。** 使用选定model的parameter_axes/terminal_order、CDL大小写/字面量/单位规则，不凭NFIN/NF/M名字猜轴，不默认参数、不转float或截断。保留全部canonical轴及exact值、token/lexeme和字段来源。语义比较按声明comparator忽略无语义的空白/注释/设备行与参数排列，保留端口/端子等有意义的顺序；来源字节hash不同不等于语义不同，语义相同也不允许丢失不同来源。
4. **身份来自CDL与xref，几何不混入语义。** 建立cell-scoped、可重复的semantic DeviceId/NetId；layout instance、LVS index/net name是query-run scoped backlink，不直接作为canonical semantic id。iXref/nXref/NET NAMES关联至source semantic对象，检查所选profile的完整性、缺失/歧义/冲突和cardinality；不按名字相似、顺序或fixture常量回退。形成独立identity/annotation seed数据，保留device/net query的exact polygon、kind/quality及来源以供未来spatial overlay消费；不得往Device/Net塞bbox、fin tracks、segments/vias或物理edge。此处identity关联不证明实际shape覆盖、连通、器件提取或body完整。
5. **Source准入与target差异分开。** Source按已验收profile落实single-finger、multiplicity及one-to-one/no-device-reduction要求；C08/C09/C10分别产生既有意义的定位typed错误。S/D swap按显式model/profile policy处理，当前`sd_symmetry=false`不能偷换端子或抹去swap evidence。Target中仍属已支持语法/语义的变化须完整保存，不因后续planner不支持而丢弃；typed差异至少覆盖被当前输入subset表达的cell/有序端口、器件增删、模型、端子/网络成员关系及每个参数轴，保留before/after、稳定operand/delta identity、scope、来源与所需capability/未支持义务，字段按§7.1细化。不得只筛NFIN或只处理第一个delta。
6. **组件成功不等于run成功。** 正常fixture的source与target语义一致只表示当前比较无差异，不产生NoChangePlanningResult；仍须后续geometry/extraction/mandatory checks及状态闭合。C13的L=4n→5n必须作为非空target差异保存，不能因NFIN相同视为no_change，也不能提前走W006 pre-context terminal拒绝；既有`sealed_no_publication`的UnsupportedTargetAxis/规划拒绝归后续完整组合。C08/09/10的预期pre-context拒绝本轮只实现对应组件错误，实际StageFailure/terminal在后续接入时验证。B端语义网名不证明body几何连接；D1=A及真实证据标记保持。
7. **结果、错误与身份可验证。** 内部API有runtime discriminated result/schema、typed ids、recursive immutability、versioned wire roundtrip和稳定canonical digest；集合与有序字段按语义区别处理，Python hash或内存地址不作身份。预期输入/准入/关联错误返回定位的typed normalization issue，保留已完成事实及来源；不伪装ParseResult、Stage6 ValidationResult或terminal。意外Exception与KeyboardInterrupt/SystemExit按纯组件边界传播，不吞掉。原W005/W006入口行为、异常及IPMR-01保护保持。

### 验收清单

| ID | 条件 → 可观察结果 | 正确性依据与验证 |
| --- | --- | --- |
| A1 实际输入链 | 已验收fixture分别经W005读取、W006 InputsReady/readback → 同一归一化组件得到等价语义产物 | 必须真实运行组件；禁用归一化期间文件IO证明不重读；W006 attempt/refs不被组件推进或改写。不得直接加载expected输出 |
| A2 语义与exact值 | 正常source/target的完整器件、端口、模型、端子、net membership、每个参数轴可核对且互相独立 | 按真实CDL、tech与手写独立判据逐项验证，包括NF/M/L/W/VT；format-only变化比较相等，ordered pin/terminal变化有意义；不可变及source backlink保真 |
| A3 canonical身份/seed | Q17/Q93及run-scoped net keys通过xref关联MN0/MP0和语义net，不按fixture常量或名字猜测 | 第二套合法重命名/重排行为，缺失/未知/冲突xref反例；保留query exact/kind/quality/provenance，不作spatial/physical成功结论 |
| A4 source子集准入 | 真实C08/C09/C10经已有reader后，分别得到UnsupportedDeviceCardinality/UnsupportedFingerCount/UnsupportedDeviceReduction等已验收含义的定位组件错误 | 在临时副本应用原变体与正确绑定，不能用提前hash/cache错误代替本项准入。保持原样张pre-context的后续归属；支持边界与swap/缺失映射反例由profile判据验证 |
| A5 target完整性与阶段 | source=target仅语义相等；C13保留L轴差异；同NFIN但其他轴/端子/模型变化不能消失 | 手工独立before/after判据；覆盖多个delta、结构性变化及未支持义务，当前source不被target修改。已支持parser能表达的target变化不能因resize=false变成空diff；不输出baseline/no_change/terminal |
| A6 DTO/错误/依赖 | 公共输入/结果/identity可严格验证、wire roundtrip、跨hash-seed digest稳定；invalid组合拒绝 | alias mutation、错误schema/ref/来源混用、expected typed issue及unexpected Exception/interrupt反例；中立合同无IO，组件无repository/transaction/runtime归档依赖 |
| A7 工程与保护 | 新组件从安装包可用，已验收读取/运行审计仍通过 | 新unit/contracts/真实读取组合、W005/W006完整回归（含IPMR-01）、strict typing覆盖新模块；Python3.10及开发解释器实际验证、新sdist/wheel、干净安装和源码外正常/拒绝/target差异smoke。绑定最终版本，准确记录矩阵及未执行项 |

允许为测试在临时目录构造有独立手工预期的派生输入、显式重绑source/header以隔离目标条件；不得改已验收fixture、答案或历史报告来迁就实现。现有scope内接口/代码问题自主修正；若必须改变输入解释、xref容错、失败阶段、profile能力或对外格式，准备具体反例与影响交PM/用户，不静默新增关键语义。

### 后续组合归属（不得视为本轮已完成）

| 后续能力 | 保留义务 |
| --- | --- |
| Stage2几何与物理构建 | semantic-lossless geometry、exact坐标、多occupant occupancy、spatial annotation、exact connectivity、body/extraction、逐层lifecycle与适用mandatory checks；source semantic draft与target独立接入完整ProposedInitialState，expected JSON不作为预制snapshot |
| Stage2正式运行接入与基线发布 | W006运行链继续归一化并记录同run审计；pre-context错误真实终结。新lineage initialize/create-if-absent+seal、已有lineage load+seal、state-head/attempt原子CAS/幂等及中断/失败合同；组件不绕过InitializationTransaction |
| 无变化判断与Stage6完整M1 | Stage3/4全量目标capability及semantic+extraction-aware检查、whole-cell mandatory checks、no_change closure/CAS；C13等sealed失败；实际只读GDS/CDL/JSON导出、独立读回、人机报告与最终terminal |
| M2及真实准入 | 首个真实shrink及repair依赖M1和真实profile G1–G4；G5最迟M3。本任务不因synthetic语义通过消除真实门或扩展resize能力 |

## 方案与决定（执行准备，PM 接收）

执行起步先调查现有W005 evidence shape、W006 readback及domain骨架，定向查看legacy纯语义比较/名称映射候选；说明复用/改造/拒绝理由，不引入归档runtime依赖。

形成一页内部输入/结果/typed identity/target-diff/seed API与错误边界方案，明确来源校验、semantic equality与record digest的区别、W005和W006两条适配路径、source准入与target后续义务分离。先请未参与方案设计者独立review；既定范围内修正后直接实现，不把普通内部设计变成新的用户审批门。当前没有新的必需输入或使用预期待决。

## 执行结果（执行）

### E1. 恢复、调查与内部方案（2026-11-02，执行）

实际恢复于 `/workspace/Layauto`：原本地 `work@4db3aa81d6f01496a680bdcb264afe99cd80f3f3`，staged/unstaged/untracked均为空；远端W007为指定 `64b4ad2f77c017affade69374510dc12e534bc07`，main为 `221492eb72e10cf2e46f1d9c76cb992087806a97`。fetch后从交接提交建立当前W007分支，保留原work分支；提交身份设为项目已有 `LucianoHoult <LucianoHoult@users.noreply.github.com>`，未force push。已读根/协作/环境规则及任务引用原文，无局部AGENTS。

调查确定W005成功value与completed、SourceFile可构成中立输入；W006用现有domain readback records适配，不扩pipeline/repository。复用v2 FrozenMap、Fraction/canonical codec与已捕获evidence。legacy `io_adapters/cdl_parser.py::diff_cdl`忽略结构/model/terminal且parser用float/默认值，不迁移；legacy query显式xref关联模式已由W005更严格实现，不再引入归档依赖。

具体[内部方案](W007/interface-plan.md)已由未参与设计的reviewer审查，IR-01/02修正及复核由reviewer记录于[接口review](W007/interface-review.md)；方案/review提交为`8a2cdf5`。两条修正分别保留W005合法路径alias行为，以及要求聚合DTO完整引用一致性。原范围内直接进入实现，未新增用户审批。

开发解释器为Python3.12.14，另准备Python3.10.22。实施前基线实际为405项通过及strict mypy 21文件通过；这是原W005/W006基线，不是W007最终验证。[环境记录](W007/verification/environment.json)保留版本及依赖。产品与独立手工判据测试在分离worktree开发，由执行者集成。后续最终测试、代码review与交接证据在此追加；执行者不写reviewer或PM结论。

### E2. 实现、最终验证与交付（2026-11-02，执行）

最终产品与测试提交为 **`0f879f01acbeac033173d0b6c6257c376bb9272a`**；其后的本次交付只追加执行/review文档及证据，不改变被测代码。入口为 `layauto_v2.normalization.from_parse_result`、`from_inputs_ready` 和 `normalize`；使用示例见[README](../../README.md#semantic-normalization-component)。domain保留typed IDs、完整source/target语义、typed differences及纯source-location转换；normalization持有中立输入/结果、聚合校验、codec、identity/seeds与组件组合。

实现保存全部cell/有序ports/globals、器件模型与有序端子、net membership和六个参数轴；exact Fraction/token、单位、lexeme及字段来源均保留。source与target独立，结构/模型/端子/全部参数差异逐项保留before/after、稳定ID、来源与后续capability义务。query-run身份只作backlink，exact polygon/quality/kind等留在独立seeds。C08/C09/C10分别返回定位组件错误；C13的4n→5n是非空channel_length目标差异，不产生pre-context terminal。无差异只代表所选comparator下语义相等。

按独立review反例补齐同capture字段归属、完整记录覆盖、net来源、集合canonical顺序、profile owner定位及公开success准入守卫；保留reader对tab-X的原行为。FR3的requests来源绑定按[独立补审方案](W007/interface-review.md#fr3-捕获请求文档锚定补审)实现：只对同一捕获SourceFile.data复用已有安全JSON/YAML decoder和所选limits，不读取路径或扩大输入语法。专属合同移至normalization以保持domain依赖方向；纯SourceRef转换最终单列 `domain/source_location.py`，既有evidence实现未改。nested wire对decoder意外异常的传播已修复并纳入回归。原findings、修正前输出与reviewer关闭依据均保存在[代码review](W007/code-review.md)，执行者不代写其结论。

| 判据 | 实际完成与可访问证据 |
| --- | --- |
| A1 | 真实W005 reader及W006 InputsReady/repository readback适配同一输入；禁IO、alias、readback关联拒绝、attempt/refs/terminal不推进见[输入链测试](../../tests/contracts/test_w007_inputs.py) |
| A2 | 按CDL/tech独立手写的器件、端口、端子、net和六轴exact期望，全部top、format-only重排及source/target独立性；手工判据见[w007_cases.py](../../tests/contracts/w007_cases.py) |
| A3 | 第二套合法query重命名/重排、缺失/未知/冲突xref、来源成组交换反例及完整identity/seeds；不以名字相似或fixture常量作runtime回退 |
| A4 | 临时复制/重绑真实C08/C09/C10，经reader成功后才到source组件准入；另覆盖M、swap及非法public success重标 |
| A5 | C13完整L差异、全部轴、多delta、cell/device/net结构及ordered ports/terminals/model变化；target义务不因source限制或resize=false丢失 |
| A6 | [合同测试](../../tests/contracts/test_w007_contracts.py)覆盖递归不可变、schema/typed ref/聚合引用、wire roundtrip、跨hash-seed digest、混源拒绝及意外Exception/interrupt同对象传播 |
| A7 | 原405项与新增148项组成最终553项；双解释器全部回归、strict typing、新包/干净安装/源码外smoke结果如下；包括W005/W006与IPMR-01 |

实际环境为Linux x86_64；开发解释器 `/workspace/.venvs/layauto/bin/python` **3.12.14**，最低版本环境 `/workspace/work/w007-venv310/bin/python` **3.10.22**。fixture为 `tests/fixtures/w003_m1`，profile为 `synthetic_static_fin_context_no_change_v2`；只在临时副本构造派生输入并重绑既有header，未修改已验收输入、答案、历史报告。完整环境/依赖、每条实际argv/cwd/UTC/耗时/退出码与原始输出在[最终验证索引](W007/verification/README.md)和[汇总回执](W007/verification/receipt.json)。

| 实际检查 | 结果 |
| --- | --- |
| 两解释器各 `python -B -m pytest -p no:cacheprovider tests/unit tests/contracts -q` | 3.12：**553 passed / 256.34s**；3.10：**553 passed / 342.94s** |
| 两解释器各 `python -B -m mypy --cache-dir <外部cache>` | 各 **33 source files，无问题**，strict配置覆盖新模块 |
| 开发解释器 `python -B -m build --outdir /workspace/work/w007-final-artifacts` | 新sdist与wheel构建成功；每包83个runtime文件逐字节匹配被测清单 |
| 两套fresh venv安装该wheel，并从 `/workspace/work/w007-final-smoke` 执行独立脚本 | 均exit 0；正常语义相等、C08拒绝、C13 exact差异/义务、W006 readback及wire；载入对应site-packages |
| 开发/最低版本和两套wheel环境 `python -m pip check` | 四次均exit 0，无依赖破损 |

最终[源码清单](W007/verification/source-manifest.json)覆盖101项runtime/tests/config，content SHA-256为 `f051ae0fecab66a1104e0aa609cc8450c1cf480a99384113027dc5a6f40976a9`；[包身份](W007/verification/package-identity.json)记录清单文件SHA及wheel `626fcf795a3bc00f672eee0e5f869e10e4957a6f1e02145e6c9657eb0c8ff7e9`、sdist `47669e27dc044d3e5e9ec76759a2118479bba796f422cedc5e1f5ca4f471b7ea`。实际包与可移植smoke脚本随Git交付。旧6712cbc候选的530项验证另存历史目录，明确不作为最终修后通过依据。[14处保护路径](W007/verification/protected-paths.json)与PM交接Git对象相同，含fixture、legacy、W005/W006、原evidence/publication、架构和current-work；没有扩展pipeline/repository。

未实现/未验证范围仍是完整几何/坐标/occupancy/connectivity/body/extraction、baseline/seal、整轮no_change/terminal、ECO、Stage6及真实EDA/PDK。最终执行/review记录提交到当前W007分支，远端交付完整SHA在推送核对后的交接回复提供；产品/测试身份以上述提交和清单固定。下一步仅交PM核验A1–A7并维护阶段；本执行不自行验收、合并main、删除分支或启动下一任务。

## Review 结论（reviewer）

2026-11-02，独立 reviewer `/root/code_review`（专项 `/root/code_review/dto_review`；均未参与方案、产品或测试实现）：**最终代码 review 通过，剩余必须修正项 0**。受审产品与测试提交 `0f879f01acbeac033173d0b6c6257c376bb9272a`；[完整报告](W007/code-review.md)保留 CR-01–CR-05、补修 FR1–FR3 及执行补查 ER-01 的原始反例、修正和逐项关闭。接口方案及 FR3 依赖调整另经[独立接口 review](W007/interface-review.md)；reviewer 未改产品或测试。

主 reviewer 实跑全部 W007 **148 passed** 和独立原始 probes，确认 source/target/完整差异、query 身份与 seeds、C08/09/10 组件准入、C13 后续目标义务、DTO/wire/immutable/digest、请求来源闭合和异常边界。独立核对最终双解释器完整回归各 **553 passed**（含 W005/W006/IPMR-01）、双 strict mypy **33 文件**、新包及两套干净安装/源码外 smoke 回执；101 个源码/测试/配置 Git blob 与清单、sdist/wheel 各 83 个 runtime 文件、14 处既有保护路径均匹配。[复核回执](W007/review-evidence/final-review.json)与[交付证据审计](W007/review-evidence/delivery-audit.json)绑定上述版本；source-manifest content SHA-256 为 `f051ae0fecab66a1104e0aa609cc8450c1cf480a99384113027dc5a6f40976a9`。

此结论支持交 PM 接收 W007，不是 PM 验收或完整 Stage2/M1 成功。真实 EDA、几何/物理状态、body/extraction、baseline/seal、整轮 no_change/terminal、ECO 和 Stage6 仍按任务边界留后续；本次未合并 main 或启动下一任务。

## PM 验收与交接（PM）

原派发阶段只准备任务和分支；实现交回后的当前接收状态见PM1。执行者的提交、review与后续PM接收分别保留，不把分支技术接收写成main集成或完整M1通过。

**派发要求独立复核（2026-11-02，PM记录）：** 未参与草稿编写的`/root/w007_handoff_review`对照架构与W003–W006相邻合同检查，剩余必须修正项0；确认source/target及seed分工、C08/09/10与C13阶段边界、真实读取适配、后续完整状态/发布/导出义务和授权范围。受审W007全文SHA-256为`7ecfe9a6dfaaeec00fcbc4a80887284d330a1fb618db9ebb7f1545110745b54d`，对应追加本段前的内容；这不是未来接口方案或产品代码review。

<a id="pm1-technical-receipt-20261102"></a>
### PM1. 分支技术接收（2026-11-02，PM）

**接收A1–A7范围内的交付，剩余必须修正项0；可进入main集成，W007最终验收待集成版本及组合验证。** 本次从干净的PM派发提交 `64b4ad2f77c017affade69374510dc12e534bc07` 快进至用户指定交付 `5e874e5e60bb74f58903080bf079796061454962`；实际远端同SHA，main仍为 `221492eb72e10cf2e46f1d9c76cb992087806a97`。最终产品/测试为 `0f879f01acbeac033173d0b6c6257c376bb9272a`，交付后续仅增加本任务文档/证据。可移植结果见[PM回执](W007/pm-receipt.json)。

PM对照任务、架构和接口补审读取了实际实现及独立review。CR-01–CR-05、FR1–FR3、ER-01均有保留的反例、修正与reviewer关闭依据；没有以旧候选6712cbc的530项结果代替最终验证。`/root/w007_accept_scope`另核对source/target、全量差异、身份/seed及公开结果守卫；`/root/w007_accept_evidence`独立核对版本、清单、日志及实际发布包。两项只读专项未新增必须修正项，不替代原独立代码review。

| 本次接收核验 | 结果与采用边界 |
| --- | --- |
| PM实际完整回归与strict typing | Python3.12.14：**553 passed / 178.49s**；**33 source files无问题**，包括W005/W006及IPMR-01。使用既有PM环境和当前源码，不作为干净安装证据；有一条第三方anyio/pytest弃用warning |
| PM实际独立反例/组合 | FR3成组交换几何及response metadata被拒绝；W006合法alias、readback/wire往返通过，attempt保持不变且无terminal，五种缺失readback均拒绝 |
| 专项实际多差异探针 | NFIN不变而目标L/W/M/NF同时变化时，四项exact差异及后续义务全部保留；漏差异被公开DTO拒绝；source NF=2得到UnsupportedFingerCount且不能重标success。脚本与原输出随[PM附件](W007/pm-evidence/)保存 |
| 版本、验证与实际包 | 最终101项源码/测试/配置与Git和清单相符，13项工程回执及日志身份闭合；随Git提供的wheel/sdist各83项runtime逐字节匹配。执行阶段双解释器各553项、双typing、新构建、两套干净安装及源码外smoke按已核验回执采用，PM未再次运行3.10或重建/安装 |
| 保护范围 | 实现交付的14处保护路径与PM派发基线相同；fixture/答案、W005/W006产品及历史证据未改。PM本次仅更新阶段、入口与接收材料，不改产品 |

FR3所需的内部依赖调整在原范围内接收：只对已捕获的requests bytes复用现有安全decoder和所选limits，来源锚定不重新读盘；专属输入/codec留在normalization，domain保持纯合同。该调整已独立补审，没有新增输入、profile能力或失败阶段。

目前得到的是可追溯的source语义、独立target、完整差异与query身份/seeds；无差异仅是语义相等，B端网名不证明body连通。完整几何/坐标/occupancy/connectivity/body/extraction、原子baseline/seal、整轮no_change/terminal、Stage6及真实EDA/PDK仍未由本任务实现或验收。本轮未合并main、删除分支或启动下一任务；建议下一步完成main集成及针对性组合验证，再准备后续Stage2物理状态切片。

### 独立执行session prompt

以下为已执行的原派发prompt，仅作历史记录；当前从PM1接收结果继续，不重新实施本任务。

```text
按Layauto项目规范，以执行角色完成W007语义身份与目标归一化。
从codex/w007-semantic-identity-normalization的PM交接提交恢复，核对远端/HEAD/工作区；起点main为221492eb72e10cf2e46f1d9c76cb992087806a97，W006经PR60集成且IPMR-01已关闭。
读取AGENTS、README、协作/环境规则、current-work、W007任务及引用的架构/W003-W006合同。先补内部组件API/DTO/identity/target-diff/seed方案并独立review，原范围内修正后直接实现A1-A7。
只消费已捕获证据，构造source semantic draft、独立target与完整typed差异、query身份/seed；exact值和字段来源保真，不重读文件或用样张作运行时输入。真实W005和W006 readback均需组合验证。
C08/09/10落实source准入的组件错误；C13 L变化完整保留为后续planner义务，不能提前terminal或漏成no_change。不要把语义网名当物理连通、body_complete或真实LVS证明。
保留fixture/答案及W005/W006能力；不实现完整Stage2状态、baseline/seal、pipeline/repository扩展、ECO或Stage6。完成测试/typing/双解释器/新包干净安装，准确保存最终版本、证据和未执行范围。
由未参与实现者独立代码review，修正并复核必须修正项。提交推送本任务产物及执行/review记录到当前W007分支，使用项目noreply身份、核对远端SHA后交PM；不自行验收、合并main、删除分支或启动下一任务。
```
