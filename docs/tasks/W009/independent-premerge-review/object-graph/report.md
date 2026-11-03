# W009 CR-02 原对象图专项复核

受审版本：`88a7ae9d0330b7c7fddda0b07366c7a96552b65e`；产品代码与 `5b1d9b5196a7c5181822c4dd0f1bd2f678475116` 相同。比较了 main `4df07e68b05df4c57a8b8d44bc41e7e073938d3a` 到 HEAD 的产品路径，以及准备提交 `4975e565a33d9594782645b6ad0f944b78ee6ae8` 到产品提交的实现变化。本专项未参与原方案/实现，也未修改产品或正式测试。

结论：**本专项未发现新的必须修正项，CR-02 关闭仍有依据。** 没有仅用编码相等作为不可变性依据。

审查了 `domain/regions.py:23` 的原对象图遍历、`:83` 的先复制后校验、`:99` 的旧 unit ref kind 补充守卫，`state/regions.py::_records` 的完整 base 检查，以及 `normalization/effective.py::_require_input` 和 `EffectiveGeometryResult.__post_init__` 对完整旧 receipt、completed、issues 的检查。检查使用 `cls is allowed`，不受自定义 metaclass 的类型相等运算欺骗；payload 只允许 Value 代数；原生 Fraction 的分子/分母也必须是原生 int。旧 source/parser/schema 字段与未消费 owner 字段仍被遍历。

单独中立 constructor 也已核对：旧 `GeometryRecordId.sha256` 由 `domain/geometry.py:66` 要求 exact str；`Rect` 四坐标由 `:22`/`:109` 要求 exact int；旧 `GeometryRef` 的 sha 已严格，而 kind 的历史宽松比较在新增 `_unit` 接缝补成 exact str。`RegionRef` 自身 kind/sha 均严格。因此正常 constructor 构造的旧 ref/id/rect 不能把字符串/整数子类别名带入单独 `ExactRegion` 或 `RegionPiece`，无需等到外层 aggregate 才发现。没有把需要绕过 frozen dataclass 的 `object.__setattr__` 或直接篡改私有存储当正常公开 constructor 入口。

本次实际运行：

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=/workspace/work/w009-review \
  /workspace/.venvs/layauto/bin/python -B \
  docs/tasks/W009/independent-premerge-review/object-graph/probe.py \
  > docs/tasks/W009/independent-premerge-review/object-graph/result.json \
  2> docs/tasks/W009/independent-premerge-review/object-graph/stderr.txt
```

退出 0；stderr 为空；Python 3.12.14。[脚本](probe.py) 与 [结果](result.json) 绑定四个当前产品文件的 SHA-256，并包含：

- 七类公开值各自通过公有 constructor 重建和 wire decode；独立遍历其真实保留图。遍历读取 FrozenMap 的实际 `_entries`，检查 backing/pair 均为原生 tuple，检查每个 dataclass 为冻结类、每个原子为 native 类型及 Fraction 内部整数；不调用产品 `validate_closed_graph` 作判据。正常完整结果有 5,488 个不同的非原子对象被检查。
- 31 个独立反例全部明确抛出 ValueError。其中新 literal 的十条接缝使用一旦执行相等比较便失败的 TrapText；原生集合接缝及 error/issues 使用一旦迭代便失败的 tuple/list 子类，证明拒绝先于外来方法执行。
- 自定义 `__class__` 的可变 SourceRef impersonator 能通过旧 EvidenceRecord 的 `isinstance` constructor；新增 binding、state builder、completed/result 均拒绝其真实类型。owner/source URI 与 error/issue/source URI 的原始字符串子类别名同样拒绝。
- 七个原生 list 接缝实际完成复制，调用者随后清空原 list 后结果仍相等，且真实保留图仍满足独立遍历判据。
- 临时修改并重绑真实捕获的 physical owner，获得实际 error 结果；其 constructor/decode 原对象图及 issues 接缝也检查。只用既有 helper 进行临时 fixture 复制/捕获重绑，没有用 helper 或产品算法提供不可变性/拒绝判据。

本专项结合代码检查覆盖原 CR-02 的 literal、旧 receipt/base、owner/completed/issues、容器多次迭代、类型身份与 Fraction 原子根因；新的执行反例扩展为有副作用的拒绝顺序与 `__class__` impersonation。原 metaclass/Fraction 具体回归由主 reviewer 本次完整回归覆盖，不能把本专项图遍历另称为重新执行了所有历史 probe。仅在当前 Python 3.12 环境运行本脚本；不构成全 Python 对象空间或恶意并发/运行时 monkeypatch 的证明。本专项不承担几何数学、全回归、typing、包安装或生产性能结论。
