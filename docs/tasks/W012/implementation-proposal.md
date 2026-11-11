# PP4 具体实施方案（建议，尚未获派发）

本文件为成本调查交 PM 的实施建议。数值依据和排序在 `cost-analysis.md`；不是已达成的产品性能成果。所有 runtime、公开 DTO/codec、正式测试和输入均未改。

## 推荐先实施的兼容工作包 A

Owner：`domain/codec.py` 的 canonical writer/reader；`normalization/{codec,geometry_codec,effective_codec,local_connectivity_codec,channel_identity_codec}.py` 的内部序列化路径。不改变公开函数签名、schema `/1`、canonical bytes、record_digest/content_ref、构造次数或认证边界。

1. **优先替换 `domain.codec._decode` 的重复分组hex校验。** 实际完整readback在校验118,841,892字符的既有hex时刷新至最终峰值7,319,108KiB；见成本分析窗口数据。具体候选是非分组单字符重复校验 `[0-9a-f]*` 加偶数长度检查（或有界chunk扫描），严格保留原语言：空字符串可表示空bytes，只接受小写ASCII十六进制且偶数长度，拒绝空白/大写/奇数/Unicode近似字符。原matcher/decoder意外异常仍传播；不靠宽松bytes.fromhex单独准入。两个正则语言/长度条件等价，但内存/速度及错误/异常合同仍需未来双解释器实证；本次没有替换或试跑新产品算法。
2. 用精确 canonical byte writer/typed token packer 直接产生已规定的 UTF-8 JSON token，减少 `_pack`构造wrapper及 `freeze → _wire → 完整 JSON对象/hex字符串 → json.dumps → utf8` 的同时存活中间树和重复深拷贝。输出使用内存buffer/chunks（无文件IO），完整 Result 最终仍返回完整 bytes。bytes 逐块写 lowercase hex，避免额外整块hex字符串；排序、字符串escape/Unicode、rational、NaN/Inf、duplicate-key/非规范表示拒绝规则逐字节保持。不改变公开freeze的防御复制语义；不得对普通外来mapping/list直接省略防御快照，单次集合快照及typed scalar规则要作为writer输入合同保留。已严格检查的内部不可变DTO按完整spec逐字段直接写token，避免先构造再逐层freeze等价的临时map。
3. 优先优化所有调用共同经过的 canonical操作，再考虑 encode-only 的 operation-local memo。memo只能缓存**本次编码中已经严格验证的同一个不可变对象的编码结果**，持强引用，key包含 exact type、schema/codec版本及对象identity；操作结束释放，失败清空。不使用进程全局缓存、不以Python hash/摘要相等代替内容/角色认证、不跨run/输入重用。memo不能增加公开 trusted/cache 标志，不能改变 `_require_input`、`_evaluate` 或公开constructor/decoder实际认证次数。若严格图检查发现可变别名或外来等值scalar，必须先拒绝；保持现有公开encoder对不合法DTO的拒绝边界。
4. 如 reader 仍由 JSON DOM/多次 freeze 主导，采用分块 hex 解码与更少中间复制；任何 streaming canonical校验仍须拒绝非规范顺序、重复key、wrong tags、缺漏/多余field、错误数字及错型等值scalar，最终重入公开constructor。不得用“digest相同”替代解析/来源/重建认证。

A 的评审门：先为现行 `/1` 制定跨进程逐字节对照（原wire/hash仍相同），原公开负例与异常探针不动，三条完整路径按冻结计划验证。writer实现细节需开发新增/受影响检查；最终冻结双全量、typing、包/干净安装。若发现保证这些合同需变更任何可观察行为，停止该子项，带实例交 PM，不把调查建议当批准。memo是次选，若输入图扫描/持有临时bytes造成退化可不采用，仍需交完整测量证据。

## 格式工作包 B（待 PM/用户决定，不随 A 自动实施）

建议针对新的完整 Result exchange 增加自包含、有界的 typed record table 格式，使相同下层证据按引用复用，且不要将完整下层 JSON bytes 再作为上层hex。示意而非已批准schema：

```json
{"wire_schema":"layauto-channel-identity-wire/2",
 "root":{"record_ref":"r0"},
 "records":[{"id":"r0","type":"ChannelIdentityResult","fields":{"input":{"record_ref":"r1"},"value":{"record_ref":"r2"}}}],
 "captures":[{"uri":"source.gds","sha256":"<actual-byte-sha256>","data":{"$bytes":"<original-byte-hex>"}}]}
```

此示意省略展示的fields在真实格式中**必须完整**，不能缩减 `completed`、semantic/source/target、readback/checkpoint或任何捕获。table对每个节点保留完整exact type、版本、字段、来源/owner/run关系。canonical顺序从稳定内容/路径规则定义，不能依赖地址、Python hash、访问顺序或随机编号。相同bytes允许blob复用，但 `(uri, sha, role, location)` 是不同的来源记录；角色相同hash仍逐角色验证。records必须自包含，不要求外部repo、文件或在线解析；拒绝缺失/外来/重复记录、错误ref种类、循环、不可达额外记录及超限展开攻击。

B 的兼容与digest决策必须具体确认：

- 当前 `layauto-*-wire/1` 闭合decoder不能静默接受 `/2`，旧decoder保持拒绝。建议新显式 `/2` codec入口，原 `/1` encode/decode和默认 `record_digest` 原样保留一段明确兼容期；默认何时改版由 PM/用户决定。新version不仅更改外层schema，还要定义所有内嵌table节点的type/version registry及升级关系。
- `/2` 实际 bytes改变，其 SHA-256 必然改变；不能把新hash写入现有 `/1` record_digest字段再声称旧refs稳定。建议区分 exchange-wire hash 与原内容ref算法；若最终要求 `/2` 成为 canonical content，则逐类发新内容身份版本、明确旧→新映射和历史readback/repo迁移。尤其 `publication_codec.content_ref` 绑定实际编码，若触碰其格式会影响 parse/tool/evidence/checkpoint/RunRequest和幂等关系，不能在本工作包顺手变更。
- 推荐 B 初期不改 publication `/1`、运行请求或原持久化ref；table中保存/验证原来源事实和旧ref。完整Result编码方式与底层semantic/layout/ref算法分别决策，不默认geometry/local/channel refs或semantic_digest都不变。对这些ref逐项给原值/新值对照，即使物理语义相同也不能推定内容身份相同。
- 需交用户的实例：相同 normal direct 结果，旧接收方只识别 `layauto-channel-identity-wire/1`，收到 `/2` 将拒绝；旧 `sha256(encode_record(result))` 与新exchange hash不同；跨run但raw bytes相同的两个readback对象不能合并run关系。PM须决定新格式的公开范围、默认/兼容期、存储身份和迁移策略。当前没有这些批准。

## 不推荐先做的认证复用/结构精简

实测中重复重建是重要成本，但不能删除公开验证或以可信标志跳过。`test_w011_exceptions.py:105–126` 明确要求 builder/constructor 第二次 `_require_input` 发生意外失败时，原异常object/cause/context/suppression不变；简单删除第二次认证会使该路径不再抛出原失败。A 保留该调用和重建边界，通过降低每次序列化成本获益。若后续仍需减少认证本身，必须另行给“原第二次decoder/认证故障→新行为”的反例、完整private context key/失效及故障语义，交PM按关键行为规则决定；本方案不预批。

同理，不把完整捕获改成摘要/中立draft、不删除readback审计副本、不改变body/U06/来源owner和FIN物理解释、不靠热缓存或少跑测试达标。

## 回归、攻击面与实施验收

- A 保留现行全部字段/type/来源验证与 `/1` byte/hash，对外来等值bool/int/Fraction/scalar、伪造source参数的未测轴、derived lexeme、跨捕获拼装、6个owner混用、URI拼写、缺漏completed/audits、跨run/revision/checkpoint、可变alias、单次集合快照均跑原负例。
- 预期错误后第二次故障及各层decoder/validator的 ValueError/TypeError/KeyError/KeyboardInterrupt/SystemExit 保留原object/cause/context/suppression；不捕获并重包意外异常。原局部图、T05 violation独立于物理edge、外部body范围、partial/未知测量、重复/重叠FIN、target-only差异均不变。
- B 额外攻击面：table/type混淆、循环/深度/展开bomb、alias/mutation、排序不确定、hash碰撞或错ref/角色、合法blob外置到不可信路径、漏捕获、跨版本误用。decoder须建立完整有界不可变图，再经既有公开认证；不能因为table ref能解析就称来源已认证。
- 前后测试用同一Python依赖、固定绝对URI、RunRequest、cache、保留roots与GC顺序。开发时新增及受影响；最终冻结双全量/typing/构建和双安装，并串行三条完整路径独立baseline/profile。性能目标以至少三次有限串行样本的中位数和各次峰值复核；原次和失败全保留，任何单条退化单列，不以平均掩盖。三次是未来实施目标验证，不要求本调查机械重复。
