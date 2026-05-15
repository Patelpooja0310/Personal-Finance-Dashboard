# auth.py — Simple Login System
 
import streamlit as st
import hashlib
 
# ─── User Database (username: hashed_password) ───────────────────────────────
# Password "admin123"  → sha256 hash
# Password "demo123"   → sha256 hash
USERS = {
    "admin": hashlib.sha256("admin123".encode()).hexdigest(),
    "demo":  hashlib.sha256("demo123".encode()).hexdigest(),
}
 
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()
 
def check_login(username: str, password: str) -> bool:
    """Returns True if credentials are valid."""
    return USERS.get(username) == hash_password(password)
 
def show_login_page():
    """
    Renders the login UI.
    Sets st.session_state.logged_in = True on success.
    """
    st.markdown("""
    <style>
        .login-box {
            max-width: 420px;
            margin: 80px auto;
            padding: 40px;
            background: #ffffff;
            border-radius: 16px;
            box-shadow: 0 4px 24px rgba(0,0,0,0.10);
        }
        .login-title {
            text-align: center;
            font-size: 28px;
            font-weight: 700;
            color: #1C1F26;
            margin-bottom: 4px;
        }
        .login-sub {
            text-align: center;
            font-size: 14px;
            color: #6B7280;
            margin-bottom: 28px;
        }
    </style>
    <div class="login-box">
        <div class="login-title">💰 Finance Dashboard</div>
        <div class="login-sub">Sign in to access your dashboard</div>
    </div>
    """, unsafe_allow_html=True)
 
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown("### 🔐 Login")
        username = st.text_input("Username", placeholder="Enter username")
        password = st.text_input("Password", type="password", placeholder="Enter password")
 
        if st.button("Login →", use_container_width=True, type="primary"):
            if check_login(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.rerun()
            else:
                st.error("❌ Invalid username or password")
 
        st.markdown("---")
        st.info("**Demo Credentials:**\n\nUsername: `demo`  \nPassword: `demo123`")
 
def logout():
    """Clears session state and returns to login."""
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.rerun()
 
def require_login():
    """
    Call this at the top of app.py.
    Blocks the app until the user is logged in.
    """
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
        st.session_state.username = ""
 
    if not st.session_state.logged_in:
        show_login_page()
        st.stop()   # stop rest of app from rendering