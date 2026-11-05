# W010 最终独立代码 review

Reviewer `/root/code_review`，2026-11-05；数学/拓扑 `/root/code_review/math_review`、公开边界 `/root/code_review/boundary_review`、工程证据 `/root/code_review/evidence_review`。四者均未参与本次方案设计、产品实现或正式测试实施。准备阶段仅读规范；收到执行者“工程矩阵全部通过，开始代码review”的明确消息后，才读取产品 diff 和运行以下独立 probes。

**最终独立代码 review 完成，新增及剩余必须修正项均为 0；可交 PM 核验接收 W010。** 未发现阻止所审版本交付的问题。本报告不代写 PM 验收或集成决定。

## 受审身份及范围

- 仓库 `/workspace/Layauto`，分支 `codex/w010-local-contact-connectivity`；base `9758a157115cc22d91ce095ac2002209b9f210d3`，冻结 product/head `0f5029df935bc0acd106aad1bc2be81304d4f442`。
- 完整 15 文件 diff：四个新 domain/state/normalization/codec runtime 模块、公开入口、typing 配置、正式合同/几何/异常测试、README 和方案/任务记录；没有只审最后一个提交。回读实际 physical/drawn/rules/formats owner、正常及特殊样本、W007–W009 输入/区域/来源合同和所引架构原文。
- [252 项源码/测试/配置清单](verification/source-manifest.json) SHA-256 `cef29336dba1bf572fd30227f354365d4a4d780e721d089b70095589d0f55889`；[完整源码归档](verification/source-snapshot.tar.gz) SHA-256 `493d36ebeb4bd5d43f8bbb06139b27e3be7997dad12e913c9ca36c362ba843d1`。
- [最终工程 receipt](verification/receipt.json) SHA-256 `856f78919b92098632fda3ca988ebcc6f4b739c817794fce691035e028562b9a`；[工程证据清单](verification/evidence-manifest.json) SHA-256 `ebf1cf092ba9168ae37dfd622aa47cae39ce812786e5c9e84bd485064d88593c`，78 个条目及 manifest 自身共 79 文件。

## A1–A8 对照

| 要求 | 独立审查与实际依据 |
| --- | --- |
| A1 真实组合与来源 | 主 reviewer 从实际 W005 reader 和 W006 repository readback 分别构造 W008→W009→W010；W010 期间禁止文件及 repository IO，完整 prior digest、input/completed/body 对象保留，attempt 仍 unsealed 且无 terminal。公开 `_require_input` 在复制前检查闭合原对象图，并完整 decode 认证 W009→W008→semantic/captured/readback；rules 的 payload 和 `tech.sources[6]` 固定角色与实际 owner 捕获顺序一致。独立构造异来源 neutral rules 后，captured success 确实拒绝。见 [主 probe](review/main-probe.py)、[结果](review/main-probe.stdout.json)、[回执](review/main-probe.receipt.json)。 |
| A2 精确接触 | 逐行核对正面积/正长度共边及点触排除，候选直接枚举 exact region pieces，不依赖不含 CUT/channel 新边界的旧轴。数学专项用单位像素集合及四邻接、独立有理矩形逐次差集分别给出预期，10,000 接触 + 10,000 包围比较通过，包含重复/空集合及 `2**120` 平移；这些大整数只验证中立数学，未扩大 GDS 范围。见 [数学报告](review/math-review.md)、[原结果](review/math-result.json)。 |
| A3 正常图 | 主 probe 不将 spec/oracle/expected 用作运行输入或答案，以手写完整 14 个几何节点、8 个 connector/端点和 6 个成员集合逐项比较，direct/readback 均一致；fixture inventory 仅对全部文件原 bytes 哈希以检查未改。16 个逐侧 audit 为 pass。BN/BP 孤立、OD channel 不入图、POLY 保持完整，节点/edge 无 net/device 标签输入。不是只核对数量。 |
| A4 歧义与完整性 | 独立实际捕获反例确认：重复导体、已同层接触的两个候选、第二候选包围失败，仍按两个独立 region 拒绝；边/角触按零 positive-area 端点拒绝。重复 connector 各自 edge 和 audit 保留。额外孔洞/重复/点边接触图 36 节点、67 边、10 分量、22 audits，对完整 edge/audit 多重集合与 Floyd 闭包成员逐项一致。公开 aggregate 从完整 effective 输入重建 nodes/edges/audits/components，主 probe 的漏边/假 audit 均拒绝。 |
| A5 特殊及 enclosure | 独立实际 via_enclosure 捕获上的 neutral 图仍为 14/8/6 且局部 violation；cut-islands 为 3/0/3。正面积唯一端点先于 enclosure，audit 不参与端点筛选，违例不删除边。数学比较独立证明 Fraction 扩张、等号、多片整体覆盖、孔洞均按 exact 集合处理；完整执行矩阵另包含公开 captured 入口的既有 via_enclosure 与多片反例。 |
| A6 公开 DTO/wire/错误 | 确认 native tuple/list 单次快照、原生 literal 与 DTO 身份白名单、版本/closed wire 字段检查，以及 neutral 完整重建与 captured 再认证分层；未依靠编码后相等替代原对象图检查。独立逐字段 166 项错形明确 ValueError 拒绝；220/220 个 direct/readback 实际 constructor 故障保留原 exception object/cause/context/suppression，覆盖 local/effective/geometry/semantic/publication/readback 完整链及四类异常/中断。另 4 组 caller 集合复制和 8 项可变 text 拒绝通过，failures=[]。见 [边界报告](review/boundary-review.md)、[逐路径原结果](review/boundary-probe-result.json)。 |
| A7 范围与后续 | 所有原 drawn/base occupancy、semantic/query/target/readback 和外部 body 输入留在完整 prior chain；本地 BODY 仅同层几何导通，外部六图形不入本地图，无 label union、via-as-wire 或 S↔D 器件边。`coverage` 只列两种接触与局部 T05 sides，明确保留未消费 operators 和 deferred；非空本地 BTAP 定位 unsupported。完整坐标、region occupancy、U06/body/FIN/器件/标注、其余 mandatory/lifecycle、baseline/no_change/terminal/Stage6 仍后置。 |
| A8 工程与真实性 | [独立工程审计](review/evidence-audit.json) 68/68 通过，实际核对 252 项等于冻结 Git、当前及实际测试树、归档；两包及两实际安装各 94 runtime 字节一致。21 条命令及 42 份 stdout/stderr 身份闭合；双完整 1465、原 1149 node IDs 全保留并新增 316、双 strict typing 48 模块、新构建及两套干净安装源码外 smoke 采用这些认证后的执行记录。Reviewer 实际重新导入两个安装。原 W007 guard 仅增加具名纯 DTO/模块引用白名单，旧守卫实质保留；16 处保护路径无 diff。见 [工程报告](review/evidence-review.md)。 |

## 直接运行与采用证据

主 reviewer 实际运行 `PYTHONPATH=/workspace/Layauto /workspace/.venvs/w010-dev312/bin/python -B docs/tasks/W010/review/main-probe.py`，Python 3.12.14，45.12 秒通过。初次未指定 source PYTHONPATH 时误命中开发环境的旧安装，脚本在导入 W010 前失败；[原 ImportError](review/main-probe.initial-import-failure.txt)保留。显式 source 路径后的通过结果和原失败分列，没有把 harness 错误算作产品 finding 或工程通过。

数学专项实际运行 20,000 项谓词比较、4 个完整实际图和 5 个定位拒绝，20.03 秒通过；正常图经过 captured 公开结果，其余特殊/压力图及拒绝在成功实际 W005→W008→W009 捕获上使用公开 neutral builder，分层范围已在报告和 JSON 逐项标明。现有 fixture helper 只用于临时副本捕获重绑，未提供数学答案。

边界专项实际运行 `PYTHONPATH=/workspace/Layauto /workspace/.venvs/w010-dev312/bin/python -B docs/tasks/W010/review/boundary-probe.py`，Python 3.12.14，**1041.08 秒、exit 0、stderr 为空**。220 条故障路径中 direct 96、readback 124；TypeError/KeyError/KeyboardInterrupt/SystemExit 各 55 条，既有 suppression true/false 均检查。166 项错形拒绝与故障保真分列，未将“抛了任意异常”写成通过。代码及各路径原输出已核读，源码 hash 与冻结产品一致；这次单次大 wire 矩阵无中途 checkpoint，等待期间一直标为 pending，未根据 CPU 或空 stderr 预报结果。完整正式矩阵中的新算法、ValueError/UnicodeError 等额外故障与畸形对照，按下述工程身份采用。

工程专项实际重新检查所有源码/Git/归档/包/实际安装字节和原输出，并从 checkout 外重新 `-I -B` 导入两安装；没有冒称重新执行双完整回归、typing、build、install 或原完整 installed smoke。原输出为 3.10.22 **1465 passed / 3615.88s**、3.12.14 **1465 passed / 2614.99s**，各 strict typing **48 source files**。原 R1 guard 失败与 preflight partial 保留历史身份，未混入最终通过。

3.10 的旧 pip 在安装树 `direct_url.json` 留空 `archive_info`；实际 URL、本次 install report 中的 sdist SHA-256、实包及全部安装 runtime 字节一致，采用这些证据认定来源，没有补造 direct_url 内不存在的 hash。

## 限制

已读有限资源原始记录及对应源码身份，确认披露了重复捕获认证、aggregate 重建、wire/canonical/hash 成本。四个样本 wire 约 15–17 MB（去 optional cache），含 cache 的正常回执约 22.8 MB；共享 host 中正常公开 build 约 10.31 秒，34 节点例约 13.90 秒，累积 RSS 高水位约 988 MiB。全部资源样本 max-pieces=1，未证明最大输入、大量多片/孔洞压力上界或生产性能；本次未重跑性能探针。

本 review 只支持 W010 声明的 synthetic/local 几何图和逐侧 T05 判据，不证明整个 T05、全规则通过、完整 Stage2/M1 或真实 PDK/EDA 准入。Reviewer 只写本报告、`review/`独立附件及任务 Review 段，不修改产品、正式测试、原 verification、PM/current-work，不提交、推送、验收或合并。
