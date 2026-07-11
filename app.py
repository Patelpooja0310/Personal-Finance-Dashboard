# app.py — Personal Finance Dashboard (Upgraded Version)
# Features: Login, SQLite DB, 3 ML Models, Extra Graphs, KPIs, CSV Upload
 
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io
 
# ── Local modules ──────────────────────────────────────────────────────────────
from auth      import require_login, logout
from database  import load_transactions, insert_transactions, clear_transactions
from ml_models import (
    prepare_ml_data, train_all_models,
    predict_next_month, plot_predictions, model_comparison_df
)
 
# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Finance Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)
 
# ── STEP 1: Block app until logged in ─────────────────────────────────────────
require_login()
 
# ══════════════════════════════════════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════
def format_inr(amount: float) -> str:
    return f"₹{amount:,.0f}"
 
CATEGORY_KEYWORDS = {
    "Food":          ["swiggy", "zomato", "dominos", "pizza", "kfc", "restaurant", "food", "cafe", "biryani"],
    "Groceries":     ["grocery", "reliance fresh", "d-mart", "big bazaar", "big basket", "supermarket", "kirana"],
    "Transport":     ["ola", "uber", "rapido", "metro", "bus", "petrol", "fuel", "auto", "cab", "rickshaw"],
    "Shopping":      ["amazon", "flipkart", "myntra", "westside", "shopping", "mall", "clothes", "fashion"],
    "Entertainment": ["netflix", "spotify", "youtube", "movie", "cinema", "prime", "hotstar", "gaming"],
    "Rent":          ["rent", "house rent", "flat rent", "pg", "hostel"],
    "Utilities":     ["electricity", "water", "gas", "internet", "wifi", "mobile", "recharge", "bill"],
    "Health":        ["hospital", "doctor", "medical", "pharmacy", "chemist", "gym", "dentist", "medicine"],
    "Education":     ["book", "course", "college", "school", "udemy", "coursera", "fees", "tuition"],
    "Income":        ["salary", "freelance", "payment", "bonus", "credit", "income"],
}
 
def auto_categorize(description: str) -> str:
    desc_lower = str(description).lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return category
    return "Other"
 
def load_uploaded_csv(file) -> pd.DataFrame:
    df = pd.read_csv(file)
    df.columns = df.columns.str.strip()
    df["Date"] = pd.to_datetime(df["Date"])
    if "Category" not in df.columns:
        if "Description" in df.columns:
            df["Category"] = df["Description"].apply(auto_categorize)
        else:
            df["Category"] = "Other"
    if "Type" not in df.columns:
        df["Type"] = df["Amount"].apply(lambda x: "Income" if x > 0 else "Expense")
    return df
 
 
# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/wallet.png", width=55)
    st.title("Finance Dashboard")
    st.caption(f"👤 Logged in as **{st.session_state.username}**")
    if st.button("🚪 Logout", use_container_width=True):
        logout()
 
    st.markdown("---")
 
    # ── Data Source ──────────────────────────────────────────────────────────
    st.subheader("📂 Data Source")
    data_source = st.radio("Choose source:", ["SQLite Database", "Upload CSV"])
 
    df = None
    if data_source == "SQLite Database":
        df = load_transactions()
        st.success(f"✅ Loaded {len(df)} rows from SQLite")
    else:
        uploaded = st.file_uploader("Upload CSV", type=["csv"])
        if uploaded:
            new_df = load_uploaded_csv(uploaded)
            if st.button("💾 Save to Database"):
                insert_transactions(new_df)
                st.success(f"✅ {len(new_df)} rows saved to SQLite!")
                st.rerun()
            df = new_df
            st.info(f"Preview: {len(df)} rows loaded")
        else:
            st.info("👆 Upload a CSV file")
 
    if df is not None:
        st.markdown("---")
 
        # ── Filters ──────────────────────────────────────────────────────────
        st.subheader("🔍 Filters")
        df["Month"] = df["Date"].dt.to_period("M").astype(str)
        months = ["All Months"] + sorted(df["Month"].unique().tolist())
        selected_month = st.selectbox("Select Month", months)
        types = ["All Types"] + sorted(df["Type"].unique().tolist())
        selected_type = st.selectbox("Filter by Type", types)
 
        st.markdown("---")
 
        # ── Budget Goals ─────────────────────────────────────────────────────
        st.subheader("🎯 Budget Goals (₹)")
        budget_food          = st.number_input("Food",          value=3000, step=500)
        budget_shopping      = st.number_input("Shopping",      value=5000, step=500)
        budget_entertainment = st.number_input("Entertainment", value=1500, step=500)
        budget_transport     = st.number_input("Transport",     value=3000, step=500)
 
        st.markdown("---")
        if st.button("🗑️ Clear All DB Data", type="secondary"):
            clear_transactions()
            st.warning("Database cleared!")
            st.rerun()
 
# ─── Guard ────────────────────────────────────────────────────────────────────
if df is None:
    st.title("💰 Personal Finance Dashboard")
    st.info("👈 Select a data source from the sidebar to get started.")
    st.stop()
 
 
# ══════════════════════════════════════════════════════════════════════════════
# FILTERED DATA
# ══════════════════════════════════════════════════════════════════════════════
filtered_df = df.copy()
if selected_month != "All Months":
    filtered_df = filtered_df[filtered_df["Month"] == selected_month]
if selected_type != "All Types":
    filtered_df = filtered_df[filtered_df["Type"] == selected_type]
 
income_df  = filtered_df[filtered_df["Amount"] > 0]
expense_df = filtered_df[filtered_df["Amount"] < 0].copy()
expense_df["Amount"] = expense_df["Amount"].abs()
 
total_income  = income_df["Amount"].sum()
total_expense = expense_df["Amount"].sum()
net_savings   = total_income - total_expense
savings_pct   = (net_savings / total_income * 100) if total_income > 0 else 0
avg_daily     = total_expense / 30 if total_expense > 0 else 0
 
# ── Advanced KPIs ─────────────────────────────────────────────────────────────
df_all_exp = df[df["Amount"] < 0].copy()
df_all_exp["Amount"] = df_all_exp["Amount"].abs()
df_all_exp["Month"] = df_all_exp["Date"].dt.to_period("M").astype(str)
monthly_exp = df_all_exp.groupby("Month")["Amount"].sum()
best_month  = monthly_exp.idxmin() if not monthly_exp.empty else "N/A"
worst_month = monthly_exp.idxmax() if not monthly_exp.empty else "N/A"
avg_monthly = monthly_exp.mean() if not monthly_exp.empty else 0
profit_pct  = savings_pct
 
 
# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════
st.title("💰 Personal Finance Dashboard")
st.caption(f"Showing **{len(filtered_df)}** transactions · {selected_month} · {selected_type} · 🗃️ Data from **SQLite Database**")
st.markdown("---")
 
# ══════════════════════════════════════════════════════════════════════════════
# ROW 1: KPI METRICS
# ══════════════════════════════════════════════════════════════════════════════
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("💵 Total Income",    format_inr(total_income))
with col2:
    st.metric("💸 Total Expenses",  format_inr(total_expense))
with col3:
    st.metric("🏦 Net Savings",     format_inr(net_savings), f"{savings_pct:.1f}% of income")
with col4:
    st.metric("📅 Avg Daily Spend", format_inr(avg_daily))
 
# ── Advanced Business Metrics Row ─────────────────────────────────────────────
col5, col6, col7, col8 = st.columns(4)
with col5:
    st.metric("📊 Profit %",            f"{profit_pct:.1f}%")
with col6:
    st.metric("📆 Avg Monthly Expense",  format_inr(avg_monthly))
with col7:
    st.metric("✅ Best Month (Low Exp)", best_month)
with col8:
    st.metric("⚠️ Worst Month (High Exp)", worst_month)
 
st.markdown("---")
 
 
# ══════════════════════════════════════════════════════════════════════════════
# ROW 2: PIE + MONTHLY BAR
# ══════════════════════════════════════════════════════════════════════════════
col_left, col_right = st.columns(2)
 
with col_left:
    st.subheader("🥧 Spending by Category")
    if not expense_df.empty:
        cat_totals = expense_df.groupby("Type")["Amount"].sum().reset_index()
        cat_totals = cat_totals.sort_values("Amount", ascending=False)
        fig_pie = px.pie(
            cat_totals, values="Amount", names="Type",
            hole=0.45,
            color_discrete_sequence=px.colors.qualitative.Set3
        )
        fig_pie.update_traces(
            textposition="inside", textinfo="percent+label",
            hovertemplate="<b>%{label}</b><br>₹%{value:,.0f}<br>%{percent}<extra></extra>"
        )
        fig_pie.update_layout(
            showlegend=True,
            margin=dict(t=10, b=10, l=10, r=10),
            height=350,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    else:
        st.info("No expense data for selected filters.")
 
with col_right:
    st.subheader("📊 Monthly Income vs Expense")
    monthly = df.copy()
    monthly["Month"] = monthly["Date"].dt.to_period("M").astype(str)
    m_income  = monthly[monthly["Amount"] > 0].groupby("Month")["Amount"].sum()
    m_expense = monthly[monthly["Amount"] < 0].groupby("Month")["Amount"].sum().abs()
    m_summary = pd.DataFrame({"Income": m_income, "Expense": m_expense}).fillna(0).reset_index()
    m_summary.columns = ["Month", "Income", "Expense"]
    m_summary["Savings"] = m_summary["Income"] - m_summary["Expense"]
 
    fig_bar = go.Figure()
    fig_bar.add_trace(go.Bar(name="Income",  x=m_summary["Month"], y=m_summary["Income"],  marker_color="#22C58B"))
    fig_bar.add_trace(go.Bar(name="Expense", x=m_summary["Month"], y=m_summary["Expense"], marker_color="#F05C5C"))
    fig_bar.add_trace(go.Scatter(
        name="Savings", x=m_summary["Month"], y=m_summary["Savings"],
        mode="lines+markers", line=dict(color="#4F6EF7", width=2.5), marker=dict(size=8)
    ))
    fig_bar.update_layout(
        barmode="group", height=350, margin=dict(t=10, b=10, l=10, r=10),
        legend=dict(orientation="h", y=1.1),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#EEEEEE"),
    )
    st.plotly_chart(fig_bar, use_container_width=True)
 
st.markdown("---")
 
 
# ══════════════════════════════════════════════════════════════════════════════
# ROW 3: MONTHLY GROWTH RATE + PROFIT VS EXPENSE
# ══════════════════════════════════════════════════════════════════════════════
col_g1, col_g2 = st.columns(2)
 
with col_g1:
    st.subheader("📈 Monthly Expense Growth Rate (%)")
    if len(m_summary) > 1:
        growth = m_summary.copy()
        growth["Growth %"] = growth["Expense"].pct_change() * 100
        growth = growth.dropna()
        colors_growth = ["#22C58B" if x <= 0 else "#F05C5C" for x in growth["Growth %"]]
        fig_growth = go.Figure(go.Bar(
            x=growth["Month"],
            y=growth["Growth %"],
            marker_color=colors_growth,
            text=[f"{v:+.1f}%" for v in growth["Growth %"]],
            textposition="outside"
        ))
        fig_growth.update_layout(
            height=320, margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(gridcolor="#EEEEEE"),
        )
        st.plotly_chart(fig_growth, use_container_width=True)
    else:
        st.info("Need at least 2 months of data for growth rate.")
 
with col_g2:
    st.subheader("💡 Profit vs Expense (Monthly)")
    if not m_summary.empty:
        m_summary["Profit"] = m_summary["Savings"].clip(lower=0)
        fig_pve = go.Figure()
        fig_pve.add_trace(go.Bar(name="Expense", x=m_summary["Month"], y=m_summary["Expense"], marker_color="#F05C5C"))
        fig_pve.add_trace(go.Bar(name="Profit/Savings", x=m_summary["Month"], y=m_summary["Profit"], marker_color="#4F6EF7"))
        fig_pve.update_layout(
            barmode="group", height=320, margin=dict(t=10, b=10, l=10, r=10),
            legend=dict(orientation="h", y=1.1),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(gridcolor="#EEEEEE"),
        )
        st.plotly_chart(fig_pve, use_container_width=True)
 
st.markdown("---")
 
 
# ══════════════════════════════════════════════════════════════════════════════
# ROW 4: DAILY TREND + BUDGET STATUS
# ══════════════════════════════════════════════════════════════════════════════
col_trend, col_budget = st.columns([3, 2])
 
with col_trend:
    st.subheader("📉 Daily Spending Trend")
    if not expense_df.empty:
        daily_sum = expense_df.copy()
        daily_sum["Date"] = pd.to_datetime(daily_sum["Date"])
        daily_sum = daily_sum.groupby("Date")["Amount"].sum().reset_index()
        fig_area = px.area(daily_sum, x="Date", y="Amount", color_discrete_sequence=["#F05C5C"])
        fig_area.update_traces(fillcolor="rgba(240,92,92,0.1)", line=dict(width=2))
        fig_area.update_layout(
            height=280, margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(gridcolor="#EEEEEE"),
        )
        st.plotly_chart(fig_area, use_container_width=True)
 
with col_budget:
    st.subheader("🎯 Budget Status")
    budgets = {
        "Food": budget_food, "Shopping": budget_shopping,
        "Entertainment": budget_entertainment, "Transport": budget_transport,
    }
    for cat, limit in budgets.items():
        spent = expense_df[expense_df["Type"] == cat]["Amount"].sum()
        pct   = min((spent / limit * 100), 100) if limit > 0 else 0
        over  = spent > limit
        color = "#F05C5C" if over else ("#F5A623" if pct > 75 else "#22C58B")
        status = "⚠️ Over budget!" if over else ("🟡 Near limit" if pct > 75 else "✅ On track")
        st.markdown(f"""
        <div style="margin-bottom:14px;">
          <div style="display:flex;justify-content:space-between;font-size:13px;margin-bottom:5px;">
            <span style="font-weight:500;">{cat} — {status}</span>
            <span style="color:{color};font-weight:500;">₹{spent:,.0f} / ₹{limit:,.0f}</span>
          </div>
          <div style="background:#E8EBF0;border-radius:8px;height:10px;overflow:hidden;">
            <div style="width:{pct:.0f}%;background:{color};height:100%;border-radius:8px;"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)
 
st.markdown("---")
 
 
# ══════════════════════════════════════════════════════════════════════════════
# ROW 5: TOP 5 EXPENSES + CATEGORY BREAKDOWN
# ══════════════════════════════════════════════════════════════════════════════
col_top, col_table = st.columns([1, 2])
 
with col_top:
    st.subheader("🔴 Top 5 Expenses")
    if not expense_df.empty:
        top5 = expense_df.nlargest(5, "Amount")[["Date", "Description", "Amount"]].copy()
        top5["Date"]   = top5["Date"].dt.strftime("%d %b")
        top5["Amount"] = top5["Amount"].apply(lambda x: f"₹{x:,.0f}")
        st.dataframe(top5.reset_index(drop=True), use_container_width=True, hide_index=True)
 
with col_table:
    st.subheader("📋 Category Breakdown")
    if not expense_df.empty:
        summary = expense_df.groupby("Type")["Amount"].agg(["sum","count","mean"]).reset_index()
        summary.columns = ["Category", "Total Spent", "Transactions", "Avg per Txn"]
        summary["% of Total"] = (summary["Total Spent"] / summary["Total Spent"].sum() * 100).apply(lambda x: f"{x:.1f}%")
        summary["Total Spent"] = summary["Total Spent"].apply(lambda x: f"₹{x:,.0f}")
        summary["Avg per Txn"] = summary["Avg per Txn"].apply(lambda x: f"₹{x:,.0f}")
        st.dataframe(summary.reset_index(drop=True), use_container_width=True, hide_index=True)
 
st.markdown("---")
 
 
# ══════════════════════════════════════════════════════════════════════════════
# ROW 6: ML PREDICTION SECTION
# ══════════════════════════════════════════════════════════════════════════════
st.subheader("🤖 ML Prediction — Expense Forecasting")
st.caption("Comparing Linear Regression vs Random Forest vs Decision Tree")
 
monthly_ml = prepare_ml_data(df)
 
if len(monthly_ml) < 2:
    st.warning("⚠️ Need at least 2 months of expense data for ML predictions.")
else:
    results = train_all_models(monthly_ml)
    next_preds = predict_next_month(monthly_ml, results)
 
    # ── Next month prediction cards ──────────────────────────────────────────
    st.markdown("#### 🔮 Next Month Expense Prediction")
    pc1, pc2, pc3 = st.columns(3)
    model_cols = [pc1, pc2, pc3]
    icons = ["📐", "🌳", "🌿"]
    for col, (name, val), icon in zip(model_cols, next_preds.items(), icons):
        with col:
            st.metric(f"{icon} {name}", format_inr(val))
 
    # ── Visual: Actual vs Predicted ──────────────────────────────────────────
    fig_pred = plot_predictions(monthly_ml, results)
    st.plotly_chart(fig_pred, use_container_width=True)
 
    # ── Model Comparison Table ───────────────────────────────────────────────
    st.markdown("#### 📊 Model Comparison (Which is Best?)")
    cmp_df = model_comparison_df(results)
    st.dataframe(cmp_df, use_container_width=True, hide_index=True)
 
    best_model = min(results, key=lambda k: results[k]["mae"])
    st.success(f"✅ **Best Model: {best_model}** (lowest MAE = least prediction error)")
    st.info("💡 *'Sir, this is not just a graph project. This is a mini business intelligence system with ML-based prediction capability.'*")
 
st.markdown("---")
 
 
# ══════════════════════════════════════════════════════════════════════════════
# TRANSACTIONS TABLE + DOWNLOAD
# ══════════════════════════════════════════════════════════════════════════════
with st.expander("📑 View All Transactions"):
    show_df = filtered_df.copy()
    show_df["Date"]   = show_df["Date"].dt.strftime("%d %b %Y")
    show_df["Amount"] = show_df["Amount"].apply(
        lambda x: f"🟢 ₹{x:,.0f}" if x > 0 else f"🔴 ₹{abs(x):,.0f}"
    )
    st.dataframe(show_df.reset_index(drop=True), use_container_width=True, hide_index=True)
 
st.markdown("---")
st.subheader("📥 Download Report")
col_d1, col_d2 = st.columns(2)
 
with col_d1:
    buf = io.StringIO()
    filtered_df.to_csv(buf, index=False)
    st.download_button(
        "⬇️ Download CSV", data=buf.getvalue(),
        file_name="finance_report.csv", mime="text/csv"
    )
 
with col_d2:
    report = f"""PERSONAL FINANCE REPORT
========================
Period       : {selected_month}
Generated    : {datetime.now().strftime('%d %B %Y')}
 
Total Income      : {format_inr(total_income)}
Total Expenses    : {format_inr(total_expense)}
Net Savings       : {format_inr(net_savings)} ({savings_pct:.1f}%)
Avg Daily Spend   : {format_inr(avg_daily)}
Avg Monthly Exp   : {format_inr(avg_monthly)}
Best Month        : {best_month}
Worst Month       : {worst_month}
Profit %          : {profit_pct:.1f}%
"""
    st.download_button(
        "⬇️ Download TXT Report", data=report,
        file_name="finance_summary.txt", mime="text/plain"
    )
 
st.markdown(
    "<br><center style='color:#9CA3AF;font-size:12px;'>"
    "Personal Finance Dashboard · Python + Streamlit + Plotly + Scikit-learn + SQLite"
    "</center>",
    unsafe_allow_html=True
)