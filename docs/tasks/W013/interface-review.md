# W013 独立方案 review

Reviewer：`/root/independent_review`，2026-11-12。未参与候选方案设计、产品或测试实现。
本轮只审实施前方案和输入事实，不构成代码 review、W013 产品通过或 PM 验收。

## 受审身份与实查范围

基线与本地 HEAD：`d6182fe6893c26490f9d58c6b808a5ce9910384b`，分支
`codex/w013-net-annotation-coverage`。初审时产品/测试/配置相对该基线无差异。
仅根 AGENTS 适用。已读 README、协作/环境说明、W013 要求及 architecture
§3.3、3.5–3.8、5.3–5.9、11.2/3/5/9/15；独立核查 W007 seed/QueryKey、
W005 raw→normalized、W009 region、W010图/codec、当前 tech/oracle 与 MR-034。

| 受审文件 | 初审 SHA-256 |
| --- | --- |
| `interface-plan.md` | `dabb22fb38e5090c54c927602458db286f14578a148a20a7917d204964b53f40` |
| `pm-decision.md` | `a54c44b9da980b84bfb6ea3b96c79656f654c5812e2eaa23174dbcefa065496a` |
| `input-boundary-probe.py` | `151d5afe6c73d91e5d214e774b94274cf9c6a315d431c350d1db517e50e3395f` |
| `input-boundary-probe.stdout.json` | `e95cb7ea6fbe3e72969a566c47247952c6ff032b32ac4c8ce1f59cf726423847` |

独立脚本 [input_contract_probe.py](review-evidence/input_contract_probe.py)
SHA-256 `b23b2edde219bfeba1cb1eb59db2eb6cf70cd563ac8278bd541b005f79c19e74`；
[原输出](review-evidence/input_contract_probe.stdout.json)
SHA-256 `d72bfe796e195a06c373a5922f1fa5c36024ddb66425e75951accb2514538d6e`。
实跑命令（仓库根目录）：

```sh
PYTHONDONTWRITEBYTECODE=1 /workspace/.venvs/layauto/bin/python -B docs/tasks/W013/review-evidence/input_contract_probe.py
```

Python 3.12.14，exit 0，约 0.93s。预期拒绝的原类型/消息在 JSON 保留，未改被审实现。

## Findings 原文

### PR-01 / P01：007 的验收层次未决，阻止关键产品实施

**必须项，PM 未决。** 任务 A1 要求保留包括 `007` 的 opaque index，而现行唯一
`calibre_like_synthetic/2` 捕获输入按 NET NAMES 行次生成 `1`/`2`/`3`/`4`，没有显式数字 token。
`domain/identifiers.py:118` 拒绝 `007`；即使绕过这一处准入，
`normalization/_validation.py:281–283` 仍要求字符串等于真实一基 ordinal。

独立反例不止构造 DTO：从真实 reader 得到 ParseResult，保留其全部原 sources，
同步把 value/completed 中 n_a 的 index 改成 `007` 后，`from_parse_result` 原样拒绝：
`ValueError: LVS index is not its captured NET NAMES ordinal`。未向 raw 添加不存在字段。
当前 `query/dialect.json.net_index` 及人工 MR-034 明确该解释，W004 也明确不能为保旧007
伪造前导零。故只有修改 regex 既不能闭合真实 capture，也不能证明 A1 已支持。

[PM 材料](pm-decision.md) 对事实和影响的表述成立。选 A 会澄清/收窄“含007”的本次验收，
选 B 会新增 raw/profile 的解释；若仅要求 neutral DTO 保真，也须明确该层次及上游准入授权。
Reviewer 不代替 PM 作此决定。本项不是普通内部算法选择，不能因已有正常 ordinal 路径
可实施而自行标关闭或把 A1–A8 宣称完成。

**状态：开放，等待 PM 明确。**

### PR-02：A7 尚缺可核查的认证/序列化展开

**必须项，方案补充。** 候选调用图说明“只存一份 W010 input”，但没有展开以下决定
新增成本的边界：public builder、Result 公开构造、new decode 各自何处重进完整 W010
codec 重建；新 codec 如何承载旧 W010 bytes；encode/decode 后有几次完整上游认证。
一份逻辑 input 不等于一份 wire 成本，旧 codec 的 bytes 再嵌入新 canonical Value 可能
增加编码体积及瞬时 retained roots。当前图不能据此核验“预计新增捕获”。

须在实施前列出候选调用序列和序列化树，明确完整 captured input 的字段出现次数、
旧 wire bytes 的承载方式、公开认证的预计触发点与测量归因。不要求现在重写旧 codec、
删验证或宣称静态推算等于性能实测；最早可运行三路 fresh process 的 time/RSS/wire
检查仍是必须节点。若实际实现偏离这份展开，须重新核受影响方案及资源风险。

**状态：开放，待执行者补充后复核。**

## 其余核查结论与限制

- source-evidence/local scope、state.annotation owner、annotation 只生成草稿、derive 分量摘要、
  不嵌 W011、不发布 baseline/terminal 的职责划分符合本次范围。
- 每个 W010 node 对应独立 target；Fraction nm 裁交、按证据边界分片、同网 union 去重、
  direct conflict 与 component conflict 分列、分量关联不替代每region直接覆盖，符合架构。
- 独立从当前 spec/oracle 做整数面积求和：POLY720、LI1110、M1 1340 nm² 直接覆盖；
  全部本地 node 面积35090 nm²，14 nodes/8 edges/6 components。OD/BODY 无直接 net mapping。
  正常 oracle 已是本地范围，外部 body_associations 独立；A 孤岛仅在 standalone special，
  不能复用旧16/10或“加回正常例”建议作为现行正常答案。
- 非 exact quality 当前不能进入 W007 成功 seed。独立构造 approximate_bbox/untrimmed seed
  均得到原 `ValueError: unsupported annotation seed geometry/quality/unit`。方案如实声明上游
  支持限制，不能在未来把该拒绝探针算成 W013 空间匹配已覆盖。非零 tolerance/未知 trim
  仍须在实际代码/组合 review 核 typed unsupported 与原来源，不得升级质量。
- 当前方案的同网多target不应自动合并物理分量；精确证据可覆盖多个target时保留全部，
  真正 mapping/quality/tolerance 歧义须显露而不随机选。代码 review 将核具体实现和反例。
- 当前只有方案/调查证据，没有新产品、wire、资源组合或工程矩阵。未发现的实现风险
  不能由本次静态核查视作已通过。

## 验证复用与当前结论

| 类别 | 本轮事实 |
| --- | --- |
| 实跑 | 上述独立轻量探针、当前 git 产品范围 diff、文件 SHA；静态合同与oracle核查 |
| 按身份采信 | 未运行旧全量；已验收上游作为现行合同依据。候选援引旧A1矩阵只作同身份历史，不当新W013最终矩阵 |
| 未覆盖 | W013实现、三路新增成本、双3.10/3.12新冻结全量/typing/build/双安装、代码/组合/资源review |
| 补跑触发 | PM 决定使输入范围变化、方案修订、实际代码/测试/config/依赖变化、证据身份不闭合或独立新风险；新产品最终矩阵必须重新冻结执行 |

**初审结论：未通过实施门。** PR-01/P01 和 PR-02 未关闭；保留本次原 findings，
执行者修订后由 reviewer 追加复核，不改写原事实。无用户/PM决定可被 elapsed time 或 reviewer
意见替代；本报告不维护 PM 阶段/current-work，不启动下一任务。

## 初审追加 PR-03：固定 roots 与独立 W011 基线的范围有歧义

**必须项，方案补充。** 初审候选一方面声明 W013 不调用/嵌入 W011，另一方面要求
“保留所有既有roots并加W013 roots”。旧 probe 的 result/restored/wire 是完整 W011
值；若按字面额外构造并保留，会改变本次主路径 workload/峰值，并把未改 W011 成本
混入新增 W013。若直接删除，又不能无记录宣称与旧三路完全同条件。

方案应列出 W013 主路径 retained roots 的实际对象与替换关系，说明是否存在 W011
对象；同机旧 W011 基线必须明确为独立条件/进程和原 roots，不能将它的构造成本隐含
进 W013 主路径。原 URI、RunRequest、cache、GC 的可比性和不等条件分别记录。
本项不会要求重开 A2/B 或为了复用旧 root 名称多跑完整 W011。

**状态：开放，待执行者补充后复核。** 初审实施门仍未通过。

## 修订复核（2026-11-12）

初审全部原文与附件已固定在 `0794d2dc90baaf8d3180e9ce4f4d91683fe90dc7`。
本次只复核修后 [方案](interface-plan.md)，SHA-256
`827dd88dd7eb638fa8ec98b15768e9ccb30880eed549d4257fc5337abda1830d`；
PM材料和初审输入探针身份未变。未修改方案或产品。

- **PR-02 方案层关闭。** 新增序列化树明确完整旧W010 canonical Value子树一次、compact字段一次、
  W011捕获零次；反向恢复原旧wire bytes，再走未改旧public decode完整认证。确认
  `domain.codec._wire` 对bytes使用hex，直接opaque bytes嵌套会新增约2B10项；修后方案避免
  对整个旧wire再hex一次，没有宣称消除旧wire内部既有重复。新public build/Result、encode、
  decode新增顶层W010 decode次数按1/1/2展开，明确旧decode内部仍递归重建，未将4说成全链总调用。
  Result由输入派生且encode重新认证，decode对照全部派生字段；无caller认证标志或跨调用cache。
  这些是待实施的具体边界，代码偏离、canonical遗漏或实际成本问题仍须重新review。
- **PR-03 方案层关闭。** 主路径roots明确替换旧W011 result/restored/wire为W013对应值，
  W011实例零；保留其它上游/readback对象和GC条件。独立同机W011基线另起进程，披露不同
  终端workload，不以总时长直接作新增模块收益结论；不默认多跑完整W011。
- **PR-01/P01 保持开放。** 未见PM决定；本次复核不替PM选择A/B或neutral层验收解释。
  **整体仍未通过实施门**，不实施关键产品、不宣称A1–A8完成。

额外独立实跑 [Value envelope基本性质探针](review-evidence/value_envelope_probe.py)，
脚本SHA-256 `a53ef7c04cb8c0e928f7262a00a2996f2a17f71cbf8e52ef9cd8df1943e41f94`；
[原输出](review-evidence/value_envelope_probe.stdout.json)
SHA-256 `1eead623319acafba512c786d5ae1cea95d275961bb603abeb048303af5f16d1`。
使用未改publication codec的SourceFile小值，旧wire806B，完整Value子树envelope874B，
opaque bytes envelope1693B；恢复的旧wire SHA完全相同，且改SourceFile sha后旧public decoder
拒绝。只验证canonical algebra和保留旧认证的必要性，**没有构造W010 Result/W013产品，没有
测其耗时或峰值**，不能替代三路资源检查点。

探针初稿错用publication envelope字段名`record`，实际为`value`，先出现
`KeyError: 'record'`。这是review脚本错误；[原脚本](review-evidence/value_envelope_probe.attempt-01.py)、
[重现stderr](review-evidence/value_envelope_probe.attempt-01.stderr.txt)保留，修后exit0；
未把它报成产品finding或删除原失败。

再次独立逐hash核对旧A1清单263文件，零差异，见
[source_identity_review.json](review-evidence/source_identity_review.json)；
旧清单SHA-256 `d42efdb27b72973a8a6f5f738d57a2fcecdde7bfe89c7b944e7144b3b088915b`。
因此当前仍是方案/调查交接，只可按身份引用上游历史证据。新产品最终矩阵、代码/组合/资源
review全部未执行；不能将上述小值探针或旧A1矩阵作为它们的替代。

## P01 用户答复后的实施门复核（2026-11-12）

本轮用户明确选择：**“保持当前真实捕获范围；007记为不支持/拒绝反例（推荐）”。**
执行按原答复追加的 [P01决定](pm-decision.md#p01-用户决定2026-11-12执行按原答复记录)
与本次授权一致。受审新方案SHA-256为
`7591fa5d2deb24ced2f2301db7d4cf953801d704ac812e9da092010262f40e1c`，
决定材料SHA-256为
`6184be393146c35dfa12bb2b073559cd4f12e2ac3f6b87db69cb811106bf488b`。
复核基于 `aaa55cc081d16ff74ab51ec5a69149ca549363ed` 后的上述文档增补；产品、测试、
配置尚无变更。原P01待决说明、拒绝反例和历次review结论保留历史身份。

**PR-01/P01 关闭。** 本次A1按当前方言真实ordinal字符串保真、同源身份与跨run拒绝核验；
`007`仍是明确不支持/拒绝见证。该决定不授权伪造raw字段、修改旧QueryKey准入、恢复旧方言，
也不把neutral构造当成真实capture支持。先前PR-02/03方案层修正继续成立，未新增必须修正项。

**本次方案实施门通过，可在该既定范围内实施W013。** 此结论仅解除关键产品实施门，
不是代码/合同/组合/资源证据review通过，更不是A1–A8产品完成或PM验收。最早完整三路
成本检查、实际代码偏离时的复核、新冻结双解释器全量/typing/build/双安装与独立代码review
仍按原要求执行；若出现新的输入/policy缺口或明显资源放大，仍须携具体证据交PM。

本次实跑仅文件身份/范围diff及文档决定核查；先前轻量探针按其源身份采信，未重复双全量。
未覆盖及补跑触发条件仍按上节执行。Reviewer未参与实现、不改PM阶段/current-work。
