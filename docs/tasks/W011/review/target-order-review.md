# W011 target-only 测试输入构造增量 review

Reviewer：`/root/code_review`，2026-11-09；未修改产品、正式测试或 fixture。此记录只审最终矩阵发现的一个测试 setup 错误及其最小补修，不替代 A8。

原测试版本 `02725e2e90be6b3145be915be699aa64ce998ed7` 给 `change_cdl` 的 before 文本是 source CDL 的参数词序。已验收 fixture 的 target 故意使用不同顺序：`VT=toy W=2n L=4n M=1 NF=1 NFIN=5`。helper 在写文件、重绑或调用 W011 前执行 `assert before in text`；原定向 3.10 输出实际为此处失败，`1 failed in 72.55s`。这仍是必须修复的测试失败；它没有执行到本次 target 变体的产品计算，不能解读成 target 差异的运行失败或矩阵通过。

已审工作区补丁只改该测试的 before/after 两个字符串，保留 target 原词序。它只把 MN0 的 NFIN 5→3、L 4n→6n、W 2n→3n，保留 VT/NF/M、MP0 target 行及 source 文件。期望计数、3 项 target delta、source comparison equal 和完整 comparison 序列断言全部未削弱；runtime/fixture/helper 均无改动。

主 reviewer 独立轻量实际 `read_inputs→W007 normalize` 证明：旧 before 不存在，修正 before 恰好匹配一次；仅 MN0 target 行改变，MP0/source 字节不变；实际 delta 依 canonical axis 顺序为 `channel_length: 4n→6n`、`fin_width: 2n→3n`、`fins_per_finger: 5→3`，恰 3 项。W011 比较次序按未变的 source associations 与几何 FIN 顺序建立，不依赖 target 的参数词序。脚本 [target-order-probe.py](target-order-probe.py) 与 [原输出](target-order-probe.stdout.txt)/[stderr](target-order-probe.stderr.txt) 保留实际命令、Python 3.12.14、执行 1.04s、受审 runtime 与 `8917d38` 相同的核对；没有重跑重型 W011 probe 或全 codec。

具体修复提交身份和正式定向修后结果待追加。旧矩阵/原定向失败应原样保留；修改后重新冻结双完整矩阵，A8 仍 pending。当前已审最小补丁没有新的代码必须项，也没有修改产品语义或放宽 fixture/答案。

## 提交与定向结果核对

执行测试分支提交 `27f885497634d0f2ed50d293e00603309d34c0cd`（parent `02725e2e90be6b3145be915be699aa64ce998ed7`）已经独立核对：仅 `tests/contracts/test_w011_geometry.py` 两行字符串调整，与上述实审补丁一致。正式修后定向原输出为 `1 passed in 136.82s`、exit 0；manifest 的被测文件 SHA-256 与该提交字节相同，start/end UTC、argv/cwd、解释器、137.11s 外层耗时及 1,733,588 KiB child high-water RSS 均保留在执行侧的 `corrected-manifest.json`。原失败输出没有覆盖。

**此最小测试补修 review 通过，新增必须项 0。** 这是对执行者原始定向结果的审计，reviewer 自己实跑的是上文轻量 W007 witness，没有将执行者的 136.82s 冒记为独立重型测试。主分支集成 SHA 和最终双矩阵仍待执行记录绑定，A8 维持 pending。
