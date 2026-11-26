# PM-01 独立复核

受审区间为 `a6c2f1e62e26b1f6fc5f934ed0cb61a2957b8600..03bbecc06e2dab2f383ba2b8e262f621d754e2fc`，产品提交的 tree 为 `1d6030d68897b0f008ab9b797a8721246e6059e0`。审阅者未编写补修。首轮代码复核检查了二维交片和一维轨号的限制，漏验了“只改变 POLY 坐标类型时，整包是否应通过”。本次从[PM 原反例](pm01_probe.py)和工艺配置合同重新核对该结论。

## 判据

从原始 `source.gds` 按大端记录长度读取 BOUNDARY、LAYER、DATATYPE 和 XY。GDS SHA-256 为 `97cf8d88771ff97f2cf189f6ae6a2fdcce585fc14f93c93d0ecf32326b415429`。流层 3/0 的唯一矩形在字节 432，范围为 [58,62) × [10,190) DBU，面积 720 DBU²。

在完整 W022 配置的副本里，单独为 POLY 声明二维格。X 边为 4 + 11i，Y 边为 −3 + 17j，Y 共 12 格。各片的预期格号和矩形通过在所给格边上逐格与原始 XY 求交得到。

| 输入 | 独立预期 | 下游应取得的结果 |
|---|---|---|
| X 共 6 格，域 [4,70) | X 在 59 处分成 1 和 3 DBU 两列，列号为 4、5。Y 覆盖 12 行，首行高 4、末行高 6，中间 10 行各高 17。共 24 片，面积 720 DBU²。 | POLY 的二维投影和 15 层整体通过。一维栅轨读数为 False。 |
| 只将 X 缩为 5 格，域 [4,59) | 矩形右沿仍在 62。域内只有 180 DBU²，余下 540 DBU² 越界，整条记录无法重建。 | POLY 返回 incomplete，原因 outside_range 指向原记录，返回该记录的片数为 0。整包受阻，一维栅轨读数为 False。 |

## 实跑和代码检查

在受审提交的仓库根目录，用项目依赖环境中的 Linux CPython 3.12.14 运行以下命令。[独立探针](pm01_review_probe.py)

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests/contracts python docs/tasks/W022/pm01_review_probe.py
```

产物按格比较全部矩形和字节来源，检查格查询可反查，比较两份运行中其余 14 层的 drawn/effective 片、region/piece 和来源；同时查验原图、固定框、坐标声明路径与实际哈希、仓库快照和未封存的 attempt。

```text
x_cells 6 global True availability reconstructed fragments 24 area 720 GDS_offset 432
x_cells 5 global False availability incomplete fragments 0 area 0 GDS_offset 432
```

探针退出码为 0。两例的格片、失败定位及其它 14 层比对均符合预期。二维栅上的 `gate_track_numbers_available` 均为 False，其余 14 层均为 None，两个 attempt 保持 unsealed。

检查受审 diff 的三处修改。普通投影判断沿用 W021 的逐源覆盖及 `incomplete` 状态，缺少必投声明仍有带来源的 `RequiredProjectionUnavailable`。一维栅轨属性检查实际声明、原图数大于零和每条原图的重建结果。示例按该属性读取栅轨，正式合同覆盖二维完整或越界、一维命中或离轨及原 W018 缺声明。输入 schema、W018 投影和 W021 候选合同的字节与基线一致。

PM-01 已通过独立定向复核，剩余必须修正项为 0，交 PM 验收。其它定向测试和 typing 见执行交接；双解释器全量仍在第 0 版首次发布集成运行。
