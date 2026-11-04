# W009 捕获 DTO 解码边界独立专项

Reviewer：`/root/ipmr01_independent_review/captured_boundary_audit`，未参与修复或正式测试编写。只读检查实现；仅新增本目录的独立 probe、结果与记录，无产品或正式测试修改。

受审版本 `8aa11baebfea935933b18cae3f23ba8c1e9c6486`，基准 `cdf3d2d5d2aeb0c441221c8bb0b41d0b302d8afa`。已读取 AGENTS、README、协作和 local/remote 环境规则、IPMR-01 补修任务及架构 §11.2，核对 domain/publication_codec.py、domain/evidence.py、domain/results.py 的实际 diff 与全部相关 DTO 构造函数。新豁免仅作用于 W009 成功输入/readback 可能重建的 15 类捕获记录；其他失败/terminal codec 保持历史边界，wire 字段表、schema、打包与 canonical 检查未变。EvidenceRecord.sources 及 ParseResult 的 issues/completed/sources 在元组快照前明确验证集合与子值。

**本专项未发现新增必须修正项。** 独立构造真实 W006 输入捕获，取得全部 15 类记录，直接使用 publication 公共 encode/decode：

- 15 类正常 roundtrip 与 digest 一致。
- 各字段 missing/extra、None/int/bool/string/bytes/rational、空/非空 tuple/map、外来 record 共 **1184** 次变异；**1143** 次明确 ValueError 拒绝，无裸 TypeError/AttributeError/IndexError 或其他意外异常。另 **41** 次是字段允许的合法 neutral canonical 替代值，逐例重新 encode/decode 严格相同；这不是 capture-bound W009 成功认证的证明。
- 独立替换 evidence.py 的 SourceFile 哈希模块绑定，注入 RuntimeError、ValueError、TypeError、KeyError、AttributeError、IndexError、UnicodeError、KeyboardInterrupt、SystemExit 九类既有对象，**9/9** 保持同对象、既有 cause/context 及 suppress-context。未全局改动 hashlib，也未破坏更早层次的 hash 运算来遮蔽该边界。

命令与解释器、原始 stdout/stderr、逐例 JSON 及三个源码 hash 见 [identity.json](identity.json)、[result.json](result.json) 和 [probe.py](probe.py)。实跑 CPython 3.12.14，退出 0，耗时约 321.60 秒，stderr 为空。探针只构造受支持 primitive wire，属于有限字段变异，不构成任意运行时篡改、所有 Unicode/数值或全输入域证明。

运行期间最终产品追加 `_validation.py` 空 count token guard，HEAD 为 `5f9af59c3d70564568861e14d24ea49653d76d71`。本专项不中途切树；已实际比较两个提交，上述三个受审 domain 模块逐字节无差异，因此本专项结果可用于该最终产品的相同捕获边界。未重跑主 reviewer 的 99 项完整异常链、全量回归或包/安装审计；这些由主 reviewer 分别记录。本专项不代写 IPMR-01 总关闭或 PM 验收决定。
