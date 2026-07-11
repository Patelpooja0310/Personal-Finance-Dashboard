# =============================================================================
# dashboard.py — Main Financial Dashboard
# Features: KPI Cards, Income vs Expense, Budget Status, Top Expenses
# =============================================================================

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, date
from typing import Optional

from database import (
    get_transactions, get_monthly_summary, get_category_spend,
    get_budgets, get_categories,
)
from auth import get_current_user_id
from visualization import (
    pie_chart_by_category, bar_chart_income_expense,
    line_chart_daily_trend, bar_chart_growth_rate,
    line_chart_monthly_trend, waterfall_chart,
)


# =============================================================================
# CURRENCY FORMATTER
# =============================================================================

def fmt(amount: float, currency: str = "INR") -> str:
    symbol = {"INR": "₹", "USD": "$", "EUR": "€", "GBP": "£"}.get(currency, "₹")
    return f"{symbol}{amount:,.0f}"


# =============================================================================
# KPI METRIC CARDS
# =============================================================================

def _render_kpi_cards(total_income: float, total_expense: float,
                      net_savings: float, savings_pct: float,
                      avg_daily: float, currency: str) -> None:
    """Render the top KPI metric row."""
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric("💵 Total Income",    fmt(total_income, currency),
                  help="Sum of all income transactions in the selected period")
    with c2:
        st.metric("💸 Total Expenses",  fmt(total_expense, currency),
                  help="Sum of all expense transactions")
    with c3:
        delta_label = f"{savings_pct:.1f}% of income"
        st.metric("🏦 Net Savings",     fmt(net_savings, currency), delta_label,
                  delta_color="normal" if net_savings >= 0 else "inverse")
    with c4:
        st.metric("📅 Avg Daily Spend", fmt(avg_daily, currency),
                  help="Total expenses ÷ days in period")


def _render_advanced_kpis(monthly: pd.DataFrame, currency: str) -> None:
    """Render secondary analytics KPI row."""
    if monthly.empty:
        return

    best_month  = monthly.loc[monthly["expense"].idxmin(),  "month"] if not monthly.empty else "—"
    worst_month = monthly.loc[monthly["expense"].idxmax(),  "month"] if not monthly.empty else "—"
    avg_monthly = monthly["expense"].mean()
    profit_pct  = (monthly["savings"].sum() / monthly["income"].sum() * 100
                   if monthly["income"].sum() > 0 else 0)

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        st.metric("📊 Avg Monthly Exp",     fmt(avg_monthly, currency))
    with c6:
        st.metric("📈 Profit %",            f"{profit_pct:.1f}%",
                  help="(Total Income − Total Expense) / Total Income")
    with c7:
        st.metric("✅ Best Month",          best_month,
                  help="Month with lowest expenses")
    with c8:
        st.metric("⚠️ Worst Month",         worst_month,
                  help="Month with highest expenses")


# =============================================================================
# BUDGET STATUS PANEL
# =============================================================================

def _render_budget_status(user_id: int, period_month: str,
                           currency: str) -> None:
    """
    Render colour-coded budget progress bars for the selected month.
    """
    st.subheader("🎯 Budget Status")
    budgets_df = get_budgets(user_id, period_month)

    if budgets_df.empty:
        st.info("No budgets set for this month. Visit the Budget page to add limits.")
        return

    for _, row in budgets_df.iterrows():
        spent  = float(row["spent"])
        limit  = float(row["budget_amount"])
        pct    = min(spent / limit * 100, 100) if limit > 0 else 0
        over   = spent > limit
        color  = "#F05C5C" if over else ("#F5A623" if pct > 75 else "#22C58B")
        status = "⚠️ Over budget!" if over else ("🟡 Near limit" if pct > 75 else "✅ On track")

        st.markdown(f"""
        <div style="margin-bottom:16px;">
          <div style="display:flex;justify-content:space-between;
                      font-size:13px;margin-bottom:6px;">
            <span style="font-weight:600;">{row['icon']} {row['category']} — {status}</span>
            <span style="color:{color};font-weight:600;">
              {fmt(spent, currency)} / {fmt(limit, currency)}
            </span>
          </div>
          <div style="background:#E8EBF0;border-radius:8px;
                      height:10px;overflow:hidden;">
            <div style="width:{pct:.0f}%;background:{color};
                        height:100%;border-radius:8px;
                        transition:width 0.4s ease;"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)


# =============================================================================
# TOP EXPENSES TABLE
# =============================================================================

def _render_top_expenses(expense_df: pd.DataFrame, currency: str,
                          n: int = 5) -> None:
    """Table of top N largest individual expenses."""
    st.subheader(f"🔴 Top {n} Expenses")
    if expense_df.empty:
        st.info("No expense data for this period.")
        return

    top = (
        expense_df
        .nlargest(n, "amount")[["date", "description", "category", "amount"]]
        .copy()
    )
    top["date"]   = pd.to_datetime(top["date"]).dt.strftime("%d %b")
    top["amount"] = top["amount"].apply(lambda x: fmt(abs(x), currency))
    st.dataframe(top.reset_index(drop=True), use_container_width=True,
                 hide_index=True)


# =============================================================================
# CATEGORY BREAKDOWN TABLE
# =============================================================================

def _render_category_breakdown(cat_spend: pd.DataFrame,
                                currency: str) -> None:
    """Summary table of spending by category."""
    st.subheader("📋 Category Breakdown")
    if cat_spend.empty:
        st.info("No category data.")
        return

    df = cat_spend.copy()
    total = df["total_spent"].sum()
    df["% of Total"] = (df["total_spent"] / total * 100).apply(lambda x: f"{x:.1f}%")
    df["Total Spent"] = df["total_spent"].apply(lambda x: fmt(x, currency))
    df.rename(columns={"category": "Category", "txn_count": "Transactions"}, inplace=True)
    st.dataframe(
        df[["Category", "Total Spent", "Transactions", "% of Total"]]
        .reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )


# =============================================================================
# MAIN DASHBOARD PAGE
# =============================================================================

def show_dashboard_page() -> None:
    """Render the complete financial dashboard for the logged-in user."""
    user_id  = get_current_user_id()
    currency = st.session_state.get("currency", "INR")
    username = st.session_state.get("full_name", "User")

    if not user_id:
        st.error("Please log in first.")
        return

    # ── Sidebar filters ───────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("### 🔍 Filters")
        all_txns = get_transactions(user_id)

        if all_txns.empty:
            st.info("No transactions yet.")
            st.title("💰 Personal Finance Dashboard")
            st.info("Add transactions to see your dashboard.")
            return

        min_date = all_txns["date"].min().date()
        max_date = all_txns["date"].max().date()

        date_range = st.date_input(
            "Date Range",
            value=(min_date, max_date),
            min_value=min_date, max_value=max_date,
            key="dash_date_range",
        )
        start_date = date_range[0] if len(date_range) == 2 else min_date
        end_date   = date_range[1] if len(date_range) == 2 else max_date
        period_month = end_date.strftime("%Y-%m")

    # ── Fetch filtered data ───────────────────────────────────────────────────
    df = get_transactions(
        user_id,
        start_date=str(start_date),
        end_date=str(end_date),
    )
    cat_spend   = get_category_spend(user_id, str(start_date), str(end_date))
    monthly_sum = get_monthly_summary(user_id)

    income_df  = df[df["amount"] > 0]
    expense_df = df[df["amount"] < 0].copy()
    expense_df["amount"] = expense_df["amount"].abs()

    total_income  = income_df["amount"].sum()
    total_expense = expense_df["amount"].sum()
    net_savings   = total_income - total_expense
    savings_pct   = (net_savings / total_income * 100) if total_income > 0 else 0
    days_in_range = max((end_date - start_date).days, 1)
    avg_daily     = total_expense / days_in_range

    # ── Header ────────────────────────────────────────────────────────────────
    st.title("💰 Personal Finance Dashboard")
    st.caption(
        f"Welcome back, **{username}** · "
        f"Period: {start_date.strftime('%d %b %Y')} → {end_date.strftime('%d %b %Y')} · "
        f"**{len(df)}** transactions"
    )
    st.markdown("---")

    # ── KPI Row 1 ─────────────────────────────────────────────────────────────
    _render_kpi_cards(total_income, total_expense, net_savings,
                      savings_pct, avg_daily, currency)
    st.markdown("")
    _render_advanced_kpis(
        monthly_sum.rename(columns={"total_expense": "expense",
                                     "total_income": "income"}),
        currency,
    )
    st.markdown("---")

    # ── Row 2: Pie + Bar ──────────────────────────────────────────────────────
    col_left, col_right = st.columns(2)
    with col_left:
        fig_pie = pie_chart_by_category(cat_spend)
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_right:
        chart_data = monthly_sum.rename(columns={
            "total_expense": "expense", "total_income": "income"
        })
        fig_bar = bar_chart_income_expense(chart_data)
        st.plotly_chart(fig_bar, use_container_width=True)

    st.markdown("---")

    # ── Row 3: Daily Trend + Budget ───────────────────────────────────────────
    col_trend, col_budget = st.columns([3, 2])
    with col_trend:
        fig_trend = line_chart_daily_trend(expense_df)
        st.plotly_chart(fig_trend, use_container_width=True)
    with col_budget:
        _render_budget_status(user_id, period_month, currency)

    st.markdown("---")

    # ── Row 4: Growth Rate + Monthly Trend ────────────────────────────────────
    col_gr, col_mt = st.columns(2)
    with col_gr:
        growth_data = monthly_sum.rename(columns={"total_expense": "expense"})
        fig_growth = bar_chart_growth_rate(growth_data)
        st.plotly_chart(fig_growth, use_container_width=True)
    with col_mt:
        trend_data = monthly_sum.rename(columns={
            "total_expense": "expense", "total_income": "income"
        })
        fig_mt = line_chart_monthly_trend(trend_data)
        st.plotly_chart(fig_mt, use_container_width=True)

    st.markdown("---")

    # ── Row 5: Waterfall ──────────────────────────────────────────────────────
    wf_data = monthly_sum.rename(columns={
        "total_expense": "expense", "total_income": "income"
    })
    fig_wf = waterfall_chart(wf_data)
    st.plotly_chart(fig_wf, use_container_width=True)

    st.markdown("---")

    # ── Row 6: Top Expenses + Category Breakdown ──────────────────────────────
    col_top, col_cat = st.columns([1, 2])
    with col_top:
        _render_top_expenses(expense_df, currency)
    with col_cat:
        _render_category_breakdown(cat_spend, currency)
