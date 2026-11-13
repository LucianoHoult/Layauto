# W014 执行与 PM 交接证据

本文件由执行维护，不代写 reviewer 结论或 PM 验收。最终结论以冻结版本、
实际工程回执和 [独立代码review](code-review.md) 为准。

## 恢复、方案与实施范围

原远端准备head `8f3f39562ed04d790c8d6c015f7c9b8742b6a3c4`，工作区干净；
从已验收W013产品恢复，未带入W012 A2。具体方案、body调查、A8提案及独立
方案门review冻结于 `40559e0186f7d80bb8a7f3256c900e0fadd66191`；门条件
剩余必须项0后才实施runtime。

产品只新增5个模块：domain terminal DTO、derive terminal聚合/body只读证明、
normalization认证入口及codec；另更新公开导出和strict typing清单。测试只新增
W014 helper、5个contracts模块及2个unit模块，不修改固定fixture/答案、旧wire/
codec/认证或历史证据。架构、roadmap、current-work及PM要求/阶段/验收段不改。

公开入口 `build_terminal_relations(LocalConnectivityResult)` 复用同一真实capture。
完整旧W010输入只保留一次；W011/W013使用原neutral builders共用local/source/
derived，channel输出compact保留，annotation保留原区域/分量coverage与conflict。
Result另保留compact NormalizationFacts，source期望、target intent和observed
各自独立。外部body不进入本地layout/occupancy/physical graph或导出。

body path的 `rule_status` 明确覆盖T04.body/T05.contact_enclosure；八端source
比较由typed TerminalRelation按T08独立报告。因此source B mismatch可以与已证明
的几何/包围事实同时存在，不能用前者改写后者或以body规则事实替代T08比较。
完整提取、其它mandatory规则、生产LVS、baseline/no_change/terminal均未建立。
`source_comparison_status` 只汇总W011已计量FIN/L/W与本轮八端的有限比较，
不是完整source/model/VT抽取匹配；coverage保留该scope及未覆盖项。

## 原失败与修正链

首个实际normal组合因native整数阈值错误调用rational(map)失败，见
[原失败](development/first-normal-failure.md)、逐文件身份及完整快照；不记为通过。
改为schema/native验证后的Fraction整数提升，保留精确值和阈值来源；unit中有
真实owner回归。独立review发现的CR-01–08保留原问题、独立反例、处理与复核，
由reviewer自行维护；不删除或把修前输出改写为通过。

## 验证恢复点

首轮资源尝试中W013三路及W014 direct通过，W014 readback被新storage guard
误拒，mismatch尚未跑；[原失败/快照/结束事实](resources-early/attempt-closure.json)
完整保留。原因是六种旧W006 DTO的合法init=False kind仅在class default存储。
最小修正只准许未改写的这类默认值；未声明属性、缺必需/init字段与可写alias
仍拒绝。真实W006轻量回归及新公开readback资源均已验证修正。

[R2三路](resources-r2/suite.json)全部实际通过，公开旧W010 decode计数各为
build/encode/decode=1/1/2；同阶段各调用一次W011/W013 neutral builder及body
evaluator，不嵌套两个完整旧Result。单次旧公开decode仍包含其原有内部重建，
计数不代表底层每个对象只重建一次。旧W013同环境三路reference按
[独立身份采信材料](resource-adoption/README.md)引用，不重标原source_id。

组件build+encode+decode耗时比reference增加8.4%–13.7%，wire增加约345KB，
三路进程主工作负载峰值约199/507/199MiB，未发现内存或wire倍增。原始过程
在packet分解/证据记账前固定HWM；单样本、非增量内存、非最大输入保证，不能
据此声称稳定性能改善。最终资源判断由独立reviewer核证。

中间候选 `8497c87a…` 的定向回归保留为64 passed/1 failed：gate_operator
变体原测试错把W009拒绝预期为W014准入。已改为真实reader→W008→W009的
UnsupportedRegionOperator边界，单点1 passed；runtime不为测试放宽。CR-08的
原review调查漏读W009由reviewer保留并更正，不伪装到达W014。

随后 [contracts-r4](development/contracts-r4.command.json)为16 passed/1 failed，
暴露残缺channel投影泄KeyError；独立CR-10又确认Result.value保留input变更会被
compact校验静默丢弃。codec现先比较所有实际保留字段的typed canonical快照，
仅对重建对象投影；五项针对性回归通过、扩展独立攻击拒绝，R3三路通过且valid
wire字节/hash与R2不变。[R3身份/成本](resource-adoption-r3/README.md)保留原版本。

[contracts-r5](development/contracts-r5.command.json)为12 passed/1 failed，
原因是执行自写的缺cell反例用了非法名称`absent-cell`，在预期边界前就被CellId
拒绝；改为合法但不存在的`ABSENT_CELL`，不修改产品safe-next逻辑。

独立CR-12发现body/local.rules EvidenceRecord外壳未知schema/parser可中立构造
及encode，decode才拒。新W014原存储检查后统一重构SourceRef/EvidenceRecord
并比较全部字段，旧class/codec不改；相应67项轻量及17项真实修复回归通过，
65模块strict typing通过。原失败命令、输出、各完整源码快照均分别保留。

该轮候选源为 `998aa8052b3a6c89e3f87e029134ef8f6601535616c8b327d5ada44a29351a84`；
后续R4、开发闭合及最终冻结见下。此处的早期修正不单独宣称最终工程通过。
安装smoke的mismatch四边包围期望已按真实GDS由20/20/20/20纠正为20/20/20/26，
见[原脚本/修正与独立数学](smoke-assertion-repair/)；不得把工具静态核验代替实际安装。

开发门最终闭合：R6保留85 passed/1 failed，失败是测试误用ChannelSeed不存在
的source属性；改为真实raw坐标operand后，只有该测试分支变化，独立301项身份
核验支持前85项采信（56 unit、11 body scope、18 codec）。
[剩余80项](development/remaining-r7.command.json)在新源实跑 **80 passed / 644.58s**，
覆盖闭合165项新增/受影响范围。原失败/快照不改写为完整通过；开发采信不替代
最终新源双1889全量。

产品、测试与配置冻结提交 **`66f5b1e5369549ed8df361f89f099acfd2f39e17`**，
完整source_id **`c7769fcbfb0312b93e4d44628c77ff21e273698a537eaba0e1454734b049d364`**，
见[frozen-source](development/frozen-source.json)。286项selected source/111 runtime，
1889 collected（原1731完整保留），strict typing65。R4与冻结源只差测试分支，
runtime/config/input/probe字节不变；[最终三样本选择](resource-adoption-r4/final-selection.json)
透明引用clean direct与原R4 readback/mismatch，无源/输出重标。
独立资源门闭合后，最终双解释器矩阵均已通过；构建及安装smoke由runner在
两组矩阵完成后串行执行。[最终整体回执](verification/receipt.json)为passed，
21条实际命令全部exit0，全部检查后再次核286项selected source身份未变。

矩阵等待期另由未参与实现的reviewer完成[授权范围审计](review-evidence/authorized_scope_audit.stdout.json)：
1356项核验覆盖实际tracked/untracked改动、PM要求/阶段/验收原文、固定样本、
旧runtime/codec、两次noreply提交与冻结字节。临时`work/`单列为本轮scratch，
已整体搬至`/workspace/work/w014-repo-scratch-20261113-final`，保留原URI文本，
不作为fixture变更或正式证据提交。该检查不代替最终工程或PM验收。

## 最终资源证据及复用范围

主样本由[独立资源review](resource-review.md)核准，按原路径和hash引用；
R4测量源`998aa805…`到最终`c7769fcb…`只有一个测试分支变化，runtime、
配置、输入和probe均未变。前述R2/R3数值是各自原时点的历史记录，当前采用
下表R4数据。normal direct原R4样本启动时与6.30秒review probe有交叠，原件
保留但不计主耗时，另取独占clean direct；其余两路不重复测量。

| 路径 | build＋encode＋decode（秒） | 对同环境W013比值 | 完整wire（bytes） | 新增wire（bytes） | 进程峰值（MiB） |
| --- | ---: | ---: | ---: | ---: | ---: |
| normal direct | 61.894 | 1.133 | 23450036 | 345944 | 196.40 |
| normal readback | 114.963 | 1.031 | 60077912 | 345944 | 491.91 |
| extraction mismatch | 61.919 | 1.093 | 23449815 | 344703 | 204.29 |

各路旧公开W010 decode调用仍为build/encode/decode=1/1/2，neutral W011/W013
及body各阶段各调用一次；valid wire字节/hash在R2→R3→R4保持不变。W013
reference为原source `803b4c4f…`，独立审计核106个旧runtime依赖完整字节未变，
没有把旧报告改标为最终source。clean direct wrapper额外设置MYPY_CACHE_DIR，
产品路径不读取它；不将两次进程的全部环境声称为逐字相同。

16GiB/4CPU环境中，独立资源门允许两解释器矩阵并行、每组pytest仍串行，
build与双安装smoke在其后串行；不与其它产品链重叠。上述均为单样本HWM，
不代表最大输入/完整矩阵上界、独立helper成本、稳定性能优化或生产表现。

## 要求与交付位置

以下列实现及检查入口；最终工程通过事实以末尾冻结回执为准。

| 要求 | 交付及验证入口 |
| --- | --- |
| A1 | 单一完整W010捕获认证；source/target/seed/tech/body完整来源闭合，run/database/单位/FRAME/对象绑定。`test_w014_contracts`、`test_w014_readback_storage`与独立来源/存储探针 |
| A2 | 每source device有完整ordered D/G/S/B target；本地六端读取W011真实topology与W013分量证据，共享gate双关系。`test_w014_relations`正常/未知/冲突/source mismatch/target-only |
| A3 | actual GDS layer+exact bbox唯一绑定；FRAME左续接、typed tap正面积唯一两侧、exact rail query锚定及真实分量冲突传播，独立context不union本地图。body scope及CR-03/04/06/07独立反例 |
| A4 | 全active、local/external N×P body对、全external tap（含orphan）审计；T04/T05阈值取同源rules；八端T08与几何/包围分列。本地16项T05原审计不变，body scope实际local overlap与原enclosure见证 |
| A5 | 七个body见证+C22按实际reader/组件边界；REQ-01精确901/20≠45；点/边/面积、类型、绑定、operator、歧义及错误提供证据定位，不伪造sealed/terminal。gate声明实际在W009拒绝 |
| A6 | 全source八端，不因缺channel丢target；原FIN4对5、全部target differences和W013 coverage/conflict保留。直接覆盖3170/正常总35090、mismatch总34634nm²；未标注OD/body仍显式存在 |
| A7 | 新DTO原生值/不可变/原存储字段全集、合法class default、完整旧evidence重构；codec认证全部保留输入与输出、typed snapshot防map冒充、closed canonical wire/ref、原异常历史。CR-01/09–12及formal native/codec/storage/evidence回归 |
| A8 | [生产单cell方案](production-body-scope.md)四类小样张、最小资料、可信替代/人工声明边界与可继续/须阻止操作。仅设计，现行reader必填和D1=A不变 |
| A9 | [方案review](plan-review.md)、[代码review](code-review.md)、[资源review](resource-review.md)；全部新测试与原1731 IDs保留，最终双3.10/3.12全量/typing/build及双clean安装源码外三路smoke全部实跑通过；独立最终review结论由reviewer维护 |

正常有限端子样张为MN0 D=Y/G=A/S=VSS/B=context VSS、MP0 D=Y/G=A/S=VDD/
B=context VDD；两B本地observed集合仍为空。保留14 nodes/8 edges/6 components，
两条context链共6外部图形不进入occupancy。该样张不表示完整extraction或LVS通过。

## 最终冻结工程检查

`verification/`在唯一冻结快照上实跑两组完整矩阵，各1889 collected且原1731
IDs无遗漏。没有将旧W013完整矩阵或开发前缀采信代替本轮全量。
完整原命令、输出、环境、快照、构建物及hash由
[evidence-manifest](verification/evidence-manifest.json)归档。

| 检查 | Python 3.10.22 | Python 3.12.14 |
| --- | --- | --- |
| 全量pytest | 1889 passed，10784.59秒；wrapper 10787.714秒 | 1889 passed，7731.42秒；wrapper 7733.730秒 |
| strict mypy | 65个source files，2.096秒，通过 | 65个source files，2.275秒，通过 |
| 开发环境pip check | 通过 | 通过 |
| clean安装 | 全新sdist安装、pip check及三路smoke通过，smoke 461.918秒 | 全新wheel安装、pip check及三路smoke通过，smoke 328.685秒 |

wheel与sdist构建实际3.515秒通过，均核完整111项runtime字节等于冻结源。
实际解释器与依赖见`verification/environment-310.stdout.txt`及
`verification/environment-312.stdout.txt`；命令、UTC时间、cwd、环境覆盖及原始
输出hash分别保留在各命令JSON。两套安装完整111项runtime字节均与冻结源及
对应构建物一致，实际import来自各自clean环境的site-packages。

两套smoke均在仓库及冻结源码树之外以`-I -B`执行normal direct、normal readback、
extraction mismatch；使用同一冻结fixture，不从tests helper导入答案。三路均
public roundtrip相等、8端=6本地+2独立body，本地14/8/6图及两unknown body
component保持；mismatch仍为MN0 FIN4对source5，readback不推进attempt、
checkpoint不变且无terminal。安装mismatch临时URI仅为正确性检查，不作资源计时。

最终回执SHA256为`fbfd34d4c63e00c6e1cdd5a340487be6306a10bb0707605a229b4eaa527fe938`；
证据manifest SHA256为`0a507f3c1d8d667d84a3d5fc59210c79b2d9845bab6d4f3def75331a3c66baa6`。
完整最终独立工程/代码review见[reviewer记录](code-review.md)，不以执行者摘要
替代review或PM验收。
[最终独立工程审计](review-evidence/final_engineering_audit.stdout.json)实际840项
通过，核原始证据、21命令、live/Git/完整快照、两包和双安装全部runtime身份，
未重跑产品链。

## 交接时的验证复用边界

| 类别 | 范围 |
| --- | --- |
| 本次实跑 | 新增/受影响开发范围、修复后的定向回归、独立关键反例及三路资源检查均保留原命令/输出/快照。最终双1889全量、双65 typing、build及双clean安装源码外三路smoke实际通过，完整结果见`verification/`原回执 |
| 按身份采信 | 开发85项前缀只按单测试分支delta采信；资源R4到冻结源只变该分支，旧W013 reference依赖完整字节不变。原1731 IDs完整保留不等于采信旧全量来替代本轮1889双全量 |
| 未覆盖 | 全部model/VT抽取、S/D swap、device reduction、其它mandatory规则、生产PDK/EDA/LVS、baseline/publication/ECO及完整M1均不在本轮；A8是设计而非可省略body_context的新reader实现 |
| 补跑触发 | 相关源码/测试/config、解释器/依赖或输入变化，合并冲突或组合行为变化，证据缺失/失败/身份不闭合，或新独立风险/合同要求；修正产品后重新冻结并完成要求的最终矩阵。仅换角色/session不触发重复双矩阵或复制大wire/安装树 |

PM接收入口为本文件、任务Review段及最终整体回执。冻结后的补记仅为文档、
证据及独立review，不改变受测产品源码。使用项目noreply提交推送原W014分支，
远端完整交付SHA由推送后实际核对并在本次交接回复给出；不自行验收、合main
或删除分支。
