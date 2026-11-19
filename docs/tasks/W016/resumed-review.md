# W016 恢复实施独立 review（工程通过；提交交PM）

Reviewer `/root/w016_review` 未参与产品实施。恢复版本
`6ca7b16cff0f953f9e7eacc834f88ac28e70abb6`，工作区初始干净。
本轮依据 [PM资源决定](pm-resource-decision.md) 继续检查；纯 report/capture
已解释的 >2 倍表示开销不再阻塞扩包。旧 [检查点review](independent-review.md)
及原证据保持，不改写为完整实现通过。下文保留阶段调查记录，以本节当前结论及末尾最终证据表为准。

## 当前结论

代码、接口、四路旧兼容及最终工程证据review全部完成；全量实跑新增发现的R08/R09依赖边界问题与R10
相对root认证问题均已修正并独立复核，当前未关闭must为0。恢复阶段R03–R07均已修正并
独立复核；R06/R07由执行主动提出具体合同/实跑问题，review确认must后补独立实证。
当前completed冻结源码/测试/config共298文件，manifest
`f99498abc0877bb918d7de88d66a5eda5d5591d41f8ce8102b04edc14826c052`，
见[completed源身份审计](evidence/resumed-review/completed-source-audit.json)。

**独立工程review通过，A8已闭合：两解释器均unit/contracts 1953项 + fixture_support 3项
= 全部tests 1956项通过。** 独立核原exit、输出hash、完整节点集合及最终298文件身份，
没有重跑长矩阵或大wire。见[最终核对](evidence/resumed-review/final-matrix-audit-r2.stdout.json)。
本结论支持按用户授权提交原分支交PM，不代PM验收或合并授权。reviewer未参与产品实施，
未更改正式测试/fixture。

## Findings

| ID | 问题与独立依据 | 执行处理 / 独立复核 |
| --- | --- | --- |
| R03 | must（来源闭合）：`_CapturedFiles` 将 caller 提供的全部 aliases 直接预填 `files.paths`，full-byte replay 最终仍返回整张预填表。真实 candidate 输入新增从未请求的 `never-requested-role` alias 后，Receipt 认证成功且 ref 改变；这项 metadata 并非实际获取事实。尚未证明可借此跨角色读取不同内容，不扩大影响声明。 | 执行将 replay lookup 与实际访问记录分开；独立 `--require-closed` 实跑四反例全部拒绝，修后hash/输出见 alias-closure.after.stdout.json，关闭该finding。 |

[独立探针](evidence/resumed-review/alias_closure_probe.py) 与
[原输出/源码hash](evidence/resumed-review/alias-closure.initial.stdout.json)
保留实际文件认证反例；另外 wrong-GDS-role、missing-first-alias、relative actual path
均被拒绝，不能把这些正确拒绝也列为缺陷。

## 兼容基线准备

复用前轮 [normal-direct](evidence/review/baseline-normal-direct/report.json)
唯一已保存 DTO/wire 快照；没有重跑该基线。原 `/tmp` 数据已失效，按原准备脚本
恢复 `/tmp/w016-parity-inputs`，normal 全部41个文件hash与保存的 baseline 相同，
后续两个版本仍消费相同绝对 URI。旧 worktree 目录不存在但 Git 注册残留，首次
启动失败已保留；`git worktree add --force --detach` 恢复同一路径到
`efc881d461ce2c87370f6df402ac50ae43c094e8`，未覆盖现存工作目录。

已与执行协调串行开始 normal-readback 基线；后续 mismatch/wrong-body 及候选
仍按串行资源时隙安排。旧七阶段完整 encode/decode 与新 API build+report 不同口径，
不将其耗时直接套用新 API 预算。此处记录基线准备，不提前宣称双侧parity。


R04（must，公开错误边界）：独立内联调用 `AnalysisRequest(Path('/'))` 曾抛
`ValueError: acquisition requires explicit path, URI and error code`；同次 `/tmp`
路径正常返回 located rejected。执行已在 facade 拒绝空文件名。保存探针时修正已生效，
[during-fix输出](evidence/resumed-review/request-path.during-fix.stdout.json)
不冒称修前快照。[明确修后探针](evidence/resumed-review/request_path_probe.py)
`--require-located` 对根目录、目录、相对路径、不存在文件四项均返回 rejected，
[输出](evidence/resumed-review/request-path.after.stdout.json) 绑定源码hash，exit0。
该具体反例关闭；未知程序异常仍必须原样传播。


normal-readback 基线已完成（exit0）：W007–W014 complete DTO/wire/closed decode
全部相等；W006 attempt/checkpoint 保持 unsealed且无terminal。见
[报告](evidence/resumed-review/baseline-normal-readback-r2/report.json)。
W011 wire 136434909 bytes，W014 wire 60066004 bytes，process HWM711924 KiB。
这是基线准备，不是候选双侧parity，也不作为新API成本reference。

独立 [selected alias探针](evidence/resumed-review/selected_alias_probe.py) 对body与manual
各执行三次实际调用：未知绑定URI→含NUL的绑定URI→有效layout symlink。
前两项分别产生原Body/ManualSourceBindingMismatch和InvalidInputPath，均保留local；
有效symlink分别完成evaluated/declared，local receipt不因独立文件变化而变更，旧结果不变。
[3.12实跑输出](evidence/resumed-review/selected-alias.after-r2.stdout.json) 绑定源码hash，
exit0。此前系统Python缺pytest（只因输入helper导入）的启动失败未进入产品；原stderr保留，
没有记作产品失败。源码审查中指出的未捕获URI及discovery吞掉InvalidInputPath两类路径均已修正，
此探针复核了其实际边界。没有弱化未知程序异常传播。

R05（must，原错误定位丢失）：所选文档discovery将`load_document`的所有InputError
统一换成`/selected_bindings`位置，真实坏body `{` 的原line1/column2因此丢失，
duplicate-key同样失去原SourceRef。独立
[修前反例](evidence/resumed-review/selected-error-location.initial.stdout.json)
与[探针](evidence/resumed-review/selected_error_location_probe.py)已保留。
执行拆分load_document和每项URI解析的catch：前者保留原issue，后者定位实际绑定字段。
[修后输出](evidence/resumed-review/selected-error-location.after.stdout.json)
对两项完整EvidenceIssue equality通过，exit0；关闭该finding。

[复合诊断探针](evidence/resumed-review/diagnostic_priority_probe.py)另作两项独立实际文件组合：

- partial FIN + MP source NFIN8/observed7 + future geometry_window选择：顶层rejected，
  source_comparison=mismatch；PartialFinCrossing保留原unsupported category/code/ref，
  severity为error；future selector仍单列unsupported，不能覆盖本地错误。
- 独立M1区域query冲突 + MN0 D source VSS/observed Y：annotation与terminals均保留error
  诊断，已知D端mismatch仍使source_comparison=mismatch。

两项均exit0，[输出与源码hash](evidence/resumed-review/diagnostic-priority.stdout.json)。
输入helper只编写实际GDS/query/CDL bytes，不供应观测答案；独立断言取自手工指定的
源端子/计数差异与已定位的几何区域。

## 当前代码review结论与后续验证

已审本轮facade、纯normalization编排、独立选中证据获取/认证、manual封闭schema、
terminal operand提取、只读view/report及新增实际文件测试。旧完整wrapper继续要求原
NormalizationInput/AnnotationBinding/body capture，旧DTO/schema/wire未加optional旁路；
新body不加入annotation capture或本地union，新annotation绑定实际local receipt digest。
Domain未反向import parser。分析没有发布、隐式补料重试、target=source或公开receipt续算入口。

当前已识别must均有具体修后独立验证；尚未发现新的未关闭must。此为代码/反例阶段结论，
**候选兼容验证、冻结身份与最终工程证据尚未闭合，不是最终实现/PM验收结论**。

按执行确认的verification-reuse安排，新
[candidate_parity.py](evidence/resumed-review/candidate_parity.py) 对冻结候选完整构造DTO、
调用真实公开encode、与基线DTO/wire逐bytes精确比较，并验证基线报告/快照hash及输入身份。
每个基线已经完成decode/完整DTO roundtrip；候选不重复大decode，不落第二套完全相同gzip。
最终codec回归覆盖候选decoder及拒绝行为。此安排不省产品认证、不仅比较digest或测试数，
也不修改原历史parity脚本。基线normal-direct按原冻结来源复用，readback已新增完成；
mismatch/wrong-body及四条候选对照继续串行。

一次已记录调度重叠：启动mismatch基线后，执行通知同源A2探针已经启动约20秒；
双方随后不再另启重链。该轮仅用作正确性/compatibility，不作为资源benchmark；
资源六小case已另在专用时隙完成，不混用口径。


其余基线现均完成（exit0）：[extraction-mismatch](evidence/resumed-review/baseline-extraction-mismatch/report.json)
和 [body-enclosure](evidence/resumed-review/baseline-body-enclosure/report.json) 每阶段完整DTO、wire、
closed decode相等；wrong-body保留W014 `error/BodyTapEnclosureFailure`。
两者W014 wire分别为23448931和23450808 bytes，具体SHA256与所有阶段元数据见原报告。
四路基线覆盖完成，但此时仍不提前认定候选等价。

[独立冻结源审计](evidence/resumed-review/final-source-audit.json) 核对298个源码/测试/config文件，
全部匹配执行的final-source-identity manifest
`af23726d482621502c322ba207b610b49bf10881aaf856f55b208009e5d8bd50`。
候选对照将在执行完成同一冻结身份的新增API/A2和资源时隙后串行运行。


R06（must，manual逐字段来源未实现）：执行在最终矩阵前主动提出该合同核查，独立review
复核 `W015/entry-contract.md:137` 与 `W015/interface-examples.md:149`，后者明确要求
“原声明及@manual逐字段ref”。当前declared返回完整原doc，但evidence_refs仅根source.ref()；
根来源不等于显式author/created_at/scope字段和各assertion位置。建议保留原doc，补完整
声明字段SourceRef（cell/instance_hint作为声明scope，不伪造原文不存在的/scope字段），
并实际验证两条assertion、URI/hash/field、report与observed不受影响。此项尚待修复复核；
前述“当前无未关闭must”是该合同复核发现前的阶段记录，不能据其启动最终结论。


R06修后独立 [实际声明探针](evidence/resumed-review/manual_location_probe.py) 通过（exit0）：
两条B assertion的14个逐字段ref全部存在，所有refs的URI/hash均匹配该次真实manual capture；
report能展开这些位置。只改声明label再次调用，local receipt和完整terminals均不变，旧report
不变。[原输出](evidence/resumed-review/manual-location.after.stdout.json) 绑定所有产品源码hash。
执行保留原doc，新增根/对象/逐字段ref，未发明源文不存在的scope字段。R06关闭；该小修
发生在最终全矩阵之前，原af23726d冻结身份保留为历史，新交付身份须重新绑定后续验证。


R07（must，异常Unicode请求路径）：执行在冻结后、全量矩阵前实际发现
`Path('/tmp/\ud800.json')`抛UnicodeEncodeError。独立review认定request编码前提属于
预期输入边界，支持在facade窄捕获该编码错误、返回located InvalidAnalysisRequest。
[独立探针](evidence/resumed-review/request_unicode_probe.py)生成时修正已生效，initial输出
不是修前反例；修前事实以执行原实跑为据。[明确修后输出](evidence/resumed-review/request-unicode.after.stdout.json)
exit0：高/低surrogate均拒为InvalidAnalysisRequest并定位/manifest_path，合法中文路径仍进入
读取层返回MissingInput。代码仅catch UnicodeEncodeError，未知异常与interrupt未吞掉。
该finding关闭，待绑定下一冻结身份。

此时候选normal-direct已经在a306冻结上完整完成（98.94秒，exit0）；四路runner随后自动
启动readback约27秒，收到执行的新fix消息后明确TERM停止，保留exit-15和已有输出，
不记为产品失败或完整对照。mismatch/wrongbody尚未启动。后续使用新目录继续，
已完整normal结果仅在新旧链相关产品源严格不变的影响分析后采信；不把中断readback算通过。


## 最终验证闭合范围（原版本复用注明）

| 范围 | 本次实跑 / 采信依据 | 结论 |
| --- | --- | --- |
| R03–R05、selected独立资料、复合状态 | [delivery独立5探针命令及exit](evidence/resumed-review/delivery-probe-runs.json)，随后release只改新facade Unicode请求前提和对应测试；既有验证的路径均合法，所测认证/解析/计算模块逐字节不变 | 全部exit0，旧失败保留；不重跑无影响大链 |
| R06 manual逐字段来源 | [独立实际双声明](evidence/resumed-review/manual-location.after.stdout.json)，产品hash与delivery逐项相符；release仅请求前提变化 | 14个字段真实SourceRef，改声明不改local/terminal，关闭 |
| R07请求Unicode错误边界 | [明确修后输出](evidence/resumed-review/request-unicode.after.stdout.json)，facade hash与release完全一致 | 高/低surrogate typed拒绝，正常中文路径不被误拒，关闭 |
| A3 body类型与ambiguous | [独立两case](evidence/resumed-review/body-rule-cases.release.stdout.json)，[脚本](evidence/resumed-review/body_rule_cases_probe.py)与原空stderr | 实际新入口保留BodyTypeMismatch/BodyUniqueMatchFailure原code/hash/位置，local保留，顶层rejected |
| A4/A6缺seed、unmatched、层级边界 | [独立三case](evidence/resumed-review/local-boundary-cases.release.stdout.jsonl)，[脚本](evidence/resumed-review/local_boundary_cases_probe.py)与原空stderr | MissingDeviceSeed保留channel诊断、annotation独立与terminal依赖；100nm² unmatched和40nm² gap实际保留；完整SREF定位unsupported且local=None，没有flatten |
| A6旧兼容 | [四路精确比较汇总](evidence/resumed-review/parity-summary.json) | normal-direct/readback/FIN mismatch/wrong-body全部完整DTO与真实公开wire逐bytes相等；readback未seal、无terminal |
| A7资源 | completed三个真实timed报告及三个独立counted报告，均已核源码/输入/依赖/report hash | 约2.674/3.100/2.760秒、HWM低于30MiB；report/capture约5.56–5.74倍，仅按PM决定记录 |
| A8 typing/build/install/定向 | [最终独立原输出及实际安装/产物核对](evidence/resumed-review/final-matrix-audit-r2.stdout.json) | completed同一冻结双75模块typing、双build、双clean源码外五case smoke及定向均通过；reviewer没有冒称重跑 |
| A8双全量 | completed 3.12/3.10各1953 passed，另各3项fixture_support passed，精确覆盖全部tests 1956节点；原两轮AST失败/中断仍保留 | 最终均exit0、原输出hash及298源身份相符；A8闭合，不把历史失败删除或计作通过 |

兼容的精确口径是原W007/W008/W009/W010/W011/W013/W014完整DTO/ref及公开wire，
基线都取`efc881d461ce2c87370f6df402ac50ae43c094e8`同绝对输入URI。基线完整decode已成功；
候选完整构造与公开encode后和保存基线逐bytes比较，没有只比较摘要、改golden或跳认证。
normal-direct在delivery完成，release与其仅两个不进入旧链的文件不同，复用依据逐项记录；
其余三路在release实跑并前后验证整个298文件集合不变。

依执行确认的封包策略，四路成功后将本轮新三路44个gzip（22305592压缩bytes）移到
`/tmp/w016-parity-archive`临时保管，Git仅保留原报告/日志/来源输入身份/脚本和本次成功比较证据；
[移动映射与压缩hash](evidence/resumed-review/baseline-archive.json)保留。历史已提交的
normal-direct唯一快照不动，候选从未复制第二套gzip。临时archive不是未来可直接采信的
持久证据；若不可用，须从原提交、`prepare_parity_inputs.py`与原绝对URI重建基线，再实际
逐bytes比较。原报告内snapshot路径是当时真实比较路径，不宣称归档后Git仍含这些大wire。

全部输入与结论仍限synthetic flat-cell；真实PDK/生产方言/EDA运行/隔离目标环境未验证。
首包parent/global与完整source证明仍未知，completed不表示完整验证通过或发布权限。


## R08：原有依赖边界失败（全量实跑发现）

执行的release Python3.12全量运行出现两个AST测试失败，随后显式SIGINT暂停，原日志保留：
[pytest-312.stdout.txt](evidence/resumed/release/pytest-312.stdout.txt)。独立已阅读真实traceback，
两项分别是`test_importer_and_domain_dependency_direction`和
`test_precontext_module_dependency_boundaries`，共同指出domain/analysis.py import pathlib。
日志为2 failed、488 passed、181.86秒，含KeyboardInterrupt，不是完整矩阵成功；不能按不同
collect顺序猜测成W008失败。该硬边界在此前独立静态review中漏检，review对此明确更正。

R08为must。建议执行将唯一公开入口的frozen `AnalysisRequest(manifest_path: Path)`定义
移到facade `layauto_v2.analysis`，domain移除pathlib与请求类，只保留无IO依赖的Evidence/view；
不能放宽既有边界测试。公开导入路径仍为合同要求的`layauto_v2.analysis.AnalysisRequest`。
当前等待执行修正后的两项原AST测试与实际入口复核；最终全量须在新冻结身份重新开始。
此前四路旧DTO/wire精确比较可否采信，须按新旧产品源差异和旧链实际依赖逐项说明。


R08修后独立执行两项未修改的原AST测试：2 passed / 0.23秒，exit0，见
[原stdout](evidence/resumed-review/dependency-boundary.after.stdout.txt)。独立
[request_owner_probe.py](evidence/resumed-review/request_owner_probe.py)从真实临时manifest调用：
公开类owner为layauto_v2.analysis、请求保持frozen，domain无Request；no-body请求completed、
8端子全部保留，source比较indeterminate；surrogate请求仍typed定位拒绝。
[原输出及完整产品hash](evidence/resumed-review/request-owner.after.stdout.json)通过，R08关闭。
未修改既有边界测试，未回避原全量失败；新冻结的最终双矩阵仍须完整执行。


R08修后新冻结：[verified-source-identity](evidence/resumed/verified-source-identity.json)，
SHA `73cb080765e2e317f2f54269f8cd306ed5e352c8c21dd2ae575f8920db54fa7b`。
独立[298文件核对](evidence/resumed-review/verified-source-audit.json)无差异，R08实际入口探针
所有产品hash与其逐项相等；相对release仅新facade和新domain.analysis请求定义迁移。
旧链并不import这两个新增模块，旧producer/wrapper/codec及输入全部未改，因此采信此前
四路实际逐bytes结果；不把两个版本的manifest混为同一个源码身份，也不重跑旧大wire。
原两个AST测试未修改，独立[测试命令/源hash/原输出hash](evidence/resumed-review/dependency-boundary.after.json)已保留。
最终双全量将从新冻结重启，`--maxfail=1`仅在失败时提前停；只有新冻结正式范围的全部实际收集项通过才能计该版完成；此处先前1954项是范围未对齐的估算，已更正。


## R09/R10：纯计算接口登记与捕获root校验

verified Python3.12全量于原W007依赖测试failfast停止：1 failed、571 passed、296.93秒，
[真实stdout](evidence/resumed/verified/pytest-312.stdout.txt)及[原meta](evidence/resumed/verified/pytest-312.json)
完整保留。13项违规来自新normalization文件中的Path以及未登记的纯parser重放/中立state依赖。
独立review此前未把W007覆盖所有normalization文件的窄allowlist逐项对齐，现明确补正。

R09处理经独立审核：normalization移除全部Path依赖；捕获路径adapter移到importer，
`captured_analysis_files(root, aliases)`仅词法构造Path和查捕获lookup，禁止resolve/访问磁盘。
Receipt仍完整逐请求供给原bytes并重parse认证。原W007测试按W008–W013同类模式，仅为
两个W016新文件、绝对ImportFrom、精确module+symbol登记现有纯parse/文档验证与不可变
neutral draft组合；原forbidden、旧模块例外和mutable state/publication禁令均未放宽。
这属于已采纳W015的纯reparse/core组合接口登记，不是任意豁免新文件。

独立执行原W005/W006/W007/W008/W010/W011/W013/W014边界、W006 unit依赖检查及新增
静态/实际纯度检查，11 passed / 4.59秒，exit0，见[原stdout](evidence/resumed-review/all-dependency-boundaries.r09.stdout.txt)。
另作[实际capture无IO探针](evidence/resumed-review/captured_replay_noio_probe.py)：先从真实文件
获取local+body+manual，再同时封锁builtins/io/os.open、stat/lstat/readlink/listdir/scandir及
Path读写/resolve/exists等20个文件系统调用，真实Receipt full-byte重放、local、body evaluated、
manual declared及8端子仍全部完成。unused alias、角色互换、缺alias也均拒绝，证明搬移
没有重新引入R03的lookup/visited混淆。[原输出及全产品hash](evidence/resumed-review/captured-replay-noio.r09-r10.stdout.json)
通过，R09关闭。

R10由执行实际反例发现：只将evidence.root改为相对字符串，原Receipt接受；
[修前原输出](evidence/resumed/alias-absolute.initial.json)中relative_raw_alias本已拒绝，
不把该正确拒绝扩大为漏洞。新factory显式要求root/actual alias path为native绝对字符串，
用词法is_absolute检查，不触FS。上述独立无IO探针同时验证relative_root拒绝，并将relative
raw alias作为正常拒伪对照，R10关闭。此更改发生在下一冻结前，没有抹除两轮真实全量失败。

下一双全量须在新冻结身份重新执行；旧四路DTO/wire是否采信将继续按精确源差异说明，
不把修改后的AST测试与此前测试身份混为同一集合。


R09/R10最终绑定completed冻结：`f99498abc0877bb918d7de88d66a5eda5d5591d41f8ce8102b04edc14826c052`。
独立[源审计](evidence/resumed-review/completed-source-audit.json)核298文件无差异；上述无IO探针
全部产品hash与此冻结一致。为避免把R10补丁前后边界运行混绑，已在新冻结重新只跑全部
10个AST边界测试文件对应检查，10 passed / 0.66秒，exit0；
[原stdout](evidence/resumed-review/all-dependency-boundaries.completed.stdout.txt)与空stderr已保存。
此前11项包括一个实际acquisition/compute纯度case，本轮静态刷新不含它；实际无IO探针独立
具有同一产品身份，不能把10/11混写成测试漏失或重复全链。

相对verified恰三个W016新增分析模块及两个测试变化，旧producer/wrapper/codec、固定
parity输入均不变，四路真实逐bytes比较继续按相关源身份采信，不反复编码大wire。
新正式测试增加三个case，最终完整矩阵总数以completed冻结实际collection为准；之前
1954/1957均是尚未对齐收集范围的估算，不能作任何冻结轮的实跑完成数。当前R09/R10均关闭、must0。


## completed工程证据先行核对（长矩阵完成前的阶段记录）

独立[核对脚本](evidence/resumed-review/engineering_evidence_audit.py)只读现成日志、源码、
安装文件及构建产物，没有重新运行产品测试或旧wire。正式
[成功输出](evidence/resumed-review/engineering-evidence.completed-r2.stdout.json) exit0，空stderr。
首轮audit漏将py.typed计入runtime而自触断言，原stderr保留；修正为120个.py与1个py.typed，
第二轮核对成功，此为review脚本选择错误，非产品/安装失败。

- f994冻结298文件当前全部匹配；双环境3.10.22/3.12.14及各自依赖版本与原环境记录一致。
- 双clean安装目录均在源码树外；各121个runtime实际文件逐bytes匹配冻结源码。
  双wheel和sdist的长度/hash及内部runtime内容全部核对相符，安装依赖也与记录一致。
- 已完成的定向、双75模块typing、双build及双安装smoke共7份执行报告均exit0，
  原stdout/stderr hash匹配f994源身份；双smoke从/tmp以-I运行no_body/body/mismatch/
  bad_body/manual五条真实文件路径，输入和实际脚本hash也已核对。
- 三个timed与三个独立counted报告具有相同case输入、产品/test源码与report hash；
  获取+认证使GDS/CDL/query各parse两次，neutral channel/annotation/terminals各一次，
  body仅选择时一次。timed约2.674/3.100/2.760秒，HWM均不足30MiB；report分别
  235792/259620/235838 bytes，report/capture比例仍按PM决定记录，不删完整诊断。

完整范围已从原收集输出逐node核对：两解释器`tests`目录的1956个ordered node完全相同，
均无重复。长矩阵的unit/contracts 1953项是其子集，差集恰为
`tests/fixture_support/test_w004_body.py`中的三个实际测试，二者不重叠；因此同一冻结下
每解释器分别跑1953+3，足以闭合全部tests，无须中断或重跑1953。集合与原collection hash
见[scope记录](evidence/resumed/completed/collection-scope.json)和独立audit输出。
补充三项尚未执行成功前不能记完整1956通过，collection相等也不代替执行。

此前1954/1957估算混用了范围。根默认collect还会拾取
[W011历史gate demo](../W011/preflight/gate-demo01/test_w011_gate_fixture.py)，其首句明确
“Engineering guard probe only, outside official source/test snapshot”，依赖专用必填
`--w011-resource-lock/log`插件选项。它在docs工程实验中，不属于本次正式tests矩阵；
不为凑根默认1957而修改配置、伪造其通过或扩展本轮产品范围。最后以两侧原执行exit、
1953 passed及补充3 passed、source/环境/输出hash闭合A8。


## 最终工程结论（双矩阵完成后）

独立[最终审计脚本](evidence/resumed-review/final_matrix_audit.py)只读取原执行结果、集合与
实际源码/环境/安装/产物，未调用pytest或产品链；[成功输出](evidence/resumed-review/final-matrix-audit-r2.stdout.json)
exit0，stderr为空。冻结298文件逐hash仍全部匹配f994，先前双环境、构建、安装、
真实输入smoke及六个资源报告的身份/原输出也重新核对一致。

| 解释器 | unit/contracts长矩阵 | fixture_support补充 | 完整正式范围 |
| --- | --- | --- | --- |
| Python3.12.14 | 1953 passed，7745.36秒；driver7747.786188836秒；exit0 | 3 passed，exit0 | 1956个tests节点完整通过 |
| Python3.10.22 | 1953 passed，10798.06秒；driver10801.143035027999秒；exit0 | 3 passed，exit0 | 1956个tests节点完整通过 |

两长矩阵stdout SHA分别为
`0c8035cdb172da372281b5e707753f3d2232fe70c91fc2086e07c74a7db277d9`与
`90ced411653911d7687fe52498be75524e5730175a840944abde1a972912a464`；
四个执行stderr均为空。命令、时间、原meta/hash、补充节点与双方环境均见最终审计。
补充输出中的subtests是三个节点内部断言，不另加进1956。首轮review汇总解析器未允许
“3 passed, 8 subtests passed”后缀而自触断言，原输出保留；只修review解析器后r2通过，
未重跑或改写任何产品测试结果。

R01/R02历史闭合和R03–R10修后独立验证均保留，当前must0。已说明的早期原失败、
后续相关源验证复用、旧大wire临时归档限制均不变；没有将元数据hash冒称新一次逐bytes比较。
工程review通过，A8完成，可按用户授权提交推送原W016分支交PM；不自行PM验收、合main、
变更current-work或开启下一任务。真实PDK/生产方言/EDA及隔离目标环境仍未覆盖。
