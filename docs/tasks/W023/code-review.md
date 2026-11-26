# W023 独立实现复核

对照 W023 A1–A5 审阅 `74b05f5dcfa5aa1513993460385510ebab22163f` 至 `9f6fa09ce79c2b9c731c909b5a2e526a06e66c47` 的 runtime、发布 DTO/codec、定向合同及样本准备。初次实现为 `f1bcbda88b6b1b6b524ef50188072ab98356cb15`。[任务](../W023-atomic-baseline-publication.md) · [方案复核](plan-review.md) · [独立探针](review_probe.py)

## 发现及处置

| 编号 | 发现与影响 | 修正 |
| --- | --- | --- |
| R1 | 同一 ready 的预组装候选有 312 个片段。把请求预算改为 0，首版事务仍接受 prepare，允许其取得一份可提交的 prepared。用同一 recipe 从 pipeline 调用则无法在该预算下组装。 | `8309595f205ed4a485ea7fd8f8681fe92e820e9d` 在 prepare 核对候选预算。另从仓库比对 ready 的 attempt、tool、parse、evidence 列表与已解析值摘要。 |
| R2 | B 请求 A 的已发布 head。A 的 checkpoint、parse 或 evidence 任一内容缺失时，原逻辑只比较快照、事件与独立目标中的 checkpoint 引用相等。B 自己的审计完好，仍可能成功封存到来源链已断的版本。 | `9f6fa09ce79c2b9c731c909b5a2e526a06e66c47` 在 seal_context 的同一锁内解析 A 的原 checkpoint 和捕获链，并重新对照 snapshot.binding。B 的独立证据继续单独核对。 |

## 读者探针

从 Git tree 导出源码至独立目录，Linux / CPython 3.12.14，使用正常 target 的 W003/W004 副本和 W022 完整 synthetic 坐标。W006 捕获后删除临时输入目录。以仓库内的 ready 和审计完成组装；读取时已经释放候选与 prepared。复跑最终版请在仓库根目录执行以下命令。

```sh
PYTHONPATH=.:tests/contracts python -B docs/tasks/W023/review_probe.py --check-origin
```

复现历史差异时保留交付版的探针文件，分别将源码和 `tests/contracts` 换成表中提交的检出目录。在首版附加 `--expect-old-budget`，在预算修正版使用默认参数。本次重型运行通过同一个 flock 串行。

| 独立观察 | 判据 |
| --- | --- |
| 切换前和切换后 | 在两个故障点分别从公开的 snapshot() 观察完整仓库。切换后抛出 KeyboardInterrupt，捕获它并按最初的 recipe 从 publish_stage2 重放。比较 generation、回执数、内容引用、head、context 和 attempt。 |
| 物理来源 | 以 struct 读取输入 GDS 的 BOUNDARY/LAYER/DATATYPE/XY/ENDEL，按 drawn 的 M1 层号和 datatype 筛选，直接由原始 XY 得出四个外框。按显式工艺格边逐格求矩形交；按 GDS 偏移和实际格号逐项与已发布几何及占用比较。 |
| 封存前置 | 同 run、同 checkpoint，检查 0 预算搭配 312 片候选，以及倒置 evidence 引用顺序和替换 ready.value 两个单变量。B 另从原版指定 head 和新捕获开始，分别使 A 的原 checkpoint、parse 或一条 evidence 在后端缺失，保留所有原公开引用。 |

## 实跑结果与结论

首版实跑得到 `budget_zero_with_prebuilt_312=accepted`。预算补修版返回 `BindingConflict`，而 B 在 A 缺少 checkpoint、parse、evidence 的三组独立故障中均得到成功回执。最终版的三组故障均返回带有实际缺失引用的 `RefConflict`；每次拒绝后仓库仍指向故障注入时的同一 root，B 的 attempt 保持本次捕获完成时的状态。

在最终版 `9f6fa09ce79c2b9c731c909b5a2e526a06e66c47`（tree `5410ec3450c21bd55fedb1204bde59a506d48359`）实跑通过以下检查。

- 0 预算配 312 片候选返回 `BindingConflict`。倒置 ready 的 evidence 引用或替换解析值均返回 `ReadbackConflict`。拒绝前后仓库读者看到的完整内容相等。
- 正常初始化的切换前 generation 为 2；切换后为 3，回执数加 1，增加一个 snapshot、初始化事件、head、目标、封存上下文和新 revision 的 attempt 记录。切换后响应被中断，公开入口重放得到同一上下文，generation 保持 3。attempt 为 `sealed_open`、revision 2，版本为 0、ECO 提交数为 0。
- M1 的 4 条原图和 10 个格片逐条相等。偏移 2352 的线端在 (2, 2) 为 (32,48)–(45,58)，面积 130 DBU²。另在偏移 2480 的原图 (50,90)–(75,98) 核出格 (3,4) 为 (50,90)–(64,98)，面积 112 DBU²。原图 SHA-256 为 `97cf8d88771ff97f2cf189f6ae6a2fdcce585fc14f93c93d0ecf32326b415429`，与仓库绑定相等。
- 独立运行的 head 为 `state_head:independent-reader:29a998edab44ea16cd34771a46bd1f1c228cf9a48d39cbfa53a6821e8eb94957`，快照为 `snapshot:independent-reader:04d5b7b1387bb5002ea1eecd86a2834016cbb3ce06df91e25e447a2226344dbb`。这些引用包含本次临时输入路径所绑定的运行身份。坐标 SHA-256 为 `cd25a045187c22d23040ea45363043b33b497d6318890a73a15782b293346009`，正常 target 为 `ddfd4713579743f578170efede62ce978a02680b42e5e2a6faeeb99016cff8db`，运行依赖 PyYAML 6.0.3。

**独立复核通过。R1、R2 已关闭，无剩余必须修正项。** 对两 run 竞争、C13、LI 直接标注、未知区域、synthetic body、二维 POLY 及实际重绑拒绝，审阅了执行侧合同断言和其所覆盖的代码改动；这些项目的实跑以任务卡执行证据为准。复核范围是单进程、synthetic 输入的 Stage 2。影响发布、绑定、来源、输入或依赖的改动应重跑相应合同和探针；实际集成版组合及 Python 3.10/3.12 全量由 PM 执行。
