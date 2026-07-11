# =============================================================================
# transactions.py — Transaction Management UI
# Features: Add, Edit, Delete, View History, Bulk CSV Import
# =============================================================================

import streamlit as st
import pandas as pd
from datetime import date, datetime
from typing import Optional

from database import (
    get_transactions, add_transaction, update_transaction,
    delete_transaction, bulk_insert_transactions, get_categories,
)
from auth import get_current_user_id


# =============================================================================
# HELPER: AUTO-CATEGORISE FROM DESCRIPTION
# =============================================================================

_CATEGORY_KEYWORDS = {
    "Food":          ["swiggy", "zomato", "dominos", "pizza", "kfc", "restaurant",
                      "food", "cafe", "biryani", "mcdonalds", "burger"],
    "Groceries":     ["grocery", "reliance fresh", "d-mart", "big bazaar",
                      "big basket", "supermarket", "kirana", "vegetables"],
    "Transport":     ["ola", "uber", "rapido", "metro", "bus", "petrol",
                      "fuel", "auto", "cab", "rickshaw", "irctc", "train"],
    "Shopping":      ["amazon", "flipkart", "myntra", "westside", "shopping",
                      "mall", "clothes", "fashion", "meesho"],
    "Entertainment": ["netflix", "spotify", "youtube", "movie", "cinema",
                      "prime", "hotstar", "gaming", "disney"],
    "Rent":          ["rent", "house rent", "flat rent", "pg", "hostel"],
    "Utilities":     ["electricity", "water", "gas", "internet", "wifi",
                      "mobile", "recharge", "bill", "postpaid", "prepaid"],
    "Health":        ["hospital", "doctor", "medical", "pharmacy", "chemist",
                      "gym", "dentist", "medicine", "health"],
    "Education":     ["book", "course", "college", "school", "udemy",
                      "coursera", "fees", "tuition", "study"],
    "Salary":        ["salary", "stipend", "payroll"],
    "Freelance":     ["freelance", "project payment", "client payment"],
    "Investment":    ["mutual fund", "sip", "stocks", "investment", "dividend"],
}


def auto_categorise(description: str) -> str:
    desc_lower = str(description).lower()
    for category, keywords in _CATEGORY_KEYWORDS.items():
        if any(kw in desc_lower for kw in keywords):
            return category
    return "Other"


# =============================================================================
# ADD TRANSACTION FORM
# =============================================================================

def show_add_transaction() -> None:
    """Render the Add Transaction form."""
    user_id = get_current_user_id()
    if not user_id:
        st.error("Please log in to add transactions.")
        return

    st.subheader("➕ Add Transaction")

    categories_df = get_categories(user_id)
    cat_names = categories_df["name"].tolist() if not categories_df.empty else ["Other"]

    with st.form("add_txn_form", clear_on_submit=True):
        col1, col2 = st.columns(2)
        with col1:
            txn_date    = st.date_input("Date", value=date.today())
            description = st.text_input("Description", placeholder="e.g. Swiggy order, Salary credit")
            amount_raw  = st.number_input("Amount (₹)", min_value=0.01, step=10.0, format="%.2f")
        with col2:
            txn_type    = st.selectbox("Type", ["expense", "income"])
            category    = st.selectbox("Category", cat_names)
            payment_mode = st.selectbox(
                "Payment Mode",
                ["UPI", "Cash", "Debit Card", "Credit Card", "Net Banking", "Other"],
            )

        notes = st.text_area("Notes (optional)", height=70)
        submitted = st.form_submit_button("✅ Add Transaction", use_container_width=True)

    if submitted:
        # Map category name → id
        cat_row = (
            categories_df[categories_df["name"] == category]
            if not categories_df.empty else pd.DataFrame()
        )
        cat_id = int(cat_row["id"].iloc[0]) if not cat_row.empty else None

        # Sign convention: expense = negative
        signed_amount = -abs(amount_raw) if txn_type == "expense" else abs(amount_raw)

        ok = add_transaction(
            user_id=user_id,
            date=str(txn_date),
            description=description,
            amount=signed_amount,
            txn_type=txn_type,
            category_id=cat_id,
            payment_mode=payment_mode,
            notes=notes,
        )
        if ok:
            st.success(f"✅ Transaction added: ₹{amount_raw:,.2f} ({txn_type})")
            st.rerun()
        else:
            st.error("❌ Failed to add transaction. Please try again.")


# =============================================================================
# EDIT / DELETE TRANSACTION
# =============================================================================

def show_edit_transaction(txn_id: int, txn_row: pd.Series,
                          categories_df: pd.DataFrame) -> None:
    """Inline edit form for an existing transaction (shown inside an expander)."""
    user_id = get_current_user_id()
    cat_names = categories_df["name"].tolist() if not categories_df.empty else ["Other"]

    current_cat  = txn_row.get("category", "Other")
    current_type = txn_row.get("type", "expense")
    current_mode = txn_row.get("payment_mode", "Cash")

    safe_cat_idx  = cat_names.index(current_cat)  if current_cat  in cat_names  else 0
    type_opts     = ["expense", "income"]
    safe_type_idx = type_opts.index(current_type) if current_type in type_opts   else 0
    mode_opts     = ["UPI", "Cash", "Debit Card", "Credit Card", "Net Banking", "Other"]
    safe_mode_idx = mode_opts.index(current_mode) if current_mode in mode_opts   else 0

    with st.form(f"edit_form_{txn_id}"):
        c1, c2 = st.columns(2)
        with c1:
            new_date   = st.date_input("Date", value=pd.to_datetime(txn_row["date"]).date(),
                                       key=f"ed_date_{txn_id}")
            new_desc   = st.text_input("Description", value=txn_row.get("description", ""),
                                       key=f"ed_desc_{txn_id}")
            new_amount = st.number_input("Amount (₹)", value=abs(float(txn_row["amount"])),
                                         min_value=0.01, step=10.0, key=f"ed_amt_{txn_id}")
        with c2:
            new_type   = st.selectbox("Type", type_opts, index=safe_type_idx,
                                      key=f"ed_type_{txn_id}")
            new_cat    = st.selectbox("Category", cat_names, index=safe_cat_idx,
                                      key=f"ed_cat_{txn_id}")
            new_mode   = st.selectbox("Payment Mode", mode_opts, index=safe_mode_idx,
                                      key=f"ed_mode_{txn_id}")
        new_notes = st.text_area("Notes", value=txn_row.get("notes", "") or "",
                                 height=60, key=f"ed_notes_{txn_id}")

        save_btn = st.form_submit_button("💾 Save Changes", type="primary")

    if save_btn:
        cat_row  = categories_df[categories_df["name"] == new_cat]
        cat_id   = int(cat_row["id"].iloc[0]) if not cat_row.empty else None
        signed   = -abs(new_amount) if new_type == "expense" else abs(new_amount)

        ok = update_transaction(
            txn_id=txn_id,
            user_id=user_id,
            date=str(new_date),
            description=new_desc,
            amount=signed,
            txn_type=new_type,
            category_id=cat_id,
            payment_mode=new_mode,
            notes=new_notes,
        )
        if ok:
            st.success("✅ Transaction updated!")
            st.rerun()
        else:
            st.error("❌ Update failed.")


# =============================================================================
# TRANSACTION HISTORY
# =============================================================================

def show_transaction_history() -> None:
    """
    Full transaction history table with:
    - Filter controls (date range, type, category, search)
    - Inline edit / delete per row
    - Pagination
    """
    user_id = get_current_user_id()
    if not user_id:
        return

    st.subheader("📜 Transaction History")

    categories_df = get_categories(user_id)
    df = get_transactions(user_id)

    if df.empty:
        st.info("No transactions found. Add some using the form above.")
        return

    # ── Filters ───────────────────────────────────────────────────────────────
    with st.expander("🔍 Filter Transactions", expanded=False):
        fc1, fc2, fc3, fc4 = st.columns(4)
        with fc1:
            start_dt = st.date_input("From", value=df["date"].min().date(), key="hist_start")
        with fc2:
            end_dt   = st.date_input("To",   value=df["date"].max().date(), key="hist_end")
        with fc3:
            type_filter = st.selectbox("Type",     ["All", "income", "expense"],  key="hist_type")
        with fc4:
            cat_opts    = ["All"] + sorted(df["category"].unique().tolist())
            cat_filter  = st.selectbox("Category", cat_opts, key="hist_cat")

        search = st.text_input("🔎 Search description…", key="hist_search")

    # Apply filters
    mask = (df["date"].dt.date >= start_dt) & (df["date"].dt.date <= end_dt)
    if type_filter != "All":
        mask &= df["type"] == type_filter
    if cat_filter != "All":
        mask &= df["category"] == cat_filter
    if search:
        mask &= df["description"].str.contains(search, case=False, na=False)

    filtered = df[mask].reset_index(drop=True)
    st.caption(f"Showing **{len(filtered)}** of {len(df)} transactions")

    if filtered.empty:
        st.warning("No transactions match your filters.")
        return

    # ── Pagination ────────────────────────────────────────────────────────────
    PAGE_SIZE = 15
    total_pages = max(1, (len(filtered) - 1) // PAGE_SIZE + 1)
    page = st.number_input("Page", min_value=1, max_value=total_pages,
                            value=1, step=1, key="hist_page")
    start = (page - 1) * PAGE_SIZE
    page_df = filtered.iloc[start: start + PAGE_SIZE]

    # ── Table header ──────────────────────────────────────────────────────────
    hcols = st.columns([1.2, 2.5, 1.5, 1.5, 1.5, 1, 1])
    for col, label in zip(hcols, ["Date", "Description", "Amount", "Category",
                                   "Mode", "Edit", "Delete"]):
        col.markdown(f"**{label}**")
    st.divider()

    # ── Rows ──────────────────────────────────────────────────────────────────
    for _, row in page_df.iterrows():
        txn_id = int(row["id"])
        cols   = st.columns([1.2, 2.5, 1.5, 1.5, 1.5, 1, 1])
        cols[0].write(pd.to_datetime(row["date"]).strftime("%d %b %Y"))
        cols[1].write(str(row.get("description", ""))[:45])

        amount = float(row["amount"])
        if amount >= 0:
            cols[2].markdown(f"<span style='color:#22C58B'>🟢 ₹{amount:,.0f}</span>",
                             unsafe_allow_html=True)
        else:
            cols[2].markdown(f"<span style='color:#F05C5C'>🔴 ₹{abs(amount):,.0f}</span>",
                             unsafe_allow_html=True)

        cols[3].write(f"{row.get('category_icon','📦')} {row.get('category','—')}")
        cols[4].write(str(row.get("payment_mode", "—")))

        # Edit toggle
        edit_key = f"edit_toggle_{txn_id}"
        if edit_key not in st.session_state:
            st.session_state[edit_key] = False

        if cols[5].button("✏️", key=f"eb_{txn_id}", help="Edit"):
            st.session_state[edit_key] = not st.session_state[edit_key]

        if cols[6].button("🗑️", key=f"db_{txn_id}", help="Delete"):
            ok = delete_transaction(txn_id, user_id)
            if ok:
                st.success("Transaction deleted.")
                st.rerun()
            else:
                st.error("Delete failed.")

        # Inline edit form
        if st.session_state[edit_key]:
            with st.container():
                show_edit_transaction(txn_id, row, categories_df)


# =============================================================================
# BULK CSV IMPORT
# =============================================================================

def show_bulk_import() -> None:
    """Upload a CSV file and bulk-insert transactions."""
    user_id = get_current_user_id()
    if not user_id:
        return

    st.subheader("📤 Bulk Import via CSV")
    st.caption(
        "Required columns: `date`, `description`, `amount`  \n"
        "Optional columns: `type`, `category`, `payment_mode`, `notes`  \n"
        "Use negative amounts for expenses, positive for income."
    )

    uploaded = st.file_uploader("Upload CSV", type=["csv"], key="bulk_upload")

    if not uploaded:
        return

    try:
        df = pd.read_csv(uploaded)
        df.columns = df.columns.str.strip().str.lower()

        # Rename common aliases
        df.rename(columns={"Date": "date", "Amount": "amount",
                            "Description": "description",
                            "Type": "type"}, inplace=True)

        required = ["date", "description", "amount"]
        missing  = [c for c in required if c not in df.columns]
        if missing:
            st.error(f"Missing required columns: {missing}")
            return

        df["date"]   = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")
        df["amount"] = pd.to_numeric(df["amount"], errors="coerce").fillna(0)

        if "type" not in df.columns:
            df["type"] = df["amount"].apply(lambda x: "income" if x > 0 else "expense")

        # Auto-categorise if category column missing
        categories_df = get_categories(user_id)
        if "category" not in df.columns and "description" in df.columns:
            df["category"] = df["description"].apply(auto_categorise)

        # Map category name → id
        cat_map = (
            dict(zip(categories_df["name"], categories_df["id"]))
            if not categories_df.empty else {}
        )
        if "category" in df.columns:
            df["category_id"] = df["category"].map(cat_map)
        else:
            df["category_id"] = None

        st.markdown(f"**Preview** — {len(df)} rows:")
        st.dataframe(
            df[["date", "description", "amount", "type"]].head(10),
            use_container_width=True
        )

        if st.button("💾 Import to Database", type="primary"):
            rows = df.to_dict(orient="records")
            inserted = bulk_insert_transactions(user_id, rows)
            if inserted > 0:
                st.success(f"✅ {inserted} transactions imported successfully!")
                st.rerun()
            else:
                st.error("Import failed. Check your CSV format.")

    except Exception as e:
        st.error(f"Error reading CSV: {e}")


# =============================================================================
# MAIN ENTRY — render the full Transactions page
# =============================================================================

def show_transactions_page() -> None:
    """Render the complete Transactions management page."""
    st.title("💳 Transactions")
    st.markdown("---")

    tab_add, tab_history, tab_import = st.tabs(
        ["➕ Add Transaction", "📜 History", "📤 Bulk Import"]
    )

    with tab_add:
        show_add_transaction()

    with tab_history:
        show_transaction_history()

    with tab_import:
        show_bulk_import()
