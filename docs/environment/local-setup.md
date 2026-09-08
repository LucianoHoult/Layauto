# 本地开发环境

文档整理：2026-09-08。机器配置和测试结果沿用 2026-09-02 的历史记录，
本轮未重新安装依赖或重跑测试。使用前按下列命令检查当前环境。
开发范围以[架构](../architecture.md)为准，当前任务见[当前工作入口](../current-work.md)。

## 在这台 Mac 上开始

| 项目 | 2026-09-02 配置记录 |
| --- | --- |
| 工作目录 | `$HOME/Library/Mobile Documents/com~apple~CloudDocs/Work/个人项目/Layauto` |
| 仓库 | `https://github.com/LucianoHoult/Layauto.git` |
| Python | Anaconda Python 3.11.5；系统 Python 3.9.6 不满足项目要求 |
| 独立虚拟环境 | `$HOME/.virtualenvs/layauto`，位于 iCloud 之外 |
| 安装范围 | editable 安装 `.[all]`，包含测试、GDS、KLayout 和可视化依赖 |

优先使用已有环境，不用系统 `/usr/bin/python3`：

```bash
cd "$HOME/Library/Mobile Documents/com~apple~CloudDocs/Work/个人项目/Layauto"
source "$HOME/.virtualenvs/layauto/bin/activate"
python --version
python -m pip check
python -c 'import layauto_v2; print(layauto_v2.__file__)'
```

编辑器和自动化命令可直接使用 `$HOME/.virtualenvs/layauto/bin/python`。
该环境依赖创建它的 Anaconda Python；移动或删除后需重建。

## 安装或重建

所有主机统一使用 Python 3.10+，依赖以[pyproject.toml](../../pyproject.toml)为准。
先确认当前 checkout 已包含包配置修复：`[tool.setuptools.packages.find]` 应限定
`include = ["layauto_v2*"]`，并声明 `all` extra；不要沿用旧分支的临时安装绕行。
本地修复可以处于未提交状态；通过 Git 交接给其他主机时，其所用提交也须包含修复。
需要重建这台 Mac 的环境时，在仓库根目录执行：

```bash
"$HOME/anaconda3/bin/python3.11" -m venv "$HOME/.virtualenvs/layauto"
source "$HOME/.virtualenvs/layauto/bin/activate"
python -m pip install -e '.[all]'
```

其他主机用自己的 Python 3.10+ 创建独立环境，再执行同一 editable 安装命令。
虚拟环境始终留在 iCloud 工作目录之外；安装后运行上面的版本、依赖和导入检查。

## 测试入口与历史基线

根目录 pytest 排除 `legacy_mvp/`；v2 测试按当前任务的验收范围运行。
需要检查归档回归时，从仓库根目录进入归档，启用上述环境后执行：

```bash
cd legacy_mvp
PYTHONDONTWRITEBYTECODE=1 MPLBACKEND=Agg \
  MPLCONFIGDIR="${TMPDIR:-/tmp}/layauto-mplconfig" PYTHONPATH=.:.. \
  python -m pytest -p no:cacheprovider tests -q
```

`MPLCONFIGDIR` 必须可写。归档含跟踪的输出和旧字节码，故测试禁写字节码。
默认 `legacy_mvp/pipeline/run_mvp.py` 会覆盖历史输出；演示应配置独立输出路径。

**历史结果，2026-09-02：**editable 安装、`pip check`、v2 导入通过；当时 v2
只有骨架、尚无 v2 测试。归档测试为 **366 通过、1 失败**，失败项
`test_pipeline_pick_macro_refactor_preserves_byte_golden` 对应缺失的
`legacy_mvp/output/annotation_coverage.txt`。这不是本轮测试结果，也不代表当前基线。

## Git、网络与交接

开始同步前检查工作区和当前分支：

```bash
git status --short --branch
git fetch origin
```

确认工作区和目标分支后再更新；保留未提交修改，避免覆盖其他 session 的工作。
提交、推送和 PR 按[协作规则](../collaboration/rules.md)与当前用户授权处理。

**代理历史记录，2026-09-02：**shell 曾指向未运行的 `127.0.0.1:7890`，
仓库 Git 曾配置 `http://127.0.0.1:7897`。本轮未核实这些端口；不要直接复用。
网络失败时检查当前 shell 代理及 `git config --get http.proxy`，只使用已确认的地址。

GitHub 插件连接状态不能证明本地 CLI 凭据有效。历史 `gh` 路径为
`$HOME/.local/bin/gh`；确认路径后用 `gh auth status` 检查登录，必要时走官方网页登录。
可用 `git push --dry-run origin <branch>` 检查目标分支推送权限，不把令牌写入仓库。

跨机器通过 GitHub 交接代码，不同时修改 iCloud 中同一份 Git 工作目录。
Remote 与 cloud 的运行位置和交接边界见[跨设备开发](remote-development.md)。

## 工程工具边界

本轮文档整理未配置或验证 VM、Virtuoso、Calibre、PDK 或商业工具许可证。
pip 安装不提供这些工具。环境说明只记录运行条件；工艺事实、模型语义和验证
能力须由实际 tech/model/query evidence 确认，不能由安装成功推断。
