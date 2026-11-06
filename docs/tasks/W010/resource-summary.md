# W010 资源摘要澄清（PM，E-N01）

日期：2026-11-06。采纳[独立合并前复核](independent-premerge-review.md)的P3非阻塞建议E-N01；本补记澄清原[执行交接](execution.md)及[代码review](code-review.md)的资源范围摘要，保留原报告/原输出字节。没有改产品或重新运行性能测量。

原[performance.json](performance.json)的四个去除optional normalized cache的direct路径样例为：

| case | result wire bytes |
| --- | ---: |
| normal | 15,470,850 |
| special_cut_islands | 12,579,736 |
| extra_20_isolated_M1 | 17,086,974 |
| extra_8_duplicate_CONTACT | 16,096,466 |

**准确范围为12,579,736–17,086,974 bytes，即十进制约12.58–17.09 MB。** 原摘要15.47–17.09 MB遗漏cut-islands下界；正常/最大wire及资源限制没有因此被低估。

原正常含cache的direct回执为22,789,218 bytes（约22.79 MB）。独立premerge [source probe](independent-premerge-review/source-probe.stdout.json)另记录readback完整回执59,422,834 bytes（约59.42 MB）；两者保留链不同，不作同一捕获身份的wire字节比较，也不据此声明生产资源上界。

原约988 MiB为累积进程RSS高水位，包含多层wire和前例影响，不能当作逐例增量。四例max-pieces均为1；大量多片/孔洞、最大输入和生产规模资源仍未验证。公开路径重复捕获认证、聚合重建、canonical wire与digest成本的原披露保持。

本次只重算原记录的min/max并核对来源及hash，见[集成前事实核验](integration-evidence/review-check/report.md)与[资源数值回执](integration-evidence/resource-values.json)。E-N01的文字精度建议已在本补记处理；没有新增合并门槛或性能保证。
