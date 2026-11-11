# A2 完整有限筛选与停止依据

2026-11-11（Asia/Shanghai），执行者 `/root`。**建议按 AI4 停止当前候选，不推荐进入最终工程/产品验收。** direct/mismatch 的单次总耗时小幅改善，与 direct decode、mismatch build 及 readback 整路退化并存；峰值基本持平。不能证明本候选有值得继续的稳定净收益。保留候选和全部实测交 PM 取舍，不扩 owner、writer/reader/memo/B 或启动下一节点。

## 同条件与实际样本

产品/正式测试/配置是候选提交 `c0a9a2e4c292255202a0ec82b6277cd8a8dd6b78` 的264项；本机 before 为 A1 main `2489b4609ae97d8211bf450d55cac9392492ac71` 的263项，均有完整快照及 Git/blob/磁盘核对。两侧实际差异仅两个 codec 和新增正式测试。见 [新冻结](freeze-screen-attempt02/freeze.json) 与两个 source-manifest/snapshot。

解释器固定 `/workspace/.venvs/layauto/bin/python` 3.12.14、同一依赖集/主机/cgroup。导入树分别为本机 before worktree 与候选，输入仍使用原正常绝对 site URI `/workspace/Layauto/tests/fixtures/w003_m1/site_config.yaml` 及原 mismatch `/workspace/w012-inputs/extraction-mismatch/site_config.yaml`；35项/五 overlay 按原清单完整字节重建。合法 captured source/target URI 字面值保持 `source.cdl`/`target.cdl`。readback 使用原 `w012-investigation-run` / `w012-investigation-lineage` / `create-w012` 和所有默认空 selections。保留 normalized cache 并核 raw、全部原上游 roots、fresh repository、一次获取前 collect 和默认自动 GC。

[原命令回执](performance-attempt02/receipt-1.json)中的6条均 fresh、串行且每路 before/after 交替，无 hook/profile。每条完整公开 build/encode/decode、全部原值/来源事实和真正巨大 wire 均执行。产品阶段计时、ru_maxrss 固定后才做补充来源/ref遍历及实际 wire IO/完整逐块比较；没有额外巨大编码。阶段总和是每样本所有被计时公开阶段之和，不是外层进程 wall。原始 outer wall/2秒采样另存，未混作产品阶段时间。

**以下每侧每路只有1次，不是要求的最终3次矩阵或重复中位结论。** 机器汇总中的单元素 median 只是该次值；原次/所有阶段和失败保留于 [完整汇总](screening-summary-attempt02.json)。

单位：秒，均 before → after。all-build 包括获取、caller reads（适用时）、W008/W009/W010及W011 build；W011 build是其子阶段，不与all-build再相加。

| 路径 | all-build | W011 build | encode | decode | 阶段总和 | 整进程峰值 KiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| extraction_mismatch | 84.284179 → 90.871801 | 60.065001 → 71.960081 | 2.818241 → 2.943032 | 69.075232 → 56.681337 | 156.177652 → 150.496170 | 326396 → 326316 |
| normal direct | 98.536131 → 77.204181 | 70.222098 → 50.577193 | 6.289962 → 2.106326 | 75.937515 → 90.459830 | 180.763609 → 169.770337 | 327444 → 325876 |
| normal readback | 149.993687 → 185.268059 | 101.479341 → 141.366418 | 3.987211 → 10.438596 | 130.609030 → 157.684997 | 284.589928 → 353.391652 | 711056 → 709204 |

总耗时：direct改善6.0816%、readback退化24.1757%、mismatch改善3.6378%。峰值改善仅0.4789%、0.2605%、0.0245%。direct decode +19.12%、readback W011 build +39.31% / decode +20.73%、mismatch W011 build +19.80%，均未剔除。不是拿旧20%/50%建议当硬门，停止依据是本轮真实混合收益与抵消退化。

- extraction_mismatch：总耗时变化 -5.681482s；W011 build +11.895079s、decode -12.393895s。完整所有阶段增减见机器汇总，未改的 W010 build 也从 20.332715 变为 16.162064s。
- normal direct：总耗时变化 -10.993272s；W011 build -19.644906s、decode +14.522314s。完整所有阶段增减见机器汇总，未改的 W010 build 也从 24.860247 变为 21.137248s。
- normal readback：总耗时变化 +68.801724s；W011 build +39.887077s、decode +27.075967s。完整所有阶段增减见机器汇总，未改的 W010 build 也从 42.360489 变为 35.842714s。

未改的上游阶段也有明显摆动；1次/路没有统计重复，不能把全部差异归为私有wrapper删减或确定的逐函数因果。静态和小值机制能说明只删纯编码包装、没有绕过认证；它们不能给完整收益背书。未另跑profile，因为当前完整筛选已不足以推荐继续，不扩展归因包。

## 完整性硬条件

| 路径 | 完整wire B | SHA-256（两侧相同） | wire降幅% |
| --- | ---: | --- | ---: |
| extraction_mismatch | 54,045,042 | `83713d7586b02181697f10ac45c59490f2c3aa02fcea37ecf92b740a03b8e2b1` | 0 |
| normal direct | 54,050,313 | `4d07033687223809e542ea661138fe0566ed162f6eab17fb7d4f806745377f16` | 0 |
| normal readback | 136,471,701 | `1b75a398b4a2f22c156600fbe19590c182f37a77d0c171ab0a8b7a79e23cd795` | 0 |

六个真正 wire 文件在本机 `/workspace/work/w012-a2/wires-attempt02/`，逐块实比与双方完整 hash 见每条 `.comparison.json`；不将巨大二进制重复提交 Git。原快照、工具、输入来源清单及 reviewer 实核记录可跨会话重建，不能只凭 hash 替代公开验证。逐字段完整DTO相等、所有已存typed refs、captured raw bytes/source解析、query seed来源、独立target、原局部图/T05/body均核对。正常5/7，mismatch实算4对source5恰一差异、全部36 evaluations/crossings保持；readback attempt/checkpoint不变、unsealed且无terminal。

## 原失败与修正

原 `performance/` 中 before-direct 完成产品阶段后，被新工具错误的 `/target.cdl` 后缀假设拦下，exit1且没有成功JSON/wire；**未用它作有效before或计算收益**。原文件、工具源码、诊断错误及真实stderr保留。I-R02改为核对完整原source/target preservation，正常/mismatch实际轻量正负见证通过，独立复核关闭，再以新的工具冻结重新完整运行六条。汇总 `failure_directories` 同时扫描原目录与本次目录，确实列出这唯一失败样本；其外层传播exit1是同一次工具失败，不重复算另一产品失败。

I-R01为交付checker在输出完成前hash自身wrapper的循环，原反例及修正隔离复跑也保留。两项finding的原文和独立关闭归 [独立review](independent-review.md)，执行不代写关闭结论。

## 尚未完成与交接

开发新测试双3.10/3.12各82通过、双strict typing54通过，受影响185项通过；这些是开发证据。**最终双全量、构建、双干净安装源码外完整组合smoke、两侧各3次fresh性能矩阵均未执行，未获产品验收。** 工程工具/环境仅准备，不能冒记已验证。原1656个正式节点全部保留，当前正式collection为1738。

原PM阶段、要求、current-work、原P1/A1/A2记录及证据保持。候选/证据提交推送原实施分支后交PM停止，不自行验收、合main、删分支或启动M1下一节点。
