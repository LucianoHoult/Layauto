# W010 独立合并前复核：精确几何与完整图专项

Reviewer `/root/geometry_review`，2026-11-06；未参与 W010 设计、实现或正式测试。受审 HEAD `c4909ab679d0c0806200fcb132db8a5de1ad3e75`，产品冻结 `0f5029df935bc0acd106aad1bc2be81304d4f442`。本专项新增/剩余必须修正项 **0**；这是数学、局部拓扑与策略拒绝专项，不替代主 reviewer 的完整 A1–A8 或 PM 决定。

读取根 AGENTS、协作/环境规则、W010 要求/方案/执行记录、W003 现行合同与 MR-045/047/052/054/056、W004 body 修订、W008/W009 输入与有效区域合同；回查架构 §2.2–2.3、§3.1/3.4–3.6、§4.7、§8.4–8.5、§12.3/12.5。检查 `state/local_connectivity.py` 全文及新 domain 合同、正式几何测试和旧 reviewer 主 probe；后两者只是覆盖线索，下面的答案由本次新 oracle 产生。

## 本次实跑

环境 `/workspace/.venvs/layauto/bin/python`，Python 3.12.14；checkout `/workspace/Layauto-w010`。全部命令带 `PYTHONDONTWRITEBYTECODE=1` 和 `-B`，输入修改仅在 `/tmp` 临时 fixture 副本，不改正式 fixture、答案或测试。原 stdout/stderr 和最终退出码均保留，详见 [geometry-receipt.json](geometry-receipt.json)。

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/layauto/bin/python -B docs/tasks/W010/independent-premerge-review/geometry-probe.py
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/layauto/bin/python -B docs/tasks/W010/independent-premerge-review/geometry-boundary-probe.py
```

两条命令均已结束，exit 0；主 probe 184.64 秒，补充 probe 52.87 秒。这是共享环境中的正确性验证耗时，不作为产品性能曲线。

- **3,200 项随机精确对照**：1,600 项同层接触、1,600 项有理包围。自写 oracle 将整数矩形集合展开成 unit-square 集合；重叠 square 或 4-neighbor square 证明正面积/正长度接触，纯对角不成立。包围按有理阈值分母整体放大后，对扩张目标的完整 square 集合作 subset 判断。没有调用产品 overlap/slab/canonicalizer 生成答案，没有仅比面积。每四例之一把产品坐标平移到 `2**103, -2**111`，独立答案仍以原小整数集合计算。
- **15 项具名边界对照**：面积、整边、局部边、角点、间隙、孔洞内空隙、孔边接触、多 piece 接触；1nm 等号、`4/3` 不足、`2/3` 足够、跨 pieces 整体包围、孔洞假 bbox、恰触孔边和有理侵入孔洞。全部符合独立集合真值。
- **14 个真实 W005→W008→W009→W010 捕获变体**：8 个成功图逐一比较完整 node 的 owner/role/精确覆盖集合、完整 edge 多重集合、逐侧 audit 多重集合和完整分量成员。另 6 个端点反例以独立 region 的 square 正面积交集算出歧义，再确认明确的 `AmbiguousConnectorEndpoint`、source.gds 定位、原 input/completed 保留；不把“抛任意异常”算通过。
- **3 个真实 owner 反例**：VIA0 错连接对、CONTACT 错 predicate、GCONTACT 错 role 均拒绝为 `UnsupportedLocalContactOperator`，定位分别为 `/layers/9/electrical_connects`、`/layers/8/contact_predicate`、`/layers/10/role`，原 input/completed 保留。

[主脚本](geometry-probe.py)只复用现有 fixture 复制、GDS bytes 编辑和捕获重绑 helper，不复用正式或历史 reviewer 的几何 oracle。对每条 raw record 独立展开有限 unit squares：LI 做集合差并按 4-neighbor 划分区域；OD 以 POLY 占据的 channel 列分出 S/D；其余本地导体保留完整 rectangle。图分量答案通过全节点关系传递闭包取得，产品使用 BFS，两者实现不同。这个 oracle 有意只用于本次有限整数 fixture；不是新的 runtime 坐标网格或验收门槛。

## 关键观察

| 路径 | 预期与本次实际结果 |
| --- | --- |
| 正常 | 手写 14 个完整 layer/role/rectangle 与全量集合 oracle 一致；8 connector 边、6 个完整分量、16 侧 pass；孤立 BN/BP 保留，POLY 为单个完整 region，OD channel 不入图，不产生 S↔D 导体边 |
| cut-islands | 三个精确集合 `[50,20,60,24]`、`[130,20,139,24]`、`[141,20,150,24]` 各成独立分量，0 边/0 audit；保留同展示/同语义标签输入不合并 |
| 实际 via_enclosure | VN `[33,50,37,54]` 的唯一 connector 边保留，完整图仍 14/8/6；LI 侧 violation、M1 侧 pass，整体 local enclosure 为 violation |
| 重复 connector | 重复 VIA0 源 record 各生成独立 source-bound edge 与两侧 audit；全图 14 节点/9 边/6 分量/18 audit，未成为额外导体或被去重 |
| 重复导体、已同层连通候选、包围不足的额外候选 | 分别按独立 region 计数得到歧义；component 合并与 enclosure 均不能消歧，全部明确 error |
| 缺侧、边触、角触 | independent positive-area 候选不足，全部明确 error |
| CUT 新边界 | `x=207/213, y=205` 不在原 LI occupancy 轴；切后多片 region 与邻接 LI 的完整同层 edge 正确保留，全图 16/9/7 |
| 孔洞与跨 pieces | 同一带洞 LI 上的两条 VIA0 均保留真实边；跨 pieces 且恰到孔边的一条 pass，侵入孔洞的一条 violation；完整图 16/10/7、20 audit |
| 负坐标及重排 | 负平移+顶点/record 重排后的全部集合/边/成员逐一匹配；纯 record 重排+query 标签改名保持正常 semantic digest，相同物理成员不因名称变化而变 |

静态定位：`state/local_connectivity.py:27–70` 的判据保持整数/Fraction；`:157–171` 的本地节点选择不纳入外部 context/channel/connector；`:180–203` 按独立 region 先计 positive-area 候选，之后生成 audit，audit 结果不控制 edge 存在；`:208–228` 用全量节点初始化分组，孤立节点不会丢失。完整比较也覆盖保留重复源和一个 region-pair 只计一条同层边。

## 限制与建议

本专项没有发现需修产品的问题，也没有新增验收标准。源认证、完整 nested exception 链、公开 wire/constructor 伪造和单次集合快照由其它专项负责；本专项未重跑 W006 readback 或完整回归、typing、打包/安装。大整数与有理边界在纯 exact 判据实跑，实际 captured 图使用现有 canonical tick=1nm fixture；不声称试过所有单位/profile 或生产规模。没有测试多片最大资源压力，不要求补生产性能曲线。完整制造坐标、region occupancy、外部 body/U06、FIN/器件提取、query 空间标注、其余 mandatory/lifecycle 和发布闭合继续后置。
