# W010 — 局部接触与物理连通草稿

从W009的精确有效区域出发，计算本地哪些区域实际接触、哪些connector建立跨层连接，以及由此形成哪些物理分量。把导通事实和连接件包围检查分别表达，保留全部来源和范围边界，供后续器件提取、标注和规则组合消费。

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| ID / 目标 | W010；从认证W009产物及同源接触/规则声明构造只读、精确、可重建的局部contact/connector/component草稿，并记录局部T05 enclosure判据 |
| 里程碑 / 依赖 | M1第六个产品切片；W005–W009已验收集成。W009经[PR #63](https://github.com/LucianoHoult/Layauto/pull/63)合并`8c60f6c6183aed79a08ec8bb232a31f918837f68`，见[PM4](W009-effective-geometry-terminals.md#pm4-integration-20261104)。本任务从含其验收补记的main `3be0b98359038bab6c23980b55a48987cc71a369`建立 |
| 授权依据 / 阶段 | 用户交回W010执行结果，沿用独立session分工。**待验收：实现及方案/代码review已交付，PM分支技术接收通过，本次新增必须修正项0。** 下一步独立合并前复核，尚未集成或最终验收，见[PM1](#pm1-receipt-20261106) |
| 恢复位置 | `codex/w010-local-contact-connectivity`，执行交付`ca39aedcb71fda02f77ffda1eb5d5dddc598226e`、冻结产品/正式测试`0f5029df935bc0acd106aad1bc2be81304d4f442`；接手包含PM1及current-work补记的最新提交，完整SHA见Git/回复。main仍为上述起点 |
| 允许修改 | 必要中立node/edge/component/enclosure DTO与refs；`state/`纯局部连通草稿；`normalization/`同源适配、组合与codec；直接必要的tech/geometry校验复用、对应tests、typing/build配置、README及本任务附件。内部模块/算法由执行者选择 |
| 非目标 | 不补完整合法工艺坐标/制造或routing lattice；不实现全部region occupancy投影、外部body证明/FIN计数/器件抽取/DeviceId-net join/query overlay、通用DRC/CSP、全部mandatory规则、lifecycle闭合、可变图更新/跨mutation lineage、baseline/seal/no_change/terminal/Stage6。fixture/答案/历史证据和生产格式不改，U06不顺手实现 |
| 架构依据 | 本次main的[architecture](../architecture.md) §2.2–2.3、§3.1/3.4–3.6、§4.5–4.8、§5.6–5.9、§8.1/8.4–8.5、§11.2–11.3/11.14–11.15、§12.3/12.5；[W003合同](W003/contracts.md)、[manual review](W003/manual-verification.md) MR-045/047/052/054/056及W004现行body修订；W007–W009已验收的输入/来源/单位/公开结果合同 |
| 负责人 / 分工 | 执行者负责方案与集成；未承担设计者review方案，未承担实现者review代码；PM负责范围/阶段/验收与入口。现行要求内选择自主处理 |

### 已核对事实与拆分理由

- [physical owner](../../tests/fixtures/w003_m1/tech/physical.json)已声明`same_layer_contact/1`和`cross_layer_contact/1`：同层正面积或正长度共边可导通，点/角触不导通；跨层connector在声明两侧各与恰好一个独立有效region正面积交叠，禁止via-as-wire；enclosure独立mandatory。
- [drawn owner](../../tests/fixtures/w003_m1/tech/drawn.json)声明局部CONTACT `OD↔LI`、VIA0 `LI↔M1`、GCONTACT `POLY↔M1`，对应唯一端点谓词及`T05.contact_enclosure`。BTAP_N/P为外部body context域，当前本地记录为0。
- [rules owner](../../tests/fixtures/w003_m1/tech/rules.json)的T05明确局部三类connector与外部BTAP分域；本地每侧exact区域须四边包围connector至少1nm，`geometry_only/required=true/reject_indeterminate`。本轮只交付该局部几何判据，不把整个T05（含外部context）或规则集标为完成。
- W009已给出每条OD的channel/S/D、每条LI切后独立区域与原record重数；POLY/M1/BODY_N/P仍有原精确图形。W008原轴不保证覆盖CUT/channel边界，occupancy只能枚举候选。
- [coordinate示例](../../tests/fixtures/w003_m1/tech/coordinate.json)仍为`example_only=true/is_complete_runtime_model=false`；现行exact接触和包围不需要先编造合法网格。完整工艺坐标、有效region投影等仍是后续必需义务。
- 现行手工[正常答案](../../tests/fixtures/w003_m1/oracle.json)为14个局部有效region、8条connector边、6个分量（含独立BN/BP）。[via_enclosure变体](../../tests/fixtures/w003_m1/failures/via_enclosure/)中VN仍与两侧唯一正面积接触，但LN侧包围不足；不能把规则失败解释成没有物理edge。

### 行为要求

1. **认证输入与纯组合。** 实际支持W005直接捕获及W006 readback经W008/W009的两条组合路径；只消费同一成功W009产物、同一捕获的physical/drawn/rules/formats及exact单位；新增rules payload须等同该捕获的tech/rules内容，并绑定实际rules source role的SourceRef，不靠同名文件或另配副本。不读盘/repository或调用EDA。domain/state只校验中立自洽，捕获认证归normalization。保留整个输入、raw drawn/base occupancy、W007语义/target/query/body和attempt；不加载spec/oracle/expected为运行输入，不以net名或器件名建边。
2. **明确局部图的节点和scope。** 每个OD S/D ExactRegion、每个LI差集独立ExactRegion、每条POLY/M1/BODY_N/BODY_P的identity region各为独立节点，全部来源与record重数保留。channel不作导体；POLY仍按完整原图形连续。FIN/CUT/BOUNDARY/MARKER保留为非消费证据，connector不是额外导体节点/导线stamp。BODY只参加本地几何节点及同层关系，不因包围OD、CDL B端或rail名称制造边。外部6个body上下文图形不进入本地图。出现非空本地BTAP仍遵守现行输入合同，并在本组件定位unsupported，不能静默忽略或扩展成本轮新body能力。
3. **精确同层接触与唯一connector端点。** 先按正面积/正长度共边计算同层region对，点/角接触不成边；内部矩形分解不得把一对region重复计边。跨层仅消费三类明确局部connector及其声明连接对；每侧以独立region为计数单位，不能先合并同层component或按bbox去重来消除多端点歧义。仅边角接触、无端点、多个region、未知/矛盾已消费operator/role/predicate/连接对须定位说明并拒绝完整草稿成功，不静默跳过connector。先按positive-area计数，不先用enclosure挑选唯一端点。重复connector record仍须分别保留来源、重数及逐侧audit；同端点拓扑可聚合表达，但不能按bbox/端点对去重而丢证据，也不能因此改变端点region计数。
4. **导通与T05分离。** 正面积且每侧唯一的connector edge不因包围不足而消失；须保存该edge及独立的逐connector/逐侧T05事实。对多片/孔洞region，1nm扩张后的connector须被exact region集合完整包含，边界等号允许；不能用region bbox、单片包围或面积相等代替。nm阈值与canonical tick按精确单位换算，必要时有理数/交叉乘比较，不float、floor、epsilon或snap。violation必须显式表达，不能声称mandatory通过；可分离图与audit结果，或拒绝总结果时保留已算接触事实及独立失败原因。构建成功不等于全部规则/运行准入成功，接口组织留给方案明确。
5. **完整分量与稳定来源。** 对所有纳入节点（含孤立区域）按已证明物理边作完整分组，不由S/D device relation、同标签/同cell/外部scope关系union。typed node/edge/component refs绑定输入、scope、单位、算子、来源及exact几何/完整成员；重建同一捕获稳定，区分来源身份与拓扑/几何语义。输入record重排可改变provenance refs，但不能改变相同几何多重集合的接触/分组语义。分量仅为本地只读草稿，不携带已验证net标签或跨snapshot lineage承诺。
6. **有限算子及公开合同。** 显式核验已消费owner/算子/版本/规则语义及来源，保留未消费声明，不因capability=true或同名ref存在声称全部算子执行。closed/versioned/递归不可变DTO、canonical wire/digest及公开constructor/decode须验证完整节点、边、分组和audit，拒绝遗漏/额外边、孤立节点丢失、伪造union、外来来源/单位/算子、false success和可变别名。预期问题定位并保留completed事实；意外异常/中断在新算法及全部嵌套旧解码链中保持原对象和既有cause/context/suppression，畸形wire明确拒绝。不得重复W009 IPMR-01/FXR-01的边界缺口。不推进attempt、发布baseline或产生terminal。

### 验收清单

| ID | 输入/条件 → 可观察结果 | 独立依据与范围 |
| --- | --- | --- |
| A1 真实组合与来源 | 实际W005/W006→W008→W009→新草稿等价、构建无IO、输入/attempt不变；错run/owner/来源及成组payload伪造拒绝 | 从真实捕获构建；禁IO、原事实/单位/完整来源和嵌套认证对照，不引用答案驱动运行 |
| A2 接触算子/精度 | 同层重叠/整边/局部边成立，点/角/间隙不成立；声明跨层positive-area且每侧唯一才有connector边 | 独立手算/点边几何，负坐标/大整数/重排、CUT边界不在原轴的反例；全量有限精确枚举可作为候选索引oracle，不能同算法自证 |
| A3 正常图 | 14节点、8connector边、6分量，成员完整；BN/BP独立、OD channel无S↔D边、POLY连续，局部8connector enclosure通过 | 按正常oracle的几何来源/成员集合独立比较，不把C_A/C_Y/net名或正常数量当唯一判据；不宣称8个器件terminal/外部body已提取通过 |
| A4 歧义/完整性 | 无侧/多侧/重复同几何导体record、同层已连通的两候选、仅边角触、未声明跨层及错误layer policy拒绝；重复connector保留各record来源/audit及相同拓扑，孤立节点不丢 | 原source record与独立region计数；只允许已声明边，不用component合并或enclosure过滤放宽唯一性；分量与完整边集双向验证 |
| A5 既有特殊与enclosure | cut-islands仍3分量/0边；via_enclosure的VN边仍在但LN侧T05 violation，不能假报通过；恰阈值/不足、跨pieces整体包围、孔洞假bbox均正确 | special沿用W009的临时header/body/query重绑，fixture不改；VN `[33,50,37,54]`与LN `[28,30,34,55]`/MN `[0,48,45,58]`各唯一正面积交叠。只验局部图/T05判据，不外推T06/T08/T10 |
| A6 公共合同 | 重建/roundtrip/digest稳定；遗漏/多边/错误分组/外来ref/unit/operator/假audit/递归alias/畸形wire拒绝，算法异常保留原对象及原链 | 独立修改公开constructor和nested wire，不只私有helper；检查新图算法、W009/base/捕获/readback完整链与输入错形对照 |
| A7 后续边界 | raw/semantic/query/body保留；图scope、未消费操作与检查覆盖显式，不按名称补边或宣称外部/完整规则/发布成功 | U06、完整工艺坐标、region投影、FIN/body/器件/标注与全部mandatory/lifecycle/atomic baseline/no_change/Stage6有明确后续归属 |
| A8 工程 | 原1149项能力保留，新增必要数学/拓扑/失败反例；Python3.10及开发解释器完整v2、strict typing、新wheel/sdist、两套干净安装/源码外真实组合smoke通过 | 最终源码/测试/配置、原命令/环境/输出、包与安装来源可核验；披露候选/边数/集合包围及重复认证复杂度、有限压力规模，不新增隐含外部限制或作生产性能保证 |

新输入/格式或关键使用预期：**当前无必须用户决定项。** 现行toy语义内的算法、DTO、索引和audit组织由执行者细化；出现需要扩大connector/多端点/生产body或完整坐标解释的具体实例时，保留原可处理范围并带样例/影响/推荐交PM。

## 方案与决定（执行准备，PM接收）

执行者先调查W009区域/codec及可复用legacy纯contact/union算法，不引入legacy或tests/support运行依赖。细化同源owner绑定、node/edge/component所有权、scope/独立region计数、contact/enclosure分离、exact union containment与单位、候选完整性、typed失败/coverage、公开重建/wire/完整异常边界和资源成本；由未参与设计者review后，在原要求内修正并实现。

允许诚实的有限O(n²)精确候选扫描，不要求先造新合法网格或全面region→occupancy投影。若使用原索引，须证明共享边、跨raw cell及切后多片候选不漏；最终只用exact几何判定。接口/算法方案尚未执行，不把本任务文字当作产品验证。

## 执行结果（执行）

### E1 恢复与方案（2026-11-05，执行）

执行者 `/root` 从干净的本地 `work@3be0b98359038bab6c23980b55a48987cc71a369` 核对 origin 为 `LucianoHoult/Layauto`，核实远端目标分支为用户指定的 `9758a157115cc22d91ce095ac2002209b9f210d3` 后 fetch 并建立当前 W010 分支。读取项目/协作/环境、current-work、W010、其架构原文、W003/W004 样本与 W007–W009 上游合同；本仓库无局部 AGENTS。未修改 current-work 或 PM 要求/阶段。

[细化方案](W010/plan.md)已由未参与设计的 `/root/plan_review` 独立审查，必须修改项0，报告绑定方案内容身份，见[方案 review](W010/plan-review.md)。明确以完整捕获回执往返认证、独立 region 端点、exact 接触与独立 enclosure、完整分组/公开重建为实现边界。方案 review 完成后才启动产品和测试实施，分别使用独立 worktree，由本执行者集成。

最终实现、A1–A8、工程/独立代码 review 及交付身份将在后续记录追加；本段不宣称产品验证或 PM 验收。

### E2 最终执行、独立 review 与交 PM（2026-11-05，执行）

已完成 A1–A8 的实现与验证，冻结产品/测试提交为 **`0f5029df935bc0acd106aad1bc2be81304d4f442`**；后续交付只保存执行、review 和证据，不改变受测/受审代码。公开入口为 `normalization.build_local_connectivity`，内部 DTO、纯 state 草稿及 closed/versioned codec 分层；完整来源、独立 region 端点和本地 scope 保持，contact edge 与逐侧 T05 enclosure 分开。正常 14 节点/8 connector 边/6 分量及 16 侧 audit 通过；cut-islands 为 3 分量/0 边；via_enclosure 的 VN 边保留且 LN 侧明确 violation。不是整个 T05/mandatory、完整 Stage2/M1 或生产准入通过。

最终 Python **3.10.22 / 3.12.14 各 1465 passed**（原 1149 nodeid 全保留，新增 316），双 strict mypy **48 个源模块**，新 wheel/sdist、两套干净安装/pip check、源码外 `-I -B` 真实 direct/readback 组合 smoke 全部通过。21 条命令均 exit 0；252 项 source/tests/config 完整快照及 94 项 runtime＝两包＝两实际安装字节身份一致。版本、A1–A8、资源成本及未验证范围详见[执行交接](W010/execution.md)、[最终回执](W010/verification/receipt.json)和[源码清单](W010/verification/source-manifest.json)。preflight 缺测试文档和 R1 旧依赖守卫的真实失败/中断保留原版本，不混充最终通过；原 guard 只增加具名纯依赖白名单，已独立复核。

完整工程矩阵结束后，未参与设计/实现/正式测试的独立 reviewer 及三项专项完成[最终代码 review](W010/code-review.md)，其最终结论为**新增及剩余必须修正项0**；下节保留 reviewer 原结论及直接运行/采用证据的范围。独立记录包括手写完整图的实际 direct/readback、20,000 项精确数学对照、166 项错形拒绝、220/220 条原异常及其链、68/68 工程身份审计；review 没有冒称重跑全部正式矩阵。受测/受审版本在 review 后没有产品、测试或配置变动。

[交付身份](W010/delivery.json)与[交付文件清单](W010/delivery-manifest.json)绑定实现、测试、实际包、命令原输出、源码快照、执行及 review 记录；最终 Git/远端完整 SHA 以推送核对和交接回复标识，不让文档自指未来提交。仅交 PM 核验接收；本执行不代做验收或集成，current-work、main 和后续任务保持原边界。

## Review结论（reviewer）

### R1 最终独立代码及工程证据 review（2026-11-05）

Reviewer `/root/code_review` 及未实施的数学、公开边界、工程证据专项，在执行者明确双解释器完整工程矩阵通过后开始审查。**最终独立代码 review 完成，新增及剩余必须修正项均为0，建议交PM核验接收。** 受审 base `9758a157115cc22d91ce095ac2002209b9f210d3`，冻结产品/测试 head `0f5029df935bc0acd106aad1bc2be81304d4f442`；[完整报告](W010/code-review.md)逐项对照A1–A8、实际15文件diff与上游合同。本段不代写PM验收或集成决定。

Reviewer 实际独立运行真实W005/W006 readback→W008→W009→W010禁IO组合，以完整手写几何/边/成员表核14节点、8 connector边、6分量和16侧audit；输入/attempt及外部body边界保持。数学专项20,000项独立谓词比较、4个完整实际图及5个定位拒绝通过，明确特殊图neutral/captured分层；via_enclosure边保留且violation、cut-islands 3/0/3、重复/孔洞完整图均有独立依据。边界专项166项字段错形ValueError拒绝、220/220个完整nested constructor故障保留原object及cause/context/suppression、4组集合快照及8项可变text拒绝通过，failures=[]；原脚本/输出/身份存于[独立review附件](W010/review/)。

独立工程审计68/68通过：252项源码/测试/配置逐字节等于Git、当前、实际测试树和完整归档，两包及两实际安装各94 runtime一致，21条命令及42份原输出身份闭合；source-manifest SHA-256 `cef29336dba1bf572fd30227f354365d4a4d780e721d089b70095589d0f55889`。双解释器各1465项（原1149 IDs全保留、新增316）、双strict typing48、新包/双干净安装及源码外组合smoke采用已独立核验执行回执，reviewer未冒称重跑全矩阵或重建/重装，另实际复查两安装导入。R1历史guard失败、preflight partial和原证据均保持原身份，不混充最终通过。

contact与T05审计分离、独立region端点计数、完整source/scope与公开neutral/captured验证已核实；完整坐标、有效region occupancy、外部body/U06、FIN/器件/标注、其余mandatory/lifecycle、baseline/no_change/terminal/Stage6及真实PDK/EDA仍后置。有限资源记录披露重复认证、约23MB含cache正常wire和约988MiB累积RSS高水位，未测大量多片/最大规模，不作生产性能保证。Reviewer只修改本Review段、代码review报告与独立附件，未改产品/正式测试/PM/current-work，未验收、合main、提交或推送。

### R2 独立合并前复核（2026-11-06）

本独立 session reviewer `/root` 及未参与原设计/实施的数学、来源、异常和工程专项，对 **main `3be0b98359038bab6c23980b55a48987cc71a369` → 待审HEAD `c4909ab679d0c0806200fcb132db8a5de1ad3e75` 完整交付**复核，以准备 `9758a157…` → 冻结产品 `0f5029d…` 定位实现；远端身份一致，原 checkout 保留，独立 worktree 完成审查。**新增及剩余必须修正项0，建议PM进入集成及组合验证。** 这是独立review建议，不代写PM验收或集成事实。见[完整报告](W010/independent-premerge-review.md)及[独立证据](W010/independent-premerge-review/delivery-audit.json)。

本次Python3.12.14完整v2 **1465 passed / 3076.64s**、strict typing **48模块**及pip check均exit0；独立新编3200+15数学判据、14个完整captured几何变体及3个策略拒绝、31项来源/公开完整性、260项异常/不可变边界和另8项FXR-01集合快照均通过。其中159个故障保持原exception及既有cause/context/suppression，含56条真实ContactProblem后再次认证路径；未以success decode或任意异常拒绝代替该边界验证。正常完整14/8/6/16、cut-islands3/0/3、VN边保留且LI侧violation、重复来源/独立端点/完整分组均有本次独立集合与图判据。

工程45/45审计核对252源/归档、两包94runtime、原1149 nodeid保留/新增316及具名依赖守卫；旧218项delivery按 **ca39aed版本Git内容**匹配。原双解释器/构建/双干净安装按身份采信，历史安装树本机不存在，不冒称重新安装或观察历史执行。两次source probe编排失败原样保留并与最终通过分开。唯一非阻塞建议E-N01（P3）为资源摘要下界应含cut-islands约12.58MB；不改变已披露最大成本或max-pieces=1等限制。本轮仅写review报告/附件和本段；产品、正式测试、fixture/答案、历史证据、PM/current-work不改，完整工艺坐标、外部body/U06、FIN/器件/标注、其余mandatory/lifecycle及发布闭合继续后置。

## PM验收与交接（PM）

最初派发时仅准备W010；当前阶段以下文最新PM记录为准。W009已验收并集成，不把新图草稿视为完整ConnectivityState或M1闭环。

**派发要求独立复核（2026-11-04）：** 未参与范围调查/任务起草的`/root/w010_handoff_review`对照架构、实际owner/样本及W008/W009接口，必须修正项0，见[独立记录](W010/handoff-review.md)。初审任务SHA-256 `b14f7051591a8ace8b888e62248afbaa29bc6f8f61dedff093b351c0c01ec4fa`；随后采纳两项非阻塞澄清：新增rules的payload与实际捕获source role绑定；重复connector保留各record/audit，并区分重复导体region的端点歧义。澄清稿SHA-256 `215bd28756437a019fe7ba6a5471bb7c23f238cb0d4e1173197ed1333879718e`，本阶段/PM接收补记未改其行为要求与A1–A8；最终文本身份由独立报告追加。

最初派发阶段为可执行，要求独立执行session先方案review后实现；当时尚无W010产品验证或验收，本段保留原派发事实。

<a id="pm1-receipt-20261106"></a>

### PM1 分支技术接收（2026-11-06）

已核对远端交付`ca39aedcb71fda02f77ffda1eb5d5dddc598226e`、冻结产品`0f5029df935bc0acd106aad1bc2be81304d4f442`、A1–A8覆盖及方案/代码独立review。PM实际Python3.12定向正式回归**50 passed / 233.81s**、原独立主probe direct/readback真实14节点/8边/6分量/16audit通过、strict typing **48模块通过**；新增独立512掩码的12,288接触/5,120有理包围/8,704等覆盖比较均通过。**分支技术接收通过，本次新增必须修正项0；待最终验收。**

252项源/完整tar、两包各94runtime、21条命令42份原输出、原1149保留/新增316、review及218项交付身份均已实核。原双解释器完整各1465项、双typing/构建/双干净安装及更广独立边界矩阵按最终身份采信；本机未重跑完整矩阵或重建/安装，原实际安装/测试树不在本机。详见[PM接收说明](W010/pm-receipt.md)及[机器回执](W010/pm-receipt.json)；旧交付清单对应ca39版本，本次PM状态追加不改写旧hash。

PM专项不冒称新的独立premerge session已经完成。下一步单独session合并前复核，通过后再main集成及组合验证；本轮未合main或启动下一任务。contact与局部T05分离、来源/scope/异常边界已核验，完整工艺坐标/body/FIN/器件/标注、其余mandatory/发布和U06仍后置，未宣称完整M1或生产准入。

### 独立执行session prompt

```text
按Layauto项目规范，以执行角色完成W010“局部接触与物理连通草稿”。
从codex/w010-local-contact-connectivity的PM交接提交恢复；main起点3be0b98359038bab6c23980b55a48987cc71a369，W009已由PR #63验收集成。先核对远端/HEAD/工作区，读AGENTS、协作/环境规则、current-work、W010及其架构/样本/上游合同引用。
先细化同源输入与算子、独立region节点/端点、exact contact与独立enclosure、完整component及scope、公开DTO/wire/失败和资源方案，经独立review后实现A1–A8。普通算法/DTO/索引选择自主处理，不引入legacy/tests-support runtime依赖。
从真实W005/W006→W008→W009构建本地物理图；同层正面积/正长度边、跨层唯一region正面积才成边。connector不是导体stamp；多端点不能先component合并或enclosure筛掉。包围失败仍保留实际edge，独立报告T05；孔洞/多片按exact集合，单位不floor/snap。外部body不union，本地BODY只作几何节点，不按net名建边。
保留原1149项及来源/输入/attempt；完成正常14/8/6、cut-islands3/0、via_enclosure边保留但违例、独立数学/歧义/公开重建/完整嵌套异常链验证，双解释器完整回归、typing、新包/双干净安装源码外smoke和最终身份记录。
独立代码review后修正复核必须项，保存原finding和阶段证据，提交推送原W010分支并核对远端完整SHA，交PM；不自行验收、合main、改current-work、删分支或启动下一任务。完整坐标/外部body/FIN器件/标注/通用规则/发布及U06继续后置，新增关键输入解释带具体实例交PM。
```
