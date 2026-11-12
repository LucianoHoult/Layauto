# W013 最终工程证据身份专项审查

审查者 `/root/input_contracts`，2026-11-12；未参与W013方案设计或实现。
本专项只核source/test/config、输入、环境、包及工程回执身份；产品/合同/组合/资源的完整
独立review由 `independent_review` 负责。本文件不代替其结论或PM验收。

## 预检：最终矩阵仍在运行

受审最终冻结source_id为
`6463eb67b1c1ce5b9fd1fca436fa499a4ad14da004ef8fcd913872bd350443a9`，
冻结HEAD `8dca80fee138b48f353f791a70d96765426c342a`。
独立[审计脚本](review-evidence/final-audit/audit.py)只读取文件、Git对象和工程记录，不import
产品、不执行pytest/mypy/capture/build/install/smoke。预检命令及原输出见
[原stdout](review-evidence/final-audit/preflight-r2.stdout.json)与
[原stderr](review-evidence/final-audit/preflight-r2.stderr.txt)。45项检查通过，0项失败：

- 273项实际源码/测试/config完整路径与SHA映射、可重建snapshot tar的全部成员、真正执行的
  `/workspace/work/w013-final/source`字节，均与冻结清单一致；开发110项回执也属于该完整映射。
  受测身份覆盖实际工作区选择，不以HEAD或测试数量代替源码身份。
- 相对准备基线`d6182fe`，产品/测试/config恰为6个新增runtime、公开入口、typing配置与4个
  新测试文件。全部已验收fixture及旧codec逐字节不变；旧报告、architecture/collaboration、
  current-work、roadmap未改。任务PM要求/阶段及PM验收段与原字节相同。
- 两套真实collection均为1731项，相同nodeid集合；原A1基线1656项全部保留，新增75项只在
  W013测试文件中。baseline collection自身与准备基线Git对象逐字节一致；不是用旧矩阵冒记新产品通过。
- 环境回执实际为Python3.10.22/3.12.14，产品导入均指向冻结snapshot；解释器可执行文件hash
  与环境准备回执一致，实际依赖版本与原准备的import记录一致。两套依赖有合理版本差异，
  未将“同一环境”当作共同版本假设。
- runner/source_identity/smoke三工具当前原件及verification副本逐字节相同；双worker调度
  明确等两矩阵结束后才构建及串行两安装smoke，没有把并行gate当作单次成本改善证据。
- 原clearance字节SHA保持`ac4ebb0b…c1888a`不动。其原`review_commit=065827b…`确实没有
  code-review文件；[引用补正](resource-clearance-reference-correction.json)指向实际
  `8dca80f…`中的同一review blob，SHA完整匹配`995c852d…4ff349`及冻结clearance记录。
  这是原引用错误的可追溯修正，无source/test/config、原review内容或原clearance字节变化。

首次审计把已知不存在的旧review对象误当作可读取blob，工具以CalledProcessError退出；
[原stderr](review-evidence/final-audit/preflight.stderr.txt)保留。修正为显式核该对象不存在后，
上述预检通过。这是专项审计工具的启动/处理错误，不是产品测试失败或通过证据。

本次预检结束时最终`receipt.json`及`failure.json`均尚不存在；只有双环境及双collection
完成回执。**最终双全量/typing/build/双干净安装源码外smoke尚未获得完成证据，不宣称通过。**
审计脚本已准备`--complete`路径，待runner完成后独立核所有命令/原日志hash、1731项双全量、
60文件双typing、包/两安装完整runtime字节与实际三路smoke结果。

| 类别 | 本专项事实 |
| --- | --- |
| 本次实跑 | 45项只读Git/字节/快照/collection/环境/工具/引用身份审计 |
| 按身份采信 | 原开发及资源/环境记录按完整source/input/tool身份引用；不重复产品捕获或全量 |
| 未覆盖 | 正在运行的新冻结最终矩阵、构建、双安装smoke完成状态及其最终证据 |
| 补跑触发 | 源码/测试/config/依赖/输入变更，identity不闭合、原证据失败/缺失或新风险；仅文档引用补记不触发双全量 |

当前结论：身份预检通过，最终工程审查待runner完成。本专项没有修改产品、测试、配置、
已验收fixture/答案、既有finding/报告、PM阶段或current-work。

## 首轮失败与R2重新冻结（追加，2026-11-12）

上节“最终矩阵仍在运行/待完成”是预检当时事实。首轮双pytest随后在同一个保留W007
`test_normalization_and_new_domain_keep_pure_dependency_boundaries`（node454）暴露架构guard
未允许W013两个normalization模块引用immutable AnnotationDraft。执行者已保存
[controlled-stop](verification/controlled-stop.json)、[failure](verification/failure.json)及双解释器
原stdout/stderr并停止剩余已知失败执行；**首轮没有完成双全量，不是通过矩阵**。

修正仅为`tests/contracts/test_w007_contracts.py`内的具名immutable draft白名单：限制为
`net_annotation.py`/`net_annotation_codec.py`、精确模块`layauto_v2.state.annotation`及唯一
导入`AnnotationDraft`；未开放其它state/publication依赖。原runtime/config/input及W013新增
75项测试不变。执行记录相关3个guard已通过，该定向结果仍不能代替新冻结最终矩阵。

新source_id为`2c5724a9d3ecf99913857ad89015c03c03475ae762c1c8ab00b5146fd3eec278`。
R2拟在`verification-r2`、`/workspace/work/w013-final-r2/source`执行；当前等待clearance与snapshot
准备完成通知，尚未进行R2预检或声称通过。已新增可选择attempt的
[审计工具](review-evidence/final-audit/audit_attempt.py)，原audit.py及原预检输出/hash保持不变。

### R2只读身份预检完成

R2实际冻结HEAD为`2a45938aba8e751183d472d660a1ab66a1063636`，完整source_id与上述新值一致。
`audit_attempt.py --attempt r2`实跑47项检查全部通过，原输出见
[r2-preflight](review-evidence/final-audit/r2-preflight.stdout.json)。273源路径及字节=完整tar=实际
R2执行snapshot，原106个runtime完全相同；唯一源码映射变化就是保留W007 guard测试。
双collection仍相同1731项、1656旧项完整保留、新增75；环境/实际导入/依赖、三冻结工具、
fixture/旧codec/PM要求阶段/current-work、R2clearance实际review blob身份均闭合。

另以独立[r2_delta_audit.py](review-evidence/final-audit/r2_delta_audit.py)核R2资源采信证明，
[12项审计](review-evidence/final-audit/r2-delta.stdout.json)全部通过：proof/review的hash、原/新
source_id及唯一test delta完全对应；逐源码恢复原guard仅差精确白名单；原三路resource probe
hash保持；旧停止双pytest的-15和原日志hash、整套停止证据manifest均保持；定向3passed回执
属于新完整源码身份。原resource测量仍绑定旧source_id，不被改写成新实跑。

预检结束时R2最终receipt/failure均尚不存在，完成记录仍只有环境/collection。
**R2最终双全量/typing/build/双安装smoke继续待实际完成，当前只有身份预检通过。**
本专项未重复产品捕获、测试或矩阵；R2预检及工具原件hash见
[新增manifest](review-evidence/final-audit/r2-preflight-manifest.json)。

### 固定输入与原资源捕获的追加身份核证

按执行者在矩阵期间的专项派发，另以只读
[fixed_input_audit.py](review-evidence/final-audit/fixed_input_audit.py)实跑137项检查，0失败，
[原输出](review-evidence/final-audit/fixed-input.stdout.json)逐项保留URI、实际/记录SHA及字节数；
[工具与输出manifest](review-evidence/final-audit/fixed-input-manifest.json)固定本次审计身份。

固定外部URI `/workspace/w012-inputs/extraction-mismatch`当前恰35个文件，无额外或缺失路径。
它们逐字节对应W013原恢复回执、原A1 preflight固定target及其origin；每个origin又与原A1
最终冻结manifest、R2新冻结manifest一致。原A1 preflight本身已对照准备基线Git对象核字节。
resource04三路每路31个实际capture source（合计93项）与当前相应固定URI及上述原输入hash/
字节数闭合；normal direct/readback的根仍为原fixture，mismatch仍为原固定外部根。
全116个已验收fixture文件另与A1、当前工作区及R2真实执行snapshot逐字节一致。

这只补强**原resource04结果的输入身份**，未重跑capture/performance/pytest或改写任何原回执，
不将R2安装smoke的临时mismatch路径当作固定URI性能比较。此时最终矩阵及安装工程证据仍待
执行者完成通知后再核，**不提前宣称A8完成**。

## R2最终工程身份核证完成（追加，2026-11-12）

在执行者通知R2 runner exit0且最终receipt存在后，本专项实际执行
`python -B docs/tasks/W013/review-evidence/final-audit/audit_attempt.py --attempt r2 --complete`。
[原stdout](review-evidence/final-audit/r2-complete.stdout.json)、
[原stderr](review-evidence/final-audit/r2-complete.stderr.txt)及
[命令回执](review-evidence/final-audit/r2-complete.command.json)保存此次独立核证。
**148项检查通过，0失败；本专项无必须修正项。**

完整受测身份仍为冻结HEAD`2a45938aba8e751183d472d660a1ab66a1063636`、273文件source_id
`2c5724a9d3ecf99913857ad89015c03c03475ae762c1c8ab00b5146fd3eec278`。
当前源码/测试/config字节、实际执行snapshot、tar、manifest和最终receipt再次逐项一致；
没有用旧source_id或旧A1矩阵替代本次最终产品矩阵。

| 已实核的原最终工程记录 | 结果与身份 |
| --- | --- |
| Python3.10.22全量 | 1731 passed，9255.950秒；原1656项完整保留、新增75 |
| Python3.12.14全量 | 1731 passed，6655.812秒；与3.10相同完整nodeid集合 |
| 双strict typing及pip check | 各60源文件通过，所有命令exit0 |
| 新wheel/sdist构建 | 两包各106个runtime文件与冻结源码逐字节相同 |
| Python3.10干净sdist安装 | 实际106文件=sdist=冻结源码；pip check通过；源码外`-I -B`三路smoke通过，434.159秒 |
| Python3.12干净wheel安装 | 实际106文件=wheel=冻结源码；pip check通过；源码外`-I -B`三路smoke通过，313.429秒 |
| 完整工程回执 | 21条命令全部exit0，各原stdout/stderr hash与单独/总回执一致；最终81份证据manifest逐hash通过 |

两安装smoke实际导入各自clean环境的site-packages，既不从checkout也不从冻结snapshot导入。
三路均走public build/encode/decode，结果完整roundtrip相等；14targets、8query evidence、
6components，direct覆盖3170nm²、正常分母35090nm²、mismatch分母34634nm²；原attempt/
checkpoint不推进且无terminal。源码外smoke的临时mismatch URI仅作正确性见证；固定URI
性能身份仍由上面的35文件/93captured-source审计及原resource04单一来源负责。

新wheel SHA-256为`4feaed09e9b8a52712a01947a7dcdd69833fbc82957094f59fd301af0ca08dde`，
sdist为`177bb9f881f6c2ede1fbf8abf144723cf7b2d0a960099a506e70b1d7ab2fba44`；
snapshot为`6524d0d1fcab71c9a0c641c5a274bee0ccf3d868e251372d18ef45a7daf010a1`。
冻结三工具、baseline及R2clearance当前字节仍与最终receipt一致。
原首轮停止失败、初次审计工具错误、全部原预检与修正引用仍保留，没有覆盖成通过结果。

| 验证复用分工 | 本专项最终事实 |
| --- | --- |
| 本次实跑 | 最终148项只读source/test/config/快照/环境/日志/包/安装/组合结果身份审计；另保留R2预检、delta与固定输入专项原输出 |
| 按身份采信 | 上表新R2双全量/typing/build/双干净安装smoke及原resource04；本reviewer没有重跑这些产品操作 |
| 未覆盖 | 本专项不是完整产品/合同review、PM验收或main集成验证；未验证生产EDA、完整M1、外部body/U06、全部mandatory规则或baseline/terminal发布 |
| 补跑触发 | 源码/测试/config/依赖/输入或实际组合行为再变、冲突或identity不闭合；仅文档/证据补记不触发重复双全量 |

结论限于**本次最终工程证据及身份闭合**。完整独立review仍由主reviewer汇总其产品/合同/
资源探针，最终接收与实际集成归PM。本专项不自行验收、合main、改PM阶段/current-work或
启动下一任务。
