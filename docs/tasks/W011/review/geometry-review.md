# W011 独立几何专项 review

Reviewer：`/root/code_review/geometry_review`，2026-11-09，未参与设计或实现；父 reviewer `/root/code_review` 委派 exact geometry、seed 定位/coverage、FIN 独立性、全部 channel/source 集合及 topology/scope 专项。只写本报告、独立 probe 与原始输出，不修改产品、正式测试、fixture/答案、任务阶段或 PM 文件。

**本专项 review 完成：CR-05 的原 wrapper 异常与复核发现的来源指针残留均已独立验证修正，最终指针修正归属 `8917d38d916c914bfa785cb116982f3f299b38de`，专项剩余必须修正项 0。** frozen589 加 patch 实测后，最终提交仅在 message 增加显式 `str(record_id)`；已按最终 commit 的独立 archive 重跑轻量 probe 通过。不能把 frozen975 的 typed 结果通过误称完整关闭。原 findings、第一次关闭判定的修正及证据均保留如下。整体 A1–A8、完整工程矩阵及最终交付结论由父 reviewer 综合，不能从本专项结论推断 PM 验收或完整工程通过。

## 身份、范围与方法

初读候选 `f49323311bd817f066cb3e2411cad45219764f04`，实际第一轮 probe 使用 `f436f591ca77af364293e8201cebc12635d7c53c`，逐文件核对其日志清单与该 commit 全部产品 `.py` 完全相同。后者只在 `_binding` 增加 `selected_source_cell`；本专项核对该增量与 selected cell 语义一致。

第二轮（retry）的实际 HEAD 已为 `f199a05452cdc9fbfbe029d4282b324c46a7ac54`，且工作树有当时未提交的 `domain/source_location.py`、`normalization/codec.py`、`normalization/component.py` 三项修正；因此不能称它为 clean f436/f199。三项 bytes 均精确匹配之后提交 `975852d3b9ea946aca24f727071cf26a7dce8bc7` 中对应文件；已用 f199 加这三项 bytes 重建完整相关 [source snapshot](geometry-retry-source.tar.gz)，逐一核对全部产品 hash 与运行首行一致，见[身份清单/重建方式](geometry-retry-identity.json)。当前内存中导入的 annotation/domain geometry 仍为修前版本；运行中 checkout 更新后的 traceback 行显示不应取代该清单。最终 CR-05 复核改为独立 `git archive` 的 frozen975 目录。

已读根 AGENTS、协作与本地/远端环境规则、current-work、W011 任务/plan/plan-review、架构 FIN/identity/annotation/提取边界、W007–W010 的当前接口要求及实现，以及实际 `physical.json`/`derived.json` 和 raw seed/FIN 几何。运行环境为 `/workspace/work/w011-engineering/dev312/bin/python`，Python 3.12.14，managed cloud executor，network policy enforced；未安装依赖、修改环境或访问网络。

重点代码为 `annotation/channel_identity.py`、`derive/fin_count.py`、`derive/channel_identity.py`，并读取相邻中立 DTO、local/effective/geometry owners。正常与变体通过真实 `read_inputs → build_geometry → build_effective_geometry → build_local_connectivity → build_channel_identity` 组合；仅测试代码负责在临时复制输入中编辑 GDS 并重绑实际字节。没有修改固定 fixture 或把 oracle 喂给 runtime。

## 原 findings（保留）

### CR-05 — P1：实际 seed 的来源 wrapper 使定位诊断抛出 ValueError

受影响位置：`layauto_v2/annotation/channel_identity.py:49`，`seed_source()`。

在候选 `f436f591ca77af364293e8201cebc12635d7c53c`，实际 W007 MN0 seed 的 `record.field_sources.record_id` 为 `{'derivation': 'author ordinal label, not a raw identity', 'sources': ({'path': 'query/requests.json', 'sha256': '57f5f38cb3ec450fd1815ef88c618c03a9703690672348b313fa35fbce97bc62', 'json_pointer': '/requests/0/record_ids/0', 'lexeme': 'D0'},)}`。`seed_source()` 把整个 wrapper 送给 `ref_from_location()`，后者缺少 path/uri，实际抛出 `ValueError('source location requires nonempty text')`。

这条 helper 被零候选、多候选、同身份不同 channel、foreign seed 等预期输入诊断路径调用；正常唯一 seed 不调用，故正常 5/7 不能证明这些 typed issue 路径可用。预期定位问题本应保留 located issue，当前会意外退出。修正须使用真实来源条目，并回归实际 missing/ambiguous/conflicting seed 路径；不能将 ValueError 大范围吞掉。

独立复现不是转述执行发现：[脚本](geometry-seed-source-original.py) 对固定 fixture 真实运行 W007、从真实 `device_seeds`/`device_identities` 构造 ChannelSeed，直接调用 helper；[原始 stdout/trace](geometry-seed-source-original.log) 保留准确异常。命令为 `/workspace/work/w011-engineering/dev312/bin/python /workspace/work/w011-review-geometry/probe_seed_source.py`，退出 1。修正及独立复核见末节，原 finding 本段不改写为从未发生。

## 阶段性实测与限制

[第一轮独立 probe](geometry-probe-original.py) 的[原始输出](geometry-probe-original.log)记录正常组合成功：MN0=5、MP0=7；分别完整 crossing Y 下界集合为 `{24,34,44,54,64}`、`{114,124,134,144,154,164,174}`；两个 channel 均保留全部 18 FIN evaluations，L=4 nm、每根 W=2 nm、共用 G、四个有序 S/D node refs，原 body/completed 保留，source 比较 equal。共享 CPU 环境下该构建用时 150.3876 秒。

第一轮后续 overlay 阶段因独立 probe 先删除 normalized cache、再复制原 failure overlay 导致 `FileNotFoundError`；这是 reviewer harness 顺序错误，原输出保留，不是产品 finding。已修为先复制/应用 overlay，再删除 cache，继续运行。尚未完成的几何边界 probe、全量测试、双解释器、typing、build/install、readback、异常全矩阵均不由此段声称通过。

第二轮[脚本](geometry-probe-retry.py)与[原始输出](geometry-probe-retry.log)实际完成：

| 样本 | 实测与独立断言 | 构建秒数（共享环境） |
| --- | --- | --- |
| normal | 全部 crossing 集合、18 FIN、5/7、L/W、同 G、四 S/D、body/completed 保留 | 143.9132 |
| 原 extraction_mismatch overlay | MN0=4、MP0=7，唯一差异 MN0 fins_per_finger 4 对 source 5 | 136.8230 |
| 原 via_enclosure overlay | 5/7；原 local.audits 全值保留，其中存在 violation | 46.2388 |
| 追加 FIN `[10,24,110,26]` | MN0 count=None、MP0=7，UnprovenIndependentFins；全部19 FIN保留 | 66.3274 |
| 追加 FIN `[59,30,61,32]` | MN0 count=None、MP0=7，PartialFinCrossing；全部19 FIN保留 | 81.9327 |
| 追加 FIN `[62,30,65,32]` | channel X 边界触碰无正面积，仍5/7，success | 74.7972 |

同轮随后完成 300 个固定随机种子、有理边界分母 6 的 union 用例，独立枚举 1/6 网格 open-cell 比较完整集合、总面积、输出不重叠及重排/重复输入不变，全部通过。再后的 reviewer 手造 seed helper 将 rational 分子/分母写成 int，而公有 Value 格式要求 decimal string，触发 `ValueError('rational components must be decimal strings')`；这是第二处 reviewer harness 错误，原输出保留，不列产品 finding，也不声称后续 seed/FIN atom 用例已在该轮通过。修后复核使用实际 raw seed 变体及 W007 解析，避免此手造格式问题。

CR-05 修正小范围复核：[frozen975 helper脚本](geometry-seed-source-fixed.py)和[输出](geometry-seed-source-fixed.log)已通过，返回 `SourceRef(uri='query/requests.json', field='/requests/0/record_ids/0', sha256='57f5f38cb3ec450fd1815ef88c618c03a9703690672348b313fa35fbce97bc62')`，没有原 ValueError。helper 之外的 seed 分支见末节，不以 helper 单独通过关闭 finding。

非阻塞文字提示：plan 第 54 行把定位、partial、重复问题合写成受影响 count=None；产品实际对定位失败保留独立可算的 channel 几何 count，仅取消无证明的 device 关联/对应 source 比较。该行为符合任务的身份与几何分离，建议执行交付澄清该句，避免混淆几何未知与身份未知。

## frozen975 独立修正复核与最终限制

修正候选 `975852d3b9ea946aca24f727071cf26a7dce8bc7` 从 Git archive 至隔离目录 `/workspace/work/w011-review-geometry/fixed975`；[最终专项脚本](geometry-fixed-probe.py)首行记录的全部 99 个产品 `.py` hash 已逐一与该 commit 验证一致。命令为 `/workspace/work/w011-engineering/dev312/bin/python /workspace/work/w011-review-geometry/geometry-fixed-probe.py`，cwd 为上述 frozen 目录，退出 0；[完整输出](geometry-fixed-probe.log)及[命令/环境/产物身份回执](geometry-command-receipt.json)可跨 session 读取。

该脚本先从真实捕获建立一次 W009 exact channels，随后在临时 fixture 副本中编辑 raw device_info 并重绑字节，通过真实 W007 取得完整来源自洽的 ChannelSeed，再调用中立 locator。它验证定位算法与 CR-05 实际来源路径，不冒称每个变体又走过完整捕获认证的 W011 result；完整真实 W011 正常/几何变体见上一表，正式 seed 变体公有组合及 A6 异常全链由主 review 汇总。

| 实际 raw seed 变体 | 独立期待和结果 |
| --- | --- |
| `[58,20,60.5,70]` | MN0 唯一定位，coverage=5/8，无 issue；通过 |
| 同身份 `[58,20,62,50]` 与 `[58,40,62,70]` | 两条独立证据，重叠面积不重复加，union coverage=1；通过 |
| `[58,20,62,180]` | AmbiguousSeedChannel + UnassociatedChannel，不利用 MP0 其它 seed 消歧；通过 |
| `[58,70,62,80]` | 边相触无正面积，MissingSeedChannel + UnassociatedChannel；通过 |
| 同身份 N/P 两条完整 seed | ConflictingDeviceSeeds + UnassociatedChannel；通过 |
| MN0 无 device-region request | MissingDeviceSeed + UnassociatedChannel，保留 MP0 与全部 channel；通过 |

上述错误分支均正常返回 typed issues，保留实际 source URI/hash，不再抛原 source-wrapper ValueError。**第一次专项复核曾据此写“CR-05 关闭”，并将 pointer 丢失当作低优先级观察；主 reviewer 指出它仍违反 located issue 要求后，该关闭判定已撤回并补充下节。** frozen975 只解决 wrapper 异常，不能用 retained seed provenance 替代 issue 自己的可定位性。原观察是：edge/ambiguous 的 issue `field` 使用分析字段 `/recognized_channel_intersection`，其具体原 request ordinal 虽在 seed provenance，issue 本身却丢失该 JSON pointer。

同一 frozen975 下再次通过 300 个 Fraction union 独立 open-cell 集合/面积见证，以及 250 个随机 FIN 矩形 × 2 个真实 channel 的 **500 项**判定。FIN oracle 使用整数 open-cell/闭边界集合，独立验证正面积、完整 channel X、完整 active Y、touch/outside、partial 的 count=None 与单根 qualified count=1，不调用产品交集/判定方法计算预期。

未发现其它可复现必须修正。这里没有独立运行双解释器完整回归、typing、build/install、源码外 readback/完整公有异常矩阵；没有重新证明所有工艺规则、模型/net/body 匹配、manufacturing coordinates、U06 或发布/no_change/Stage6。构建耗时只是共享主机有限样本，未独立测峰值 RSS 或最大输入能力；这些工程证据与资源限制交父 reviewer 核验最终候选。

## CR-05 复核残留：必须保留真实 record pointer

原残留 findings：在 frozen975，`locate_channels()` 给 missing/ambiguous issue 构造 source 时，用 `replace(seed_source(seed), field='/recognized_channel_intersection')` 覆盖了真实 JSON pointer。两个真实 W007 seeds 同时零候选时，两个 issue 的 source 都是同一 `query/requests.json`/SHA 和不存在的 `/recognized_channel_intersection`，message 也都为 `device seed has 0 positive-area channel candidates`，无法从诊断唯一回指 D0/D1。这是 CR-05 located failure 合同的剩余必须修正，不是可以依赖调用方猜测的展示问题。

[轻量独立 probe](geometry-pointer-probe.py)使用固定 fixture 的真实 W007 seeds，直接给中立 locator 空 channel 集合制造两条零候选诊断；不重跑完整 W011 链。frozen975 的[原输出](geometry-pointer-original.log)退出 1，明确打印期待 `/requests/0/record_ids/0`、`/requests/1/record_ids/0` 与实际两个相同错误字段。`5894399d7b79d655a4a278e78419c4d21eea828e` commit 当时还没有工作树中的 pointer 修正，对其独立 archive 的[原输出](geometry-pointer-589-original.log)同样退出 1；不能仅凭工作树已修改就声称该 commit 通过。

执行修正保留 `seed_source(seed)` 的实际指针，并在 message 中加入具体 `record_id`，分析算子名改放 message。为避免并发改写身份，本 reviewer 从 frozen589 另建隔离目录，只叠加已保存的 [annotation patch](geometry-pointer.patch)；完整修正文件是 [geometry-pointer-annotation.py](geometry-pointer-annotation.py)，所有产品 hash 在[修后输出](geometry-pointer-fixed.log)首行。相同 probe 退出 0：两个实际 source 等于两个原 seed source，互不相同；逐项读取真实 requests JSON 并解析 pointer，分别得到 `D0`/`D1`，message 也包含对应 ID。**CR-05 指针残留独立修正复核通过；现已同时满足 wrapper 解包与具体记录定位要求。** 该 patch 的最终 commit 归属由主 reviewer/执行完成身份核对后追加，不重写原失败。

最终提交归属追加：本 reviewer 直接读取 `8917d38d916c914bfa785cb116982f3f299b38de:layauto_v2/annotation/channel_identity.py`，实际 SHA-256 为 `b30ad5ed83f111de23307ccbdba8d82789eb73b5cb72334fbd668a91f03f7451`，与此前 `ca5ba85e59f6da055d85fc8777ed5f44e21e324d0698626cdc6028be4f62bbcd` **不是字节相同**；唯一差异为 message 内的 `seed.record["record_id"]` 加显式 `str(...)`。ChannelSeed 已要求该值为 exact str，但为准确验证最终候选，仍从该 commit 独立 archive 后重跑同一轻量 probe，退出 0，见[最终输出](geometry-pointer-891.log)及[Git bytes 核对回执](geometry-pointer-commit.json)。该输出首行全部产品 hash 也逐一匹配最终 commit。CR-05 含原异常及定位残留均最终关闭，几何专项代码必须项为 0；A8 和最终整包/矩阵身份由主 reviewer 后续核对。
