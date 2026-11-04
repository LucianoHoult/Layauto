# W009 捕获 DTO 解码边界最终独立专项

Reviewer：`/root/ipmr01_independent_review/captured_boundary_audit`，未参与修复或正式测试编写。只读检查实现，仅新增本目录的独立 probe、结果与记录；没有修改产品、正式测试或 PM 记录。

受审版本 **`73e38df8f932bbb5bd9caf074b442ad2f5c286e9`**，基准 `cdf3d2d5d2aeb0c441221c8bb0b41d0b302d8afa`。已读取 AGENTS、README、协作和 local/remote 环境规则、IPMR-01 补修任务及架构 §11.2，核对 domain/publication_codec.py、domain/evidence.py、domain/results.py 及快照正式回归的实际 diff。新豁免只作用于 W009 成功输入/readback 可重建的 15 类捕获记录；其他失败/terminal codec 保持历史边界。wire 字段表、schema、打包与 canonical 检查未变。

主 reviewer 已发现并留存集合快照 finding。本专项检查 `73e38df…` 的处置：EvidenceRecord.sources 和 ParseResult 的 issues/completed/sources 均先验证 tuple/list 容器形状，再单次构造 exact tuple 快照，随后校验并保存同一快照。校验不再消费调用者容器的另一次迭代，因此有效首值无法在保存阶段变成未校验的 None；无效首值也不能靠后续迭代转成有效值。此处 finding 的原文、编号及总体处置结论由主 reviewer 维护。

**本专项确认上述处置有效，未发现新增必须修正项。** 在最终版本独立实跑：

- 主 reviewer 的原 `collection_snapshot.py` 见证：两入口均保留合法 SourceRef/SourceFile，`retained_invalid_none=false`，无裸 AttributeError。见 [本次原始输出](collection-snapshot.stdout.json)。
- 正式双向 ChangingList 回归独立执行 **8 passed in 0.58s**；覆盖四个公有集合入口、有效/无效首值、调用者后续 mutation 及迭代次数等于 1。见 [输出](snapshot-tests.stdout.txt)。
- 独立构造真实 W006 捕获取得全部 15 类记录，正常 public roundtrip 与 digest 一致。各字段 missing/extra、None/int/bool/string/bytes/rational、空/非空 tuple/map、外来 record 共 **1184** 次变异；**1143** 次明确 ValueError 拒绝，`unexpected_exceptions=[]`。另 **41** 次是字段允许的合法 neutral canonical 替代值，逐例重新 encode/decode 严格相同；它们不代表 capture-bound W009 成功认证。
- 仅替换 evidence.py 的 SourceFile 哈希模块绑定，注入 RuntimeError、ValueError、TypeError、KeyError、AttributeError、IndexError、UnicodeError、KeyboardInterrupt、SystemExit 九类既有对象，**9/9** 保持同对象、既有 cause/context 及 suppress-context。未全局改动 hashlib 或用更早层次 hash 失败遮蔽该边界。

本次全部命令退出 0，三个 stderr 均为空。解释器、命令、源码/正式测试与 Git 对象逐字节匹配、原始输出 hash 见 [identity.json](identity.json)；完整字段变异见 [result.json](result.json) 和 [probe.py](probe.py)。此前 8aa 版本的专项保存在 `../captured-before-final/`，本次最终结论采用重新实跑的 73e 身份，不将旧模块相同的判断用于新修复。

本专项运行 CPython 3.12.14；未重跑主 reviewer 的 99 项完整异常链、全量回归、Python3.10 或包/安装审计，相关结果由主 reviewer 分别记录。有限 primitive wire 变异及这组容器反例不构成任意运行时篡改或所有输入域证明。本专项不代写 IPMR-01 总关闭或 PM 验收决定。
