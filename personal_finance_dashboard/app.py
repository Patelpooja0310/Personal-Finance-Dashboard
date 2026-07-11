# =============================================================================
# app.py — Personal Finance Dashboard  |  Main Entry Point
# Tech Stack: Streamlit · MySQL · Plotly · Scikit-Learn · bcrypt
# =============================================================================
# Run:  streamlit run app.py
# =============================================================================

import streamlit as st
from auth import require_login, logout, get_current_user_id

# ── Page Config (must be first Streamlit call) ────────────────────────────────
st.set_page_config(
    page_title="Finance Dashboard",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "Personal Finance Dashboard — built with Streamlit + MySQL + Plotly + ML",
    },
)

# ── Step 1: Authenticate before anything else ─────────────────────────────────
require_login()

# ── Import page modules AFTER auth (avoids DB calls before login) ─────────────
from dashboard    import show_dashboard_page
from transactions import show_transactions_page
from reports      import show_reports_page
from ml_models    import (
    prepare_ml_data, train_all_models, predict_next_month,
    forecast_savings, spending_anomaly_detection,
    plot_predictions, plot_savings_forecast, plot_anomalies,
    model_comparison_df,
)
from database import get_transactions, get_monthly_summary, get_category_spend
from visualization import (
    sunburst_chart, heatmap_spending_pattern, scatter_transaction_sizes,
)


# =============================================================================
# GLOBAL STYLES
# =============================================================================

st.markdown("""
<style>
    /* Remove default Streamlit padding */
    .block-container { padding-top: 1.5rem; padding-bottom: 1rem; }

    /* Sidebar header */
    .sidebar-logo { font-size: 1.6rem; font-weight: 800; color: #1C1F26; }
    .sidebar-sub  { font-size: 0.82rem; color: #6B7280; margin-top: -8px; }

    /* Nav button active state */
    div[data-testid="stSidebarNav"] { display: none; }

    /* Metric card shadow */
    div[data-testid="metric-container"] {
        background: #FAFBFF;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 16px 20px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }

    /* Divider */
    hr { border-top: 1px solid #E5E7EB; margin: 1rem 0; }
</style>
""", unsafe_allow_html=True)


# =============================================================================
# SIDEBAR NAVIGATION
# =============================================================================

PAGES = {
    "🏠 Dashboard":      "dashboard",
    "💳 Transactions":   "transactions",
    "📊 Reports":        "reports",
    "🤖 ML Forecasting": "ml",
    "📈 Advanced Charts":"charts",
    "⚙️ Settings":       "settings",
}

with st.sidebar:
    # ── Brand ─────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
        <span style="font-size:2rem;">💰</span>
        <div>
            <div class="sidebar-logo">Finance Dashboard</div>
            <div class="sidebar-sub">Personal Money Manager</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    username  = st.session_state.get("full_name") or st.session_state.get("username", "")
    st.caption(f"👤 Logged in as **{username}**")
    st.markdown("---")

    # ── Navigation ────────────────────────────────────────────────────────────
    st.markdown("**Navigation**")
    if "active_page" not in st.session_state:
        st.session_state.active_page = "dashboard"

    for label, page_id in PAGES.items():
        is_active = st.session_state.active_page == page_id
        btn_type  = "primary" if is_active else "secondary"
        if st.button(label, use_container_width=True, type=btn_type, key=f"nav_{page_id}"):
            st.session_state.active_page = page_id
            st.rerun()

    st.markdown("---")

    # ── Logout ────────────────────────────────────────────────────────────────
    if st.button("🚪 Logout", use_container_width=True, type="secondary"):
        logout()

    # ── Footer ────────────────────────────────────────────────────────────────
    st.markdown("""
    <div style="position:fixed;bottom:20px;left:0;width:260px;
                text-align:center;font-size:11px;color:#9CA3AF;">
        Personal Finance Dashboard v2.0<br>
        Streamlit · MySQL · Plotly · Scikit-Learn
    </div>
    """, unsafe_allow_html=True)


# =============================================================================
# PAGE ROUTING
# =============================================================================

active = st.session_state.get("active_page", "dashboard")

# ── 1. DASHBOARD ──────────────────────────────────────────────────────────────
if active == "dashboard":
    show_dashboard_page()

# ── 2. TRANSACTIONS ───────────────────────────────────────────────────────────
elif active == "transactions":
    show_transactions_page()

# ── 3. REPORTS ────────────────────────────────────────────────────────────────
elif active == "reports":
    show_reports_page()

# ── 4. ML FORECASTING ─────────────────────────────────────────────────────────
elif active == "ml":
    st.title("🤖 ML Expense Forecasting")
    st.markdown(
        "Compares **Linear Regression**, **Random Forest**, and **Decision Tree** "
        "to predict your next month's expenses and forecast future savings."
    )
    st.markdown("---")

    user_id = get_current_user_id()
    currency = st.session_state.get("currency", "INR")
    symbol   = {"INR": "₹", "USD": "$"}.get(currency, "₹")

    raw_df  = get_transactions(user_id)
    monthly = prepare_ml_data(raw_df)

    if monthly.empty or len(monthly) < 2:
        st.warning("⚠️ You need at least 2 months of expense data to run ML predictions.")
        st.info("Add more transactions or import historical data via the Transactions page.")
        st.stop()

    results     = train_all_models(monthly)
    next_preds  = predict_next_month(monthly, results)
    savings_fc  = forecast_savings(monthly, months_ahead=6)
    anomaly_df  = spending_anomaly_detection(monthly)

    # ── Prediction cards ──────────────────────────────────────────────────────
    st.subheader("🔮 Next Month Expense Prediction")
    icons = ["📐", "🌳", "🌿"]
    cols  = st.columns(len(next_preds))
    for col, (name, val), icon in zip(cols, next_preds.items(), icons):
        col.metric(f"{icon} {name}", f"{symbol}{val:,.0f}")

    st.markdown("---")

    # ── Actual vs Predicted ───────────────────────────────────────────────────
    st.subheader("📈 Actual vs Predicted Expenses")
    fig_pred = plot_predictions(monthly, results)
    st.plotly_chart(fig_pred, use_container_width=True)

    # ── Model comparison ──────────────────────────────────────────────────────
    st.subheader("📊 Model Comparison")
    cmp_df = model_comparison_df(results)
    st.dataframe(cmp_df, use_container_width=True, hide_index=True)

    best = min(results, key=lambda k: results[k]["mae"])
    st.success(f"✅ Best Model: **{best}** (lowest MAE = most accurate)")
    st.markdown("---")

    # ── Savings Forecast ──────────────────────────────────────────────────────
    if not savings_fc.empty:
        st.subheader("💰 Savings Forecast — Next 6 Months")
        fig_sav = plot_savings_forecast(monthly, savings_fc)
        st.plotly_chart(fig_sav, use_container_width=True)

        st.markdown("**Projected Savings (₹)**")
        fc_display = savings_fc.copy()
        for col in ["projected_savings", "lower", "upper"]:
            fc_display[col] = fc_display[col].apply(lambda x: f"{symbol}{x:,.0f}")
        fc_display.rename(columns={
            "month_label": "Month",
            "projected_savings": "Projected Savings",
            "lower": "Lower Bound",
            "upper": "Upper Bound",
        }, inplace=True)
        st.dataframe(fc_display.reset_index(drop=True),
                     use_container_width=True, hide_index=True)

    st.markdown("---")

    # ── Anomaly Detection ─────────────────────────────────────────────────────
    st.subheader("🔍 Spending Anomaly Detection")
    st.caption(
        "Months highlighted in 🔴 red spent significantly more than your average. "
        "Z-score threshold: 1.5σ"
    )
    fig_anom = plot_anomalies(anomaly_df)
    st.plotly_chart(fig_anom, use_container_width=True)

    anomalies_found = anomaly_df[anomaly_df["is_anomaly"]]
    if not anomalies_found.empty:
        st.warning(f"⚠️ {len(anomalies_found)} anomalous month(s) detected:")
        for _, r in anomalies_found.iterrows():
            st.write(f"  • **{r['month']}** — {symbol}{r['total_expense']:,.0f} "
                     f"({r['anomaly_label']}, Z={r['z_score']:.2f})")
    else:
        st.success("✅ No spending anomalies detected.")


# ── 5. ADVANCED CHARTS ────────────────────────────────────────────────────────
elif active == "charts":
    st.title("📈 Advanced Analytics")
    st.markdown("Deep-dive visualisations for spending patterns and distributions.")
    st.markdown("---")

    user_id = get_current_user_id()
    raw_df  = get_transactions(user_id)

    if raw_df.empty:
        st.info("No transaction data yet.")
        st.stop()

    expense_df = raw_df[raw_df["amount"] < 0].copy()

    tab1, tab2, tab3 = st.tabs(["🌞 Sunburst", "🗓️ Heatmap", "🔵 Scatter"])

    with tab1:
        st.caption("Drill into monthly spending by category")
        fig = sunburst_chart(raw_df)
        st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.caption("Discover your highest-spend days of the week")
        fig = heatmap_spending_pattern(expense_df)
        st.plotly_chart(fig, use_container_width=True)

    with tab3:
        st.caption("View individual transaction sizes coloured by category")
        fig = scatter_transaction_sizes(raw_df)
        st.plotly_chart(fig, use_container_width=True)


# ── 6. SETTINGS ───────────────────────────────────────────────────────────────
elif active == "settings":
    st.title("⚙️ Settings")
    st.markdown("---")

    from database import get_user_by_id, update_password

    user_id = get_current_user_id()
    user    = get_user_by_id(user_id)

    if not user:
        st.error("Could not load user profile.")
        st.stop()

    tab_profile, tab_password, tab_categories = st.tabs(
        ["👤 Profile", "🔒 Password", "🏷️ Categories"]
    )

    # ── Profile tab ───────────────────────────────────────────────────────────
    with tab_profile:
        st.subheader("Profile Information")
        st.text_input("Username",  value=user["username"], disabled=True)
        st.text_input("Email",     value=user["email"],    disabled=True)
        st.text_input("Full Name", value=user.get("full_name", ""),  key="s_fullname")
        currency = st.selectbox(
            "Preferred Currency",
            ["INR", "USD", "EUR", "GBP"],
            index=["INR", "USD", "EUR", "GBP"].index(
                user.get("currency", "INR")
            ),
        )
        if st.button("💾 Save Profile"):
            st.success("Profile preferences saved to session.")
            st.session_state.currency = currency

    # ── Password tab ──────────────────────────────────────────────────────────
    with tab_password:
        st.subheader("Change Password")
        from auth import validate_password_strength
        new_pw  = st.text_input("New Password",     type="password", key="s_pw1")
        conf_pw = st.text_input("Confirm Password", type="password", key="s_pw2")

        if new_pw:
            ok, msg = validate_password_strength(new_pw)
            if ok:
                st.success(msg)
            else:
                st.warning(msg)

        if st.button("🔒 Update Password", type="primary"):
            if not new_pw or not conf_pw:
                st.error("Both fields are required.")
            elif new_pw != conf_pw:
                st.error("Passwords do not match.")
            else:
                ok, msg = validate_password_strength(new_pw)
                if not ok:
                    st.error(msg)
                elif update_password(user_id, new_pw):
                    st.success("✅ Password updated successfully!")
                else:
                    st.error("❌ Failed to update password.")

    # ── Categories tab ────────────────────────────────────────────────────────
    with tab_categories:
        from database import get_categories, add_category, delete_category

        st.subheader("Manage Categories")
        cats_df = get_categories(user_id)

        if not cats_df.empty:
            st.dataframe(
                cats_df[["name", "type", "color", "icon", "is_default"]]
                .rename(columns={"name": "Name", "type": "Type",
                                  "color": "Color", "icon": "Icon",
                                  "is_default": "Default"}),
                use_container_width=True, hide_index=True,
            )

        st.markdown("**Add Custom Category**")
        with st.form("add_cat_form"):
            cc1, cc2, cc3, cc4 = st.columns(4)
            cat_name  = cc1.text_input("Name",  placeholder="e.g. Travel")
            cat_type  = cc2.selectbox("Type",   ["expense", "income"])
            cat_color = cc3.color_picker("Color", "#4F6EF7")
            cat_icon  = cc4.text_input("Icon",  placeholder="✈️", max_chars=4)
            if st.form_submit_button("➕ Add Category"):
                if cat_name:
                    ok = add_category(user_id, cat_name, cat_type, cat_color, cat_icon or "📦")
                    if ok:
                        st.success(f"Category '{cat_name}' added!")
                        st.rerun()
                    else:
                        st.error("Category already exists.")
                else:
                    st.error("Category name is required.")
