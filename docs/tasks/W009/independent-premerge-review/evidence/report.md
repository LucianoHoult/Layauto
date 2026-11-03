# W009 合并前证据与性能说明专项

Reviewer：本次独立复核的 `/root/evidence`，未参与原方案、实现或原验收。日期：2026-11-03。审查对象为 `88a7ae9d0330b7c7fddda0b07366c7a96552b65e`，产品提交 `5b1d9b5196a7c5181822c4dd0f1bd2f678475116`，准备提交 `4975e565a33d9594782645b6ad0f944b78ee6ae8`，main 基线 `4df07e68b05df4c57a8b8d44bc41e7e073938d3a`。

**本专项未发现必须修正项。** A8 的最终证据可按下述身份和采信边界使用；完整回归与 typing 的本次实跑由主 reviewer 另记。

## 实际审计

已读根 AGENTS、README、协作及本地/远端环境规则、W009 要求、方案与独立方案 review、执行交接、代码 review、PM1 与机器回执，并阅读四个产品模块中与复杂度及完整保留值检查有关的实现。仓库无后代 AGENTS。

在 `/workspace/work/w009-review` 实际运行：

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/layauto/bin/python -B \
  docs/tasks/W009/independent-premerge-review/evidence/audit.py \
  > docs/tasks/W009/independent-premerge-review/evidence/result.json
```

Python 为 3.12.14，命令退出 0；[独立脚本](audit.py)及[原始 JSON 结果](result.json)可复验。脚本仅使用标准库读取源码、Git 对象、归档和记录，没有执行原验证脚本，也没有写产品、正式测试或旧证据。

| 核验对象 | 本次实际结果 |
| --- | --- |
| 提交链及比较范围 | main→准备→产品→待审 HEAD 祖先关系一致；准备→产品包含实际实现，产品→待审 HEAD 仅 PM 文档、导航和证据。未只审最后一个提交。 |
| 最终 source manifest | SHA-256 `32e60e783a7a7e4172ee3916e3ceb4fade329585b87a7c7091a85c8a6418d1b6`；240 项当前文件、产品提交对象及待审 HEAD 对象逐字节全部相等；覆盖全部已跟踪 runtime 与 unit/contracts Python、README、pyproject。 |
| 完整源码快照 | 240 个唯一文件名及全部字节与 manifest 相等；tar SHA-256 `5ed2228559ea6dcf7a1417e19b8f706f1e88283edfca0c01809489cb147ec727` 与最终回执相等。 |
| 最终验证证据 | 117 项 evidence manifest 的 hash 全匹配；15 条归档命令均记 exit 0，原输出及逐命令 JSON 的 command/cwd/exit/hash 相互一致，runner 字节匹配。双 pytest 输出各 914 passed，双 mypy 各 44 source files。 |
| wheel / sdist 实物 | wheel SHA-256 `27e97b27f8e3a4f5e2ff804a32fe3bd3aa33d3a6ea1f3e9b96075ea5858aaf95`；sdist `2716df4fe382dfb64127ed9b46ee3c80aa53b071bab10175d7e4b65806c72c98`。两包各 90 项 runtime，文件名无重复、字节等于最终源与包记录。 |
| 安装来源和源码外 smoke 记录 | 两套 pip install-report 均选择所记的本地 artifact URI 与对应 SHA；安装身份记录各 90 项等于最终源；smoke 命令有 `-I -B`，所记 cwd 在历史 checkout `/workspace/Layauto` 外，环境所记导入来自 site-packages、isolated=1、禁字节码，package manifest 及成功 checks 一致。 |
| 最终 review 修正证据 | 最终数学及 container/metaclass/Fraction 双解释器结果的源码 SHA 全匹配最终清单；双 CR-02 最终输出各 67 passed。最终 PM 异常/Fraction probe stdout 的源码 SHA 亦匹配最终清单。 |
| PM1 | 核对产品/准备/main SHA、最终清单 SHA、20 个 PM 附件 hash，以及 pytest、typing、exception、Fraction 四条命令记录的原输出 hash。归档输出为 914 passed / 44 source files。 |
| 保护路径 | 准备提交至待审 HEAD 未改 fixture、答案及 W003–W008 历史路径。 |

最终清单中的 `git_head=4975e565…` 是执行时尚未提交的工作区基线，清单同时记录全部 240 项内容；本次已用产品提交和待审 HEAD 的 Git 对象补足与最终提交的逐字节关联。它不表示最终代码仍等于准备提交内容。

## 历史身份

`pre-cr02` 清单 `9e3fde92…` 和 `pre-container` 清单 `9899cec7…` 各自 240 项 tar 内容均匹配其清单与状态记录；pre-container 独立 zip 的完整 240 项也匹配同一清单。前者 3.12 的 847 项和 3.10 的中断、后者两解释器中断矩阵及当时包/安装属于各自历史候选，不作为当前最终结果。早期 CR-01 的双解释器 `exception-after*.json` 确实绑定 pre-cr02 清单；PM1 的异常 probe 绑定最终清单，两者版本含义分别保留。

初始 IR-01 关闭后的方案全文 SHA `b14226b6…` 与当前方案相等。完整回归的最终 914 项、44 模块和两包只采用最终 `32e60e783…` 清单对应记录。

## 复杂度与性能说明

实现与最终披露一致：单目标 m 个命中 CUT 至多 O(m) 个 x slabs，每 slab 扫描并排序 y 区间，通用 O(m² log m)；输出片数 p 最坏 O(m²)。局部分组使用 O(p²) 邻接比较；每个 region 的 overlap/connectedness 为 O(q²)，canonical cover 的一般上界为 O(q² log q)。将这些后处理成本代入最坏片数，整条链可能远高于差集扫描本身。文档明确列出这些成本，没有仅用差集扫描时间代表公开 API 性能。

公开构造器重建、完整 W008 base/receipt 原对象图检查与 canonical 编码会重复遍历；共享对象无 memoization；decode 还包括捕获认证。执行交接和 performance.json 已明确披露这些额外成本及分项计时。

最终 10 条有限性能执行均绑定最终三文件 SHA。纯差集最大到 200 CUT，crosscuts 的 10,201 片属于纯差集见证；neutral draft stress 最大记录为 strips/overlap 100 CUT，crosscuts 20 CUT、121 个局部区域，以及 holes 25 CUT。正常 capture 的公开 API 单次记录约 1.45 秒。脚本明确区分 actual capture、neutral in-memory stream stress、pure difference，每项只有一次计时，未声称统计吞吐、生产规模或新增几何上限。现有 W005 1000 stream record 上限未被包装成本组件的新限制。

非阻塞建议：后续接入更大真实输入前，针对高片数、单 region 多孔洞、共享捕获反复验证分别建立规模曲线，并记录内存峰值；当前单次 toy 计时适合作为有限见证。该建议不改变 W009 验收或新增本轮性能门槛。

## 采信和未验证范围

原安装目录在本机均不存在。本专项没有重建包、创建或重装环境、遍历旧安装树、运行原 Python 3.10 矩阵或历史 smoke。现在观察到的是源码/包实物的内容及归档命令、安装来源和输出之间的一致性；这不能独立证明所有历史命令当时确实执行。原双解释器、构建与干净安装运行事实按原最终回执及原独立安装字节审计采信，本次未把采信写成重新安装或重新观察历史执行。

本专项未验证生产性能、真实 EDA/PDK、完整坐标、connectivity、FIN/body、canonical device/net join、baseline/seal/no_change 或 Stage6。它们继续按当前任务边界后置；U06 与 synthetic body_context 必填合同未改变。
