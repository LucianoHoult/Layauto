# W015 独立方案 review

Reviewer：`/root/w015_independent_review`，未承担方案设计/样张生成/产品实现。
初审候选`5a815f58584746986b344f7616786b6360986e42`，准备base
`e7c92c03d0b48aa143259da4fc9fbedc382efee0`，产品main
`3b8d78902591bca32ec9b8ee5d3167d115e1a974`。仅审方案与实施准备，不是产品review/PM验收。

**最终：方案 review 通过，剩余必须项 0。** 初审两个必须项均经执行修正与独立复核关闭；
另两项minor已修正。原 finding 保留如下；最终结论见本文件修后段，
不能把原候选、初次probe错误或候选输入materialize成功记作分析入口已可用。

## 原 findings

| ID | 级别 / 原问题与影响 | 独立依据 | 执行处理 / 复核 |
| --- | --- | --- | --- |
| F01 | must，候选真实输入URI不闭合。header把raw URI重定位到candidate-input根，但requests仍用旧`query/raw/...`；tech bundle的六owner仍用旧`tech/...`。即使13 closure+9 raw hashes和closure摘要都正确，也不能走现parser，A3/A5真实文件闭环准备尚不完整 | 独立从`git show 5a815f5`重建原文件；[initial输出](evidence/review/candidate.initial.stdout.json)确认6个request路径不匹配、6个owner路径不存在；现`parse_query`实际`RequestBindingMismatch`。只用旧固定tech隔离raw请求问题，不伪造receipt；脚本[candidate_probe](evidence/review/candidate_probe.py) | `bcb676944acbda8853b15c52777e06d76ba9a176`修复独立tech/requests副本；最终候选`a2d55db…`独立核URI/实际owner/raw/query均闭合，关闭 |
| F02 | must，receipt认证构造边界不唯一。entry-contract要求`LocalAnalysisReceipt`构造器重parse实际bytes，实施文件表却把同名receipt列入domain，同时要求domain不import parser、认证wrapper在normalization。下一执行者无法按唯一类型合同实现，可能引入反向依赖或把未认证domain数据当receipt | 直接比较初审entry-contract“新LocalAnalysisReceipt/构造器”段与implementation-proposal文件表/“新domain不依赖importers”段；架构§11.15禁止domain依赖importers；现GeometryInput认证wrapper落normalization可作对照 | `bcb6769…`明确domain.LocalAnalysisEvidence/只读view与normalization.LocalAnalysisReceipt；结果不持/导入wrapper，首包无receipt消费API。最终全文及差异独立核对，关闭 |
| F03 | minor，W009依赖表把`_require_input`写为“完整W008 codec重建”，实际是closed graph检查+encode，没有decode；会误导认证/重构成本计数 | 现`normalization/effective.py::_require_input`与`geometry_codec.encode_record`；[独立AST/身份核验](evidence/review/identity.initial.stdout.json)确认encode有、decode无 | `bcb6769…`已改为闭合图检查+wire编码、不decode；源码AST及最终文本一致，关闭 |
| F04 | minor，资源门把历史W014 build+encode+decode数值引用为不存在的已测build+report路径；不同口径不可直接套2倍比较 | 对照原resource-review与初审implementation-proposal；执行者自查也定位该措辞 | `a2d55db…`明确历史仅参考，同口径reference才可算倍率，无reference用绝对HWM/捕获重复/无界次数门，120秒仅提议PM预算复核触发。独立差异核对，关闭 |

F01由执行者冻结后自查亦发现；本review没有以执行消息代替验证，独立从原commit重现并记录
结果。独立probe针对原候选的预期是“可复现失败”，因此命令exit0代表反例断言成立，
**不代表原候选输入成功**。执行者的首轮缺body代码错断言与候选probe失败另在原证据保留。

## 独立核对范围及判断

已读取根AGENTS、README/文档导航、协作/环境规则、W015全部要求与prompt、引用架构
§2.2–2.3/3.6/5.6–5.9/11.10/11.13–11.15/12，以及W014生产body设计及方案文件。
本轮范围只改文档/候选材料，review不自行调整架构合同、验收标准或产品范围。

- 源码事实：reader在本地GDS parse前读取必需body；ParseResult success/error闭合；
  NormalizationInput要求完整records/value；GeometryInput严格body二source角色与GDS backlink；
  W013旧binding封闭normalization hash/readback，W014旧body evaluator强制同annotation捕获源；
  中立几何、channel/FIN的纯输入足以支持另建严格local wrapper。核实际源码而非只读摘要。
- 来源/语义：新manifest/header/receipt必须独立版本；新query本地闭包仍涵盖实际GDS/CDL/raw/
  requests/dialect/tech六owner/limitations；只有synthetic能显式生成新header/run id，保持tool
  未执行、LVS not_run。target/policies/body从新本地闭包分离不授权删旧必填或复制source为target。
- 样张/错误：S1–S7分开source/observed、parent/global、body和manual；正常gap与source FIN
  mismatch保留；实际错误/选中违例不能变unknown。手算coverage为40−24=16，交叠为2×4=8，
  独立核算一致；这两个是overlay子例，不是完整新API已跑结果。instance toy未知字段拒绝与
  未来受信instance绑定错明确分开，没有声称当前能验证真实层级映射。
- 兼容/可实施性：推荐对source-only/annotation/body/terminal抽纯operand内核，旧wrapper/
  DTO/wire/ref严格保持，新annotation binding不冒旧normalization hash；首包T01–T10有实际
  文件→认证local→报告闭环及旧错误/codec回归。提取验证器与旧wire parity仍需产品实现独立
  review，本文不以设计替代实现正确性。局部完成不形成run、baseline/no_change或修改/发布许可。
- 资源：一份capture/共享local事实，禁止三份完整W011/W013/W014 Result嵌套；三case早测包含
  真实公开认证/中立重构和report大小，成本放大/无界认证回PM。不因少认证取巧，不复活W012 A2。
  既有W014数字只作历史引用，不是本主机测量或新入口性能承诺。
- 真实资料：生产方言/PDK/trust authority/隔离环境仍未知；不请求raw/PDK/log/hash，
  不假定pass/fail可外传，不从synthetic通过推真实生产支持。人工供电声明无物理证明权能。

## 实跑、采信、未覆盖与补跑触发

本次实跑在Linux `/workspace/Layauto`、Python3.12.14：

1. `python -B docs/tasks/W015/evidence/review/candidate_probe.py initial`，exit0：
   原候选hash完整但URI/实际parser失败反例成立，原输出/stderr保留。
2. `python -B docs/tasks/W015/evidence/review/candidate_probe.py current`，初次修后工作区exit0：
   URI一致、closure/raw哈希闭合、现parse_query读出2 instance/4 net xref、2 device/8 net region
   记录；这只是已有parser直接消费候选文件的有界探针，**不是新receipt认证/分析API**。
3. `python -B docs/tasks/W015/evidence/review/identity_audit.py`，exit0：
   与main逐文件比对runtime/tests/config身份，并独立确认关键源码边界和PM/架构owner未改。
   工作区被审文件hash随输出记录；修后冻结身份已在下段最终核验闭合。

按身份采信：W014 PM2已接收的旧能力和原工程/资源证据作为当前已集成基线，
本轮实际逐文件身份核对支持产品未变；未重跑历史双全量/typing/build/安装/大wire。
不把执行摘要或空CI当验证，也不重新封装历史原证据。

未覆盖：新schema/新receipt/新API尚未实现，S1–S7新结果均候选；没有真实EDA、生产格式、
完整terminal roundtrip、资源benchmark或新产品矩阵。本次review通过不能授权产品实施或代替PM。
补跑触发：修后受影响候选输入/合同重新独立核对；未来runtime/tests/config/依赖/认证调用图
变化、来源证据不闭合或新反例触发对应产品检查；新产品冻结后依规范最终矩阵、PM实际集成组合。
仅文档/证据补记不触发重复全量。

## 修后独立复核与最终结论

修后冻结候选：`a2d55dbf20c1b07b9f5ca3faddad9c6a8721637b`（前一修复为
`bcb676944acbda8853b15c52777e06d76ba9a176`）。本reviewer直接核两次diff与修后合同、
实施方案、样张、prompt、candidate输入及来源，不仅采用执行者关闭说明。

- F01：独立probe最终按candidate tech实际URI读六owner，并核13 closure+9 raw的逐文件hash/
  sorted digest、6个request/raw URI逐条相等；现`parse_query`实际成功得到2/4/2/8记录。
  [最终独立输出](evidence/review/candidate.final.stdout.json)记录manifest/header的精确hash，
  与冻结候选一致。旧候选失败及初次修后工作区输出保留，不改写成相同结果。
- F02：domain只冻结`LocalAnalysisEvidence`与只读LocalAnalysis/result；认证wrapper是
  `normalization.analysis_input.LocalAnalysisReceipt`，从captured bytes重parse，结果只含view/
  receipt_ref，report/裸Evidence不具认证权能，未来公开消费必须重认证。精确构造/依赖边界已唯一，
  无需domain反向import parser。F03/F04源码事实和资源口径亦分别修正。
- 最终[身份核验](evidence/review/identity.final.stdout.json)实际确认284个runtime/tests/config
  文件与main逐字节相同，原PM要求/阶段/验收及架构/current-work/roadmap未改。
  核验中记录被审工作区文件hash；本报告及后续交接文字不追求自包含hash。

A1源码调查、A2入口合同、A3候选输入/样张、A4兼容/认证分拆、A5首包真实文件步骤与T01–T10、
A6资源门均在本轮方案范围有可审交付；A7完成独立review及must关闭。**可交PM接收具体方案，
不代表产品验收或实施授权。** 后续仅执行/review交接和文档检查补记可由PM按精确身份采信；
若更改合同/样张/实施方案/prompt/候选输入，须重核受影响结论。新产品的旧DTO/wire parity、
来源防伪、资源及最终矩阵义务均保留，不能从本次已有parser小探针推断新API已可用。
