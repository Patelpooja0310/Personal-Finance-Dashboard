# =============================================================================
# database.py — MySQL Database Layer
# Handles: connection pooling, table auto-creation, all CRUD operations
# =============================================================================
# Dependencies: mysql-connector-python, pandas
# Config:       Edit DB_CONFIG below or set environment variables.
# =============================================================================

import os
import pandas as pd
import mysql.connector
from mysql.connector import pooling, Error
from datetime import datetime
from typing import Optional, List, Dict, Any
import bcrypt

# =============================================================================
# DATABASE CONFIGURATION
# Override via environment variables in production (e.g. Docker / .env file)
# =============================================================================
DB_CONFIG = {
    "host":     os.getenv("DB_HOST",     "localhost"),
    "port":     int(os.getenv("DB_PORT", "3306")),
    "user":     os.getenv("DB_USER",     "root"),
    "password": os.getenv("DB_PASSWORD", "MySQL@Project123"),
    "database": os.getenv("DB_NAME",     "finance_dashboard"),
    "charset":  "utf8mb4",
    "use_unicode": True,
    "autocommit": False,
}

# Connection pool — reuses connections instead of opening a new one per query
_pool: Optional[pooling.MySQLConnectionPool] = None


def _get_pool() -> pooling.MySQLConnectionPool:
    """Lazily create and return the global connection pool."""
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="finance_pool",
            pool_size=5,
            pool_reset_session=True,
            **DB_CONFIG,
        )
    return _pool


def get_connection():
    """Borrow a connection from the pool."""
    return _get_pool().get_connection()


# =============================================================================
# SCHEMA AUTO-CREATION
# Creates all tables if they don't already exist (idempotent).
# =============================================================================
_DDL_STATEMENTS = [
    # ── Users ─────────────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS users (
        id            INT          AUTO_INCREMENT PRIMARY KEY,
        username      VARCHAR(50)  NOT NULL UNIQUE,
        email         VARCHAR(120) NOT NULL UNIQUE,
        password_hash VARCHAR(255) NOT NULL,
        full_name     VARCHAR(100),
        currency      VARCHAR(10)  NOT NULL DEFAULT 'INR',
        is_active     TINYINT(1)   NOT NULL DEFAULT 1,
        created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                                   ON UPDATE CURRENT_TIMESTAMP,
        last_login    DATETIME
    ) ENGINE=InnoDB
    """,
    # ── Categories ────────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS categories (
        id          INT          AUTO_INCREMENT PRIMARY KEY,
        user_id     INT          NOT NULL,
        name        VARCHAR(80)  NOT NULL,
        type        ENUM('income','expense') NOT NULL DEFAULT 'expense',
        color       VARCHAR(10)  DEFAULT '#4F6EF7',
        icon        VARCHAR(10)  DEFAULT '📦',
        is_default  TINYINT(1)   NOT NULL DEFAULT 0,
        created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE KEY  uq_user_category (user_id, name),
        CONSTRAINT fk_cat_user FOREIGN KEY (user_id)
            REFERENCES users(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """,
    # ── Transactions ──────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS transactions (
        id            INT           AUTO_INCREMENT PRIMARY KEY,
        user_id       INT           NOT NULL,
        category_id   INT,
        date          DATE          NOT NULL,
        description   VARCHAR(255),
        amount        DECIMAL(15,2) NOT NULL,
        type          ENUM('income','expense') NOT NULL,
        payment_mode  VARCHAR(50)   DEFAULT 'Cash',
        notes         TEXT,
        created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                    ON UPDATE CURRENT_TIMESTAMP,
        CONSTRAINT fk_txn_user FOREIGN KEY (user_id)
            REFERENCES users(id) ON DELETE CASCADE,
        CONSTRAINT fk_txn_cat  FOREIGN KEY (category_id)
            REFERENCES categories(id) ON DELETE SET NULL
    ) ENGINE=InnoDB
    """,
    # ── Budgets ───────────────────────────────────────────────────────────────
    """
    CREATE TABLE IF NOT EXISTS budgets (
        id          INT           AUTO_INCREMENT PRIMARY KEY,
        user_id     INT           NOT NULL,
        category_id INT           NOT NULL,
        month       CHAR(7)       NOT NULL,
        amount      DECIMAL(15,2) NOT NULL,
        created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                  ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY  uq_budget (user_id, category_id, month),
        CONSTRAINT fk_bud_user FOREIGN KEY (user_id)
            REFERENCES users(id) ON DELETE CASCADE,
        CONSTRAINT fk_bud_cat  FOREIGN KEY (category_id)
            REFERENCES categories(id) ON DELETE CASCADE
    ) ENGINE=InnoDB
    """,
]

# Default categories seeded per new user
_DEFAULT_CATEGORIES = [
    ("Salary",        "income",  "#22C58B", "💵"),
    ("Freelance",     "income",  "#4F6EF7", "💻"),
    ("Investment",    "income",  "#A78BFA", "📈"),
    ("Food",          "expense", "#F05C5C", "🍔"),
    ("Groceries",     "expense", "#F59E0B", "🛒"),
    ("Transport",     "expense", "#3B82F6", "🚗"),
    ("Shopping",      "expense", "#EC4899", "🛍️"),
    ("Entertainment", "expense", "#8B5CF6", "🎬"),
    ("Rent",          "expense", "#EF4444", "🏠"),
    ("Utilities",     "expense", "#06B6D4", "⚡"),
    ("Health",        "expense", "#10B981", "🏥"),
    ("Education",     "expense", "#F97316", "📚"),
    ("Other",         "expense", "#9CA3AF", "📦"),
]


def create_tables() -> None:
    """Execute all DDL statements to ensure schema is up to date."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        for stmt in _DDL_STATEMENTS:
            cur.execute(stmt)
        conn.commit()
    finally:
        conn.close()


# =============================================================================
# USER OPERATIONS
# =============================================================================

def create_user(username: str, email: str, password: str,
                full_name: str = "") -> Dict[str, Any]:
    """
    Register a new user.
    Returns {"success": True, "user_id": int} or {"success": False, "error": str}
    """
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO users (username, email, password_hash, full_name)
               VALUES (%s, %s, %s, %s)""",
            (username, email, hashed, full_name),
        )
        user_id = cur.lastrowid
        # Seed default categories
        for name, cat_type, color, icon in _DEFAULT_CATEGORIES:
            cur.execute(
                """INSERT IGNORE INTO categories
                   (user_id, name, type, color, icon, is_default)
                   VALUES (%s, %s, %s, %s, %s, 1)""",
                (user_id, name, cat_type, color, icon),
            )
        conn.commit()
        return {"success": True, "user_id": user_id}
    except Error as e:
        conn.rollback()
        if e.errno == 1062:   # Duplicate entry
            return {"success": False, "error": "Username or email already exists."}
        return {"success": False, "error": str(e)}
    finally:
        conn.close()


def verify_user(username: str, password: str) -> Optional[Dict[str, Any]]:
    """
    Verify login credentials.
    Returns user dict on success, None on failure.
    """
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(
            "SELECT * FROM users WHERE username=%s AND is_active=1",
            (username,),
        )
        user = cur.fetchone()
        if user and bcrypt.checkpw(password.encode(), user["password_hash"].encode()):
            # Update last_login
            cur.execute(
                "UPDATE users SET last_login=%s WHERE id=%s",
                (datetime.now(), user["id"]),
            )
            conn.commit()
            return user
        return None
    finally:
        conn.close()


def get_user_by_id(user_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a user record by primary key."""
    conn = get_connection()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT * FROM users WHERE id=%s", (user_id,))
        return cur.fetchone()
    finally:
        conn.close()


def update_password(user_id: int, new_password: str) -> bool:
    """Hash and update the user's password."""
    hashed = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "UPDATE users SET password_hash=%s WHERE id=%s",
            (hashed, user_id),
        )
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()


# =============================================================================
# CATEGORY OPERATIONS
# =============================================================================

def get_categories(user_id: int,
                   cat_type: Optional[str] = None) -> pd.DataFrame:
    """Return all categories for a user, optionally filtered by type."""
    sql = "SELECT * FROM categories WHERE user_id=%s"
    params: list = [user_id]
    if cat_type:
        sql += " AND type=%s"
        params.append(cat_type)
    sql += " ORDER BY type, name"
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()


def add_category(user_id: int, name: str, cat_type: str,
                 color: str = "#4F6EF7", icon: str = "📦") -> bool:
    """Create a custom category. Returns True on success."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO categories (user_id, name, type, color, icon)
               VALUES (%s, %s, %s, %s, %s)""",
            (user_id, name, cat_type, color, icon),
        )
        conn.commit()
        return True
    except Error:
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_category(category_id: int, user_id: int) -> bool:
    """Delete a non-default category owned by user_id."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """DELETE FROM categories
               WHERE id=%s AND user_id=%s AND is_default=0""",
            (category_id, user_id),
        )
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()


# =============================================================================
# TRANSACTION OPERATIONS
# =============================================================================

def get_transactions(user_id: int,
                     start_date: Optional[str] = None,
                     end_date: Optional[str] = None,
                     category_id: Optional[int] = None,
                     txn_type: Optional[str] = None) -> pd.DataFrame:
    """
    Fetch transactions for a user with optional filters.
    Joins category name and icon for display convenience.
    """
    sql = """
        SELECT
            t.id, t.date, t.description, t.amount, t.type,
            t.payment_mode, t.notes, t.created_at,
            COALESCE(c.name, 'Uncategorised') AS category,
            COALESCE(c.color, '#9CA3AF')      AS category_color,
            COALESCE(c.icon,  '📦')           AS category_icon
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s
    """
    params: list = [user_id]
    if start_date:
        sql += " AND t.date >= %s"
        params.append(start_date)
    if end_date:
        sql += " AND t.date <= %s"
        params.append(end_date)
    if category_id:
        sql += " AND t.category_id = %s"
        params.append(category_id)
    if txn_type:
        sql += " AND t.type = %s"
        params.append(txn_type)
    sql += " ORDER BY t.date DESC, t.id DESC"

    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params=params)
        if not df.empty:
            df["date"] = pd.to_datetime(df["date"])
        return df
    finally:
        conn.close()


def add_transaction(user_id: int, date: str, description: str,
                    amount: float, txn_type: str,
                    category_id: Optional[int] = None,
                    payment_mode: str = "Cash",
                    notes: str = "") -> bool:
    """Insert a single transaction. Returns True on success."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO transactions
               (user_id, category_id, date, description, amount, type,
                payment_mode, notes)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s)""",
            (user_id, category_id, date, description,
             amount, txn_type, payment_mode, notes),
        )
        conn.commit()
        return True
    except Error:
        conn.rollback()
        return False
    finally:
        conn.close()


def update_transaction(txn_id: int, user_id: int,
                       date: str, description: str,
                       amount: float, txn_type: str,
                       category_id: Optional[int],
                       payment_mode: str,
                       notes: str) -> bool:
    """Update an existing transaction owned by user_id."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """UPDATE transactions
               SET date=%s, description=%s, amount=%s, type=%s,
                   category_id=%s, payment_mode=%s, notes=%s
               WHERE id=%s AND user_id=%s""",
            (date, description, amount, txn_type,
             category_id, payment_mode, notes, txn_id, user_id),
        )
        conn.commit()
        return cur.rowcount == 1
    except Error:
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_transaction(txn_id: int, user_id: int) -> bool:
    """Delete a transaction owned by user_id."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM transactions WHERE id=%s AND user_id=%s",
            (txn_id, user_id),
        )
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()


def bulk_insert_transactions(user_id: int,
                             rows: List[Dict[str, Any]]) -> int:
    """
    Bulk-insert a list of transaction dicts.
    Each dict must have keys: date, description, amount, type,
    and optionally: category_id, payment_mode, notes.
    Returns the number of rows inserted.
    """
    conn = get_connection()
    try:
        cur = conn.cursor()
        sql = """
            INSERT INTO transactions
                (user_id, category_id, date, description,
                 amount, type, payment_mode, notes)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        data = [
            (
                user_id,
                r.get("category_id"),
                r["date"],
                r.get("description", ""),
                float(r["amount"]),
                r["type"],
                r.get("payment_mode", "Cash"),
                r.get("notes", ""),
            )
            for r in rows
        ]
        cur.executemany(sql, data)
        conn.commit()
        return cur.rowcount
    except Error:
        conn.rollback()
        return 0
    finally:
        conn.close()


# =============================================================================
# BUDGET OPERATIONS
# =============================================================================

def get_budgets(user_id: int, month: str) -> pd.DataFrame:
    """
    Return budgets for a user in the given month (YYYY-MM).
    Includes category name, icon, colour, and the actual spend.
    """
    sql = """
        SELECT
            b.id, b.category_id, b.month, b.amount AS budget_amount,
            c.name AS category, c.icon, c.color,
            COALESCE(ABS(SUM(t.amount)), 0) AS spent
        FROM budgets b
        JOIN categories c ON b.category_id = c.id
        LEFT JOIN transactions t
            ON  t.user_id      = b.user_id
            AND t.category_id  = b.category_id
            AND DATE_FORMAT(t.date, '%%Y-%%m') = b.month
            AND t.type = 'expense'
        WHERE b.user_id = %s AND b.month = %s
        GROUP BY b.id, b.category_id, b.month, b.amount,
                 c.name, c.icon, c.color
        ORDER BY c.name
    """
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn, params=[user_id, month])
    finally:
        conn.close()


def upsert_budget(user_id: int, category_id: int,
                  month: str, amount: float) -> bool:
    """Insert or update a monthly budget limit."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO budgets (user_id, category_id, month, amount)
               VALUES (%s, %s, %s, %s)
               ON DUPLICATE KEY UPDATE amount=%s, updated_at=NOW()""",
            (user_id, category_id, month, amount, amount),
        )
        conn.commit()
        return True
    except Error:
        conn.rollback()
        return False
    finally:
        conn.close()


def delete_budget(budget_id: int, user_id: int) -> bool:
    """Remove a budget entry."""
    conn = get_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "DELETE FROM budgets WHERE id=%s AND user_id=%s",
            (budget_id, user_id),
        )
        conn.commit()
        return cur.rowcount == 1
    finally:
        conn.close()


# =============================================================================
# ANALYTICS HELPERS
# =============================================================================

def get_monthly_summary(user_id: int) -> pd.DataFrame:
    """
    Return month-by-month income, expense, and savings for a user.
    Used by dashboard and ML models.
    """
    sql = """
        SELECT
            DATE_FORMAT(date, '%%Y-%%m')                         AS month,
            SUM(CASE WHEN type='income'  THEN  amount ELSE 0 END) AS income,
            SUM(CASE WHEN type='expense' THEN  ABS(amount) ELSE 0 END) AS expense
        FROM transactions
        WHERE user_id = %s
        GROUP BY month
        ORDER BY month
    """
    conn = get_connection()
    try:
        df = pd.read_sql(sql, conn, params=[user_id])
        if not df.empty:
            df["savings"] = df["income"] - df["expense"]
        return df
    finally:
        conn.close()


def get_category_spend(user_id: int,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> pd.DataFrame:
    """Category-wise total spend for the given period."""
    sql = """
        SELECT
            COALESCE(c.name, 'Uncategorised') AS category,
            COALESCE(c.color, '#9CA3AF')      AS color,
            COALESCE(c.icon,  '📦')           AS icon,
            SUM(ABS(t.amount))                AS total_spent,
            COUNT(*)                          AS txn_count
        FROM transactions t
        LEFT JOIN categories c ON t.category_id = c.id
        WHERE t.user_id = %s AND t.type = 'expense'
    """
    params: list = [user_id]
    if start_date:
        sql += " AND t.date >= %s"
        params.append(start_date)
    if end_date:
        sql += " AND t.date <= %s"
        params.append(end_date)
    sql += " GROUP BY category, color, icon ORDER BY total_spent DESC"
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()


# =============================================================================
# BOOTSTRAP — call create_tables() when this module is first imported
# =============================================================================
try:
    create_tables()
except Exception as _boot_err:
    # Surface a friendly message instead of crashing the whole app
    import warnings
    warnings.warn(
        f"[database.py] Could not connect to MySQL: {_boot_err}\n"
        "Set DB_HOST / DB_USER / DB_PASSWORD / DB_NAME env vars.",
        RuntimeWarning,
    )
