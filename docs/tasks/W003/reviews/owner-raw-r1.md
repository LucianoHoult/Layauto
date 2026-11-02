# W004 raw / provenance 独立专项 review（第一轮）

Reviewer：`/root/independent_review/raw_review`，未参与实现；2026-10-31。受审固定快照为 `/workspace/work/w004/review-r1/snapshot`，基线 `9f6735dcede8e8b2135f89ff10f079a752ed758b`。本报告只覆盖该快照，不把后续工作区修复自动视为复核通过。

结论：正常 raw 及 normalized 的实际值、回链和 F1/F2 链自洽；发现分类 owner 未被实际语义消费的必须修正项。主 reviewer 负责汇总与最终版本复核。未运行任何产品 parser/runtime、Calibre、Virtuoso、生产 downstream gate 或部署操作。

## 独立核验结果

执行命令：

```sh
PYTHONDONTWRITEBYTECODE=1 python /workspace/work/w004/reviewer/raw/independent_raw.py > /workspace/work/w004/reviewer/raw/independent_raw.json
PYTHONPATH=/workspace/work/w004/deps PYTHONDONTWRITEBYTECODE=1 python /workspace/work/w004/reviewer/raw/owner_probe.py > /workspace/work/w004/reviewer/raw/owner_probe.json
```

环境为 Python 3.12；第一项只使用标准库，不导入任何被审 generator/parser/verifier。第二项为隔离目录下对被审 `witness` 的冲突探针，不能冒充独立算法结果。

- 枚举9份 actual raw，与 header raw 列表及 requests manifest 对账；逐叶重算 source/target/raw/closure SHA-256 和 canonical closure digest。
- 独立读取 iXref/nXref 与 NET NAMES；验证 Q17→MN0、Q93→MP0，1..4→n_a/n_y/n_lo/n_hi→A/Y/VSS/VDD，opaque index 只按当前 query-run 的名字顺序解释。
- 从10个 DEVICE/NET region 的完整4顶点直接读 `(y,x)` 整数，以 `Fraction(value,20)` 换算 nm；验证矩形四角、相邻边与闭合边、顶点保序及具名 bbox，逐条对照手写 spec 和 normalized，全部一致。
- 独立遍历486处实际 source locators，检查行/token/JSON pointer、lexeme 与实际 bytes hash；所有 normalized record 顶层语义字段均有 `field_sources`。
- 对27个 request 文件逐个取实际 bytes 并加入一个 LF，重新计算该选择的 bytes hash 与完整 canonical request digest；每个变化均改变摘要。原正常 descriptor digest 与 RunAttempt/raw_request_digest/idempotency 三处一致。
- F2 独立确认坏 DEVICE_INFO 原文仅删除 `END OF RESPONSE`；实际坏 bytes hash、重绑 header、独立 fixture-read ToolRun、ParseResult、StageFailure localized/completed refs、failure RunRecord completed/failure refs 全链同源。
- 在独立目录真正应用 C02–C05、C06、C21 replacement/remove。C02缺结束符，C03 NET NAMES声明5但实际4，C04 `p 1 4`变`q 1 4`，C05 geometry precision变0；六例达到所声明缺陷。只有C06保留有意 nXref raw hash不匹配；其余被测overlay无意外输入hash错误，C21仅cache A→Y与raw冲突。
- 回查 legacy 原始格式描述：geometry precision及 `(y,x)/precision µm` 有来源；xref的header结束标记不是文件终止符；DEVICE metadata与section tuple仍opaque，未从它们推断真实模型参数。当前方言继续明确synthetic、生产版本未核实、LVS not_run。

详细坐标、路径与负例结果保存在 `independent_raw.json`，脚本原文保存在同目录。

## 必须修正 R-OWNER（供主 reviewer 合并）

`tech` 分类只有读取/合并，不足以证明消费者采用了所选事实。当前 `w003_verify.py::parse_cdl` 硬编码模型、DGSB、参数轴及 `n` 单位；`units` 硬编码1nm nominal。独立复制正常样本，改 selected owner 并重绑 header/closure 后，有以下复现：

| 修改 | source GDS/CDL | `w003_verify.witness` 实际结果 | 应有后果 |
| --- | --- | --- | --- |
| `tech/physical.json#/models/TOY_N/parameter_axes/NFIN` 从 `fins_per_finger` 改为 `multiplicity` | 不变 | `no_defect` | 所选语义与固定模型子集矛盾，应拒绝/明确unsupported |
| `tech/formats.json#/unit_scale_contract/nominal_tick_m/numerator` 从1改为2 | source仍1nm | `no_defect` | 实际编码与所选nominal scale冲突，应拒绝 |

这违反 W004 R1/MR-004/D2“唯一 owner 的实际消费”。不要求扩展通用配置或产品parser；固定辅助可以只支持当前值，但必须校验所选owner与支持语义一致，并由该owner参与答案/冲突判断。复现脚本及输出为 `owner_probe.py`、`owner_probe.json`；所有操作限本review隔离目录，未改共享实现。

主 reviewer 告知主执行者已在修正上述问题，且另有独立专项发现 dialect/header/quality 冲突；本报告没有运行那一专项的探针，故不将其作为本人的独立结果。

## 限制

本专项不覆盖完整body几何、GDS独立读回、全部29负例、图、最终文件包、人工状态或产品行为；这些由主 reviewer/其他专项检查。正常bytes通过不等于helper对任意配置漂移正确，也不等于生产格式已核验。最终快照及修复仍需复核，W004/W003是否验收由PM决定。
