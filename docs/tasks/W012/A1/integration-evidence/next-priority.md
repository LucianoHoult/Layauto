# A1 集成后的唯一近期优先项建议

建议在 A1 实际合入 main 并完成组合验证之后，**先收敛兼容 A2 的具体方案与独立方案 review，再决定实施；本次不直接回 M1 网络标注实现，也不启动 A2 产品实现。** 这项建议只形成近期规划，不是 A2 派发或新格式授权。M1 仍是产品主线，A2 准备是为减少已经实测的完整路径成本，不构成一个新的产品里程碑。

本次只读恢复到 `/workspace/Layauto` 的 `codex/w012-compatible-hex-validation@1a1459e3179e7bd234e4971c1969a6a78f387fd2`，初始工作区干净。已读 AGENTS、README、协作规则、current-work、roadmap、W012 要求/PM 决定、成本分析/实施建议、A1 性能分析/数据摘要及合并前 review，并回查 architecture §3.6–3.7、§5.3–5.8、§11.15。未运行产品、测试、benchmark 或 profile，未改仓库；此文件是仓库外的 PM 辅助建议。A1 的最终 main 集成状态由负责集成的 PM 记录，本建议不预报其完成。

## 实际数据支持的取舍

| 完整路径 | 同机三次中位总秒 before→after | 整进程峰值 KiB before→after | 完整 wire B |
| --- | ---: | ---: | ---: |
| normal direct | 94.419→75.800（降19.72%） | 2,851,076→325,436 | 54,050,313，未变 |
| normal readback | 186.625→144.067（降22.80%） | 7,344,896→708,536 | 136,471,701，未变 |
| extraction mismatch | 93.170→79.514（降14.66%） | 2,860,516→324,668 | 54,045,042，未变 |

来源：`docs/tasks/W012/A1/performance-analysis.md`、`performance-summary.json`。总秒是每个样本的各阶段之和再取中位，不能把各阶段中位相加。708,536 KiB 约 692 MiB / 0.676 GiB；这些是有限 synthetic 输入的整进程高水位，不能当成生产/最大输入上界。合并前 review 已通过且新增/剩余必须项均为 0；它支持集成 A1，不等于 W012 整体完成。

A1 已解决定位到的重复分组 hex matcher 瞬时峰值；65 个大 hex 调用的顺序/长度和公开构造、认证、codec 调用次数保持。最大的窗口不再刷新 HWM，但 readback 仍需约 144 秒，且完整 wire 仍 136.5 MB。A1 后 readback 的单阶段中位为 W011 build 51.427 秒、完整 decode 66.115 秒、外层完整 encode 2.616 秒（仅作阶段定位，不相加冒充总秒）。因此只优化外层 encode 无法用这 2.6 秒证明充分收益；应优先检查 build/decode 共同反复经过的编码、freeze 和下层完整重建路径。

P1/P2 原调查进一步说明：31 份原始捕获总计 280,706 B，readback wire/raw 为 486.17 倍；原对象及 decode 后 bytes payload 的已测重复只是 MB 以内到约 1.8 MB，不是 GiB 峰值的解释。外层 hex 字符占 readback wire 99.9465%，其中主要是完整下层 wire 被再次按值嵌入，不是原捕获本身占了全部空间。原 profile 的 W011 build 内 `_require_input` 累计占比约92–94%，其自身 exclusive 很小，成本在包含的下层 codec/重建；这些累计时间相互包含，不能相加。该 profile 有插桩扰动，不能当 A1 后无插桩的函数耗时预测。

因此下一项应先解决“保留完整认证时，怎样降低每次经过序列化路径的工作量”的方案可行性。少跑测试、互斥 gate 和原始捕获去重均不能替代这项问题。

## 与直接回 M1 网络标注的比较

直接做网络标注会推进 R06/R07/R12，且已有 W007 语义/identity seeds、W009 effective regions、W010 local graph、W011 channel identity 可承接，A1 后内存已显著降低，**没有证据证明 A2 是网络标注的功能硬依赖或目前无法运行标注开发**。

不过，网络标注仍需按 architecture §5.3–5.8 准备 fragment/region target、net_xref join、exact/quality-aware 匹配、coverage/conflict/unknown、component-to-net summary，以及来源/有效性边界；它不会自然减少当前完整 Result 的嵌套按值 wire 成本。继续扩大状态链可能增加既有重复序列化负担，但本次没有新测量，不宣称增长幅度或预定 OOM。当前用户明确关注测试太慢及单次完整捕获/wire/重建成本，144 秒的残余成本已实测，故先做一项有边界的 A2 方案收敛比直接扩展状态链更符合当前优先级。

这一排序不能被解释为无限期推迟 M1。A2 准备的交付点是可执行的兼容方案或明确不可行/收益依据不足的结论，经独立方案 review 交 PM 处理；若无法在既有边界内给出可核验方案，回 M1 网络标注，不自动追加格式、认证复用或泛化优化任务。网络标注本身完成后，M1 仍需外部 body/完整坐标、其余 mandatory/lifecycle、原子 baseline、extraction-aware no_change 及 Stage 6 产物/terminal，不能据此宣称闭环完成。

## A2 近期准备应收敛的内容

唯一近期项为“兼容 A2 方案收敛及独立方案 review 准备”。不在本轮同时立网络标注实施任务，不擅自命名新的已派发任务编号。

1. 依据现有 A1 后 profile 和静态调用链，圈定 common canonical writer/typed packer 如何减少 `_pack → freeze → _wire → JSON/hex → UTF-8` 同时存活的中间树与重复复制，列出实际涉及的 producer/consumer；避免只优化最后一次外层 encode。先核旧方案在 A1 后仍成立的事实及尚未归因部分，不机械重跑重型调查。
2. Reader 的 chunk hex/少复制仅在现有数据足以说明相应成本且能保持完整 canonical 检查时纳入同一方案；不把 writer、reader、memo 当成三个并行必做包。优先收敛最小共同路径；operation-local encode memo 是次选，需证明同一已验证不可变对象、exact type/schema/identity、持强引用、结束/失败释放，以及无可变 alias 绕过。当前不批准任何 memo 实现。
3. 明确原 `/1` canonical bytes、digest/ref、公开 signature、全部来源/owner/run/原始 bytes、公开 constructor/认证的调用和重建边界都保持；公开 freeze 的防御快照、错型等值 scalar、单次集合快照及意外异常传播保持。第二次认证故障是已有可观察合同，不能为提速删掉第二次认证、加 trusted 标志或改 catch 行为。
4. 给出与 A1 集成版本对照的验证计划：同固定 URI/RunRequest/输入/cache/GC/retained roots，完整 direct/readback/mismatch，逐字节核 wire/hash，独立无插桩测量与诊断 profile 分开；开发新增/受影响，最终实现若另获派发仍按冻结源双全量/typing/构建/干净安装。单路径退化单列，不以平均遮蔽。最终前后样本条件不匹配时旧 A1 数值只作历史参照。
5. 先交 owner/范围、错误与来源不变量、可证等价方法、风险、测量/工程成本、建议验收方式及其数据依据，经未承担设计者 review；之后才由 PM 决定是否派发具体实施。旧兼容包20%/50%只是未批准的整体建议，不能成为 A2 硬门；本次也不另设任意耗时/内存预算或承诺收益。

## wire 限制与禁止暗含的决策

兼容 A2 保持 `/1` 逐字节相同，所以 **wire 降幅必为 0**。它最多减少产生/校验同一 wire 的时间和临时空间，不能向用户承诺解决136.5MB大小。需要减小 wire 时必须另行形成 B 的具体自包含表示、公开入口/默认兼容期、exchange hash 与内容身份、publication/ref/历史迁移材料后决策；本建议不启动 B，也不让 B 变成 A2 的前置条件。

剩余约700MiB profile 峰值在最后 matcher 观测窗口后刷新，尚未逐函数/allocator 归因；不能将它全归给 JSON、重编码或某个 constructor。P1/P2 profile 数值、A1 profile 单次 decode 221.044→222.850秒与无插桩三次结果均须保留原限制，不混成新承诺。

可供 PM 对用户简报：A1 已把 readback 峰值从约7GiB降至约0.68GiB、完整路径耗时从187秒降至144秒，但136.5MB wire和重复重建保留。建议下一步只收敛保持现有格式及验证合同的 A2 方案，独立 review 后再决定实施；M1 网络标注随后承接。当前不启动新格式，也不预设收益门。
