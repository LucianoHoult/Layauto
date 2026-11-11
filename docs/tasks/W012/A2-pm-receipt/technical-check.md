# W012 A2：PM 专项技术接收判断

日期：2026-11-11 UTC。检查者：`/root/a2_plan_technical_check`。受检仓库 `/workspace/Layauto`，分支 `codex/w012-a2-serialization-plan`，HEAD `71488d6034b40cb67970466b082298a8dc0d5eee`；开始时 staged、unstaged、untracked 均为空。

## 结论

**技术上可以接收 AP1–AP5 的方案交付，并另派一次 W010/W011 两 encoder 的有限实施。未发现要求退回方案的实质必须项。** 方案已确定 owner、入口、字段/分派算法、快照时点、旧→新完整字节等价方法、认证与异常防线，不需要实施者重新决定格式或删减认证。此次结论不是不存在的产品 diff 验收，也不证明完整路径已获得性能改善。

这个推荐只支持现有两处 closed encoder 的操作内私有 pack helper 与调用点，以及必要的正式合同对照、测量/工程证据。不能由此自动扩为 writer、reader、memo、下层四 codec 的改造、B 新格式、跨操作缓存或 `trusted` 参数。完整收益未知，但已有真实调用链和临时构造机制足以支持这样一个可随完整筛选结果停止的最小实施；没有必要为方案阶段再运行小时矩阵。

## 实际读取与检查

- 启动/规范：根 `AGENTS.md`、`README.md`、`docs/README.md`、`docs/collaboration/rules.md`、local-setup、remote-development；检查目标树未发现额外局部 AGENTS。读取 Cloud runtime 技能并核当前环境 running、observations_current=true、网络 enforced；未安装依赖。
- 要求/交付：W012 任务的当前范围、A2 边界、PM4/PM5、AP1–AP5，`A2-plan-prompt.md`，A2 的完整 `plan.md`、`independent-review.md`、`delivery.md`、`reference_pack.py`、`check.py`；读取 `check.command.json`，解析 `check-result.json` 的有限见证和计数。
- 规范架构原文：§2.2–2.3、§2.6、§3.7–3.8、§11.2、§11.9、§11.15，尤其 exact 输入/原 bytes/来源、递归防御冻结、持久记录 canonical schema 与 content identity、模块依赖边界。
- 实际源码：`domain/codec.py` 全文；`domain/regions.py` 的 `validate_closed_graph`；两目标 codec 全文；W010/W011 normalization builder/Result constructor 全文；publication/semantic/geometry/effective codec 的 `_pack`、`_unpack`、encode/decode 与 captured constructor 异常边界。
- 正式合同：`test_w011_exceptions.py` 全文；`test_w011_contracts.py` 的全字段 roundtrip、完整重建、alias/closed、wire 字段、capture forgery、CR01/CR04 用例；W009 `ChangingList` 单次快照用例。另用 `rg` 搜索正式 tests 对 FrozenMap/freeze/_pack 的故障注入，命中的 capture.freeze 用例属于公开捕获流程，未找到依赖这两 encoder 第 N 次私有 wrapper 分配的既有测试。
- 轻量只读数值核：用标准库解析 A1 九份 after 性能 JSON 与真实 readback after-profile，复算三路阶段中位，提取两 encoder 实际调用次数；读取 `measurement-plan.md`。没有运行 A2 check（它会写原结果）、pytest、完整 build/decode 或 benchmark，没有改仓库、commit/push。

263 项证据身份和交付封存由另一 PM 专项核验负责；本报告不重复全量逐项 hash，不把自己未读的旧安装树或完整大 wire 宣称为本轮已核。

## 最小方案为何足够具体

两个现有 `encode_record(record: object) -> bytes` 都先做根 `_SPEC` exact type 检查和原图 `validate_closed_graph`，之后才 `_pack`。现有 `_pack` 为 record/fields、tuple、map、scalar 和 delegate 标签创建 `FrozenMap`；其 constructor 递归 freeze 已打包子树，父 wrapper 又重复这个过程。方案只把 envelope 内的 `_pack(record)` 切换为新私有 helper；旧 `_pack` 继续服务 `_unpack` 的完整重建值核对。

方案逐项固定了本次算法：沿原 `_SPEC` 字段次序 `getattr` 递归，沿原 delegate classes/tag/encoder 顺序调用原 encoder 得到完整 bytes；exact FrozenMap 叶在原分支时点立即 `freeze(value)`；tuple 当场物化；scalar 使用原 `freeze`；操作自建 dict/tuple 最终进入未变 `canonical_bytes` 的全树 freeze、`_wire`、json.dumps 和整体 UTF-8。没有 asdict、反射发现字段、摘要替代、按 equality 准入或延后保留 caller map 指针的空白。

虽然新 helper 返回 `object`，这里的 typed pack 指沿现有 exact registry 和固定标签进行分派，并不是另建公开 DTO/schema。两个 owner 各自复用原 registry 是合理最小范围。多一个私有算法会有漂移维护成本；未来定向测试应覆盖 registry 全字段与各 delegate 分支，不能用拆通用框架来扩大本次实施。

## 为何能够作用于 build/decode

实读代码确认 W011 builder 先 `_require_input`，其中做 W010 完整 encode→decode；随后 W011 Result constructor 再 `_require_input`、`replace(self.value)`、`_evaluate`，并用 channel encoder 比较完整 draft。decode 也不是只做 JSON 反序列化：domain canonical 检查之后，`_unpack` 逐层进入公开 constructor、原 `_pack(result)` 比对和尾部 `encode_record(result) == data`。因此两个 encoder 是 build/decode 内的共同路径。

真实 readback after-profile 的 W010/W011 encoder 调用分别为：build 30/2，decode 95/3，最终 encode 14/1。A1 无插桩 after 三次中位 readback build/decode/最终 encode 为 51.426606/66.114896/2.616473 秒，direct 为 27.860428/35.128253/1.422533，mismatch 为 28.757855/37.506055/1.458006，均与方案一致。方案确实没有只依靠最后约 2.6 秒的外层 encode 推断整体改善。

这些调用次数只证明候选可达。原 profile 无完整 caller 边，不能从全部 domain freeze/map exclusive 的 89.925018/114.519416 秒中划出这两个 owner 可省份额；其中大量工作属于保留的公开快照、lower codec、decode 和重建。插桩 exclusive 也不是无插桩 wall 可省秒数，嵌套 cumulative 不能相加。W010/W011 编码虽反复出现，保留的 lower 重建仍可能主导成本。

## 可删的纯临时构造与必须保留的验证

| 允许减少 | 不得据此删减 |
| --- | --- |
| 两 encoder 的私有标签 FrozenMap wrapper，以及父 wrapper 对已 pack 子树的重复 freeze/map/tuple/Fraction 副本 | 公开 FrozenMap/freeze/freeze_map/canonical_bytes 实现，公开 DTO constructor 的防御快照，最终 canonical 完整 freeze |
| encode 私有构造中已经消失的第 N 次 allocation；机器资源耗尽阈值不能承诺完全相同 | 公开故障边界、原异常对象/cause/context/suppression、既有正式故障注入与第二次认证测试 |
| 只在本操作存活、没有对外可写别名的自建 dict/tuple | domain.decode 的 FrozenMap/规范重编码，所有 `_unpack` 公开 constructor，旧 `_pack(result)` 比对和最终原 bytes 实比 |

W011 Result 的 `_require_input`、`replace(self.value)`、`_evaluate` 和 draft/semantic/issues/completed 完整核对都位于此次替换点之外，方案明确保留。W010 及其下游 capture 核源也保留。第二次认证并非可疑冗余：正式用例在第一次预期 ChannelProblem 后，明确要求第二次 `_require_input` 故障发生并保留原异常历史。方案未增加 catch/rethrow/translation，也未移动原预期错误 handler，故有明确静态保持依据；未来仍必须跑这些正式回归，不能把本轮 BrokenMap 私有小值见证称为已运行公开异常链。

原图 closed 检查必须在任何 fold/copy 前；它按 exact 类型拒绝 text/DTO/Fraction 子类、equal-object 和可变集合。叶 map 的即时 freeze、tuple 的立即物化与公开 constructor 的单次集合快照位置保留，因此新 owned 树不会成为减弱 alias 防线的理由。W009 `ChangingList` “验证并保存同一次迭代”的合同不在本次改动内。

## 字节、来源与接口保持

本方案的结构归纳可成立：record 同 exact 类和全部字段，delegate 同调用顺序及完整 nested bytes，map/scalar 在原位置快照，tuple 同序递归，最终由同一个 canonical 算法编码。需要保持的是含原生类型/标签的完整树及完整 bytes；仅 `freeze(new) == freeze(old)` 不足以区分 Python 的 bool/int/Fraction 等值，方案已同时要求完整字节对照。

未变的 `_wire`/json.dumps 继续拥有 map 排序、escape、无 Unicode normalization、rational 十进制串、bytes lowercase hex、大整数转换、最后整体 UTF-8 及其异常顺序。原 decoder 的 duplicate key、未知/缺字段、wrong tag、非规范 hex/rational/排序/空白/float 等拒绝语言不变。不得将结构/认证归约为“hash 一样”。

所有 schema/status/input/semantic/completed、原 capture bytes、URI 拼写、source location、run/owner/attempt/checkpoint 关系和完整 nested wire 都仍进入原字段；record_digest/content_ref 仍由原完整编码计算。因此兼容性必须表现为 `/1` bytes、长度、所有 hash/ref 和公开签名保持，wire 降幅为 0。不是新格式提案，不需要实施者另定迁移合同。

## 小值依据、限制与 PM 可派发验收

交付中的六个真实小 root 既有完整 old/new 字节对照又交原公开 decoder 重建。例：SeedLocation freeze263→91、FrozenMap init151→43；ContactComponent290→91、169→41。这是 cProfile 调用次数见证，**不是候选产品微基准或完整收益**。22 个 private subvalue、surrogate 错误属性和 BrokenMap 异常见证帮助检查机制，但未覆盖全部 `_SPEC`、完整 Result、来源组合攻击或公开第二次认证。本轮标准库解析只是检查既有结果，没有重跑原有限见证。

新 dict 树与最终冻结树可能同时存活，lower codec/旧 decoder _pack/完整 DOM/hex/JSON/UTF-8 都保留；小值构造降低不能外推峰值降低或生产资源上界。方案明确了这些不确定性，足以作为“先有限实施，再由完整结果决定是否值得集成”的候选依据。

PM 可另行派发的最小实施/验收边界是：

1. 两私有 helper、两处 encoder 表达式、必要正式定向对照和证据工具；根 exact/原图 closed 检查、原 `_SPEC`、所有 delegate、旧 decoder `_pack`、公开签名与认证链不变。不得改 fixture/答案或删旧断言以过关。
2. 开发先覆盖新增/受影响的全字段分支、typed equality/closed、来源/run/owner、alias/单次快照、decoder 接受/拒绝、完整重建和既有异常/第二次认证合同，说明选择范围。
3. 先按方案做有限一组成对完整三路筛选；保持原 URI、RunRequest、cache/raw 核查、fresh repository、roots/GC 和阶段计时范围。若原输入身份不能复原，先建立同条件两侧新 baseline，不与历史数字硬比。完整 direct/readback/mismatch 全字段与完整 wire 逐块实比，所有 hash/ref/原功能事实保持；bytecmp 放计时外。
4. 值得继续时再完成方案既定两侧各三次 fresh 串行交替的无插桩 wall/RSS 前后比较，披露原次、失败、分路与整体结果及退化；额外 profile 单列。兼容性是硬条件，不添加新的任意百分比/资源预算。完整结果分辨不出改善或退化抵消收益时交 PM 决定不集成并回 M1，不能借机扩大候选。
5. 真正产品源码/正式测试/配置冻结后，按现有协作要求完成双3.10/3.12全量、strict typing、构建及双干净安装、源码外完整组合 smoke；相关源再变则定向修正后按新冻结完成最终矩阵。独立 reviewer 审产品 diff、证据和 findings，PM 再决定验收/集成。

这是既有 AP4 和协作规则的可执行化，不是新增性能门槛。本次 runtime/正式测试/配置无改，工程完整矩阵可以在另一专项核准同源后采信 A1，不能将该采信写成 A2 新算法已验证。

独立方案 reviewer 已报告 A2-R01 为交付 checker 输出生成顺序问题并关闭，剩余必须项 0；本专项没有重做其复现/封存，也没有代写其 finding 复核。最终封存、远端身份及 AP 完整覆盖仍须由 PM 证据专项核验后汇总。上述技术推荐不自动改变当前 task 阶段、main 或启动产品实施。
