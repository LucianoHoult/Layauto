# W010 独立合并前复核

日期：2026-11-06。Reviewer：本独立 session `/root`；数学、公开异常、来源及工程专项分别为 `/root/geometry_review`、`/root/exception_review`、`/root/source_review`、`/root/evidence_review`，均未参与被审 W010 的设计、产品或正式测试实施。主 reviewer 阅读产品与合同、核查专项脚本及原输出并汇总判断；历史 review/PM 记录仅为核查线索。

**独立合并前复核通过。** 剩余必须修正项 **0**，建议 PM 进入集成及组合验证。A1–A8 在声明的 synthetic/local 子集内满足；另有1项P3非阻塞文档精度建议。本结论不代替 PM 验收或 main 集成结果。

## 实际版本与完整范围

| 版本 | SHA |
| --- | --- |
| main 基线 | `3be0b98359038bab6c23980b55a48987cc71a369` |
| 准备 | `9758a157115cc22d91ce095ac2002209b9f210d3` |
| 冻结产品/正式测试 | `0f5029df935bc0acd106aad1bc2be81304d4f442` |
| 执行交付 | `ca39aedcb71fda02f77ffda1eb5d5dddc598226e` |
| 实际受审 HEAD | `c4909ab679d0c0806200fcb132db8a5de1ad3e75` |

初始 `/workspace/Layauto` 为干净 `work@3be0b983…`；origin 为用户指定仓库。实际 fetch/远端查询确认 W010 与 main 都匹配上述 SHA，无受审版本漂移。在 `/workspace/Layauto-w010` 建立独立 `review/w010-independent` worktree，原 checkout 保留。默认沙箱首次无法连接代理，随后使用平台附加网络权限成功，未改代理/TLS。见[远端观察](independent-premerge-review/remote-before.txt)、[版本审计](independent-premerge-review/version-scope.json)。

审查 main→HEAD **254 个变更路径的完整交付**；准备→冻结 **15 文件**用于定位四个新 runtime 模块、公开导出、typing、正式测试/守卫和文档。冻结→HEAD 的产品、正式测试、配置及 README 没有变更；交付→HEAD 23 个路径仅 PM 文档/证据。没有仅审最后一次提交。架构、协作/环境、fixture/答案及 legacy 相对 main 保持；旧 delivery manifest 专门按 **ca39aed 的 Git 字节**验证，任务文件随后追加 PM 状态不构成交付不一致。

已读根 AGENTS/README、协作与本地/远端环境规则（无局部 AGENTS）、W010 任务及 plan/plan-review/execution/code-review/pm-receipt.md/json；回查架构 §2.2–2.3、§3.1/3.4–3.6、§4.5–4.8、§5.6–5.9、§8.1/8.4–8.5、§11.2–11.3/11.14–11.15、§12.3/12.5，W003 contracts 与 MR-045/047/052/054/056、W004 body 修订、W008/W009 输入/单位/region/public contract。W009 IPMR-01、FXR-01 原 finding 及修后复核均已回读，按完整嵌套边界和单次快照检查。

## A1–A8 判断

| 要求 | 独立判断与依据 |
| --- | --- |
| A1 真实组合与来源 | 满足已审子集。实际 W005 与 W006 readback→W008→W009→W010 在禁文件/repository IO 下等价；保留 input/effective/body 原对象、全部 completed 和 unsealed attempt。rules payload 绑定 tech.sources[6] 实际角色；两种错误来源、四组成组 payload 伪造×builder/constructor、错 run/unit 均明确拒绝。见[来源专项](independent-premerge-review/source-review.md)。 |
| A2 精确接触 | 满足。逐 piece 正面积或正长度边判据不依赖原 occupancy 轴；3,200 次独立集合对照及15具名边界覆盖角点/间隙、负值、超大整数、有理数、多片、孔洞及等号。CUT 新边界实际不在原 LI axes，完整图仍正确。大整数在中立数学层验证，不扩大 GDS 输入范围。 |
| A3 正常完整图 | 满足。手写完整14个几何节点，另按每条原record的独立unit-square集合、完整边多重集合及关系传递闭包核8条connector、6个完整分量和16侧audit；不仅核数量/面积。孤立BN/BP保留、POLY连续、OD channel不入图且无S↔D导体边。 |
| A4 端点与完整性 | 满足。独立有效region正面积交集先于component和enclosure：重复导体、已同层连通的两个候选及其中一个包围不足均拒绝歧义；缺侧/仅边角触拒绝。重复connector独立保留两源及全部边/audit；错连接对/角色/predicate由实际捕获返回定位问题。 |
| A5 特殊及包围 | 满足。实际captured cut-islands为3节点/0边/3分量，同标签/同展示格不union；实际via_enclosure仍14/8/6，VN边保留且LI侧violation、M1侧pass。多片整体包围、孔洞假bbox、恰阈值、有理阈值均按独立集合真值核对；代码只用整数/Fraction，未floor/snap/float。见[几何专项](independent-premerge-review/geometry-review.md)。 |
| A6 公开合同/异常 | 满足。公有constructor与nested result wire的漏/多节点、边、成员、假audit/union、foreign ref/unit、false success明确拒绝；正常同捕获roundtrip/digest稳定。原对象图在编码前验证，neutral重建与captured认证分层。本次260项边界检查完成，159/159注入故障保留原对象及cause/context/suppression；其中56条真实ContactProblem后的二次嵌套认证未污染原context。另8项原FXR-01交替集合快照通过。见[异常专项](independent-premerge-review/exception-review.md)。 |
| A7 作用域 | 满足。保留全部raw/base、semantic/target/query/body及readback；actual query改名后完整图和semantic digest不变，而完整captured receipt identity变化。外部六个body图形不入本地图；CDL B端和rail标签不建边。本地BODY仅几何节点，局部BTAP仍unsupported；coverage明确列出未消费与后置能力。 |
| A8 工程 | 身份与guard满足：252源、两包94runtime、原1149 nodeid保留/新增316、具名白名单均实核；本次typing48通过。本次完整v2实跑1465 passed；历史双解释器/构建/双安装按下节身份采信。 |

数学/完整图oracle由本次独立脚本编写：整数unit-square集合与四邻接、按有理分母缩放后的目标集合包含，以及图关系传递闭包；产品仅是actual侧。fixture helper只负责复制、编辑实际输入bytes与重绑，不提供答案。来源专项通过neutral错来源对照证明“自洽”不等于captured success；畸形输入要求具体ValueError/located issue，故障注入则要求原异常对象及完整链，二者不混记。

## Findings 与必须修正项

新增及剩余必须修正项均为 **0**；非阻塞建议 **1**（E-N01）。无需产品修正，保留原报告、findings 和 PM 记录。

**E-N01 — P3，非阻塞文字精度建议。** 位置：`docs/tasks/W010/execution.md:32`，同类摘要也见原代码 review 的资源限制段。最小复核：读取 `docs/tasks/W010/performance.json` 四个 case 的 `result_wire_bytes` 并取最小/最大。预期四例无 optional cache 的范围约 **12.58–17.09 MB**；实际摘要写约 **15.47–17.09 MB**，遗漏 cut-islands 的 **12,579,736 bytes**。影响仅为范围下界文字；正常/最大 wire、约988 MiB 累积 RSS、重复认证以及 max-pieces=1 的限制没有被低估，不影响合并条件。建议后续由 PM/执行澄清摘要；本 reviewer 保留原报告/证据，不直接改写。完整数值与复验脚本见[工程专项](independent-premerge-review/evidence-review.md)。

本次来源probe另实测完整readback回执wire为 **59,422,834 bytes**；它包含不同的readback保留链，不与原direct约22.8MB作同一身份比较。此为补充观察，并非生产上界。

本轮不新增生产性能门槛。大量多片、最大输入及生产规模未验证；已有大 wire、重复认证、有限四例及累积 RSS 披露基本准确。不能将累积高水位当逐例增量，也不能把核心算法计时当公开捕获路径成本。

## 本次实跑、采信与限制

本次 Linux Python **3.12.14**，已有 `/workspace/.venvs/layauto`；pytest9.2.0、PyYAML6.0.3。原环境缺 mypy，本次仅向独立 `/workspace/work/w010-premerge-deps` 安装 mypy2.4.1/types-PyYAML6.0.12.20261103，不改项目依赖或宣称干净安装。typing/pip-check 子进程与 wrapper 都带该路径；最初 setup/pytest wrapper 的包元数据为 null 仅指其自身未加载 target 路径，不代表随后 typing 未运行。禁字节码，pytest 关闭 cacheprovider，mypy/cache/临时输入独立保存。

完整输出、实际命令/解释器/cwd/HEAD/耗时/最终退出码/hash见 [runner](independent-premerge-review/run_check.py) 与 `independent-premerge-review/validation/`。

| 本次实际执行 | 结果与证据 |
| --- | --- |
| `python -m pytest tests/unit tests/contracts -q -p no:cacheprovider` | exit0，**1465 passed in 3076.64s (0:51:16)**，无warning，stderr为空；wrapper总耗时3078.855s。[完整输出](independent-premerge-review/validation/pytest.stdout.txt)/[最终回执](independent-premerge-review/validation/pytest.json)。 |
| `python -m mypy --cache-dir /workspace/work/w010-premerge-cache/mypy` | exit0，**48 source files**；[输出](independent-premerge-review/validation/typing.stdout.txt)/[回执](independent-premerge-review/validation/typing.json)。 |
| `python -m pip check` | exit0；[回执](independent-premerge-review/validation/pip-check.json)。 |
| 新编独立数学/完整图 | 两命令exit0；3200随机+15具名数学判据、14个captured变体（8完整成功图/6端点error）、3个错误策略定位拒绝；[回执](independent-premerge-review/geometry-receipt.json)。 |
| 新编来源/公开完整性 | exit0，31项（6正常/neutral对照、25明确拒绝），176.807s；[原结果](independent-premerge-review/source-probe.stdout.json)/[回执](independent-premerge-review/source-receipt.json)。 |
| 新编异常/不可变边界 | exit0，260/260、failures=[]，1429.580s；159原异常链含56真实policy后二次认证。另FXR-01四入口正反8/8，exit0；[结果](independent-premerge-review/exception-results.json)/[回执](independent-premerge-review/exception-command.json)/[快照](independent-premerge-review/exception-snapshot-command.json)。 |
| 新编工程身份及守卫 | 45/45审计通过，exit0；实际baseline/head收集1149/1465、guard2 passed及15组AST正反例；[回执](independent-premerge-review/evidence-audit-run.json)。 |

来源probe两次harness失败原脚本、原输出及退出码单独保存：一次错误地在拒绝捕获wrapper外构造错run对象；另一次误要求query-only变化改变neutral图ref。最终以真实adapter拒绝及完整captured receipt digest区分修正；没有修改产品或放宽验收，失败不计最终通过。见[历史说明](independent-premerge-review/source-harness-history.json)。其它本次独立专项无harness失败。

身份审计后采信原 R2 Python3.10.22/3.12.14 各1465、双typing48、新wheel/sdist、双干净安装和源码外 `-I -B` direct/readback smoke。252项源码/测试/配置等于冻结Git和完整tar；两包各94 runtime与源码相同；21条命令、42份原输出、78项工程清单及ca39交付218项一致。原1149 nodeid本次实际收集全部保留，新增316；2项守卫实跑及15组AST正反例证明仅具名文件/模块/符号例外，没有目录豁免。详见[工程报告](independent-premerge-review/evidence-review.md)、[逐项结果](independent-premerge-review/evidence-result.json)。

**本机不存在原测试树和两套历史安装树。** 没有重建/重装、遍历或重新导入历史安装；日志/hash一致仅支持采信历史证据，不等于重新观察历史执行。本次未重跑Python3.10、build/install或资源性能探针。原preflight/R1失败、中断及partial输出保持原身份，不计最终通过。不同checkout的绝对capture URI可改变完整receipt hash；同一捕获内才要求roundtrip/digest相等，跨捕获以实际几何/成员和语义身份比较。

完整工艺坐标、有效region occupancy、外部body/U06、FIN/器件提取、query空间标注、其余mandatory/lifecycle、baseline/seal/no_change/terminal/Stage6及真实PDK/EDA继续后置，不构成本轮缺陷。本图只证明声明范围内的本地物理接触和局部T05逐侧判据，不证明全部规则、完整Stage2/M1或生产准入。有限数学枚举及故障注入不构成全整数域/任意运行时篡改的形式证明。

## 交回 PM

剩余必须修正项 **0**，建议 PM 进入 main 集成及组合验证，再由 PM 记录最终验收。E-N01 可在后续文档整理中处理，不设置新的合并门槛。

[提交前范围审计](independent-premerge-review/delivery-audit.json)核对本次仅新增本报告/独立附件、任务只在 reviewer 区追加，以及252项受测源码/测试/配置不变、原 checkout 干净、最终退出码/原输出hash与报告链接。仅按用户授权提交推送原 `codex/w010-local-contact-connectivity` 分支，完整提交/远端 SHA 以推送后核对回复为准；不修改产品、正式测试、fixture/答案、历史记录、PM段或current-work，不自行验收、合main、删分支或启动下一任务。
