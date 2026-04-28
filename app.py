import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import io

st.set_page_config(
    page_title="Personal Finance Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

CATEGORY_KEYWORDS = {
    "Food":          ["swiggy", "zomato", "dominos", "pizza", "kfc", "restaurant", "food", "cafe", "biryani"],
    "Groceries":     ["grocery", "reliance fresh", "d-mart", "big bazaar", "big basket", "supermarket", "kirana"],
    "Transport":     ["ola", "uber", "rapido", "metro", "bus", "petrol", "fuel", "auto", "cab", "rickshaw"],
    "Shopping":      ["amazon", "flipkart", "myntra", "westside", "shopping", "mall", "clothes", "fashion"],
    "Entertainment": ["netflix", "spotify", "youtube", "movie", "cinema", "prime", "hotstar", "gaming"],
    "Rent":          ["rent", "house rent", "flat rent", "pg", "hostel"],
    "Utilities":     ["electricity", "water", "gas", "internet", "wifi", "mobile", "recharge", "bill", "broadband"],
    "Health":        ["hospital", "doctor", "medical", "pharmacy", "chemist", "gym", "dentist", "medicine"],
    "Education":     ["book", "course", "college", "school", "udemy", "coursera", "fees", "tuition"],
    "Income":        ["salary", "freelance", "payment", "bonus", "credit", "income"],
}

def auto_categorize(description):
    desc_lower = description.lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return category
    return "Other"

@st.cache_data
def load_sample_data():
    df = pd.read_csv("transactions.csv")
    df["Date"] = pd.to_datetime(df["Date"])
    return df

def load_uploaded_data(file):
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

def format_inr(amount):
    return f"₹{amount:,.0f}"


with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/wallet.png", width=60)
    st.title("Finance Dashboard")
    st.markdown("---")

    st.subheader("📂 Load Data")
    data_source = st.radio("Choose data source:", ["Use Sample Data", "Upload My CSV"])

    df = None
    if data_source == "Use Sample Data":
        df = load_sample_data()
        st.success("✅ Sample data loaded (Jan–Apr 2024)")
    else:
        uploaded = st.file_uploader("Upload CSV file", type=["csv"])
        if uploaded:
            df = load_uploaded_data(uploaded)
            st.success(f"✅ Loaded {len(df)} transactions")
        else:
            st.info("👆 Upload a CSV file to begin")

    if df is not None:
        st.markdown("---")
        st.subheader("🔍 Filters")
        df["Month"] = df["Date"].dt.to_period("M").astype(str)
        months = ["All Months"] + sorted(df["Month"].unique().tolist())
        selected_month = st.selectbox("Select Month", months)
        categories = ["All Categories"] + sorted(df["Type"].unique().tolist())
        selected_cat = st.selectbox("Filter by Type", categories)

        st.markdown("---")
        st.subheader("🎯 Budget Goals (₹)")
        budget_food          = st.number_input("Food Budget",          value=3000, step=500)
        budget_shopping      = st.number_input("Shopping Budget",      value=5000, step=500)
        budget_entertainment = st.number_input("Entertainment Budget", value=1500, step=500)
        budget_transport     = st.number_input("Transport Budget",     value=3000, step=500)


if df is None:
    st.title("💰 Personal Finance Dashboard")
    st.info("👈 Select a data source from the sidebar to get started.")
    st.stop()

filtered_df = df.copy()
if selected_month != "All Months":
    filtered_df = filtered_df[filtered_df["Month"] == selected_month]
if selected_cat != "All Categories":
    filtered_df = filtered_df[filtered_df["Type"] == selected_cat]

income_df  = filtered_df[filtered_df["Amount"] > 0]
expense_df = filtered_df[filtered_df["Amount"] < 0].copy()
expense_df["Amount"] = expense_df["Amount"].abs()

total_income  = income_df["Amount"].sum()
total_expense = expense_df["Amount"].sum()
net_savings   = total_income - total_expense
savings_pct   = (net_savings / total_income * 100) if total_income > 0 else 0
avg_daily     = total_expense / 30 if total_expense > 0 else 0

st.title("💰 Personal Finance Dashboard")
st.caption(f"Showing **{len(filtered_df)}** transactions · {selected_month} · {selected_cat}")
st.markdown("---")

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("💵 Total Income",    format_inr(total_income))
with col2:
    st.metric("💸 Total Expenses",  format_inr(total_expense))
with col3:
    st.metric("🏦 Net Savings",     format_inr(net_savings), f"{savings_pct:.1f}% of income")
with col4:
    st.metric("📅 Avg Daily Spend", format_inr(avg_daily))

st.markdown("---")

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
        barmode="group",
        height=350,
        margin=dict(t=10, b=10, l=10, r=10),
        legend=dict(orientation="h", y=1.1),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#EEEEEE"),
    )
    st.plotly_chart(fig_bar, use_container_width=True)

st.markdown("---")

col_trend, col_budget = st.columns([3, 2])

with col_trend:
    st.subheader("📈 Daily Spending Trend")
    if not expense_df.empty:
        daily_sum = expense_df.copy()
        daily_sum["Date"] = pd.to_datetime(daily_sum["Date"])
        daily_sum = daily_sum.groupby("Date")["Amount"].sum().reset_index()
        fig_area = px.area(
            daily_sum, x="Date", y="Amount",
            color_discrete_sequence=["#F05C5C"]
        )
        fig_area.update_traces(fillcolor="rgba(240,92,92,0.1)", line=dict(width=2))
        fig_area.update_layout(
            height=260, margin=dict(t=10, b=10, l=10, r=10),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(gridcolor="#EEEEEE"), xaxis=dict(gridcolor="rgba(0,0,0,0)")
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
            <span style="color:#1C1F26;font-weight:500;">{cat} — {status}</span>
            <span style="color:{color};font-weight:500;">₹{spent:,.0f} / ₹{limit:,.0f}</span>
          </div>
          <div style="background:#E8EBF0;border-radius:8px;height:10px;overflow:hidden;">
            <div style="width:{pct:.0f}%;background:{color};height:100%;border-radius:8px;"></div>
          </div>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

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
        summary["Total Spent"] = summary["Total Spent"].apply(lambda x: f"₹{x:,.0f}")
        summary["Avg per Txn"] = summary["Avg per Txn"].apply(lambda x: f"₹{x:,.0f}")
        st.dataframe(summary.sort_values("Transactions", ascending=False).reset_index(drop=True),
                     use_container_width=True, hide_index=True)

st.markdown("---")

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
    st.download_button("⬇️ Download CSV", data=buf.getvalue(),
                       file_name="finance_report.csv", mime="text/csv")

with col_d2:
    report = f"""PERSONAL FINANCE REPORT
========================
Period     : {selected_month}
Generated  : {datetime.now().strftime('%d %B %Y')}

Total Income   : {format_inr(total_income)}
Total Expenses : {format_inr(total_expense)}
Net Savings    : {format_inr(net_savings)} ({savings_pct:.1f}%)
Avg Daily Spend: {format_inr(avg_daily)}
"""
    st.download_button("⬇️ Download TXT Report", data=report,
                       file_name="finance_summary.txt", mime="text/plain")

st.markdown("<br><center style='color:#9CA3AF;font-size:12px;'>Personal Finance Dashboard · Python + Streamlit + Plotly</center>",
            unsafe_allow_html=True)