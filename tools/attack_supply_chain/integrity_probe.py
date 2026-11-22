#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""完整性校验探测 → import 劫持降级判定（Ch11 §11.4 · sc-05b）。

零 PyRIT、零 I/O 叶子辅助。覆盖课件 sales_calc.py 被 hash 校验挡住后改放恶意
pandas.py 的手法（L912/L914/L981-1005/L1213）。三态判定不臆断；清理字段引用
共享变更登记契约（契约#3），不另立平行清单（C1）。
"""
from typing import Dict, List


def probe_integrity(baseline_ts: str, observed_ts: str,
                    output_stalled: bool, evidence_available: bool = True) -> Dict[str, str]:
    """以「改脚本后时间戳/输出停更」为观测点判定是否存在完整性校验（三态）。"""
    if not evidence_available or not baseline_ts or not observed_ts:
        return {"verdict": "UNDETERMINED", "reason": "缺时间戳观测，不臆断校验存在"}
    if output_stalled and observed_ts == baseline_ts:
        return {"verdict": "有校验",
                "reason": "改脚本后时间戳停更且输出停滞 → 存在 hash/完整性校验（Ch11 L914）"}
    if not output_stalled and observed_ts != baseline_ts:
        return {"verdict": "无校验", "reason": "时间戳继续更新、输出未停滞 → 未见完整性校验"}
    return {"verdict": "UNDETERMINED", "reason": "观测不一致，须实网复核"}


def import_hijack_plan(module_name: str = "pandas", backed_up: bool = False) -> Dict[str, object]:
    """有校验时的降级方案：不改原脚本→同目录放同名依赖模块→劫持 import（含备份前置）。"""
    # 前置：调用方须先经 probe_integrity 判定为「有校验」再调用本方案。
    return {
        "precondition": "probe_integrity == 有校验",
        "steps": [
            "备份原脚本与目标文件（Ch11 L914）",
            "不修改原脚本；在其同目录放同名依赖模块 %s.py（Ch11 L981-1005）" % module_name,
            "劫持 import 触发载荷；守卫条件与来源标注齐全",
        ],
        "backup_done": backed_up,
        "cleanup_ref": "docs/contracts/collect_evidence.contract.md#3（cleanup_state 字段，C1）",
    }


def cleanup_steps(module_name: str = "pandas", recovery_verified: bool = False) -> Dict[str, object]:
    """清理三步：删恶意模块→杀 reverse shell 进程→验证自动化恢复（未验证记 pending）。"""
    return {
        "steps": [
            "删除恶意 %s.py 模块（Ch11 L1213）" % module_name,
            "杀 reverse shell 进程（非守护线程阻碍计划任务恢复）",
            "验证销售自动化恢复（须实测，不假称）",
        ],
        "cleanup_state": "done" if recovery_verified else "pending",
    }
