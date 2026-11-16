# W014 合并前独立 review session prompt

```text
按Layauto项目规范，以未参与W014设计/实现的独立review session复核是否具备main集成条件。恢复codex/w014-terminal-body-relations最新PM接收head，先核完整远端SHA、工作区、AGENTS、协作规则和明确任务范围。

版本：main/base为8f3f39562ed04d790c8d6c015f7c9b8742b6a3c4；执行交付6033537add14beadbbc441fdcfe5f6ef905ea948；实际产品/测试/config冻结66f5b1e5369549ed8df361f89f099acfd2f39e17；286项source_id=c7769fcbfb0312b93e4d44628c77ff21e273698a537eaba0e1454734b049d364，111 runtime。后续PM接收只改文档/核对脚本，不冒作新的受测产品；恢复时检查这个事实仍成立。

先读W014任务A1–A9及PM1、plan/plan-review、execution、code-review最终与原finding、body-design-notes、production-body-scope、resource-review最终选择及verification/receipt。对照architecture §2.3/3.3/3.6/4.5–4.7/5.6–5.9/11.2/11.5/11.9/11.15、roadmap U06、W003/W004现行合同与独立oracle及REQ-01。审实际15条产品/测试/config diff和W007/W009/W010/W011/W013生产者消费者两侧，不仅阅读总结或重跑执行测试。

重点1：每个source device有完整ordered D/G/S/B。器件身份/channel定位、local node/component、query observed net、CDL expected、target intent分开；共享gate保留两器件关系，不整条POLY独占；不以S/D swap、同名、source expectation消除unknown/conflict/mismatch。缺channel仍保留四端及缺项，原FIN4对source5、全部target差异、W013coverage/issues不能被覆盖；source_comparison_status是有限FIN/L/W/八端比较，不是完整model/VT/extraction/LVS结论。

重点2：外部body来源有序绑定context owner与actual GDS，top/FRAME/对象/单位/profile/operator/rules闭合。独立检查正面积、FRAME处正长度续接、唯一匹配、local body包围active、全local/external异型body pair与全部external tap（含orphan），不是只遍历指定成功链。几何链、T04/T05包围规则和T08 source比较分别表达。exact rail query锚须精确，901/20不能变45；精确锚之后仍传播真实rail component冲突。context expected_semantic_rail是待核主张，不能当观测真值；外部6图形不进入本地layout/occupancy/导出，本地14/8/6及两body unknown不改变。独立手算/反例覆盖包围边界、断开、类型、歧义和“提供但错误”情形。

重点3：公开captured入口与neutral DTO分开审。原存储字段全集、可写alias/native scalar/tuple/FrozenMap、合法旧init=False class default、SourceRef/EvidenceRecord外壳、Result所有实际保留的input/value/facts、typed canonical快照、decode结构错误及原异常object/cause/context/suppression。CR01–07/09–12关闭是否完整；CR08公开漏洞归因已撤回，须读其真实W009拒绝边界，不把历史文字当新阻塞。不能在编码前复制丢弃坏字段、只验证投影，或把内部错误伪装成输入ValueError。旧codec/wire/完整认证保持，单份W010捕获+neutral W011/W013/body不是两套Result嵌套。

重点4：A8是设计交付。核四类生产单cell样张能保留本地已知端口/net，区分未知父级/global关系、未证明body路径、错误选定证据及人工意图。缺资料不等于cell错误，错误证据不能降成未选择；可信替代/冻结需完整scope与body/boundary invariant。现reader仍必填body_context，不能将本设计写成已经支持的生产入口或新增用户已批准格式，不重新问D1=A。

验证采用docs/collaboration/rules.md#verification-reuse：先列本次实跑、按身份采信、未覆盖、补跑触发。R2标签不能误用：W014最终目录为verification/，双3.10/3.12各1889、双typing65、build、双clean安装三路smoke已有同源证据；PM另核286源/live/frozen/delivery/tar、81证据hash、21命令输出及两包各111 runtime，只是文件/收据核对。按身份采信这些完整矩阵，独立性来自审代码、数学/来源/攻击反例和必要公开组合，不因换session重跑双全量或复制大wire/安装树。新增风险、身份不闭合或实际源/输入/依赖变化才补对应验证；重型路径串行，先解释范围。

资源核最终R4选择：clean direct、原R4 readback/mismatch各保持原路径和hash；原direct曾与6.30秒probe交叠，不能改成全套无交叠新suite。R4测量源998aa805…到最终c7769fcb…只改测试分支；旧W013 reference为803b4c4f…并核相关106旧runtime。最终新增wire约345KB，三路公开阶段耗时比1.133/1.031/1.093，峰值约196/492/204MiB；单样本、有限fixture，不当稳定优化/生产或最大输入上界。W010公开decode为1/1/2，不能据此声称所有内部对象只重建一次。

仅新增docs/tasks/W014/independent-premerge-review.md与必要有界脚本/原输出，并追加任务reviewer区；不改产品/正式测试/fixture/历史报告、PM要求/验收段或current-work。报告绑定base/head或确切快照，逐A1–A9给独立判断、findings/复现影响、证据及覆盖限制，结论为可交PM集成及组合验证或仍有阻塞。保留探针自身失败及修正事实，不包装成产品finding或测试通过。

沿原W014分支使用项目noreply身份提交推送，核远端完整SHA后交PM；不自行验收、合main、删分支或启动下一任务。发现问题只报告并给局部修复交接，不自行扩大产品范围。
```
