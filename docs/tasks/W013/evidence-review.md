# W013 实施前交接证据独立核证

核证者：`/root/validation_inventory`，2026-11-12。未参与方案设计或产品实现；
本轮仅写本文件，不代写方案 reviewer 结论或 PM 决定。

受核本地 HEAD 为 `0794d2dc90baaf8d3180e9ce4f4d91683fe90dc7`；准备基线为
`d6182fe6893c26490f9d58c6b808a5ce9910384b`。核查时 `interface-plan.md`
已有未提交修订，方案复核由独立 reviewer 负责。本报告不代替方案门结论。

## 实际核证

- 逐项重算旧 A1 manifest 的 **263** 份文件 SHA-256，0 缺失、0 变化；manifest
  `docs/tasks/W012/A1/verification-r2/source-manifest.json` 自身 hash 为
  `d42efdb27b72973a8a6f5f738d57a2fcecdde7bfe89c7b944e7144b3b088915b`，
  与本轮 `preflight-audit.json` 引用相同。
- 实读 `preflight-audit.py`：其 probe 使用当前解释器、仓库根 cwd，保留原 stdout/stderr、
  argv/返回码/耗时及脚本和 stdout hash。`input-boundary-probe.py` 的 hash
  `151d5afe6c73d91e5d214e774b94274cf9c6a315d431c350d1db517e50e3395f`、
  原 stdout hash `e95cb7ea6fbe3e72969a566c47247952c6ff032b32ac4c8ce1f59cf726423847`
  均匹配回执；原 stderr 为空。原输出列出的 10 个来源文件逐项重算一致。
- 独立以 Python 3.12.14、`PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.`、`-B`，在
  `/workspace/Layauto` 通过 stdlib `runpy.run_path(..., run_name='__main__')`
  重跑原 `input-boundary-probe.py`，仅在内存捕获其 JSON，不覆盖原材料；exit 0，
  约 0.929s。与原 JSON 比较仅 `head` 从准备基线变为上述本地 HEAD；4 个真实 net
  identity、8 个真实 seed、`1`/`7` 接受及 `007` 原 ValueError 均重现。
- 原回执未单列继承的 `PYTHONPATH`，因此不能仅凭该回执证明历史进程的 import 搜索路径。
  本次显式 `PYTHONPATH=.` 另以 `layauto_v2.__file__` / `inspect.getsourcefile`
  核得 package、`read_inputs`、`from_parse_result`、`normalize` 全部来自当前 checkout：

| 对象 | 文件（均在 `/workspace/Layauto/`） | SHA-256 |
| --- | --- | --- |
| package | `layauto_v2/__init__.py` | `4660c29e97188f1bf0efdacc758eb59deb5ef72a05e30675633033c6f43f6e05` |
| read_inputs | `layauto_v2/importers/reader.py` | `ea43085a6dcafdde759a8c930446b911aac33f2a37a82e3c3daabad5c5f947f7` |
| from_parse_result | `layauto_v2/normalization/input.py` | `2a50146fd4083ec6ee6fd6c12da52def6057341e4a3e68ddcf9686a9beb52cd9` |
| normalize | `layauto_v2/normalization/component.py` | `7eaef9bfb41e2ee14e65444d37066bd14388f56aaedb725bf9571982a8b96c69` |

上述独立重现和来源核查足以支撑本次实施前输入事实，不追认历史进程未记录的环境。
后续新产品回执须显式保留环境覆盖与实际 import 来源；当前没有因此必须重复重型矩阵的理由。

- 对准备基线检查实际 tracked diff，改动仅本任务执行区及 `docs/tasks/W013/` 新材料；
  runtime/tests/config/fixture、旧报告/finding、architecture/collaboration/current-work 均未变。
  当前未跟踪文件也仅在 W013 review-evidence 内。任务 PM 要求与阶段所在前缀，以及 PM
  验收段，逐字节与准备基线相同；没有代改 PM 阶段或 current-work。
- 用 `git show 0794d2dc90baaf8d3180e9ce4f4d91683fe90dc7:docs/tasks/W013/interface-plan.md`
  重建初审原方案，SHA-256 为
  `dabb22fb38e5090c54c927602458db286f14578a148a20a7917d204964b53f40`，
  与初审报告一致。原失败/finding 可从该不可变提交取得；修订文件不替代原审身份。

## 结论及验证复用

本次交接的来源和变更范围核证通过，无新增证据必须项；**W013 新产品尚未实施，
A1–A8 未完成**。方案门与 P01 未决事项以 `interface-review.md` / `pm-decision.md`
的独立记录为准，本报告不能关闭它们。

交接前补核：修后方案 hash
`827dd88dd7eb638fa8ec98b15768e9ccb30880eed549d4257fc5337abda1830d`，
与 reviewer 修订复核所列相同；复核报告 hash
`28b935f319b5f6b1d5e9537a1bffe701d27be9dffb3173c3d20788417a689b5f`。
报告明确 PR-02/03 只在方案层关闭、PR-01/P01 仍开放、整体未通过实施门。
PM 材料的恢复点补记与这一结论一致（当前 hash
`832861b5653d5a3dce8f1e9b38dacd9235ef0837c400a04a5cd3991291de0819`），
未将任何选项写成批准。再次核得263文件和任务PM要求/阶段/验收段均不变。

| 类别 | 本轮范围 |
| --- | --- |
| 实跑 | 上述文件/hash、实际 diff、PM 原文对比、原 probe 独立重现、当前 import 来源核查 |
| 按身份采信 | 仅与263文件逐项相同的旧A1上游历史证据，不将历史秒数当本机新测 |
| 未覆盖 | W013代码、wire、三路资源组合、新冻结双3.10/3.12全量/typing/build/双干净安装smoke、代码/组合/资源review |
| 补跑触发 | 关键输入决定/方案改变、源码/测试/config/依赖变化、身份缺失或新风险；新产品最终矩阵仍须重新冻结执行 |

没有运行重型组合或矩阵，没有用旧 A1 矩阵代替 W013 最终验证。
