#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""契约漂移防线夹具（S2 / S6）。

覆盖三层：
  1. 下游解析契约定点（M6）：golden 片段经 report_exam.index.parse_fragment 解析，
     断言 step_id / 目标 / 命令 / 输出 / flag / 截图逐字提取正确——共享工具改动任一片段
     节标题即令本测试变红。
  2. 契约清单完整性（M1）：docs/contracts/collect_evidence.contract.md 结构齐全、
     CHANGELOG 已回填 F3 变更 commit。
  3. 消费者依赖断言（M4）：docs/contracts/consumers.md 中每个消费者的依赖元素都在
     契约清单中逐字出现（经 scripts/check_contract_consumers.py）。

仅标准库（unittest + subprocess）。运行：python -m unittest discover -s tests
"""
import os
import subprocess
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

CONTRACT = os.path.join(ROOT, "docs", "contracts", "collect_evidence.contract.md")
CONSUMERS = os.path.join(ROOT, "docs", "contracts", "consumers.md")


def _load_checkout_lock():
    """按路径加载 checkout_lock 模块（scripts/ 无 __init__.py）。"""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "checkout_lock", os.path.join(ROOT, "scripts", "checkout_lock.py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(script, *args):
    return subprocess.run(
        [sys.executable, os.path.join(ROOT, "scripts", script)] + list(args),
        cwd=ROOT, capture_output=True, text=True,
    )


GOLDEN_FRAGMENT = """### 步骤 recon-01：发现资产

> **目标**：`10.0.0.5`　|　**时间戳**：`2026-11-15T00:00:00+08:00`　|　**证据片段**（collect_evidence.py）

#### 确切命令

```bash
nmap -sV -p 22 10.0.0.5
```

#### 关键输出

```text
22/tcp open ssh OpenSSH 9.2
```

#### 截图（访问证明）

![recon-01 截图](evidence/recon-ai-real/recon-01.png)

#### flag 取证（双通道一致）

```text
FLAG{recon-ok}
```

| 通道 | 值 |
|---|---|
| 控制面板提交值 | `FLAG{recon-ok}` |
| 截图/正文中的值 | `FLAG{recon-ok}` |
| 一致性 | **一致** |

#### 证据校验（五件套 / 三件套）

| 证据项 | 必需 | 状态 |
|---|---|---|
| 截图 | 是 | 已提供 |

**三件套齐全**：是。
"""


class ParseFragmentGoldenTests(unittest.TestCase):
    def test_golden_fragment_parses_correctly(self):
        from report_exam.index import parse_fragment
        frag = parse_fragment(GOLDEN_FRAGMENT, source_path="recon-01.md")
        self.assertEqual(frag.step_id, "recon-01")
        self.assertEqual(frag.title, "发现资产")
        self.assertEqual(frag.target, "10.0.0.5")
        self.assertIn("nmap -sV -p 22", frag.command)
        self.assertIn("22/tcp open ssh", frag.output)
        self.assertEqual(frag.flag, "FLAG{recon-ok}")
        self.assertEqual(frag.screenshot, "evidence/recon-ai-real/recon-01.png")


class ContractManifestTests(unittest.TestCase):
    def test_manifest_wellformed(self):
        r = _run("check_contract_manifest.py", "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_manifest_backfills_f3_change(self):
        with open(CONTRACT, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("e9f8bdd", text, "契约清单 CHANGELOG 未回填 F3 变更 commit")
        self.assertIn("shot_status", text, "契约清单未登记 shot_status 三态字段")


class ConsumerRegistryTests(unittest.TestCase):
    def test_consumers_deps_within_manifest(self):
        r = _run("check_contract_consumers.py", "--check")
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_registry_lists_report_exam_consumer(self):
        with open(CONSUMERS, encoding="utf-8") as f:
            text = f.read()
        self.assertIn("report-exam", text, "登记表缺 report-exam 消费者")


class CheckoutLockContractParsingTests(unittest.TestCase):
    def test_parse_change_commits(self):
        mod = _load_checkout_lock()
        sample = (
            "- `v3`（2026-11-15）commit:`e9f8bdd` PR:#250 破坏性:是 变更:...\n"
            "- `v2`（历史）变更:...\n"
        )
        self.assertEqual(mod._parse_change_commits(sample), [("e9f8bdd", "250")])

    def test_parse_change_commits_empty(self):
        mod = _load_checkout_lock()
        self.assertEqual(mod._parse_change_commits("无 commit 登记"), [])


if __name__ == "__main__":
    unittest.main()
