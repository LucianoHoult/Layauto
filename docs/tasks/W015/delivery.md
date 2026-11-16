# W015 执行交接（方案候选，交 PM 接收）

## 恢复位置与授权

分支`codex/w015-single-cell-analysis-plan`，起始`e7c92c03d0b48aa143259da4fc9fbedc382efee0`，
产品main `3b8d78902591bca32ec9b8ee5d3167d115e1a974`。启动时本地在`work@8f3f395`，
工作区干净；普通fetch因sandbox代理不可达，授权网络fetch成功后确认FETCH_HEAD等于指定起点，
新建目标本地分支继续。未覆盖任何已有修改，未引入W012 A2。

本轮仅任务执行/方案/review区与W015目录。PM阶段/要求/验收/current-work不改；不改产品、
正式tests、固定fixture、旧schema/wire、架构正文；不实施、不自行验收、不合main、不删除分支。

## A1–A7覆盖

| 项 | 产物与可观察结果 |
| --- | --- |
| A1 | [plan](plan.md)源码/调用依赖表、legacy边界；[探针输出](evidence/coupling.stdout.json)明确旧失败阶段；[源码身份](evidence/source-identity.json) |
| A2 | [entry-contract](entry-contract.md)：推荐API、manifest/header/receipt、必需输入、状态优先级、facet/错误/消费方式、target/policy边界 |
| A3 | [interface-examples](interface-examples.md)：S1–S7最小请求差异、五域事实、来源/缺项/错误/受阻；[具体manifest](evidence/candidate-input/analysis.json)/[完整header](evidence/candidate-input/local-header.json)为人工候选输入，未执行新API |
| A4 | [implementation-proposal](implementation-proposal.md)：最小文件表、旧入口/DTO/wire兼容矩阵、annotation/body隐藏耦合与等强认证分拆 |
| A5 | 同方案的有限首包步骤、T01–T10实际文件验收、最小生产调查表；[可派发prompt草案](implementation-prompt.md)须PM接收后使用 |
| A6 | 同方案的旧/新调用图、一次capture/中立重构边界、早期三case资源及退回PM门；未新跑资源benchmark |
| A7 | 独立review安排在方案冻结后；review结论及finding关闭以[independent-review](independent-review.md)为准，不能以本执行摘要替代 |

## 验证复用与限制

- 本次实跑：旧reader/geometry小型probe、输入候选materialize、现有parser对候选引用的
  consumption探针及来源/链接/JSON/样张/范围核查。
  每项命令/结果见[evidence说明](evidence/README.md)。首轮耦合探针错误断言、
  候选路径重定位失败均保留；修后均exit0。F01/F02执行处理为真实候选URI闭合及明确
  domain中立数据/normalization认证wrapper，独立复核结论只由reviewer填写。
- 按身份采信：本轮产品/runtime/tests/config与上述main逐文件不变；W014 PM2已集成能力、
  [集成原回执](../W014/integration/receipt.json)及[资源原记录](../W014/resource-review.md)
  只作旧产品行为/成本依据；不把历史双1889/typing/build/安装标成本轮执行或新分析入口通过。
  本次身份清单与基线Git比较支持未改结论，没有重做旧大wire/安装树。原矩阵结论采用PM2
  接收的范围，不声称本轮重验每条历史命令。
- 未覆盖：新API尚未实现、所有新结果均候选；未跑产品最终矩阵/性能/真实EDA/生产方言；
  未运行新的完整terminal roundtrip；未做真实新会话生产恢复或内网验收。
- 补跑触发：本轮只文档变更做文档/来源/独立反例检查；任何未来runtime/tests/config/输入/
  依赖/来源认证图变化、旧证据失效或review新风险都补受影响范围，产品冻结后完成规范最终
  双矩阵；实际合并仍需PM组合检查，不能以方案通过代替。

## PM 接收点与下一步

请PM核A1–A7、独立finding闭合与候选合同是否在授权内，再为首包另建实施任务并明确
baseline/branch/正式owner同步。候选推荐已收敛，无需用户重复选择D1。剩余真实生产资料、
trust authority、父级映射/冻结/窗口验证器、修改/完整运行都不在本包承诺中；涉及新增关键
使用预期时再带具体样张交PM。生产隔离边界保持，不索取raw/PDK/log/hash，不假设pass/fail外传。

Git交接以本分支最终推送SHA为准；报告不追求包含自己的最终hash。review候选commit与修后
文件身份由reviewer记录；推送后核远端完整SHA并在对用户回复交PM恢复入口。
