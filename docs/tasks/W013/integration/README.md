# W013 实际 main 合并版本的组合验证

被测 merge：`088ed3c718eb5a0703511ff6b214274f30052ff1`，对应 [PR #68](https://github.com/LucianoHoult/Layauto/pull/68)。
已审 head：`da90a793cc1d1e45ae7f2de26d9e98766191428d`；两个 Git tree 完全相同。
结论与验收状态归[任务 PM2](../../W013-net-annotation-coverage.md#pm2-integration)，本目录保留本次实际命令和原输出。

## 实跑范围

- `probe.py`：从本次 checkout 导入产品，核对 273 项冻结源码/测试/config；复用已冻结 `verification-r2/installed_smoke.py` 的公开 API 断言，串行执行 direct、readback、extraction-mismatch。核 local graph、网络身份、精确覆盖、未知 body、完整 encode/decode roundtrip，以及 readback attempt/checkpoint 不变、terminal 缺席。正常 direct 另核公开 digest 和负面积伪造拒绝。
- `probe.command.json`、`probe.stdout.jsonl`、`probe.stderr.txt`：实际命令、运行位置、退出码、耗时、脚本/输出 hash，以及三路结果。没有保存大 wire 副本；当前 URI/运行身份不同，wire hash 不与历史 benchmark 作等值或性能比较。
- `boundaries.command.json`、对应 stdout/stderr：现行 ordinal/007 拒绝、两种非 exact quality 拒绝、新模块依赖/no-IO 边界及旧 W007 精确架构 guard。
- `environment-and-review.json`：本次 Python/依赖、review manifest 的 49 文件核对；没有 GitHub CI 状态，不记为 CI 通过。

这是源码树集成检查，**不是重新构建、干净安装、双全量或性能矩阵**。使用现有 Python 3.12 环境，未安装依赖；原 R2 双 1731、双 typing、两包/双安装三路 smoke 按冻结身份采信，原独立反例与资源证据保持其各自版本。当前环境中没有 mypy/build/setuptools 元数据，不影响本轮实际命令，也不宣称本机重跑这些工程检查。

新脚本仅复用原 smoke 的计算检查函数，没有执行其隔离安装 main，也没有重复执行原安装 smoke 的动态禁止 IO instrumentation；本轮依赖边界测试与原同源证据分别说明。

## 复现

在 merge 的独立 checkout 中放置本目录脚本，从仓库根目录运行 `python -B docs/tasks/W013/integration/probe.py`，将输出写到新目录。脚本要求 HEAD 为上述实际 merge，且导入来源为该 checkout；不要覆盖历史原输出。边界检查的准确 argv 见命令回执。

仍未验证完整 M1、生产 body/U06、真实 EDA/PDK、完整工艺坐标/mandatory、baseline 发布或 Stage 6。实际集成通过也不把 source-evidence 草稿升级为生产证明。
