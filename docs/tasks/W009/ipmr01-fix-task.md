# W009 IPMR-01 局部补修交接（PM）

日期：2026-11-03。本项属于 W009 原行为6/A6 的缺陷修复，不建立新产品任务，不改变原验收答案或输入解释。

## 恢复位置与事实

- 分支：`codex/w009-effective-geometry-terminals`。接手包含本文件及 PM2 的最新 PM 提交，完整 SHA 见 Git/PM 回复。
- 独立合并前 review 交付：`386a139c38e815086fafc183ea73ea650e72cc5b`；受审产品仍为 `5b1d9b5196a7c5181822c4dd0f1bd2f678475116`，main 保持 `4df07e68b05df4c57a8b8d44bc41e7e073938d3a`。
- [原报告](independent-premerge-review.md)的 IPMR-01 为 P2 必须修正，阻止集成。原独立完整914项/44模块通过仍是旧版本事实，不能关闭本项。
- PM 在上述 review 提交实际重跑最小复现，确认内部 `TypeError` 被改成 `ValueError('invalid geometry wire fields')`，原对象仅保留在 cause。见[PM复现回执](ipmr01-pm-confirmation/reproduce-receipt.json)和[实际输出](ipmr01-pm-confirmation/reproduce.stdout.json)。此脚本 exit0 代表成功复现缺陷，合同结论是 failed。

## 修复目标与范围

使 W009 公开 decode 的完整可达调用链在合法 wire 的内部重建出错时，保留原异常对象及其既有 cause/context；预期的畸形 wire 由明确的结构、字段和类型校验拒绝。

已确认路径：`effective_codec` 的 `geometry_record` 分支调用 `geometry_codec._unpack`；后者的 constructor broad catch 仍改写 `LayoutDraft._materialize`、`BasePartition._layers`、`BaseOccupancy._fragments` 的意外异常。原 CR-01 修复只覆盖 W009 自有重建，不能代表完整嵌套链已经满足要求。

允许修改直接相关的 `normalization/geometry_codec.py`、必要的 W009 组合边界，以及为明确畸形值拒绝所需的最小 domain/state 校验和对应测试。执行者先梳理调用链与预计改动，选择最窄且完整的修法；如调整共享 W008 decoder，必须验证其原公开行为。不要仅特殊放行 TypeError、只保留 cause、按异常类型猜测输入/算法错误，或在外层捕获后重抛 cause。不能仅删 catch 而让畸形值变成裸 AttributeError/TypeError。

检查同一 W009 可达链上的同类边界；有具体可达反例时一并处理并由 reviewer 记录。无需机械删除所有历史 codec 的 catch 或重写无关模块。不得改变 wire schema、捕获认证、几何数学、来源/身份和闭合不可变合同来绕过缺陷；确需改变关键外部合同则带具体实例交 PM。

## 修后验证与关闭条件

1. **完整异常矩阵：** 实际运行原 [exception_paths.py](independent-premerge-review/provenance-exceptions/exception_paths.py)，检查 JSON 的 `case_count=99`、`same_object_count=99`、`identity_failures=[]`，不能只看进程 exit0。它覆盖 draft/result、W009自身、layout/partition/occupancy 和捕获解析路径的九类异常/中断；追加有意义的既有 cause/context 保真见证，并将关键反例纳入正式回归。
2. **畸形输入对照：** 在受影响的 W008/W009 公有构造/decode 入口，覆盖缺字段、多字段、错误 scalar/集合/嵌套 DTO、错误来源/单位/引用及非 canonical wire；继续明确拒绝，原合法值/roundtrip/digest与认证保持。重点防止用异常传播修复换来畸形输入裸异常或伪造成功。
3. **兼容与工程：** Python3.12完整 v2、Python3.10受影响的 W008/W009 回归及 strict typing；新 wheel/sdist、两套干净安装和源码外真实 W005/W006→W008→W009 的正常/错误/codec smoke。保存实际解释器、最终源/测试/配置清单、命令、退出码、原输出及包/安装身份；3.10全套若未重跑须明确，其余旧结论按受影响范围说明采信理由。几何算法及性能未变化的历史证据可按版本引用，无须重复无关穷举。
4. **独立复核：** 由未承担修复实现者检查实际 diff，重跑99项异常矩阵、畸形输入对照及真实正常组合，核对新源码/包身份。原 findings 和失败脚本保留；新增修后见证，不能把旧最小脚本改成假通过。该最小脚本明确断言缺陷存在，修后直接运行应不再满足旧断言，并不表示修复失败。
5. **交 PM：** Reviewer 单独给出 IPMR-01 关闭或保留、追加 findings 处置、剩余必须修正项和验证限制。执行者不代写 reviewer 结论，reviewer 不代写 PM 验收。未关闭或有新增必须修正项时，继续在本轮处理并复核；关键使用预期变化另交 PM。

## 写入与发布

新增执行交接 `docs/tasks/W009/ipmr01-fix.md`，独立复核 `docs/tasks/W009/ipmr01-fix-review.md`，新证据目录 `docs/tasks/W009/ipmr01-verification/`；任务文件仅在执行/reviewer各自区追加。保留旧方案、CR-01/CR-02、独立premerge报告、原始失败材料和 PM1/PM2，不改写旧清单或历史验证输出。

将补修产品、正式回归、执行/review记录与可访问证据提交推送原 W009 分支，沿用 `LucianoHoult@users.noreply.github.com`，核对远端完整 SHA 后交回 PM。若工作区存在他人改动，先隔离并保留。不得自行修改 PM 阶段/验收或 current-work，不合并 main、不删分支、不启动 W010。

## 可直接派发的执行 prompt

```text
按 Layauto 项目规范，以执行角色修复 W009 IPMR-01，并安排未参与修复者独立复核。
从 codex/w009-effective-geometry-terminals 包含本文件和 PM2 的最新提交恢复；原 review 交付386a139c38e815086fafc183ea73ea650e72cc5b，main未变。
先核对分支/远端/工作区，读 AGENTS、协作/环境规则、W009原要求、独立premerge报告、PM2和 docs/tasks/W009/ipmr01-fix-task.md；该补修交接是本轮具体范围。
修复完整 W009 嵌套 base 解码链的异常改写，同时保留畸形 wire 的明确拒绝、原输入认证和几何/不可变合同；在直接相关共享 decoder/DTO 内做最窄且完整的修改，不只修一个故障注入点。
完成99项异常同对象矩阵、既有cause/context和畸形输入对照、3.12完整/3.10受影响回归、typing、新包及两套源码外干净安装smoke。按交接保存最终身份与原输出，保留历史材料。
独立 reviewer 复核 IPMR-01及追加问题后，提交推送原W009分支并核对完整远端SHA，交回PM；不自行验收、合main、改current-work或启动W010。
```
