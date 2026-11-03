# W009 PM 几何专项核验

- 受审提交：`5b1d9b5196a7c5181822c4dd0f1bd2f678475116`；分支 `codex/w009-effective-geometry-terminals`。
- 角色：PM 接收委派的只读专项检查；不是新的完整独立 premerge review，不作 PM 最终验收/合并决定。
- 结论：本次专项未发现必须修正项。未修改仓库、产品、测试、fixture 或任务记录。

读取了根 AGENTS/README、协作/环境规则、W009 要求、方案、方案及代码复核结论，并对照架构 Stage 2、几何/occupancy/physical connectivity、FIN/gate/OD/CUT 责任边界，检查 `domain/regions.py`、`state/regions.py` 和相应合同测试。

实际实现按 CUT 精确边界作集合差，逐 drawn record 保留贡献来源和空结果；不会按 W008 原占用整格删减、外接 bbox 填洞或按 bbox 丢掉重复 record。内部区域分组只用正长度共享边，角触不合并，未建立跨 record 电气图。沟道正面积相交、唯一 stripe、完整 active 高度和内部 x 条件在本轮矩形 toy profile 中恰好形成完整左 S/右 D；channel/S/D 内部互斥、合计覆盖 active，POLY 原记录保持。聚合构造按原 base/owner 重新计算，未见遗漏/外来片段可以进入成功草稿的路径。集合边界采用半开点归属，后续 contact 使用边界闭包的语义仍由后续任务负责。

独立编写并直接运行 `exhaustive_geometry_probe.py`，不引用 fixture 答案、测试 helper 或产品 canonical-cover 函数作 oracle：

- 穷举 3×3 单元的全部 512 个 CUT 覆盖掩码，合计 41,472 个边界/顶点/中点及外部点归属检查通过。
- 512 组独立四邻接 BFS 连通分量与产品局部区域分组一致，包含洞、分离、角接触、空差集。
- 512 组把单位 CUT 合并成最大行区间后的等覆盖输入，结果完全一致；重复和反序 CUT 亦不改变结果。
- 全部 512 组另经 11 倍缩放及正负 `2**90` 平移，结果精确等于原输出变换；不依赖 float 或固定单位栅格。
- 实际正常 W005→W008→W009 组合通过，保留原 input/base 对象；直接手算核对 2 个 channel、4 个端区的 exact bounds 和完整互斥覆盖。

命令（仓库根目录）：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/Layauto /workspace/work/w005-pm-check-env/bin/python -B /workspace/work/w009-pm/geometry/exhaustive_geometry_probe.py > /workspace/work/w009-pm/geometry/exhaustive_geometry_result.json 2> /workspace/work/w009-pm/geometry/exhaustive_geometry_stderr.txt
```

实际环境 Python 3.12.14 / Linux，进程 exit 0，2.419 s，stderr 空；完整结果保存环境、HEAD、三项相关源码 SHA。采用已有 PM 环境，不作为新包/干净安装证据。未运行全套或复跑全部原 findings；完整矩阵由主 PM 核验。本次有限集合穷举不证明生产规模性能、所有整数输入、完整工艺网格、物理连通、FIN/body 提取或真实 EDA。
