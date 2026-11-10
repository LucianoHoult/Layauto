# W012 P1/P2 PM 接收

**P1/P2、PP1–PP5 调查阶段验收通过，新增必须修正项0；产品优化尚未实施，W012整体未完成。** 核对原分支交付 `5085f994f0bd4b0c39f7ac1ccdbcacc43d281720`、工具冻结和实际命令/输出、R01单行统计修正及独立复核。完整身份和证据哈希见[机器回执](pm-receipt.json)。本阶段已提交分支材料的集成状态另记，不将其冒作产品优化发布。

PM 独立[证据专项](pm-evidence/evidence/report.md)实际 **1048项轻量核验通过**，核实262源/100runtime、六路fresh串行baseline/profile、相同wire/capture、内存补测、全部原输出/manifest以及R01关闭。原1521项独立review与本次1048项均为证据/工具核验，不是产品测试数量。PM另实际完成 **18项观测器透明性/异常历史小检查**及原probe轻量selfcheck，见[原输出](pm-evidence/observer.stdout.txt)和[结果](pm-evidence/observer-result.json)。[方案专项](pm-evidence/plan/report.md)未发现必须修正项，明确A/B的兼容边界。

没有重跑重型baseline/profile、双全量、typing或包/安装。产品源不变，W011工程验证按源身份采信。本机没有原固定mismatch目录；已核35项origin bytes/hash及持久清单/测量capture身份，后续比较前必须按清单重建并核对，不能声称本次已重测。

## 接收的成本结论

- 无插桩三路径阶段总计约 **91.922 / 187.952 / 88.231s**；readback完整wire **136,471,701B**，整进程峰值 **7,327,952KiB**。各路径原输出/计时/来源与profile身份一致，不能与旧W011不同URI/RunRequest的样本直接计算优化收益。
- 外层hex约占99.9%，主要是已编码下层wire被再次按值展开/转hex；不是原始捕获占用了99.9%。原始payload仅约0.28MB，读回logical bytes约1.75MB，不能独自解释GiB峰值。
- 额外readback中，既有 **118,841,892字符** hex校验调用窗口将进程高水位刷新到 **7,319,108KiB**，返回后RSS约348MiB。这个窗口定位支持优先改matcher；不等于净分配或已测清regex内部全部分配。
- 重复认证/重建也是实测成本，cumulative时间互相嵌套不能相加；profile约51%的codec disjoint self-time也不能直接当无插桩函数耗时或收益预测。

## PM 决定与下一步

先准备 **兼容A1：现有hex校验的最小优化**。它属于已有性能目标内的内部实现，保持 `/1` canonical bytes、wire大小/全部hash/ref及公开验证/异常合同；本轮不需要用户重新批准普通算法选择。具体派发边界和验收由下一实施记录明确。writer/reader/memo待A1数据后再细化，不能顺手扩成整个兼容包。

20%耗时/50%RSS是完整兼容方案的可行性目标建议，**不硬绑给最小A1，不记为获批的产品承诺**。A1须提供完整三路同条件前后证据，查明matcher窗口及整进程峰值改善/残余成本，逐路径披露耗时退化；不能靠减少测试数或microbenchmark代替。

新格式B继续保留，**不随A1批准**。实施前要交用户可审阅的旧/新完整样本、旧decoder拒绝例和兼容矩阵、exchange hash与各类content ref前后表、历史readback/repository迁移范围，再决定公开入口、默认/支持期及内容身份策略。当前无需用户就尚未完整定义的B做选择；保持旧格式不妨碍先降低现有内存/时间成本。
