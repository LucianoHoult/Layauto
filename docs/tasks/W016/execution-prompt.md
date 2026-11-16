# W016 独立执行session prompt

```text
按Layauto项目规范执行W016，角色为执行，交付单cell只读分析入口。恢复
codex/w016-single-cell-analysis最新远端准备head，核完整SHA/工作区/AGENTS；基线为
W015方案merge d0bb5628384f3a9fec1fe87b6311b854996f574b，产品仍为W014已验收版本。
保留既有改动，不能从W012 A2候选派生。

先读docs/tasks/W016-single-cell-analysis.md全部A1–A8与PM澄清、引用架构原文、
W015的entry-contract/interface-examples/implementation-proposal/independent-review和PM1。
W015方案已接收，本轮授权产品实施；不要重新只交方案或沿用W015“不得实施”的旧prompt。
先记录实际最小文件表、认证/异常依赖、测试/资源计划；只有实质偏离方案才补方案review。

实现layauto_v2.analysis.analyze_cell(AnalysisRequest)：实际新manifest/GDS/source CDL/
tech六owner/limitations/raw query与独立header→完整local来源认证→source/identity、exact
drawn/effective/local graph、FIN、coverage/conflict、D/G/S与B缺项的只读结果。不读target/
export/validation文件，不构target=source；本包仍query必需、dummy_fixture、flat受限能力。
新独立版本不放宽旧read_inputs/W006、NormalizationInput、AnnotationBinding或任何旧DTO/wire。

按W015方案在strict wrapper下面提取pure operand内核；domain只冻结中立Evidence/view，
normalization拥有重parse实际bytes的Receipt，不在domain import parser。新annotation绑定
真实local receipt，不把digest冒名填旧normalization字段。report是诊断view，不能decode
回可信receipt；首包只公开顶层分析，不新增公开receipt续算/持久化入口。

external_body未选与选错分开；有synthetic context则独立认证对象/作用域/单位/来源并跑
全部现有W014 body规则，external不进本地union。manual只接窄声明，不补observed或父级。
未来trusted_lvs_freeze/geometry_window明确unsupported且不读资料；parent/global首包未知。
completed是分析完成，保留FIN mismatch、正常coverage gap和局部规则违例，不等于全套通过；
按已采纳status/facet规则保留rejected、unsupported、依赖未执行、部分诊断和原始code/ref。

补资料须显式新调用、重新获取认证，旧结果不可变；manifest变更需相容的新synthetic header
闭包，不在运行中等待补文件/隐式重试或改旧证据。local是选定cell的scope；首包不展开层级，
reachable hierarchy按真实capability拒绝。manual instance_hint不形成受信父级映射。

按A1–A8及W015 T01–T10从真实临时文件实现验证，旧fixture/答案不改；新header的显式迁移
保留原证据和synthetic身份，不从expected/spec/oracle/helper造观测答案。测source/geometry/query
独立正确性、FIN4对5、手算coverage/conflict、错body/错误链、alias/native/mutable/forged refs，
新旧接口互拒与旧W007–W014同输入完整DTO/wire/hash parity，readback与W006审计/retry保持。

最早可运行时串行测无body正常/有body正常/无body mismatch，记各阶段时间、HWM、
capture/report bytes、认证及neutral重构次数。按任务资源门及时交PM具体测量/调用图/缩包建议，
不等双全量才发现成本，不复制多份完整Result，不少认证取巧，不复活W012 A2。

按verification-reuse迭代跑新增/受影响范围；未参与实现者独立代码及接口review，必须项修正
并独立复核。冻结源码/测试/config后双3.10/3.12全量、typing、build及双干净安装源码外真实
文件smoke。保留原失败和可复用身份/输出；review换session不重复双全量，PM集成仍需组合检查。

更新README公开入口及任务执行证据，按需同步授权owner的实施细节，不改PM要求/阶段/
current-work/历史证据。以项目noreply身份提交推送原W016分支，核远端完整SHA，交A1–A8、
独立review、资源、本次实跑/采信/未覆盖/补跑触发和恢复点；不自行验收、合main或删分支。
真实PDK/方言/工具与隔离环境仍未验证，不索取上传保密raw/PDK/log/hash或假定pass/fail外传；
分析不产生baseline/no_change/terminal/实际修改或发布许可。
```
