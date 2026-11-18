# W016 PM 交付复核与补修交接

被审产品提交为 `fa78b42ae1dbcf74dfeaa7060ea3b4e66753a6e0`。**PM-01（P2）阻止本次验收及合并**。独立实现 review 在其覆盖范围内关闭了 R01–R10，本次发现来自另一组组合输入。

## PM-01 已知的端口绑定错误在几何阶段提前返回时丢失

在与来源绑定的 synthetic 样本文件副本上，PM 经公开 API 运行以下四组输入。各组独立生成临时 manifest，按实际文件内容重算 header 闭包。CDL 变体将所选 cell 的端口数从 4 改为 3，query 的 source 端口数保留为 4。几何变体选择一个当前实现不支持的比较规则。

| 输入 | 实际请求状态 | 对调用方可见的事实 |
| --- | --- | --- |
| 正常无外部 body | completed | FIN 为 5/7，六个 D/G/S 核对一致，两 B 待证明，父级未知 |
| 只有端口数不一致 | rejected | 报告 SourceTopIdentityMismatch，指向 query/raw/iXref.temp |
| 只有几何规则不支持 | unsupported | 报告 UnsupportedGeometryComparator，指向 tech/formats.json |
| 两项同时存在 | unsupported | 只报告 UnsupportedGeometryComparator |

最后一行应保留两项已知诊断及其来源，并按已采纳的状态优先级返回 `rejected`。当前行为会让调用者只看到几何能力限制，漏掉需要修正的 CDL/query 绑定。所有四组都没有选择 body 文件。[W015 结果合同](../../W015/entry-contract.md) · [PM 实际输出](public_checks.stdout.json)

`normalization/analysis.py::analyze_local` 在构建几何前已取得 `semantic_issues`。几何异常分支随后返回，此时语义问题尚未放入任何返回值。公开入口只能按剩余的几何诊断汇总。这一顺序解释了单项可见、组合丢失的结果。修复时应保留已计算的问题、来源和已经取得的本地事实。依赖未满足的计算继续显示未执行。单纯调整顶层状态优先级无法恢复丢失的诊断。

复现命令为 `python -B docs/tasks/W016/pm-delivery-review/public_checks.py`，在仓库根目录运行。本次使用 Python 3.12.14，退出码 1 来自组合结果断言。检查脚本只在临时目录更改 synthetic 输入。[复现脚本](public_checks.py) · [原断言输出](public_checks.stderr.txt)

## 交付证据

PM 核对冻结清单的 298 项文件、11 份工程命令的冻结身份、退出状态与输出哈希，以及四路旧接口比较报告与固定 fixture 身份。两个解释器各有 1953 项 unit/contracts 和 3 项 fixture_support 通过。既有双矩阵、typing、构建及安装结果按该版本采信。资源原记录中三次公开调用约 2.67–3.10 秒，进程峰值低于 29 MiB，继续沿用 PM1 的体积优化后置决定。完整产品矩阵和资源测量本轮均采信原记录，PM 本轮实跑的是上述四组公开调用。[证据核对](evidence-check.json) · [执行交付](../delivery.md)

## 给原执行 session 的 prompt

> 继续 W016，在 codex/w016-single-cell-analysis 最新 PM 补记上修复 PM-01。先读本记录，在当前产品提交复现四组输入。沿 analyze_local 的来源准入与几何提前返回路径保留独立错误，检查共享提前返回的同类路径。用实际临时文件新增定向回归，覆盖单项控制和组合结果，核两种原始诊断、来源、rejected 优先级、本地已知和未执行范围。原 PM 失败材料保留，修后验证写入新位置。
>
> 按项目 verification-reuse 先跑受影响检查，由未参与修复者用公开 API 独立复核。最后按 W016 A8 在修后冻结版本完成规定的双版本工程验证。对旧接口及资源证据按改动影响说明哪些可继续采信、哪些需要补测。提交并推送原分支，给 PM 完整 SHA、独立结论和验证范围，留待 PM 决定合并。
