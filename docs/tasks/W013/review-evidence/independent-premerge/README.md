# 本次独立合并前复核证据

主报告：[independent-premerge-review.md](../../independent-premerge-review.md)。
受审 head `f31df3f3e6cd5df7ecef2e1f91977c3b68a9fac4`，base
`d6182fe6893c26490f9d58c6b808a5ce9910384b`；产品 source_id
`2c5724a9d3ecf99913857ad89015c03c03475ae762c1c8ab00b5146fd3eec278`。
本目录仅含新独立有界探针及输出，没有完整 wire/安装树副本。原历史证据继续引用 W013
原路径和不可变版本，未复制或改写。

| 文件 | 实际范围 |
| --- | --- |
| `coverage/probe.py`、`probe.stdout.json` | 768 次集合运算及带孔/重复 target 的40格逐格核对；最小 seed handles 只用于隔离算法，不冒充 captured receipt |
| `coverage/oracle_audit.py`、`oracle_audit.stdout.json` | 不 import 产品；独立读取当前答案、spec 和 raw 计算正常及 cut 专例几何 |
| `neutral/probe.py`、`stdout.json` | 原生 storage/owner/字段攻击、正常 neutral roundtrip/DAG、异常链及18种精确 AST guard 组合 |
| `binding/probe.py`、`stdout.json` | 真实 raw→W007，以及 W007/W008 两层 header admission；007 原拒绝 |
| `binding/mutate_receipt.py`、`header_attack.py`、`header-attack.*` | 一次真实 W010 构建后，实际 W013 builder 对同步篡改 run/database/top 的 receipt 拒绝；bytes/hash 不变 |
| `public_probe.py`、`public.stdout.jsonl`、`public.command.json` | 完整 direct public build/encode/decode，原 W010 bytes、1/1/2 decoder 调用、派生字段篡改、16项原异常链及原 map storage 检查 |
| `evidence/audit.py`、`stdout.json` | 59 项只读实际字节/日志/包/来源身份核对，不 import 产品或重跑工程矩阵 |
| `current-environment.json` | 主 reviewer 新探针的当前解释器/关键依赖信息；不替代原 R2 双环境证据 |
| `commands.json` | 专项实际 argv/cwd/显式 env/exit，以及主 reviewer 原命令回执路径；不是新执行 |
| `final_check.py`、`final-check.stdout.json` | 只读核归档完整性、允许写入范围、旧任务/PM段保真、273源身份、链接和脚本语法 |
| `manifest.json` | 归档文件 hash 与原 work 路径映射；不包含其自身 hash，整体身份由 Git commit 固定 |

成功检查的 stderr 均保留。`*.attempt01*`、binding 的 attempt02 是本轮探针作者的
失败/诊断，不是产品失败：coverage 首稿 conflict 手算未扣孔、oracle Fraction 调用错误、
binding 首稿假定 W007 就完成全 header 认证。首稿与原输出先保存，随后只改新探针。
`run_public.attempt01.py` 是最初 repo 父目录定位错误的 runner；第一次错误见工具 transcript，
归档 `runner.attempt01.stderr.txt` 是修正前对同一原脚本的再次复现，仍未启动产品子进程。
文档封包时的两次预核拒绝分别是 manifest 尚未生成、初版生成器漏掉嵌套的
`neutral/manifest.json`；原因记录在 `final-check.*failure.json`。修正封包顺序/完整路径枚举后，
最终同一只读检查通过，没有产品执行或产品身份变化。
两个已执行 binding probe 源码快照保留原空白行尾；本目录 `.gitattributes` 仅对这两个
确切路径关闭 blank-at-eol 检查，避免修改原脚本字节或其 hash；不放宽产品或其它证据检查。

所有成功探针实际运行于原 `/workspace/Layauto/work/w013-premerge/`，完成后按原字节移到本目录。
`neutral/manifest.json` 的旧 work 路径也按原记录保留，新的外层 manifest 提供移动映射。
`commands.json` 只记录实际已执行命令，不能因本次归档重写其路径或声称补跑。

复现时在独立 checkout 使用新的输出路径，勿覆盖原证据。以下纯检查可直接从 repo root
运行（将 stdout/stderr 写到新的 `work/` 文件）：

```sh
PYTHONPATH=. python -B docs/tasks/W013/review-evidence/independent-premerge/coverage/probe.py
python -B docs/tasks/W013/review-evidence/independent-premerge/coverage/oracle_audit.py
PYTHONPATH=. python -B docs/tasks/W013/review-evidence/independent-premerge/neutral/probe.py
PYTHONPATH=. python -B docs/tasks/W013/review-evidence/independent-premerge/binding/probe.py
python -B docs/tasks/W013/review-evidence/independent-premerge/evidence/audit.py .
```

`public_probe.py`/`run_public.py` 的 repo 定位与原 work 目录层级绑定；重现这条已记录命令时，
先只将这两个脚本恢复到新的 `work/w013-premerge/`，再从 root 执行
`python -B work/w013-premerge/run_public.py`。runner 对输出使用 exclusive-create，保留已有
输出。`header_attack.py` 从 cwd 定位 repo，需将 `binding/mutate_receipt.py` 保持在脚本同目录
的 `binding/` 下，可从 root 直接运行归档脚本。
两条 captured 路径应串行；它们是有界正确性复现，不能用当前耗时宣称跨环境性能变化。

没有复跑双全量、typing、构建/安装或 readback/mismatch 完整资源矩阵。
原环境二进制/安装树、固定外部 mismatch 目录不在新环境中，原执行按身份采信；来源 hash
核到保留 origin 字节。新 probe 的结果不扩大 synthetic exact/local 草稿的产品范围。
