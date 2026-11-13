#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""技能合规校验器（S1/S4）。

依据 GOVERNANCE.md §4.2 / §4.4 / §8.2 校验 skills/**/SKILL.md：
  1. front-matter 必填字段齐全（name/priority/domain/scoring_unit/trigger/input/output）
  2. priority ∈ {P0,P1,P2}
  3. domain ∈ {D1..D11}
  4. scoring_unit ∈ 允许集合
  5. name 与目录名一致
  6. 正文包含四要素小节：执行体 / 质量门 / 校验标准 / 失败与豁免
  7. name 未登记于 GOVERNANCE.md §4.4 时告警（新增技能须同 PR 更新 §4.4）

退出码：0 = 通过；1 = 存在错误；2 = 用法错误。
仅依赖 Python 标准库，本地与 CI 判定一致。
"""
import argparse
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_SKILLS_DIR = os.path.join(ROOT, "skills")
DEFAULT_GOVERNANCE = os.path.join(ROOT, "docs", "governance", "GOVERNANCE.md")

PRIORITIES = {"P0", "P1", "P2"}
DOMAINS = {"D%d" % i for i in range(1, 12)}
SCORING_UNITS = {"AI向量机", "传统向量机", "独立机", "域控", "通用"}
REQUIRED_FIELDS = ["name", "priority", "domain", "scoring_unit", "trigger", "input", "output"]
# §4.2 五要素中，元信息 = front-matter；正文须含其余四小节
SECTION_ALIASES = {
    "执行体": ["执行体", "执行", "execution"],
    "质量门": ["质量门", "quality gate"],
    "校验标准": ["校验标准", "验收标准", "acceptance criteria"],
    "失败与豁免": ["失败与豁免", "失败豁免", "failure", "exemption"],
}


def read(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def display_path(path, base):
    """跨盘符安全地取相对路径；不同挂载点时回退为绝对路径。"""
    try:
        return os.path.relpath(path, base)
    except ValueError:
        return os.path.abspath(path)


def parse_frontmatter(text):
    """解析以 --- 起始的 front-matter 为 {key: value}；返回 (meta, body)。"""
    if not text.startswith("---"):
        return {}, text
    m = re.match(r"^---[ \t]*\n(.*?)\n---[ \t]*\n?(.*)$", text, re.S)
    if not m:
        return {}, text
    meta, body = m.group(1), m.group(2)
    meta_dict = {}
    for line in meta.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        meta_dict[k.strip()] = v.strip().strip('"').strip("'")
    return meta_dict, body


def section_present(body, aliases):
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("#"):
            low = s.lower()
            if any(a in low for a in aliases):
                return True
    return False


def listed_in_governance(name, governance_path):
    if not os.path.isfile(governance_path):
        return True  # 无法核对时不误伤
    text = read(governance_path)
    return bool(re.search(r"`%s`" % re.escape(name), text))


def iter_skills(skills_dir):
    if not os.path.isdir(skills_dir):
        return []
    out = []
    for entry in sorted(os.listdir(skills_dir)):
        p = os.path.join(skills_dir, entry)
        sk = os.path.join(p, "SKILL.md")
        if os.path.isfile(sk):
            out.append((entry, sk))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="技能合规校验器")
    ap.add_argument("--skills-dir", default=DEFAULT_SKILLS_DIR)
    ap.add_argument("--governance", default=DEFAULT_GOVERNANCE)
    args = ap.parse_args(argv)

    skills = iter_skills(args.skills_dir)
    if not skills:
        print("WARN: 未发现技能目录（%s）；当前仓库尚无技能，视为通过。" % args.skills_dir)
        return 0

    errors, warnings = [], []
    for dirname, path in skills:
        text = read(path)
        meta, body = parse_frontmatter(text)
        label = "%s (%s)" % (dirname, display_path(path, ROOT))

        if not text.startswith("---"):
            errors.append("%s: 缺少 front-matter（须以 --- 起始）" % label)
        missing = [f for f in REQUIRED_FIELDS if f not in meta]
        if missing:
            errors.append("%s: front-matter 缺失字段 %s" % (label, missing))
        if meta.get("priority", "") not in PRIORITIES:
            errors.append("%s: priority 非法（%r），须为 P0/P1/P2" % (label, meta.get("priority")))
        for d in re.split(r"[,\s]+", str(meta.get("domain", ""))):
            d = d.strip()
            if d and d.upper() not in DOMAINS:
                errors.append("%s: domain 非法（%r），须为 D1..D11" % (label, d))
        if meta.get("scoring_unit", "") not in SCORING_UNITS:
            errors.append("%s: scoring_unit 非法（%r），须为 %s" % (label, meta.get("scoring_unit"), sorted(SCORING_UNITS)))
        name = meta.get("name", "")
        if name != dirname:
            errors.append("%s: name(%r) 与目录名(%r) 不一致" % (label, name, dirname))
        for section, aliases in SECTION_ALIASES.items():
            if not section_present(body, aliases):
                errors.append("%s: 正文缺少「%s」小节" % (label, section))
        if name and not listed_in_governance(name, args.governance):
            warnings.append("%s: name(%r) 未登记于 GOVERNANCE.md §4.4，新增技能须在同 PR 更新 §4.4" % (label, name))

    for w in warnings:
        print("WARN: " + w)
    if errors:
        print("ERROR (%d):" % len(errors))
        for e in errors:
            print("  - " + e)
        print("FAIL：技能合规校验未通过。")
        return 1
    print("PASS：共校验 %d 个技能，全部合规。" % len(skills))
    return 0


if __name__ == "__main__":
    sys.exit(main())
