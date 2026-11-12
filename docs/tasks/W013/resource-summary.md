# W013 修后同源组合成本

受测源码/测试/config身份：
`6463eb67b1c1ce5b9fd1fca436fa499a4ad14da004ef8fcd913872bd350443a9`。
完整映射、输入URI/字节、解释器、阶段时间、原日志和命令见
[修后三路原回执](resource-attempt-04/suite.json)及[计算索引](resource-analysis.json)。
Python3.12.14，当前同机，16GiB/4CPU；三路各自fresh process串行执行。

| 固定路径 | 首次W005/W006→W010阶段(s) | W013公开build/encode/decode合计(s) | API路径峰值(MiB) | 完整wire(B) | 相对内嵌W010增量(B) |
| --- | ---: | ---: | ---: | ---: | ---: |
| normal-direct | 10.986 | 54.579 | 199.87 | 23,104,092 | 314,874 |
| normal-readback | 23.242 | 112.808 | 506.46 | 59,736,484 | 315,538 |
| extraction-mismatch | 10.986 | 54.337 | 200.55 | 23,104,160 | 314,878 |

“W013公开阶段”包含重新认证上游的成本，不能当作新空间算法本身的耗时。
观察器只计量原有调用、返回原对象，没有增加捕获或删认证。三路均实证W010完整public decode
按build/encode/decode的**1/1/2，共4次**执行；每次内部继续完整认证W009/W008/W007/readback。
direct中这四次累计47.591s，新neutral draft构建三次累计2.403s，source normalization三次
0.089s，capture binding digest三次0.307s。其它包含Value解析、canonical编码、比较等。
`_require_input`等更外层的inclusive计时与这些内层计时重叠，**不能相加**。

完整W010 canonical Value只在新wire出现一次，W011完整Result出现零次。direct内嵌的旧wire
为22,789,218B，SHA与[同机W010参考](resource-attempt-01/w010-reference-normal-direct.json)
完全相同；新wire仅多约0.315MB，而不是把旧bytes再hex包装导致2倍项。三路新packet SHA
也均与[修正前的首轮三路](resource-attempt-03/suite.json)完全一致；修正只增加拒绝非法数据的
检查，没有改变正常wire或旧codec。旧codec/source/ref实现均未修改。

最早完整组合另保留在[首direct](resource-attempt-02/normal-direct.json)：公开三阶段57.702s、
峰值199.11MiB、wire23,104,092B；随后首轮三路与此次修后各自的source identity均独立保存。
direct单次测量差异不能当作稳定提速。readback修前/修后峰值存在约28MiB差异，源码检查路径
和GC/分配时序不同，未将其归因于某一项收益或损失；本次实际峰值按表报告。

本次峰值口径与原probe一致：全部upstream与result/restored/wire roots保持存活，起始前
一次gc.collect、其后默认GC，在公开API路径结束后固定HWM，再做packet分解和证据记账。
该数值不包括后续分析步骤引起的额外HWM，不是最大输入或生产资源上限。URI、原readback
RunRequest、cache和roots替换方式见[方案](interface-plan.md)，35项mismatch输入按
[原字节恢复回执](fixed-mismatch-restoration.json)恢复；没有为了对比更改URI。

W010参考与新W013是不同终端workload；旧W011/A1跨环境秒数仅作历史背景，不从它们推断
新模块的性能改善。本次未构造额外完整W011捕获，也未运行A2/B。当前没有重复全捕获wire
增长或资源阻塞：成本主要为明确保留的完整公开认证，scope内新数据约0.315MB。
资源独立核证归[code-review](code-review.md)；最终工程矩阵使用同一源码身份，包/smoke在
双全量结束后串行运行。并行矩阵只是调度选择，不是单次耗时/内存改善证据。
