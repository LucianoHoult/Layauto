# W008 — 几何事实与基础占用

把已经捕获的GDS证据变成完整、可追溯的本地图形草稿，并建立可重建的精确占用索引，供后续物理状态构建使用。本轮回答“有哪些图形、准确位于哪里、一个索引格里有哪些图形片段”，不据此回答电气连通或合法布线位置。

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| ID / 目标 | W008；交付immutable geometry draft、exact坐标换算及versioned base projection/occupancy draft，消费实际捕获输入，无IO或发布副作用 |
| 里程碑 / 依赖 | M1第四个产品切片；W003/W004已验收synthetic输入、W005读取、W006运行审计、W007语义组件。W007经[PR #61](https://github.com/LucianoHoult/Layauto/pull/61)合入main `765ff864f4341b91996f70f25723411eebc0d6c2`，最终验收见[W007 PM2](W007-semantic-identity-normalization.md#pm2-integration-20261102) |
| 授权依据 / 阶段 | 用户派发独立执行任务，并于2026-11-03交回实现/review，请PM继续。**待验收：A1–A8分支技术接收通过，剩余必须修正项0；最终验收待main集成版本及组合验证。** 依据见[PM1](#pm1-technical-receipt-20261103) |
| 恢复位置 | `codex/w008-geometry-base-occupancy`；产品交付`aced62b0adda35fe7bcd8284a7354badc5b03649`，PM复核HEAD `baad5347627db194649430cf6b0f5ebf0aa1165e`仅多U06文档澄清。接手包含本次PM1记录的后续提交，完整SHA见Git/回复；临时环境不假定跨session可用 |
| 允许修改 | `domain/geometry.py`及必要typed ids/中立DTO/codec；`state/layout_store.py`、`coordinate.py`、`occupancy.py`的纯草稿/数学组件；`normalization/`中的适配与构建；必要的tech中立合同、读取侧无IO校验复用；对应tests、typing/build配置、README和本任务附件。具体类型与文件划分留内部方案 |
| 非目标 | 不实现完整Stage2CoordinateSystem/合法routing lattice、制造网格或移动能力；不做CUT Boolean、terminal split、spatial annotation、connectivity/body/extraction、mandatory rules、生命周期最终闭合、完整ProposedInitialState、initialize/seal、pipeline/repository扩展、ECO、no_change/terminal或Stage6；不改已验收fixture/答案及真实PDK/EDA边界，不落实MR-040配置机制 |
| 架构依据 | 上述main的[architecture](../architecture.md) §1.4、§2.2–2.3、§3.1/3.3–3.5、§4.1–4.4/4.8、§5.4–5.9、§11.2–11.3/11.10/11.14–11.15、§12.3/12.5；[W003合同](W003/contracts.md)、[MR-051/052/054/056](W003/manual-verification.md)、[W005后续组合](W005-input-reading-binding.md#pm已确定的任务拆分)、W006 InputsReady/readback及W007输入/seed合同 |
| 分工 / 阻塞 | 一名执行者负责集成；未参与设计/实现者独立review接口及最终代码；PM接收并维护阶段。当前synthetic范围无新的必需用户选择，正式工艺坐标空间继续后置 |

### 已核对事实与坐标边界

- `tests/fixtures/w003_m1/tech/coordinate.json`明确`example_only=true`、`is_complete_runtime_model=false`，只有unit ref/frame origin等示例信息。不能把它、D记录中的coordinate_ref或32×16专例桶当成完整产品坐标模型。
- `tech/drawn.json`按层声明`exact_fragment_rectangles`或`none`。FIN/POLY为A，LI/M1等按当前选定profile为B，BOUNDARY为C1、MARKER为C2；按实际声明消费，不能照通用层名例子重新分类。
- `tech/formats.json`声明`flat_boundary_rectangles/1`及`toy_gds_real8_nm/1`，正常本地GDS有40个BOUNDARY记录；六个外部body-context图形不在本地drawn scope。正常与特殊样本中的terminal/component/occupancy见证不是预制runtime状态。
- MR-052把主坐标具体设计、投影和API留给后续开发，没有指定通用生成公式。**本轮只建立内部base projection/index**，可从已捕获exact drawn边界确定有限稀疏分区；具体分层/分区算法需独立方案review。该选择不增加外部输入，也不推断工艺合法track。正式coordinate binding与合法移动空间在后续任务按tech/profile补齐。

### 行为要求与边界

1. **输入来自同一捕获，字段必须能回到原始证据。** 从W005成功ParseResult及W006真实readback构造经验证的中立输入；可复用W007适配，但不能只凭NormalizationInput已构造就信任GDS内容。W007现有GDS校验主要覆盖refs，本轮所消费的XY、bbox、layer/stream key、单位、top/record位置及tech policy必须与已捕获bytes和对应owner绑定一致；value与completed同时伪造也须拒绝。可以在适配层复用既有无IOdecoder来核对捕获bytes，不能重新读取文件或发起工具。`domain/`、`state/`不得依赖parser/normalization/pipeline/repository/transaction实现。
2. **保留全部本地图形及其身份。** 依选定capability逐record无损建立唯一drawn geometry草稿，包括未注释、MARKER/C1/C2及重复/重叠图形；保存element-tagged stream key、canonical layer/purpose、exact geometry、原XY及unit/preservation/source backlinks，保留适用的tier、role、edit/lifecycle等policy来源。未知或超范围记录按已声明policy定位拒绝，不丢弃或扩大支持。稳定typed record identity不能依赖fixture展示名、Python hash、任意遍历顺序或只用bbox去重；内容相同的不同record仍分别可追溯。保留metadata语义与整个capture，不承诺byte/stream顺序完全相同的导出。
3. **精确单位换算，不移动源图形。** 在已验证UnitScaleContract下，原整数ticks→nominal物理值→canonical DBU精确可逆；保留REAL8 raw、exact decoded、nominal、encoding delta及合同身份。用整数/Fraction等精确值，不能float、截断、snap或借annotation tolerance吞掉冲突。区分record/provenance digest与按所选geometry comparator得到的语义digest；后者保留top及record multiplicity，并可忽略已声明无语义的stream顺序/矩形起点和方向差别。
4. **Base projection有明确来源和用途。** 分区模型是版本化的内部数学/索引产物，其身份绑定算法/参数、输入geometry与相关layer/unit policy，可由这些事实重建。方案须给出有限范围、边界归属、physical↔index转换、片段构造规则及soundness证明/手算例。不能把临时桶或此模型填进完整ImmutableContext.coordinate_ref，也不能由FIN pitch、单根POLY、via electrical_connects或图形GCD猜其它层合法lattice。coordinate只提供数学服务，不拥有occupancy。
5. **逐record完整投影，容纳多个occupants。** 按已选layer projection policy生成base occupancy，每个fragment精确引用所属drawn record和索引cell；每条纳入投影的记录，其fragments的几何并集等于原图形，且内部无无意重复/重叠。不同records的重合保持各自身份和重数，不用单值cell覆盖旧occupant。C1/C2仍在layout草稿中、默认不进入主occupancy；VIA/CONTACT只保留自身drawn占用，不另造上下层wire事实。原CUT只作drawn geometry/索引，本轮不产出扣除后的有效导体。
6. **保持几何、身份与物理解释分工。** W007 source/target/全部差异及query seeds保持独立且不可改写。Query polygon不是GDS补丁；本轮不stamp net/device到occupancy、不猜annotation coverage、不据同格/相邻格/网名创建physical edge。外部body上下文只保留其独立输入引用和scope，不复制到本地geometry/occupancy。正常expected的ON.S/ON.D/OP.S/OP.D已包含terminal split，不能加载为本轮drawn-base投影答案；cut-islands两片段的有效拓扑也留后续验证。
7. **公开合同可验证，成功限于组件范围。** 结果、layout、分区及occupancy具有closed/versioned schema、typed refs、recursive immutability、canonical wire/digest和聚合一致性校验；公开constructor/decode不能接受漏record、外来fragment、坐标/单位/来源错配或伪造success。预期问题定位到输入并保留已完成事实；意外Exception及KeyboardInterrupt/SystemExit按纯组件边界传播。不得把此草稿叫committed snapshot、完整AuthoritativeState或ProposedInitialState；不推进W006 attempt/refs，不产生baseline、no_change或terminal。

### 验收清单

| ID | 输入/条件 → 可观察结果 | 正确性依据与验证 |
| --- | --- | --- |
| A1 实际组合与无IO | 真正经W005读取、W006 InputsReady/repository readback，再与W007语义产物同源组合 → 等价geometry/base occupancy，attempt/terminal不变 | 禁用构建期间文件IO；合法alias与错误run/source/readback反例，保持W005/W006/W007错误边界。不得加载expected/spec/oracle作为运行时输入 |
| A2 字段与捕获闭合 | 保持sources不变却成组篡改XY/bbox/layer/units/top/record位置/tech政策 → 拒绝；正常全40本地图形保留、外部6图形不混入 | 从真实raw bytes及显式owner手核，加入value/completed同时伪造、遗漏/复制record和同hash错role等反例，不仅比两个同源派生dict |
| A3 几何与单位保真 | 原ticks、单位及canonical值精确对应；符合已声明比较器的顺序/顶点起点/反向变化保持语义等价 | 独立整数/Fraction算术；负坐标、边界、重复和重叠records、合法重命名/平移、不可精确表示/错误单位绑定；保留旧unsupported stream/nonrectangle拒绝，不用bbox包围非矩形 |
| A4 分区可重建 | 从geometry+policy重建相同versioned partition/occupancy；输入或模型变化不能沿用旧身份 | 方案给出内部索引用途、无工艺合法性承诺及边界规则；手工期望与不同输入重排/跨hash-seed检查。示例coordinate仍保留example身份，不改fixture补假axes |
| A5 完整多占据 | 每条投影record coverage完整，重复/重叠多occupant不覆盖；C1/C2完整保留但不主stamp，via不产生重复wire | 每record并集/面积/交叠独立检查与双向refs验证。若边界分区天然拆开不相交矩形，用重叠/重复records和明确的内部测试partition覆盖多片段；32×16只能作为具名测试见证，不能进入runtime默认值 |
| A6 公共DTO与错误 | mutation/alias、漏record/fragment、错误schema/ref/单位/来源、非法success及wire修改均拒绝 | closed schema、递归不可变、canonical roundtrip/digest、意外异常/中断同对象传播；检查依赖方向及无legacy runtime依赖 |
| A7 阶段与范围 | 本轮无target/seed改写、无annotation/net/component声明、无body/physical/no_change成功、无状态发布 | 真实W005/W006/W007组合及scope断言；正常/特殊fixture只采用本轮涉及的几何判据，保留终端分区/CUT/body等后续见证归属 |
| A8 工程与交付身份 | 保留既有553项能力；新增判据、strict typing、Python3.10及开发解释器、新包及两套干净安装/源码外组合smoke通过 | 实际最终源代码/测试/配置清单、命令/环境/原始输出、wheel/sdist实物及安装来源可核验；不混用修前结果，不为满足数量镜像实现 |

允许在临时目录构造有独立手工预期的派生输入、显式重绑header以隔离目标条件；不修改已验收fixture/答案、旧报告或生成器来迁就实现。必要的读取侧复用仅限既有语法/结果合同内的无IO校验，须覆盖受影响原回归。

### 后续组合归属（不计作本轮完成）

| 后续能力 | 必须保留的义务 |
| --- | --- |
| 完整工艺坐标空间 | 逐层axes/pitch/offset/方向、B-tier axes及来源；routing/placement合法空间、正式coordinate binding。W008内部base index不得替代它或改变源几何 |
| 有效几何与物理解释 | CUT Boolean、gate terminal split、qualified contacts/vias、effective conductor/device/body regions、physical connectivity与device extraction；正常四个OD terminal和cut-islands见证在此闭合 |
| Annotation与状态闭合 | W007 seeds的spatial overlay、fragment/region身份、coverage/conflict、保守分类；body D1=A、精确独立上下文及真实证据标志；逐层lifecycle、mandatory predicates及完整ProposedInitialState |
| 正式运行与M1 | 同run审计、Stage2 pre-context拒绝、initialize/seal/CAS/幂等、全量目标及semantic/extraction-aware no_change、Stage6 GDS/CDL/JSON读回/报告/terminal；C13的sealed规划拒绝仍需组合验证 |
| 真实准入/M2 | G1–G4仍为真实M2前置，G5最迟M3；本任务不授予resize/edit capability，不代表真实EDA/PDK验证 |

**后续需求补记（2026-11-02，PM）：** 用户要求考虑生产环境不提供body tapcell的情况，已纳入[路线图U06](../roadmap.md#production-body-evidence)，由生产读取适配及body能力任务落实。该项应区分缺资料、可信替代证据与错误资料，并明确测试能力和完整运行准入；不扩展本任务A1–A8，不在W008中静默删除现有synthetic输入的body_context必填校验。

## 方案与决定（执行准备，PM 接收）

先调查W005 GDS字段/捕获bytes、W007输入/readback与当前domain/state骨架；定向查看legacy坐标/矩形投影候选，只取可证明正确的纯算法，不保留grid持有occupancy、ViaInstance/Net.segments等多份事实源。

内部方案至少包含：输入适配及捕获闭合；record identity和两种digest；exact unit换算；base partition来源/版本/边界与重建；layout/occupancy ownership；公开DTO/错误/codec；两条真实读取路径及独立测试判据。具体算法、类型名和模块组织留执行者决定。先由未参与设计者review，原范围内修正后直接实现，不把一般算法选择变成用户审批门。

当前无需新增用户选择。若确需新增对外profile/schema、默认pitch、改变输入解释/拒绝阶段或能力承诺，先准备最小输入/输出、依据、影响和推荐项交PM；在具体决定前推进不受影响工作，不静默扩展范围。

## 执行结果（执行）

### E1 执行恢复与方案（2026-11-02）

启动核对时远端W008与指定起点均为`2d5f42258b5a2cf09f686a06c483e2a6915bc48c`。本机原checkout在W003，已有`.DS_Store`修改；保持不动，另建`/private/tmp/layauto-w008` worktree追踪本任务分支。执行角色未改PM阶段、current-work、架构或已验收fixture/答案。

[内部方案](W008/plan.md)与[独立方案review](W008/plan-review.md)先于产品实现。IR-01要求显式核对body双来源、header/body的top/unit/profile/scope跨文档绑定，已按review意见补充后实施。方案和review身份见报告；该review不代表代码或PM验收。

已实现capture-authenticated GeometryInput、完整LayoutDraft、精确单位转换、drawn-layer-edges/1基础分区、多occupant BaseOccupancy及closed/versioned wire。正常40条本地drawn记录形成41片段；body上下文独立保留。完整执行、A1–A8与限制见[执行交接](W008/execution.md)。产品/测试最终身份见下段；独立review结论由reviewer维护。


### E2 最终验证与交付身份（2026-11-02）

最终235文件manifest SHA-256：`30b4e446ff6b38f8c06be92916576928b87abdf62d10bc58f1b22ffa34a5f881`。Python3.11.5与3.10.22各**730 passed**（保留553项＋新增177项），双strict typing各40模块通过；新wheel/sdist、两套全新安装、pip check及源码外`-I -B`真实W005–W008组合/错误/codec smoke均通过。两包与两安装的各86个runtime文件逐一等于受测源码。命令、原始输出、包实物、安装来源及hash见[最终回执](W008/verification/receipt.json)、[包身份](W008/verification/package-identity.json)、[安装身份](W008/verification/installation-identity.json)。

独立代码review发现CR-01的首次获取URI/历史alias混淆；已修复，补足直接构造、嵌套wire、15角色反例及真实alias回归，修后完整重跑与重建结果为上述最终身份。修前713项与旧包另存`W008/verification/pre-cr01/`，不混充最终证据。finding原文及独立复核归[代码review](W008/code-review.md)。

执行期间远端新增PM文档提交`2560999021f2551793346187e3c4825276cba2ff`，已安全快进整合并保留本轮全部改动。该提交仅登记U06后续需求，不扩展本轮范围。提交推送沿用`LucianoHoult@users.noreply.github.com`；最终交付SHA在Git与执行回复核验，PM从本分支接收。未自行验收、合并main、删除分支或启动下一任务；完整工艺坐标、physical/body/CUT/terminal解释与正式状态发布均未实现。

## Review 结论（reviewer）

### R1 独立方案、代码及修正复核（2026-11-02）

Reviewer `/root/plan_review` 未参与实现；输入绑定专项由独立的 `/root/plan_review/role_probe` 只读复核。[方案 review](W008/plan-review.md) 的 IR-01 已明确 header/body 跨文档及双来源绑定并复核关闭；[代码 review](W008/code-review.md) 的 CR-01 发现“缺失首次采集 URI 被误当作历史 alias”，已由执行者修正并独立复核关闭。**剩余必须修正项 0，可交 PM 核验接收；本节不是 PM 验收或合并决定。**

最终受审材料绑定 [235 文件清单](W008/verification/source-manifest.json)，SHA-256 `30b4e446ff6b38f8c06be92916576928b87abdf62d10bc58f1b22ffa34a5f881`。Reviewer 重算全部条目，零差异；起点 `2d5f42258b5a2cf09f686a06c483e2a6915bc48c`，审查期间整合的 `2560999021f2551793346187e3c4825276cba2ff` 仅补 PM 后续需求文档，产品及清单身份未变。最终提交/远端 SHA 由执行者提交后报告，不虚构预先提交身份。

Reviewer 实跑修后输入/codec **127 项**（3.11）及 CR-01/alias/wire **19 项**（3.10），原反例已定位拒绝；另独立执行 1,000 组数学分区、实际空 GDS 草稿/codec，以及最终 wheel 3.11、sdist 3.10 两套源码外 `-I -B` 组合 smoke。独立核对两个包和两个安装目录各 **86 项 runtime 文件**，均匹配受审源；完整 [13 项命令回执与日志 hash](W008/review/final-receipt-audit.json) 核验通过。两解释器各 **730 项完整测试**、两次 strict mypy **40 模块**及构建/干净安装采用已核验最终执行回执，未冒称 reviewer 重跑全矩阵或重建安装。原 713 项及旧包只保留修前历史身份。

A1–A8 的逐项依据、原 finding/反例、修正关闭和直接运行/采用证据区别见代码报告。当前交付严格限于捕获绑定的全部 drawn geometry 与内部精确 base occupancy；完整工艺坐标、合法移动、物理连通、body/extraction、发布与完整 M1/生产验证仍按原任务后置。

## PM 验收与交接（PM）

原派发和本次PM1分支接收按各自版本保留；当前技术接收通过，尚未合并main或完成最终集成验收。W007的39项集成检查仅是历史依赖证据，本次W008实际验证见PM1。

**派发要求独立复核（2026-11-02，PM记录）：** 未参与草稿设计的`/root/w008_handoff_review`及其输入边界专项，对照上述架构原文、MR-051/052/054/056、实际GDS/tech声明和W005/W007接口检查，必须修正项0。确认内部base index没有冒充完整工艺坐标空间，保留来源闭合、多占据、独立body scope及后续物理/发布义务。受审基线为本次main，W008全文SHA-256为`611e5e83385771b193521e28917c980c72b9deb864303f42933c0798da87ce14`，对应追加本段前的草稿；这不是未来接口/代码review或W008产品验证。

<a id="pm1-technical-receipt-20261103"></a>
### PM1. 分支技术接收（2026-11-03，PM）

**接收A1–A8范围内的交付，剩余必须修正项0；可进入main集成，W008最终验收待集成版本及组合验证。** 用户交付为`aced62b0adda35fe7bcd8284a7354badc5b03649`；本次复核HEAD为`baad5347627db194649430cf6b0f5ebf0aa1165e`，远端一致。后者仅在current-work/roadmap补充U06，产品、测试及执行证据未变；main仍为`765ff864f4341b91996f70f25723411eebc0d6c2`。完整命令、环境、原始输出、身份及采用边界见[PM回执](W008/pm-receipt.json)和[PM附件说明](W008/pm-evidence/README.md)。

PM对照任务、架构及接口核对实现和独立review；IR-01、CR-01均有原问题、修正和reviewer关闭依据。`/root/w008_accept_geometry`只读检查几何/分区/occupancy/聚合边界并运行限定探针；`/root/w008_accept_evidence`独立核对Git、清单、日志和实际包字节。两项专项未新增必须修正项，不替代原独立方案/代码review。

| 本次接收核验 | 结果与采用边界 |
| --- | --- |
| PM实际完整回归与strict typing（A1–A8） | Linux Python3.12.14：**730 passed / 421.70s**；**40 source files无问题**。使用既有PM环境和当前源码，不作为干净安装证据；一条第三方anyio/pytest弃用warning保留在原输出 |
| PM实际CR-01原反例（A2/A6） | 未改变原复现材料；同bytes但错误首次获取URI被拒绝为`GeometryCaptureBindingMismatch`，定位`site_config.yaml#/inputs/gds`，9项已完成事实保留 |
| 专项实际几何探针（A3–A7） | **16项限定检查通过**：大整数精确分区/边界、真实40个本地records与38个投影records的41片段逐record面积及无内部重叠、6个外部body shapes隔离、漏项/重复构造器拒绝、单位逆变换与非整数拒绝。大整数是数学DTO检查，不扩展GDS输入范围 |
| 来源与版本（A2/A8） | **235项**源码/测试/配置清单与当前及交付Git字节一致；**84项**证据附件与**13条**命令回执/日志身份一致；最终730项记录与修前713项分开，证据审计32/32通过 |
| 实际包与采用的安装验证（A8） | 随Git的wheel/sdist各**86个runtime文件**直接逐字节匹配最终源码。原Mac Python3.10.22/3.11.5各730项、各40模块typing、新包/两套干净安装/源码外smoke按已核验回执采用；本次未重建安装或访问原Mac安装目录。3.10安装来自sdist，缺失的pip archive hash不补写为已存在 |
| 原能力及范围（A1/A7/A8） | 已验收fixture/答案、support、W005/W006实现、W007核心组件和历史报告未改；W007唯一旧测试调整是具名W008纯适配/状态依赖放行。真实组合不推进attempt，不产生baseline/no_change/terminal |

上述84项附件核验发生在PM追加记录前；原清单包含本任务文件的交付版本。当前只更新其阶段/恢复位置和PM段，并标明旧prompt已执行，A1–A8、执行及reviewer原文不变。该历史任务文件hash按`aced62b`追溯，其余83项及235项源码清单仍与当前一致；不重写原清单来覆盖历史身份。

完整本地图形、精确单位和多occupant索引在本任务范围接收。`drawn-layer-edges/1`只表示内部索引；完整工艺坐标、CUT/terminal split、annotation、物理连通/body/extraction、生命周期/原子baseline、整轮no_change及Stage6仍留后续。捕获bytes的纯decoder复用和依赖检查调整符合原授权，没有新增外部输入或能力承诺。

U06“只输入待修改底层cell、外部tapcell/全局电源上下文缺失”的需求继续有效，由后续生产读取/body任务提出具体方案；本轮没有将body_context改为可选，也没有把未知外部连接视为已证明。建议下一步完成main集成及针对性组合验证，再准备后续Stage2切片。本次仅提交PM记录与证据，未合并main、删除分支或启动下一任务。

### 独立执行session prompt

以下为已执行的原派发prompt，仅作历史记录；当前从PM1及current-work继续，不重新实施本任务。

```text
按Layauto项目规范，以执行角色完成W008“几何事实与基础占用”。
从codex/w008-geometry-base-occupancy的PM交接提交恢复；main起点为765ff864f4341b91996f70f25723411eebc0d6c2，W007经PR61已验收集成。先核对远端/HEAD/工作区，读AGENTS、README、协作/环境规则、current-work、W008及其引用的架构与W003–W007合同。
先细化无IO输入/字段回绑、geometry身份/单位/保真、内部base partition、多occupant、DTO/codec/错误方案并独立review，原范围内修正后直接实现A1–A8。内部算法自主选择；不要直接加载example coordinate或32×16见证当完整运行网格，不推断合法routing lattice。
从真实W005/W006捕获证据构建全部本地图形与精确可重建的base occupancy。补足GDS/tech字段到捕获bytes的绑定，不能只信任既有NormalizationInput；原ticks不float/snap，保留重复记录和C1/C2，外部body图形不混入本地scope，W007 source/target/seeds不改写。
不实现CUT/terminal split、annotation/connectivity/body/extraction、完整坐标合法空间、baseline/seal、pipeline/repository扩展、no_change/ECO/Stage6；不改已验收fixture/答案和历史证据。使用独立手算判据、真实组合与公开DTO反例，完成双解释器、typing、新包/干净安装/源码外smoke并保存最终身份及未执行范围。
由未参与实现者独立代码review，修正并复核必须修正项；代码、测试、可访问证据及执行/review记录提交推送当前分支，沿用项目noreply身份，核对远端完整SHA后交PM。不得自行验收、合并main、删除分支或启动下一任务。
```
