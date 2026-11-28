# W026 从同一份已发布版图检查十条必需规则

## 任务要求（PM）

**阶段为已验收。** [PM-01](#pm01) 的修正及 [main 组合验证](#pm2-integration)已完成。归属 M1 的 Stage 3，沿用 `codex/w026-connector-enclosure` 分支和本任务卡路径。开发基线为 `96615e24391d9e5f593a9536d99dc0c1061b7409`。原 T05 专项在派发前扩为整包。一次交付当前 synthetic 工艺的十条必需规则，其中 [W025](W025-effective-li-spacing.md#pm2-integration) 已实现 T06/T07，本次新增 T01–T05、T08–T10。执行 session 组织一次独立方案复核和一次整包代码复核，同一分支交回 PM。

检查以[绑定的工艺声明及 mandatory_rule_policy](../../tests/fixtures/w003_m1/tech/rules.json)为准。Stage 3 只读已发布状态，提供完整规则入口，保留 W024 的 `check_m1_spacing` 和 W025 的 `check_spacing` 的原有行为。打开上下文时只准备数据，调用方显式请求时才求值。整轮无修改由 Stage 4 判定目标、Stage 5 在选定快照正式调用并收口，Stage 6 导出回读。M2 接入修改候选、约束传播和撤回。[架构分工](../architecture.md#stage5-rule-invocation)

### 规则分组与证据

| 规则 | 要回答的问题及证据 |
| --- | --- |
| T01 外框、T02 FIN 网格 | 所有要求检查的原始图形是否都落在唯一 BOUNDARY 中？每条 FIN 的实际宽度、节距、相位和完整序列是否符合所选配置？按图形、坐标和来源指出偏差，覆盖边界等号及漏轨。 |
| T03 器件识别 | 沟道与器件能否一一对应，栅是否完整跨过有源区，计数、L/W、NF/M 是否满足声明并与 source/target CDL 对应？用真实沟道与 FIN 事实对照双方 CDL，覆盖计数正确而其他条件不成立的情况。 |
| T04 体区、T08 端子 | 分别证明体区包围有源区、与反型体区无正面积重叠、外部 tap 对应目标电源，以及器件 D/G/S/B 的端序和关系。用本地物理连通分量核对 D/G/S，用绑定的独立外部上下文证明 B。缺外部证据时沿用所选入口合同。[W014](W014-terminal-body-relations.md) |
| T05 连接件包围 | 正常样本中本地有 4 个 CONTACT、3 个 VIA0、1 个 GCONTACT，外部另有 BTAP_N/P 各 1 个。两侧各需唯一匹配的实际导体区域并满足四边 1 nm 余量。按配对声明复用 [W010 的精确集合包含](W010-local-contact-connectivity.md)和 W014 的外部审计。返回具体连接件、哪一侧、对应区域、阈值来源；多块区域要保留实际缺口。 |
| T06 有效 LI、T07 金属 M1 间距 | 整包入口调用已验收的距离计算；与已有专项入口逐条核对状态、精确距离及对应原图、CUT 和规则来源。 |
| T09 无修改保真 | 用受检快照及本次运行的有序 ECO 链，对照绑定的原输入，核对 CDL 语义、drawn 几何、外框与零提交。显式标记受检版本与比较依据。此处的通过仅描述已核实的快照事实；实际导出文件的保真由 Stage 6 回读核验。 |
| T10 图形和标注覆盖 | 逐项核对原图与有效区域保留情况。无标注按策略披露，marker 保持非导电，同名但物理分离的区域保留各自分量。覆盖一个按声明允许、需要披露的未知项。 |

### T05 的三份已发布输入和一个上游拒绝用例

在 W003/W004 临时输入中选择 W022 完整坐标并重绑 header。正常、本地过孔右移、外部恰好达标三例分别发布第 0 版，另沿原公开入口验证一个 Stage 2 拒绝用例。[PM 输入与第 0 版读回探针](W026/pm_inputs.py)

| 样本 | 手算依据 | 预期结果 |
| --- | --- | --- |
| 正常 | 本地过孔 VN 的 X 范围是 [29,33]，LI 是 [28,34]，两边各有 1 nm 余量。外部 TN.ext 与电源轨 MN.ext 的四边最小余量为 2 nm。 | 两域通过。1 nm 等号通过。 |
| [本地过孔右移](../../tests/fixtures/w003_m1/failures/via_enclosure/geometry_change.json) | VN 变为 [33,37]，与同一 LI 仍有 1 nm 横向重叠，但右边伸出 3 nm。GDS 中 VN 和 LI 分别在字节偏移 2096、1648。 | 仅 VN 的 LI 侧违反，另一侧和外部 tap 仍达标。物理连接边和包围结果分别可查。 |
| 外部 tap 恰好达标 | 将正常样本 TN.ext 改为 `(-12,49)–(-8,53)`。电源轨下边 Y=48 nm，余量从 2 降至 1 nm。 | T05 通过，外部电源轨侧报告 1 nm 等号及其来源，本地证据与正常版一致。 |
| [外部 tap 贴到轨边](../../tests/fixtures/w003_m1/failures/body_enclosure/body/context.json) | 原有失败样本的 TN.ext 下边为 Y=48 nm，余量为 0 nm。 | Stage 2 拒绝发布，报告 `BodyTapEnclosureFailure` 并定位到 `body/context.json`。该运行没有第 0 版，后续正式检查沿用这项拒绝。 |

对于当前已登记的 synthetic 工艺，T05 阈值来自 `tech/rules.json#/rules/4/parameters/enclosure_nm`。W010 同时核对该版本的规则声明，并用精确区域集合检查给定边距。实现前可对照[本地包围计算](../../layauto_v2/state/local_connectivity.py)和[外部 tap 审计](../../layauto_v2/derive/body_relations.py)。

从仓库根目录复跑输入核对：

```sh
PYTHONPATH=.:tests/contracts python -B docs/tasks/W026/pm_inputs.py
```

PM 已在 W025 合并版 `f235e446` 用 Python 3.12.14 实跑以上四个输入。三份成功发布的快照中，VN 的本地最小余量分别为 1、−3、1 nm，TN.ext 的电源轨余量分别为 2、2、1 nm。余量为 0 nm 的第四份在 Stage 2 返回 `BodyTapEnclosureFailure`，来源为 `body/context.json#/shapes/4`，核对了文件摘要，仓库没有产生 head。前三份的 W025 间距入口均报告 T06/T07 通过、T05 待求值。这组数值供新入口做对照。

### 验收项

| 项 | 可观察结果 |
| --- | --- |
| A1 整包方案 | 实施前逐条列出规则声明、操作数及证据来源、已有生产者、公开结果与正反例。按类别复用几何和关系计算，按绑定声明选层及对象。用移动过孔或 CUT 的例子说明将来改变旧/新覆盖范围时哪些规则需重查。独立 reviewer 先核实方案与输入可达性。 |
| A2 正常版十条实算 | 从 W003/W004 正常原文件和 W022 完整坐标发布第 0 版，打开一次上下文，显式调用整包入口，返回十条可追溯的通过结果。每条都能定位受检版本、规则声明及支撑判定的对象和来源；按规则披露可接受的未知标注。产品只读取绑定的输入和事实，测试预期与独立复算归测试侧。 |
| A3 反例和独立诊断 | 每条规则有针对性的对照，按可达性记录是上游拒绝、规则违规、证据不足或执行错误。至少一份可发布的实际输入同时触发两条违规，两项原因与各自单项输入一致。如用本地过孔伸出叠加 C14 的 M1 线距缩小，先验证重绑后的组合可发布。完整求值保留各条独立结果；必需规则缺算子、缺证据、执行出错等按绑定策略处理。仅已评估且满足的必需项可计入通过。 |
| A4 T05 对照与只读兼容 | 复现上表四个样本；再检查一个多块区域或唯一匹配反例。本地仍有物理连接时，能单列包围违规。T06/T07 在前三个输入仍通过。核对上下文、head、attempt 和快照在查询前后一致，保留跨版本错配的拒绝，以及旧公开入口及其选择范围。 |
| A5 验证与交接 | 提交一个能跑出完整十条结果和双违规的公开入口示例。独立 reviewer 对照声明和原始输入，覆盖各规则类别、T05 的本地及外部证据、T09 阶段边界和组合诊断。开发与交付跑新增及受影响检查、受影响模块的严格类型检查；以同一正常快照复用测试输入，记录首次准备和整包求值耗时。修正后定向复核，按[验证分工](../collaboration/rules.md#verification-reuse)区分本次实跑、按版本采信和未覆盖。 |

完整必需规则和无修改收口时由 PM 做阶段集成及双解释器全量。实际修改中的局部传播、撤回和最终候选判定在 M2 验收。Stage 3 的求值范围为当前 synthetic 工艺下已封存的双域输入。生产无外部 tap 的单 cell 分析沿用[W016](W016-single-cell-analysis.md)，完整运行按其实际输入合同处理。

## 执行与交接

> 在 `codex/w026-connector-enclosure` 一次完成 W026 A1–A5。用同一个已发布快照和一份规则目录，提供 T01–T10 的只读整包检查。复用已验收的 T06/T07 及 Stage 2 的事实，保留两个旧入口。先独立复核方案，再按类别实现；交付正常十条结果、逐条反例、至少一个组合违规及独立代码复核。跑新增及受影响检查，将实现、复现命令、证据与完整 SHA 推回原分支，交 PM 验收。

## 执行包

[实施前逐条方案](W026/plan.md) · [独立方案与代码复核](W026/review.md) · [定向证据和复现命令](W026/handoff.md) · [可运行整包示例](W026/example.py)

<a id="pm01"></a>

## PM-01　输出 Y 的两个漏极被切断，T08 仍报告通过

**阻止合并。** PM 在交付提交 `9651ab9fe29ce3a38f6c7ddb4533d290c3451932` 用 Python 3.12.14 实跑了正常和双违规样本。正常版十条通过；双违规版仅 T05、T07 报错，分别为 VN 的 LI 侧余量 −3 nm 和 M1 实测 4 nm（要求 5 nm）。两版均成功发布，检查前后仓库、head 和 attempt 一致。另在 Python 3.10.22 上通过 4 项依赖边界检查；交付与最终受审实现 `017bf8d` 的产品、测试、打包配置一致。执行侧的 48 项检查和 16 文件 typing 见原交接。

**单独改变什么。** 在正常输入的临时副本中，对偏移 1776 的竖直 LI 加一条横向 CUT `(83,78)–(91,81)` nm，然后重绑输入。它横跨 LI 的整个宽度 84–90 nm。下方 MN0.D 和上方 MP0.D 之间由此留下 3 nm 的空隙，原 CDL 和 raw query 仍分别将两端标为 Y。间距规则要求 2 nm，因此本例的 T06 通过。规则声明要求 T08 按 `same_component` 检查本地 D/G/S；正常设计中两个漏极同属输出分量 C_Y。[工艺声明](../../tests/fixtures/w003_m1/tech/rules.json) · [独立设计答案的端子表](../../tests/fixtures/w003_m1/independent-design-answer.json)

**实际结果。** W014 冻结端子行给出两个不同的物理分量，T10 也披露 Y 的两个孤岛。但 T08 对两端各自比较分量上的标注名与 CDL 名，均为 Y，两条端子观察均通过；整包返回 `all_required_passed=True`。在这一版读取时，MN0.D 分量摘要始于 `6930355b`，MP0.D 的始于 `9086fa32`。复跑应比较同一次捕获中的分量关系。[产品求值路径](../../layauto_v2/constraints/device_rules.py) · [公开复现](W026/pm01_terminal_open.py)

```sh
PYTHONPATH=.:tests/contracts python -B docs/tasks/W026/pm01_terminal_open.py
# 在修正版上运行
PYTHONPATH=.:tests/contracts python -B docs/tasks/W026/pm01_terminal_open.py --expect-fixed
```

**补修验收。**

1. 在已绑定电路和当前精确物理图之间核对本地端子的必需连接。此输入只应使 T08 为 `violation`，整包为假；诊断应给出网络、具体器件与端子、互不相连的分量和可复查的来源。分量的身份与连通性由现有图提供。用声明和端子关系选择检查对象，避免绑定到示例的器件名、网名或坐标。
2. 正常版两漏极同分量时十条通过。保留已有 T08 名称不符和证据不足行为、外部 B 端的独立关联。T10 对没有本地端子互连义务的同名孤岛继续披露；该类孤岛本身允许存在。原双违规样本保留 T05/T07 两项，检查保持只读。
3. 增加正式定向回归；独立 reviewer 用另一处会切断同一必需连接的 CUT 或等价真实输入复核，包括应通过的孤岛对照。仅实跑新增及受影响检查并记录受测身份，双解释器全量沿用阶段安排。修正、复核及证据推回原分支，交 PM 重新验收。

### PM-01 补修交接

受测产品提交为 `8a5513f42e9f20bcf1285cca2607796cf2f2156f`。T08 用当前选定 cell 的 CDL 端子构造本地互连要求。两个及以上本地端子声明在同一网络时，`local_net_connectivity` 观察列出每个器件、端序角色、物理节点和分量，逐一关联到已发布图。端子上的网络标注、外部 B 链及 T10 的同名孤岛披露各自保留。

在起点 `b42f77cf87ea41f640769d7e28e4336977fb5b65` 按上文第一条命令实跑，复现了已断路而整包通过。修正版仍使用同一输入。检查后可从 `report.for_rule('T08.terminal_graph').observations` 取出 `local_net_connectivity`，通过 `facts['terminals']` 查看逐端分量，`sources` 反查两处 CDL 声明、查询、快照分量和规则的 `relation_basis`。公开复现命令会打印这些来源。

```sh
PYTHONPATH=.:tests/contracts python -B docs/tasks/W026/pm01_terminal_open.py --expect-fixed
PYTHONPATH=.:tests/contracts python -B docs/tasks/W026/pm01_review_probe.py
PYTHONPATH=.:tests/contracts python -B docs/tasks/W026/example.py normal combined
python -B -m pytest -q tests/contracts/test_w026_devices.py tests/contracts/test_w026_drawn.py -k 'local_gate_and_drain or cut_between_output or declared_drain or missing_gate_net or same_label_islands'
python -m mypy --strict layauto_v2/constraints/device_rules.py
```

**任务卡切口实测。** 追加 CUT 的 GDS 偏移为 2672。版本 0 中仅 T08 为 `violation`，整包 `all_required_passed=False`。T06 实测 3 nm、T10 披露两个 Y 孤岛，两项均通过。两个漏极各自的分量仍观察到标签 Y。诊断的 CDL 来源及受检图中的分量如下。

| 网络 | 端子 | 原始声明 | 已发布图的物理分量 |
| --- | --- | --- | --- |
| Y | MN0.D | source.cdl 第 3 行 | `6930355b3d18c2a47526b44c8e199eb3ca5ef94fe81378f7b68e8e1d6221d056` |
| Y | MP0.D | source.cdl 第 4 行 | `9086fa32563ecef7503527f506910e0bf6caab473f0f193dcf7d2b4970502db7` |

该次受检快照 SHA-256 为 `2cf72074997d1358ab25da5d36e8f61cd4516e0b7776975b2d421db29f76ef6e`。分量可在这份快照的 `/connectivity/components/<分量摘要>` 读回，判定声明位于 `tech/rules.json#/rules/7/relation_basis`。

正常版十条通过。原组合样本保持 T05、T07 两项违规，分别为 VN/LI 右边 −3 nm 和 M1 间距 4 nm（要求 5 nm），其他八项通过。各次检查前后的快照内容、head、attempt 和仓库状态一致。独立复核对另外两个切口直接遍历物理图边，结果及复现见[独立复核记录](W026/pm01_review.md)。

Python 3.12.14 实跑上述 5 项定向回归，全部通过。覆盖正常 A/Y 互连和独立 B 链、Y 断路、逐端名称不符及跨角色 D/S 的声明互连、缺少栅端网络证据时的 indeterminate，以及允许的同名孤岛。受影响产品模块严格类型检查通过。其余 W026 验证按既有受测身份采信，双解释器全量留到阶段集成。待 PM 重新验收。

<a id="pm2-integration"></a>

## PM 集成验收

交付 `ee4d51be21f7d15edc3aa27087b3669667388022` 与受审实现 `8a5513f42e9f20bcf1285cca2607796cf2f2156f` 的产品、测试及打包配置一致。PM 核对了补修 diff、W010 分量/W014 端子来源、新的按声明网分组和外部 B 端独立取证路径。合入提交 `176326e04a78c48dab0df5a5f6857961733c00cf` 的完整 Git tree 为 `93dc747ba15c5b809fee24e1163ceab0812fca5a`，与交付一致。[PR #97](https://github.com/LucianoHoult/Layauto/pull/97)

合并前 PM 在 Python 3.12.14 运行原 3 nm 切口。仅 T08 违规，整包为假，诊断包含 Y、两个不同分量以及 source.cdl 第 3、4 行。另将切口上移至 Y=157–161 nm，独立遍历图边确认两漏极仍在同一分量。此时也有两个 Y 岛，T10 披露，十条通过。两例均保持只读。Python 3.10.22 上另通过 4 项模块边界检查，补修产品模块的严格类型检查通过。

实际合并版的组合结果使用 [PM 复现脚本](W026/pm_integration.py)。脚本从每组实际输入发布一次，独立从 GDS 字节量出 VN/LI 余量和 M1 最近一对的间距，并遍历物理图检查两漏极可达性。报告包含十项，查询前后的仓库快照、head 和 attempt 相同。

| 合并版实跑，Python 3.10.22 | VN 的 LI 余量 | M1 间距 | 两漏极可达 | 十条规则的结果 |
| --- | --- | --- | --- | --- |
| 正常 | 1 nm | 5 nm | 是 | 十条通过 |
| C14 的 M1、C15 的 VN、PM 的输出 CUT 组合 | −3 nm | 4 nm | 否 | 仅 T05、T07、T08 违规，其余七条通过 |

```sh
# 修正版的原切口
PYTHONPATH=.:tests/contracts python -B docs/tasks/W026/pm01_terminal_open.py --expect-fixed
# 合并版组合
PYTHONPATH=.:tests/contracts python -B docs/tasks/W026/pm_integration.py
```

**A1–A5 已验收，PM-01 关闭，剩余必须修正项为 0。** 原 48 项定向检查和补修 5 项各按所记受测版本采信；与补修相交的 T08、T10 及只读组合按上述命令实跑。范围为本次 synthetic 工艺的已发布快照。[W027](W027-no-change-closure.md) 在无修改关闭的实际集成版运行 Python 3.10/3.12 双全量。若输入合同、分量身份、规则组合或合并源码改变，按其影响重新验证。
