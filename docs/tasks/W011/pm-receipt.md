# W011 PM 分支技术接收

**分支技术接收通过，新增必须修正项 0；尚未最终验收或集成 main。** 本次核对交付 `3c464baade7b6ea8c712cfb84265490b8e3f754e`，源码/正式测试/配置冻结 `e89bdaa6a091f56cfaf7862dced7232d34e22514`，runtime 修正 `8917d38d916c914bfa785cb116982f3f299b38de`；不是只采信执行摘要。完整 UTC、命令、源身份和文件哈希见[机器回执](pm-receipt.json)。

## PM 实际检查

- Python 3.12.14、已有 PM 环境，实际 **12 passed / 128.69s**（另 31 deselected，1 项外部 anyio pytest 插件弃用 warning）。覆盖禁 IO 的真实 direct 组合、正常完整 crossing 集合、原 extraction_mismatch 的实测 4 对 source 5、精确 FIN 边界；[命令回执](pm-evidence/targeted.json)记录进程总耗时 129.307s，[原输出](pm-evidence/targeted.stdout.txt)保留。strict mypy **54 文件通过**，见[命令](pm-evidence/typing.json)及[输出](pm-evidence/typing.stdout.txt)。
- 新编独立 rational coverage 检查 **384 例、6,144 个原子区域成员对照**，验证重排、重复、精确细分及巨大正负偏移不改变 exact union，见[结果](pm-evidence/coverage-probe.stdout.json)与[脚本](pm-evidence/coverage_probe.py)。另由独立范围专项核查 A1–A7、上游必要补修、CR-01–06 处置，并实际运行 **256 例、5,981 项** exact coverage 检查；[报告](pm-evidence/scope/report.md)明确静态/实跑边界。
- 工程专项 **150 项核对通过**：262 项源与 current/Git frozen/Git delivery/完整 tar 一致，两实际包各 100 runtime、21 条最终命令/原输出/工程与资源索引、双 collection 原 1465 + 新 140 均核对；[报告](pm-evidence/evidence/report.md)和[完整结果](pm-evidence/evidence/audit-result.json)保留。

原双解释器各 1605、typing54、构建和双干净安装源码外 direct/readback/mismatch smoke 按相同最终源及原独立 review 采信。本机没有原安装/测试树，本次未重建、重装、重跑双全量或完整 readback codec；不把归档安装清单当成本次实际观察安装目录。旧失败和修正历史保持原身份。

## 资源成本与范围

独立重新核对了原 fresh-process 数据及 1,399 条原采样，没有新跑资源 benchmark：

| 路径 | 完整 Result wire | 整进程 `ru_maxrss` |
| --- | ---: | ---: |
| normal direct | 54,050,313 B | 2,847,416 KiB（约 2.716 GiB） |
| normal readback | 136,461,405 B | 7,322,828 KiB（约 6.984 GiB） |
| extraction_mismatch | 54,049,506 B | 2,854,456 KiB（约 2.722 GiB） |

完整矩阵 3.10 另有 **9,257,804 KiB（约 8.83 GiB）采样高点**；共享 cgroup 最高采样 12,299,743,232 B。fresh-process 高水位、长进程采样与共享值的范围不同。RSS 包含 imports、上游捕获与重建、完整结果和 wire，不是 W011 的增量分配；constructor 包含在 build/decode。仅 40 drawn records、18 FIN 的有限 synthetic 观察无法证明最大输入、多器件、并发或生产可用上界。

当前 W011 的有限计量要求有对应代码与证据，没有已确认的性能预算被证明违反；这不代表资源成本可忽略。**专门合并前 review 须独立判断它是否影响当前受限集成；扩大状态链或输入前，PM 应优先收敛捕获重复保留/重复认证的处理方案，并保留来源认证与异常合同。** 本轮没有批准新 wire 合同、规模承诺或生产能力。

## 交接

下一步使用[专门合并前 review prompt](independent-premerge-prompt.md)。本次 PM 专项不替代用户沿用的独立 review session；其结论通过后，再评估 main 集成并验证实际合并版本。W011 仍只回答 channel 身份及有限 FIN/L/W 计量，完整 net/body/model、T02/全部规则、坐标、baseline/no_change/Stage6 和 U06 继续保留。
