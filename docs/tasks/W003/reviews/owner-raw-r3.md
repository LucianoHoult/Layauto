# W004 R-OWNER 最后复核（第三轮）

Reviewer：`/root/independent_review/raw_review`，未参与实现。被测冻结版 `/workspace/work/w004/review-r3/snapshot`；已独立重算其 `SHA256SUMS.json`：`9136e0509ab50e03ea260eb0d1ecaedfb4aa6a58cda17a5cc926d715de0fbd76`。r1/r2 finding、脚本及输出均保持原文。

结论：本专项提出的 R-OWNER 四个反例均已修复并复核；无本专项剩余必须修正项。

在独立目录保持原 source GDS/CDL，分别修改所选owner并独立重绑实际header/closure bytes，冻结版 `witness` 的实际结果：

| 探针 | 实际结果 |
| --- | --- |
| TOY_N NFIN轴改为multiplicity | UnsupportedModelAxes |
| nominal_tick改为2nm | UnitSourceConflict |
| CDL n suffix改为10nm | CdlUnitContractConflict |
| nominal_user_unit改为2µm | UnitContractConflict |

新增代码也检查 `first_nominal = nominal_tick / nominal_user_unit` 及canonical tick与nominal tick的一致性。此次复核为固定fixture支持子集的声明冲突拒绝，不是通用配置或产品parser能力证明。

命令（Python 3.12，已安装KLayout）：

```sh
PYTHONPATH=/workspace/work/w004/deps PYTHONDONTWRITEBYTECODE=1 python /workspace/work/w004/reviewer/raw/owner_probe_r3.py > /workspace/work/w004/reviewer/raw/owner_probe_r3.json
```

脚本与结果位于上述路径。另对照r2/r3清单，受影响raw/cache/记录样张路径保持同一bytes身份（具体逐路径比对见 `r2-r3-unchanged.json`）；因此沿用r2的独立raw精确值、558回链、27项实际bytes摘要敏感性、F2同源链及6overlay结论，未机械重跑无变化范围。

本报告仅关闭本专项技术finding。主review另核body/GDS/图/完整身份；没有运行产品、EDA或production downstream gate，也不代替PM最终验收W004或关闭W003。
