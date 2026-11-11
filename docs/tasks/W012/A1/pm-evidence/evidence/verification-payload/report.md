# W012 A1 PM 专项证据核验：最终工程与包

对象为 `/workspace/Layauto` 原分支 `codex/w012-compatible-hex-validation`、HEAD `db07a16fb7cbbac030adae84a9eb88cc0c8aa650`。只读仓库；产物仅写本目录。最终脚本 1286 项轻量检查通过，交付问题 0。读取了根 AGENTS、README、协作规则、local-setup/remote-development、A1 performance-analysis/independent-review；目标树无下层 AGENTS。

## 实际核验

- 当前 263 项源/测试/配置逐项 SHA-256 等于 `verification-r2/source-manifest.json`，也逐项等于产品/测试冻结提交 `ca1f810c3c97376f71089d8b4054760ff198012f`。tar 内真实 263 个文件逐项内容 hash 相同。100 个 runtime 项是清单中的完整 runtime 子集。
- 直接读取最终 r2 21 条原命令、逐条 command JSON 和原 stdout/stderr。21 条 exit code 均为 0，stdout/stderr 实际 hash 与回执相符。runner/smoke 脚本 hash、source-manifest/source-snapshot hash 也吻合。
- 独立解析两侧 collection 原 stdout 的真实 node ID：各 1656，两个解释器集合相同；原 baseline collection 1605 项全部保留，新增 51 项全部来自 `tests/contracts/test_w012_hex_validation.py`。原 pytest stdout 为 Python 3.10.22：`1656 passed in 7939.88s`；3.12.14：`1656 passed in 5716.06s`。双 strict typing 原 stdout 各 54 源文件无问题，双 dev 和双安装 pip check 均成功。
- 四个真实 wheel/sdist blob 本机可读；重新 hash 包 blob、读每包真实 100 个 runtime 成员并逐项 hash。各侧 wheel/sdist runtime payload 完全相同，before/after 唯一 runtime payload 差异是 `domain/codec.py`。after 两包 runtime payload 也逐项等于当前/冻结 runtime。
- 实读 `before-source.tar` 全部普通文件并逐项 hash，精确等于 `before-source-identity.selected_files`；其 100 runtime hash 同时等于 before identity、performance frozen `sources.before` 和真实 before 包 runtime payload。
- 安装报告确实选择 3.10 sdist、3.12 wheel；pip 原 report 的本地 artifact URL/hash 与实际包相符。保存的两套安装身份各含 100 个 runtime hash，逐项等于实际 after 包和冻结源。
- 两条保存的 smoke 原命令均 `-I -B`，cwd 在 checkout 和工程 snapshot 之外；原 stdout 指向对应 clean 安装包，完成 direct/readback/mismatch 三路径。计数正常 5/7、mismatch 4/7；36 项 FIN evaluation 的详细断言在已绑定 hash 的 smoke 脚本中，输出的 18 原 FIN、14 node/8 edge/6 component、T05 pass、body 6 及 attempt/checkpoint 不变、无 terminal 均闭合。
- manifest 真实覆盖/hash 全部核对：r2 78 项、before-package 18 项、handoff-artifact 430 项、review-evidence 66 项。没有把这些核验条数当正式产品测试数。

## 采信与限制

本次没有重跑 pytest、typing、构建、安装、smoke、codec 或性能；工程执行结果基于上述已核身份的原命令/输出采信。

两套原安装树及其 Python 解释器当前均不可访问（保存路径 `/workspace/w012-a1-final-r2/clean-310/...` 与 `clean-312/...`）。因此本次不能直接重新读取那两套安装文件，采信保留的安装身份逐文件 hash、真实包、pip report、源码外 `-I -B` 原命令/输出链。该可访问性限制不冒称为本机安装复验。

before 两包是本轮从原源重建的可访问 artifact；原材料没有 before 安装/smoke，本次也没有作此宣称。源码外 smoke URI 指向工程 snapshot，不能拿它的 wire hash 与固定原 URI 性能样本混比。

## 核验器自身修正记录

初次 checker 错把结构化 `review-evidence-manifest` 当平面映射，报本机检查器路径解析错误；第二次把 baseline stdout 的空行和结尾统计行也当 node ID，出现三条检查器误报。修正为读取 `files` 映射、只解析真实 `tests/...::...` node ID 后，1286 项全部通过。保留 `attempt01-stderr.txt`、`attempt02-*`，这些不是交付产品或原测试失败。

完整逐项结果见 `result.json`；可重复只读脚本为 `check.py`，本次调用及输出身份见 `command.json`。
