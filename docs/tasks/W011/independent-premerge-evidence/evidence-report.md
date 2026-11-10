# W011 本次独立合并前工程与资源证据复核

Reviewer：`/root/evidence_review`，2026-11-10；未参与 W011 设计、实现或正式测试。范围是工程证据、版本身份、全交付文档范围及资源可用性；几何/DTO 的独立正确性由本次其它专项复核。本专项必须修正项 **0**。

本次实际运行[新审计脚本](evidence-audit.py)，exit 0，**297 项核对通过**，stdout 为[完整机器结果](evidence-audit.stdout.json)，[stderr](evidence-audit.stderr.txt)为空。命令为仓库根目录 `python -B docs/tasks/W011/independent-premerge-evidence/evidence-audit.py`，解释器及 UTC 在机器结果内。它只使用标准库读取 Git/实际 tar/实际 wheel/原输出，不运行产品、正式回归、重型 codec 或安装。没有把以往 reviewer/PM 的 passed 字段当作本次证据。

## 版本及完整源码

实核祖先链为 main `61775e8fde6e9ea247ec08a32067c44c3be48ff8` → 准备 `81e01da1e5a6ce8e7132f3cebf8ee92bc237246f` → 产品修正 `8917d38d916c914bfa785cb116982f3f299b38de` → 冻结 `e89bdaa6a091f56cfaf7862dced7232d34e22514` → 交付 `3c464baade7b6ea8c712cfb84265490b8e3f754e` → 最新 PM head `8452027e57fb1c58607640d7eb755b38ffc70716`。

262 项 manifest 的 path 集合恰为冻结提交全部 `layauto_v2/`、`tests/`、`pyproject.toml`、`README.md` 和 W003 records 示例选择；完整 tar 无重复或 link 成员，逐字节等于 manifest。全部 262 项分别与冻结、交付、最新 PM head 的 Git blobs 及本次 live 文件一致。100 项 runtime 也逐项等于产品修正 `8917d38`；main 到最新 head 没改 fixture。冻结后变动均在 docs，不能将 PM 文档提交冒记为另一份实际跑过双矩阵的源码。

实际 wheel/sdist 解包分别得到 100 个 runtime 文件，无重复成员、tar 无 link；每项字节等于冻结 runtime。wheel SHA-256 为 `7ba118f36d864b7097fc3c87de43fc398cd93ef215a24be87e764096162540d8`，sdist 为 `1e6219a2fc82525ea9efc94bd3d4dc770b5a2742f668490979e639d6ad2f1b2b`。

## 双矩阵、安装、历史失败与 gate

工程 83 项索引、资源 16 项索引与实际全部文件集合/哈希完全相同；旧失败 attempt 的 31 项索引，以及 preflight archive 索引也重新逐 hash 核对。21 条最终命令均有 argv、cwd、environment overrides、UTC、exit 0、stdout/stderr，独立单命令 JSON 与 aggregate 一致，也与外层 runner 原 21 行记录一致。

两份原 collection 各为 1605 个唯一 ID，彼此相同，完整包含原 baseline 的 1465 IDs；新增恰为 W011 的 140 IDs。原输出分别是 Python 3.10.22 的 `1605 passed in 12905.97s`、3.12.14 的 `1605 passed in 7310.82s`；双 mypy 原输出均为 strict `54 source files`。没有删 baseline、只读摘要或只比最终计数。构建在双矩阵之后，双安装 smoke 串行。

两份归档安装身份的 runtime 100 文件、pip 报告 artifact hash、源码外 cwd、`-I -B` import 身份、完整 smoke 原脚本与输出均核对。原 clean 3.10 从 sdist、clean 3.12 从 wheel 安装；两条正常 direct/readback 保留完整 crossing/原图/T05/body/attempt，mismatch 明确实际 4 对 source 5。正常 direct/readback 的完整 wire digest 跨解释器相同。原脚本还断言完整 Result encode/decode、对象相等、稳定 wire/digest，以及公开不完整 measurement 被拒绝；本次静态检查了这些断言在成功打印 JSON 前实际执行。

**本机两个原 site-packages 路径均不存在。** 安装内容、fresh venv 和源码外 smoke 依赖按相同 frozen source 身份核验的原归档证据采信；本次未重装、未重新观察原安装目录、未重跑双完整矩阵/完整 readback codec。

`02725e2` 首轮旧输出的 `2 failed, 1603 passed in 9500.70s` 与 exit 1、closure/中断事实原样保留；旧 3.12 没有 full 运行通过证据。后续仅 `tests/contracts/test_w011_geometry.py` 改动：修正 target 字段顺序，以及按既有 W005 schema 边界检查 foreign operator。两份已归档原 patch 与集成 `75c846f`/`6ea8b0a` 的 patches 逐字相同，runtime/schema/fixture 未变。原辅助提交 `27f8854`/`1cb7e1b` 的 Git objects 未在本机，因此本次通过完整归档 patch、原 commit 文本与集成 Git patch建立等价，没有声称直接读取缺失对象。

原 HG-01 的 finding 和修正仍在 gate review 中。静态重查最终插件先 local fd + WAIT/flock、成功后才发布 `_LOCK_FD`，异常关闭 local descriptor，session finish 仍持锁至进程退出；只控制等待/日志，不改 collection、fixture 或结果。正式双进程四事件、同 inode、non-inheritable fd、首个 W011 node 与相同插件 hash 已核；3.10 等锁 **2603.347384s**、3.12 **0.000139s**，包含在矩阵 elapsed 内，不能作为纯计算基准。parent RELEASED 是退出观察，不能当内核解锁精确时刻。

## 资源单独判断

三个 fresh-process probe 的 argv/时间、原 stdout/stderr、probe hash、runtime/config identity 以及原 93 份 capture 逐项 bytes/SHA 独立核对。每次均为 31 份、280,706 B acquisition、40 drawn records/18 FIN、36 FIN decisions；mismatch 的五处替换恰为既有 approved overlay，其 source CDL 仍是原 MN0 NFIN=5。三个命令串行并成功执行完整 Result roundtrip。

| 原 fresh 样本 | 完整 Result wire B | 整进程 `ru_maxrss` KiB | W011 build / encode / decode 秒 |
| --- | ---: | ---: | --- |
| direct | 54,050,313 | 2,847,416 | 37.209 / 1.522 / 46.759 |
| readback | 136,461,405 | 7,322,828 | 74.948 / 3.064 / 101.861 |
| mismatch | 54,049,506 | 2,854,456 | 35.419 / 1.397 / 45.179 |

原 observer 的 **1399 条 JSONL** 重新求每 PID 最大 RSS 与共享 cgroup 采样高点，全部值及进程身份与 summary 一致：矩阵 3.10 **9,257,804 KiB**（约 8.83 GiB）；3.12 6,248,624 KiB；双安装 smoke 为 9,119,696 / 6,927,912 KiB；共享 cgroup 最高采样 **12,299,743,232 B**。原 16 GiB cgroup、4 CPU quota 下 memory.events 均零且前后未变，既有 memory.peak 未变，不能归因本次。fresh readback 约 6.984 GiB 是整进程高水位，含 imports、上游捕获/重建、保留原对象及 wire；不是 W011 增量。constructor 已包含在 build/decode；10s 采样不是精确峰值，observer 也未覆盖最早约 28s。

当前执行环境另实读 cgroup：memory.max=17,179,869,184 B，cpu.max=`400000 100000`，memory.events 全零；专项审计时 memory.current=620,138,496 B。它们只用于安排本轮轻量核查，不替代原 benchmark 或承诺今后运行可用空间。

**集成判断：没有证据显示这份受限 40-record synthetic M1 组件的串行完整路径被资源阻塞；原完整矩阵、双安装和 fresh readback 已实际完成，也无已确认性能预算被证明违反。因此本专项不据此增设阻断 main 的验收门。** 但这个很小输入已有约 136.5 MB wire 与约 7 GiB fresh readback、长矩阵约 8.83 GiB 采样高点，成本显著，不能作为可忽略的日志事项。建议 PM 保持重型完整 Result/codec 串行，避免与完整矩阵及其它重型 codec 并发；稳定 W011 基线后优先准备已登记 W012，按同条件完整 direct/readback/mismatch 归因重复捕获/重建并证明优化，扩大链或输入前重新评估。没有最大输入、多器件、多片段、并发或生产资源上限证据；这些未测范围不能虚构通过，也不在本轮用任意新数值门槛替代现有 A8。

## main 到 head 的其它文档

逐项静态检查 README、docs/README、协作规则、current-work、roadmap 和 W012 登记 diff。README 新 API/scope 随产品冻结；typing 新纳入四个模块且保持 strict/Python3.10。W007 dependency guard 只具名允许新 closed codec 读 immutable LocalConnectivityDraft，未泛化允许 state import。PM 后续文档将 W011 标为分支技术接收、专门 review/main 集成待完成，保留 U06/完整规则/no_change/发布后置；协作规则区分开发定向与最终双完整，未放宽最终冻结要求。W012 明确待准备、未实施、未选方案或量化承诺，不将登记本身当性能修复或 W011 自动放行。归属和范围无新必须修正项；本专项未改这些 PM 文档或启动 W012。

## 本次审计 harness 的失败记录

首次[stderr](evidence-audit.initial.stderr.txt)为本脚本错以为两份 pip JSON 都含 `archive_info.hashes`；原 3.10 采用合法 `hash`，修正读取两种现存形状。第二次[stderr](evidence-audit.second.stderr.txt)为原辅助 Git object 本机不存在，转为上述归档 patch 等价核查。第三次[stderr](evidence-audit.third.stderr.txt)及[第四次](evidence-audit.fourth.stderr.txt)均为本脚本错误要求 peak summary timestamp 与 JSONL 行 timestamp 完全相等；原 observer 在峰值更新时先读 clock，写 enclosing JSONL 时再读 clock，两者差几十微秒。最终重新核全部非时间字段相等，并核 summary 时间确在对应原 sample 区间内。四次是本次审计代码假设错误，不是产品/归档数据 finding；最终 exit 0 不覆盖其原失败记录。

未验证范围：本次未重新运行工程矩阵/安装/资源测量、未连 EDA/生产服务器；本专项不代替本次几何、异常/DTO 和 root 综合 review，不宣布 PM 验收或 main 集成完成。
