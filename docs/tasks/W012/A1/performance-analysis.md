# A1 完整路径前后实测

本轮只更换hex校验的内部条件；wire/1、公开函数、所有constructor/认证边界及完整捕获不改。具体方案先经独立review；产品/测试冻结`ca1f810c3c97376f71089d8b4054760ff198012f`，测量编排`d9d68475fefbeb420e738ad2ee5c2b6e92e7c5ec`。before为同机新测的原runtime，不使用P1/P2历史计时充当before。

环境为同一`/workspace/.venvs/layauto/bin/python`（3.12.14/PyYAML6.0.3）；性能venv未改，双工程环境另建。before导入`/workspace/w012-a1-before`、after导入本checkout，输入始终是原固定URI；35项mismatch输入逐字节按原清单重建/核对。RunRequest/cache/GC和所有保留roots严格沿用原计划；每次在fresh进程完整构造/encode/decode，三路径每侧各3次，按rep/case交替before/after且重型测量串行。profile与后续矩阵不重叠基准。

## 三次中位与全部峰值

秒为各实际阶段时间之和（获取/caller reads/W008/W009/W010/W011/完整encode/decode）；不含后续hash、原始wire保存/父进程bytecmp与分析。RSS是进程高水位KiB，不当函数净分配。每次原输出/源与工具身份/UTC命令均在[performance/](performance/)；原次和失败不覆写。

| 路径 | before总秒（r1/r2/r3） | after总秒（r1/r2/r3） | 中位秒 before→after | before峰值KiB（r1/r2/r3） | after峰值KiB（r1/r2/r3） | 中位耗时/峰值降幅 |
| --- | --- | --- | --- | --- | --- | --- |
| normal-direct | 94.419 / 91.868 / 94.423 | 75.800 / 75.681 / 80.278 | 94.419 → 75.800 | 2850796 / 2851236 / 2851076 | 325192 / 325520 / 325436 | 19.72% / 88.59% |
| normal-readback | 186.625 / 180.999 / 191.274 | 144.067 / 141.516 / 159.434 | 186.625 → 144.067 | 7344896 / 7344896 / 7321284 | 706668 / 708860 / 708536 | 22.80% / 90.35% |
| extraction-mismatch | 91.773 / 93.998 / 93.170 | 79.514 / 77.872 / 83.337 | 93.170 → 79.514 | 2860508 / 2860516 / 2860924 | 324668 / 325432 / 324424 | 14.66% / 88.65% |

三个路径的总耗时中位均改善；没有以总平均隐藏某条路径退化。原P1/P2 20%/50%是完整兼容包建议，不是A1硬门，mismatch约14.66%的时间改善也如实保留，不扩为writer/memo追目标。单次和分阶段中位及各次原数见[performance-summary.json](performance-summary.json)，不将每个微小变化都归因于matcher。三次有限synthetic样本没有给出生产/最大输入资源上界或统计置信保证。

### 小阶段的观测增幅

总阶段中位均下降，但以下小阶段的中位出现增幅，保留绝对秒数及比例。未对这些增幅做单独因果归因；三次样本不足以判定其是稳定退化或噪声，不能声称全部阶段普遍提速。

| 路径 / 阶段 | before中位s | after中位s | 观测增幅 |
| --- | ---: | ---: | ---: |
| normal-direct / W005_read_inputs | 0.696350 | 0.721508 | +3.61%（+0.025159s） |
| normal-direct / W008_adapter_and_build | 0.372333 | 0.381485 | +2.46%（+0.009152s） |
| normal-readback / W006_prepare_inputs | 1.477519 | 1.547533 | +4.74%（+0.070014s） |
| normal-readback / W009_build | 1.232702 | 1.240679 | +0.65%（+0.007977s） |
| extraction-mismatch / W008_adapter_and_build | 0.392832 | 0.396149 | +0.84%（+0.003317s） |
| extraction-mismatch / W011_result_encode | 1.446178 | 1.458006 | +0.82%（+0.011828s） |

## 完整结果与实际bytes

每个样本均断言完整36项FIN evaluation/crossing、正常5/7、mismatch实际4对source5/恰一项差异及touch，保留原40图形/18FIN、局部图8edge/6component/T05 pass/body/所有来源及独立source语义。readback attempt/checkpoint不变、unsealed且无terminal；完整公开decode DTO与原结果相等。更广partial/未知、错型等值/别名、来源和异常负例另由本轮选定273项及最终新源双全量验证，不采信旧同源矩阵替代新最终验证。

| 路径 | 每次before/after完整wire B | 每次before/after SHA-256 |
| --- | ---: | --- |
| normal-direct | 54,050,313 | `4d07033687223809e542ea661138fe0566ed162f6eab17fb7d4f806745377f16` |
| normal-readback | 136,471,701 | `1b75a398b4a2f22c156600fbe19590c182f37a77d0c171ab0a8b7a79e23cd795` |
| extraction-mismatch | 54,045,042 | `83713d7586b02181697f10ac45c59490f2c3aa02fcea37ecf92b740a03b8e2b1` |

父进程在各被测进程结束后，按1MiB块比较实际完整wire（不是仅比hash）。所有18次均与本轮相同路径before r1原bytes相同，before/after同捕获和GC条件也核对；证据在逐样本command和[最终回执](performance/receipt.json)。实际wire保留在`/workspace/w012-a1-performance/wires/baseline/`，不重复提交约1.47GB的大wire到Git；可由冻结源/输入/工具重建。编码器完全未改，wire降幅为0；不省略证据、不外置解析依赖来制造资源改善。

## 独立归因与残余成本

新旧readback profile均已完成，完整wire相同；所有阶段的明确constructor（含`__init__`/`__post_init__`）和`_require_input`/`_evaluate`/`_analyze`/normalize/公开encode/decode_record调用次数逐项相同，见[profile-summary.json](profile-summary.json)。65个大hex调用的顺序和长度也完全相同，不减少捕获或跳过认证。

| 最大既有hex校验窗口（118,841,892字符） | before | after |
| --- | ---: | ---: |
| 调用前RSS KiB | 347652 | 358520 |
| 调用后RSS KiB | 363556 | 358520 |
| 调用前HWM KiB | 3604172 | 501568 |
| 调用后HWM KiB | 7326636 | 501568 |
| 窗口matcher秒（仅诊断） | 5.968508 | 0.233527 |
| 整个profile进程峰值KiB | 7326636 | 720336 |
| 全部65个matcher窗口刷新HWM次数 | 5 | 0 |

旧版最大窗口将HWM刷新至该进程最终7,326,636KiB；新版同输入窗口RSS/HWM均未增长，全部65窗口没有刷新HWM。该数据与无插桩三次峰值下降共同支持已消除本次定位的重复分组matcher瞬时峰值。窗口HWM不是净分配，不把多次刷新相加，也未采样regex引擎内部每项分配。

新版整个profile峰值仍720,336KiB，高于所有matcher窗口记录的HWM上限648,896KiB：它在最后观测窗口之后、完整路径结束前刷新（此区间包括decode收尾、结果比较及profile收集）。保留完整136MB wire及canonical重编码等路径仍有临时空间，但该余量未做逐函数/allocator归因，不能把720,336KiB全部归为某个未测函数。它低于旧GiB峰值，但不宣称所有内存成本已解决。此残余成本/重复序列化若需进一步定位或优化，应由PM另派范围，A1不扩为writer/memo。

插桩本身会影响CPU。profile完整decode wall为221.044→222.850s（单次约+0.82%），不能以此替代无插桩三次decode及总耗时结果，也不能声称所有profile阶段均改善。上述窗口秒数用于定位原matcher工作；实际产品耗时结论只使用前表18个无插桩样本。原始profile函数exclusive/cumulative时间均保存，inclusive时间不相加。

## 验证与交接

开发新增/受影响检查通过；最终新源双3.10/3.12全量各1656项、strict typing各54源文件、构建、两套全新安装的源码外`-I -B`完整组合smoke全部通过，21条原命令exit0，见[工程完整回执](verification-r2/receipt.json)。全部原1605项保留，263源/测试/配置与受测after身份一致，100runtime只有codec的最小改动。[四份实际包](package-comparison.json)均可访问，runtime payload唯一差异为`domain/codec.py`；不把构建metadata/包blob身份混作wire身份。

源码外smoke的输入URI指向工程冻结snapshot，完整wire/hash按各自原stdout保存，不与上表固定URI基准混比。首轮工程中断及第二次轮询断连均保留，最终完成依据为内部21条原命令及闭合receipt，不将partial或外层started记为通过，详见[执行记录](execution.md)。

独立代码/正确性/性能review见[reviewer报告](independent-review.md)。本次仅交PM核验A1，不自行验收、合main、改current-work或启动下一子项；剩余峰值/重复序列化若需深入，由PM另派范围，新wire的公开范围、默认兼容、digest/ref和历史迁移仍需独立具体决定材料。
