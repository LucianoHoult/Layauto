# W016 单 cell 分析工程交付记录

恢复基线 `6ca7b16cff0f953f9e7eacc834f88ac28e70abb6`，分支
`codex/w016-single-cell-analysis`，启动工作区干净。
[PM资源决定](pm-resource-decision.md)已解除纯report/capture倍率暂停，纯体积优化后置；
其他资源门及正确性合同保持。本记录是工程交接，不是PM验收或合并授权。

## 实现与合同

公开 `layauto_v2.analysis.analyze_cell(AnalysisRequest)` 从绝对manifest路径获取实际文件。
独立schema/header、完整captured-byte重parse Receipt及冻结result不改变旧DTO/wire/ref。
source-only语义不需要target/export/validation；认证后共享中立exact geometry、effective/local
图、channel/FIN、annotation和端子核，完整保留targets/fragments/gaps/conflicts/unmatched。

无body仍计算D/G/S，B及parent/global未知。所选synthetic body独立获取和认证，执行现有
全部body路径及T04/T05规则，外部形状不进local union。manual只显示预期，保留逐字段
SourceRef；instance_hint不产生受信parent mapping。未来selector不读文件且unsupported。
顶层状态优先级rejected > unsupported > completed，保留复合错误及已知source mismatch；
未完成facet带dependency。completed只表示分析请求处理完成。

每次新调用重新获取认证，旧结果不可变；没有运行中续传/隐式重试。report是完整诊断view，
没有decode或受信receipt续算入口，不产生run/attempt/baseline/terminal或发布许可。
预期错误保持原code/ref，未知异常及process interrupt传播。能力仍限synthetic/flat，query必需。

实际文件与演进见[恢复实施](resumed-execution.md)，用法见[README](../../../README.md)。
独立[恢复review](resumed-review.md)关闭R03–R10；原R01/R02及资源中断记录见
[检查点review](independent-review.md)，全部原失败和证据保留。

## 冻结与复现身份

[completed-source-identity.json](evidence/resumed/completed-source-identity.json)覆盖298项runtime、
测试及配置（含116个固定fixture文件），SHA-256：
`f99498abc0877bb918d7de88d66a5eda5d5591d41f8ce8102b04edc14826c052`。
[verify_frozen.py](evidence/resumed/verify_frozen.py)在每项最终命令前后逐文件验hash；
结果metadata绑定完整命令、cwd、起止时间、exit和原stdout/stderr hash。

[completed目录](evidence/resumed/completed/)保存最新检查；Python3.10.22与3.12.14的
[310环境](evidence/resumed/completed/environment-310.json)、
[312环境](evidence/resumed/completed/environment-312.json)含实际解释器及依赖版本。
Linux主机；双build明确`--no-isolation`并使用setuptools84.2.1/wheel0.48.0。
[构建身份](evidence/resumed/completed/build-artifacts.json)保留wheel/sdist长度/hash。
双clean安装分别逐hash匹配121个runtime文件，安装树/构建物/缓存均在/tmp。

[source外smoke](evidence/resumed/installed_smoke.py)在`/tmp`、`python -I`下运行，包必须
来自各自site-packages；实际no-body/body/mismatch/bad-body/manual五case及surrogate请求边界
均通过。[smoke输入身份](evidence/resumed/completed/smoke-input-identity.json)绑定128文件和
实际执行脚本。显式[迁移helper](../../../tests/support/analysis_inputs.py)只生成新输入声明与
closure，不生成观测答案；原header/raw/旧cache保存，固定fixture与答案未改。

## A1–A8 覆盖

| 项 | 实际依据 |
| --- | --- |
| A1 | 真实无body文件；FIN5/7、14node/8edge/6component、六D/G/S equal，B及完整source比较indeterminate；公开API及独立真实调用 |
| A2 | 同来源旧W014与新链逐body对象/path/rule/audit/terminal对照，完整local graph相等；新header/annotation绑定造成的query refs明确另列 |
| A3 | 真实缺文件/syntax/hash/top/role/URI/unit/未知字段及各body错误；manual绑定/日期/重复/伪assurance；future selector无IO；独立symlink/NUL及原parser位置完整相等 |
| A4 | FIN4对5与partial FIN、局部T05 violation；独立GDS/query手算target40/covered24/gap16、conflict8；独立100nm² unmatched、复合error加已知mismatch不丢失 |
| A5 | 每实际path捕获一次；实际captured后封锁20项FS操作仍完整计算；补资料新调用/旧结果冻结；raw/payload/native storage/alias/root/角色防伪，异常及interrupt传播；R01–R10修后独立反例 |
| A6 | 新值被旧consumer/codec拒绝；旧read_inputs/W006不变；四路完整旧DTO/ref/公开wire精确双侧比较；实际SREF保持flat capability的原unsupported，不flatten |
| A7 | 最新冻结三个独立timed调用及另外三个profiled调用，完整API耗时/HWM/bytes/阶段/构造次数；详下 |
| A8 | 最新双mypy各75源、双build、双clean源码外5case smoke通过；双3.10/3.12全量各1953 passed、补充各3 passed/8 subtests passed，全部exit0；独立最终工程核对见review |

## 资源口径与结果

[探针](evidence/resumed/resource_probe.py)使用Python3.12.14，每case独立进程，三case串行；
本表不是双解释器性能比较。整体墙钟含实际获取、
完整认证、全部计算及完整report；阶段有包含关系，不能相加。HWM为Linux进程累计
`ru_maxrss` KiB，不是report增量。capture bytes为去重SourceFile.data总字节数；report为
完整compact UTF-8、无LF、未压缩字节数。新输入URI/compact声明与原W015候选不同，
不能用倍率变化推断同输入性能变化。

| case | 整体秒 | HWM KiB | captures | capture bytes | report bytes | 倍率 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 无body正常 | 2.673733 | 29344 | 23 | 42395 | 235792 | 5.5618 |
| 有body正常 | 3.099535 | 29508 | 24 | 45202 | 259620 | 5.7436 |
| 无body FIN mismatch | 2.760156 | 29568 | 23 | 42395 | 235838 | 5.5629 |

精确值、阶段、源码/输入/依赖身份见`completed/resource-*.json`。
`completed/count-*.json`为**另一组profiled调用**，不能把其约12秒混作上述timed耗时。
GDS/CDL/query各2 parse（获取解析+完整Receipt重parse），Receipt构造1；中立顶层
layout/partition/occupancy/effective/local/channel/annotation/terminal各1，body仅选中时1。
各owner中立一致性重构次数另列，不能把“顶层1次”说成所有构造仅1次。
未发现完整capture按facet复制或认证次数随facet增长；报告不含raw或多份完整旧Result。

已解释的5.56/5.74倍率依PM决定保留。body新增完整路径/规则审计/B支持/来源；没有删诊断、
删来源、跳认证或只压缩文件来过门。原[构成统计](resource-checkpoint.md)只适用于当时
235613-byte内部原型，本轮没有做第三轮专用字段/地址压缩。这三个小synthetic样本不代表
最大输入、真实PDK/EDA或生产主机性能；旧七阶段大wire不是新API的同口径reference。

## 实跑、采信、原失败与限制

本次最终冻结实跑双typing/build/clean安装、三timed+三profiled资源及纯度/防伪/边界回归。
长测试命令`pytest -p no:cacheprovider tests/unit tests/contracts -q --maxfail=1`每解释器
collection为1953项；fixture_support的3项已在同冻结双侧补跑通过，完整tests共1956项。
只在失败时failfast，通过时覆盖全部节点，不删测试或修改golden。
[节点范围审计](evidence/resumed/completed/collection-scope.json)说明根默认额外收集的1项
W011历史docs资源插件demo（自述不属正式源码/测试快照，需专用插件参数），不把1957误写为
产品矩阵数，也不为该历史demo改变当前配置。

四路旧兼容全部实际逐bytes通过：[parity-summary](evidence/resumed-review/parity-summary.json)。
基线固定`efc881d461ce2c87370f6df402ac50ae43c094e8`，同绝对URI/bytes；基线完整decode，
候选完整构造DTO并公开encode后精确比较，无重复candidate gzip。normal-direct实跑于a306
冻结，其余三路于release冻结；到当前f994，相关旧producer/wrapper/codec/config均同bytes，
不import新analysis模块，独立按相关身份采信，不重复大wire。

本轮新增44份基线gzip共22305592 bytes在成功精确比较后移/tmp归档；Git仅保存原报告、
脚本、来源/长度/hash与比较证据，[归档映射](evidence/resumed-review/baseline-archive.json)可查。
历史已提交normal-direct唯一快照保持。若临时归档不可用，未来须从固定提交/输入/URI重建，
不能把hash当作现存wire快照。

| 原失败/中断 | 原证据及修正 |
| --- | --- |
| 新API收集、partial状态聚合、A2旧cache身份失配 | `evidence/resumed/`原attempt记录；参数改名、保留局部计算error及显式迁移旧cache，固定答案不改 |
| release全量2 failed/488 passed/181.86s后SIGINT | [原日志](evidence/resumed/release/pytest-312.stdout.txt)及interruption sidecar保留；R08把Path请求移公开facade，domain恢复中立，原AST未放宽 |
| verified全量1 failed/571 passed/296.93s | [原日志](evidence/resumed/verified/pytest-312.stdout.txt)及正常exit1metadata保留；R09移纯重放adapter到importer，仅为两新normalization文件精确登记纯module/symbol依赖；原IO/旧模块禁令不变 |
| R10相对root伪造 | relative_root原被接受，现拒绝；relative raw alias原本正确拒绝，是对照而非第二漏洞；独立无IO重放复核通过 |

早先af/a306/release/verified冻结与各自输出均保留，不冒记成当前全矩阵。
原按不同collection顺序猜失败节点误指W008的说明已明确纠正，权威是原traceback的两个AST失败。
独立R03–R10原反例、修正范围及逐项复核见review，不把旧58项当本轮新增功能通过。

最终双长矩阵均正常完成，源码/正式tests/config未再改变：

| Python | unit/contracts | pytest秒 | driver秒 | fixture support | exit |
| --- | ---: | ---: | ---: | --- | ---: |
| 3.10.22 | 1953 passed | 10798.06 | 10801.143035 | 3 passed / 8 subtests passed | 0 |
| 3.12.14 | 1953 passed | 7745.36 | 7747.786189 | 3 passed / 8 subtests passed | 0 |

[最终执行核对](evidence/resumed/completed-validation-summary.json)汇集11项命令metadata/hash，
每项均exit0，所有原stdout/stderr hash及298项源文件已核一致。双全量按顺序串行；
fixture helper仅为不足1秒的小型补充，既有节点未重复，未把subtests另算pytest节点。
最终独立工程核对以[review](resumed-review.md)的结论为准。
始终未覆盖：真实PDK/EDA/生产方言/隔离主机、任意层级、完整M1、无query、可信LVS/窗口、
实际parent/global映射及修改/发布。源/正式tests/config变化须重新冻结最终双矩阵；依赖/输入
改变、身份无法闭合、集成冲突或新风险按影响补验；纯文档补记只核身份/归属/链接。

本工程交付仅提交推送原分支交PM，远端完整SHA由交接回执核对；
不改PM要求/阶段/current-work，不自行验收、合main或删分支。


封包空白检查：源码、正式tests/config、Markdown、JSON和证据脚本通过。
原命令txt保留pytest失败行尾空格及build stderr末尾空行；完整`git diff --check`
会报告这些原始格式。仅在空白检查中排除原日志txt，原bytes/hash保持，产品验证无排除项。
