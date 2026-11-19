# W016 PM-01 补修交付

起点为 `codex/w016-single-cell-analysis` 的 `c9081f1a11612450e7228840e541452a6d7f9c89`。按 [PM2 补修要求](../pm-delivery-review/decision.md)重跑原公开脚本，随后修复几何提前退出时丢失的来源诊断。下表取自同一脚本的[修前输出](before.json)和[修后输出](after.json)。

| 真实临时输入 | 修前 | 修后 | 修后可核事实 |
| --- | --- | --- | --- |
| 正常，无 body | completed | completed | FIN 5/7，六个 D/G/S 一致，两个 B 待证明，parent unknown |
| 仅 CDL/query 端口不一致 | rejected | rejected | `SourceTopIdentityMismatch` 在请求摘要出现一次，指向 `query/raw/iXref.temp` 第 8 行 |
| 仅不支持的几何比较器 | unsupported | unsupported | `UnsupportedGeometryComparator` 指向 `tech/formats.json` |
| 两项同时出现 | unsupported，仅报告比较器 | rejected | 保留上述两项诊断，各自的完整 SourceRef 与单项对照相等 |

原脚本用仓库根目录运行的 `python -B docs/tasks/W016/pm-delivery-review/public_checks.py`。修前退出 1 的[原断言](before.stderr.txt)与 PM2 目录的历史失败均已保留。测试使用 synthetic 文件，修改后按实读字节重绑输入。

## 修复与定向复核

`analyze_local` 先检查来源身份，再求 drawn、effective 和 local_graph。任一几何阶段提前返回时，现在将已知的来源问题随 channel_fin、annotation 两个消费者返回。这两个 facet 保留 `not_evaluated`、空值和原依赖，已解析的 source 与先前成功的几何事实仍可读取。公开入口按完整 finding 去重，保留首次出现的顺序和每个 facet 的原诊断。原状态优先级决定组合结果为 `rejected`。

正式回归新增五个实际文件用例，覆盖两个单项控制、PM 组合和另两个共享返回点。每项断言包含来源文件的实算 SHA-256、状态及下游依赖。首轮测试构造的 required operator 在准入阶段即被拒绝；随后改用穿过同一 active 的第二根 POLY，在 effective 阶段真实触发 `AmbiguousGateStripe`。[首次定向输出](targeted-attempt1.txt) · [修正后 8 项通过](targeted.txt)

独立 reviewer 用公开 API 实跑十组输入，对比完整 finding、原文件身份和未执行的依赖。另以两个 unsupported 问题组合验证该情形仍返回 `unsupported`，并检查旧调用的结果和报告保持原值。[独立复核及边界](review.md)

## 冻结与证据复用

冻结清单含 298 项 runtime、正式测试及项目配置，SHA-256 为 `ecbc677c16f839ff294ce2a79296479f630c58d5dc5ef65713096daed8fdbb02`。工程命令在执行前后逐项验 hash。旧冻结至本轮仅变化两个新分析模块和一个正式测试文件。四路旧接口的生产者、wrapper、codec、配置与 fixture 均具有原身份，沿用正常直达、readback、FIN mismatch、错误 body 的完整 DTO 与公开 wire 的原逐字节比较。相关依赖、固定输入或编码变更时应重跑受影响路径。[冻结清单](frozen.json) · [身份与采信范围](reuse.json) · [四路原比较](../evidence/resumed-review/parity-summary.json)

## A8 最终工程验证

两个解释器在同一冻结上串行运行 `python -m pytest tests -q -p no:cacheprovider --maxfail=1`。两侧都覆盖 352 项 unit、1606 项 contracts 和 3 项 fixture_support，节点及收集顺序相同。8 个子测试另计。[收集核对](collection.json) · [3.10 原输出](pytest-310.stdout.txt) · [3.12 原输出](pytest-312.stdout.txt)

| 解释器 | 全量 pytest | pytest 耗时 | mypy | 构建与安装 | 源码外公开 smoke |
| --- | --- | ---: | --- | --- | --- |
| 3.10.22 | 1961 passed，8 subtests passed | 15694.18 秒 | 75 源通过 | wheel 和 sdist 成功，wheel 安装成功 | 6 组通过 |
| 3.12.14 | 1961 passed，8 subtests passed | 10116.73 秒 | 75 源通过 | wheel 和 sdist 成功，wheel 安装成功 | 6 组通过 |

双侧各自在干净环境安装本次 wheel，从 `/tmp` 用 `python -I` 读取真实临时文件。六组分别覆盖无 body、有效 body、FIN mismatch、错误 body、manual 和 PM-01 组合。安装后的 121 个运行时文件均与冻结源码匹配。工程命令、时间及原输出哈希见[验证索引](validation.json)，另有[构建与安装身份](build-install-identity.json)、[输入身份](smoke-inputs.json)及双版本环境清单（[3.10](env-310.json)、[3.12](env-312.json)）。

## 修后资源实测与适用范围

Python 3.12.14 在独立进程中串行实跑四组，先记录无 profiler 的整体公开调用墙钟和进程 HWM，再另启进程计数。capture 为已去重 SourceFile 的原始 bytes 总和，report 为完整未压缩 UTF-8 JSON。前三组沿用上一轮探针，其阶段耗时有包含关系。组合输入在 drawn 提前返回，其报告只包含已经取得的事实、诊断和未执行范围。

| 输入 | API 墙钟（秒） | 进程峰值（KiB） | capture 数 | capture（bytes） | report（bytes） | report/capture |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| 无 body 正常 | 4.084 | 31112 | 23 | 42395 | 235792 | 5.56 |
| 有 body 正常 | 4.255 | 30892 | 24 | 45202 | 259620 | 5.74 |
| FIN mismatch | 3.688 | 31204 | 23 | 42395 | 235838 | 5.56 |
| PM-01 组合 | 0.874 | 26740 | 23 | 41640 | 21528 | 0.52 |

四组调用均执行完整认证，GDS/CDL/query 各解析两次（获取、认证各一次），receipt 构造一次。前三组的全部探针构造计数和前一版本对应样本逐项一致。组合组的 source operands 和来源准入各调用一次，几何规则拒绝后未进入下游中立构建。公开返回的 capture 按 URI 唯一；修复只复用原 issue，未引入按 facet 复制捕获或重跑认证的路径。[三组原始探针](../evidence/resumed/resource_probe.py) · [组合计时](resource-combined.stdout.txt) · [组合计数](count-combined.stdout.txt)

前三组的相对输入文件及内容与上轮逐项相同。receipt 引用还绑定绝对目录和别名，跨目录报告摘要不同。本轮从起始提交取出原产品，用与修后版本相同的绝对输入路径重跑这三组，完整报告逐字节相等，每个摘要均与本轮计时记录吻合。[同路径比较脚本](compare_reports.py) · [原比较输出](same-root-reports.stdout.txt)

四个 synthetic 样本均低于 120 秒及 1 GiB 的既定复核门。正常三组的报告倍率沿用 [PM1 体积决定](../pm-resource-decision.md)。本次范围限于本机、上述输入及正式工程矩阵；生产 PDK、真实 EDA、隔离目标主机和大规模输入的性能仍待对应环境验证。验收与合并由 PM 决定。
