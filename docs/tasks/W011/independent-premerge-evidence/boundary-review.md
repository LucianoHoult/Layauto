# W011 专门合并前 review：公开边界、来源和异常专项

Reviewer：本次独立 session 的 `/root/boundary_review`，2026-11-10 UTC；未参与 W011 设计、实现或正式测试编写。**本专项新增/剩余必须修正项 0**。结论只覆盖下述边界范围，由主 reviewer 汇总几何、工程证据和资源/集成判断，不代写 PM 验收。

## 范围和身份

受审范围 main `61775e8fde6e9ea247ec08a32067c44c3be48ff8` → 原分支最新 head `8452027e57fb1c58607640d7eb755b38ffc70716`，工作目录 `/workspace/Layauto-w011-review`。核对 `e89bdaa6a091f56cfaf7862dced7232d34e22514..HEAD` 的 `layauto_v2/`、`tests/`、`pyproject.toml` 无差异。本次 probes 运行的是最新 head 保留的冻结产品字节；PM 后续文档没有被记成新跑过矩阵的源码。

读取根 AGENTS、README、协作/本地/云端环境规则、W011 task/plan/plan-review/execution/code-review/PM receipt；回查架构 §2.3、§3.3、§4.5–4.6、§5.3–5.9、§11.2/11.5/11.9，W003/W004 来源和闭包要求及 W007–W010 组件合同。核查本次新 domain/annotation/derive/normalization、codec 与上游 `normalization/codec.py`、`component.py`、`domain/source_location.py` 的 main 起点 diff；无额外局部 AGENTS。没有修改产品、正式测试或 fixture/答案。

## 本次实跑

使用现有 `/workspace/.venvs/layauto/bin/python`，Python 3.12.14，`PYTHONPATH=.`，禁 bytecode/cache。命令、文件 hash 和冻结源关系见 [boundary-receipt.json](boundary-receipt.json)。三条命令均 exit 0：

| 实跑 | 结果和边界 |
| --- | --- |
| [boundary-probe.py](boundary-probe.py) | 57 项检查通过，11.659s，整进程 `ru_maxrss=33,676 KiB`。其中 W007 16 类真实 exemplar 的 576 个 field/type 对照为 560 项明确 ValueError、16 项合法/可选变化接受，无非 ValueError 的 malformed 形状泄漏；所有接受项逐条保留，不把它们算成非法输入拒绝。 |
| [boundary-owner-probe.py](boundary-owner-probe.py) | 9 项检查通过，18.577s，整进程 `ru_maxrss=679,660 KiB`。真实 W005→W008→W009→W010 后构建中立 draft，normal 控制为 5/7；对两个 seed 的同位置矛盾 owner、未计量 NF 来源和完整性删除逐项拒绝。 |
| 原 W007 wire 边界回归 | `test_wire_rejects_unknown_version_fields_and_invalid_value_combinations`：**6 passed，106 deselected / 8.67s**。unknown schema、额外/缺字段、假 error、trailing bytes 与 float 原拒绝边界保留，见[原输出](boundary-w007-regression.stdout.txt)。 |

上述小型 probe 的 RSS 是各自整进程测量，不能当成完整 W011 Result 的资源数据或 W011 增量内存。没有跑新完整 W011 Result/readback codec、双完整矩阵、mypy、构建/安装、EDA 或资源 benchmark；原完整链异常回归按主报告核实的冻结源身份采信。

## CR-01–CR-06 复核

原 finding 与修后残留仍以 [code-review.md](../code-review.md) 为准；本专项未修改它们。

| 原 finding / 必须修正 P2 | 最终处置与本次独立依据 |
| --- | --- |
| CR-01，`f493233` 的 ChannelSeed 接受 opaque/source operands 错型 | `_field_locations/_seed_operands` 验完整来源字段、derivation/source arity、xref 共同 row、原 lexeme 与 exact vertices。实际 W007 seed 正常 roundtrip；原三类 metadata/record/xref malformed 均拒绝，再逐一替换所有 record/identity 的来源字段也均拒绝。关闭成立。 |
| CR-02，`f493233` 新 `semantic_record→Parameter` route 将意外异常转换为 ValueError | 上游 codec 去掉通用 TypeError/KeyError/AttributeError/UnicodeError catch；子项先解码，各 constructor 明确拒绝错形。新实跑在真实 source ParameterComparison wire 注入 TypeError、KeyError、AttributeError、UnicodeError、ValueError、KeyboardInterrupt、SystemExit，并分别带 suppression=false/true，共14条均保留同一对象和既有 cause/context/suppression。576字段对照及6条原 wire 回归证实 malformed 拒绝仍在。新完整 Result route 的原冻结矩阵证据另按身份采信；本次不冒称重复实跑。关闭成立。 |
| CR-03，`f493233` W007 expected admission/identity handler 内再次构造污染 context | `component.normalize` 将 error facts/Result 构造移出 handler。新独立临时输入分别改 source NF=2、xref MN0→UNDECLARED，并自行重算实际 header/closure hashes；控制分别为 UnsupportedFingerCount/UnknownDeviceIdentity。再于实际 `NormalizationResult`/`replace` 二次构造注入 TypeError、KeyboardInterrupt、SystemExit × 两种 suppression，共12条原对象/异常链均不变。此处实跑 W007 实际 cause，不把它宣称为本次 W011 全 Result 构造。关闭成立。 |
| CR-04，Python 等值错型叶；后续 completed canonical 漏项及未计量 NF source 投影遗漏 | 新值类型 `validate_members` 递归重构确切类型；Draft 完整重构 source/local/全部结果；Result 重入 supplied Draft constructor、比较完整 codec bytes，并对 completed/semantic/issues 使用完整 typed canonical 对比。新 probe 对 nested int/bool width、Fraction(source.line) 和调用方 list alias 均验证；真实中立 draft 的未计量 NF source line=999 与 Fraction(line) 均拒绝。再删除 comparisons/topology/locations 与一个 outside FIN verdict（**count保持不变**）也均拒绝。completed bool/int 与全 Result 漏 NF 的原完整实跑由历史最终修复证据和冻结矩阵支持，本次作代码增量核对。关闭成立。 |
| CR-05，`f436f59` wrapper 当 SourceRef；修后 pointer 被 operator path 覆盖 | `seed_source` 现解包 `record_id.sources[0]`，Missing/AmbiguousSeedChannel 保留来源 JSON pointer，message 含真实 record ID。原最终 `8917d38` 两个 seed 的 pointer 解析重跑、首次关闭撤回和修后证明均保留；本次静态核对修复仍在。缺失/多候选及 pointer 的本次几何专项另行实跑，不能用正常5/7替代此错误路径。 |
| CR-06，`c37eecf` 同来源位置 registry operand 与传入 owner 自相矛盾仍接受 | `_owners` 同时比较声明 canonical bytes 和 URI/SHA/JSON pointer。新 probe 在两份实际 seed 中分别把同位置 registry operand.target_layer 改为 METAL，保留 path/SHA/pointer、同步3个同位置副本；ChannelSeed 自身可构造，真实公开中立 Draft 分别明确 ValueError 拒绝，normal control仍5/7。说明是在中立 owner 交叉自洽边界拒绝，没有把捕获读取职责倒灌进 domain。关闭成立。 |

## 公开合同和来源认证的静态判断

`build_channel_identity` 只有一个成功 W010 input 参数；先对原对象 closed graph 检查，再经 W010 canonical codec 完整重建。W007 semantic 从该 input 的 GeometryInput.semantic_input 产生，caller 不能额外传其它 run 的 semantic。derived 从同一 tech payload 与 `tech.sources[2]` 构造；physical/drawn/rules/formats/units 的实际认证由保留的 W008–W010 捕获链执行。消费 FIN/profile/seed 操作及 model 参数 axes 另按具名常量核对；保留未消费声明。未见凭文件名/owner名替代来源 payload/role 的新入口。

公开 DTO 为 closed/versioned，集合先单次复制后验证/保留，nested exact Fraction 和 SourceRef 在公共聚合边界重建。Result 不只比较投影或两个 count：先验证 supplied draft 的全部 source 参数，再比较完整 draft wire；同理 completed 的 boolTrue/int1 等值用 canonical bytes区分。`encode_record` 的 closed graph 检查与 `decode_record` 的完整 constructor 重建保持分工，没有宽泛 catch、发布或额外 IO。

上游改动范围有限：`normalization/codec.py` 保留 discriminator/字段集合/canonical bytes 对照，仅取消吞掉意外异常的通用翻译；`component.py` 保留 expected issue/progress，仅把二次构造移出 handler；`source_location.py` 增加 FrozenMap、缺 hash、非法 UTF-8 的显式 ValueError，SourceRef 继续验证所有定位 scalar。新 source_location 对照6项覆盖 plain dict、缺 hash、surrogate、bool/Fraction line 和错 field；均明确拒绝。没有证据表明这些必要修补改变已支持的输入语义或放宽原 malformed 拒绝合同。

## 限制与交接

本专项没有新增产品 finding 或修复交接。以上“关闭成立”综合本次独立实跑、最终实现检查与按冻结身份采信的原完整链证据；每条已标清实跑层级，不能将 neutral/W007 probe 等同完整 W011 Result/readback 矩阵。A1 的 W006 attempt/完整 captured 交叉拼装和 A6 全 nested W010→W009→W008→W007 例外矩阵由主 reviewer 对原1605矩阵及其来源身份进一步核实。资源成本与是否阻塞当前受限M1集成另由主报告独立判断。
