# Layauto v2 首版路线图

先让一个小输入按完整规则得到可信产物，再扩大同一闭环能处理的变化。例如先证明一个单元无需修改时能保真导出，再让一个器件的 `fins_per_finger: 5 → 4` 经检查、原子提交后生成一致的 GDS/CDL/JSON，最后覆盖同一单元内多个器件一起缩小。

本文只分配里程碑、依赖和验收义务；产品语义仍唯一归 [architecture.md](architecture.md)。R/D/U 编号是规划索引，不新增产品合同。依据为 `main@6eccdff99a4da64e46921d16a4c339198813bc78` 的完整架构 §1–13；2026-09-08 编写，2026-09-09 独立规划 review 后经 PM 接收，**规划文档已验收；全部产品里程碑尚未实现或验收**。详细盘点、review、PM 接收与快照见 [W001](tasks/W001-v2-global-plan.md)，当前恢复见 [current-work.md](current-work.md)。本轮不提交、不实现产品、不拆分架构正文。

## 1. 已确认范围与规划原则

- 首版最低能力是具名 profile 下、单个标准单元内的 fixed-frame `nfin` shrink。沿用 2026-09-04 已确认的 single-finger（`finger_count = 1`）、one-to-one layout↔schematic mapping、no-device-reduction；single-finger 不限制 fin 数、cell 内器件数或一次 intent 的 delta 数。[架构 §1.4][a-1.4]、[§7.3][a-7.3]
- `explicit_static_fin_plus_active_window` 仍是候选；不能从 legacy、参数拼写、fixture 方位或 PDK 名字推定真实物理语义。先核对真实 tech/model/query evidence，再启用对应 shrink capability；不匹配时如实 unsupported，不拆指/归并或回退 legacy。[§4.5][a-4.5]、[§6.2][a-6.2]
- 默认 whole-intent：每个 delta 都须被解释和准入，全部要求一起成功或无 ECO publication。必要 LI/VIA0/M1/marking repair 属于 shrink 本身，不能随通用 routing 的延期一起删掉。[§6.5–6.6][a-6.5]、[§7.1][a-7.1]
- 缩小的是接纳的输入/能力集合；已接纳切片的精度、状态所有权、mandatory checks、失败语义、不可变发布和导出只读边界从第一次交付就成立。Runtime Stage 1–6 不是开发里程碑编号。[§2][a-2]、[§8.1][a-8.1]、[§9.1][a-9.1]
- MVP 完成标准是声明范围内的核心产物、自一致性、fixture 与审计证据；不能称为真实 foundry signoff 或所有 PDK 通用支持。[§10.5][a-10.5]

## 2. 起点与可用材料

| 项目 | 2026-09-08 现场盘点 | 规划影响 |
| --- | --- | --- |
| v2 实现 | `layauto_v2/` 58 个 Python 文件仅含模块 docstring；无 v2 测试 | 从行为合同与真实输入链路起步，不能按 skeleton 文件存在宣称模块完成 |
| legacy 材料 | 有 CDL/query parser、GDS IO、配置 loader、dummy raw+YAML、inverter 双 shrink 场景及测试 harness | 按 §11.14 定向取用纯逻辑/案例，移入 v2 owner 并重写有害假设；不全面再审 legacy |
| 证据缺口 | 仓库未提供可证明真实工具来源的完整 captured bundle 或已验证真实 tech/model/query profile；已有 raw captures 来自 dummy generator | synthetic 可启动工程合同和错误路径开发；真实 profile 准入仍是 M2 的独立门 |
| 本机验证条件 | Python 3.11.5；`pip check` 通过，pytest/GDS/KLayout/YAML/绘图库可定位；`wheel` 缺失 | 可做本机轻量检查；尚无产品、构建、真实 EDA 或 PDK 通过证据。安装/工具细节留在环境文档 |

精确路径、取用/改造/拒绝理由和现场方法见 [W001 的盘点](tasks/W001-v2-global-plan.md#2-现状与证据盘点)。历史 366 pass / 1 fail 仅为 legacy 的 2026-09-02 记录，不是 v2 验收，也未在本轮重跑。

## 3. 里程碑与依赖

主线：**M0 准入准备 → M1 保真无变更闭环 → M2 首个 shrink 闭环 → M3 首版范围覆盖 → M4 可复现首版验收**。

M0 分开交付“工程输入/合同准备”和“真实 profile 证据准入”。前者足以让 M1 在明确 synthetic profile 内开发；后者可以并行补证，但必须在 M2 接纳真实 profile 前完成。若真实材料不可得，M1 和相应合成测试可以继续，M2 保持有依据的阻塞，不通过把验收改成 dummy 成功消除阻塞。

| 里程碑 | 可观察能力与代表输入→结果 | 依赖 / 退出验收 |
| --- | --- | --- |
| **M0：知道首个输入能否被接纳** | 从一套 source/target CDL、GDS、raw query、tech/model 资料，给出有出处的 profile/能力矩阵、样本限制和可执行闭环方案；证据不足有明确缺项与获取路径 | [W002](tasks/W002-first-input-admission.md)。工程出口：schema/共享接口/失败流及样本来源有独立 review；真实准入出口：Geometry/CDL/FinCount/DeviceExtraction/body/rules 与 query binding 可证明，不能只填 profile 名称。两种出口分别记录 |
| **M1：输入无需改变时也能保真交付** | 同源 GDS + source/target 语义已满足的 CDL + raw query，经真实 parser、归一化、baseline publication，得到 `no_change` 的 GDS/CDL/JSON、人/机器报告、ValidationResult 和 terminal PipelineResult | 依赖 M0 工程出口。完整输入链路不使用 legacy JSON、normalized-only 或预制最终 snapshot。按 semantic/extraction-aware 判断目标已满足；初始化逐层 lifecycle 完整，空 ECO chain，不伪造 empty commit。产物 readback、自一致性、audit-readiness 及该路径的失败/并发/幂等检查通过 |
| **M2：首个受限 shrink 真正改变产物** | 在已准入 profile 下，一个 required `fins_per_finger` shrink 经过 fully-ground repair、exact mandatory checks、finalization、whole-intent publication，产出相互一致且可追溯的五类核心结果 | 依赖 M1 + M0 真实准入出口。首个样本优先选择可证明保持 frame/body/halo、局部 repair 可闭合者；具体几何/方言由 W002 证据决定。全部 R15–R20 在本切片内成立；未改器件/参数轴及固定几何不变，拒绝/失败无 ECO publication，Stage 6 失败不回滚已提交 state |
| **M3：首版声明范围内的整轮 ECO 可信** | 同一 cell 多 device / 多 required shrink 一起成功；supported+unsupported 混合 intent 全部拒绝；后一 delta 的检查或 finalization 失败时整组无 ECO commit | 依赖 M2，且 R05 所选 `calibre` acquisition 的运行/方言证据齐备；工具/资料不可得则明确上报阻塞，不宣称首版完成。多 delta 成功只有一个 whole-intent envelope；验证跨器件归属、共享/邻接/unknown/cut/via/marking 相互影响，按声明 capability 成功或 typed-fail，不能静默忽略。覆盖矩阵全部首版项已有正例、反例和适用范围证据 |
| **M4：另一环境可复现并验收首版** | 按仓库输入、profile、版本、命令重新产生代表产物与完整验证/限制报告；PM 能沿版本核验每个首版义务 | 依赖 M3；在已声明支持的解释器/依赖矩阵完成 CI、安装/构建与组合验证；required core artifacts、reporting、validation 和 terminal refs 一致。独立 review findings 处理后 PM 验收；是否集成及其版本另按用户授权记录 |

**第一次“输入→处理→产物”贯通在 M1**：它运行真正的文件读取、状态构建和导出，但无 ECO；采用 synthetic raw captures 时明确 `synthetic` assurance，不证明真实 PDK。**第一次实际 ECO 修改闭环在 M2**：此时才有 changed snapshot；成功不能依赖 exporter 补图、仅改 CDL 或自造 golden。M3 完成后才具备首版全范围覆盖，M4 只收口组合证据与复现，不把关键错误路径首次验证推迟到最终节点。

### 各切片共同验收门

1. 输入有来源、版本、profile、hash/closure 和限制；fixture 原始 capture 与 normalized 产物同源，几何/单位/identity 可追溯。未覆盖输入拒绝或按显式非生产 policy 保留 suspect，不伪装匹配。[§2.2][a-2.2]、[§12.8][a-12.8]
2. 基础状态及 ECO 只经各自 transaction 和唯一 repository 发布；检查覆盖该切片实际触及的全部 mandatory scope。Planner/constraint/exporter 不成为第二 state owner。[§2.3][a-2.3]、[§2.6][a-2.6]
3. 新接口首次交付就验证其正常、拒绝、错误与不变量；只有 `feasible` 可 commit。失败分类按到达阶段与是否 publication，不能把 skipped/deferred/error 或 coverage gap 汇总为已通过。[§8.1][a-8.1]、[§10.5][a-10.5]
4. Stage 6 只读 final snapshot、ordered chain、frozen RunRecord；required export/report/check 失败必须反映于最终 disposition。Manifest 只表示 export set 完整，不能独自作为生产接受信号。[§2.7][a-2.7]
5. 每项交付绑定代码/文档版本、输入/profile、命令环境、结果和未验证范围；每次里程碑给代表产物，PM 对照实际材料验收。具体协作程序归 [协作规则](collaboration/rules.md)。

## 4. 首版要求到验收的覆盖

“首交”表示该范围内合同和必要负例首次随功能交付；后续里程碑扩大组合覆盖，不准许先绕过合同。以下均为**首版必需**，条件项按已接纳 profile 的实际需要落实，或提供不适用/拒绝的证据；不能仅凭“未实现”标不适用。

| ID / 要求归属 | 架构出处 | 首交 → 完整覆盖 | 可检查的验收结果 |
| --- | --- | --- | --- |
| R01 输入子集与 profile admission | [§1.4][a-1.4]、[§4.8][a-4.8]、[§7.3][a-7.3] | M0 → M2/M3 | 单指/一对一/无归并正例；multi-finger/非一对一/reduction 反例在可执行候选前 typed-unsupported；fin、finger、multiplicity/token 语义独立核对 |
| R02 stream geometry 保真 | [§3.1][a-3.1]、[§5.2][a-5.2] | M1 → M3 | 每个 reachable record 保真；仅已证明 axis-aligned rectangle 才可 bbox；非矩形、hierarchy/transform/property/text/unknown key 在能力外 fixed passthrough 或 baseline 前 typed-fail，保留 unannotated geometry |
| R03 exact unit 与坐标 | [§2.2][a-2.2]、[§12.5][a-12.5]、[§10.2][a-10.2] | M1 → M2/M3 | REAL8 bytes/exact value/nominal DBU 绑定保留；源 tick 不 snap、不经 float；真实单位冲突/非唯一 scale/输出不可表示拒绝；candidate 合法化和输出量化另有 policy 与 exact delta |
| R04 CDL 与完整 target intent | [§3.2][a-3.2]、[§7.1][a-7.1]、[§10.2][a-10.2] | M1 → M2/M3 | dialect parse/reparse 保持 pins/globals/model/terminal/directive/未改参数；expressions sound evaluate/rewrite 或拒绝；include/library/preprocess 闭包可移植；多 target source 不一致拒绝，所有差异进入 delta ledger |
| R05 query acquisition 与绑定 | [§2.2][a-2.2]、[§12.6][a-12.6]、[§12.7][a-12.7] | M0/M1 → M2/M3 | Stage 1 的 `calibre` 与 `dummy_fixture` 两类 acquisition 均在首版内：前者由 versioned query adapter 取得 raw，后者读取预置 raw，二者走同一 parser/schema。M1 可先交 dummy_fixture，M3 前完成所选真实 query runtime/dialect 的运行与 captured 验证，缺工具/资料则阻塞上报；header 校验 layout/netlist/top/deck/map/options 的传递闭包及 run/tool/status；missing terminator、dialect drift、hash mismatch 有 EvidenceIssue/ParseResult/StageFailure；不能绕过 parser |
| R06 identity 与 layer registry | [§5.3–5.5][a-5.3]、[§4.8][a-4.8]、[§12.3–12.4][a-12.3] | M1 → M2/M3 | opaque LVS id 只在 query run 内；rename/renumber/S/D swap 有显式 join 和 model/body symmetry；drawn/annotated/display color 分开，registry 唯一解析、冲突拒绝，禁止名字相等 fallback |
| R07 annotation、coverage 与 post-edit validity | [§5.6–5.8][a-5.6]、[§11.5][a-11.5] | M1 → M2/M3 | 同 cell 多 fragments、跨边界 evidence、approximate/raw bbox、tolerance 多解不整 cell 过标；sharing/short/unknown 分别报告；修改后重归属或失效，旧 annotation 不冒充新 LVS match，也不增删物理 edge |
| R08 配置与 tech 事实边界 | [§12.1–12.5][a-12.1]、[§11.1][a-11.1] | M0/M1 → M3 | safe YAML 拒绝 duplicate/unknown keys、可执行 tag、超限 size/depth；validated immutable DTO，closed rule variants，无 eval；site policy 不重写工艺/设计事实，不放宽 mandatory checks |
| R09 layer tier/edit/lifecycle | [§4.1–4.4][a-4.1]、[§4.7–4.8][a-4.7]、[§9.4][a-9.4] | M1 → M2/M3 | A/B projection 与 C1/C2 lifecycle 各自声明；shape override 优先；preserved/frame 不重建、derived 需 certified contract；辅助 geometry 保真；tier/derived/FIN no-edit 不混为布尔开关 |
| R10 baseline 与 context | [§2.1][a-2.1]、[§2.3][a-2.3]、[§11.8][a-11.8] | M1 → M3 | 新 lineage 仅 InitializationTransaction create-if-absent 发布 version 0，不能应用 target；已有 lineage load+seal，不重初始化；tech/evidence/coordinate binding 漂移拒绝 |
| R11 state、occupancy 与 views | [§3.4–3.5][a-3.4]、[§3.7–3.8][a-3.7]、[§9.5][a-9.5] | M1 → M2/M3 | geometry/occupancy projection 可相互核验，每个 coverage delta 绑定 exact geometry；grid 不持 occupancy；segments/vias/fin attribution 只读可重算，失效后重算或 typed stale failure |
| R12 exact physical topology | [§3.6][a-3.6]、[§4.5–4.7][a-4.5] | M1 → M2/M3 | 相邻 cell 不等于接触；同 cell 可不连通；via 需 qualified overlap；cut 使用 Boolean operator；gate 分隔 S/D，不把 transistor 两端 union；body 域有 graph 或有证据的冻结；component lineage 记录 merge/split/remove/create |
| R13 不可变 snapshot 与 wire codec | [§2.6][a-2.6]、[§3.8][a-3.8]、[§11.15][a-11.15] | M1 → M2/M3 | nested alias mutation 不能改变旧 snapshot digest；typed ids/Decimal/Enum/Path/sets/region tables 显式 encode/decode、排序、跨进程 digest 稳定，拒绝 NaN/Inf，不用 Python hash |
| R14 全 delta planning 与确定性 | [§6.6][a-6.6]、[§7.1–7.6][a-7.1] | M1 拒绝/no_change；M2 修改 → M3 | 全量 capability admission；current 与 immutable target 分离；候选绑定单一 base/preconditions、fully-ground/dependency-closed、排序可重复；unsupported 不漏掉、不静默 partial；stale locator/candidate 拒绝或重规划 |
| R15 shrink 物理变化及局部 repair | [§6.2–6.5][a-6.2]、[§7.3–7.4][a-7.3] | M2 → M3 | static-fin profile 不删加 raw FIN、不编辑未获准 fin/gate cut；OD/active 变化由 extractor 解释；必要 LI/VIA0/M1/marking 修复在同一 fully-ground plan 内；unresolved repair 不可执行，Stage 5 不代做 routing |
| R16 mandatory predicates 与范围闭包 | [§8.1–8.7][a-8.1]、[§12.2][a-12.2] | M1 适用 baseline 检查；M2 修改 → M3 | old∪new footprint 扩张到 rule halo/whole entity/via-cut partners/pre-post components/body/derived；不能证明局部闭包就 full-check 或 fail。触及的 width/spacing/line-end/extension/enclosure/cut/OD/blockage exact checks 齐全；relation assurance 缺失 fail/defer 或有证明的 fallback；只有 feasible 可发布 |
| R17 intent/frame/body/halo invariants | [§6.3][a-6.3]、[§8.3][a-8.3] | M2 → M3 | parent/candidate extractor count 分别等于 before/after；未改轴/其它 device count-topology、channel/cardinality、固定 FIN/gate/rails/well/frame/body 保持；pin reachability 满足，冲突 annotation 不合并。触及 halo 需完备 neighbour classes/coverage proof 或完整 tiled required signoff，否则拒绝 |
| R18 finalization 闭包 | [§2.6][a-2.6]、[§9.1][a-9.1]、[§9.4–9.5][a-9.4] | M1 baseline；M2 修改 → M3 | versioned DAG 按真实 delta 刷新 annotation/extraction/connectivity/relations/derived/consumers，dirty 输入不判通过或提前判失败；post-finalization 重算范围并重检至无 pending；cycle 无 termination/unique-result proof 则 fail |
| R19 whole-intent 提交与回滚 | [§3.8][a-3.8]、[§9.1–9.7][a-9.1] | M2 → M3 | 所有 authoritative components、完整 ChangeSet/lineage/provenance 和 RunRecord 一起可见；下一读取立即见新 snapshot；多 delta 单 envelope；任一 staging/check/finalization/freeze 失败无半状态、无成功 CommitEvent |
| R20 repository 状态机/CAS/幂等 | [§2.6][a-2.6]、[§9.2][a-9.2]、[§11.4][a-11.4] | M1 初始化/关闭；M2 ECO → M3 | process-local mutex+CAS，head/revision/phase/mode 同域校验；并发同 parent 仅一成功；响应丢失 same-key/same-digest 返回原 refs，异 digest conflict；终态后 mutation、whole/partial 混用拒绝；旧 snapshot 不变 |
| R21 no_change | [§2.7][a-2.7]、[§7.1][a-7.1] | M1 → M3 | semantic/extraction-aware target 已满足，空 ECO chain、当前 snapshot、closure head CAS；仍正常 export/validate/report；不能仅比较 CDL 字符串或伪造 empty commit |
| R22 全阶段 failure lifecycle | [§2.1][a-2.1]、[§2.6–2.7][a-2.6]、[§11.13][a-11.13] | M1 首批；M2 对应路径 → M3 | parser 前有 unsealed RunAttempt；pre-context failure 最小 frozen RunRecord，无 ECO/post-change geometry；run_record_freeze 唯一缺记录特例 terminal reject；Stage 6 failure 保持既有 RunRecord/state，仅 diagnostic refs 和 policy 汇总；InternalStageFailure 不吞 KeyboardInterrupt/SystemExit |
| R23 核心 artifacts 与只读导出 | [§10.1–10.2][a-10.1]、[§11.11][a-11.11] | M1 → M2/M3 | GDS/CDL/JSON 来自 frozen snapshot/tech/ordered chain，不能 replay 得到 geometry；readback/reparse 检查语义、单位、metadata、CDL closure；重复输出的差异可解释；snapshot 内容不变 |
| R24 artifact/terminal publication | [§2.7][a-2.7]、[§11.11–11.13][a-11.11] | M1 → M2/M3 | unique immutable artifacts 实际 bytes hash/size，完整后才 manifest；required export 失败不正常 validation；最终 terminal PipelineResult 绑定同一 refs、由 frozen policy 聚合 accept/requires_review/reject；latest consumer 要原子重验 head，manifest 不单独授权消费 |
| R25 validation 与正确性依据 | [§10.4–10.5][a-10.4]、[§11.12][a-11.12] | M1 → M2/M3 | fixture/golden、自一致性、audit-readiness 分开，golden 非唯一 oracle；run+snapshot+chain+manifest 绑定；execution/coverage/severity/disposition 独立，degraded pass 不合成为 required clean；启用的 required tool 缺失为 error+reject |
| R26 报告与 provenance | [§9.6][a-9.6]、[§10.6][a-10.6]、[§11.11][a-11.11] | M1 → M2/M3 | 人/机器报告覆盖输入、全 delta、候选/规则/传播统计、rollback/commit、base/derived changes、coverage/validity、限制、manifest 与 checks；从 frozen inputs 生成，不仅统计 edit ops；reporting failure 有独立结果并进入 pipeline |
| R27 owner/依赖边界与 legacy 隔离 | [§11.1–11.15][a-11.1] | M1/M2 随接口 → M3 | module boundary tests 保护 neutral DTO、single publication owner、constraints query-only、export/validation/reporting/tooling 的方向；v2 runtime/production tests 不 import legacy；每段取用有 parity 或纠正旧语义的回归 |
| R28 Python、依赖与 CI | [§11.1][a-11.1] | M1 开始 → M4 收口 | 保持 Python 3.10+，显式运行/可选依赖、strict type checker、支持的解释器矩阵与 CI；runtime schema validation 独立存在；安装/构建在干净环境验证，不能从本机 pip check 推出可部署 |
| R29 fixture 分层与再生成 | [§12.8][a-12.8]、[§13.2][a-13.2] | M0 来源；M1 首批 → M3/M4 | regression/synthetic edge/tool-captured 区分；raw-normalized 同源、generator 可重复/regen-clean 或 machine-readable limitation；每项记录 profile/版本/来源；多器件/多delta正例及三个输入子集反例齐备 |

### §13 历史义务的落点复核

本表只把已吸收的问题关联到上述验收，不重开 legacy 全面审计；详细规则继续回对应架构正文。

| 架构条目 | 首版覆盖位置 |
| --- | --- |
| §13.1 FIN 可编辑 / per-device FIN | R01、R15、R17；M2 拒绝错误 edit |
| §13.1 fin 只按 Y 归属 | R12、R15、R17；M3 同 track 不同 X 的多 device 检查 |
| §13.1 legacy JSON 主路径 | R05、R27、R29；M1 起禁用 |
| §13.1 via/routing 多份 owner | R11、R12、R19、R27；M1/M2 |
| §13.1 scalar net/unknown 乐观 DRC | R07、R12、R16；M1/M2，M3 组合 |
| §13.1 Stage 6 writeback/stdout validation | R19、R22–R26；M1/M2 |
| §13.2 buffer/inverter 命名错位 | R04、R06、R26；M0/M1 按语义命名 |
| §13.2 boundary dummy POLY / 未识别器件 | R02、R07、R17、R29；M1 保留披露，M2 触及则检查/拒绝 |
| §13.2 odd width / int 截断 | R03、R29；M1 exact input，M2 candidate，M3 边界 |
| §13.2 LI spacing | R16；M2 mandatory，不能延期给 signoff |
| §13.2 VIA0 enclosure / extension | R15、R16；M2 同一 repair 闭环 |
| §13.2 device_info seed/rounding 差异 | R03、R07；M1 不当几何 truth |
| §13.2 net_shapes 非 trimmed region | R05、R07、R29；M0/M1 记录 quality/limitation |
| §13.2 HDB/query dialect 未经真实验证 | R05、R29、U01；M0/M2 真实来源门 |
| §13.2 fixture drift / gdstk 依赖 | R28、R29；首批 fixture 即检查，M4 复现 |
| §13.2 placeholder SKILL / stdout-only | R25、R26、D01；未启用能力不冒充 pass |

## 5. 有依据的延期与远期依赖

这些是现有架构已经允许的范围选择，不重新请求确认；未来启用时需要具体能力/输入/验收方案。延期不免除当前已接纳切片所需的不变量和失败 gate。

| ID / 延期项 | 既有依据 | 首版保留的边界 / 后续依赖 |
| --- | --- | --- |
| D01 SKILL/Virtuoso mirror、Stage 6 真实 Calibre DRC/LVS 及其生产 runner/解析/localization | [§1.4][a-1.4]、[§10.3–10.5][a-10.3] | MVP Python 核心导出仍完整；声明的 post-MVP check 记 deferred，disabled/not-applicable 才 skipped，启用 required 后错误必须 reject。未来依赖真实工具/PDK/license/captures 与 external apply assertions/idempotency/undo；本延期只适用于 Stage 6；Stage 1 两类 query acquisition、raw→normalized 同源与 baseline binding 仍按 R05 交付 |
| D02 跨进程/断电 durability 与 recovery | [§2.6][a-2.6]、[§9.2][a-9.2]、[§11.13][a-11.13] | 首版采用允许的 process-local publication 合同，原子可见、rollback、CAS/幂等保留；未来 durable backend 需 single composite-root/ACID、fsync/consistency、journal/crash-injection/recovery 证据 |
| D03 partial apply / dependency-group publication | [§7.1][a-7.1]、[§7.5][a-7.5] | 首版只启用 whole-intent + no_change；partial 请求明确不支持。未来须新 snapshot replan、well-founded progress、完整 chain、partial failure 非生产结果，不能隐式开启 |
| D04 grow、多指/器件归并、其它 fin representation | [§1.4][a-1.4]、[§7.3][a-7.3] | 首版 admission 拒绝；未来依赖各自真实 profile/operator/extractor/repair 与验收，不从 token 或拆分/合并绕过 |
| D05 完整 add/remove device、buffer insertion、general reroute、跨 cell/from-scratch | [§1.4][a-1.4]、[§7.4][a-7.4] | 保留目标和 capability seam；未来依赖拓扑 intent、完整 router/search、extraction 与 signoff。首版 shrink 内的 geometry/via add/remove 等必要 repair 仍在 M2 |
| D06 M2 以上完整金属栈、多重图形化/cut-mask/coloring、density/full deck | [§1.4][a-1.4]、[§8.7][a-8.7]、[§12.2][a-12.2] | 非 mandatory 的 signoff-only coverage 披露；本切片触及的 mandatory predicate 无权降级，缺能力即拒绝 |
| D07 完整动态 body graph、通用 stream/CDL 方言扩展 | [§3.6][a-3.6]、[§1.4][a-1.4]、[§3.1–3.2][a-3.1] | body 只有 baseline LVS + body/boundary invariant 证明冻结时才可不建动态 graph；其它 format/record/表达式须保真 passthrough 或拒绝，不默丢。具体首个子集待 U01/U02，不能借本行提前确认 |
| D08 交互图、可选可视化、搜索/RL/LLM 候选排序 | [§2.7][a-2.7]、[§6.3][a-6.3]、[§10.6][a-10.6] | 核心人/机器报告必需；可选 visualization 缺失记 ReportingResult 限制，若未来 policy 要求则成 gate。复杂排序依赖可验的 deterministic planner seam，不阻塞首版 |

架构正文拆分不在本路线图的产品依赖链，本轮不启动；历史工作流提案不作为里程碑验收或新增权限来源。

## 6. 待查明事项与上报点

未知项不是已批准延期。先在 [W002](tasks/W002-first-input-admission.md) 调查成可审阅材料；普通技术细化由 PM/执行/reviewer 处理。只有新的关键输入解释、对外行为/格式或能力/验收承诺变化，才按协作规则附具体样本、证据、影响和推荐项交用户决定。

| ID / 缺口 | 负责与消除方式 | 阻塞什么 / 可继续什么 |
| --- | --- | --- |
| U01 首个真实 tech/model/query/profile 及 matched baseline | W002 定位可用 source GDS/CDL、model/deck/version、四类 raw query 与 header closure、单位/terminal/size axes、LVS completion/match；不把 ASAP7-style dummy 当 PDK。外部资料不可得时列最小资料清单与获取责任 | 阻塞 M0 真实准入和 M2 真实 profile 成功；M3 另需本系统所选真实 query acquisition 的运行证据，外部 captures 不自动证明 live adapter 已执行；不阻塞 M1 synthetic 合同开发。用户无需重确认单指等既定范围 |
| U02 首个 Geometry/CDL/输入输出子集 | 从真实样本列 reachable records、hierarchy/properties、CDL expressions/includes/model tokens、reader/writer 能力。flat rectangle、source/target CDL、无损或拒绝的窄子集是优先调查方向，不是已冻结使用承诺 | 缺口影响具体样本是否可入 M1/M2；若需要用户选择保真/格式/输入预期，先呈最小输入→产物和反例，再决定；不能静默改架构 |
| U03 repair、rule、marking/body/halo 可闭合性 | 列所有触及局部 rules/extractors/derivators/dependencies 与来源，验证 fixed-frame/不触 halo 的证明或完整 abutment contract；缺项使用 full-check 或拒绝 | 阻塞对应 M2 candidate，不阻塞独立 codec、repository、baseline/export 工作；不能用“后续 signoff”替代 |
| U04 报告/CDL/fixture 的关键使用预期与独立 oracle | 先看现有代表材料，形成最小报告字段/样张提纲、CDL preserve 差异、fixture 生成与独立期望来源。技术保真由 agent 核验；若关键用户预期未定义，再提交具体选项 | 不把选图风格当全部主线前置；影响验收解释的选择必须在对应产物实现前解决。Golden 不能由同一实现自造并独自证明正确 |
| U05 可复现环境与 CI 矩阵 | 保持 Python 3.10+；调查现有依赖、strict checker、支持解释器和 CI 落点，落实构建缺 `wheel` 等实际问题；下游独立 tool open/syntax gate 随所选 production profile 验证 | M1 开始补齐工程条件，M4 收口；本机已安装依赖不等于新机可用，真实工具开通不由本轮规划自动授权 |

**目前没有需要用户立即重新决定的产品范围。** 尚未有足够真实材料把 U01–U04 化成具体选择；下一项先调查并上报实际缺项/分叉，不要求用户凭空选 PDK、方言或图表，也不把未答复当同意。

## 7. 近期工作与完成前核对

- **W001 规划已验收：**独立 review 为 0 项实质 findings，PM 已核对被审身份、要求覆盖与限制；文档仍未提交/未集成。详细状态和证据归任务文件，规划验收不等于产品实现授权。
- **首项 W002：**准备首个输入证据清单、准入矩阵与 M1/M2 共享接口/失败流方案。已按任务模板写到可直接开展定向调查的粒度；W001 接收后 PM 已确认可执行，尚未启动；继续范围为只读调查与文档准备。缺真实外部资料时仍能完成仓库定向核验与精确索取清单，不必先安装 EDA。
- W002 接收后只展开 M1 的近期实现包；共享状态/publication/物理解释方案先独立 review。M2–M4 保留能力目标、依赖和验收，不预写全部 helper/模块任务或承诺日历排期。

| PM 核对 | 本规划的处理 | 尚不代表 |
| --- | --- | --- |
| 首版遗漏 | 完整架构 §1–13 经梳理；R01–R29 覆盖主合同，§13 每个条目都有验收归属 | 独立规划 review 与 PM 接收已完成；不代表已有产品测试通过 |
| 延期依据 | D01–D08 各有原文；局部 repair、Stage 1、mandatory checks、多 delta 原子性不随延期项消失 | 未知 profile/body/format 不视为已批准缩减 |
| 依赖可满足性 | M0 工程出口与真实准入分离，U01–U05 明确阻塞范围和可继续工作 | 真实 PDK/资料当前不可证明可得，不能保证 M2 日期或用 synthetic 消除该门 |
| 首项可执行性 | W002 有输入路径、只读调查/规划输出、验收、来源限制、上报点和下一步，仓库可启动部分无需外部工具 | 没有提前启动实现、扩大授权、commit 或进行架构拆分 |


[a-1.4]: architecture.md#14-支持范围与暂不覆盖范围
[a-2]: architecture.md#2-总体数据流与阶段边界
[a-2.1]: architecture.md#21-stage-编号约定
[a-2.2]: architecture.md#22-stage-1输入证据获取
[a-2.3]: architecture.md#23-stage-2事实归一化与-layout-state-构建
[a-2.6]: architecture.md#26-stage-5可行性检查事务提交与派生刷新
[a-2.7]: architecture.md#27-stage-6artifact-export-与-validation
[a-3.1]: architecture.md#31-几何事实源
[a-3.2]: architecture.md#32-语义事实源
[a-3.4]: architecture.md#34-grid-作为坐标系统
[a-3.6]: architecture.md#36-connectivity-state-作为拓扑解释层
[a-3.7]: architecture.md#37-read-viewslocalization-queries-与-artifact-views
[a-3.8]: architecture.md#38-snapshotcommit-log-与-provenance
[a-4.1]: architecture.md#41-tier-a1d-coordinate--backdrop--routing-layers
[a-4.5]: architecture.md#45-profile-scoped-fin--gate-representation
[a-4.7]: architecture.md#47-via--cut--routing-connectivity
[a-4.8]: architecture.md#48-layer-map-与-tech-bundle
[a-5.2]: architecture.md#52-gds-geometrybbox_by_layer
[a-5.3]: architecture.md#53-lvs-identityixref--net_xref
[a-5.6]: architecture.md#56-per-region--fragment-annotation-overlay
[a-6.2]: architecture.md#62-nfin-resize-的物理含义由-profile-决定
[a-6.3]: architecture.md#63-固定-cell-frame-下的-resize-placement-model
[a-6.5]: architecture.md#65-routingviacut-与-derived-markings-的局部修复
[a-6.6]: architecture.md#66-unsupported-intent-与失败语义
[a-7.1]: architecture.md#71-target-intent--diff-model
[a-7.3]: architecture.md#73-v2-mvp-的-resize-planning-特例
[a-7.4]: architecture.md#74-resize-repair-planning
[a-7.5]: architecture.md#75-unsupported-intent-handling
[a-8.1]: architecture.md#81-constraint-engine
[a-8.3]: architecture.md#83-rule-records-与-predicates
[a-8.7]: architecture.md#87-csp-frontline-rules-与-signoff-only-rules
[a-9.1]: architecture.md#91-transaction-scope
[a-9.2]: architecture.md#92-commit-to-authoritative-state
[a-9.4]: architecture.md#94-policy-controlled-geometry-finalization
[a-9.5]: architecture.md#95-derived-views-refresh
[a-9.6]: architecture.md#96-commit-log--changeset--provenance
[a-10.1]: architecture.md#101-stage-6-no-mutation-boundary
[a-10.2]: architecture.md#102-gds--json--cdl-export
[a-10.3]: architecture.md#103-skill--virtuoso-interaction
[a-10.4]: architecture.md#104-calibre-drc--lvs-closure
[a-10.5]: architecture.md#105-validation-model
[a-10.6]: architecture.md#106-reportsvisualization-与-debug-artifacts
[a-11.1]: architecture.md#111-建议-package-layout
[a-11.4]: architecture.md#114-repository
[a-11.5]: architecture.md#115-annotation
[a-11.8]: architecture.md#118-transactions
[a-11.11]: architecture.md#1111-export
[a-11.12]: architecture.md#1112-validation
[a-11.13]: architecture.md#1113-pipelinepy
[a-11.15]: architecture.md#1115-模块依赖方向与边界测试
[a-12.1]: architecture.md#121-site_configyaml
[a-12.2]: architecture.md#122-drc_rulesyaml
[a-12.3]: architecture.md#123-layer_mapyaml
[a-12.5]: architecture.md#125-配置边界哪些信息不进入-config
[a-12.6]: architecture.md#126-calibre--lvs-query-evidence-获取与结构化输入
[a-12.7]: architecture.md#127-生产工具环境适配
[a-12.8]: architecture.md#128-fixture-策略基于真实-query-事实构建-synthetic-cases
[a-13.2]: architecture.md#132-audit-derived-highlights-的-architecture-obligation
