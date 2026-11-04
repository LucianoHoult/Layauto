# W009 独立合并前几何专项复核

日期：2026-11-03；专项 reviewer：`/root/geometry`，未参与原方案或实现。受审 HEAD 为 `88a7ae9d0330b7c7fddda0b07366c7a96552b65e`；完整范围为 main `4df07e68b05df4c57a8b8d44bc41e7e073938d3a` 到该 HEAD，并以准备 `4975e565a33d9594782645b6ad0f944b78ee6ae8` 到产品 `5b1d9b5196a7c5181822c4dd0f1bd2f678475116` 定位实现。没有把最后一个 PM 文档提交当作产品 diff。

**几何专项未发现必须修正项，A3–A5 在声明的 toy 子集内有独立复核依据。** 这不是对 A1–A8 的独立总评、PM 验收或集成决定；其余专项由主 reviewer 汇总。

## 读取与实现检查

读取根 AGENTS、README、协作/本地及跨设备环境说明、W009 要求/方案/方案 review/执行/代码 review/PM1，W008 现行输入/单位/逐 record/base occupancy 要求，W003 contracts（含 W004 body/owner 修订）、MR-045/046、MR-052/054/056，以及架构 §2.2–2.3、§3.1/3.4–3.6、§4.5–4.8、§5.6–5.9、§11.2–11.3/11.14–11.15、§12.3/12.5 对应条款。旧 MR 的本地 BTAP 文字按历史版本理解，现行外部 body context 以 W004 实物与补充合同为准。

- `state/regions.py:31` 的差集仅使用 exact integer 交集和 x slab/y interval，保留所有正面积余量；重叠 CUT 的区间覆盖合并正确，重复 CUT 的几何只作用一次。输出不会以 bbox 填孔。`_groups` 仅按正长度共享边分组，角触片仍分开。
- `state/regions.py:112` 为每个 LI 原 record 独立计算；贡献来源来自全部正面积命中 CUT，按 typed id 排序。全覆盖仍有 `RecordRegions` 空结果，重复 LI 没有按几何去重；未命中及边角触 CUT 不进入贡献列表。
- `state/regions.py:121` 按正面积交集筛选 POLY，以完整 drawn 矩形区分 stripe。相同矩形的重复 POLY 保留各来源；不同矩形同时命中拒绝，不把部分交叠或相同裁剪交集猜成同一 stripe。full-y、strict interior-x 检查对当前矩形 active 恰好保证完整左 S/右 D。channel、S、D 内部互斥且并集为 active，没有使用展示名或正常数量。
- 差集直接读取原 exact rect，未按 W008 raw occupancy 整格删除。内部 slab 与原 partition、工艺坐标和后续接触谓词的职责在模块、方案、README 和执行交接中明确。半开点归属用于索引；局部分组不生成跨 record 或 S↔D 电气导体边。
- `domain/regions.py` 的 canonical cover、正面积互斥/连通检查，与 `EffectiveDraft` 按原 base/owner 重建完整 record 集合相配合。单 DTO 自洽不等于捕获认证；本专项未把中立 DTO 当作真实输入收据。

## 新的独立实跑

复验命令（在仓库根目录）：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD" \
  /workspace/.venvs/layauto/bin/python -B \
  docs/tasks/W009/independent-premerge-review/geometry/probe.py
```

本次实际使用 `/workspace/work/w009-review`、Python 3.12.14；退出 0，stderr 为空，耗时 50.643 秒。[脚本](probe.py)及[原输出](result.json)保留源码 SHA 和受审 HEAD。临时 capture 仅在 `/workspace/work` 下创建并随运行结束移除；没有修改产品、正式测试、fixture、答案或历史证据。

数学 oracle 是独立的 unit-pixel 集合减法和四邻接 flood fill。产品的 `slab_difference`/`_groups` 仅作为被测对象，不供应 expected 值，也不使用原测试 helper 的数学 oracle。

| 实跑范围 | 独立判据与结果 |
| --- | --- |
| 4×3 单位格全部 4096 个 CUT 覆盖掩码 | 精确剩余 pixel 集合、每组的完整 pixel membership、四邻接分组、面积和内部互斥全部一致；覆盖洞、多片、全空、未切、边和角接触 |
| 320 个固定种子随机矩形 CUT 集合 | CUT 可超出 target、重叠、重复或不命中；逐半单位坐标含边/顶点检查，原顺序与反序加重复 CUT 结果一致 |
| 2 个大整数仿射变换 | 包括比例 `2**80+1`、平移到 `2**127`/`2**512` 量级；以原像精确点归属验证，不 rasterize 巨大包围盒 |
| 总计 4418 组、521222 个点检查 | 全部通过；前 4416 组另比较完整局部连通分区。最多观测 7 个矩形片、6 个局部组 |
| 真实 normal W005→W008→W009 | 手写答案得到 `[58,20,62,70]`、`[58,110,62,180]` 两个 channel；四端区为 `[20,20,58,70]`、`[62,20,100,70]`、`[20,110,58,180]`、`[62,110,100,180]` |
| 原 special/cut_islands，经临时重绑 capture | LB 为 `[130,20,139,24]`、`[141,20,150,24]`，面积 72；A_REMOTE `[50,20,60,24]` 原样保留 |
| 12 个单 active/gate 场景 | 无 gate、边/角触、多 stripe、不同且重叠 stripe、drawn 不同但裁剪交集相同均拒绝；部分高度、贴左边、横向、全覆盖均拒绝；唯一 stripe 和完全重复 POLY 成功且保留贡献重数 |
| 真实 duplicate targets/CUT 与 GDS 反排 | 两个相同 LI 各保留不同 id；两个相同 CUT 和一个重叠 CUT 各保留来源，边触 CUT 不计贡献；孔洞余量 exact membership 一致，反排的 semantic digest 一致 |

后一个 capture 另外直接核对每个 LI 的 W008 raw occupancy 仍只有完整 `[200,200,210,210]` 一个 cell/fragment，CUT 内部边界没有进入 LI raw axes；W009 正确保留孔洞，证明该见证没有按整格删减。

测试输入变换复用了既有 `ready_copy`、`rewrite_geometry`、`special_input`，仅用于临时字节修改和 header/body/query 的绑定；没有导入它们的面积、集合或端区答案 helper。normal/special 的几何 expected 均在本脚本中手写；运行产品不读取 expected/spec/oracle。

## 范围、复杂度和剩余限制

执行交接的 O(m² log m) slab 上界、O(m²) 输出增长、O(p²) 分组及 region 自检/canonical cover 成本，与实际嵌套循环一致；完整公开链还有 base/capture 重建与严格原对象图遍历成本，文档没有只报核心差集复杂度。现有有限压力记录明确区分真实 capture、neutral stress 与纯差集，没有新增外部规模限制或生产性能保证。本次 probe 也不承担性能基准职责。

完整工艺坐标、region occupancy 投影、物理接触/电气连接图、canonical device/net join、FIN/body 提取、query overlay、规则、baseline/seal/no_change、Stage6、真实 EDA 和 U06 生产缺外部上下文方案均不在本轮几何结论中。当前 synthetic `body_context` 必填合同保持。

本专项没有重跑双解释器、构建或干净安装；没有将历史日志一致性称为重新安装或重新观察历史执行。全量回归、typing、来源与原对象图/异常路径及包证据身份由主 reviewer 和其他独立专项核验。有限穷举及随机见证不能替代全整数域形式化证明；本专项无额外阻塞建议。
