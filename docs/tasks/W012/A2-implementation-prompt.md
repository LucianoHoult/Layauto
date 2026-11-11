# W012 A2 最小私有 typed pack：独立执行 session prompt

```text
按Layauto项目规范，以独立执行session完成W012 A2最小私有typed pack实施；先核本分支最新PM派发阶段，只有“可执行”才开始产品修改。
从codex/w012-a2-private-typed-pack的PM准备提交恢复，父级方案交付71488d6034b40cb67970466b082298a8dc0d5eee，main仍为A1验收2489b4609ae97d8211bf450d55cac9392492ac71。核远端完整SHA、工作区、AGENTS/协作/环境规则，读W012最新PM决定、AI1–AI6、A2 plan/independent-review/delivery和PM接收材料，以及实际producer/consumer与必要架构原文；不从旧方案prompt重做AP1–AP5。
runtime仅改normalization/local_connectivity_codec.py与channel_identity_codec.py：按已审方案增加各自私有编码helper，只替换encode_record envelope的pack调用。沿用原_SPEC及exact type/字段/delegate次序；原图validate_closed_graph在任何复制前，map/scalar在原分支位置立即freeze，tuple按序物化，所有nested encoder仍返回完整原bytes。自建dict/tuple只在本操作存活，再交未变canonical_bytes完整freeze/_wire/JSON/UTF-8。原_pack留给decoder且代码不动，_unpack/decode、所有公开DTO/重建、两次认证与_evaluate不动；不将附件参考原型的节点/深度/叶/整数上限带入产品。
只减少这两个encoder的私有FrozenMap包装和对子树的重复freeze，不能删公开验证或新增trusted/cache/memo。保持/1完整字节、wire大小、所有hash/ref、公开签名、来源/run/owner/原bytes、closed/exact scalar、防御快照/单次集合快照及异常object/cause/context/suppression。原domain codec/lower codec/fixture/答案/架构/生产body要求不改；剩余调用的意外异常直接传播，不能删除原测试或放宽旧finding以达标。若发现公开异常依赖拟删的临时构造，恢复该路径或带反例交PM，不自行豁免。
开发先新增及受影响范围：覆盖两个_SPEC的字段/标签/delegate、真公开入口的root/别名/错型等值/来源/run/owner及公开decoder接受拒绝、Unicode/rational/bytes/大整数与异常历史、W009单次快照和W011第二次认证。以原accepted_pack/canonical与明确字节/类型不变量、既有独立判据组合验证，不把新helper自己生成的golden作唯一依据；新附件不能成为runtime依赖。先做受影响方案一致性复核，不重开全量架构或泛化writer设计。
完整筛选前固定两侧实际source/test/config身份；在同机同解释器依赖、固定输入URI/RunRequest/cache/roots/GC上，串行各一组normal direct、normal readback、原extraction_mismatch的before/after完整公开build/encode/decode，全部wire逐字节/hash/ref和正常5/7、mismatch实际4对source5、来源/局部图/T05/body/independent target、readback unsealed/checkpoint/无terminal不变。baseline必须是本机A1原runtime；导入树与输入路径分离，按原35项/五overlay重建mismatch；不能拿不同环境旧样本当before或偷偷换URI。必要脚本先自检，不覆写P1/A1/A2原产物。
如果有限筛选未显示值得继续的改善或出现抵消收益的退化，保留候选和真实结果，明确未完成最终工程/未获产品验收，交PM取舍并停止，不扩大owner或自动启动B。若有依据继续，冻结新源码/正式测试/配置，完成双3.10/3.12全量、strict typing、构建及双干净安装源码外完整组合smoke。最终同条件两侧各3次fresh串行交替无插桩比较，可复用满足同身份/条件的本轮样本；各次、失败和中位完整保留，三路分别披露build/decode/总耗时与峰值/退化，wire降幅为0，不设旧20%/50%硬门。profile只在必要归因时另跑，不能混为产品wall或添加额外巨大编码制造成本。最终矩阵后相关源再变，先定向修正再对新冻结版本完成要求；文档补记不冒记成新受测产品。
由未参与实现或测量工具设计者独立review代码/完整性/性能证据，复核受影响旧合同及新增测试、异常/认证、前后条件/完整wire和收益归因；修正复核必须项并保留原finding和失败。足以推荐时交PM待验收；收益不清也可以交有依据的停止结论，但不冒称完成产品交付。
本轮可写上述两runtime文件、直接必要的新/受影响正式测试、W012下新的A2-implementation附件和任务执行/方案区；PM阶段/要求/current-work与原P1/A1/A2记录由原owner维护，不改原证据。沿用项目noreply身份提交推送原实施分支，核远端完整SHA并交PM；不自行验收、合main、删分支或启动M1下一节点。关键外部格式/行为、身份/历史迁移或架构变化另带具体材料交PM/用户，不推定已获批。
```
