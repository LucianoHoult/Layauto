# W010 独立合并前复核：异常链与不可变边界专项

Reviewer `/root/exception_review`，2026-11-06，未参与 W010 设计、产品实现或正式测试。
受审 HEAD `c4909ab679d0c0806200fcb132db8a5de1ad3e75`；准备到冻结产品
`9758a157115cc22d91ce095ac2002209b9f210d3` → `0f5029df935bc0acd106aad1bc2be81304d4f442`。
二者后的产品/正式测试无变化。工作目录 `/workspace/Layauto-w010`。

## 静态判断

已读根 AGENTS、README、协作与本地/云环境规则，W010 原要求、方案及现有边界
review，W009 IPMR-01 原 finding、修后结论及 FXR-01；回查架构 §2.2–2.3、
§3.5–3.6、§8、§11.2–11.3/11.15，与实际 local/effective/geometry/semantic/
publication decoder、captured DTO 和 closed graph 实现。原 review 仅作定位线索。

- 新 local decoder 显式检查字段/tag，再直接调用 constructor；没有对任意内部
  TypeError/ValueError/中断作宽泛翻译。嵌套 geometry/effective decoder 直接传递；
  semantic NormalizationInput/ReadbackBinding 和 publication 捕获链继续使用 W009
  IPMR-01 修后的构造器路径。
- `normalization/local_connectivity.py:111` 的公开 builder 在 ContactProblem
  handler 中只保存 issue，于 **123 行**离开 handler 后构造 error result。
  因而后续 `_require_input` 全链再认证失败不会自动以已处理 policy error 替换原
  `__context__`。专项以真实不支持的 captured policy、真实第二次嵌套认证注入验证，
  不只测试 success decode 或替换整个认证 helper 后直接抛异常。
- 新 DTO 集合只接受 native tuple/list，对同一 tuple snapshot 校验并保存；本轮
  不以必须支持 list 子类作为新增标准。已有 EvidenceRecord/ParseResult 接受的
  list 子类仍按 W009 FXR-01 修后路径单次取快照。原对象图 closed validation 在
  编码复制前执行，native tuple/list 的递归可变别名不能通过 captured success。
- neutral aggregate 重建节点、边、逐侧审计及全量分组；captured result 另外完整
  认证原 W009 输入和 rules source role。此专项对 omission/shape/alias 取有限样本；
  数学、来源成组伪造和完整图反例由主 review 及其它专项分别核验。

## 实际验证

状态：**完成，专项新增及剩余必须修正项 0。** 主 probe 实际 exit **0**，Python
**3.12.14**，1429.580s；[完整结果](exception-results.json) 为 **260/260 checks**、
`status="passed"`、`failures=[]`。脚本、stdout/stderr hash 与完成回执一致，受审
runtime/tests/config 未改。未以 partial 输出或空 stderr 代替最终退出码。

脚本 [exception-probe.py](exception-probe.py) 不 import 正式测试或历史 review helper。
实际命令、解释器、cwd、HEAD、脚本 hash、退出码与输出 hash 由
[exception-command.json](exception-command.json) 记录；原输出为
[stdout](exception-stdout.txt) / [stderr](exception-stderr.txt)。

正常 fixture 经真实 W005 与 W006 readback → W008 → W009 → W010 构造。
不支持 policy 只修改 `/tmp` 内 fixture 副本的 physical operator 字符串，重绑实际
closure hash 并移除可选 normalized cache；仓库 fixture、产品和正式测试不变。
这检验既有格式内的不支持语义，不提出新输入格式或能力。

矩阵检查异常同对象、原 cause、原 context、suppression 位；畸形 wire/constructor
对照要求明确 ValueError 和非空诊断，不把任意异常记成通过。故障注入在合法真实
捕获建立后进行，且有正常 roundtrip/digest、真实 error result 往返对照。

| 本次实际检查 | 结果 |
| --- | --- |
| 正常 direct/readback 完整 roundtrip 与 digest | 2/2，同一捕获身份内比较；不要求不同 checkout 的完整 receipt hash 相等 |
| 完整 local result nested decoder | 92/92 原对象和原链；44 direct + 48 readback，覆盖新 contact/enclosure/component、W009 difference、base layout/partition/occupancy、semantic request、CDL/query 校验、捕获 SourceFile hash、readback content_ref；ValueError/TypeError/KeyboardInterrupt/SystemExit，含两种 suppression 位 |
| 公开 builder 相同算法/嵌套边界 | 11/11 RuntimeError 原对象和原链 |
| 真实不支持 captured policy | direct/readback 均明确 `UnsupportedLocalContactOperator`、来源 `tech/physical.json#/operators/same_layer_contact~11`，保留 input/completed；两条 error wire 均 roundtrip，4/4 |
| ContactProblem 后构造 error result 的第二次实际认证 | **56/56** 原对象和原链：direct 24、readback 32。故障点为实际 layout materialization、request decoder、SourceFile hash，以及 readback content_ref；四类异常各测 suppression false/true；另 56/56 计数确认进入第二次 `_require_input`，首次认证照常执行 |
| Native list 快照 | nodes/edges/audits/components、edge endpoints、component members、result issues/completed 共 8/8；caller list 改成 `[None]` 后新 DTO 保持原值 |
| 原兼容单次快照/新边界 subclass 与递归别名 | inherited EvidenceRecord 正反 2/2；新 list 子类明确拒绝且 0 次迭代；被篡改为 list 的 nested draft 在 encode 和 captured success constructor 均明确 ValueError |
| 畸形及遗漏对照 | 8 类公开记录各 missing/extra 字段 16/16；nodes/edges/audits/components 在 constructor 与 nested wire 遗漏共 8/8；nested effective bytes 错形 1/1，全部明确 ValueError |

累计 **159/159** 故障注入保留原 exception object、cause、context、suppression。
56 条第二次认证用的是实际捕获 policy error；不会把先前 ContactProblem 污染进
新异常的 context。没有新增必须修改建议；这些有限实测不声称穷尽所有 Python
错误或畸形字节，不把故障矩阵时长当生产性能证明。

本专项未重跑完整工程矩阵、构建或安装，不替代主 reviewer 的实跑回归及工程审计。

独立 [exception-snapshot.py](exception-snapshot.py) 已完成：
EvidenceRecord.sources 与 ParseResult.sources/completed/issues 四入口，各验证
valid-first/invalid-first 的交替 list 子类，共 **8/8**。每次仅迭代一次；合法首次
快照保持 tuple 且后续 caller 变化无效，非法首次快照明确 ValueError。
[回执](exception-snapshot-command.json) exit **0**，Python **3.12.14**，0.984s；
[原结果](exception-snapshot.stdout.json) / [stderr](exception-snapshot.stderr.txt)。
此项为本次实际重现 W009 FXR-01 修后行为，不只是采信原记录。
