# W015 小型只读调查与身份

运行位置Linux `/workspace/Layauto`，Python3.12.14，直接从checkout导入，无新安装。
本轮未执行双全量/typing/build/安装/完整wire矩阵；未调用EDA。

- `python -B docs/tasks/W015/evidence/coupling_probe.py`：最终exit0，约2.4秒为命令墙钟，
  不作为benchmark。正常reader/geometry及6个临时输入变体，原stdout/stderr原位保存。
- `coupling_probe.attempt01.py`及`coupling.attempt01.stdout.json/.stderr.txt`：首轮exit1，
  仅探针对缺key的期望代码错误（实际MissingField），无runtime/fixture修复。
- `python -B docs/tasks/W015/evidence/prepare_candidate_input.py`：exit0，生成
  [实际候选manifest](candidate-input/analysis.json)和[完整候选header](candidate-input/local-header.json)。
  这些是候选synthetic输入，**尚无新API执行**。来源原header/raw不改，13项local依赖、
  9项raw hash绑定；不生成观测答案，不读expected/spec/oracle/helper。
  [来源记录](candidate-input/provenance.json)明确新synthetic id和local闭包的变更。
  相对路径基于analysis.json目录；从仓库任意checkout可按同一文件位置重建。

实际文件样张展示新schema而非可给现read_inputs的输入。实施后可把此闭包复制到临时工作区，
补各场景新manifest/header后做T01；所有依赖按实际捕获bytes认证。原GDS、CDL、raw、tech、
limitations沿用已提交synthetic文件；没有生产工具执行身份，也没有伪造hash。

源码事实核对覆盖reader/config/schema、results、semantic/identity/_validation/contracts/input、
geometry_input/geometry/effective/local_connectivity/channel_identity/net_annotation/terminal_relations、
state/layout_store/regions/local_connectivity/annotation、annotation/net_regions、
domain/net_annotation/terminal_relations、derive/channel_identity/net_annotation/body_relations/terminal_relations。
legacy只读cdl_parser/calibre_query两源；架构引用原文及W014/U06一并核对。

`source-identity.json`记录本次起点所有runtime/正式tests/config字节清单与产品main比较，
只证明身份未改，不代原产品测试。review绑定冻结候选commit或明确path快照，不绑定报告自身hash。
