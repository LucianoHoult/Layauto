# PM-01 独立复核（修复与修后A8通过）

Reviewer `/root/w016_review` 未参与本轮产品或正式测试补修。依据
[PM决定](../pm-delivery-review/decision.md)、W015结果合同及architecture只读分析边界，
独立审查起点 `c9081f1a11612450e7228840e541452a6d7f9c89` 上的实际工作区diff。
仅写本目录的review和小型证据，未修改产品、正式测试或PM段。

PM-01所述组合反例已修复，修后冻结双版本A8及资源证据已独立核完，当前无未关闭must。
工程结论为通过，可交PM复核；本review不代PM验收或准许合并。

## 本次独立实跑

经唯一公开入口 `analyze_cell(AnalysisRequest)`，从真实临时文件构造以下10组输入。
每组按实际内容重绑header，输入helper只复制/编写输入bytes，不供应观测答案。
命令、298文件源码/测试/config身份、解释器依赖及原输出hash见
[meta](independent-probe.meta.json)；[脚本](independent_probe.py)、
[原stdout](independent-probe.stdout.jsonl)、[空stderr](independent-probe.stderr.txt)均保留，exit0。

| 输入 | 公开结果 | 独立检查 |
| --- | --- | --- |
| 正常无body | completed | FIN5/7、六D/G/S equal、两B indeterminate、parent unknown |
| 端口数单错 | rejected | SourceTopIdentityMismatch仅一次，原iXref URI/hash/line8 |
| drawn comparator单错 | unsupported | UnsupportedGeometryComparator原来源 |
| drawn comparator + 端口错 | rejected | 两个完整finding分别等于单项控制，包括原SourceRef和message |
| effective歧义gate stripe单错 | unsupported | 实际新增POLY bytes产生AmbiguousGateStripe |
| effective歧义gate stripe + 端口错 | rejected | 两项原finding保留，已完成drawn值仍存在 |
| local_graph contact operator单错 | unsupported | UnsupportedLocalContactOperator原来源 |
| local_graph contact operator + 端口错 | rejected | 两项原finding保留，drawn/effective值仍存在 |
| NF=2来源准入单错 | unsupported | UnsupportedFingerCount保留CDL原参数来源 |
| NF=2 + drawn comparator | unsupported | 两项unsupported均保留，没有误升rejected或丢来源 |

所有组合保留已解析source中的实际3/4端口及两器件。几何失败之后，尚未执行的
channel_fin/annotation仍为not_evaluated、value=None，依赖为local_graph/source_identity，
同时保留已知的来源前置问题；terminals仍有channel_fin/annotation依赖。单项与组合之间
逐完整finding等值检查，强于只对code或URI作断言。各条finding的SHA另与该组实际文件核对。
顶层同一个来源问题仅出现一次；后续调用没有改写先前返回结果或report。

## 实际diff与共享路径

`normalization/analysis.py`原先在source准入/identity检查后，drawn、effective或local_graph
任一预期错误都会走同一个except提前返回，遗漏尚未挂入facet的semantic_issues。
修正以`dataclasses.replace`给两个依赖该来源的未执行facet附加原issue元组，没有改变
其status/value/dependencies，也未为收集更多错误越过几何依赖。所有facet字典均为本次调用
局部对象；replace生成新冻结facet，不原地修改旧facet。未知程序异常的传播范围未变。

`analysis.py`对本地facet聚合后的完整AnalysisFinding去重。key包括category/code、完整
SourceRef、affected_refs、severity、message，不是按code粗粒度合并；相同code但不同位置
或不同消息仍是不同诊断，首个出现顺序保持。来源单错原来在两个消费facet各列一次，
现在顶层摘要仅一次；各facet的原问题仍分别可见。unsupported+unsupported控制组证明
本修复没有仅通过强行调整顶层优先级掩盖信息丢失。

本轮产品diff仅涉及这两个新分析模块；正式测试增加实际文件控制/组合覆盖。旧read_inputs、
W006及W007–W014 producer/wrapper/codec未修改，未改旧DTO/schema/wire，也未调整
原PM复现材料。几何共享except的三个入口已由独立实际文件覆盖。

## 采信与限制

- 执行的8项定向结果可作为补充证据，本review结论主要依据上述独立10组公开调用和实际diff。
- 旧四路DTO/wire的实际逐bytes结果可按未变旧生产者/codec及固定输入身份采信，不为本次
  新API诊断修正再次跑大wire；这不是声称本轮重新做了旧接口比较。
- 本轮改变公开诊断汇总与组合错误report，原资源结果仅是原版本记录。修后测量或按影响
  复用应明确其版本/输入/范围，不能把旧计时写成新实跑。
- 按PM决定，在修后完整冻结上重新执行A8双版本工程验证；原输出/hash/范围现已独立
  核完，见下文。旧f994矩阵仍是历史证据，未冒作本轮修后矩阵。
- 真实生产PDK/方言、EDA及隔离目标环境、父级/global证明仍未覆盖；completed不表示完整
  LVS/提取匹配或修改许可。

## 修后冻结与工程先行核对

修后冻结清单为[frozen.json](frozen.json)，298文件，SHA
`ecbc677c16f839ff294ce2a79296479f630c58d5dc5ef65713096daed8fdbb02`。
独立十组公开探针的完整源码/测试/config身份与其逐项一致。独立
[工程审计脚本](independent_engineering_audit.py)只读取原证据、实际安装文件及构建载荷，
不调用产品测试、collection或旧wire；[先行核对输出](independent-preflight-r3.stdout.json)
exit0，空stderr。

已核两版75源mypy、build、clean install及源码外五个原代表case加PM组合case的十份
原命令/退出状态/输出hash；各121个实际安装runtime文件、wheel/sdist内容逐bytes匹配
本冻结。源检查按原命令从仓库运行的有效环境核对（其中layauto元数据来自本地egg-info），
安装检查按源码外-I环境核对，两侧依赖及解释器均与记录一致。早期review审计脚本误读
环境字段名、误以-I匹配非-I源环境的两次失败日志保留，仅修审计方法，不是产品失败。

[reuse.json](reuse.json)记录的原PM材料及四路parity报告hash已独立核对未变；
旧冻结至本轮恰为上述三个文件差异。两侧[collection](collection.json)均直接收集tests目录，
各1961节点（unit352、contracts1606、fixture_support3），有相同ordered-node摘要。
此处采信原collection命令的摘要记录，不冒称重新收集了节点；最终已核完整tests执行命令
及同数量全部通过。先行核对后的两长矩阵和四case timed/count均已完成，最终结论如下。


## 最终A8与资源核对

[最终只读审计输出](independent-final.stdout.json)通过，stderr为空；命令、审计脚本及输出hash
另记于[独立补充核对](independent-same-root-audit.json)。共20份原工程命令的exit均为0，
逐项核对原stdout/stderr hash、同一ecbc冻结身份、实际环境和安装载荷；当前完整源码/测试/
config目录仍与298文件清单一致。等待器已正常退出，没有为review重跑产品或长矩阵。

| 项目 | 修后实跑及独立核对 |
| --- | --- |
| Python 3.12完整tests/ | 1961 passed，另8 subtests passed；pytest 10116.73s，driver 10119.243s，exit0 |
| Python 3.10完整tests/ | 1961 passed，另8 subtests passed；pytest 15694.18s，driver 15697.835s，exit0 |
| typing | 两版各75源通过 |
| build/install | 两版wheel/sdist成功；各121实际runtime文件逐bytes与冻结匹配 |
| 源码外安装调用 | 两版各五个原case及PM组合case通过；实际导入clean安装目录 |
| A7及组合成本 | 四组未profile计时与独立构造计数均exit0，输入及report摘要成对相等 |

两长矩阵均直接执行`python -m pytest tests -q -p no:cacheprovider --maxfail=1`，没有筛选或
提前失败；1961不同节点涵盖unit352、contracts1606、fixture_support3。8 subtests是节点内
子断言，不额外计作1961以外的产品测试节点。没有沿用前轮1953+3或旧估算1954/1957。
3.12原stdout SHA为`fd5124aa874cfe629bf9e2fd3fd4dd5dd630ac2def580a639fb22c19f71b29d5`，
3.10为`63b3b10b9b47dd434fc65c51e8456a55d1891d54e2fb12b57825fe3fabf0e4cd`；双stderr为空。

| 实际公开调用 | 未profile墙钟秒 | 进程累计HWM KiB | capture bytes | 完整未压缩report bytes | report/capture |
| --- | ---: | ---: | ---: | ---: | ---: |
| 无body正常 | 4.0835 | 31112 | 42395 | 235792 | 5.5618 |
| 有body正常 | 4.2548 | 30892 | 45202 | 259620 | 5.7436 |
| 无body FIN mismatch | 3.6882 | 31204 | 42395 | 235838 | 5.5629 |
| PM-01端口错+不支持comparator | 0.8738 | 26740 | 41640 | 21528 | 0.5170 |

计时与计数是不同调用，全部在两长矩阵结束后串行执行。四组GDS/CDL/query均各解析2次
（获取和认证重放）；三正常路径的channel、annotation、terminal中立构造各1次，body仅
选中时评估1次。组合路径的source admission为1次，没有进入layout/channel/annotation/
terminal构造，仍保留两个原finding。计数调用的开销未冒作上述未profile时间，HWM也未
冒作report增量内存。均低于120秒/1GiB触发值；report倍率按
[PM资源决定](../pm-resource-decision.md)记录，不将已解释的表示开销再当作未解决must。
本补修未改报告encoder或引入每facet完整Result/capture复制；这些小样本不证明生产规模上限。

## 同路径报告补充与结论边界

旧资源探针与本轮使用不同绝对root，receipt绑定的root/aliases参与报告，故输入文件bytes
相同不必有相同report hash。保留该差异，没有直接把不同root摘要不等判作产品回归。
执行补充[same-root比较](same-root-reports.stdout.txt)在同一绝对输入路径下分别载入修前和
修后包，对无body正常、有body正常、FIN mismatch三份完整report bytes直接断言相等。
独立核对比较脚本、原meta和输出hash，并将临时修前包121 runtime文件逐bytes对照
`c9081f1`与原f994清单；三份比较摘要均与本轮资源report相符。该补充通过，不替代原四路
旧DTO/wire；后者仍按未变的相关生产者/codec和原证据身份复用。

PM原复现、原决定、初次定向设置失败及历史R01–R10/矩阵失败均保留。PM-01的诊断丢失
及重复顶层摘要已闭合，本次修后A8证据充分，无新增must。真实生产PDK/方言、EDA、隔离
目标环境和父级/global证明仍未覆盖；是否验收由PM决定，本review未合并main。
