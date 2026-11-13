# W014 独立执行 session prompt

```text
按Layauto项目规范执行W014，角色为执行，不代写PM验收。恢复codex/w014-terminal-body-relations最新远端PM准备head，核工作区、完整SHA、AGENTS和current-work；产品基线main00ee6c6f51b683a8aefa96a5415b7ca969778502（W013已验收），后续准备提交仅文档，不能带入W012 A2候选。

首先阅读docs/tasks/W014-terminal-body-relations.md全部要求、协作规则和引用的架构原文，以及W011/W013生产者接口和验收证据。目标是逐器件核对D/G/S/B与source CDL，正常6个本地端＋2个独立context body端；不修改本地物理graph、不发布baseline或terminal，不宣称真实LVS/生产准入。

先交具体方案到docs/tasks/W014/：最小文件表、输入/输出及状态样张、同源/owner/来源闭合、端子target与source/observed区别、T04/T05/T08事实及判断覆盖、错误边界和资源调用图。安排未参与方案设计的独立review，必须项关闭后在既有合同内实施。普通内部实现问题自主解决；新输入解释、物理语义或关键使用预期先带具体反例/影响交PM，不自行放宽标准。

复用W011真实channel identity/topology、W013区域/分量net证据及现行tech body_context/2。完整输入仍来自真实reader/captures；禁止从oracle/spec/expected或fixture helper导入答案。正常MN0 D=Y/G=A/S=VSS，MP0 D=Y/G=A/S=VDD；B通过独立外部几何链分别关联VSS/VDD，本地BN/BP仍为unknown且无额外union。shared gate不能整条独占归某device，CDL端口名不代表物理pin access。S/D按现行ordered profile，swap unsupported。比较网络来源不能抄CDL期望或context.expected_semantic_rail。

按A1–A7覆盖所有正常/拒绝/缺口：同源、精确边/面积/包围、所有适用对象与唯一性、完整端子集合、source与observed不混用、unknown/conflict/mismatch分开、7个body见证和原REQ-01的45.05对45误配反例；保存W011 4对5差异和W013缺口。已被reader拒绝的案例说明真实阶段，不伪装到W014或terminal。新DTO/codec要闭合来源、不可变/native/alias/字段、确定编码与原异常历史；旧wire/ref/认证不变。

另交production-body-scope.md满足A8：针对只输入底层cell，给具体小样张和推荐处理方案，保留本地已知端口/net，区分未知父级供电关联与外部body物理路径，列最小上下文、可信替代证据/人工标注的证明边界及可继续/须阻止的操作。本轮这是设计交付，不改reader的body_context必填，不把toy格式推广为全部生产要求；有关键取舍交PM，已确认D1=A不重复问用户。

遵循默认verification-reuse。开发跑新增及受影响项；最早可运行时完成direct/readback/mismatch资源检查，说明共用捕获、重建次数、新增wire/耗时/峰值，不默认嵌套两份完整W011/W013结果；资源显著放大在最终矩阵前交PM，不靠删认证或少跑测试伪造收益。最终新冻结产品按任务完成双3.10/3.12全量、typing、build、双clean安装源码外三路smoke，并完成未参与实现者的独立代码review及修正复核。明确实跑/采信/未覆盖/补跑触发；无源变化不因换review/PM再复制大wire或重跑双矩阵。

仅改任务授权runtime/测试及执行材料；不改固定fixture/答案、历史证据、PM要求/阶段/current-work，不启动后续任务。新增失败见证放测试临时副本或新测试数据，旧样本不覆盖。完成后用项目noreply身份提交推送原W014分支，核远端完整SHA，交A1–A9覆盖、原失败/修复证据、资源限制和U06方案给PM；不自行验收、合main或删除分支。
```
