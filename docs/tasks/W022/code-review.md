# W022 独立代码复核

受审范围从 `6581c250cf0d11b1869d96202d490a2d077ab9ea` 到 `1a576c8fa3f5afc25cbc9ab5ddc518ed21201574`，受审 tree 为 `dc2e87f6e49e13a0e04d04378c3665d942982050`。审阅者未参与实现。对照[任务卡](../W022-layer-initialization-checks.md)、[实施前复核](plan-review.md)和生产者源码，检查了产品、合同、示例与 typing 配置的实际 diff。

| 验收项 | 复核依据和结果 |
|---|---|
| A1、A2 | 检查从单一候选构造，重新按已认证 GDS 元素、字节定位、顶层、精确单位及 drawn 映射生成期望签名，按层与实际记录逐项比较。相同几何、不同偏移仍保留重数。合同中注入同形 MARKER 丢失和错框，两者都有具体源位置。固定框核对唯一 boundary 角色和同一原记录，T01 的零边距适用于全部非框原图。 |
| A3 | W018 的半开格求交和轨带构造保证同一来源内的片互不重叠，W021 分 drawn 记录及 effective piece 核算精确面积。W022 沿用同一候选的索引和诊断。另核对 CUT 独立专例和完整电路中相同几何的合同。 |
| A4 | W005 校验 required_operator_refs 与算子字典。缺算子、缺比较器在 Stage 1 保留原错误；W008 检查所选比较器语义，W018 的 ProjectionConfigError 保留具体字段和先前几何。W022 自行比对 lifecycle/1、T01 及层职责，必投空层也需坐标；二维栅覆盖仍缺栅轨。 |
| A5 | 事务可以直接读中立 state 模块的 LayerInitializationChecks。其层表由候选派生，字段冻结，对外使用只读映射，依赖没有反向进入 normalization 或 transactions。结果可回查候选的 unknown 区域、外部 synthetic body、target 差异和原 capture。两个样张都测到仓库快照相等。首次检查的增量 Python 驻留量和诊断 JSON 体积是不同口径。 |

## 独立实跑

Linux、CPython 3.12.14，在仓库根目录、项目依赖已安装的环境下执行以下命令。探针直接按 GDS 大端记录长度前进，解码 BOUNDARY 的层、用途和 XY，按所选 drawn 层映射和坐标配置独立计算预期。输入采自 W003 原始文件和显式配置副本。[复核探针](review_probe.py)

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:tests/contracts python docs/tasks/W022/review_probe.py
PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 python -B -m pytest -p no:cacheprovider -q \
  tests/contracts/test_w018_projection.py::test_cut_islands_same_cell_loses_no_area_or_provenance
```

- 完整配置逐一对上 15 层和全部 40 条 GDS 记录的偏移。POLY 命中 -3 号轨，中心 60 nm、原图偏移 432。M1 偏移 2352 的线端与 (2,2) 格相交为 (32,48,45,58)，精确面积 130 DBU²。
- 缩窗只将 M1 的 X 方向从 10 格改为 2 格，右边缘变为 32 DBU。直接解码的四条 M1 右边缘依次为 45、45、75、110 DBU，均超出。该层恢复数为 0/4，四条 outside_range 回指偏移 2352、2416、2480、2544；其余 14 层逐层通过。
- W018 CUT 专例实跑 1 passed。按 GDS 偏移 182 和 246 的 LI 与 CUT 作差，在格 (4,1) 得到两个 9 × 4 nm 的矩形，各 36 nm²，间隔 2 nm。

按受审产品版本对照[首次实测样张](evidence/first-check.json)，其 SHA-256 为 `f1896d0f62a16deab8ffef4296b96aa4ae8468a4462e78d4819b8756ed134fee`，28,117 字节。原 W018 有 10 层缺坐标，完整 W022 有 10 层完成重建、2 层显式跳过、3 层有声明且无本地记录。两份样张与独立复算相符。

本次复核覆盖 synthetic 局部几何、坐标、错误和证据链，剩余必须修正项为 0，可交 PM 验收。受审源的定向测试和 typing 见[执行交接](../W022-layer-initialization-checks.md)。若改变记录签名、层职责、坐标/有效片构造或事务消费边界，应补跑受影响合同和相应探针。版本 0 的原子发布、上下文封存和双解释器全量归后续发布集成节点。
