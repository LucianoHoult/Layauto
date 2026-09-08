# 跨设备开发 Layauto

官方文档核实日期：2026-09-08。本轮只整理说明，未配置或验证本机 Remote 配对、
SSH 主机或 Codex cloud 环境。应用入口和账号可用性以实际界面及官方文档为准。

先决定任务在哪里运行，再选择入口：

| 使用场景 | 入口 | 代码与命令运行位置 |
| --- | --- | --- |
| iPhone 上继续这台 Mac 的任务 | ChatGPT 移动 app 的 Remote | 已配对且在线的 Mac |
| 另一台支持远控的桌面设备 | ChatGPT 桌面 app 的远程连接 | 已连接主机 |
| Windows 只有 Chrome，要独立开发 | Codex cloud 网页 | 独立云环境 |
| 项目已有 Linux/其他远端开发主机 | 桌面 app 的 SSH 项目连接 | 远端主机 |

## Remote：继续已有主机上的工作

Remote 使用连接主机的文件、工具、凭据和权限。手机发指令、查看结果及处理审批，
不把这台 Mac 的开发环境复制到手机。

按官方流程在主机 app 中启用连接，使用相同账号和 workspace 完成设备配对。
运行期间保持主机在线、唤醒且 app 正在运行；具体按钮及账号要求见
[OpenAI：Remote connections](https://learn.chatgpt.com/docs/remote-connections)。

SSH 项目的文件和命令位于远端；该主机需要自己的依赖环境。
截至核实日期，Handoff 可在本地与匹配项目的已连接主机间移动任务和 Git 状态，
但官方未支持 Handoff 到 Codex cloud。浏览器 cloud 入口不能当作 Mac 原任务的
远程入口；详见同一份[远程连接文档](https://learn.chatgpt.com/docs/remote-connections)。

## Cloud：从仓库版本开始独立工作

在 [Codex cloud](https://chatgpt.com/codex) 连接 GitHub 仓库、创建环境，
指定任务使用的分支与提交，并配置依赖。任务运行在隔离云环境，可在网页审阅结果
并通过 PR 交接。入口及配置步骤见
[OpenAI：Codex cloud](https://learn.chatgpt.com/docs/cloud)。

Layauto 在云主机同样要求 Python 3.10+，并选用已经包含包配置修复的提交；
修复条件和完整安装说明见[本地开发环境](local-setup.md)。在所选环境的仓库根目录执行：

```sh
python -m pip install -e '.[all]'
python -m pip check
python -c 'import layauto_v2; print(layauto_v2.__file__)'
```

不要假定云任务持有 Mac 的未提交文件、Python 环境、商业工具或完整对话。
所需代码和上下文应随可访问的仓库版本交接；额外工具与权限在运行主机分别配置。

## Git 与 session 交接

1. 切换前检查工作区、分支和提交；把目标、结果证据、未决问题及下一步写入任务记录，
   由 PM 更新[当前工作入口](../current-work.md)的链接和全局下一步；初始化时按协作规则暂存交接。
2. 经授权提交和推送后，把目标分支、提交 SHA 与任务文档路径交给下一 session；
   明确其运行主机和可修改范围。未提交的草案不能视为云端可见。
3. 接手者先读[协作规则](../collaboration/rules.md)、当前工作入口和任务所需的
   [架构](../architecture.md)段落；在新主机独立检查依赖和测试入口。
4. 完成后交回 diff、验证证据和未覆盖项；回到 Mac 时先检查工作区，再接收所需提交。

iCloud 同步文件，Git 交接已提交代码和文档；它们不承担 session 对话管理。
不要让多台机器同时改动 iCloud 中同一份 Git 工作目录。

## 工程工具边界

本轮未配置或验证 VM、Virtuoso、Calibre、PDK 或商业工具许可证。
这些条件应在实际运行主机分别核实；环境可用不等于工艺、模型或 query 语义已验证。
相应事实和能力边界以[架构](../architecture.md)及实际工程证据为准。
