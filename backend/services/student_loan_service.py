"""
RealtouchHR - UK Student Loan & Postgraduate Loan Service
Implements 2025-26 deduction rules for Plans 1, 2, 4, 5 and Postgraduate Loan.
"""
from typing import Optional, Dict
from enum import Enum

# 2025-26 Annual thresholds (HMRC figures)
PLAN_THRESHOLDS = {
    "plan_1": {"annual": 24990, "rate": 0.09, "name": "Plan 1"},
    "plan_2": {"annual": 27295, "rate": 0.09, "name": "Plan 2"},
    "plan_4": {"annual": 31395, "rate": 0.09, "name": "Plan 4 (Scotland)"},
    "plan_5": {"annual": 25000, "rate": 0.09, "name": "Plan 5"},
    "postgrad": {"annual": 21000, "rate": 0.06, "name": "Postgraduate"},
}


class LoanPlan(str, Enum):
    NONE = "none"
    PLAN_1 = "plan_1"
    PLAN_2 = "plan_2"
    PLAN_4 = "plan_4"
    PLAN_5 = "plan_5"
    POSTGRAD = "postgrad"


def calculate_loan_deduction(
    annual_earnings: float,
    plan: str,
    pay_frequency: str = "monthly",
    has_postgrad: bool = False,
) -> Dict[str, float]:
    """
    Calculate per-pay-period student loan deduction.

    pay_frequency: weekly | monthly | annual
    Returns: {plan_deduction, postgrad_deduction, total_deduction, threshold_used}
    """
    periods = {"weekly": 52, "monthly": 12, "annual": 1}.get(pay_frequency, 12)

    plan_deduction = 0.0
    plan_threshold = 0.0
    if plan and plan != "none" and plan in PLAN_THRESHOLDS:
        cfg = PLAN_THRESHOLDS[plan]
        period_threshold = cfg["annual"] / periods
        period_earnings = annual_earnings / periods
        if period_earnings > period_threshold:
            plan_deduction = round((period_earnings - period_threshold) * cfg["rate"], 2)
        plan_threshold = round(period_threshold, 2)

    pg_deduction = 0.0
    if has_postgrad:
        cfg = PLAN_THRESHOLDS["postgrad"]
        period_threshold = cfg["annual"] / periods
        period_earnings = annual_earnings / periods
        if period_earnings > period_threshold:
            pg_deduction = round((period_earnings - period_threshold) * cfg["rate"], 2)

    return {
        "plan": plan,
        "plan_deduction": plan_deduction,
        "plan_threshold_per_period": plan_threshold,
        "postgrad_deduction": pg_deduction,
        "total_deduction": round(plan_deduction + pg_deduction, 2),
        "pay_frequency": pay_frequency,
    }


def get_plans() -> list:
    """Return all loan plans for UI dropdowns"""
    plans = [{"id": "none", "name": "No loan", "annual_threshold": None, "rate": None}]
    for plan_id, cfg in PLAN_THRESHOLDS.items():
        plans.append({
            "id": plan_id,
            "name": cfg["name"],
            "annual_threshold": cfg["annual"],
            "rate": cfg["rate"],
        })
    return plans
