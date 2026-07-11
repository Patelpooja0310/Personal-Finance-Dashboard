# =============================================================================
# auth.py — Authentication & Session Management
# Handles: Registration, Login, Logout, Password Hashing, Session State
# =============================================================================

import streamlit as st
import bcrypt
import re
from typing import Optional, Dict, Any
from database import verify_user, create_user, get_user_by_id


# =============================================================================
# PASSWORD UTILITIES
# =============================================================================

def hash_password(password: str) -> str:
    """Return a bcrypt hash of the given plaintext password."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def check_password(password: str, hashed: str) -> bool:
    """Return True if plaintext password matches the stored bcrypt hash."""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def validate_password_strength(password: str) -> tuple[bool, str]:
    """
    Enforce minimum password requirements.
    Returns (is_valid: bool, message: str).
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[0-9]", password):
        return False, "Password must contain at least one digit."
    return True, "Strong password ✅"


def validate_email(email: str) -> bool:
    """Basic regex check for a valid email address."""
    pattern = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


# =============================================================================
# SESSION HELPERS
# =============================================================================

def _init_session() -> None:
    """Initialise all auth-related session state keys."""
    defaults = {
        "logged_in": False,
        "user_id":   None,
        "username":  "",
        "full_name": "",
        "currency":  "INR",
    }
    for key, val in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = val


def is_logged_in() -> bool:
    _init_session()
    return st.session_state.logged_in


def get_current_user_id() -> Optional[int]:
    return st.session_state.get("user_id")


def get_current_username() -> str:
    return st.session_state.get("username", "")


def _set_session(user: Dict[str, Any]) -> None:
    """Populate session state after a successful login."""
    st.session_state.logged_in = True
    st.session_state.user_id   = user["id"]
    st.session_state.username  = user["username"]
    st.session_state.full_name = user.get("full_name") or user["username"]
    st.session_state.currency  = user.get("currency", "INR")


def logout() -> None:
    """Clear session state and force a rerun to the login page."""
    for key in ["logged_in", "user_id", "username", "full_name", "currency"]:
        st.session_state[key] = None if key == "user_id" else ("" if isinstance(st.session_state.get(key), str) else False)
    st.session_state.logged_in = False
    st.rerun()


# =============================================================================
# LOGIN PAGE UI
# =============================================================================

def _show_login_form() -> None:
    """Render the login tab content."""
    st.markdown("#### 🔐 Sign In")
    username = st.text_input("Username", placeholder="Enter your username", key="login_user")
    password = st.text_input("Password", type="password", placeholder="Enter your password", key="login_pass")

    col_btn, col_forgot = st.columns([2, 1])
    with col_btn:
        login_clicked = st.button("Login →", use_container_width=True, type="primary")

    if login_clicked:
        if not username or not password:
            st.error("Please enter both username and password.")
            return
        user = verify_user(username.strip(), password)
        if user:
            _set_session(user)
            st.success(f"Welcome back, {user.get('full_name') or username}! 🎉")
            st.rerun()
        else:
            st.error("❌ Invalid username or password. Please try again.")

    st.markdown("---")
    st.info(
        "**Demo Credentials:**\n\n"
        "Username: `demo`  \nPassword: `Demo@1234`"
    )


# =============================================================================
# REGISTRATION PAGE UI
# =============================================================================

def _show_register_form() -> None:
    """Render the registration tab content."""
    st.markdown("#### 📝 Create Account")

    full_name = st.text_input("Full Name",  placeholder="Your full name",  key="reg_name")
    username  = st.text_input("Username",   placeholder="Choose a username", key="reg_user")
    email     = st.text_input("Email",      placeholder="your@email.com",   key="reg_email")
    password  = st.text_input("Password",   type="password",
                               placeholder="Min 8 chars, 1 uppercase, 1 digit", key="reg_pass")
    confirm   = st.text_input("Confirm Password", type="password",
                               placeholder="Re-enter password", key="reg_confirm")

    # Live password feedback
    if password:
        ok, msg = validate_password_strength(password)
        if ok:
            st.success(msg)
        else:
            st.warning(msg)

    if st.button("Create Account", use_container_width=True, type="primary"):
        # ── Validation ────────────────────────────────────────────────────────
        if not all([full_name, username, email, password, confirm]):
            st.error("All fields are required.")
            return
        if not validate_email(email):
            st.error("Please enter a valid email address.")
            return
        ok, msg = validate_password_strength(password)
        if not ok:
            st.error(msg)
            return
        if password != confirm:
            st.error("Passwords do not match.")
            return
        if len(username) < 3:
            st.error("Username must be at least 3 characters.")
            return

        # ── Create user ───────────────────────────────────────────────────────
        result = create_user(
            username=username.strip(),
            email=email.strip().lower(),
            password=password,
            full_name=full_name.strip(),
        )
        if result["success"]:
            st.success("✅ Account created! You can now log in.")
        else:
            st.error(f"Registration failed: {result['error']}")


# =============================================================================
# MAIN AUTH GATE  — call require_login() at the top of app.py
# =============================================================================

def show_auth_page() -> None:
    """
    Full-page authentication UI with Login and Register tabs.
    Styled to match the dashboard theme.
    """
    st.markdown("""
    <style>
        /* Centre the auth card */
        .auth-wrapper {
            display: flex;
            justify-content: center;
            margin-top: 40px;
        }
        .auth-header {
            text-align: center;
            margin-bottom: 12px;
        }
        .auth-title {
            font-size: 2rem;
            font-weight: 800;
            color: #1C1F26;
        }
        .auth-sub {
            font-size: 0.95rem;
            color: #6B7280;
            margin-top: -8px;
        }
    </style>
    """, unsafe_allow_html=True)

    _, mid, _ = st.columns([1, 2, 1])
    with mid:
        st.markdown("""
        <div class="auth-header">
            <div style="font-size:3rem;">💰</div>
            <div class="auth-title">Finance Dashboard</div>
            <div class="auth-sub">Track, analyse & forecast your finances</div>
        </div>
        """, unsafe_allow_html=True)

        tab_login, tab_register = st.tabs(["🔐 Login", "📝 Register"])
        with tab_login:
            _show_login_form()
        with tab_register:
            _show_register_form()


def require_login() -> None:
    """
    Call this at the very top of app.py.
    Blocks all app content until the user is authenticated.
    """
    _init_session()
    if not st.session_state.logged_in:
        show_auth_page()
        st.stop()
