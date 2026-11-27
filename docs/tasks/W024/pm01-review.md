# W024 PM-01 独立复核

受审基线为 `58698b964bf685a9830ded54490de0e00de709a0`，修复提交为 `c3112971a85fd14645fbda996d1574bdb79d70b4`。对照分别从两个提交的干净工作区运行，使用 Linux x86_64、CPython 3.12.14、PyYAML 6.0.3。[PM 验收项](../W024-stage3-rule-context.md#pm1-receipt)

独立探针用正常样本先发布第 0 版，再让第二个 run 复用同一 head。两个 checkpoint 各自通过仓库校验，且原始字节的 SHA-256 不同。删除临时输入后，依次比较完整仓库、仅替换建版 checkpoint 字节、仅替换复用 checkpoint 字节三种情况。替换仅限于原引用键下存储的字节，内容取自另一个 run 的完整 checkpoint。对照在打开上下文的边界捕获错误，只有打开成功才执行 T07。[独立探针](pm01_review_probe.py)

在基线，建版 run 能拒绝损坏的原记录，复用 run 读了自身 checkpoint 一次，读取原版 checkpoint 零次。即使仓库直接读取原引用已报 `RefConflict`，复用 run 仍给出 6 对、最小 5 nm、通过。独立探针退出码为 1。

入口核对 snapshot、建版事件和目标的原 checkpoint 引用一致，再校验本次封存 checkpoint 及其输入绑定。引用有别时还须用仓库的 `read` 解引用原版。仓库会检查内容地址、记录种类和运行身份，原异常信息包含完整引用。规则工艺读取仍沿本次工具记录进行。[修复差异](https://github.com/LucianoHoult/Layauto/commit/c3112971a85fd14645fbda996d1574bdb79d70b4)

在修复或交付提交的仓库根目录运行以下命令。要复现旧版，可在基线工作区使用同一条命令，并把脚本路径替换为本次交付中该探针的绝对路径。

```sh
PYTHONPATH=.:tests/contracts python -B docs/tasks/W024/pm01_review_probe.py
```

| 修复版仓库内容 | 建版运行 | 复用运行 |
| --- | --- | --- |
| 两条 checkpoint 完整 | 本次与原版共用一个引用，读取一次，5 nm 通过 | 两个不同引用各读一次，5 nm 通过 |
| 原版槽下写入复用记录字节 | RefConflict，给出原版引用 | RefConflict，给出同一原版引用 |
| 复用槽下写入原版记录字节 | 原版读取一次，5 nm 通过 | RefConflict，给出复用运行自身的引用 |

本次修复版对照的原版引用为 `checkpoint:creator:1cba858c31911e65ce708f6f111d565aad3214ddf10c42537b8299021c0454be`，复用引用为 `checkpoint:reuse:efe4ced567fad549ad0e3c824431ac54b8e5ae1ad0972f3d27445a19215ec882`。每次损坏均先由仓库直接读取确认摘要冲突。每次查询前后 root 指针、仓库观测、head 与 attempt 一致，两次运行均保持 sealed_open。完整数据的两个报告各保留本次 checkpoint、工具引用及同一原快照。

**独立代码复核通过，可交 PM 重新验收。** 上表为原样运行该探针的实测结果，修复版退出码为 0。探针 SHA-256 为 `9ef1a585c30da9cb997fd516a485f4b39d865e2c0e90e539522637e8331deb18`。两提交间的产品差异仅在 Stage 3 入口。存储 codec、仓库读校验、测距和输入样本沿用既有受测身份。相应实现或证据身份变化时复跑受影响的合同和该对照。
