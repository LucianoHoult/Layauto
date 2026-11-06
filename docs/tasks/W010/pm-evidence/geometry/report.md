# W010 PM 几何/局部图专项核验

核验日期：2026-11-06。角色：PM 委派的只读专项 `/root/w010_pm_geometry`；未参与本轮实现或正式测试，不代替完整独立合并前 review 或 PM 验收。

核验对象为 `codex/w010-local-contact-connectivity@ca39aedcb71fda02f77ffda1eb5d5dddc598226e`，准备基线 `9758a157115cc22d91ce095ac2002209b9f210d3`，产品 `0f5029df935bc0acd106aad1bc2be81304d4f442`。四个W010 runtime文件的当前字节与产品提交无差异。**本专项未发现必须修正项。** 未修改仓库、产品、正式测试、fixture、报告或Git状态；只写工作区外本专项材料。

## 静态核验

读取根AGENTS/README、协作/环境规则、W010原要求、实施方案、方案及代码review，回查架构Stage2、§3.6/4.7与domain/state边界；完整核对新domain/state源码，以及normalization认证/构造边界。

- 同层判据按正面积或正长度共享边建边，角/点触不建边；一对独立region只计算一次，不按其内部piece重复计边。
- connector逐原record保留，先按声明两侧独立region的正面积交集计数，候选不经过component合并或enclosure过滤；重复导体来源不会按bbox去重。每条重复connector仍各有独立edge及两侧audit。
- enclosure精确扩张`Fraction(1, canonical_tick_nm)`后检查完整region集合；x slabs和y区间覆盖没有bbox/单片替代，孔洞会失败、跨piece整体覆盖及边界等号可通过。audit结果不删物理edge。
- graph从完整节点集合初始化邻接，包含孤立BODY节点；channel、connector、FIN/CUT/FRAME/MARKER和六个external body图形不成为本地图导体。非空local BTAP定位unsupported，没有BODY↔OD或同名net补边。
- public draft重建binding、全部node/edge/audit/component后比较，完整成员与边集不能靠局部叶DTO伪造；neutral一致性与captured输入再认证分层。此专项不代替父PM的完整公开异常/来源路径验证。

## 本次独立有界实跑

自行编写 `exhaustive_probe.py`，预期值不来自产品几何算法、正式测试helper、fixture答案或原review探针。

- 穷举3×3单元的全部512种覆盖掩码，以整数像素集合的交集和四邻接共享边作为contact oracle：**12,288项**比较通过，包含点/边/重叠/间隙、空集合和`(2**100,-2**100)`平移。
- 针对固定中心connector，用1/6 tick细分格的完整覆盖作为独立enclosure oracle，测试margin `0, 1/3, 1/2, 1, 3/2`，包含孔洞和边界等号：**5,120项**比较通过，含原坐标与大整数平移。该oracle不是产品x-slab/y区间实现；有限闭矩形像素并集的开细分格覆盖同时保证其闭包边界。
- 将单位像素分解改为逐行合并矩形，另作 **8,704项**接触/包围比较，结果保持。以上contact和enclosure均实际覆盖True/False两类结果。

命令（仓库根目录）：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/Layauto /workspace/work/w005-pm-check-env/bin/python -B /workspace/work/w010-pm/geometry/exhaustive_probe.py > /workspace/work/w010-pm/geometry/probe.stdout.json 2> /workspace/work/w010-pm/geometry/probe.stderr.txt
```

Python3.12.14/Linux，进程exit0，stderr空；约 **0.882秒**。原输出保存HEAD、解释器/平台、脚本SHA-256和四个受查runtime文件SHA。脚本SHA-256：`1d97e2653b8d6b71affe0e4f84de9ccfc372fe4ca9d4b36c2386b72d57728008`。

## 范围与限制

此次动态检查只验证有限中立几何谓词和分解/平移不变性；未复跑完整正式测试、原20,000项数学review、原完整公开主probe/异常矩阵、typing、构建/安装、性能或EDA。实际normal/special图、完整captured组合与版本证据由父PM和原独立review分别核验/采信；本专项没有将其冒称本次实跑。未据有限穷举证明所有整数输入、多片资源上界、真实PDK、body、完整mandatory或M1。
