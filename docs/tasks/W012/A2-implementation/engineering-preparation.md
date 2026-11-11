# A2 工程验证准备

独立准备协作者 `/root/engineering_prep`，2026-11-11（Asia/Shanghai）。本材料仅记录工具、环境和轻量自检；**未执行 A2 双全量、typing、构建、安装或完整 smoke**。须待 root 完整三路筛选确认有依据继续、产品/正式测试/配置冻结后，才运行最终矩阵。准备不改变 PM 阶段，不是产品收益或验收。

工作树 `/workspace/work/w012-a2/engineering` 是 PM 准备 `0213c346ac03b7b7282aae522c299155958ac8f6` 的 detached worktree；只新增本 A2-implementation 附件，未改 runtime、原测试、原证据或入口。已读项目 AGENTS、README、协作/环境规则、current-work、AI1–AI6、A1 最终 runner 与完整安装 smoke、相关资源记录，以及 cloud runtime/package/network 技能。环境 running、observations_current=true、network enforced，VPN=false；未用 sudo，未改测量专用 `/workspace/.venvs/layauto`。

准备了两个独立开发解释器，所有下载、venv 和缓存均位于 `/workspace/work/w012-a2/envs/`：

- `dev310/bin/python`：CPython 3.10.22。
- `dev312/bin/python`：CPython 3.12.14。

两个环境依赖安装、`pip check` 与完整包清单均成功，原命令/stdout/stderr/hash见 [preparation-receipt](engineering-preparation/preparation-receipt.json)。安装仅为 pyproject 声明的 runtime/dev 工具依赖；没有预装 checkout 包，最终 runner 必须验证导入来自其冻结 source。准备脚本见 [prepare_engineering_environment.py](prepare_engineering_environment.py)，重复运行会拒绝覆盖已有命令输出。

[engineering_tools.py](engineering_tools.py) 从 A1 已用 runner 复制，只调整 A2 标签、默认基线为 A1 的1656个 node ID、只允许单 worker；其余冻结快照、source/tests/config 前后身份、双 strict typing、包成员100项源码身份、sdist3.10/wheel3.12全新安装与源码外 `-I -B` 完整组合 smoke 保持。来源hash及改动说明见 [origin](engineering-tools-origin.json)。[installed_smoke.py](installed_smoke.py) 仅改 A2 标题，完整 direct/readback/原五 overlay mismatch、正常5/7及实际4对5、全部crossings、来源/局部图/T05/body与unsealed/checkpoint/无terminal、公开重建及IO禁入检查保持。

轻量 [selfcheck](engineering-preparation/selfcheck-result.json) 已通过 AST 语法及既有证据目录拒绝覆盖检查；预期失败原 stderr 保留，不计产品失败。`--help` 输出亦保留。工程运行按本机16GiB限制和既有约9GiB长矩阵采样高点，**双解释器及安装 smoke 串行**，与性能测量互斥；不把调度算性能收益。

冻结并确认新测试总数后，在主实施树运行如下命令（`COUNT` 由真实 collection 确定，不能沿用旧数冒记）：

```sh
/workspace/work/w012-a2/envs/dev312/bin/python -B \
  docs/tasks/W012/A2-implementation/engineering_tools.py \
  --root /workspace/Layauto \
  --out /workspace/Layauto/docs/tasks/W012/A2-implementation/verification \
  --work /workspace/work/w012-a2/final-verification \
  --smoke /workspace/Layauto/docs/tasks/W012/A2-implementation/installed_smoke.py \
  --python310 /workspace/work/w012-a2/envs/dev310/bin/python \
  --python312 /workspace/work/w012-a2/envs/dev312/bin/python \
  --expected-tests COUNT --matrix-workers 1 \
  --baseline-collection /workspace/Layauto/docs/tasks/W012/A1/verification-r2/collection-312.stdout.txt \
  --baseline-test-count 1656
```

输出及work必须新建/空；失败保留后用新的 attempt 目录，不覆写。最终 receipt 生成前任何单项通过都不能记为完整矩阵通过。相关产品/正式测试/配置再变须按新冻结重做要求；纯文档补记不冒记新受测产品。
