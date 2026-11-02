# W005 — 读取真实文件并核对输入绑定

把已验收的样本交给正式v2读取组件：从GDS、source/target CDL、raw query与配置读出可追溯的内容；文件缺失、格式不支持或来源不一致时给出明确错误。成功输出可供后续Stage 2消费的evidence，不从样张加载预制状态。

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| 目标 / 依赖 | M1的首个产品组件切片；依赖已验收的W003/W004样本，实物基准`633e3feef8062565019838f2d270e89b7f81c4ed`。W002 E7的完整no_change闭环目标及R4首交义务保持 |
| 授权 / 阶段 | 2026-10-31用户同意PM清单整理、同步验收记录及准备最小读取任务。**可执行：下一执行session按本任务实现读取/绑定组件；本PM session仅准备任务和文档。** 无当前输入语义待决项 |
| 输出边界 | 一个可由测试及未来pipeline调用的组件API，返回不可变、经过运行时校验的配置/tech及versioned evidence、解析结果和定位信息。名称/DTO组织由执行者细化并review；本轮不发布新的稳定CLI或对外wire承诺 |
| 允许修改 | `layauto_v2/importers/`，必要的中立`domain/` evidence/results/codec类型、`tech/` schema与纯读取公共入口；`tests/unit/`、`tests/contracts/`及读取组合测试；必要依赖/typing/build配置与使用说明、本任务执行记录。新增目录按职责创建，不为所有未来模块填空 |
| 非目标 | 不实现pipeline/run入口、repository/RunAttempt/terminal publication、Stage 2 identity/spatial join与状态、规则求值/resize/导出、真实Calibre/Virtuoso获取或生产上传；不改变D1=A、MR-040后置及真实工具延期。不修改已验收fixture以迎合程序 |
| 架构依据 | [architecture](../architecture.md) §2.1–2.3、§3.1–3.2、§4.8、§5、§11.2/11.10/11.13–11.15、§12.1–12.8；架构原文优先，任务不另定产品合同 |
| 分工 / 阻塞 | 一名执行者统一集成；未参与实现者做接口/最终代码review，PM核对结果。当前无阻塞；普通内部选择自主处理，新关键输入/能力/对外行为变化附实例交PM |

### 输入、结果与范围

1. **配置与技术资料。** 从实际site文件所在目录解析路径，读取其选择的GDS、source/target CDL、query header、body context、tech六owner及policy/limitations。仅接纳已声明版本/字段和`dummy_fixture`输入范围；校验必需项、唯一owner、跨字段/registry引用、单位/模型合同及重复outputs一致性。safe YAML/JSON拒绝重复/未知key、错误类型/版本、可执行tag、非有限数及超size/depth；阈值与测量约定须来自明确schema/profile并在测试中给边界，不照抄helper固定答案冒充通用loader。
2. **GDS。** 逐record解析当前flat轴对齐BOUNDARY矩形子集，完整保留top、element-tagged layer/datatype、原整数XY及REAL8原bytes/exact值。矩形须逐个证明lossless；支持范围外的元素、层键、hierarchy、property、非矩形明确拒绝。使用精确单位合同验证nominal scale，不能先转float再恢复精度、取整或补图。未注释MARK等可支持几何同样保留。
3. **CDL。** 解析source/target全部top、ordered pins、globals、模型、有序D/G/S/B及参数lexeme/exact值，保留文档/空依赖闭包来源。所选literal dialect之外的表达式、include、未知directive/参数及非法值明确报错。返回两份可追溯解析结果；不据5/7相等宣称no_change，不在reader做目标规划。
4. **Query。** 从实际9份raw及requests/dialect读取四种capability。落实格式内必要的nXref/NET NAMES/response关联、数量/结束结构、opaque metadata、完整polygon、坐标顺序/precision、具名exact值/quality及原文位置。区别这种格式关联与Stage 2跨GDS/CDL的语义/空间join。normalized只作可重新解析的缓存/测试期望；若提供则比较并拒绝漂移，不能作为唯一输入绕过raw。缺normalized的合法输入仍可解析；坏raw配套删缓存仍须按坏raw原因失败。
5. **绑定与来源。** 对本次实际读取bytes核验source/top、完整raw列表、netlist/deck/map/runset/include/preprocess/options闭包、body输入及tech叶子和parser/dialect版本；读取内容与校验hash必须是同一份bytes。核对query-run/database身份、tool信息、mode/classification/assurance、LVS completion/match状态的合法组合及同次输入一致性；synthetic/not_run不能仅靠重绑hash伪称真实executed/matched，未知状态如实保留。状态冲突给EvidenceIssue/ParseResult，不新增degraded默认放宽；只有已显式接纳的profile才可按架构标suspect。body context本轮只做schema、来源hash与单位/profile绑定，检查context内部ID/类型引用自洽；FRAME/BN等样本名字不来自GDS BOUNDARY，真实GDS对象定位和跨格式几何匹配留Stage 2，不引入spec/oracle作为运行时映射表，也不重算外部物理连接或输出`body_complete`。不靠文件名、同名网线或固定fixture ID推断事实。缺失/错误hash/重复或不一致绑定要定位到具体文件/字段。
6. **错误与事实记录。** 组件返回tagged config/ParseResult/EvidenceIssue等中立结果，带原因、source refs、bytes hash（仅实际读到时）、行/token/record偏移及已完成解析依据；正常/失败非法字段组合经runtime validation拒绝。期望错误不得只print或吞掉；意外异常保留根因，KeyboardInterrupt/SystemExit传播。若接收外层提供的ToolRunResult，只单向关联其id，不反写execution记录、不伪造Calibre执行。组合测试实际读文件，但不把测试driver称为产品pipeline或RunRecord。

### 验收清单

| ID | 条件 → 可观察结果 | 必需验证 |
| --- | --- | --- |
| A1 正常读取 | 已验收site→配置/tech、40个本地图形/BOUNDARY元素、两份完整CDL、四种query capability及绑定的外部context evidence | 通过组件API从实际bytes得到结果，对照独立答案/来源；expected/spec/oracle/records不得成为运行时答案输入；输入目录前后hash不变 |
| A2 精度与schema | 原XY/REAL8、CDL数值与query `(y,x)/precision`→精确值和完整provenance；修改副本不能改变返回对象 | 精度边界、重复/未知key、版本/类型、非有限数、tag、size/depth、owner/模型/单位声明冲突；最小中立codec需跨进程稳定digest且拒非法exact表示，不能使用Python hash或float作truth |
| A3 来源拒绝 | 缺输入/header/闭包/raw/context、错top/bytes/profile/单位或header运行/匹配状态组合冲突→有定位的读取/绑定错误 | 在临时目录实际应用replacement/remove；绑定故意坏与语法故意坏分开，重绑后仍检出目标缺陷，不能用意外hash错误遮蔽它；缓存删除/漂移及重绑hash后伪称真实executed/matched分别覆盖 |
| A4 格式拒绝 | 超出声明的GDS/CDL/query结构→明确unsupported/parse error，保留可读取原始证据 | 实际覆盖C01–C07、C11/C12、C17/C18、C21的所属读取/绑定目的；C09的合法NF字面量精确读出，single-finger语义准入交Stage 2，不将读取成功写成准入通过；C22及body missing-context/wrong-binding覆盖所选必需输入/算子声明与绑定 |
| A5 非单样本硬编码 | 同一声明子集内的第二个合法输入→按其真实内容读取；破坏某一输入只影响相应结果/错误 | 临时样本一致重命名top/器件/query对象、合法变换记录/参数顺序或坐标并完整重绑；独立计算期望。不能写死INV、Q17、40、5/7、9raw文件名或旧expected hash来过测试 |
| A6 可组合及隔离 | 未来调用者可以取得读取结果/错误而不建立layout state、写输出或调用EDA | importer不import tooling/state/normalization/pipeline；domain不含IO；产品代码与生产测试不import legacy或tests/support。仅迁移纯逻辑并记录来源、纠正点及parity/回归依据 |
| A7 工程首交 | 独立测试及组合读取、strict typing、wheel/干净安装可复现 | 针对新增组件的单元/合同/组合测试；选择并执行strict checker；在隔离目录构建安装并导入/跑关键读取。保留Python≥3.10，至少检查最低支持版本及实际开发版本；环境缺失写明待验证范围，不声称矩阵已通过 |

C08/C09/C10的跨证据语义cardinality/model admission、C13的目标差异、C14–C16/几何body的规则或提取失败、C19/C20输出转换等仍由后续normalization/admission/validation/export负责。W005必须保留其输入事实、列出接收方和期望阶段；不得为了凑29例全部reject把这些语义检查塞进reader，也不得把读取成功算成这些反例通过。所有pre-context失败并非都发生在Stage 1。

新输入使用预期待决：无。所选synthetic格式与D1范围已有实物及用户决定；内部API和schema校验实现细节留执行者。若现有样本与架构出现具体冲突，先给最小复现和影响交PM，不自行改架构或改golden。

## 方案与决定（执行准备，PM 接收）

### PM已确定的任务拆分

W002 E7的完整M1-P1闭环拆为可验证的组件交付和后续组合，**W005只验收读取组件**。此拆分不免除E7/R4的错误路径、typing/build及支持解释器义务：本次触及的接口同批验证，未触及的由下列后续包承担。旧[handoff](W003/handoff.md)“下一实现任务必须同批验收”的列表描述完整M1范围，不能将其中Stage 2–6自动塞进W005，也不能视作已完成。

| 后续组合任务 | 不得遗漏的义务 / 启动条件 |
| --- | --- |
| 输入组件接入pipeline及pre-context审计 | 任何正式run入口须在解析前经repository创建unsealed attempt；串联真实fixture读取的ToolRunResult与ParseResult。失败经StageFailure→最小failure RunRecord→terminal（含freeze/terminal失败与interrupt边界），绑定F1全request及F2真实坏raw；不能用W005结果替代run记录 |
| Stage 2与baseline/no_change | identity/spatial join、完整坐标/occupancy/connectivity、body/extraction/mandatory规则；完整初始化、seal、phase/revision/CAS/幂等及不可变性。样张expected JSON不是完整snapshot |
| Stage 6及完整M1组合 | 实际只读GDS/CDL/JSON导出、独立读回、Manifest、人机报告与terminal；输出精度/overflow、required failure和全部run生命周期错误验证。组合通过前不宣称M1完成 |

该表分配既有义务，不在本轮派发多个产品任务。MR-040配置机制精简另在改变当前入口/优先级前给具体取舍；旧Virtuoso readback在真实工具集成前明确，真实准入G1–G5按原里程碑保留。

### 执行起步

读取当前v2骨架与上游输入/下游consumer合同，先在本节补一页组件API/DTO、错误与边界验证设计，并请未参与实现者检查依赖方向和Stage 1/2分界。既有范围内review修正后直接实施，不为普通内部接口再造用户审批；代码完成再做独立review。定向查看legacy CDL/query纯格式逻辑与测试，拒绝float-round、固定fixture答案、convenience JSON和归档runtime依赖；W004 helper仅作为行为参考/测试支撑，不能整包复制成产品parser。

## 执行结果（执行）

未开始。执行者填写起始版本/环境、实际写入范围、A1–A7的命令与结果、未执行范围和完整身份。不得提前填写通过。

## Review 结论（reviewer）

产品代码尚未review。任务派发文档复核与未来接口/代码review需各自注明版本、范围和结论。

## PM 验收与交接（PM）

W003/W004样本前置已收口，当前派发W005读取组件；不代表W005实现或M1完成。恢复使用包含本文件的已发布提交，不能仅取633e3fe后执行旧W004 prompt。具体发布SHA见Git和本轮交接回复，main合并独立记录。

**派发文档复核（2026-10-31，PM记录）：**未参与本任务编写的`body_scope`对照架构完成独立复核，剩余必须修正项为0。已落实其body内部引用/Stage2定位分界、header运行与匹配状态组合校验等意见，并明确C09语义准入及图形/stream record区别。受审全文SHA-256为`bd5330364c3107e569841b3271ec3adab23029ab6a6eb427c5bfe586bb7dec62`，覆盖追加本段之前的任务正文。`pm_review`另复核收口/导航/portable receipt，旧阶段冲突已修正，无剩余必须修正项。两项均为文档复核，不表示产品代码或测试已经通过。

### 下一执行session prompt

```text
按Layauto项目规范，以执行角色完成W005输入读取与绑定组件。
从PM交接指定分支/提交恢复，先核对HEAD和全部已有差异；读AGENTS、README、协作规则、current-work、W005及引用的架构/已验收W004输入合同。
W003/W004已收口，不重做样本修订。按W005补简短API/DTO/错误边界方案，安排独立接口review后直接实现；普通内部选择自主处理。
真正从GDS/CDL/raw/header/config/context读取并校验，不从expected/oracle/spec或normalized-only加载答案；完成A1–A7及跨样本变体验证。
本任务仅组件API。pipeline/run入口、RunAttempt/RunRecord终态、Stage2状态与Stage6导出按W005后续组合表保留，不虚报本次已完成；新关键行为变化附实例交PM。
代码完成后安排未参与实现者独立review，修复必须修正项并复核，交完整版本/命令/结果/未执行范围。保留历史MR/E/R和已验收fixture。
提交/推送按该session实际授权；交回PM接收，不自行合并main或扩展到下一产品任务。
```
