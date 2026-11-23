# W019 独立代码复核

**结论：可以交 PM 验收，必须修复项为 0。** 受审范围为 `d0b8540e0e06326f51f7fd4c56d3e43c7ca667c1..07605914bece908d24f5ff6a92cedb27b9d8d2f9`。独立 reviewer 在 Linux、Python 3.12.14 上审查代码、消费者合同、测试、示例及成本探针。以下命令从仓库根目录运行。[可复现探针](review_probe.py)

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. python docs/tasks/W019/review_probe.py
python -m pytest -q \
  tests/contracts/test_w019_analysis_occupancy.py::test_effective_cut_islands_preserve_piece_and_contributor_ids \
  tests/contracts/test_w019_analysis_occupancy.py::test_invalid_declaration_and_capture_drift
```

| 核查 | 独立实测与判断 |
| --- | --- |
| 两个认证入口与同源性 | 给 W018 完整输入链与 W019 本地 manifest 提供同字节的 GDS 和六个工艺 owner。两次返回的坐标模型和 48 个 drawn 片段逐项相等。W016 的索引持有本次已构建的 layout 和 effective 对象。阅读两条认证链确认，几何、坐标与来源在共享 binder 前均已绑定，同一调用无法另选坐标文件。 |
| A1/A2 的交集与反查 | 探针对 48 片分别从其 GDS 偏移按流记录长度寻找 XY，按大端有符号整数解码，用手工格边作裁剪；FIN 用原 Y 边计算轨号。M1 (2,2) 命中 X=32–45、Y=48–58，面积 130，偏移 2352 的原线 X=0–45。 |
| A3 独立的 body 错误 | 在同一绝对路径由实际无外部文件且未选择，改为显式选择缺失文件并重绑本地 header。原分析请求为 completed，后者保留 rejected 和 external_body.error，68 个 drawn/effective 片段全部相等。另核验执行测试中有效 synthetic context、GDS 绑定错误及无 body 时 B/父级不足三条路径。 |
| A4 超预算、CUT 与声明错误 | 68 片恰好成功，降到 67 返回完整所需数、首个越限的有效 piece 及空索引。上述两项 pytest 实跑均通过。固定 CUT 流在 LI (4,1) 产生两片各 36 nm²、间距 2 nm，region/piece 与 LI/CUT 来源可回查。坐标字段中的斜线和波浪号正确转义并保留原 URI、SHA-256。 |
| A5 来源变化与旧索引 | 同一 GDS 下将实际 M1 X pitch 从 16 改为 15，先观察到陈旧 header 的 ClosureHashMismatch；重绑后原线正好填满三个 15 DBU，第四格为空，模型身份改变。禁止文件读、打开与 resolve 后，旧索引仍返回 16/16/13 和原片段对象。 |

**文档建议已落实。** W018 的 `view` 参数筛选已构建的片段。传递 drawn-only 索引时，调用方查询 effective 也会筛出空元组。已核对 README 的补充说明，消费者先检查 `index.effective is not None` 即可判断该视图是否被请求。[公开调用约定](../../../README.md#query-process-grid-occupancy)

**证据身份。** 独立比对了冻结副本中产品、配置、测试、fixture、示例及 W018 样例声明共 316 个 Git blob，均等于受审提交。定向检查所用主 GDS 的 SHA-256 为 `97cf8d88771ff97f2cf189f6ae6a2fdcce585fc14f93c93d0ecf32326b415429`，CUT GDS 为 `1f57cb548544c934827f49d3ffb181048efc55e02976ab7ebe66b43621a37ef2`。另用干净 venv 的 `python -I` 检查 wheel、site-packages 和冻结源的 128 个包文件逐字节相同，wheel SHA-256 为 `afb6d636f1fc2e9a9f9688585c82a399a09f473f3a5f52aa76833411db4d39a1`。

在上述身份上采信执行者的严格类型检查、构建、安装、依赖检查和安装后公开入口冒烟。原版本与本版无查询报告字节一致，首次查询多 238 字节；1,000 次查格加反查实测新增读取和构建次数均为零。执行记录保存定向矩阵及单次计时的原始结果。[执行与验证](delivery.md)

此次独立检查覆盖 synthetic flat-cell 接口与所列反例。相关代码、配置、依赖或样本字节变化后应重核受影响结论，合并版本的双解释器全量由 PM 在 Stage 2 阶段执行。
