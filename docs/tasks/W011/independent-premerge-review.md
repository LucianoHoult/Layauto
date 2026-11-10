# W011 独立合并前复核

Reviewer：本次独立 session `/root`，专项 `/root/geometry_review`、`/root/boundary_review`、`/root/evidence_review`；均未参与 W011 原设计、实现或正式测试编写。日期：2026-11-10 UTC。

**结论：新增 finding 0，剩余必须修正项 0；建议 PM 进入 main 集成及实际合并版本的组合验证。** 建议限于本任务受限 synthetic M1 组件及已有资源安排，不是完整 Stage 2/M1 或生产可用性验收。本 reviewer 未验收、合 main、删分支或启动 W012。

## 版本、恢复与审查范围

| 身份 | 实核值与含义 |
| --- | --- |
| main 起点及远端 main | `61775e8fde6e9ea247ec08a32067c44c3be48ff8` |
| 准备提交 | `81e01da1e5a6ce8e7132f3cebf8ee92bc237246f` |
| 产品最终修正 | `8917d38d916c914bfa785cb116982f3f299b38de` |
| 双矩阵源码/测试/配置冻结 | `e89bdaa6a091f56cfaf7862dced7232d34e22514` |
| 执行交付 | `3c464baade7b6ea8c712cfb84265490b8e3f754e` |
| 本次待审 head，含 PM 接收及后续文档 | `8452027e57fb1c58607640d7eb755b38ffc70716` |

开始时 `/workspace/Layauto` 为干净的 `work@61775e8…`，staged/unstaged/untracked 均空。先检查内存及已有进程，再读取项目规则；沙箱内 Git 连接代理失败后，通过授权的环境外 Git 获取并 `ls-remote` 核对上述两个远端 head。在 `/workspace/Layauto-w011-review` 建原名 W011 分支的独立 worktree，原 checkout/分支保持不动。仓库仅根 AGENTS，无适用局部 AGENTS。[环境记录](independent-premerge-evidence/environment.json)区分初始观察与回归运行期间的资源读数。

审查整个 main→待审 head，而非只审产品最后一次修复。上述提交均为待审 head 的祖先；262 项源/测试/配置在冻结 Git、交付 Git、待审 Git、当前文件及完整 snapshot 中逐项一致。100 个 runtime 文件也与 `8917d38…` 相同。`e89bdaa…` 后只有文档/证据补记，**不将 `3c464ba…`、PM 接收或 `8452027…` 冒记为另一次跑过双矩阵的源码**。

已读 AGENTS、README、协作规则、本地/远端环境规则，W011 任务、plan/plan-review、execution/code-review、PM receipt 及原 finding/修后附件。回查 architecture §1.4、§2.2–2.3、§3 的事实/状态边界、§4.5–4.8、§5.3–5.9、§6.2、§8.1/8.3、§11.2/11.5/11.9/11.14–11.15、§12.3–12.5/12.8；实际 physical/derived/drawn/formats/rules、W007–W010 接口及 W003 contracts、MR-006–009/MR-031/032、W004 原要求。current-work 仅作导航。

检查新增 domain/annotation/derive/normalization/codec 全文、三处上游窄修、正式测试/helper/typing 及具名依赖守卫。main→head 其余 README、docs 导航、协作、roadmap/current-work、W012 规划属于准备/PM 文档，未将 W011 提升为已集成、完整 M1 或生产通过；W012 明记待准备、无实现。fixture/答案、architecture 和 legacy 无产品改动。本轮写入仅本报告、独立附件及任务 reviewer 段。

## A1–A8 判断

| 项 | 对代码、原始证据和本次检查的判断 |
| --- | --- |
| A1 同源纯组合 | 新入口只接收成功 W010 Result；先检查原对象 closed graph，再经 W010→W009→W008→W007 完整重建认证，使用其中 GeometryInput.semantic_input 运行 W007。外部 semantic 不能作为第二输入拼装。derived 固定捕获角色及原 rules/formats/units 链保留。本次真实 direct 禁 IO、跨捕获替换拒绝实跑；真实 W006 caller-read readback、attempt/checkpoint 不变及无 terminal 采用冻结矩阵/源码外 smoke/资源 probe 原证据，并静态检查相应完整断言。本次未重跑 readback codec。 |
| A2 完整正常集合 | 本次独立实际 W005/W008/W009 + 同捕获 W007、再中立 FIN/locator 核 40 drawn、18 FIN、36 个 channel×FIN 判定及完整 12 crossing；另正式组合核实际 W010/W011。N channel `[58,20,62,70]` 对 F01–05，P `[58,110,62,180]` 对 F07–13，均 L=4nm、逐根 W=2nm；不只是比较 5/7。四个有序 S/D refs 回到同一图，两个 channel 共享 G node，未把整条 POLY stamp 为唯一 DeviceId。 |
| A3 几何边界 | evaluate_fins 先正面积，再完整 channel X 和 active Y 包含，等号允许；touch/outside 不计，partial 不取整。325 个独立整数 open-cell/闭端点判据、同 Y 异 X、长 FIN 的两个 X channel、重复/重叠及范围外重复新探针通过。重复 records 与关系保留，无法解释独立 FIN 的受影响 count=None，不双计或 bbox 去重。精确大整数/重排的完整 captured 变体另按未改变的正式矩阵采信；有理覆盖新探针含 ±10^90 偏移，不把中立数学范围冒记为 GDS 支持范围。 |
| A4 定位与覆盖 | 每 seed 保存所有正面积候选；先逐 seed 唯一，再核全部 source device/channel one-to-one，不用排序、名字或其它 seed 消掉自身多解。新探针核 partial 2/5、有理 5/8、重叠多 seed union=1、missing/touch/ambiguous/冲突/分裂身份，以及多余 channel、缺 source device。CR-05 两 source pointers 实际解析回 D0/D1。300 组 rational union、62,900 成员点核精确集合及不重叠/重排/重复。唯一定位不是完整区域 annotation；身份不足时可保留几何 count，但无关联不生成 source 比较。 |
| A5 source/current 与 target | 计量函数不接受 target。comparisons 遍历所有成立关联的 NFIN/L/每个正面积 FIN W，differences 保留全部 mismatch。原 extraction_mismatch 本次实跑仍实际 4 对 source 5，F05 仅触边；partial count 未知仍留可判 L/W，零 crossing 的 W 未测列表及 indeterminate/mismatch 语义明确。本次正式回归核这两条路线；source 多差异、target-only 多轴由原矩阵和独立原 probe 按身份采信，代码路径单独静态检查。NF/M 是 W007 准入，不是几何测量。 |
| A6 公开合同 | DTO closed/versioned、递归不可变；先一次 snapshot 再验证 tuple。新 aggregate 重构 nested members，顶层对 supplied draft 完整 public replace 并比较完整 wire，对 semantic/completed/issues 比较 typed canonical 表示；不以 Python bool/int/Fraction 等值或投影摘要替代完整性。constructor/decode 重算全部 locations/associations/FIN verdicts/relations/topology/comparisons/issues。本次新错型/别名/来源/owner/异常探针及完整 Result 未计量 NF 来源回归通过；完整 readback roundtrip 和整条嵌套异常矩阵按冻结源原证据采信。 |
| A7 scope/拓扑 | W011 只引用 W010 nodes/components，不造边/union，不合并 body；本次 via_enclosure 组合仍保留 edge 和原 T05 violation、外部 body scope。实际消费算子和来源认证；未消费声明完整保留。不声称 TOY_N/P/VT、全部 D/G/S/B net、全 T03/T08、T02/mandatory、U06、完整坐标、baseline/no_change/发布或 Stage6 已通过。 |
| A8 工程与独立性 | 本次独立重算 262 源/快照、两实际包各 100 runtime、21 条命令及原输出、双 1605 IDs=原1465+140、typing54、双安装和源码外 smoke 的版本关联；旧失败和 gate 历史保留。实际运行与归档采信边界见下节。没有因 review 写入而改变冻结 runtime/tests/config，不要求机械重跑小时级双矩阵。 |

完整 crossing 的 nominal nm 集合为：MN0 的 y 区间 `24..26,34..36,44..46,54..56,64..66`；MP0 为 `114..116,124..126,134..136,144..146,154..156,164..166,174..176`；所有 crossing x=`58..62`。原 18 FIN 的其余记录、身份及来源仍保留。独立探针未将 oracle/spec 作为 runtime 输入，正式测试才把实际集合与独立手工 oracle 双向对账。

## 原 CR-01–CR-06 的独立关闭复核

原 finding、修正前版本、harness 失败及阶段性关闭撤回保留于 [code-review](code-review.md)，本次不覆盖历史原文。

| 原 finding（均 P2 必须项） | 修正依据及本次复核 |
| --- | --- |
| CR-01，seed opaque/source fields 错型可构造并 roundtrip | ChannelSeed 验证完整字段、derivation/source operands、xref 同行、坐标 lexeme 与 exact 值。新 probe 重跑三类原错型及每个来源 operand 拒绝，合法真实 seed roundtrip。 |
| CR-02，新 semantic_record→Parameter 转换意外异常 | W007 codec 移除 blanket TypeError/KeyError/AttributeError/UnicodeError 转换；子构造异常直接传播。新 probe 对 7 类异常×两 suppression 状态共 14 条，核原对象及已有 cause/context/suppression。576 个上游字段类型对照中 560 个明确 ValueError，16 个合法/可选中立变化接受，未出现非 ValueError 形状泄漏；不把合法变化算漏拒绝。 |
| CR-03，W007 expected 后 completion 污染 context | facts=replace 与 error Result 构造移出 NormalizationError handler。新 probe 真实 UnsupportedFingerCount/UnknownDeviceIdentity 控制后，对两 completion hook 的 TypeError/KeyboardInterrupt/SystemExit 及两 suppression 状态共 12 条保留历史。完整 W011 可达路线另核源码及原回归。 |
| CR-04，嵌套等值错型、completed bool、投影漏 NF 来源 | 新成员递归 public 重构；Result 完整 draft/semantic/completed/issues 的 canonical 比较。新中立 probe 拒 int/bool width、Fraction line、NF line=999，以及漏 outside FIN verdict 而 count 不变；本次正式 Result 回归核未测 NF 来源；completed bool 和完整 readback 伪造按原最终 runtime 证据采信，静态确认相同防线。 |
| CR-05，source wrapper crash 及虚构 pointer 残留 | helper 取实际 `sources[0]`，保留原 pointer，message 带实际 seed ID。新 missing/ambiguous 两诊断实际解析回 D0/D1，source SHA 与文件一致。 |
| CR-06，同一 registry 位置与 owner 矛盾 | 比较 registry operand canonical lexeme 及 URI/SHA/pointer。新 probe 对两个真实 seed 分别同步更改三份 operand 的 POLY→METAL，公开中立 aggregate 明确 ValueError 拒绝；normal 5/7 对照通过。 |

三处上游改动必要且窄：`normalization/codec.py` 保留新嵌套语义叶的意外异常；`normalization/component.py` 修复 expected 后构造的异常历史；`domain/source_location.py` 显式拒绝非 FrozenMap、缺 SHA 和非法 UTF-8 文本，避免取消 blanket catch 后原 malformed 边界泄漏。没有改变 schema、CDL grammar、参数解释、准入能力或 fixture。原受影响 W007 148 项及最终双矩阵有原输出；本次另独立验证上述 malformed 控制。**原六项关闭成立，无需重新打开。**

## 证据层次与工程审计

本次实跑采用已有 `/workspace/.venvs/layauto/bin/python`，Python 3.12.14；未安装/升级依赖。`pip check` 实际通过；该环境缺 mypy，本次未声称重新运行 typing。

- [选定回归脚本](independent-premerge-evidence/run_regression.py)、[回执](independent-premerge-evidence/regression.json)、[stdout](independent-premerge-evidence/regression.stdout.txt)、[stderr](independent-premerge-evidence/regression.stderr.txt)：真实 direct/正常完整集合/mismatch/partial L-W/零 crossing/T05/body/拓扑/跨捕获/完整未测来源 **9 passed / 504.95s**，命令 exit0、505.258s，串行单进程，stderr为空；该命令的子进程 ru_maxrss 为1,421,568 KiB，不作为完整 readback benchmark。
- [几何专项](independent-premerge-evidence/geometry-report.md)：独立数学集合、真实 upstream 捕获及 self-consistent neutral 变体，明确不把中立变体冒称每例已通过完整捕获认证。
- [边界专项](independent-premerge-evidence/boundary-review.md)：57 项小型检查（内含576个字段类型变体）、9项真实 W005→W010 中立 aggregate 检查及原 W007 malformed wire 正式回归 **6 passed / 8.67s**；另核源码及原 findings 处置。本次没有完整 Result/readback codec 新 benchmark。
- [工程/资源专项](independent-premerge-evidence/evidence-report.md)：**297 项核对通过**，直接读取实际 tar/wheel/sdist、Git blobs、commands/stdout/stderr 与1399条采样，独立审计脚本及原输出可重现；不是只采信 status 字段或复用摘要。本次审计脚本四次自身假设失败的 stderr 原样保留（pip hash合法形状、缺本机原辅助对象、observer两次读clock的微秒差），报告逐条解释后再作最终核对；不列产品 finding，也不冒称失败的审计执行通过。

按相同冻结身份采信的历史工程事实：Python 3.10.22 / 3.12.14 各 **1605 passed**，pytest 输出分别 12905.97s / 7310.82s，3.10 命令总时长包含 2603.347s gate 等待；原 1465 node IDs 全保留，新增140，双 collection 集合相同。双 strict mypy 各54文件、工程/安装 pip check、构建 wheel/sdist、sdist→clean3.10 与 wheel→clean3.12 安装及源码外 `-I -B` direct/readback/mismatch smoke 均 exit0。

本机不存在原测试/安装环境目录。实际包字节本次可读、逐项核对；原安装文件清单、安装报告及源码外导入和 smoke 输出是**归档证据采信**，本次没有重新安装、观察原安装目录或重建双解释器树。最终源未变，故本次按风险补跑上述九项和新边界探针，不重跑双全量/新包/安装/完整 readback wire。

首轮 `02725e2…` 的 **2 failed / 1603 passed**、旧3.12仅 collect 启动后中断而 full 未运行，以及更早 preflight 失败保留。两项修正仅 tests-only setup：实际 target 参数词序、schema 先行拒绝的 operator 应在 W005 error 入口核对；未削减业务断言/原参数 IDs，runtime/fixture 未改，最终矩阵覆盖修后冻结源。HG-01 及资源 gate 的修正/真实互斥记录也保留；gate 在 fixture setup 前拿锁直至进程退出，未跳过测试，不将并发调度当单次产品优化。

## 资源与当前集成可用性（独立于几何正确性）

本机 cgroup memory.max=`17,179,869,184 B`（16 GiB）、CPU quota=4；开始约16 GiB可用，未见已有测试/codec 重进程。本次九项正式回归在单一进程串行，专项只运行轻量 upstream/中立探针，未并发完整 Result/readback codec 或完整矩阵。初始/运行时观测不等于新资源 benchmark。

| 原 fresh-process 路径 | 完整 W011 Result wire | 整进程 ru_maxrss |
| --- | ---: | ---: |
| normal direct | 54,050,313 B | 2,847,416 KiB（约2.716 GiB） |
| normal readback | 136,461,405 B | 7,322,828 KiB（约6.984 GiB） |
| extraction_mismatch | 54,049,506 B | 2,854,456 KiB（约2.722 GiB） |

原 readback 的 W011 build≈74.95s、encode≈3.06s、decode≈101.86s，完整命令≈211.58s；constructor 认证已经包含于 build/decode，**没有独立 constructor 耗时测量**。这些是含 imports、所有上游捕获/认证、结果保留和 wire 的整进程高水位，不能当 W011 增量 RSS。原长矩阵1399条10s采样另有3.10单进程 **9,257,804 KiB（约8.83 GiB）** 高点，共享 cgroup 最高采样12,299,743,232 B；采样高点不是精确进程峰值，共享值不等于单进程 RSS。来源、范围和命令 hash 均在专项独立重算。

**当前受限集成未发现实际资源阻塞，但成本显著，不能忽略。** 依据是相同冻结源的真实 full readback encode/decode、双矩阵 gate 和双源码外 smoke 都在原16 GiB/4 quota环境完成，本次关键 direct/拒绝路径也能执行；没有已确认的任务资源预算被证据证明违反。没有据未测最大规模或假设的新预算增设阻塞门。40 drawn/18 FIN、31份共280,706 B捕获却产生约136.5 MB readback wire，足以表明重复保留/认证需要优先处理；单次成本不能靠少跑测试解决。

资源建议交 PM（非几何 finding、非新增验收门）：沿用重型完整 Result/readback 与矩阵互斥、串行的集成安排，并留意长进程累计保留；在扩大状态链、输入或并发前，优先准备已登记的 [W012](../W012-capture-wire-performance.md)，用同条件完整路径分解捕获复制、wire 和重复构造/认证，再确定量化目标。优化须保留 bytes/owner/run绑定、完整公开验证和原异常合同。不能从这些有限样本推断最大输入、多器件规模或生产可用上界；本次没有新测此上界。

## 交 PM

本报告未发现需执行者修复交接的新 finding，**剩余必须修正项0**。PM 可按本次待审身份进入 main 集成，并对实际合并版本做所需组合验证；review 建议不是 PM 最终验收，也不宣称 main 已包含 W011。若集成前源码/正式测试/配置改变，按实际影响复核；文档补记不冒记为新受测源码。完整 net/body/model、T02/全规则、U06、工艺坐标、原子 baseline/no_change/终态与 Stage6 仍后置。

本轮材料按用户授权以项目 `LucianoHoult <LucianoHoult@users.noreply.github.com>` 提交推送原 W011 分支；最终提交及远端完整 SHA 由 Git 与交接回复实核，不在本文预写自身未来 hash。
