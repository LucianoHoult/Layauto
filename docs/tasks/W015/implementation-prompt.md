# 首包实施 prompt 草案（待 PM 接收后派发，不是本轮执行授权）

```text
按Layauto项目规范执行PM新建的单cell分析入口实施任务。先核批准任务要求、base/branch/
完整SHA、工作区、适用AGENTS及docs/collaboration/rules.md#verification-reuse。任务编号、
实施起点及分支由PM在派发时填写，不能沿用W015“只做方案”授权直接改产品。

读W015/plan.md、entry-contract.md、interface-examples.md、implementation-proposal.md、
independent-review.md与delivery.md，回查架构§2.2/2.3、3.6、5.6–5.9、11.10/13/15、12及
W014/production-body-scope.md。具体PM已采纳差异优先，未采纳候选不能自称生效合同。

交付有限可运行闭环：实际analysis manifest + GDS/source CDL + tech六owner/limitations +
同源raw query/header/requests/dialect → 新local来源认证receipt → source/identity、drawn/
effective/local graph、FIN、coverage/conflict、D/G/S比较与B未知、缺项/受阻操作report。
新API analyze_cell(AnalysisRequest)固定local_readonly，首包仅现synthetic方言；不需要target/
export/validation文件，不构造target=source，不伪造tool/body成功，不放宽旧read_inputs/W006。

先复核reader读取顺序、NormalizationInput/GeometryInput、AnnotationBinding的旧normalization
hash/readback绑定、evaluate_body对annotation capture集合的要求。按W015方案在strict wrapper
下提取pure operand内核；新LocalAnalysisReceipt/AnalysisAnnotationBinding/AnalysisAnnotationDraft
与terminal/report均独立版本，旧DTO/codec不接受新类型，原fields/version/ref/wire必须保持。
不得把新local digest填旧normalization字段，不得向旧receipt塞空body或monkeypatch认证。

body显式not_selected与选中错误分开。首包可选旧synthetic context，但另行认证其实际bytes、
GDS/top/frame/object/units/tech，并运行全部现W014已实现body几何/规则检查；external不进入
local occupancy/union。parent/global首包未知。manual只接窄声明文件，不补observed/body。
trusted_lvs_freeze/geometry_window选择明确unsupported且不读文件，不实现生产验证器或修改。

分步先做T01/S1真实文件smoke和错误链，再接annotation/terminals及T06，再接body/manual及
S2–S7；所有验收映射见implementation-proposal的T01–T10。现fixture和历史证据保持。
新synthetic header显式迁移生成，保存原来源，重算实际本地closure/raw/caches绑定；
新旧格式互拒，生产tool-captured证据不得按synthetic迁移。观测答案不能从expected/spec/
oracle/helper生成；手算coverage/conflict及FIN反例、旧同来源结果parity作为独立依据。

最早可运行时串行测无body正常/有body正常/无body FIN mismatch的获取/认证/计算/report
时间、HWM、capture/report bytes、完整来源和neutral/认证调用次数，遵守W015资源退回门。
不复制嵌套完整W011/W013/W014捕获，不用全链wire作为层间通道，不以少认证换速度；
资源或兼容必须项无法有界闭合时交PM具体失败，不扩大链或复活W012 A2。

迭代跑新增/受影响/来源与失败探针，独立review未参与实现者核合同、差异、反例及旧DTO/wire
parity，修正并独立复核must。冻结实际源/测试/config后按规范做双3.10/3.12全量、typing、
build及双干净安装源码外真实文件smoke。保存身份、原输出/失败与采信边界，PM在实际集成
版本另做必要组合；不能用换session作为重复双全量理由。

真实OS/依赖/CDL/query/PDK与trust资料仍未知，遵守隔离服务器边界，只能向内上传代码，
向外仅可描述数值脱敏格式；不索取上传raw/PDK/log/hash，不默认允许外传pass/fail。
synthetic通过不证明真实工具/生产准入。无body分析不产生baseline/no_change/terminal/修改许可。

写入PM明确授权的产品/测试/正式owner文档与新任务证据，不自行改验收标准/PM阶段/current-work。
按派发授权提交推送对应分支，交要求覆盖、独立review、实跑/采信/未覆盖/补跑触发与恢复点。
不自行验收、合main、删除分支或追加生产范围。
```
