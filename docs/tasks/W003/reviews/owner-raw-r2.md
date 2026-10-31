# W004 raw / owner 修复复核（第二轮）

Reviewer：`/root/independent_review/raw_review`，未参与实现。受审冻结版 `/workspace/work/w004/review-r2/snapshot`，SHA256SUMS.json 身份为 `af14667908160f6388881c0c67cc862cecba81f78ee936f28e7817e3d68c01bd`。r1脚本、输出和finding原文均保留。

## 结果

原 R-OWNER 两个具体探针已修正：

| 探针 | r1 | r2 |
| --- | --- | --- |
| TOY_N NFIN轴改成multiplicity，重绑 | no_defect | UnsupportedModelAxes |
| nominal_tick_m改成2nm，重绑 | no_defect | UnitSourceConflict |

独立raw脚本已按新DEVICE metadata_count=2（integer type token＋first-layer tag）读取，不导入generator/parser/verifier。重新验证9raw、10region完整vertices和bbox、486原始回链外新增owner引用、27实际文件bytes摘要敏感性、F2坏raw完整同源链以及C02–05/C06/C21实际overlay，均通过。精确数量与结果见 `independent_raw_r2.json`。

## R-OWNER 仍有剩余必须修正部分

修复后的 `parse_cdl` 已验证 model axes，`units` 已采用nominal_tick，但单位来源仍不完全约束解释。针对同一finding，保持source GDS/CDL不变，仅改所选owner并重绑header/closure：

| 修改 | r2实际结果 | 问题 |
| --- | --- | --- |
| `tech/formats.json#/cdl_dialect/numeric_suffixes/n/denominator` 从1000000000改成100000000 | no_defect | 所选n suffix已表示10nm，helper仍把L=4n当4nm；CDL与geometry/nominal单位应冲突 |
| `tech/formats.json#/unit_scale_contract/nominal_user_unit_m/numerator` 从1改成2 | no_defect | 所选user unit成为2µm，但GDS两UNITS仍绑定1nm和0.001 user-unit/tick，不满足nominal_tick/user_unit关系 |

这仍属于R1单位链/唯一owner实际消费，不是新的产品能力要求。固定样本辅助可明确只接受当前声明，但应拒绝这些owner冲突，或使用所选精确单位计算后拒绝不一致。

复现：`owner_probe_r2.py` 创建隔离目录，修改owner并独立更新header/closure实际bytes hash，随后调用被审 `witness`；结果保存 `owner_probe_r2.json`。这是针对被审helper的反例，不能冒充独立几何算法。

## 命令、环境与范围

```sh
PYTHONPATH=/workspace/work/w004/deps PYTHONDONTWRITEBYTECODE=1 python /workspace/work/w004/reviewer/raw/owner_probe_r2.py > /workspace/work/w004/reviewer/raw/owner_probe_r2.json
PYTHONDONTWRITEBYTECODE=1 python /workspace/work/w004/reviewer/raw/independent_raw_r2.py > /workspace/work/w004/reviewer/raw/independent_raw_r2.json
```

Python 3.12；owner探针使用已安装KLayout；独立raw核验只用标准库。没有修改共享实现，没有运行产品/EDA、生产downstream gate、发布或验收。body/GDS/图/包身份由主review另查。本专项结论为：实际新版raw及记录链仍自洽，R-OWNER原两点修复已验证，但上述两个单位冲突还须修复后复核。
