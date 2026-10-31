# W004 R3 / raw 同源专项独立 review，修复复核

Reviewer：`raw_independent_review`，未参与样本实现。2026-10-31。原 findings 和初审证据保留于 `review-r1.md`，本记录不覆盖其原文。

受审版本为 `/workspace/work/w004/review-r2/snapshot`，基线 `9f6735dcede8e8b2135f89ff10f079a752ed758b`。独立重算父目录 SHA256SUMS.json 的 SHA-256，结果为 `af14667908160f6388881c0c67cc862cecba81f78ee936f28e7817e3d68c01bd`，与派发身份一致；再次核对128个相关fixture/helper/examples实物与清单相符。

结论：**R3-F1、R3-F2均已修正并独立复核通过；本专项范围无剩余必须修正 findings，可交总review及PM。** 仅指本版固定synthetic样本的来源/数值/关联/失败证据，不是产品parser、真实Calibre格式、W004最终验收或W003关闭结论。

| Finding | 复核与结论 |
| --- | --- |
| R3-F1（总review IR4）：unit/quality owner冲突被忽略 | `normalize`现在读取并核对dialect的axis/precision/unit/raw tick，使用其precision核对raw；读取derived registry的quality/accepted geometry/source并验证exact-only声明；header与dialect单位解释也显式一致性检查。对unit/vertices/bbox/precision加入dialect owner实际hash/pointer，对quality/geometry_kind/derived_layer加入对应derived registry实际hash/pointer。本reviewer重跑原三种独立copy冲突：header axis和dialect precision均为`QueryUnitDeclarationConflict`，registry quality为`QueryQualityDeclarationConflict`，没有意外hash错误遮蔽。已关闭。 |
| R3-F2（总review IR5）：DEVICE INFO缺少来源明确的type行 | 两份DEVICE INFO均有metadata_count=2、数字type lexeme、seed layer；type仍为opaque，不推断生产模型或端子。独立核对所有normalized metadata和位置回链；normal EvidenceRecord现为第8行token0=`400`，精确解释y=20nm。另在重绑坏raw目录分别删除type并将count改1、或将type改非数字，均明确`DeviceMetadataDrift`。F2坏raw仍仅缺END OF RESPONSE，完整同源链未退化。已关闭。 |

独立正确性脚本 `r2/check_raw.py` 不import fixture generator/normalizer/verifier。它重读9份raw，用Fraction、独立多输入join、正交边/鞋带面积核对全部10polygon和16records；2 instance、4 net、2 device regions、8 net regions，146具名字段与**558**实际定位回链通过。17 closure叶、27 F1 request输入bytes及canonical摘要、F2坏raw→重绑header→单独fixture-read ToolRun→ParseResult→StageFailure/localized→failure RunRecord completed refs重新核对通过。C02–C05继续在独立目录真实应用全部replacement/remove；其目标缺陷和其余绑定闭合均成立。

本轮命令及输出：

- `PYTHONDONTWRITEBYTECODE=1 python /workspace/work/w004/raw-review/r2/check_raw.py` → `r2/independent-results.json`、`r2/independent.stdout.json`。
- `PYTHONPATH=/workspace/work/w004/deps PYTHONDONTWRITEBYTECODE=1 python /workspace/work/w004/raw-review/r2/reproduce_conflicts.py` → `r2/conflicts-results.json`；原三冲突复现，调用被审helper只用于确认拒绝行为。
- `PYTHONPATH=/workspace/work/w004/deps PYTHONDONTWRITEBYTECODE=1 python /workspace/work/w004/raw-review/r2/check_metadata_rejection.py` → `r2/metadata-results.json`；两个新增元数据拒绝见证及EvidenceRecord line8回链。

环境Python 3.12.14；独立数值脚本仅stdlib，拒绝复现调用被审支持helper并使用已安装KLayout依赖。没有运行产品Stage1–6、真实Calibre/Virtuoso、production downstream gate、publication或生产上传；没有声称全词法/未知结构通用parser覆盖。本轮未修改仓库实现、原MR、W003 E/R或W004 E1/E2/RP1；最终技术与人工范围由总review/PM接收。
