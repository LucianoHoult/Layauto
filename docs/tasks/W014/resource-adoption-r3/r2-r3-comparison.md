# W014 R2→R3 valid wire 与实际公开成本

R2 source：`d75b1b03b90e1eb010806a689a828fdcdeb715fdc20eb493a5bfd2219ae7f8a9`；R3 source：`2d46bbdaccd858af936d37427ec8bad11d0bb11074d92cddb901da6197ecf639`。原测量身份和原文件均保留。

三路 valid wire 的 SHA-256 和 bytes 完全相同，完整 W010 wire、compact bytes、输入、解释器/依赖、probe字节也相同。公开W010认证调用仍为build/encode/decode=1/1/2。

| Case | Phase | R2 (s) | R3（含完整retained检查）(s) | 差值(s) |
| --- | --- | ---: | ---: | ---: |
| normal-direct | build | 14.250 | 13.656 | -0.594 |
| normal-direct | encode | 15.994 | 16.067 | +0.074 |
| normal-direct | decode | 28.975 | 28.592 | -0.382 |
| normal-readback | build | 30.231 | 27.079 | -3.152 |
| normal-readback | encode | 33.929 | 32.121 | -1.808 |
| normal-readback | decode | 60.982 | 57.548 | -3.433 |
| extraction-mismatch | build | 13.928 | 14.217 | +0.289 |
| extraction-mismatch | encode | 18.666 | 16.709 | -1.957 |
| extraction-mismatch | decode | 31.829 | 28.580 | -3.249 |

原probe未单独对 `_retained` 计时；这里是包含新完整检查的实际公开调用成本，不把单样本变快归因为检查负成本或稳定性能收益。

R2→R3完整selected源差异只有以下三项，唯一runtime变化是新codec：

- `layauto_v2/normalization/terminal_relations_codec.py`：`a64f2d42cd9431d60a38a057abf956b654e4fc979ef4c9824782a112e13a2bc4` → `08f172f7e80ea56afbaf7a4d19391f9d5d44ba6e2a450adb154c61932933148a`。
- `tests/contracts/test_w014_body_scope.py`：`b10c156acfd655b4b76e3fa8dabd149c72a9b7df7ab7ef6a25efd8558dc2bdb4` → `85b7d5d597c1073c3b064c7e314fb0cb0d6e3ecfcbad1dadc054d3d03e9916c8`。
- `tests/contracts/test_w014_contracts.py`：`34ace98cc4089e316fe7e3f01fbc719ac47edb3b584adb1434cc638b51c66e22` → `98ba63b43643c0c8c6272944b267831a7e1104e770ec177a5660b7c7e48c8eeb`。

本次只读取原报告、日志和suite作轻量证据核对；没有重跑任何产品链。
