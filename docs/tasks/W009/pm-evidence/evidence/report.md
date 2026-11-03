# W009 PM 接收：交付证据专项

核验对象：`codex/w009-effective-geometry-terminals@5b1d9b5196a7c5181822c4dd0f1bd2f678475116`。准备起点：`4975e565a33d9594782645b6ad0f944b78ee6ae8`。执行者：PM 专项子 agent `/root/w009_pm_evidence`，只读检查；没有修改产品、测试、fixture、仓库文档或 Git 状态。结论：**本专项未发现必须修正项**。这不是完整产品 review、PM 最终验收或 main 集成结论。

## 本次实核

读取根 AGENTS、README（继承已读上下文）、协作规则、环境说明、W009 任务、方案 review、代码 review 和执行交接，核对原要求、执行范围与证据版本。

- 最终 source-manifest 的 240 个源码、测试、配置和 README 文件，逐项与当前工作区 SHA-256 相符；全部 Git 跟踪的 runtime/unit/contracts Python 均在清单内。
- 完整 source-snapshot.tar.gz 的 240 个文件与该清单完全一致；包内 90 个 runtime 文件逐字节匹配源码。
- verification/evidence-manifest 的 117 项文件全部匹配；receipt 的 15 条命令均记录 exit 0，所有原始输出 hash 匹配。pytest 输出分别为 914 passed，strict mypy 分别为 44 source files；验证 runner 自身 hash 亦匹配。
- wheel 和 sdist 实物在当前 checkout 可访问，整体 hash 与内含各 90 个 runtime 文件均匹配最终源码。wheel 为 `27e97b27f8e3a4f5e2ff804a32fe3bd3aa33d3a6ea1f3e9b96075ea5858aaf95`，sdist 为 `2716df4fe382dfb64127ed9b46ee3c80aa53b071bab10175d7e4b65806c72c98`。
- 双安装身份记录的 runtime 清单、直接 artifact URL/hash、实际安装来源路径、源码外 cwd、`-I -B`、smoke 原始输出与成功检查相互一致。
- 7 份最终数学/container/metaclass/Fraction probe 的记录身份与当前 source manifest 相符；最终方案全文 hash 与 IR-01 关闭记录相符；性能记录引用最终三个产品文件 hash。
- CR-01/CR-02 原问题与中间版本记录保留；CR-02 双解释器最终 67 项回归输出存在。最终工程回执指向修后源码；pre-cr02/pre-container 历史中止结果不计作最终矩阵。
- `tests/fixtures`、W003–W008 历史任务/报告相对准备起点的 diff 为空。既有 W007 测试仅追加确切纯组件依赖白名单，typing 仅扩充新模块；没有放宽为全目录豁免。

## 实跑与采信边界

本次实际执行的是 `audit.py`，结果见 `audit-result.json`。它重算当前仓库、源码归档、包实物和已归档命令/输出/安装记录的字节与内部一致性，未重跑 pytest/mypy、构建、安装或 smoke。

原两套 clean install 目录不在当前机器。因此本次**没有重新遍历原实际安装树**；原独立 reviewer 的安装树审计结论按其版本和原记录采信。现存包实物可重新安装验证，但本专项没有将原安装结论改称本机实跑。历史命令实际执行由原回执/review 支持，hash 复核不能自行证明所有历史运行行为。

## 复验

```sh
cd /workspace/Layauto
PYTHONDONTWRITEBYTECODE=1 python -B /workspace/work/w009-pm/evidence/audit.py
```

脚本固定检查上述交付 HEAD；后续 PM 文档提交后复验应在该交付 checkout 执行，不能把 HEAD 守卫失配误判成产品内容不一致。
