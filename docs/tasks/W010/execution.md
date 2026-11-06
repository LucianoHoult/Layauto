# W010 执行交接

执行者 `/root`，2026-11-05；工程证据整理 `/root/engineering_preflight`，domain/state 实施 `/root/graph_implementation`，几何判据测试 `/root/geometry_tests`，公开合同/异常测试 `/root/contract_tests`。后两者是测试实施者，不作为独立代码 reviewer。

起始 checkout 干净，远端目标/起始提交为 `9758a157115cc22d91ce095ac2002209b9f210d3`。本地原 `work@3be0b98359038bab6c23980b55a48987cc71a369` 保留；fetch 后在用户指定 `codex/w010-local-contact-connectivity` 工作。方案与未参与设计者的 [独立 review](plan-review.md) 先于产品实施，方案/记录提交 `dcb1d67`。PM 任务阶段、current-work、main、fixture/答案/历史证据不由执行者改写。

## 交付行为和判据

`normalization.build_local_connectivity` 接受成功 W009 捕获回执，先检查原对象图闭合，再完整往返重建原 W009/W008/direct/readback 链；rules payload 及 source role 都来自同一捕获。domain/state 只负责中立一致性与纯几何，公开 draft 构造器重建全部节点、边、分量、逐侧 audit。wire 是 closed/versioned/canonical；错误返回保留原 input 与 completed。非预期异常及中断按原对象和原 cause/context/suppression 传播，包括 expected policy failure 退出后 error result 的再次认证。

独立 region 是端点计数单位；同层 component 不用于合并候选，enclosure 不用于筛掉歧义端点。每条重复 connector 独立保留 edge/来源/逐侧 audit。接触边与局部 T05 独立，graph success 可伴 `local_enclosure_status=violation`；这不是全部 mandatory 或整轮运行成功。Exact 集合包围按 Fraction x slabs/y interval coverage 检查；不采用 bbox、单片、面积相等、floor/snap/epsilon。完整原 drawn/base occupancy、W007 输入/target/query、独立 external body 与 readback attempt 保留。

| 要求 | 可重执行的证据/判据 |
| --- | --- |
| A1 | `test_w010_geometry` 的真实 direct/readback 无 IO 组合、原输入/attempt 不变；`test_w010_contracts` 的 rules role、成组 rules/physical/drawn/formats 伪造与真实 bytes 再认证 |
| A2 | 独立 arrangement 点/线接触判据、手算整边/局部边/角点/gap、负坐标/大整数、CUT 非原轴及重排；[数学 helper](../../../tests/contracts/w010_cases.py) 不调用产品几何算法生成答案 |
| A3 | 完整手写 oracle/spec 的几何、成员和 connector 对照，正常 14 节点/8 边/6 分量、16 侧 audit pass；BN/BP 独立、channel 不导通、POLY 连续，无 net/device stamp |
| A4 | 无侧/多侧/重复导体/已同层接触候选仍歧义、边角无端点、错角色/连接对/predicate 拒绝；重复 connector 来源/audit 保留；公开完整节点/边/分组双向重建 |
| A5 | 原 cut-islands 临时重绑后 3 分量/0 边；原 via_enclosure VN 边保留且 LN 侧 violation；Fraction 阈值、等号、多片整体包围及孔洞假 bbox 的独立 arrangement 反例 |
| A6 | 公开 constructor、nested wire、全部新 record 字段、false success、foreign refs/units/operators/audits、literal/metaclass/Fraction/递归别名；新算法及全部嵌套旧认证/解码的异常身份、已有 cause/context/suppression 与畸形 wire 对照 |
| A7 | `coverage` 公开局部 scope、未消费 operator refs 和 deferred 义务；保留非消费 raw records 和六个外部 body 图形，非空本地 BTAP 定位 unsupported；不读答案作运行输入 |
| A8 | 最终双解释器完整回归、strict typing、新包、两套干净源码外真实组合 smoke 由最终 verification 回执绑定；原 1149 个测试节点不删除；既有架构守卫仅按具名文件/模块/符号加入 W010 的纯草稿依赖白名单，并新增 domain/state 方向保护。最终数字见下段，preflight 不能替代最终矩阵 |

首轮几何候选为 54 pass、2 个测试预期不符：M1 role 冲突已经由既有 reader 的 BodyReferenceTypeMismatch 拒绝，而 BODY role 错误定位归 physical owner。测试随后按原合同归层修正，没有放宽 reader 或改变产品输入解释。原起始快照 preflight 首轮漏带 W006 独立比较用的 `docs/tasks/W003/examples/records.json`；已保存 harness 失败、补齐快照及定向复测，未将其写成原 1149 项全通过。细节见 [preflight](preflight/README.md)。

首次完整矩阵 R1 的两解释器均命中既有 W007 dependency guard：该守卫已分别为 W008/W009 的 pure state 添加窄白名单，但尚未列出本次 W010 纯草稿/codec 依赖。R1 原失败、部分结果和中断原因保存在 [verification-r1](verification-r1/failure.json)，未冒记最终通过。执行仅补充 W010 两文件/模块/符号白名单并增加新 domain/state 方向保护；产品 runtime、读取和发布边界不变。该窄变动双解释器定向复核及独立检查保存在 [boundary-check](boundary-check/)，最终完整矩阵重新冻结执行。

## 资源和覆盖边界

全量有限扫描不使用 raw occupancy 作候选，因此包括 CUT 新边界、多片以及正长度共享边。N 节点、C connector、每 region 最多 P 片时，同层候选 O(N²P²)、connector O(CNP)、enclosure 每侧 O(P² log P)，分量 O(N+E)；公开 aggregate、捕获再认证与 nested wire 会重复重建，费用不能只算核心扫描。没有新增输入容量上限；原 reader 的限制仍适用。

[独立可运行的资源探针](performance_probe.py) 与 [原始结果](performance.json) 覆盖正常、cut-islands、额外 20 个孤立 M1、额外 8 条重复 CONTACT，共 4 个真实捕获组合。正常 raw capture 路径公开 build 约 10.31 秒、encode 约 0.71 秒、decode 约 13.68 秒；34 节点压力例公开 build 约 13.90 秒、完整 roundtrip 约 18.44 秒。各例去掉 optional normalized caches，wire 约 15.47–17.09 MB；保留 cache 的原正常回执 wire 实测 22,789,218 bytes。累积进程 RSS 高水位约 988 MiB，包含多层保留 wire 与前例高水位，不能作为逐例增量。

这些是共享 host 并发检查时的有限样例，全部 max pieces=1；多片/孔洞正确性由独立数学反例覆盖，未测大量多片资源压力，不作生产性能保证。探针记录源/配置及 fixture 前后 hash、版本、原命令和实际输出，不能将 core neutral builder 的较短时间冒充公开路径成本。

后续仍需完整制造/工艺坐标、region occupancy、外部 body/U06、FIN/器件抽取及语义 join、annotation overlay、其余 mandatory/lifecycle、atomic baseline/seal、no_change、terminal 和 Stage6。没有运行真实 PDK/EDA，当前图只证明本地 scope 中已声明的几何接触。

## 最终版本、验证与交 PM

最终产品与测试冻结提交为 **`0f5029df935bc0acd106aad1bc2be81304d4f442`**（产品初始提交 `fba1e7be688c5fce88834dc8b859a8660bff6b7f`，随后仅补依赖守卫与对应新测试）。最终 R2 在同一冻结 source 上完成，详见[验证说明](verification/README.md)、[完整回执](verification/receipt.json)与[原始命令/输出清单](verification/evidence-manifest.json)。

| 最终检查 | Python 3.10.22 | Python 3.12.14 |
| --- | --- | --- |
| 完整 unit/contracts | **1465 passed / 3615.88s** | **1465 passed / 2614.99s** |
| strict mypy | **48 source files，无问题** | **48 source files，无问题** |
| 开发环境 pip check | 通过 | 通过 |
| 本次新包的全新安装 | sdist | wheel |
| 安装 pip check / 源码外 `-I -B` 实际组合 smoke | 通过 / 通过 | 通过 / 通过 |

原 1149 个测试 nodeid 双解释器逐项核对保留，新增 316 个，共 1465 个；没有跳过原能力。21 条工程命令全部 exit 0，原 stdout/stderr、环境/依赖、命令/cwd/耗时、fixture/profile、实际安装目录与包来源均可核验。开发解释器为 `/workspace/.venvs/w010-dev312/bin/python`，最低版本为 `/workspace/.venvs/w010-py310/bin/python`；执行 host 为 Linux x86_64，非 Mac/真实生产 EDA。

最终[252 项 source manifest](verification/source-manifest.json) SHA-256 为 `cef29336dba1bf572fd30227f354365d4a4d780e721d089b70095589d0f55889`；[完整相关快照](verification/source-snapshot.tar.gz)为 `493d36ebeb4bd5d43f8bbb06139b27e3be7997dad12e913c9ca36c362ba843d1`。94 项 runtime Python/py.typed 文件逐字节满足冻结源码＝新 wheel＝新 sdist＝两套实际安装。两套安装 smoke 均得到真实 14/8/6 图及 16 侧 audit，覆盖 direct/readback、禁 IO、attempt 不变、公开重建与伪成功拒绝。

本次 wheel SHA-256 `f77c718aa292d8c15c37206a1543462e29888dc65e38e61cc830856f75c60232`，sdist `49b5fdd10ee7aca6f349dfcaea1d42292dfd647a6d05a9aa695d180d85d25d5b`；[包身份](verification/package-identity.json)和[两安装身份](verification/installation-identity.json)连同实际包随 Git 保存。最后一次只读核对确认根目录及快照的 source/tests/config/路径集合与 smoke 均未改变；[保护范围核对](scope-check.json)确认 current-work、架构、协作/环境、原 fixture/答案/legacy 和旧生产链保持，旧测试仅有具名纯依赖守卫扩展。

完整工程矩阵结束后，才向未参与实现/测试的 `/root/code_review` 发出正式独立代码 review 启动信号；review 结论、原 findings 与独立复核由 reviewer 保存，不由执行者代写。最终提交推送原分支、核对远端完整 SHA 后，只交 PM 核验；main/current-work 与下一任务由 PM 掌握。本记录不自行验收。

独立最终[代码 review](code-review.md)现已实际完成，新增及剩余必须修正项均为 0；其原结论由 reviewer 保存。报告 SHA-256 `0a94d2e8dfc01a274f85dff34ad06bb466c243a7b63f72bd7ea0831cf97c6b7f`，21 项独立报告/probe/原输出由[review 身份清单](review/final-review-identity.json)绑定（SHA-256 `c70f530791a216f3290cec00110e7eec5282bf938061717986f96879315de880`）。代码 review 没有要求产品修正，所有源、测试、配置、README 与受测/受审 `0f5029d` 相同；本次仅提交交付记录和证据。最终远端完整 SHA 在推送后的交接回复核对，PM 再维护阶段和入口。
