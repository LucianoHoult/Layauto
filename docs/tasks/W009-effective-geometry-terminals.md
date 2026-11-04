# W009 — 有效几何与沟道、端区草稿

把W008保存的原始图形进一步解释为当前已声明toy算子作用后的精确区域：CUT实际扣掉了哪里，OD与POLY交叉的沟道在哪里，扣除沟道后哪些区域分别是几何意义上的S/D端区。保留原始drawn图形与全部来源，供后续物理连通、标注和提取使用。

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| ID / 目标 | W009；从认证的W008几何产物及同源physical/drawn/formats声明构造只读、精确、可重建的有效几何与channel/terminal区域草稿 |
| 里程碑 / 依赖 | M1第五个产品切片；W003/W004样本、W005读取、W006审计、W007语义/身份和W008基础几何已验收集成。main起点`4df07e68b05df4c57a8b8d44bc41e7e073938d3a`，W008产品经[PR #62](https://github.com/LucianoHoult/Layauto/pull/62)集成，见[W008 PM2](W008-geometry-base-occupancy.md#pm2-integration-20261103) |
| 授权依据 / 阶段 | 用户2026-11-04交回补修及独立复核，沿用独立session分工。**待验收：IPMR-01、FXR-01已独立关闭并经PM重新接收，剩余必须修正项0，可进入main集成与组合验证。** 当前尚未集成或最终验收，见[PM3](#pm3-ipmr01-receipt-20261104) |
| 恢复位置 | `codex/w009-effective-geometry-terminals`，补修交付`6cb4ecc2ecaa8bd6e5236b28b70149d9a4917534`，产品/正式测试`73e38df8f932bbb5bd9caf074b442ad2f5c286e9`；接手包含PM3及current-work补记的最新提交，完整SHA见Git/回复。main仍为上述起点 |
| 允许修改 | `layauto_v2/domain/`必要中立区域/算子/来源DTO；`state/`内有效几何/区域草稿纯组件；`normalization/`适配、组合与codec；必要的同范围tech校验复用；对应tests、typing/build配置、README及本任务附件。模块/类型名由内部方案选择 |
| 非目标 | 不实现完整工艺坐标/合法routing lattice、全层导通图/connector edges、电气ComponentId、body-to-rail证明、fin计数/完整器件提取、query spatial overlay、规则执行器/CSP、lifecycle最终闭合、baseline/seal/发布、ECO/no_change/terminal/Stage6；不改fixture/答案/历史证据，不新增生产格式或MR-040配置机制 |
| 架构依据 | 本次main的[architecture](../architecture.md) §2.2–2.3、§3.1/3.4–3.6、§4.5–4.8、§5.6–5.9、§11.2–11.3/11.14–11.15、§12.3/12.5；[W003 contracts](W003/contracts.md)、[manual review](W003/manual-verification.md) MR-045/046（以W004修订后的body合同为准）、MR-052/054/056；W007/W008输入、身份、单位及公开结果合同 |
| 负责人 / 分工 | 一名执行者集成；未参与方案/实现者分别复核方案和代码；PM维护任务要求、阶段、入口与验收。原范围内的算法/DTO选择自主处理 |

### 已核对事实与本次拆分理由

- 当前[physical owner](../../tests/fixtures/w003_m1/tech/physical.json)声明`identity_OD`、`positive_area_OD_intersect_POLY_with_exactly_one_gate_stripe_per_active`、`terminal_split/1`及“OD扣除channel后，左连通区域为S、右为D；不支持swap”。`POLY`导体穿过沟道连续，器件S/D关系不是导体边。
- [drawn owner](../../tests/fixtures/w003_m1/tech/drawn.json)声明CUT的`cut_target=LI`和`rectangle_set_difference/1`。该算子要求精确集合相减、保留全部正面积结果并区分分离区域，不把差集外接bbox当有效几何。
- W008的GeometryInput已重新解析同一捕获中的全部tech owner；GeometryResult保存认证输入、完整drawn layout及base occupancy。新增消费的physical字段仍须绑定该owner与捕获，不能从另一份可变配置接入。
- [coordinate示例](../../tests/fixtures/w003_m1/tech/coordinate.json)仍是`example_only=true`、`is_complete_runtime_model=false`。本轮集合运算直接使用已验证的exact坐标，可独立交付；不能把内部边界分区或FIN pitch升级为完整合法工艺网格。完整坐标模型继续保留为Stage2后续义务。
- W008逐层base partition只采用该层drawn边界，LI轴不保证包含CUT边界，OD轴也不保证包含channel边界。不能按整格删减或标注有效区域；raw occupancy可作候选索引，结果须按exact几何计算，并保持原raw覆盖合同。
- 正常样本独立答案中的四个OD端区，以及[cut-islands答案](../../tests/fixtures/w003_m1/special/cut_islands/oracle.json)的两块LI差集已有明确几何依据。答案中的net、component、spacing、body和终态不属于本轮验收成功声明。

### 行为要求

1. **消费认证输入，保持纯组件组合。** 支持真实W005→W008及W006 readback→W008两条路径，不重新读文件或repository、不调用EDA。若需要同源W007结果，只能核验关联并保留source/target/differences/seeds；不得靠query名称或CDL端口决定几何。公开成功结果绑定完整W008输入身份、消费的owner/算子版本和exact单位；中立DTO自洽与最终捕获认证分层，domain/state不得反向依赖parser。
2. **只执行明确支持的算子语义。** 从唯一owner取得CUT目标、差集、active/channel与terminal解释。显式检查所消费的operator/profile语义与版本，不能只看同名ref存在或capability=true就接受；不执行配置中的任意表达式。已有W005缺项/不支持错误继续保留；本轮组件不假称整个required_operator列表已经实现。需要改变输入解释或扩大支持子集时，先交具体实例与影响给PM。
3. **精确差集保留所有区域及来源。** 对目标drawn record扣除适用CUT集合；多个/重复/重叠CUT按集合语义处理，结果与输入排列无关，未命中CUT不改变几何，全覆盖产生明确的空结果。保留每个原record及贡献CUT的来源/身份，重复原record不能被bbox去重而丢失追溯。可采用规范化的精确矩形集合表示多片、孔洞和非矩形结果；每个结果都能回到原drawn及operator。raw layout与W008 base occupancy不被改写，不把有效片段冒充新的drawn输入。
4. **按选定profile识别channel和端区。** 先用正面积OD∩POLY识别每个active内唯一gate stripe；无gate、多gate或无法唯一确定时按该profile定位拒绝。点/边接触不能冒充正面积channel。OD扣除channel后的所有正面积残余都须解释；若不能形成该profile明确的左右S/D区域，拒绝而不丢片或猜方位。沟道与端区内部不重叠，其并集应还原适用active。POLY原图形保持；不得由此建立S↔D导体边。几何区域的内部连通分组仅为差集/端区计算服务，不是跨record电气连通图。
5. **区域身份与消费边界明确。** 区域及其矩形分解具有稳定typed refs，绑定来源、单位、算子和exact几何；区分原record重数、集合覆盖和区域分解，不能因遍历顺序不同改变同一结果的语义。输出S/D只表示当前toy空间规则，尚未完成canonical DeviceId/net join或完整DeviceExtractionContract。非消费图形及外部body证据保持原独立引用；body、FIN、marker等不因本轮处理而被删除或宣称已经解释。
6. **可验证的不可变结果及错误。** 区域/集合/结果使用closed/versioned合同、递归不可变、canonical wire/digest和公开constructor/decode聚合检查；拒绝漏片、多片、外来来源/单位/算子、bbox填洞和伪造success。预期问题定位到source/field并保留已完成事实；意外Exception及KeyboardInterrupt/SystemExit按纯组件边界传播。成功仅表示本次几何运算完成，不推进W006 attempt、不发布baseline或terminal。

### 验收清单

| ID | 输入/条件 → 可观察结果 | 正确性依据与验证 |
| --- | --- | --- |
| A1 真实组合与来源 | 实际W005/W006捕获→W008→新草稿等价；构建无IO、原语义/图形/base occupancy/attempt不变 | 禁用构建期间文件/repository IO；错误run/来源/owner与成组payload伪造反例；不加载expected/spec/oracle为运行输入 |
| A2 算子与作用域 | 只消费声明CUT目标及active/channel/terminal操作，拒绝未知/矛盾的已消费算子或错policy/单位 | 从捕获owner逐字段核对；支持范围明确，保留旧读取/异常边界，不扩展生产profile |
| A3 差集数学 | 单CUT、多CUT、重复/重叠CUT、孔洞/多片、边角接触、未命中及全覆盖 → 精确无漏无额外覆盖 | 独立手算/面积/点归属与集合等价判据，不仅拿另一个调用同算法的helper比较；负坐标、大整数及重排检查，不float/snap/截断 |
| A4 沟道与端区 | 正常2个active/2个channel/4个OD端区与手工答案几何相符；无gate、多gate、点边相触、channel不能分开端区等拒绝 | 按实际OD/POLY构造；检查channel+残余的完整覆盖、S/D唯一性和来源，不使用ON/OP等展示名或输入record序号硬编码；不把正常数量当唯一oracle |
| A5 既有特殊见证 | cut-islands中LB被切为`[130,20,139,24]`和`[141,20,150,24]` nm，面积合计72；独立A_REMOTE仍保留 | 从实际special GDS构造；可在临时目录重绑所需header/输入以隔离几何条件，原fixture不改。只取几何答案，不声称component_count、spacing/T06/T08/T10已通过 |
| A6 公开合同与稳定性 | 递归mutation/alias、遗漏/重复/外来区域、改operator/unit/source、非法success与嵌套wire拒绝；重建/重排稳定 | typed refs、canonical roundtrip及跨hash-seed检查；验证边界与数学集合语义均独立检查，异常/中断同对象传播 |
| A7 范围与后续接口 | 保留原drawn/occupancy/semantic/query/body证据；输出区域可被后续geometry/contact/overlay消费者引用 | 不新增全层physical edge、电气ComponentId、net stamp、fin/body完整证明或publish/no_change；完整坐标/有效region投影与所有后续义务有明确交接 |
| A8 工程与交付 | 保留原730项能力，新增必要独立判据；Python3.10及开发解释器、strict typing、新包及两套干净安装/源码外真实组合smoke通过 | 记录最终源码/测试/配置、命令/环境/输出、包与安装来源；评价算法复杂度/片段增长并披露已测规模，不把有限样例当全规模性能保证，不静默新增外部限制 |

新输入格式或使用预期：**当前无必需用户决定。** 算法分解、内部DTO、registry组织属于既定语义内的实现选择，先由执行者准备方案并独立review。若发现既有profile不足以解释具体输入，保留可处理范围并以实例上报，不扩大多gate/S-D规则或编造完整coordinate默认值。

### 后续组合归属（不计作本轮完成）

| 后续能力 | 保留义务 |
| --- | --- |
| 正式坐标与region投影 | 完整逐层axes/pitch/offset/方向及来源、合法空间/coordinate binding；有效region与occupancy/annotation目标的精确覆盖及身份。不得以本轮算子矩形分解替代 |
| 局部物理连通 | same-layer contact、qualified via/contact、component identity/lineage；正面积/正长度边/点接触区别，connector不得via-as-wire双写，enclosure仍为独立必需检查 |
| 器件提取与标注 | FIN/channel qualification、one-to-one semantic/device join、D/G/S/B/模型/参数核对、query spatial overlay/coverage/conflict及保守unknown分类 |
| body及U06 | D1=A既有synthetic上下文证明；[U06](../roadmap.md#production-body-evidence)叶cell缺外部tapcell/全局电源上下文的最小输入、部分能力与完整准入方案。人工net标注不等于物理证明，scope外关联不在本地图添加物理边 |
| M1运行闭合 | 全量mandatory rules、逐层lifecycle、完整ProposedInitialState、原子baseline/seal、semantic/extraction-aware no_change、Stage6读回/报告/terminal；真实G1–G4/G5及生产边界保持 |

## 方案与决定（执行准备，PM 接收）

执行者先调查现有GeometryInput/GeometryResult、drawn与physical owner，以及legacy中与矩形集合运算相关的纯算法候选；不得依赖tests/support或legacy runtime。方案至少说明：捕获与算子绑定、集合/区域/record所有权、exact差集与分解的确定性、channel/端区适用条件、public DTO/codec及错误、原730项兼容、独立判据和资源复杂度。明确集合/边界表达与W008半开索引、后续接触判据的关系；正确性结合包含/交叠/点归属及边角反例，不能仅凭面积相等判断。未参与设计者review后，原范围内修正并实现。

执行方案已落实，见[细化方案](W009/plan.md)及[独立方案review](W009/plan-review.md)。IR-01按实际owner纠正角色校验并独立关闭；方案review先于产品实现。执行者只选择既定范围内的算法、DTO和codec，不修改任务要求或PM验收。

## 执行结果（执行）

### E1 实现与验证交接（2026-11-03，执行）

从用户指定的`4975e565a33d9594782645b6ad0f944b78ee6ae8`恢复，初始工作区干净，沿用`codex/w009-effective-geometry-terminals`。先完成细化方案与独立review，再实现认证W008→exact CUT/channel/左右S-D区域草稿、typed refs、不可变DTO/closed wire及聚合校验。raw drawn/base occupancy、W007语义/query及body独立证据保持。

[执行交接](W009/execution.md)记录A1–A8判据、范围、算法复杂度和后续义务。独立代码review的CR-01涉及neutral aggregate decode意外异常被翻译，CR-02涉及literal/旧子值可变别名进入公有constructor；均已按原范围修复，新增同对象传播及closed-value反例，并按修后身份重跑最终矩阵；finding原文及独立复核由reviewer维护。最终双解释器、typing、新包/两套干净安装及源码外组合结果见[最终回执](W009/verification/receipt.json)；最终源码身份见[清单](W009/verification/source-manifest.json)。最终提交/远端完整SHA由Git与执行回复核对，PM接收后另行验收；本段不宣称PM验收、main集成或完整Stage2/M1通过。

### E2 最终验证与交 PM（2026-11-03，执行）

最终 Python 3.12.14 / 3.10.22 各 **914 passed**，保留原730项并新增184项；双 strict mypy 各44模块、依赖检查、新wheel/sdist、两套全新安装及真正checkout外`-I -B`实际W005/W006→W008→W009组合、codec和组件错误smoke全通过。两个包与两个安装目录各90个runtime文件逐字节匹配最终源码。

[240项最终清单](W009/verification/source-manifest.json) SHA-256为`32e60e783a7a7e4172ee3916e3ceb4fade329585b87a7c7091a85c8a6418d1b6`；[完整快照](W009/verification/source-snapshot.tar.gz)为`5ed2228559ea6dcf7a1417e19b8f706f1e88283edfca0c01809489cb147ec727`。15项实际命令、原始输出、包与安装来源见[最终回执](W009/verification/receipt.json)及执行交接。修前/中止结果分别保存原版本身份，不混充最终通过。

独立review修正项处置与剩余数量由下节及reviewer报告维护。执行交付提交推送沿用项目noreply身份，远端完整SHA在Git与执行回复核对；PM从当前W009分支接收并决定验收/集成。未合并main、未改current-work/PM要求段，未启动下一任务。


### E3 IPMR-01 完整嵌套解码补修（2026-11-03，执行）

从指定恢复提交 `cdf3d2d5d2aeb0c441221c8bb0b41d0b302d8afa` 在原分支隔离工作树执行，原 checkout/远端 main 保持。按 [补修要求](W009/ipmr01-fix-task.md) 修复 W009 复用 W008 layout/partition/occupancy 的 constructor 异常包裹，并处理实际确认的 semantic receipt/readback/captured SourceFile 同链边界；畸形字段通过显式结构/类型/引用/索引检查拒绝，输入认证、wire/schema、数学与不可变合同保持。原 finding、历史报告及 PM1/PM2 均保留。

[本轮执行交接](W009/ipmr01-fix.md)记录调用链、追加反例、235项正式新回归、各版本及验证范围；[新证据目录](W009/ipmr01-verification/README.md)保存最终245项源/测试/配置清单、原99项异常矩阵、既有cause/context、畸形对照和双解释器/新包/两套源码外干净安装材料。最终Python3.12完整**1149项**、Python3.10受影响**988项**、双typing各44源模块、新wheel/sdist及两套源码外干净安装smoke通过；原99矩阵达到99/99且失败列表为空。3.10其余unit parser未重跑，范围与版本限制见本轮执行交接及机器回执。独立review由未承担修复者维护下节及单独报告；执行者不代写关闭或 PM 验收。最终分支/远端完整SHA在Git及执行交回时核对，不修改PM阶段/current-work、不合main或启动后续任务。

## Review 结论（reviewer）

### R1 独立方案、代码及修正复核（2026-11-03）

[方案review](W009/plan-review.md)由未参与设计的`/root/plan_review`完成，IR-01已关闭。代码review由未参与原方案/实现的`/root/code_review`完成，并包含独立数学及closed-value专项；[完整报告](W009/code-review.md)保留CR-01异常身份和CR-02原对象图/容器/数值别名的原finding、具体反例、执行修正和独立复核。**代码审查完成，两项finding均关闭，剩余必须修正项0。** 本结论不是PM验收或合并决定。

Reviewer直接执行过W009新增117项、3.10定向8项、修正阶段双解释器各43项，并在最终源码重新执行双解释器各67项closed-value回归及独立1,515组集合/585,511点；异常身份与literal/borrowed/container/metaclass/Fraction反例按实际阶段保存，未把中间版本冒充最终交付。最终源码及工程证据核验见下段。

### R2 最终身份及工程证据核验（2026-11-03）

Reviewer对最终`32e60e783a7a7e4172ee3916e3ceb4fade329585b87a7c7091a85c8a6418d1b6`清单240项、完整源码tar240项、两包与两实际安装各90项runtime逐字节核对，均一致；最终数学/closed probe结果的源码SHA亦等于该清单。[最终独立审计](W009/review/final-evidence-audit.json)核验15项命令exit0及原始输出hash；[归档审计](W009/review/final-archive-evidence-audit.json)另核验117个证据文件hash。

最终Python3.12.14/3.10.22各**914 passed**、strict mypy各44模块，以及build、pip check和两次真实checkout外`-I -B`源码包组合smoke，采用已独立核验的执行回执；reviewer未冒称重跑全部矩阵或重建安装。[包来源/安装树独立审计](W009/review/package-audit.json)确认直接artifact URL/hash、site-packages来源及源码外cwd。**最终代码与工程证据审查完成，剩余必须修正项0，建议交PM核验接收。** 这不是PM验收或合并决定；完整坐标、connectivity/body/extraction、baseline/terminal及生产义务仍按原范围后置。

### R3 独立合并前复核（2026-11-03）

本次独立 reviewer session 对 `main@4df07e68b05df4c57a8b8d44bc41e7e073938d3a` 至待审 `88a7ae9d0330b7c7fddda0b07366c7a96552b65e` 的完整交付复核，并以准备 `4975e565…` 至产品 `5b1d9b51…` 定位实现，按 PM1 恢复；未只审最后一个 PM 提交。详见[独立合并前报告](W009/independent-premerge-review.md)与[可复验材料](W009/independent-premerge-review/)。

**剩余必须修正项 1（IPMR-01，P2），暂不建议 PM 进入集成。** 合法 W009 draft/result wire 的嵌套 W008 base 重建仍经旧 geometry codec broad catch，将内部 TypeError/KeyError/AttributeError/IndexError/UnicodeError 改写为新 ValueError；99项独立矩阵中30项失去原对象，主 reviewer 另行最小复现。原 CR-01 对 W009 自身算法路径的修正确实生效，但完整嵌套链关闭不充分；原 IR-01、CR-02 的关闭仍有独立依据。保留原 finding/报告和 PM1，不由本节改写历史结论、验收标准或 PM 阶段。

本次 Python3.12完整 v2 **914 passed / 1010.02s**、strict typing **44模块**通过；新独立几何4418组/521222点、原对象图31反例/7快照及来源/畸形wire26项已实跑。240项源码/快照、117证据、15命令输出、两包各90项runtime和最终修正身份匹配；旧安装树不在本机，原双解释器/构建/干净安装按身份采信，未冒称重装或重新观察历史执行。详细结果见本次报告和原始回执。修正后须独立复核受影响路径和最终交付身份，再交 PM 决定集成；本轮未改产品、正式测试、fixture/答案、历史证据、PM 段或 current-work，未自行验收、合并或启动后续任务。

### R4 IPMR-01 局部修后独立复核（2026-11-03，11-04恢复工程审计）

未参与补修实现的 `/root/ipmr01_independent_review` 在独立 worktree 审查恢复 `cdf3d2d5d2aeb0c441221c8bb0b41d0b302d8afa` → 最终产品/正式测试 `73e38df8f932bbb5bd9caf074b442ad2f5c286e9` 的完整11文件diff（8 runtime、3正式测试），见[修后独立报告](W009/ipmr01-fix-review.md)。原 IPMR-01、CR-01/CR-02、R1–R3 及 PM1/PM2 原文和历史失败材料保持。

最终源码独立实跑原99项异常矩阵，明确核对 **99/99/identity_failures=[]**；另有267项W008公有wire畸形拒绝、33项constructor/完整W009 result receipt对照、1184项捕获wire变异、真实W005/W006无IO组合及36项完整readback既有cause/context保真。独立新增FXR-01指出本轮集合校验/保存两次迭代导致非法快照或裸AttributeError；执行者已修为一次快照，原反例和双向8项正式回归由未参与修复者独立关闭。**IPMR-01与FXR-01已关闭，剩余必须修正项0。**

11月4日恢复后独立核对245项最终源/快照、两包与两实际安装各90 runtime、24份总回执命令及全部原始输出hash一致，见[工程审计](W009/ipmr01-verification/review/engineering-audit.json)。16份已完成R3构建/安装/smoke保留11月3日身份，断连partial归档不计通过，8份缺失环境/pytest/typing/pip回执从头补跑；原产品probe输出身份未变。最终Python3.12完整**1149 passed / 1069.07s**、Python3.10全部contracts加W006 publication unit **988 passed / 1465.64s**、双typing各44模块和依赖检查通过；3.10其余parser unit未重跑。Reviewer实际读包/安装树但未冒称重建或重装，新增认证检查后的绝对性能未重测。**独立产品及工程复核完成，建议交PM核验接收；本段不代写PM验收或集成决定。**

## PM 验收与交接（PM）

最初派发时仅准备W009范围与独立执行入口；当前阶段以下文最新PM记录为准。既有W008及更早任务的验收事实保持。

**派发要求独立复核（2026-11-03，PM记录）：** 未参与草稿设计的`/root/w009_handoff_review`对照架构、实际owner/样本、W008接口和U06边界检查，必须修正项0，见[独立记录](W009/handoff-review.md)。原受审草稿SHA-256为`858f3a6e06350e36dd1760cc37cf2a0d7ef890301d7178ce6380c6a4f54d15b7`；此后采纳两项非阻塞澄清：逐层raw轴不保证包含CUT/channel边界，以及集合正确性不能仅凭面积判断。本记录与阶段补记不代表未来方案/代码review或产品验证。

<a id="pm1-receipt-20261103"></a>

### PM1 分支技术接收（2026-11-03）

已核对远端交付`5b1d9b5196a7c5181822c4dd0f1bd2f678475116`、A1–A8覆盖、IR-01/CR-01/CR-02独立关闭及最终源码/证据身份。PM实际Python3.12完整**914 passed / 599.29s**、strict typing **44模块**通过；18项异常同对象、Fraction别名拒绝及独立512组几何穷举通过。源码/归档240项、证据117项、两包各90项runtime与交付一致，fixture及历史材料未改。**分支技术接收通过，本次新增必须修正项0；待最终验收。**

详见[PM接收说明](W009/pm-receipt.md)和[机器回执](W009/pm-receipt.json)。原双解释器/干净安装证据按最终身份采信；本机未重建/重装或重跑3.10，原安装树不在本机。PM专项不冒称新的独立premerge session已完成。下一步单独session合并前复核，再做main集成及组合验证；本轮未合并、未启动W010。完整Stage2/M1、真实EDA与U06生产缺外部body上下文义务继续保留。

<a id="pm2-ipmr01-20261103"></a>

### PM2 接收独立合并前复核及补修派发（2026-11-03）

接收review交付`386a139c38e815086fafc183ea73ea650e72cc5b`，见[独立报告](W009/independent-premerge-review.md)。**IPMR-01为P2必须修正，剩余1项，暂缓集成。** PM实际重跑原最小复现：合法W009 wire的base occupancy重建出现内部TypeError，经旧geometry decoder改成ValueError，原对象仅留在cause；[回执](W009/ipmr01-pm-confirmation/reproduce-receipt.json)明确记录合同failed，脚本exit0表示复现缺陷。

原PM1和CR-01所测W009自有算法路径保持异常对象，但未覆盖复用的layout/partition/occupancy完整嵌套链；原“0项”是当时覆盖下的历史结论，当前A6不满足，以本PM2为准。正常几何、来源、原对象图和914项/44模块记录不被改写，也不能替代缺失错误路径的修正。

已建立[IPMR-01局部补修交接及执行prompt](W009/ipmr01-fix-task.md)，允许在直接复用的W008 decoder及必要DTO边界作最窄且完整修复；必须同时验证99项异常同对象矩阵和畸形输入拒绝，并更新受影响最终源码/包/测试证据。修后由未承担实现者独立复核，再交PM重新接收。当前未修产品，未合main或启动W010。

<a id="pm3-ipmr01-receipt-20261104"></a>

### PM3 补修重新接收（2026-11-04）

核对补修交付`6cb4ecc2ecaa8bd6e5236b28b70149d9a4917534`、产品`73e38df8f932bbb5bd9caf074b442ad2f5c286e9`及完整11文件产品/正式测试diff。[独立修后复核](W009/ipmr01-fix-review.md)确认IPMR-01与追加FXR-01关闭；PM再次实跑全部新增正式回归**235 passed / 316.54s**、原异常矩阵**99/99同对象、identity_failures=[]**和strict typing **44模块通过**，代码专项另41例通过，未发现新增必须修正。

245项源/完整tar、两包各90项runtime、24命令原输出及16沿用/8恢复重跑/14中断归档身份已实核一致。采用原最终3.12完整**1149项**、3.10受影响**988项**及新包/双干净安装证据；本机未重跑完整1149/3.10或重建/安装，原实际安装树不在本机，未冒称重新遍历。详见[PM重新接收说明](W009/ipmr01-pm-receipt.md)及[机器回执](W009/ipmr01-pm-receipt.json)。原失败与历史通过记录各保留原身份。

**补修分支接收通过，当前剩余必须修正项0，解除IPMR-01集成阻塞；阶段待验收。** 原独立合并前复核加本次独立修后复核已有完整交接，下一步main集成及组合验证后记录最终验收。本轮未合main或启动W010；完整M1/真实EDA与U06后续义务保持。

<a id="独立执行session-prompt"></a>

### 独立执行session prompt（原派发，保留）

```text
按Layauto项目规范，以执行角色完成W009“有效几何与沟道、端区草稿”。
从codex/w009-effective-geometry-terminals的PM交接提交恢复；main起点4df07e68b05df4c57a8b8d44bc41e7e073938d3a，W008已验收集成。先核对远端/HEAD/工作区，读AGENTS、README、协作/环境规则、current-work、W009及其引用的架构原文与W003–W008合同。
先细化认证输入/physical算子绑定、exact集合差集、channel/端区识别、区域身份/来源、不可变DTO/codec/错误及独立判据方案，并由未参与设计者review；原范围内修正后直接实现A1–A8。
从真实W005/W006→W008捕获产物构造CUT后的有效区域及OD/POLY channel、OD减channel后的toy左右S/D区域；保留全部来源、原drawn/base occupancy和W007语义/query。不得加载答案为运行输入、按展示名硬编码、float/snap、bbox填洞、漏掉差集片段或由S/D关系造导体边。
本轮不实现完整工艺坐标、全层导通图/connector、电气component、body证明/FIN完整抽取/query overlay、DRC/CSP、baseline/seal/no_change/Stage6；U06继续由后续生产输入/body任务落实，不改body_context必填或fixture。新增关键输入解释先以具体实例交PM，普通算法与模块选择自主处理。
保留既有730项能力，完成独立数学/真实组合/公共DTO反例、双解释器、typing、新包/两套干净安装/源码外smoke；保存最终身份、原输出和未验证范围。独立代码review后修正并复核必须修正项。
将产品、测试、可访问证据及执行/reviewer记录提交推送当前W009分支，沿用项目noreply身份，核对远端完整SHA后交PM。不得自行验收、合并main、删除分支或启动下一任务。
```
