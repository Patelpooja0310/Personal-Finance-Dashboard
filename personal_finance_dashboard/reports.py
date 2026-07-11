# =============================================================================
# reports.py — Financial Reports & Downloads
# Features: Monthly Report, Expense Report, Category Report, CSV/TXT Download
# =============================================================================

import io
import streamlit as st
import pandas as pd
from datetime import datetime, date

from database import (
    get_transactions, get_monthly_summary, get_category_spend,
    get_budgets,
)
from auth import get_current_user_id


# =============================================================================
# HELPERS
# =============================================================================

def fmt(amount: float, currency: str = "INR") -> str:
    symbol = {"INR": "₹", "USD": "$", "EUR": "€"}.get(currency, "₹")
    return f"{symbol}{amount:,.2f}"


def _period_range(df: pd.DataFrame) -> tuple[date, date]:
    """Return (min_date, max_date) from a transactions DataFrame."""
    if df.empty:
        today = date.today()
        return today, today
    return df["date"].min().date(), df["date"].max().date()


# =============================================================================
# MONTHLY REPORT SECTION
# =============================================================================

def _build_monthly_report_text(monthly: pd.DataFrame,
                                username: str,
                                currency: str) -> str:
    """Generate a plain-text monthly financial report."""
    lines = [
        "=" * 60,
        "   PERSONAL FINANCE — MONTHLY REPORT",
        f"   Generated : {datetime.now().strftime('%d %B %Y, %H:%M')}",
        f"   User      : {username}",
        "=" * 60,
        "",
    ]
    for _, row in monthly.iterrows():
        savings_pct = (row["savings"] / row["income"] * 100
                       if row["income"] > 0 else 0)
        lines += [
            f"  Month     : {row['month']}",
            f"  Income    : {fmt(row['income'], currency)}",
            f"  Expense   : {fmt(row['expense'], currency)}",
            f"  Savings   : {fmt(row['savings'], currency)}  ({savings_pct:.1f}%)",
            "  " + "-" * 40,
        ]

    total_income  = monthly["income"].sum()
    total_expense = monthly["expense"].sum()
    total_savings = monthly["savings"].sum()
    savings_pct   = total_savings / total_income * 100 if total_income > 0 else 0

    lines += [
        "",
        "SUMMARY",
        "-" * 40,
        f"Total Income   : {fmt(total_income, currency)}",
        f"Total Expenses : {fmt(total_expense, currency)}",
        f"Net Savings    : {fmt(total_savings, currency)} ({savings_pct:.1f}%)",
        "",
        "=" * 60,
    ]
    return "\n".join(lines)


def show_monthly_report() -> None:
    """Monthly income/expense/savings summary with chart and download."""
    user_id  = get_current_user_id()
    currency = st.session_state.get("currency", "INR")
    username = st.session_state.get("full_name", "User")

    monthly = get_monthly_summary(user_id)
    if monthly.empty:
        st.info("No transaction data found.")
        return

    monthly = monthly.rename(columns={
        "total_expense": "expense", "total_income": "income"
    })
    monthly["savings_pct"] = (
        monthly["savings"] / monthly["income"].replace(0, 1) * 100
    ).round(1)

    st.subheader("📅 Monthly Report")

    # Summary table
    display = monthly[["month", "income", "expense", "savings", "savings_pct"]].copy()
    display.columns = ["Month", "Income", "Expense", "Savings", "Savings %"]
    for col in ["Income", "Expense", "Savings"]:
        display[col] = display[col].apply(lambda x: fmt(x, currency))
    display["Savings %"] = display["Savings %"].apply(lambda x: f"{x:.1f}%")
    st.dataframe(display.reset_index(drop=True), use_container_width=True, hide_index=True)

    # Totals
    t_income  = monthly["income"].sum()
    t_expense = monthly["expense"].sum()
    t_savings = monthly["savings"].sum()
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Income",   fmt(t_income,  currency))
    c2.metric("Total Expense",  fmt(t_expense, currency))
    c3.metric("Net Savings",    fmt(t_savings, currency),
              f"{t_savings/t_income*100:.1f}%" if t_income > 0 else "—")

    # Downloads
    st.markdown("##### Downloads")
    dc1, dc2 = st.columns(2)
    with dc1:
        buf = io.StringIO()
        monthly.to_csv(buf, index=False)
        st.download_button(
            "⬇️ Download CSV",
            data=buf.getvalue(),
            file_name=f"monthly_report_{datetime.now().strftime('%Y%m')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with dc2:
        report_txt = _build_monthly_report_text(monthly, username, currency)
        st.download_button(
            "⬇️ Download TXT",
            data=report_txt,
            file_name=f"monthly_report_{datetime.now().strftime('%Y%m')}.txt",
            mime="text/plain",
            use_container_width=True,
        )


# =============================================================================
# EXPENSE REPORT SECTION
# =============================================================================

def show_expense_report() -> None:
    """Detailed expense breakdown with date-range filter."""
    user_id  = get_current_user_id()
    currency = st.session_state.get("currency", "INR")

    all_df = get_transactions(user_id)
    if all_df.empty:
        st.info("No transaction data.")
        return

    min_d, max_d = _period_range(all_df)

    # Date filter
    c1, c2 = st.columns(2)
    start = c1.date_input("From", value=min_d, min_value=min_d, max_value=max_d, key="rep_start")
    end   = c2.date_input("To",   value=max_d, min_value=min_d, max_value=max_d, key="rep_end")

    df = get_transactions(user_id, str(start), str(end))
    expense_df = df[df["amount"] < 0].copy()
    expense_df["amount"] = expense_df["amount"].abs()

    if expense_df.empty:
        st.warning("No expenses in the selected range.")
        return

    st.subheader(f"💸 Expense Report: {start.strftime('%d %b %Y')} → {end.strftime('%d %b %Y')}")

    # Category summary
    cat_summary = (
        expense_df.groupby(["category"])["amount"]
        .agg(Total="sum", Count="count", Average="mean")
        .reset_index()
        .sort_values("Total", ascending=False)
    )
    cat_summary["% Share"] = (cat_summary["Total"] / cat_summary["Total"].sum() * 100).round(1)
    cat_summary["Total"]   = cat_summary["Total"].apply(lambda x: fmt(x, currency))
    cat_summary["Average"] = cat_summary["Average"].apply(lambda x: fmt(x, currency))
    cat_summary["% Share"] = cat_summary["% Share"].apply(lambda x: f"{x}%")

    st.markdown("**Category Breakdown**")
    st.dataframe(cat_summary.reset_index(drop=True), use_container_width=True, hide_index=True)

    # Raw transactions
    with st.expander("📄 All Expense Transactions"):
        show_df = expense_df[["date", "description", "category", "amount", "payment_mode"]].copy()
        show_df["date"]   = pd.to_datetime(show_df["date"]).dt.strftime("%d %b %Y")
        show_df["amount"] = show_df["amount"].apply(lambda x: fmt(x, currency))
        st.dataframe(show_df.reset_index(drop=True), use_container_width=True, hide_index=True)

    # Download
    buf = io.StringIO()
    expense_df.to_csv(buf, index=False)
    st.download_button(
        "⬇️ Download Expense Report CSV",
        data=buf.getvalue(),
        file_name=f"expense_report_{start}_{end}.csv",
        mime="text/csv",
        use_container_width=True,
    )


# =============================================================================
# BUDGET REPORT SECTION
# =============================================================================

def show_budget_report() -> None:
    """Budget vs actual comparison for a selected month."""
    user_id  = get_current_user_id()
    currency = st.session_state.get("currency", "INR")

    st.subheader("🎯 Budget Report")
    selected_month = st.text_input(
        "Month (YYYY-MM)", value=datetime.now().strftime("%Y-%m"),
        key="budget_rep_month",
    )

    budgets_df = get_budgets(user_id, selected_month)
    if budgets_df.empty:
        st.info(f"No budgets set for {selected_month}.")
        return

    budgets_df["Utilisation %"] = (
        budgets_df["spent"] / budgets_df["budget_amount"].replace(0, 1) * 100
    ).round(1)
    budgets_df["Status"] = budgets_df.apply(
        lambda r: "⚠️ Over" if r["spent"] > r["budget_amount"]
                  else ("🟡 Near" if r["Utilisation %"] > 75 else "✅ OK"),
        axis=1,
    )

    display = budgets_df[["category", "budget_amount", "spent",
                           "Utilisation %", "Status"]].copy()
    display.rename(columns={"category": "Category",
                             "budget_amount": "Budget",
                             "spent": "Spent"}, inplace=True)
    display["Budget"] = display["Budget"].apply(lambda x: fmt(x, currency))
    display["Spent"]  = display["Spent"].apply(lambda x: fmt(x, currency))
    display["Utilisation %"] = display["Utilisation %"].apply(lambda x: f"{x}%")

    st.dataframe(display.reset_index(drop=True), use_container_width=True, hide_index=True)


# =============================================================================
# FULL TRANSACTION DOWNLOAD
# =============================================================================

def show_download_section() -> None:
    """One-click download of all transactions as CSV."""
    user_id  = get_current_user_id()
    currency = st.session_state.get("currency", "INR")
    username = st.session_state.get("username", "user")

    st.subheader("📥 Download All Data")

    df = get_transactions(user_id)
    if df.empty:
        st.info("No data to export.")
        return

    # CSV
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    c1, c2 = st.columns(2)
    with c1:
        st.download_button(
            "⬇️ All Transactions (CSV)",
            data=buf.getvalue(),
            file_name=f"all_transactions_{username}_{date.today()}.csv",
            mime="text/csv",
            use_container_width=True,
        )

    # Summary TXT
    monthly = get_monthly_summary(user_id).rename(
        columns={"total_expense": "expense", "total_income": "income"}
    )
    with c2:
        report_txt = _build_monthly_report_text(monthly, username, currency)
        st.download_button(
            "⬇️ Full Summary (TXT)",
            data=report_txt,
            file_name=f"finance_summary_{username}_{date.today()}.txt",
            mime="text/plain",
            use_container_width=True,
        )


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def show_reports_page() -> None:
    """Render the complete Reports page with all sections."""
    st.title("📊 Reports")
    st.markdown("---")

    tab_monthly, tab_expense, tab_budget, tab_download = st.tabs([
        "📅 Monthly",
        "💸 Expenses",
        "🎯 Budget",
        "📥 Download",
    ])

    with tab_monthly:
        show_monthly_report()

    with tab_expense:
        show_expense_report()

    with tab_budget:
        show_budget_report()

    with tab_download:
        show_download_section()
