# W014 资源基线采信与比较

这是跨源码身份采信，不是同源六路 suite。原失败、原 source_id 和原输出均保留。

- W013 基线来源：`803b4c4f444f6c32f68966799d25fe8dffad31a914138633b0ed383eaa102bce`，三条独立成功命令。
- W014 本次三路：`2d46bbdaccd858af936d37427ec8bad11d0bb11074d92cddb901da6197ecf639`，原 R2 suite。
- 非 W014 runtime 实际字节相同：106 个文件；原始捕获、W010完整wire、解释器/依赖和probe字节逐项相同。

| Case | W013 build+encode+decode (s) | W014 (s) | 耗时比 | 新增wire bytes | wire比 | W013/W014峰值MiB |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| normal-direct | 54.633 | 58.315 | 1.0674 | 345944 | 1.014973 | 201.84/198.51 |
| normal-readback | 111.496 | 116.748 | 1.0471 | 345944 | 1.005792 | 506.38/481.28 |
| extraction-mismatch | 56.645 | 59.506 | 1.0505 | 344703 | 1.014919 | 196.52/200.20 |

完整 selected source delta：

- `layauto_v2/domain/terminal_relations.py`：modified；`20f1b840091a77b04e39abce82ce2901af5bc68468b6c947cb6cfba2a9219779` → `d7654ce54ab139f4be690d5616393cc503cd2bf1b660930273fece4bc8b09b89`。
- `layauto_v2/normalization/terminal_relations_codec.py`：modified；`bd72e501c7f74383836e1e64c29413b3e6bf08c10e1c8d7fb95a3d61207f7924` → `08f172f7e80ea56afbaf7a4d19391f9d5d44ba6e2a450adb154c61932933148a`。
- `tests/contracts/test_w014_body_scope.py`：modified；`b10c156acfd655b4b76e3fa8dabd149c72a9b7df7ab7ef6a25efd8558dc2bdb4` → `85b7d5d597c1073c3b064c7e314fb0cb0d6e3ecfcbad1dadc054d3d03e9916c8`。
- `tests/contracts/test_w014_contracts.py`：modified；`2f5a6def8be3717b2220f18235709670f056ebe38190fc4612734e2b0e1ede64` → `98ba63b43643c0c8c6272944b267831a7e1104e770ec177a5660b7c7e48c8eeb`。
- `tests/contracts/test_w014_readback_storage.py`：added；`None` → `0e056dbbb763791b55048ac77a87269d96af835ff8115160e076f6300496813f`。
- `tests/unit/test_w014_terminal_values.py`：modified；`9ef8cb52d975a538d29d0393d6d34f6ff612296edb19dbc7094469f9aa06b30d` → `ffb47f62e8614c9f7447e62a8d552e352c64ec9119667cc06789e61f22f30a57`。

双矩阵调度依据：此前 W013 在相同16GiB/4CPU限制下完成双1731全量；本轮三路最高进程峰值为481.28MiB。两份最高样本加2GiB保留量为2.940GiB，相对内存限制余量13.060GiB。

样本峰值不保证全量上界；两个矩阵各自串行测试，build与两个安装smoke必须排在矩阵后。是否采用workers=2由root/reviewer核验后另写clearance。

本次实跑：仅证据读取/字节核对与报告生成。按身份采信：原W013三路reference。未重跑产品链；原W014 early失败不计成功。

补跑触发：旧runtime/输入/依赖/probe改变，原证据缺失/失败，source delta超出W014专有路径，或发现W013 reference受新路径影响。
