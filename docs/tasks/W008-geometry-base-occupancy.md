# W008 — 几何事实与基础占用

把已经捕获的GDS证据变成完整、可追溯的本地图形草稿，并建立可重建的精确占用索引，供后续物理状态构建使用。本轮回答“有哪些图形、准确位于哪里、一个索引格里有哪些图形片段”，不据此回答电气连通或合法布线位置。

## 任务要求（PM）

| 字段 | 内容 |
| --- | --- |
| ID / 目标 | W008；交付immutable geometry draft、exact坐标换算及versioned base projection/occupancy draft，消费实际捕获输入，无IO或发布副作用 |
| 里程碑 / 依赖 | M1第四个产品切片；W003/W004已验收synthetic输入、W005读取、W006运行审计、W007语义组件。W007经[PR #61](https://github.com/LucianoHoult/Layauto/pull/61)合入main `765ff864f4341b91996f70f25723411eebc0d6c2`，最终验收见[W007 PM2](W007-semantic-identity-normalization.md#pm2-integration-20261102) |
| 授权依据 / 阶段 | 用户2026-11-02同意继续合并W007并准备下一独立执行任务。**可执行：先细化内部方案并独立review，原范围内修正后直接实现A1–A8。** 本次PM只准备任务，尚无W008实现或产品验证 |
| 恢复位置 | `codex/w008-geometry-base-occupancy`，从上述main建立；使用包含本任务、W007 PM2与current-work的PM交接提交，完整SHA见Git/回复。临时环境不假定跨session可用 |
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

尚未执行。接手后记录方案、实现版本、A1–A8实际验证与限制；产品/测试变化后重新核对受影响证据，使用项目noreply身份提交推送本分支并核验远端SHA。不得代写reviewer结论或PM验收。

## Review 结论（reviewer）

接口及产品review尚未执行。由未参与被审变更者保存受审版本、独立判据、可复现findings、修正与复核依据；不把设计可执行写成代码已通过。

## PM 验收与交接（PM）

当前仅准备任务与分支，未验收W008。W007合并后实际39项组合检查通过，合并tree等于已审head，详见W007 PM2；不能把这些结果当作W008验证。本任务完成后交PM接收，不自行合并main、删除分支或启动下一任务。

**派发要求独立复核（2026-11-02，PM记录）：** 未参与草稿设计的`/root/w008_handoff_review`及其输入边界专项，对照上述架构原文、MR-051/052/054/056、实际GDS/tech声明和W005/W007接口检查，必须修正项0。确认内部base index没有冒充完整工艺坐标空间，保留来源闭合、多占据、独立body scope及后续物理/发布义务。受审基线为本次main，W008全文SHA-256为`611e5e83385771b193521e28917c980c72b9deb864303f42933c0798da87ce14`，对应追加本段前的草稿；这不是未来接口/代码review或W008产品验证。

### 独立执行session prompt

```text
按Layauto项目规范，以执行角色完成W008“几何事实与基础占用”。
从codex/w008-geometry-base-occupancy的PM交接提交恢复；main起点为765ff864f4341b91996f70f25723411eebc0d6c2，W007经PR61已验收集成。先核对远端/HEAD/工作区，读AGENTS、README、协作/环境规则、current-work、W008及其引用的架构与W003–W007合同。
先细化无IO输入/字段回绑、geometry身份/单位/保真、内部base partition、多occupant、DTO/codec/错误方案并独立review，原范围内修正后直接实现A1–A8。内部算法自主选择；不要直接加载example coordinate或32×16见证当完整运行网格，不推断合法routing lattice。
从真实W005/W006捕获证据构建全部本地图形与精确可重建的base occupancy。补足GDS/tech字段到捕获bytes的绑定，不能只信任既有NormalizationInput；原ticks不float/snap，保留重复记录和C1/C2，外部body图形不混入本地scope，W007 source/target/seeds不改写。
不实现CUT/terminal split、annotation/connectivity/body/extraction、完整坐标合法空间、baseline/seal、pipeline/repository扩展、no_change/ECO/Stage6；不改已验收fixture/答案和历史证据。使用独立手算判据、真实组合与公开DTO反例，完成双解释器、typing、新包/干净安装/源码外smoke并保存最终身份及未执行范围。
由未参与实现者独立代码review，修正并复核必须修正项；代码、测试、可访问证据及执行/review记录提交推送当前分支，沿用项目noreply身份，核对远端完整SHA后交PM。不得自行验收、合并main、删除分支或启动下一任务。
```
