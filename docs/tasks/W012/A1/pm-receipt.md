# W012 A1 PM 分支技术接收

**A1分支技术接收通过，新增必须修正项0；专门合并前review、main集成及最终验收尚待。** 被核交付 `db07a16fb7cbbac030adae84a9eb88cc0c8aa650`，产品/测试冻结 `ca1f810c3c97376f71089d8b4054760ff198012f`，最终工程manifest记录起点 `212554cdc402f6b86e92b8b81cd43752a01ff858`。263源/100runtime一致，唯一产品diff是bytes hex校验条件；encoder、schema/1、公开验证/认证边界未改。详见[机器回执](pm-receipt.json)。

## PM 实际核验

- 实际Python3.12.14正式回归 **89 passed / 0.47s**（新A1 51项及既有W005合同，另1项外部pytest插件warning），strict typing **54文件通过**。见[回归命令](pm-evidence/targeted.json)、[原输出](pm-evidence/targeted.stdout.txt)及[typing输出](pm-evidence/typing.stdout.txt)。
- 实际重跑一次完整normal readback公开构造/encode/decode：正常5/7、完整来源/局部图/T05/body、roundtrip相等、attempt/checkpoint不变/unsealed/无terminal；wire **136,471,701B**，SHA-256 `1b75a398b4a2f22c156600fbe19590c182f37a77d0c171ab0a8b7a79e23cd795` 与固定输入原记录一致。阶段总计 **140.617s**、整进程峰值 **710,728KiB（约694MiB）**，命令总耗时141.381s。见[命令](pm-evidence/readback.json)、[完整结果](pm-evidence/readback-result.json)及[原输出](pm-evidence/readback.stdout.txt)。这是本机一次after检查，没有新的before，不用它计算新降幅。
- 独立[合同专项](pm-evidence/contract/review.md)实际 **39,187项**有限语言/异常/AST/原profile计数核验通过；数学证明 `(HH)* = H* ∩ 偶数长度` 与有限见证分开。公开JSON原生str及原matcher/fromhex异常历史保持；私调恶意str子类新增len副作用与方案报告已披露边界一致，不扩成公开类型承诺。
- [证据专项](pm-evidence/evidence/report.md)的 **1305项性能/原证据**与 **1286项工程/包**轻量核验分别通过；不是产品测试数。263源/tar、18个fresh串行样本、源/工具/输入及固定条件、原1656×2/typing54×2、21条命令、四个实际包各100runtime及原1605+新51均实核；A1-R01非空stage防覆写原finding/修正/复核关闭成立。

原双全量、构建/双安装、更广异常及全部18样本按同一源和原始证据采信，本次未重复重型矩阵或成对性能。原大wire、before runtime、性能venv、固定mismatch及原安装树本机不存在；原独立reviewer实际重读大wire/安装的结论及原命令/receipt可核，本次没有重比全部1.47GB或重新观察原安装树。四个包本身和归档源码/原结果可直接读取。

## 性能结论及限制

直接从18份原 `wall_seconds`/RSS记录重算，先求每次阶段总和，再取三次中位：

| 路径 | 总秒中位 before→after | 峰值KiB中位 before→after | 耗时 / 峰值降幅 |
| --- | --- | --- | --- |
| normal direct | 94.419→75.800 | 2,851,076→325,436 | 19.72% / 88.59% |
| normal readback | 186.625→144.067 | 7,344,896→708,536 | 22.80% / 90.35% |
| extraction_mismatch | 93.170→79.514 | 2,860,516→324,668 | 14.66% / 88.65% |

原18次和两侧profile的wire/hash保持；65个大hex调用及constructor/认证计数未减少。旧5次校验窗口刷新HWM，新0次，支持已消除本次定位的matcher瞬时峰值。HWM不是净分配，profile时间不是baseline。六处小阶段增幅、单次profile decode约+0.82%和约700MiB残余峰值均保留，不能声称全部阶段提速或所有内存/规模问题解决。136.5MB完整wire和重复重建仍在，20%/50%不是A1硬门，新wire/下一子项未批准。

**非阻断记录观察：** `performance/commands.json`及`profile/commands.json`最后一项未回写bytecmp字段；对应单条 `.command.json` 与最终receipt均保存完整比较成功。PM已另存[层级对照](pm-evidence/index-tail-reconciliation.json)，保留原索引/原hash，不把索引差异冒称缺少最后样本或本机实际大wire比较。

下一步使用[专门合并前review prompt](independent-premerge-prompt.md)，复核通过后由PM安排main及实际合并版本的组合验证。本次PM专项不替代该独立session，不启动writer/reader/memo、新wire或下个子项。
