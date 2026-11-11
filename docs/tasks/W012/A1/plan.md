# A1 最小方案与验证计划（实施前）

恢复：远端准备 `7f7c1304bdafd941791421cef64864fb1616303c`，调查接收 `9b573c99d5f4021636f498292f42b53540bff1a1`；原100 runtime/262源与main `0a3326aa363477724465886cd05874d0997fba3e`相同。原工作区干净。遵循W012最新PM1/PM2及I1–I6；原P1/P2附件和finding不改。

## 唯一产品改动候选

仅替换 `domain/codec.py::_decode` 的bytes分支准入条件，由重复分组 `(?:[0-9a-f]{2})*` 改为 `re.fullmatch(r'[0-9a-f]*', raw) and len(raw) % 2 == 0`。保留matcher先执行、长度后判断，仍只调用一次matcher；不先用长度短路遮蔽原matcher异常。原 `isinstance(..., str)`、`bytes.fromhex(raw)`、错误raise、公开函数及最终canonical重编码不动，不新增helper/cache/except或修改其它runtime。

语言证明：令H为16个小写ASCII十六进制字符，原语言为(HH)*；新语言H*与偶数长度的交集恰为(HH)*，包含空串。空白、换行、大写、奇数、Unicode近似字符均不被新条件接纳。非分组的单字符重复在本次CPython3.10/3.12使用简单repeat路径，预期避免每两字符一次的分组repeat瞬时空间；实际内存改善只以完整公开路径和matcher窗口实测判断，不将语言证明当内存证明。

未改encoder、格式或constructor/认证路径，预期 `/1` 所有bytes/hash/ref完全相同。matcher/fromhex意外异常保持原对象、cause/context/suppression，不捕获或重包。旧的奇数合法字符串matcher会返回无匹配，新matcher会匹配后由长度拒绝，最终公开拒绝相同；原matcher调用和fromhex不准入边界保留。内部Match对象不是公开返回值。此方案先交未设计者独立review，通过后才改产品。

## 开发验证

新增直接必要的hex合同测试：全部256字节/hex对、有限代表字母表的完整枚举与独立逐字符/长度判据，空/奇数/大小写/ASCII空白/换行/Unicode/长合法和非法尾部；公开decode中畸形tag/错型/duplicate-key/JSON空白、Unicode转义、非规范数字及canonical原bytes拒绝。核原matcher和fromhex的异常object/cause/context/suppression，含ValueError/TypeError/KeyError/KeyboardInterrupt/SystemExit；核matcher调用仍发生于奇数/非法字符串，fromhex仅合法语言调用。

运行新增及现有受影响基础codec、publication/嵌套geometry/effective/local/channel codec和W011二次故障/来源/别名/错型等值负例。按依赖选择具体测试并保存收集清单/命令/原输出。原测试不删、不降断言。实现与测试冻结后，执行新源双3.10/3.12全量、strict typing、构建与两解释器干净安装的源码外完整组合smoke。

## 同条件完整性能

新A1工具仅适配原P1 probe的runtime导入位置/身份、输出和byte comparison；原工具不改。before在 `/workspace/w012-a1-before` 导入，after在本checkout导入。输入始终为 `/workspace/Layauto/tests/fixtures/w003_m1/site_config.yaml`，mismatch始终 `/workspace/w012-inputs/extraction-mismatch/site_config.yaml`，先按P1 preflight35项清单重建/核原bytes。RunRequest固定原P1的 `w012-investigation-run` / `w012-investigation-lineage` / `create-w012`，cache原模式。各进程开始一次gc.collect，之后默认GC；同样保留parsed/geometry/effective/local/result/wire/restored和readback仓库/ready/checkpoint/parse/tool/audits/attempt。

两侧最终每路径各3个fresh无插桩进程，所有重型性能样本串行；允许开发第一组同时成为最终相同冻结源样本。按rep和case交替before/after，减小时间漂移，不以历史单次作before。保存每次时间、wire长度/hash、整进程峰值/失败；实际wire保存于Git外测量工作目录，父进程在样本结束后逐块byte-for-byte比较（不在被测阶段额外encode）。三路完整FIN/crossing/来源/局部图/T05/body及unsealed/checkpoint/无terminal断言继承原probe，并验证target独立和refs等价。

新旧独立profile/窗口诊断与baseline分开，观察既有matcher参数长度与RSS/HWM，不额外编码大对象。新pattern也被观察；比较完整constructor/认证次数是否相同、最终峰值是否仍出现在matcher窗口。逐路径报告各次/中位耗时和各次峰值、改善/退化及残余成本；20%/50%不是A1硬门，不为达标扩到writer/memo/新格式。

独立方案/代码/正确性/性能review必须项全部修正复核后，以项目noreply提交推送原A1分支并核远端完整SHA，交PM停止；不验收、合main、删分支、改current-work或开始下一子项。
