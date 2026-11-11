# W012 A1 独立执行 session prompt

```text
按 Layauto 项目规范，以独立执行 session 完成 W012 的兼容优化 A1：降低现有 hex 校验的瞬时内存成本。
从 codex/w012-compatible-hex-validation 的PM准备提交恢复，起点调查接收提交9b573c99d5f4021636f498292f42b53540bff1a1，runtime仍等同已验收main0a3326aa363477724465886cd05874d0997fba3e；先核远端完整SHA、工作区、AGENTS/协作/环境规则及 W012 最新 PM 决定/A1要求，读取 P1/P2 cost-analysis、implementation-proposal、independent-review 和 PM 接收证据。
本轮仅处理 domain/codec.py::_decode 中已定位的重复分组 hex matcher 及直接必要的测试/工具/记录；可以选择等价的不重复分组校验或有界扫描，具体算法先形成最小方案并由未参与设计者独立review。保留空bytes、小写ASCII且偶数长度的原接受语言，以及 malformed/canonical 拒绝与原异常合同。
schema /1、canonical bytes、wire大小/所有hash与content refs、公开函数、constructor/认证次数及边界不变。不要实现新 /2、通用writer/reader重构、memo/cache，或减少完整捕获/跳过认证。P1/P2的20%/50%是完整兼容包的目标建议，不是本最小阶段获批的硬门或收益承诺。
开发先跑新增及受影响范围，核hex完整合法/非法边界、空/奇数/大小写/空白/Unicode与JSON规范性、原异常object/cause/context/suppression、嵌套公开codec及二次故障；不要重写原finding或用删测试达标。最终冻结交付仍双解释器全量、strict typing、构建与双干净安装源码外组合smoke。
无插桩同条件比较优化前后 normal direct、normal readback、原 extraction_mismatch 的完整公开Result构造/encode/decode。runtime导入位置可分离，输入URI、RunRequest/cache、对象保留和GC顺序必须相同；先按原清单重建/核对固定mismatch输入，不能把历史不同环境单次样本冒充本机before。
开发可先各一组fresh对照筛选；最终性能比较两侧各3个fresh串行样本，复用本轮已满足相同身份/环境的测量，保存原次/失败与中位/各次峰值。完整wire/hash逐字节等价、实算正常5/7及实际4对source5、原图/T05/body/来源和readback unsealed/checkpoint/无terminal边界保持。解释matcher窗口峰值是否消除、整进程峰值和各路径耗时改善/退化；新旧profile只作归因，不与无插桩基准混比。不以microbenchmark、减少测试数或新短wire代替完整路径结果。
独立代码/正确性/性能review，修正复核所有必须项并保留原证据；若仍有不可解释成本或需超出A1，停在具体问题交PM，不自行扩大到writer/memo或新格式。
用既有项目noreply身份提交推送原A1分支并核远端完整SHA，交PM；不自行验收/合main/删分支/改current-work或启动下一子项。新wire的公开范围、默认兼容、digest/ref和历史迁移仍另行给用户具体决定材料。
```
