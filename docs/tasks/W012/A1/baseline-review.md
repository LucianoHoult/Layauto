# A1 已完成 baseline 的独立核验（工程/profile待最终复核）

Reviewer `/root/a1_plan_review`，未重跑产品测量。仅核对已完成18样本的原始证据和实际wire文件；[脚本](baseline-review-evidence/check.py)、[原stdout](baseline-review-evidence/stdout.txt)/[stderr](baseline-review-evidence/stderr.txt)、[结果](baseline-review-evidence/result.json)保留。**2642项独立轻量检查通过，未见必须项。**

核对18个fresh子进程的before/after配对次序和实际起止时间无重叠；before完整262源仍等于W011，after只多新hex测试并仅改codec；实际包导入位置、同一解释器/平台、固定35项mismatch重建bytes、各31捕获/280706B、RunRequest与GC/完整保留断言一致。所有样本per-case命令/receipt、原stdout/stderr与工具hash匹配。原P1完整结果断言原样保留，正常5/7、mismatch实际4对source5/一项差异及完整crossing、局部图/T05/body、readback unsealed/checkpoint/无terminal均通过；未扩写为三条输入覆盖所有错误路径。

独立读取Git外的18份实际wire，以1MiB块与各case before-r1逐字节比较，并分别重新计算存储文件SHA256，全部与各样本实际长度/hash相同。大wire未提交Git；路径/比较记录在实际命令和本结果中，不把“只比hash”描述为逐字节检查。

| 路径 | before阶段总计中位秒 → after | before峰值中位KiB → after | 总耗时改善 | 峰值改善 |
| --- | --- | --- | ---: | ---: |
| normal direct | 94.418923 → 75.799891 | 2,851,076 → 325,436 | 19.7196% | 88.5855% |
| normal readback | 186.625165 → 144.066817 | 7,344,896 → 708,536 | 22.8042% | 90.3534% |
| extraction_mismatch | 93.170488 → 79.514097 | 2,860,516 → 324,668 | 14.6574% | 88.6500% |

各次原值、逐阶段中位数及全部峰值已独立重算并与 `performance-summary.json` 全部相同。中位总计是每次阶段之和的中位数，不是各阶段中位数之和；runner elapsed包含启动/轮询/wire写入，不能替代阶段总计。

不是所有小阶段都有观测降幅：direct W005约+3.61%/W008+2.46%，readback W006 prepare约+4.74%/W009+0.65%，mismatch W008+0.84%/encode+0.82%。这些绝对值较小，三次样本不足以指定噪声或算法因果，最终分析应披露，不能称所有阶段普遍提速。各路径总计中位数均下降；20%/50%不是此次A1硬门，不将direct/mismatch不足20%记为未达既定验收。

本节不声称profile归因、双全量/typing或包/双安装已完成，也不证明生产/最大输入资源上界；这些须按最终完整证据统一独立review。

另对实际冻结probe SHA `5dc3d2417e2f45486648730151e9150f444041b6eae1a35730783bbb88909f1a` 完成[69项小值观测器透明性检查](baseline-review-evidence/hook_check.py)，[结果](baseline-review-evidence/hook-result.json)和原输出保留。新旧pattern的匹配/不匹配、flags、5类异常两种suppression下的原object/cause/context及恢复、foreign pattern不触发自定义比较、WireMeter小record完整bytes/roundtrip均保持。只编码小测试值作前后透明性对照，hook本身未增加encode/digest大对象；未产生新的产品性能样本。
