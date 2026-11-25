# W020 独立方案复核

结论为可以按[执行方案](plan.md)实施。审查起点为 `fd629b1a0afc7b8dedb3ea0da52c86c574a7b210`，方案文件 SHA-256 为 `6d6d413af2d6775ad023b01cdb458e2f7290d2d5d5768b541f1ee8bb1ad5510b`。依据为[任务卡](../W020-stage2-baseline-readiness.md)、[架构 §2.3](../../architecture.md#23-stage-2事实归一化与-layout-state-构建)、W007/W008 的 readback 认证、W010 节点与分量、W014 标注目标和 W018 投影来源合同。下列探针在新增运行代码前独立执行，使用 Python 3.12.14。

## 从实际输入核验连接点

用 `copy_input` 复制 W003 实际输入至临时目录，用 W018 的 `select_projection` 选择逐层工艺并更新 header closure。以 run ID `pre-implementation-review` 调用 `prepare_inputs`。按 ready 的引用回读 checkpoint、parse、tool 与 evidence，用 `geometry_from_inputs_ready` 构造 geometry、effective、local；从同一 geometry/effective 调用 `build_discrete_occupancy(fragment_budget=100)`，从同一 local 调用 `build_terminal_relations`。组装前后均实测为 `unsealed`，revision 1。

| 来源与步骤 | 独立探针的结果 |
| --- | --- |
| GDS BOUNDARY | 直接读 `source.gds`，按 GDS 大端记录长度前进、以 int32 解码 XY。偏移 1648，stream layer 4，LI 原图 [28,34) × [30,55) DBU。运行时 record ID 为 `1520c086fbd443225fd2361cc4ba4d38eda87d5f97edd5a0cf68a887f4ec11c5`。|
| 格与有效区域 | `LI (1,3)` 的 drawn 和 effective 各一片，均为 [28,34) × [30,40)，60 DBU²；effective region 为 `ba2d47b831631b57b9b974e767c079def342d08b8ac210ac3b1407f71cee9d36`。独立按 LI 两轴的 20 × 10 DBU 节距可得相同交集。|
| 物理与标注 | 节点 `7fce9f6dfaf13a99f00b7431564f03882de82365c8c1be781c4237418d5a3a5f`，分量 `656bd9b055f519897cb4f4e86da8a0f713eea6022d6a46cc6dec00fa814de16d`。本次 target 为 `a45f8557587a612cb39119ecc5fb3cf316274a5c0a213dc8afbf0af3d741d44a`，标注 fragment 为 `5af7347c80c4de789216cfc6137d774b41d84daff9b29b6c06a8f9bf0ec77fb6`。另一次捕获应循引用重算这些身份。 |
| 网络及源字段 | 运行时 evidence 给出 R04、n_lo、VSS。原始 `net_shapes_n_lo.txt` 第 4–10 行与 `query/header.json` 的 y,x 轴序和 20 单位/nm 比例复算为 [28,34) × [30,55) nm，覆盖整片。请求清单记录 R04，`nXref.temp` 第 11 行把 n_lo 对应到 source CDL 的 VSS。 |
| M1 第二个见证 | 直接解码 GDS 字节，偏移 2352 的原图为 [0,45) × [48,58)。W018 样例 M1 的格 (2,2) 范围为 [32,48) × [40,60)，相交面积 13 × 10 = 130 DBU²。 |

## 对实现和验收的约束

1. 只读入口接收 repository 和一份 ready，核对同一 attempt 和引用的完整内容，沿 capture 内实际拥有的对象向下传递。对 W008/W009/W010/W014 与 W018 的分支按实际 status 判断。若预算越界或组件只有诊断 draft，即使有可读字段也要保留具体原因和原始来源。意外异常和进程中断沿用现有边界。
2. 可复跑主链以 record ID、piece/region、node、component membership 和 annotation target/ref 逐段连接。按 unit binding 将格片换算成 nm 后核对标注的实际覆盖。只凭同格、有公共边或属于同一分量无法说明某格片自身被哪个 query 覆盖。物理连接的依据来自实际有效节点、工艺规则、连接器及端点。
3. A/B 用相同顶层和不同实际文件，交错准备、组装与读取。两份事实的 refs、坐标与来源要回到各自 run。以 retained capture 在原文件被替换后继续查询可以检出重读。负例核对目标器件 MN0 的 L=4n→5n、双方 CDL 第 3 行和确切字段，区分 NFIN 声明、W011 几何计数和 Stage 4 的其余义务。
4. 对每层分列图形数量、声明、可计算片段及未覆盖诊断。例如 POLY 有一条真实 gate，其间距和相位缺声明，阻断本样本所需 gate-track 初始化；CUT 零记录、BOUNDARY 显式跳过各自有独立来源。不能从投影成功或返回空表推得全层覆盖。保留未标注图形、local BODY 与外部 body 关系的独立作用域。
5. 成本需在首次完整组装实测。报告使用小型 locator 和 refs，长捕获从原对象取。交付分清六类事实、逐层 preserve/frame/derive、version 0 原子发布和后续无修改判定的验收输入。本次复核运行了上列现有组件探针，交付复核另核新增入口的反例和定向回归。W019 双解释器矩阵的既有范围按其受测身份复用，W020 双版本全量由 PM 在阶段集成执行。
