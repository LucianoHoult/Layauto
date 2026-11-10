# W011 main 集成前身份核对

检查者 `/root/w011_integration_audit`；只读范围为 main `61775e8…`、独立待审 `8452027…`、专门 review 交付 `9791c1e9eb6c7e3e1878067f045abcad4e4d0b7d`。本机执行时间与完整 SHA 见 `audit-result.json`。

**417 项身份、输出与明确范围检查通过，新增必须修正项 0。** `audit.py` 最终 exit 0，`audit.stdout.json` 为摘要，`audit-result.json` 为全部检查；最终 stderr 为空。

- `8452027→9791c1e` 只有 34 个 review 路径。除 W011 任务外，均是专门报告/附件；任务改动精确为 reviewer R2 追加，去掉该段可重建原任务文本，PM 段和原要求没有变化。
- 262 项源码、正式测试、配置在当前文件、冻结 `e89bdaa…`、原执行交付 `3c464ba…`、待审 `8452027…`、交付 `9791c1e…` 和完整 source tar 的 SHA-256 全一致。100 项 runtime 与原产品修正 `8917d38…` 一致；原冻结、交付、待审与最新 review 的祖先关系成立。
- 最新交付 tree 为 `498cfd7b239c76629ee3c02919cb590347404f5c`。尚未核对后续实际 main merge tree；若 parent 提供合并身份，可另核。
- 专门 review 清单的 33 个文件逐字节/size 匹配交付 Git。审计原 stdout 的 `status=passed`、297 条实际检查列表和 head/frozen 绑定一致；9 项真实组合正式回归的命令 exit0及 stdout/stderr SHA 均匹配，stdout 确为9 passed；W007 malformed 原 stdout确为6 passed。几何/边界命令回执全 exit0。本次没有重跑297项审计内部操作、这些正式测试或探针。
- 报告明确新增 finding0、必须项0，建议仅当前受限串行 synthetic M1 集成。fresh readback 136,461,405B/7,322,828KiB、长矩阵采样9,257,804KiB的范围不同；报告明确RSS不是W011增量、采样不是精确进程峰值、没有生产/最大输入保证，并建议重型串行及优先W012。没有把归档双矩阵/readback/安装写成本次新实跑。

本次没有产品导入、重型 codec/readback、构建、安装、资源 benchmark 或产品修改；不代替 PM 集成后的实际组合验证或最终验收。

脚本自身两次准备错误已保留：`audit-initial.stderr.txt` 记录把 runtime 包内相对路径当成 repo 路径，修正为 `layauto_v2/` 前缀；`audit-second.stderr.txt` 记录报告措辞是“不能当 W011 增量 RSS”而脚本最初限定为“不是”，已按实际同义明确表述修正。二者均为审计 harness 假设问题，未列产品 finding；最终完整运行才计为通过。

## 实际 merge 补核

PR #65 的 main 合并为 `59f2cda44e30779bb3e82346d71a389831314506`。只读补核确认两 parent 按顺序为原 main `61775e8fde6e9ea247ec08a32067c44c3be48ff8` 与专门 review head `9791c1e9eb6c7e3e1878067f045abcad4e4d0b7d`；merge tree 与已审交付 tree 均为 `498cfd7b239c76629ee3c02919cb590347404f5c`。262 项源码/正式测试/配置在 merge Git blob 与当前 checkout 均匹配原 source manifest，未有额外源变化。补核结果保存于 `merge-check.json`，必须修正项仍为0。没有重跑或修改先前 audit 输出，未运行产品/重型命令；parent 正在独立完成实际 merge 的组合验证，本补核不代替该验证。
