# W013 合并前独立 review session prompt

```text
按Layauto项目规范，以未参与W013设计/实现的独立review session复核W013是否具备main集成条件。
恢复codex/w013-net-annotation-coverage最新PM接收提交，先核远端完整SHA/工作区/AGENTS/协作规则。产品交付63a0962f1b56655f234140822bffa8f56b7bb15f，冻结2a45938aba8e751183d472d660a1ab66a1063636，273项source_id=2c5724a9d3ecf99913857ad89015c03c03475ae762c1c8ab00b5146fd3eec278；main基线d6182fe6893c26490f9d58c6b808a5ce9910384b。后续PM接收仅文档，不冒作新受测产品。
先读W013当前要求/PM1、pm-decision、interface-plan/review、code-review、handoff-scope-audit、resource-summary及R2证据；对照架构§3.3/3.5–3.8/5.3–5.9/11.2/11.5/11.9/11.15、MR-020/MR-034及现行独立local oracle，审实际产品diff/调用两侧。007按已决定的现行ordinal合同拒绝，不扩parser/QueryKey；正常六本地分量是4关联+2未知body，A三分量属于cut专例，不能将旧正常孤岛说明当当前golden。
重点查：raw/xref→NetId/QueryKey及run/database/owner/tech/unit/top/scope绑定；exact partition/union/coverage分母、同网重复/部分/边点/同cell多occupant、unmatched/质量/unsupported；component推断与region直接覆盖区别，unknown body/MARK保留、冲突不造物理edge。查neutral/captured两级合同：operator owner一致性、FrozenMap backing/alias/native scalar、分类与全部contributor闭合、字段/来源/异常object/cause/context/suppression，CR-01–03关闭是否完整；保留的W007架构guard只能精确放行两个模块的只读AnnotationDraft，不能放开publication/mutable state。
审新codec只承载一次完整W010 canonical Value、旧wire/ref与原完整认证保持；草稿仅synthetic local/source-evidence，不发布baseline/terminal、不把外部body证据变成本地连接，不把标注视作LVS通过。检查binding与目标几何变化后的失效边界，任何任意shape摘要不能替代region完整性。
遵循verification-reuse默认规则：已有R2双1731、双typing60、build/双干净安装三路smoke及PM273源/81证据/21命令/两包106runtime核对可按身份采信；独立性靠审代码、独立数学/来源/攻击反例及关键公开路径，不机械重跑双全量或复制整套wire/安装树。先列实跑/采信/未覆盖/补跑触发依据；需要重型检查时先说明具体未闭合风险、串行限量，不能冒记未跑检查。PM receipt只是文件/收据核对，不代替你的独立产品判断。
资源04旧source6463eb67…经R2仅test whitelist delta采信，新runtime/config/input/probe均同源的链要核适用性。新wire约23.1/59.7/23.1MB、compact增量约0.315MB、W010公开decode认证1/1/2；inclusive计时不能相加，W013/W011是不同终端工作负载，不能声称跨环境提速。原失败/修正/引用补正均保留，资源仍有完整认证成本。
只新增docs/tasks/W013/independent-premerge-review.md及必要有界复现/原输出，追加任务reviewer区；不改产品/正式测试/fixture/历史报告、PM验收段或current-work。报告绑定实际base/head或快照，列A1–A8/必须项、复现影响、证据与限制，明确“可进入PM集成及组合验证”或“仍有阻塞”。使用项目noreply身份提交推送原W013分支、核远端完整SHA，交PM；不自行验收、合main、删分支或启动后续任务。
```
