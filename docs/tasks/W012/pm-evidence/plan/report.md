# W012 PM 只读方案专项

审查版本：`/workspace/Layauto`，分支 `codex/w012-capture-wire-performance`，HEAD `5085f994f0bd4b0c39f7ac1ccdbcacc43d281720`。开始时工作区干净。只读核对根 AGENTS、README、协作/远端环境规则、W012 任务与成本/实施/独立 review 原文，以及必要架构、公共 codec 和异常合同；未改仓库、未跑产品测试或重型测量。报告写在仓库外。辅助只读专项 `/root/w012_plan_check/codec_boundaries` 未参与被审方案设计。

**必须修正项 0。** P1/P2 的接收边界明确，现有方案足够支持 PM 在接收调查和独立 review 后继续准备并派发兼容优化；不能把当前调查交付冒记为优化实施、性能验收或全任务完成。以下是后续派发建议，不是追加到本轮 P1/P2 的阻断 finding。

## 1. 授权与 PM 可继续推进的范围

`docs/collaboration/rules.md:64–71` 明确：既定要求内的实现选择、可逆修复和原目标内技术问题由执行/review/PM 处理；新增关键对外格式/行为、能力承诺、验收标准或架构合同才交用户决定。用户已经要求优化完整捕获、wire 和重复重建；不能因为执行者本次只获派 P1/P2，就将“PM 接收后继续 A”重新变成用户许可门。W012 任务 `:34、44、52、60` 要求的门是先调查、独立方案 review、PM 明确下一次派发，当前仍须由 PM 更新允许写入及实施范围，执行者不能自行突破本次只读产品边界。

| 可由 PM 继续具体派发 | 范围及前提 |
| --- | --- |
| A1：hex matcher 最小修复 | `layauto_v2/domain/codec.py:109–112`；只换等价校验，保持 `/1` wire、所有 digest/ref、公开验证、异常透传及最终 canonical 重编码检查。 |
| canonical writer / typed token packer | 可以作为后续内部实现子项；先明确通用 `freeze/canonical_bytes` 与已验证 DTO 快路径的输入边界，再独立 review 字节等价、防御快照和严格类型。不能把 writer 的建议当成已具备可直接合入的实现细节。 |
| 减少 reader 中间复制 | 以 A1 后 profile 为依据；公开 malformed/canonical 拒绝语言、完整构造和认证保持。分块实现及 buffer 选择属于内部算法选择。 |
| encode-only、单次操作 memo | 仅缓存本次已严格检查的同一不可变对象编码；完整 exact type/schema/codec 版本/identity key、强引用、失败清理和操作结束释放；不得跨 run、跨 encode 或替代角色/来源/公开验证。须证明扫描与缓存保留没有抵消收益，可不采用。 |
| 有证据的原 bytes 存储复用 | 可以调查但低优先级；不能合并不同 URI、role、owner、run 的记录。当前已测重复原 payload 只是 MB 量级，不足以单独解释 GiB 峰值。 |

整包 A 不允许改变 public signature、`/1` canonical bytes、`record_digest/content_ref`、公开 constructor/decoder 的构造和认证边界。`implementation-proposal.md:7、11、14、38` 已写明这些条件。反复认证本身虽贵，也不能简单删第二次认证；`tests/contracts/test_w011_exceptions.py:105–126` 有“预期错误后二次认证失败仍抛原异常 object/cause/context/suppression”的具体合同。若优化必须改变这类可观察行为，先交 PM 带实际前后反例归类；关键行为改变按规则交用户决定。

## 2. 建议先派最小 A1，按结果决定后续 A

证据强度支持先做 A1：`cost-analysis.md:76–86` 将完整 readback 最终 `7,319,108 KiB` HWM 刷新定位到既有 `118,841,892` 字符 hex 的原 matcher 调用窗口；调用前当前 RSS 约 `340,640 KiB`。这证明该窗口值得优先修复，不等于已逐项测清 regex allocator，也没有对 direct/mismatch 做同样窗口诊断。完整 writer/memo 同时牵涉快照、排序、escape、typed scalar 和多层 `_pack`，扩大审查范围而不利于区分收益来源。

建议下一阶段只准入 A1，runtime 首选只改上述 codec matcher，新增相应合同负例/等价检查与证据；不同时重写 writer、加 memo、改构造/认证。原语言是 `[0-9a-f]` 组成的偶数长度字符串，含空串；`re.fullmatch('[0-9a-f]*', raw)` 加偶数检查是可审阅候选。拒绝大写、空白、奇数和 Unicode 近似字符；`bytes.fromhex` 会接受比原语言更宽的输入，不能单独作准入。实施可保留先 matcher 后长度检查，避免新短路无意遮蔽 matcher 故障探针；不要顺手把原 `isinstance` 改成新的 type 准入。任何候选的速度、内存与双解释器行为仍须实测。

开发检查应围绕新增 hex 语言边界、原 codec canonical/duplicate-key/错误探针，并按共同 codec 消费者选择 W005–W011/publication 的受影响来源、类型、roundtrip 和异常回归；无需每次迭代机械跑全部重型矩阵。最终在冻结源码/测试/配置上做用户已确认的双解释器全量、typing、构建及干净安装；公共 codec 改动不能继续采信旧 W011 全量作为新源码最终结果。

性能验收仍以三条完整路径为单位：保持原绝对 URI、captured bytes、RunRequest、cache 模式、GC 和全部 retained roots；保留完整来源/36 FIN evaluations、正常 5/7、mismatch measured4/source5、一项差异、局部图/T05/body、readback attempt/checkpoint 和完整 DTO 恢复。逐字节 `/1` 对照与既有 wire hash 应不变，wire 降幅为 0。先做有限新路径验证与 independent correctness/performance review，再决定是否展开 writer/reader/memo；不为追数字自动扩大 scope。

## 3. 20% 时间、50% RSS 的处理

`cost-analysis.md:92–98` 已正确将它们标成有依据但尚未验证的建议：20% 来自约 51–52% codec self-time 与假设可消除部分工作的推算；50% 来自 readback 窗口的瞬时峰值空间。它们不是新算法实测，不是生产/最大输入资源上界，也不是已批准产品承诺。

PM 可以把这些数字保留/采用为后续兼容 A 的内部努力目标或可行性检查点，无需只为普通实现继续与内部目标再问一次用户；若要将其升格为对用户的新硬性验收承诺，则须按协作规则具体说明依据和影响后决定。最小 A1 的完成标准宜是语言/来源/异常/字节合同保持、三路同条件测量有明确结果；A1 可能只解决主要内存峰值，不能先断言时间也会降 20%。若只达内存改善，按子阶段实际成果接收并继续剩余优化，不将整个 W012 标为完成，也不改动既有正确性标准凑达标。

实施比较至少对同一受控环境做前后各三次 fresh、串行、无插桩完整路径，以各路径的中位阶段总计和逐次整进程峰值复核，逐路径披露退化。P1 的一次 baseline 足够作调查依据，但不能把“未来三次 after 的中位数 / 旧一次 before”描述成稳定统计收益；未来必要复测应与实现合并安排。profile/窗口诊断单独运行，只作归因。报告当前无新的性能实测。

## 4. B 真正需要用户决定的内容

新自包含表格式可以继续作具体方案设计、静态兼容矩阵或离线原型研究；这不授权直接增加或切换产品公开格式。用户决定材料应收敛到实际可观察差异，而非泛问“是否同意优化”：

1. **公开范围和默认行为。** 新 `/2` 是显式 opt-in exchange 入口，还是替换既有 `encode_record/decode_record` 默认；哪些组件开放、`/1` 支持期和默认切换时机。当前 channel decoder 在 `channel_identity_codec.py:146–153` 明确拒绝 `/2`，不能静默放宽。旧接收方收到新 wire 将失败，这是明确的兼容变化。
2. **wire hash 与内容身份。** 新 bytes 改变实际 SHA-256；现有 `record_digest` 直接 hash encode 输出（同文件 `:157–158`），`publication_codec.py:133–143` 又把 digest 进入 `ContentRef(kind,run_id,digest)`。必须决定新 exchange hash 是否与旧 canonical content identity 分离；若更改底层 semantic/geometry/effective/local/channel refs，逐项说明版本、旧/新值和消费者影响，不能凭物理语义相同推定 ref 不变。
3. **历史 readback/repository 与幂等关系。** 决定 `/2` 是否进入 repository 持久化以及既有 records/refs 的读写、旧→新映射和迁移策略；publication、RunRequest、parse/tool/evidence/checkpoint 身份是否完全保留。推荐首版新格式显式可选，维持 publication `/1`、原 request/ref 和原默认 digest，以控制迁移范围；这是待用户决定的具体推荐，尚非产品批准。

建议给用户同一个 normal direct 的 `/1` 与拟议 `/2` 样本、旧接收方拒绝示例、exchange hash/各类 ref 前后表，再给“跨 run 同 raw bytes 仍保留各自 run/owner 记录”的例子。当前仅有示意 schema，未完成完整 schema/原型 benchmark；不能把 `20MB/45MB/20MB` wire 建议当作确定可达或已批准验收线。完整捕获、sources/completed/readback、exact type/owner/run/role 不可删，自包含、确定性排序、无缺失/循环/多余/展开攻击仍是技术正确性义务，不应让用户替开发决定这些必要防线。

## 5. 给 PM 的具体下一步

先按 PP1–PP5 接收本次调查及剩余 findings=0 的独立 review；记录“P1/P2 已接收、优化未实施”。随后在既有 W012 下明确一个 A1 实施阶段及允许写入范围，指派执行/独立 review，维持“开发新增/受影响、最终冻结双全量”的既定安排。A1 实测后继续判断 writer/reader/memo 的必要性，保持完整 wire/重复重建仍有待处理的事实。B 另备上述具体用户决策材料，不让它阻塞 A1，也不由普通内部授权自动推出新公开格式或身份迁移。
