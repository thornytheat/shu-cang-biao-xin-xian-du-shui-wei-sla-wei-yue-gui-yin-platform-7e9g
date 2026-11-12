"""误违约对账决策（补采迟到重算）单测。

场景：就绪事件补采迟到，先按旧延迟判了违约；实际就绪时间补录后重跑检测，
台账里已不违约的记录按处置态分流——
  未处置(open)   → delete（从待办消失，无痕迹）
  已认领/已复盘  → void（保留处置痕迹，标作废）
  已作废         → keep（幂等，不重复作废）
  重新成为候选    → revive（复活）/ keep（正常更新）
"""
from __future__ import annotations

import pytest

from src.services.breach_core import (
    RECONCILE_DELETE,
    RECONCILE_KEEP,
    RECONCILE_REVIVE,
    RECONCILE_VOID,
    reconcile_action,
)


# ---------- 误违约（不再是候选） ----------


def test_open_false_breach_is_deleted():
    """未处置的误违约从待办消失。"""
    assert (
        reconcile_action(is_candidate=False, handling_status="open", is_voided=False)
        == RECONCILE_DELETE
    )


@pytest.mark.parametrize("status", ["claimed", "resolved"])
def test_handled_false_breach_is_voided(status):
    """已认领 / 已复盘的误违约保留处置痕迹并标作废。"""
    assert (
        reconcile_action(is_candidate=False, handling_status=status, is_voided=False)
        == RECONCILE_VOID
    )


@pytest.mark.parametrize("status", ["open", "claimed", "resolved"])
def test_already_voided_stays_voided(status):
    """重复运行不重复作废：已作废记录保持原痕迹（幂等）。"""
    assert (
        reconcile_action(is_candidate=False, handling_status=status, is_voided=True)
        == RECONCILE_KEEP
    )


# ---------- 仍是候选 ----------


def test_voided_candidate_is_revived():
    """作废后重新成为候选（补录值又被修正回迟到）→ 复活。"""
    assert (
        reconcile_action(is_candidate=True, handling_status="claimed", is_voided=True)
        == RECONCILE_REVIVE
    )


@pytest.mark.parametrize("status", ["open", "claimed", "resolved"])
def test_active_candidate_is_kept(status):
    """有效候选正常 upsert（重复检测不新增、不重复升级）。"""
    assert (
        reconcile_action(is_candidate=True, handling_status=status, is_voided=False)
        == RECONCILE_KEEP
    )


# ---------- 不变量 ----------


def test_reconcile_is_deterministic_and_total():
    """同一输入永远同一决策；所有组合都落在四个动作内。"""
    actions = {RECONCILE_KEEP, RECONCILE_DELETE, RECONCILE_VOID, RECONCILE_REVIVE}
    for is_candidate in (True, False):
        for status in ("open", "claimed", "resolved"):
            for is_voided in (True, False):
                kwargs = {
                    "is_candidate": is_candidate,
                    "handling_status": status,
                    "is_voided": is_voided,
                }
                decision = reconcile_action(**kwargs)
                assert decision in actions
                assert reconcile_action(**kwargs) == decision
