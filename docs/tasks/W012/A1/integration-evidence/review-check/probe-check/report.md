# W012 A1 review111 / finite probe identity check

结论：新增必须项 **0**、剩余必须项 **0**。交付中的111项正式回归原输出与150,728有限候选探针结果，按已核身份可采信；本子核验未重跑产品、pytest、探针、工程矩阵或大wire。

核验对象为交付 `1a1459e3179e7bd234e4971c1969a6a78f387fd2` 的 `docs/tasks/W012/A1/premerge-review-evidence/`，原受审head为 `e4179dd42cc0de853df73bafd9140a363c8fa5be`。执行核验时共享checkout已进入合并head `08dd232139918dc97b0a6d255aad237eb844686a`，实际核其tree与交付1a相同，工作区始终clean。

- 67项 `files-manifest.json` 全部逐项SHA-256闭合，文件集合也完整匹配seal排除规则；manifest SHA-256为 `44903ec18bce2a214f4c60243b7b51acf7404716c1e3b666c62f2a67a7ba0a4f`。seal结果/原stdout相同，seal命令与stream身份闭合。
- 全部11份根命令记录的cwd、reviewed_head、22份stdout/stderr哈希均通过；原退出码与seal的10条既有命令记录一致，seal自身exit0。
- 正式原输出为targeted **89 passed** 与affected **22 passed**，均exit0、stderr空、禁用插件自动加载和缓存/字节码写入；两命令测试文件互不重叠。affected的22条独立node ID及collect命令参数与实际运行参数闭合，合计111项，不把有限探针计入正式测试数。
- 第三轮探针exit0、stderr空，原stdout与 `contracts/result.json` 逐字节相同（SHA-256 `2cc90dfe379e109516a92bd0c300fdce9e02b7f45bba9f4f9cc9828a6e249195`）。独立重算候选数量 `65536 + 65536 + Σ(7^n,n=0..5) + 40 + 8 = 150728`，与结果的acceptance/前后对照计数相符。实际读成功探针，oracle逐nibble构造bytes，无regex、len/parity或fromhex oracle。
- 三份探针源快照均与seal记录和manifest逐项一致；前两轮exit1及原错误/源快照完整保留，分别为观察列表串用和结果展示的bytes JSON序列化，第三轮对应修正已实读。
- 两份codec快照逐字节等于Git实际blob：main `0a3326aa363477724465886cd05874d0997fba3e` 原版SHA-256 `f1a3a45fbce452957c1c04b8b8c711f17c63a81c5c30d637e9d89dd67d414252`；e417交付版SHA-256 `498efd7d2cd8367bb660883b6e23cc302776d27cfbe487687ef6eab37773b1c7`。后者也实际等于1a的codec blob。成功探针源SHA-256 `fb61dd56ee3aab15282f35dd485ffaf4ab3b48ae40829c92430112240379c73c`。

限制：这是对原结果与证据身份的只读核验。有限synthetic候选不是全生产输入域或最大输入保证；已披露私调恶意str子类的len副作用仍保留，不扩大公开JSON边界承诺；未在此子项重比大wire、读取原安装树或重跑性能/工程矩阵。

本checker首轮仅因PM已合并导致固定HEAD断言失败，失败命令、原stderr及原脚本快照保留在 `attempt01.*` / `check-attempt01.py.txt`，不属于产品finding。调整为接受已核tree相同的合并head后第二轮exit0。最终脚本 [check.py](check.py)、[原命令](attempt02.command.json)、[原stdout](attempt02.stdout.txt)、[原stderr](attempt02.stderr.txt)、[结构化结果](result.json) 均位于本目录；仓库未修改。
