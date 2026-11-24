# W019 PM-01 补修独立复核

**PM-01 已复核关闭，可交 PM 重新验收。** 在 `7a984a15b484bdbb0cf70c5ecf4cdafd2dcf4775..708c2a39c3d8a46514ac3aa2c01eb21aa334f9f7` 上审了产品与正式回归的完整差异。受审源码 tree 为 `5cf6ec15cf3171155f893cc06a3ab6495a5ad13d`。PM 原探针在两端相同，SHA-256 为 `0334f7459eb713949a58a980f721170abd13d98b1491a44bc712941835436579`。实跑环境为 Linux、Python 3.12.14。[PM 原问题及范围](../W019-single-cell-occupancy-query.md#pm1-receipt) · [原探针](pm01_probe.py)

### 从报告还原组合原因

从仓库根目录运行 `python -B -m docs.tasks.W019.pm01_probe`。另在探针的 `observe` 返回处独立解析 JSON，由 `facets.occupancy.ref` 进入摘要，沿 `issues.ref`、各 issue 的 `ref` 和 `fields.source.capture` 读取代码、字段及捕获表中的 URI、SHA-256。每组都与实际文件字节和 Python 结果中的来源核对。组合查询报告还原出以下两项，各自与对应单项输入完全一致。

| code | 捕获 URI 及字段 | SHA-256 |
| --- | --- | --- |
| InvalidProjectionDeclaration | `tech/layer-discretization.yaml#/coordinate_projection/layers/M1/y_edges` | `77c8c5c79c6f135339c7a0948f7d2704eb84194ba78a222eaa0035b063f08163` |
| UnsupportedRegionOperator | `tech/physical.json#/operators/rectangle_set_difference~11` | `6e61de7dec745b485734edd5f0ede049d69b09535386ad202930494680db13db` |

### 独立反例与边界

另在同一临时目录使用 `projected_manifest` 建立实际 W016 文件，将坐标 `units_ref` 改为 `formats#/absent`，将 `terminal_split/1` 算子改为 `unimplemented in review`。分别单改、合改后重绑 header，再用预算 0 查询。独立探针命令为 `PYTHONPATH=.:tests/support python -B /workspace/work/w019/pm01_extra_review.py`，临时脚本 SHA-256 为 `a7ccd8a6cfbf90aa5e6ec526341b2d3e638916cbfe6c25d4cb5860eaa78717ed`。

| 输入与选择 | 原分析 / 占用状态 | 由报告引用查得的原因 |
| --- | --- | --- |
| 坐标单错，含 effective | completed / invalid_declaration | InvalidProjectionDeclaration |
| 算子单错，含 effective | unsupported / not_evaluated | UnsupportedRegionOperator |
| 组合，含 effective | unsupported / not_evaluated | 两个单项的并集 |
| 同一组合，仅 drawn | unsupported / invalid_declaration | 查询保留坐标原因，原分析 findings 保留算子原因 |
| 同一组合，无查询 | unsupported / 原报告 | 顶层 findings 与前两种选择相等，报告没有占用摘要 |

此反例中的坐标来源为 `tech/layer-discretization.yaml#/coordinate_projection/units_ref`，SHA-256 为 `e8943cba4d1da1c693fd19e210b3861dc296029f471f713351d08bc72bfac8fd`。算子来源为 `tech/physical.json#/operators/terminal_split~11`，SHA-256 为 `d241cd46ae84d4d45c0ddcf52cc01b3cccdc68cd2d24a346ab5b340a00e68429`。两组定位均由报告还原并核对原始字节。

每次已认证分析保留 40 条 drawn 记录。占用受阻时 `value is None`，禁用投影内核也能取得完整诊断。监测 `Path.read_bytes` 的三组已认证输入均读取 23 个不同文件，每个读取一次。申请占用时坐标 binder 调用一次。无查询时 binder 调用零次。另在未重绑 header 时改变坐标文件字节，公开入口返回 rejected、local=None，查询报告 local_authentication 与 ClosureHashMismatch，binder 和投影内核调用均为零。

独立复核限定于上述来源、组合诊断和查询调用边界。原 W019 的 M1、CUT、预算和 body 结果依照[原交付记录](delivery.md)及[独立代码复核](code-review.md)追溯。补修的执行侧定向矩阵、typing 和安装结果由执行交付记录保管。源码、认证路径、报告格式或关键样本变化时重查相应结论，双解释器全量仍归实际集成后的阶段验收。
