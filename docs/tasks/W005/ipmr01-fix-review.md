# W005 IPMR-01 局部补修独立复核

日期：2026-11-02。Reviewer：`ipmr01_review`，未参与本轮产品实现或生产回归测试编写。复核使用独立 detached worktree；只写本报告、任务 reviewer 记录及独立验证日志，不改被审实现、已验收输入、答案或原报告。

**结论：在最终产品提交 `0a6de39e02947e3ae8af64a4dca9487ee8898ca3` 上，IPMR-01 及本轮发现的 IPMR01-FR1 均可关闭；剩余必须修正项为 0。** 补修满足 PM2 定向关闭条件，交回 PM 核对集成与验收；本结论不代替 W005 最终验收，不授权合并 main。

## 版本与范围

- 交接基线：`4207e773f93111ba6bfd2c6b6ac9da1eacd87fbb`。
- 首轮补修受审提交：`9c899c7be309c17931eec656ebdb46482ccb3909`。
- 最终产品/生产回归受审提交：`0a6de39e02947e3ae8af64a4dca9487ee8898ca3`。执行证据提交：`9ff519c1e9f04f360b649b5e93a1e05ddd6ff9c2`，独立核对相对前者仅追加文档/日志，产品、测试、构建配置与 README 相同。
- 依据：[PM2](../W005-input-reading-binding.md#pm2-ipmr01-20261102)、[原独立报告的 IPMR-01](independent-premerge-review.md)、架构 §2.2、§11.2、§12.1、§12.6 及协作规则。原 finding 与原执行/review/PM 事实保留。
- 检查字符串 key/value 解析、解码后重复 key、typed 错误与来源/定位/completed、canonical evidence、持久回归及受影响解释器/构建安装证据；不重复全项目审查或代替 PM 验收。

## 首轮发现及原始复现

### IPMR01-FR1 — P2，非法八位 Unicode 转义仍突破 typed 错误边界（最终已关闭）

首轮 `9c899c7…` 的 surrogate pair 修复和新增 34 项回归通过；原三用例已变为缓存 `InvalidUnicodeScalar`、两种合法 note 均成功且可 digest。但是 PyYAML 在新字符串校验前处理八位 `\U` 转义时，越界 Unicode 值仍直接抛出底层异常：

```python
from layauto_v2.domain.evidence import SourceFile
from layauto_v2.importers.config import load_document

load_document(SourceFile('probe', br'{"x":"\U00110000"}'))
# ValueError: chr() arg not in range(0x110000)
load_document(SourceFile('probe', br'{"x":"\UFFFFFFFF"}'))
# OverflowError: Python int too large to convert to C int
```

Reviewer 也通过公共 API 复现：复制 `tests/fixtures/w003_m1` 到临时目录，将 `query/normalized/device_regions.yaml` 的 `schema_version` 设为 marker，再在序列化文本中把 marker 替换为上述任一字面 escape，调用 `read_inputs`。缓存不在 header closure，无需重绑；两例分别裸抛相同异常，调用者拿不到已完成 evidence 与已读 cache bytes/hash。

此输入使用文档层已接受的 YAML 八位 Unicode escape 语法，但值超出 Unicode 范围；属于 PM2 第 1/3 项既有非法字符串与 typed 错误义务。执行者已接收为本轮局部补修必须修正项。没有要求改 canonical codec、扩大格式能力或进入 Stage 2。

## 首轮独立验证

在上述受审提交、Linux x86_64 / CPython 3.12.14，使用 `/workspace/work/w005-ipmr01/dev/bin/python -B`，从 review worktree 执行：

| 直接执行 | 结果 |
| --- | --- |
| `-m pytest -p no:cacheprovider tests/unit/test_w005_unicode.py tests/contracts/test_w005_unicode_inputs.py -q` | **34 passed in 4.02s** |
| `docs/tasks/W005/ipmr01-verification/original_repro.py` | 原 cache 用例返回 `error / InvalidUnicodeScalar`；escaped/literal note 均为同一 U+1F600，成功且 digest 正常 |
| 独立标量探针：边界及固定 seed 的 256 个非 BMP 标量，嵌套 key/value 两种表达 | 与独立构造的 Unicode scalar payload、canonical bytes 全等 |
| 完整 2048 个单 surrogate × key/value | **4096** 例均 `InvalidUnicodeScalar`，source hash 和 token 起始行列匹配 |
| 32 个非 BMP key × 两种 escaped/literal 顺序 | **64** 例均 `DuplicateKey`，定位第二个 key |
| FR1 两种越界八位 escape，直接 loader 与公共缓存路径 | 均复现上述裸异常，因此首轮不能关闭全部字符串边界问题 |

以上有限探针不是所有文档格式的穷尽证明。

## 最终复核

### 关闭依据

| Finding / PM2 条件 | 最终独立核查 |
| --- | --- |
| 原 IPMR-01：合法 pair 与非法 surrogate | `string_value` 在每个字符串节点将合法 high/low pair 转为 Unicode scalar；同一路径用于递归 key/value。孤立、反序及不完整配对为 `InvalidUnicodeScalar`，source 保留实际 hash 与 scalar 起始行列。非 BMP 首尾边界、连续字符及直接 UTF-8 均接纳；codec 未修改，也没有字符忽略/替换。 |
| 解码后重复 key | key 先经过字符串解码，再检查已存在的 key；两种表达和两种顺序均定位第二个 key，拒绝静默覆盖。未知 key 仍进入封闭 schema 校验。 |
| typed cache 错误与已完成依据 | 原复现及新增公共缓存回归均得到具体错误、实际缓存 URI/原 bytes/hash/位置，并完整保留 config、tech、policies、header、gds、source_cdl、target_cdl、body、query 九份 evidence。缓存变体没有重绑或更早 hash 错误遮蔽目标缺陷。 |
| 成功 payload canonical digest | 合法 escaped/literal note 完整重绑后均成功，config 解析语义相同，最终 value 及每份 completed payload 均可 digest。原 bytes/hash 仍不同，测试没有错误要求两个完整 provenance 结果 digest 相同。 |
| IPMR01-FR1 | `_SafeLoader` 只在 flow scalar scanner 捕获 `ValueError/OverflowError`，并核对双引号、当前位置前为 `\U`、八位十六进制且值大于 U+10FFFF。匹配时生成带 mark 且链接原异常的 `ScannerError`，沿既有文档语法路径返回 `InvalidDocumentSyntax`；其他异常重新抛出。直接 loader 和公共 cache key/value 越界探针通过，最大合法 scalar 及字面反斜杠不受影响。 |
| 程序异常与中断 | 五类 scanner 注入异常保留同一异常对象并传播；公共 API 原有 RuntimeError、KeyboardInterrupt、SystemExit 传播回归通过。没有全局捕获或改变 facade 的 `InputError` 边界。 |

### Reviewer 直接执行

以下均绑定最终产品提交 `0a6de39…`。开发环境 CPython 3.12.14，最低版 CPython 3.10.22，PyYAML 6.0.3；读取/探针运行于独立 review worktree。原复现最终明确设置 `PYTHONPATH=.`，日志记录实际导入文件，避免 editable 安装路径混淆。

| 命令 / 检查 | 实际结果及记录 |
| --- | --- |
| 开发版 `python -B -m pytest -p no:cacheprovider tests/unit/test_w005_unicode.py tests/contracts/test_w005_unicode_inputs.py tests/contracts/test_w005_inputs.py::test_interrupts_and_unexpected_errors_preserve_root_cause -q` | **50 passed in 5.16s**，其中新增 47 项，另 3 项既有公共异常/中断回归。见 [review-final-tests.txt](ipmr01-verification/review-final-tests.txt)。 |
| 最低版 `python -B -m pytest -p no:cacheprovider tests/unit/test_w005_unicode.py tests/contracts/test_w005_unicode_inputs.py -q` | **47 passed in 7.07s**，同一日志。 |
| `MYPY_CACHE_DIR=/workspace/work/w005-ipmr01/review-mypy-cache /workspace/work/w005-ipmr01/dev/bin/python -m mypy` | **Success: no issues found in 13 source files**。strict / Python 3.10 设置未改变。 |
| 原报告三用例 | 缓存 typed error，两种 note 均成功并可 digest。见 [review-original-repro.txt](ipmr01-verification/review-original-repro.txt)。 |
| `PYTHONPATH=. python -B docs/tasks/W005/ipmr01-verification/review-unicode-probe.py` | 重跑首轮 256 / 4096 / 64 项探针；另 **128** 个越界八位转义 key/value、**4** 个公共缓存用例全部满足 typed error、定位和证据断言。保留 literal backslash 与 U+10FFFF。可复现 [脚本](ipmr01-verification/review-unicode-probe.py)及[输出](ipmr01-verification/review-unicode-probe.txt)。 |
| 源码外 `/workspace/work/w005-ipmr01/wheel-env-final/bin/python -I -B <review-worktree>/docs/tasks/W005/ipmr01-verification/wheel_smoke.py <review-worktree>/tests/fixtures/w003_m1` | 正常 40 图形 / 8 net regions、三种非法 escape × key/value、两种成功 note 的 payload digest 和重复 key 均通过；实际导入新环境 site-packages。见 [review-wheel-smoke.txt](ipmr01-verification/review-wheel-smoke.txt)。采用执行者已建干净环境，reviewer 未再次创建环境或重复构建。 |

### 采用的执行证据与独立身份核验

读取并核对 [receipt.json](ipmr01-verification/receipt.json) 对应命令/输出：最终开发版完整 `tests/unit tests/contracts` **284 passed in 34.05s**、Python 3.10 受影响范围 **120 passed in 13.22s**、strict mypy 13 source files、隔离 PEP517 sdist→wheel、全新 3.12 安装与 `pip check`。这是采用执行者的完整验证记录；reviewer 自己运行的范围如上，不将定向复跑写为全量复跑。

独立逐项重算 receipt 的 **23** 项证据 hash，以及 source manifest 的 **77** 个文件与 `git show 0a6de39:<path>`。实际新 wheel 和安装目录内 **67** 项产品文件均与该提交相同，包含 `py.typed`；[身份核验输出](ipmr01-verification/review-artifact-identity.txt)保存结果。Wheel SHA-256 为 `b7309629177d587aeb0cc0eb2c4e17a2f95c9d9e7496ce426154db0c2f106bfe`，sdist SHA-256 为 `69a0c1c94299e462ac0630e9553b59e936a86e5394b8fdc1292b0a46a67c4de7`。第一版 `*-r1` 与旧 W005 日志仅保留历史身份，没有用于证明最终改动。

对基线至最终产品及证据提交的 diff 检查确认：产品只改 `importers/config.py`；新生产回归仅两个测试文件。已验收 fixtures、答案、support、架构、旧三个 review 报告和旧 verification、PM 状态/当前入口未改写。新增执行/review 记录不构成任务状态变更。

## 未验证范围与交回 PM

本轮没有重跑 Python 3.10 全组件测试或在 3.10 做干净 wheel 安装；未验证其他解释器/平台、legacy 回归、fixture 重新生成、Calibre/Virtuoso/PDK 或生产环境。运行的有限探针不代表所有 YAML/PyYAML 版本的完整证明。

正式 pipeline 的 attempt/RunRecord/terminal、Stage 2 状态与跨格式/空间/body 物理判断、Stage 6 导出及完整 M1 仍不在本轮范围。IPMR-01 与 IPMR01-FR1 的关闭只表示本次字符串解析与错误/evidence 边界补修满足 PM2；交 PM 决定后续集成与验收，不自行合并 main 或删除分支。
