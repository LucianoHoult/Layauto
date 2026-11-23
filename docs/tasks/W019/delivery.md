# W019 执行交付

执行分支为 `codex/w019-single-cell-occupancy-query`。起点为 `d0b8540e0e06326f51f7fd4c56d3e43c7ca667c1`。方案复核先行，受测实现、测试、公开示例和成本探针随后冻结在 `07605914bece908d24f5ff6a92cedb27b9d8d2f9`，Git tree 为 `44cf74fa56e08896fb834c8ce359d5638eac7d51`。[方案复核](design-review.md) · [调用示例](example.py) · [公开接口说明](../../../README.md#query-process-grid-occupancy)

## 公开入口实测

| 验收项 | 临时样本的观察 |
| --- | --- |
| A1 分层查询 | drawn 有 15 层、40 条原记录，FIN、LI、M1 分别有 18、20、10 片。FIN 轨道 0 命中 (10,24)–(110,26)。POLY 有一条记录但缺声明，BOUNDARY 显式跳过，CUT 为零条记录。M1 有效格 (9,9) 返回空元组。 |
| A2 线端 | M1 (2,2) 的格边为 (32,40)–(48,60) DBU，片段为 (32,48)–(45,58) DBU，面积 130 DBU²。从该片回溯 `source.gds` 的 BOUNDARY 偏移 2352，原线为 (0,48)–(45,58)，三个格内宽度依次为 16、16、13 DBU。 |
| A3 tapcell | 三次选择分别为实际无文件且未选择、已选择有效 context、已选且 GDS 哈希绑定错误。三组逐片几何、来源、模型、分层及格号/源记录查询相等。前两次 completed，第三次 rejected 并保留 body 诊断。无外部资料时两条 B 端均 indeterminate，父级状态 unknown。 |
| A4 CUT 及异常 | CUT 专例的 LI 格 (4,1) 有两片，各 36 nm²，间隔 2 nm。两片分别关联真实 region/piece、偏移 182 的 LI 和偏移 246 的 CUT。旧坐标配置的 15 层都报告缺声明。非法键 `x/edge~` 的字段为 `/coordinate_projection/layers/M1/x~1edge~0`，绑定实际 URI 与 SHA-256。主样本 drawn 给 47 片预算时报告需 48 片。加入 effective 后给 48 片预算时报告需 68 片。两者均返回首个越限来源，索引值为空。 |
| A5 成本与兼容 | 首次查询复用 W016 的 layout/effective 对象以及 W018 的绑定与投影实现。从同一成功结果重复查格、查原记录均使用同一个索引。原起点与交付版本对同一路径同一输入的无查询报告 SHA-256 完全一致。 |

主样本的输入哈希和每层记录数、片数可核对 [main-sample.json](evidence/main-sample.json)。特例沿用 W018 配置变体和固定的 CUT GDS，只核对本地几何。测试中的 manifest/header 更新均发生在临时目录。[公开合同测试](../../../tests/contracts/test_w019_analysis_occupancy.py)

## 成本

在隔离安装的 wheel 上，对同一绝对路径、同一输入记录了一次顺序采样。毫秒为该次进程的实测值。读取计数来自实际 `Path.read_bytes`，构建计数在构建入口取得。[原始结果](evidence/cost.json) · [可重跑探针](cost_probe.py)

| 操作 | 文件读取 | layout / effective 构建 | 坐标绑定 / 离散占用构建 | 耗时 | JSON 字节数 |
| --- | ---: | ---: | ---: | ---: | ---: |
| 只分析 | 23 | 1 / 1 | 0 / 0 | 2698.165 ms | 235812 |
| 分析并首次查格 | 23 | 1 / 1 | 1 / 1 | 2939.332 ms | 236050 |
| 原结果上查格并反查 1000 次 | 0 | 0 / 0 | 0 / 0 | 2.477 ms | 236050 |

前两次的 23 个路径各读一次，W016 的 base 分区与原占用也各建一次。新增报告摘要占 238 字节。无查询报告的 SHA-256 为 `1f89eadd7dff4faf923531d4b86d38d80ba60806626c6b80cf2a3086ffe2f821`。绝对样本目录参与 W016 receipt 身份，换目录允许报告哈希随之变化。

## 实跑与复现

交付检查从上述提交的 `git archive` 展开，在 Linux x86_64、CPython 3.12.14 执行。测试选择覆盖 W019、W016 公开入口/报告及 body 对照、W018 坐标与绑定/投影、以及有改动的模块依赖合同。定向测试 107 项全部通过，耗时 194.99 秒。严格 mypy 检查 82 个源文件通过。生成 sdist，再从 sdist 构建 wheel；新的无系统包 venv 从该 wheel 安装。切到源码目录外用 `python -I` 确认导入来自其 site-packages，128 个安装文件与冻结源码逐个相同，公开调用实得偏移 2352 和面积 130。[命令与身份](evidence/verification.json) · [原始运行日志与依赖版本](evidence/transcripts.tar.gz)

从仓库根可在已安装运行依赖的 Python 3.10+ 环境执行短例。若已在临时目录准备了带 W018 坐标声明的本地 manifest，可将其绝对路径作为末尾参数。干净安装冒烟采用后一种调用。

```sh
PYTHONPATH=. python docs/tasks/W019/example.py
```

子任务的定向结果供 review/PM 按同一源码、测试、配置、输入和依赖身份采信。源文件、依赖、绑定样本或集成行为有变化时补跑受影响项。双解释器全量按任务卡留给 PM 合并后的 Stage 2 组合验收。本轮覆盖已声明的 synthetic flat-cell 输入。生产 PDK 和 EDA 留待其相应阶段。
