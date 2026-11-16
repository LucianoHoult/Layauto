# W015 独立执行session prompt

```text
按Layauto项目规范执行W015，角色为执行，任务是“单cell读取与分析入口的合同及实施准备”，本轮不改产品。

恢复codex/w015-single-cell-analysis-plan最新远端提交，核仓库、完整SHA、工作区和适用AGENTS；产品基线main 3b8d78902591bca32ec9b8ee5d3167d115e1a974，W014已验收集成。准备提交只改文档，不带入W012 A2候选。保留已有改动，必要时独立worktree。

先读docs/tasks/W015-single-cell-analysis-entry.md全部要求、协作规则、引用的架构原文、W014/production-body-scope.md，以及实际reader/schema/认证adapter/几何/关系的生产者消费者。完成A1–A7，不只重复U06原则。目标是让未来新分析入口在未选择外部body资料时保留可认证本地事实，明确未知父级关系、body缺证明、实际错误和受阻操作。当前完整read_inputs/W006合同保持。

先核真实耦合：reader在本地解析完成前读取body，geometry_input认证body记录和GDS角色，GeometryResult及W014访问body evidence。提出最小兼容分拆，不能删必填检查后吞错、伪造成功ParseResult/空body或monkeypatch认证。输出源码符号/调用依赖表，以及必要的小型只读探针；探针只写任务证据目录或临时副本，不改runtime或固定fixture。

在docs/tasks/W015/交一个推荐的Python API/请求/结果合同和具体输入输出样张，明确状态、字段来源及调用者如何消费局部结果。逐项说明分析是否需要target/intent、query header和export/validation policy；不偷偷构造target=source、虚构工具身份或放宽query/tech来源绑定。local source、observed、parent/global、body assurance和manual intent独立，保留unknown/conflict/mismatch，分析完成不等于完整run或修改许可。

覆盖S1–S7：无外部选择、正确synthetic上下文、选中但缺文件/格式错/绑定错/违例、人工意图、未来可信替代证据、无body且本地FIN/query问题、完整运行/超范围修改。样张标候选和synthetic，不能称现产品已经支持。可信LVS冻结与几何窗口仅定义未来边界，不本轮实现生产格式或验证器。只提供网名不证明导通，不从expected/spec/oracle/helper生成观测答案。

交最小文件改动表、旧接口/DTO/wire兼容表、第一实现包的步骤与验收测试映射，以及可直接执行的实施prompt草案。方案须指向“真实文件→本地分析结果与缺项”的有限闭环，不止内存DTO。真实生产资料的不足明确记录；遵循隔离服务器边界，不索取或上传真实raw/PDK/log/hash，也不假设可外传pass/fail。

列早期组合与资源计划，避免复制嵌套完整W011/W013/W014捕获、重复认证/重建无上界。按docs/collaboration/rules.md#verification-reuse只做本轮必要探针、来源/链接/样张检查，不跑双全量、构建/安装和大wire矩阵；未来产品最终矩阵仍按既有规则安排。

具体方案形成后安排未参与设计者独立review，核源码事实、来源/错误边界、样张、兼容性、实施可行性和资源风险，修正并独立复核所有必须项；保留原finding和失败。内部方案问题自主解决。用户已确认缺外部资料可做本地分析，不重复问D1或泛化选项；超出已授权关键预期才整理最小样张/影响/推荐交PM。

仅写本任务方案/执行/reviewer对应区和docs/tasks/W015/，不改产品、正式测试、固定fixture、历史证据、架构正文、PM要求/阶段/current-work。使用项目noreply身份提交推送原W015分支，核远端完整SHA，交A1–A7覆盖、方案review、实跑/采信/未覆盖/补跑触发和实施草案给PM。本轮到交PM为止，不自行验收、合main、删除分支或实施产品。
```
