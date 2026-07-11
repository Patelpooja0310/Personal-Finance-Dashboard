# =============================================================================
# visualization.py — All Plotly Chart Builders
# Charts: Pie, Bar, Line, Area, Waterfall, Heatmap, Sunburst, Scatter
# =============================================================================

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from typing import Optional

# Shared colour palette
PALETTE = {
    "income":     "#22C58B",
    "expense":    "#F05C5C",
    "savings":    "#4F6EF7",
    "warning":    "#F5A623",
    "neutral":    "#9CA3AF",
    "bg":         "rgba(0,0,0,0)",
    "grid":       "#EEEEEE",
    "qualitative": px.colors.qualitative.Set3,
}

_LAYOUT_DEFAULTS = dict(
    paper_bgcolor=PALETTE["bg"],
    plot_bgcolor=PALETTE["bg"],
    margin=dict(t=40, b=40, l=10, r=10),
    font=dict(family="Inter, sans-serif", size=13),
)


def _apply_defaults(fig: go.Figure, height: int = 380) -> go.Figure:
    fig.update_layout(height=height, **_LAYOUT_DEFAULTS)
    fig.update_yaxes(gridcolor=PALETTE["grid"], gridwidth=1)
    return fig


# =============================================================================
# 1. PIE / DONUT CHART — Category Spending
# =============================================================================

def pie_chart_by_category(df_spend: pd.DataFrame,
                           title: str = "Spending by Category") -> go.Figure:
    """
    Donut pie chart of expense amounts per category.

    Input: DataFrame with columns [category, total_spent]
    """
    if df_spend.empty:
        return _empty_figure("No expense data available.")

    fig = px.pie(
        df_spend,
        values="total_spent",
        names="category",
        hole=0.48,
        title=title,
        color_discrete_sequence=PALETTE["qualitative"],
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<br>%{percent}<extra></extra>",
        pull=[0.03] * len(df_spend),
    )
    fig.update_layout(
        legend=dict(orientation="h", y=-0.15),
        showlegend=True,
        title_font_size=15,
    )
    return _apply_defaults(fig, height=400)


# =============================================================================
# 2. GROUPED BAR CHART — Income vs Expense by Month
# =============================================================================

def bar_chart_income_expense(monthly: pd.DataFrame) -> go.Figure:
    """
    Grouped bar chart with a savings line overlay.

    Input: DataFrame with columns [month, income, expense, savings]
    """
    if monthly.empty:
        return _empty_figure("No monthly data available.")

    fig = go.Figure()

    fig.add_trace(go.Bar(
        name="Income",
        x=monthly["month"],
        y=monthly["income"],
        marker_color=PALETTE["income"],
        hovertemplate="Income<br>%{x}<br>₹%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Bar(
        name="Expense",
        x=monthly["month"],
        y=monthly["expense"],
        marker_color=PALETTE["expense"],
        hovertemplate="Expense<br>%{x}<br>₹%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        name="Net Savings",
        x=monthly["month"],
        y=monthly["savings"],
        mode="lines+markers",
        line=dict(color=PALETTE["savings"], width=2.5),
        marker=dict(size=8),
        hovertemplate="Savings<br>%{x}<br>₹%{y:,.0f}<extra></extra>",
    ))

    fig.update_layout(
        barmode="group",
        title="📊 Monthly Income vs Expense",
        xaxis_title="Month",
        yaxis_title="Amount (₹)",
        legend=dict(orientation="h", y=1.1),
        hovermode="x unified",
        title_font_size=15,
    )
    return _apply_defaults(fig, height=400)


# =============================================================================
# 3. LINE CHART — Daily Spending Trend
# =============================================================================

def line_chart_daily_trend(expense_df: pd.DataFrame) -> go.Figure:
    """
    Area line chart showing daily expense totals.

    Input: transactions DataFrame with columns [date, amount]
    """
    if expense_df.empty:
        return _empty_figure("No expense data for this period.")

    daily = (
        expense_df.copy()
        .assign(date=lambda d: pd.to_datetime(d["date"]))
        .groupby("date")["amount"]
        .sum()
        .abs()
        .reset_index()
        .rename(columns={"amount": "daily_expense"})
    )
    # 7-day rolling average
    daily["rolling_7d"] = daily["daily_expense"].rolling(7, min_periods=1).mean()

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=daily["date"],
        y=daily["daily_expense"],
        name="Daily Spend",
        mode="lines",
        line=dict(color=PALETTE["expense"], width=1.5),
        fill="tozeroy",
        fillcolor="rgba(240,92,92,0.10)",
        hovertemplate="%{x|%d %b %Y}<br>₹%{y:,.0f}<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=daily["date"],
        y=daily["rolling_7d"],
        name="7-Day Avg",
        mode="lines",
        line=dict(color=PALETTE["savings"], width=2, dash="dot"),
        hovertemplate="7-Day Avg<br>₹%{y:,.0f}<extra></extra>",
    ))

    fig.update_layout(
        title="📉 Daily Spending Trend",
        xaxis_title="Date",
        yaxis_title="Expense (₹)",
        legend=dict(orientation="h", y=1.1),
        title_font_size=15,
    )
    return _apply_defaults(fig, height=340)


# =============================================================================
# 4. MONTHLY TREND LINE — Expense Over Time
# =============================================================================

def line_chart_monthly_trend(monthly: pd.DataFrame) -> go.Figure:
    """
    Multi-line chart: expense, income, savings trends over months.
    """
    if monthly.empty:
        return _empty_figure("No data available.")

    fig = go.Figure()
    for col, color, label in [
        ("expense", PALETTE["expense"],  "Total Expense"),
        ("income",  PALETTE["income"],   "Total Income"),
        ("savings", PALETTE["savings"],  "Net Savings"),
    ]:
        fig.add_trace(go.Scatter(
            x=monthly["month"],
            y=monthly[col],
            mode="lines+markers",
            name=label,
            line=dict(color=color, width=2.2),
            marker=dict(size=7),
            hovertemplate=f"{label}<br>%{{x}}<br>₹%{{y:,.0f}}<extra></extra>",
        ))

    fig.update_layout(
        title="📈 Monthly Financial Trend",
        xaxis_title="Month",
        yaxis_title="Amount (₹)",
        legend=dict(orientation="h", y=1.1),
        hovermode="x unified",
        title_font_size=15,
    )
    return _apply_defaults(fig, height=380)


# =============================================================================
# 5. EXPENSE GROWTH RATE — Bar Chart (%)
# =============================================================================

def bar_chart_growth_rate(monthly: pd.DataFrame) -> go.Figure:
    """
    Month-over-month expense growth rate as a signed bar chart.
    Green = reduction, Red = increase.
    """
    if monthly.empty or len(monthly) < 2:
        return _empty_figure("Need at least 2 months of data.")

    df = monthly.copy()
    df["growth_pct"] = df["expense"].pct_change() * 100
    df = df.dropna(subset=["growth_pct"])

    colors = [PALETTE["income"] if v <= 0 else PALETTE["expense"] for v in df["growth_pct"]]

    fig = go.Figure(go.Bar(
        x=df["month"],
        y=df["growth_pct"],
        marker_color=colors,
        text=[f"{v:+.1f}%" for v in df["growth_pct"]],
        textposition="outside",
        hovertemplate="%{x}<br>%{y:+.1f}%<extra></extra>",
    ))
    fig.add_hline(y=0, line_dash="dot", line_color=PALETTE["neutral"])
    fig.update_layout(
        title="📊 Month-over-Month Expense Growth Rate",
        xaxis_title="Month",
        yaxis_title="Growth (%)",
        title_font_size=15,
    )
    return _apply_defaults(fig, height=340)


# =============================================================================
# 6. WATERFALL CHART — Cumulative Cash Flow
# =============================================================================

def waterfall_chart(monthly: pd.DataFrame) -> go.Figure:
    """
    Waterfall chart showing cumulative savings journey month by month.
    """
    if monthly.empty:
        return _empty_figure("No data available.")

    fig = go.Figure(go.Waterfall(
        name="Cash Flow",
        orientation="v",
        measure=["relative"] * len(monthly),
        x=monthly["month"],
        y=monthly["savings"],
        connector=dict(line=dict(color="#CCCCCC", width=1)),
        increasing=dict(marker=dict(color=PALETTE["income"])),
        decreasing=dict(marker=dict(color=PALETTE["expense"])),
        hovertemplate="%{x}<br>₹%{y:,.0f}<extra></extra>",
    ))
    fig.update_layout(
        title="💧 Cumulative Cash-Flow Waterfall",
        xaxis_title="Month",
        yaxis_title="Savings Change (₹)",
        title_font_size=15,
    )
    return _apply_defaults(fig, height=360)


# =============================================================================
# 7. SUNBURST CHART — Category × Month Spending
# =============================================================================

def sunburst_chart(transactions_df: pd.DataFrame) -> go.Figure:
    """
    Two-level sunburst: outer = month, inner = category.
    Shows drill-down view of where money goes each month.
    """
    if transactions_df.empty:
        return _empty_figure("No transaction data.")

    df = transactions_df.copy()
    df = df[df["amount"] < 0].copy()
    df["amount"] = df["amount"].abs()
    df["month"] = pd.to_datetime(df["date"]).dt.to_period("M").astype(str)

    grouped = (
        df.groupby(["month", "category"])["amount"]
        .sum()
        .reset_index()
        .rename(columns={"amount": "total"})
    )

    fig = px.sunburst(
        grouped,
        path=["month", "category"],
        values="total",
        title="🌞 Spending Breakdown: Month → Category",
        color_discrete_sequence=PALETTE["qualitative"],
    )
    fig.update_traces(
        hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<br>%{percentParent:.1%}<extra></extra>"
    )
    fig.update_layout(title_font_size=15)
    return _apply_defaults(fig, height=450)


# =============================================================================
# 8. HEATMAP — Spending by Day of Week × Week of Month
# =============================================================================

def heatmap_spending_pattern(expense_df: pd.DataFrame) -> go.Figure:
    """
    Calendar heatmap: rows = day of week, columns = week of month.
    Intensity = total expense.
    """
    if expense_df.empty:
        return _empty_figure("No expense data.")

    df = expense_df.copy()
    df["date"]        = pd.to_datetime(df["date"])
    df["amount"]      = df["amount"].abs()
    df["day_of_week"] = df["date"].dt.day_name()
    df["week_of_month"] = df["date"].dt.day.apply(lambda d: f"Week {(d - 1) // 7 + 1}")

    pivot = (
        df.groupby(["day_of_week", "week_of_month"])["amount"]
        .sum()
        .unstack(fill_value=0)
    )

    days_order = ["Monday", "Tuesday", "Wednesday", "Thursday",
                  "Friday", "Saturday", "Sunday"]
    pivot = pivot.reindex([d for d in days_order if d in pivot.index])

    fig = go.Figure(go.Heatmap(
        z=pivot.values,
        x=pivot.columns.tolist(),
        y=pivot.index.tolist(),
        colorscale="Reds",
        hovertemplate="<b>%{y} · %{x}</b><br>₹%{z:,.0f}<extra></extra>",
        colorbar=dict(title="₹ Spent"),
    ))
    fig.update_layout(
        title="🗓️ Spending Pattern: Day of Week × Week of Month",
        xaxis_title="Week of Month",
        yaxis_title="Day of Week",
        title_font_size=15,
    )
    return _apply_defaults(fig, height=340)


# =============================================================================
# 9. SCATTER — Transaction Size Distribution
# =============================================================================

def scatter_transaction_sizes(df: pd.DataFrame) -> go.Figure:
    """
    Scatter plot of individual transaction amounts over time,
    coloured by category.
    """
    if df.empty:
        return _empty_figure("No data.")

    plot_df = df.copy()
    plot_df["date"]   = pd.to_datetime(plot_df["date"])
    plot_df["amount"] = plot_df["amount"].abs()

    fig = px.scatter(
        plot_df,
        x="date",
        y="amount",
        color="category",
        size="amount",
        size_max=30,
        title="🔵 Transaction Size Distribution",
        labels={"amount": "Amount (₹)", "date": "Date"},
        color_discrete_sequence=PALETTE["qualitative"],
        hover_data=["description", "type"],
    )
    fig.update_layout(
        legend=dict(orientation="h", y=-0.25),
        title_font_size=15,
    )
    return _apply_defaults(fig, height=380)


# =============================================================================
# UTILITY
# =============================================================================

def _empty_figure(message: str = "No data") -> go.Figure:
    """Return a blank figure with a centred annotation."""
    fig = go.Figure()
    fig.add_annotation(
        text=message,
        xref="paper", yref="paper",
        x=0.5, y=0.5,
        showarrow=False,
        font=dict(size=16, color=PALETTE["neutral"]),
    )
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
    )
    return _apply_defaults(fig, height=300)
