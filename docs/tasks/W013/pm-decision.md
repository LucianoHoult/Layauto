# P01：007 与当前已验收捕获合同冲突

2026-11-12，执行调查，基线 `d6182fe6893c26490f9d58c6b808a5ce9910384b`。
这是具体输入范围/验收预期待决，尚无 PM 决定；不是 W013 已实现交付。

## 证据与反例

1. W013 A1 要求“保留QueryKey opaque lvs_index（含007）”，同时要求消费真实W007 seeds，
   不更改已验收fixture/答案、旧codec/wire/ref或自行扩展输入解释。
2. 当前 `query/dialect.json.net_index` 明定
   `1-based ordinal of NET NAMES; query-run scoped opaque; join nXref by lvs_name`。
   当前NET NAMES四行仅为n_a/n_y/n_lo/n_hi；没有显式数字token。
3. `importers/calibre.py:_net_records` 按ordinal生成字符串1/2/3/4；
   `normalization/_validation.py:_validate_query` 强制等于 `str(line_1based - 3)`。
   `domain/identifiers.py:QueryKey` 的 `[1-9][0-9]*` 也拒绝前导零。
4. [可复现脚本](input-boundary-probe.py) 实跑真实reader→W007，取得上述四个身份和8个exact seeds；
   `QueryKey(..., index='7')` 接受，`index='007'` 原异常是
   `ValueError: net query key requires a positive opaque decimal index`。
   [原输出](input-boundary-probe.stdout.json) 保留执行环境、输入URI、来源hash、index字段provenance。
5. 人工 `W003/manual-verification.md` MR-034 明确：新方言若按NET NAMES顺序提供编号，编号可变，
   不为强保旧007伪造raw字段/前导零。`W004-fixture-revision.md` 格式调查段再次确认该决定。

opaque 表示身份只在query-run/database内有效，不能由其数值推断canonical NetId；
不表示每个当前dialect都能提供任意词法形式。把当前ordinal7格式化成007会改变真实证据；
只放宽QueryKey不能让真实reader/capture认证产生007。向NET NAMES写入“007 n_a”会改变名称/语法，
也不是现有声明的显式index字段。

## 需 PM 明确的选择

推荐 **A：本次保持当前捕获子集**。A1按真实1/2/3/4字符串保真与跨run身份拒绝验收；
007记录为当前dialect不能表示的已知限制/拒绝反例，不宣称已支持。未来带显式index的真实
raw格式或profile另行准备；不恢复已废弃的旧convenience JSON。此项会澄清/收窄A1“含007”预期，
须 PM 明确后才能把A1记为满足，执行者不能自行批准。

备选 **B：本次必须让007端到端可组合**。先提供/决定新的captured格式/profile与词法来源，
确定其与当前ordinal方言的区分及source provenance，再独立review最小W005/W007/DTO变更。
这会扩大输入边界、错误路径、测试/typing/最终验证范围；不应只改regex、不应伪造旧raw。
当前没有该新格式的证据，不能自行发明。

若PM意图只要求未来neutral DTO保真而非本次真实捕获支持，也须明确其验收层次与是否授权
改变已验收QueryKey准入；不能用neutral探针冒充真实seed/capture组合。

## 当前恢复点

- [具体方案候选](interface-plan.md) 已准备，等待未参与设计/实现的独立review。
- 关键产品实施停于方案门；不发布baseline/terminal，不改PM阶段/current-work，不宣称A1–A8完成。
- 本次实跑：分支/远端/工作区/祖先与A1产品diff；真实reader→W007与007构造反例；环境库存、
  263项旧A1源码清单逐hash核验。原产品无变化，不运行无意义的新双全量。
- 按身份采信：仅现有A1相同源码的历史上游证据，历史耗时非本机测量。未覆盖：W013新产品、
  三路新增资源组合、新冻结矩阵/typing/build/双安装、代码review。
- 补跑触发：PM关闭P01且方案必须项关闭后实施；最早组合即测direct/readback/mismatch；
  若有资源放大先交PM；最终产品须新冻结双3.10/3.12矩阵，任何相关源码改变重新冻结验证。
