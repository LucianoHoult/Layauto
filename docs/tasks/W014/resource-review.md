# W014 独立资源与采信核验

Reviewer `/root/plan_review`，未参与产品实现或资源工具编写。
本文件核资源证据、跨身份采信及矩阵调度，不代替最终产品review或PM验收。

**最新结论：** 资源门和最终工程证据核验均已通过。最终新冻结source c7769fcb…
已实际完成双1889、双typing65、build及双clean安装源码外三路smoke，
独立[840项工程审计](review-evidence/final_engineering_audit.stdout.json)闭合
[最终receipt](verification/receipt.json)；产品review见[独立代码结论](code-review.md)，
不代PM验收。原clearance和R2/R3/R4证据保持原时点，不因最终完成改写原pending。

资源采信链保持：R4 measured998aa805…的最终原样本选择独立598项通过；
严格test-only delta到c7769fcb…由301项独立核验支持，85采信+80实际闭合开发
165范围；冻结66f5b1e…的300项核验放行原clearance。R3的554项原核验保留
2d46…身份，不冒称新guard成本。

## 最终资源门结论

**资源门通过**，绑定source_id
`c7769fcbfb0312b93e4d44628c77ff21e273698a537eaba0e1454734b049d364`、
冻结提交`66f5b1e5369549ed8df361f89f099acfd2f39e17`，三个固定case均闭合，
`parallel_matrices_safe=true`。最终receipt见[clearance](resource-clearance.json)，
SHA-256=`b9c699e9d2284fbc40a32641c98a89f4293e9c244ee50f203f5298f0153a2222`。

独立[resource_freeze_audit.py](review-evidence/resource_freeze_audit.py)实际300项
只读核对通过，见[原输出](review-evidence/resource_freeze_audit.stdout.json)。
核完整286 selected live及Git archive字节与冻结清单相同；R4→冻结仍严格仅
已独立审过的测试else分支变化，runtime/config/input/probe不变。remaining-r7
原命令returncode0、source前后c7769fcb…不变、原stdout/stderr hash闭合，实际
80 passed/644.58秒，nodeids正好覆盖审定的80项后缀；与85项采信前缀无交叠，
165新增/受影响范围闭合。原targeted-r6的85passed/1failed完整保留。

原资源门允许两个解释器矩阵并行、各自pytest串行，build和双clean安装/源码外
三路smoke随后串行；实际最终21命令的时间排序与原门条件一致。双1889/
typing/build/安装原证据现已由840项独立工程审计通过，最终产品review见上链。
本资源调度结论与工程通过均不代PM验收或生产准入。原clearance JSON中“最终
工程待办”保留其放行前时点事实与原SHA，没有改写受测工具所消费的receipt。

R4调度披露：恢复消息交错导致reviewer原metadata after（实际6.30秒）与R4
direct短时重叠。direct原命令开始于08:54:14.986 UTC，after stdout最后写入
08:54:27.396 UTC；没有精确进程开始receipt，不把按elapsed倒推当作精确边界。
原direct结果/命令保持，其正确性与source identity仍可核；最终清洁耗时样本
已单独补一次direct，readback/mismatch无reviewer产品probe。最终采样选择
引用三条各自实际原路径/hash，不复制或重标成另一个同源suite。

## R4 最终原样本选择（有效实测身份，保留当时核验记录）

以下保留最终source冻结前的核验与当时pending；当前门和工程结论见上文。

独立[resource_r4_audit.py](review-evidence/resource_r4_audit.py)实际598项只读核对
通过，见[原输出](review-evidence/resource_r4_audit.stdout.json)。核最终选择owner
及nested采信owner全hash、全部引用原证据、六条W013/W014成功命令与原logs、
286个selected live字节、完整原失败snapshot、106个非W014 runtime实际字节、
精确source delta、输入/完整W010 wire/解释器/依赖/probe及认证1/1/2。原W013
reference仍保持803b4c4f…，当前实测998aa805…；没有把early失败采为通过。

| 最终路径 | 原样本owner | W014公开三阶段秒 | 对W013比 | 新增wire字节 | 峰值MiB |
| --- | --- | ---: | ---: | ---: | ---: |
| direct | resources-r4-direct-clean/w014-normal-direct.json | 61.894 | 1.1329 | 345944 | 196.40 |
| readback | resources-r4/w014-normal-readback.json | 114.963 | 1.0311 | 345944 | 491.91 |
| extraction mismatch | resources-r4/w014-extraction-mismatch.json | 61.919 | 1.0931 | 344703 | 204.29 |

详细原路径/hash见[final-selection](resource-adoption-r4/final-selection.json)，
不把混合选择伪称新suite。clean direct wrapper多一个MYPY_CACHE_DIR覆盖项，
已独立核runtime源无该变量引用、实际命令不运行mypy；其它相关overrides、
解释器/依赖/probe/输入均相同，未虚称所有环境字面相等。R3→R4及clean direct
validwire SHA/bytes/compact、W010认证与neutral builder次数全部相同；新metadata
验证实际包含在公开build/encode/decode成本里，单样本差异不是独立helper计时。

本身份资源检查通过，无资源must。最高491.91MiB、相同16GiB/4CPU及原W013
双1731成功矩阵支持两个解释器并行、各自pytest串行；build/install/smoke随后
串行，期间无其它重链。两份最高样本加2GiB为2.961GiB，只是调度依据，不是
全矩阵或最大输入上界。最终clearance仍须绑定165项通过后的冻结身份；资源
检查通过不代替最终产品review与PM验收。

## R7 测试单点修正与资源采信

本节保留修正后、80项完成前的采信依据；80实际通过及最终工程结论见上文。

targeted-r6原失败、完整source snapshot和原stdout/stderr保留：85passed/1failed，
测试在触及新validator前误读不存在的ChannelSeed.source。候选c7769fcb…相对
R4实测998aa805…严格仅test_w014_contracts.py一个else分支变化，改从真实坐标
operand构造SourceRef，channel/net分别缺失各自raw device_info/net_shapes来源。
不涉及runtime/config/input/probe，不触发R4资源重跑。

独立[candidate_r7_identity_audit.py](review-evidence/candidate_r7_identity_audit.py)
实际301项只读核对通过，见[原输出](review-evidence/candidate_r7_identity_audit.stdout.json)
及[完整精确补丁](review-evidence/candidate_r7_test_only.patch)。核原失败snapshot
全部字节及现候选全部live字节、AST其它测试/fixture/import和未改分支、原命令/
logs、1889 collection与实际165项选择顺序。实际失败是index85的channel用例；
前85恰为56unit+11scope+18codec，修正仅影响后缀channel/net两分支。85前缀按
明确依赖/分支身份采信，剩余80必须实跑；不能将85/1整次失败改写为165成功。
最终双解释器全量仍须在新候选冻结源执行，不因测试单点修正而省略。

**历史恢复点（R2→R3）：** contracts-r4发现CR-10/11公开codec保留字段验证问题，相关
候选未通过定向验证。下面R2身份/成本核验仍作为历史证据成立，但新的codec
修正改变正常encode检查成本，不能把本报告的R2判断直接改标给新runtime。
需完成计划中的W014资源R3及独立复核后，才能为新冻结source落clearance；
旧W013 reference仍按未变依赖/输入/probe身份采信。此时没有最终clearance。

## R3 修后独立复核（历史资源身份，已由R4接替）

新codec CR-10/11修正后，W014三路在source
`2d46bbdaccd858af936d37427ec8bad11d0bb11074d92cddb901da6197ecf639`
重新实跑完成。独立 [resource_r3_audit.py](review-evidence/resource_r3_audit.py)
实际554项只读核对通过，见 [原输出](review-evidence/resource_r3_audit.stdout.json)。
三条新原命令exit0、原logs、source全清单、probe/依赖/输入、106旧runtime字节、
公开完整roundtrip及W010认证1/1/2均闭合。原W013 reference仍保留803b4c4f…原身份，
没有把early失败或不同source冒充本次通过。

| R3路径 | 含新retained检查的build+encode+decode秒 | 对W013比 | 新增wire字节 | 峰值MiB |
| --- | ---: | ---: | ---: | ---: |
| direct | 58.315 | 1.0674 | 345944 | 198.51 |
| readback | 116.748 | 1.0471 | 345944 | 481.28 |
| extraction mismatch | 59.506 | 1.0505 | 344703 | 200.20 |

另直接逐字段核R2→R3三路valid wire SHA/bytes、compact bytes、完整W010 wire、
neutral builder计数及输入全部相同。新完整retained验证包含在实际公开成本中，
没有单独对该helper计时，不能将单样本变快称为检查负成本或性能优化。
[R3工程报告](resource-adoption-r3/README.md)和
[R2/R3比较](resource-adoption-r3/r2-r3-comparison.md)与原数据一致。
R3 README原“R2 suite”模板标签已由owner更正，并保留更正前文件及manifest。

本身份资源检查通过，无资源must。结合相同16GiB/4CPU的原双全量与新最高
481.28MiB，继续支持两个解释器矩阵各自串行、彼此并行，后续build/install/smoke
串行且不重叠其它重链。样本乘二加2GiB约2.94GiB仍不是完整矩阵内存上界。
此时contracts-r5的82项定向尚在执行，尚未落clearance；后续CR12及R4见上文。
历史资源通过不冒充最终产品或PM验收通过。

## 资源身份与实跑

独立脚本 [resource_final_audit.py](review-evidence/resource_final_audit.py) 实际完成
528项只读核对，见 [原输出](review-evidence/resource_final_audit.stdout.json)。
未运行新的产品捕获/编码/资源benchmark，不复制大wire或安装树。

- 原W013三条成功reference保持source_id
  `803b4c4f444f6c32f68966799d25fe8dffad31a914138633b0ed383eaa102bce`。
  early attempt中的W014 readback失败、未运行的mismatch不采信为通过。
- W014 R2三条实际build/encode/decode成功保持source_id
  `d75b1b03b90e1eb010806a689a828fdcdeb715fdc20eb493a5bfd2219ae7f8a9`。
- 当前候选`8ef803c96ed693a1f97843fa5dede942151e76c326a9b5cd29f7b92a3377048d`
  与R2严格只有两个W014 tests的字节差异，全部runtime/config/input相同。
  [精确补丁](review-evidence/final_test_only_delta.r4.patch)以旧R2 hash重构证明：
  增加两项decode拒绝断言、local异型body overlap真实变体，并纠正gate测试的
  W009实际拒绝阶段。test文件不在资源probe调用图内，不触发资源重跑。

独立核34份采信证据的hash/大小、6条成功原命令exit0及stdout/stderr、逐路完整
source manifests、原失败快照全部文件hash、106个非W014 runtime实际字节、
解释器/依赖/环境、probe/identity tool、captured输入及完整W010 wire hash。
由此支持[工程采信报告](resource-adoption/README.md)的跨source结论；没有把两套
不同source改标成一个同源suite。新的W014 guard/codec不被W013 builder调用；
本次差异不改变reference所执行的旧依赖，换身份本身不要求重复三路reference。

## 成本与限制

| 路径 | W013→W014 build+encode+decode秒 | 耗时比 | 新增wire字节 | W014峰值MiB |
| --- | ---: | ---: | ---: | ---: |
| direct | 54.633→59.218 | 1.0839 | 345944 | 198.72 |
| readback | 111.496→125.142 | 1.1224 | 345944 | 507.12 |
| extraction mismatch | 56.645→64.423 | 1.1373 | 344703 | 198.57 |

所有路径公开完整roundtrip相等，W010认证调用计数分别为build1/encode1/decode2，
每phase W011 neutral/W013 neutral/body各一次。W014完整包保留一份旧W010
Value加compact输出，没有新增两份完整W011/W013 Result。

增量是已授权新关系/FIN/body派生的实际成本；wire增长约0.58%–1.50%，峰值与
reference相当。本次受限synthetic路径没有出现内存或序列化规模的显著放大，
资源上没有阻止最终矩阵的未解决问题。单样本耗时不是稳定性能统计或生产保证，
不能以此声称优化、最大输入可用或真实PDK准入。

## 双矩阵调度判断

支持最终`matrix_workers=2`：当前cgroup为16GiB、4CPU，与已成功完成双1731全量
的W013 R2限制相同；新三路最高HWM约507MiB，两份最高样本加2GiB保留量约
2.99GiB。旧106个runtime及其广泛测试工作负载没有改变；新路径峰值未放大。
这是结合历史全量与本次实测的调度判断，不能只把样本HWM乘二当作全量上界。

每个解释器中的pytest继续串行；build、双clean安装及三路smoke在双矩阵后串行。
双矩阵期间不再重叠另一个capture/codec/resource重链。实际矩阵日志及资源情况
仍须保存；失败按实际原因处理，不把空CI状态或调度许可记成产品通过。

最终clearance须在定向回归成功、最终source冻结后落到该精确source_id；当前
定向contracts-r4仍执行中，本报告不会提前宣称它通过。最终产品review继续等待
指定双全量/typing/build/双源码外安装smoke和完整身份回执。

补跑触发：实际runtime/input/probe/deps变更、原证据失败或不可闭合、相关调用图
改变或独立发现新风险时核受影响范围；仅文档/证据补记及不参与workload的test
delta按精确身份采信，不重做同一大wire或三路封包。
