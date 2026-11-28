# W026 从已发布版图检查连接件的包围量

## 任务要求（PM）

**阶段为可执行，归属 M1 的 Stage 3。** 分支 `codex/w026-connector-enclosure`。交付可供后续 Stage 5 显式调用的 `T05.contact_enclosure`。本例工艺规定，连接件两侧应分别有唯一匹配的导体区域，且该区域需要在四边至少多盖住连接件 1 nm。已有的 [W010 本地连接与包围审计](W010-local-contact-connectivity.md)、[W014 外部 tap 见证](W014-terminal-body-relations.md)及 W023 快照提供依据。[W025](W025-effective-li-spacing.md#pm2-integration) 的 T06/T07 保留各自语义。

沿用[阶段分工](../architecture.md#stage5-rule-invocation)与[所选工艺声明](../../tests/fixtures/w003_m1/tech/rules.json)。正常样本含 4 个 CONTACT、3 个 VIA0、1 个 GCONTACT，另有外部只读上下文中的 BTAP_N 与 BTAP_P 各 1 个。执行 session 负责实现与证据，独立 reviewer 负责复核方案与代码，PM 负责实际集成。

### 三份已发布输入和一个上游拒绝用例

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
| A1 声明和入口 | 从同一已认证上下文读取此版绑定的规则、连接层配对、物理算子、阈值和单位。调用方可用一次只读查询看到 T05/T06/T07 及其余七条规则的状态。本轮新增求值能力能与已有规则组合，W024/W025 已有入口保留原行为。 |
| A2 本地几何 | 按所选配对检查每个连接件的两侧，对实际有效区域判定包围，包括区域由多块矩形组成的情况。各类连接件由工艺声明选定两侧，共用精确包围判断和结果表达。复用 W010 已有精确集合包含能力和已绑定的审计。结果能解释哪一侧和哪项要求未满足，并能定位连接件 GDS、对应 region 和阈值字段。区分判定用阈值与几何实测；多个矩形的外框可能盖住真实的缺口。 |
| A3 外部 tap | 在其独立绑定的上下文内检查所有声明的 tap，分别列出 body 侧、rail 侧的唯一匹配、包围和来源。优先复用 W014 已冻结的精确边距、候选身份与证据。T05 根据自己的几何条件结论，外部图形维持原作用域；T04 的体区连续性及 T08 的端子/网络判定各自归属原规则。 |
| A4 缺项与组合 | 对三份已发布输入，核实每个结论属于对应版本及其 GDS/上下文摘要。单独核对外部余量 0 nm 样本在发布前的拒绝与来源。处理缺失、声明不相容或无法确认匹配时，区分已证实的几何违规与资料不足，并定位到实际来源；Stage 2 已拒绝的输入沿用上游诊断。复用原生产者对受支持 T05 版本与参数的校验。本地及外部查询前后 head、attempt 和已发布内容一致，T06/T07 在三例中仍通过。 |
| A5 方案、独立复核与验证 | 先画清从已发布事实到两域结论的路径，决定哪些包围计算和结果表达可复用。在方案中用移动连接件或改变相邻 CUT 的例子说明旧/新范围将唤醒哪些检查。用公开入口交付可复跑示例。Reviewer 从原图和外部 JSON 分别复算本地等号、伸出、外部等号及上游贴边拒绝，并检查一个多块区域或唯一性反例。跑新增与受影响检查，按[验证分工](../collaboration/rules.md#verification-reuse)复用其余既有证据。 |

完整必需规则和无修改收口时由 PM 做阶段集成及双解释器全量。实际修改中的局部传播、撤回和最终候选判定在 M2 验收。Stage 3 的求值范围为当前 synthetic 工艺下已封存的双域输入。生产无外部 tap 的单 cell 分析沿用[W016](W016-single-cell-analysis.md)，完整运行按其实际输入合同处理。

## 执行与交接

> 在 `codex/w026-connector-enclosure` 按卡完成 W026 A1–A5。先独立复核方案，再实现从已发布快照检查 T05 的公开入口，复用已有本地和外部几何证据。用正常、本地过孔伸出和外部 tap 恰好达标三例定位两域结果；核实外部余量降为 0 时仍由 Stage 2 拒绝。保留原 T06/T07 入口并提供三规则组合。只跑新增及受影响范围，完成独立代码复核后将实现、运行命令和证据推回原分支，交 PM 验收。
