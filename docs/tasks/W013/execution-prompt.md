# W013 独立执行 session prompt

```text
按Layauto项目规范，执行W013网络区域标注与覆盖草稿。恢复codex/w013-net-annotation-coverage最新PM准备提交，起点为main2489b4609ae97d8211bf450d55cac9392492ac71的A1产品；先核远端完整SHA、工作区、AGENTS/协作/环境规则及W013全部要求。不要切到6045d8f的A2候选或带入其codec/测试。
先读实际W007 net identities/seeds、W009有效region、W010局部图与codec/来源合同，tech/query输入和独立oracle/手工意见；按architecture §3.3/3.5–3.8/5.3–5.9/11.5等制定具体输入绑定、target/fragment、匹配/coverage/冲突、结果owner和canonical/异常方案。画调用与序列化边界，给小输入输出和最小文件清单；由未参与方案设计者独立review并修正必须项后实施。新关键预期/格式/policy缺口先带反例交PM，不自行猜测。
仅做当前synthetic支持范围内的local网络区域标注。复用真实net_xref→NetId/QueryKey seeds；按tech layer mapping、精确单位/区域和声明的quality/tolerance/trim匹配，不能用query造几何、cell center整格涂色、名字猜网或升级approximate质量。保留部分覆盖/未匹配证据/未知导体/marker/歧义与冲突；同net不同物理分量不合并，component摘要不代表各region均直接被query覆盖。对照oracle本地投影，外部body节点/边不混入W010本地范围；现有body要求/U06不改。
完成W013 A1–A8，保留不可变/防御快照/公开完整验证/原异常链、旧codec的wire/ref、来源及run/owner绑定；输出只是source-evidence/local草稿，不发布baseline/terminal、不宣称完整M1或真实EDA。只改本任务最小相关模块与必要测试，新证据放docs/tasks/W013/，不改已验收fixture/答案或旧finding/报告。
默认执行docs/collaboration/rules.md#verification-reuse，无须用户再次提醒：开发跑新增及受影响范围，交接列实跑/按身份采信/未覆盖/补跑触发条件。最终新冻结源码/测试/配置完成双3.10/3.12全量、typing、构建与双干净安装源码外组合smoke；独立review核证据身份并补关键探针，换session本身不重跑双全量。不能用旧A1矩阵代替新产品最终矩阵，源码改变按规则重新冻结验证。
最早完整组合即测固定direct/readback/mismatch的耗时、峰值和wire大小，说明新增模块与未改上游成本；不默认重复嵌套完整W011捕获。沿用原输入URI/RunRequest/cache/roots/GC，跨环境旧秒数只作历史参考；必要时同机复测/重复以辨别波动。若出现明显重复序列化增长/资源阻塞或成本解释不清，在昂贵最终矩阵前交PM具体证据与建议，不默默扩大状态链、不删认证或重开A2/B。
独立代码/合同/组合/资源证据review，修正复核必须项并保留原失败。沿用项目noreply身份提交推送原W013分支，核远端完整SHA，交PM；不自行验收、合main、删分支、改PM阶段/current-work或启动下一任务。方案review遇关键未决项、资源节点阻塞时保留可复现材料交PM，不能把部分交付标完整。
```
