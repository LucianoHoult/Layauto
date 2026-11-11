# W012 兼容 A2 方案收敛：独立执行 prompt

```text
按Layauto项目规范，以独立执行session完成W012的“A2兼容方案收敛与独立方案review”，本次不实施产品优化。
从codex/w012-a2-serialization-plan的PM准备提交恢复；起点main为2489b4609ae97d8211bf450d55cac9392492ac71，已含A1最终验收。先核远端完整SHA/工作区/AGENTS和协作环境规则，读W012最新PM决定与A2 AP1–AP5、A1实际merge/263源和after-profile/性能报告、原P1方案与必要架构/接口合同。
本次只写W012下新的A2方案、有限参考原型/工具自检及证据、独立review和任务执行/方案区；runtime/正式测试/fixture/原工具报告/PM阶段/current-work不改，不新增或切换公开codec。
优先复用A1后真实profile/阶段数据和静态调用链，区分wall、exclusive、嵌套cumulative；readback build约51s、decode约66s、最终encode约2.6s，不能只优化最后encode却推定总收益。只收敛一个最小共同序列化/typed pack/freeze候选，reader或memo不是并行必做包，B新wire不在本次范围。
提出可直接实施的owner/入口/数据流/字段算法、旧到新字节等价方法，以及可变输入防御快照、closed/exact scalar、排序/escape/rational/UTF-8、来源和异常防线。列出拟减少的中间对象/复制与必须保留的公开DTO constructor、完整重建及第二次认证路径，不得以“都不可变”或hash相同跳过认证。若需演示，可在附件内做有界独立参考原型和小样本对照，不替换/monkeypatch现有完整runtime入口，不称微基准是产品收益。
方案保持/1完整canonical bytes/wire大小/全部hash/ref、公开签名、来源/run/owner/原bytes以及既有公开验证/异常合同；wire降幅必须为0。旧20%/50%不是A2硬门，任何目标建议都要给成本/影响依据及不确定性，不承诺未测生产上界。
给出候选对build/decode各条实际调用路径的收益依据、残余和退化风险；未来验证必须固定输入URI/RunRequest/cache/roots/GC、完整direct/readback/mismatch逐字节与无插桩前后比较。未来真正实施开发先新增/受影响，最终冻结仍双全量/typing/构建/双干净安装；本次方案阶段runtime不变，采信同源已验收A1工程证据，不重复小时级矩阵或18条benchmark。有限新检查应有实际必要性及身份/命令/原输出，不为凑数量补测。
未参与方案/参考工具设计者做独立review，重点检查收益归因、完整性与别名/异常/第二次认证、wire等价和方案是否已足以直接派发最小实现。保留finding并修正复核必须项；可以交“有依据的推荐方案”或“兼容范围内收益/等价依据不足，建议回M1网络标注”的结论，不能泛泛留待以后研究或自动扩成新格式/认证删减。
提交推送原A2方案分支，沿用项目noreply身份并核远端完整SHA，交PM；不自行验收、合main、改入口、实施产品优化或启动新子项。若改变关键外部格式/行为、身份/历史迁移或架构才可继续，带具体反例/影响交PM，不推定批准。
```
