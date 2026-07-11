-- =============================================================================
-- PERSONAL FINANCE DASHBOARD — MySQL Database Schema
-- =============================================================================
-- Run this file once to bootstrap the database:
--   mysql -u root -p < schema.sql
-- =============================================================================

CREATE DATABASE IF NOT EXISTS finance_dashboard
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE finance_dashboard;

-- =============================================================================
-- 1. USERS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS users (
    id            INT          AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    email         VARCHAR(120) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,             -- bcrypt hash
    full_name     VARCHAR(100),
    currency      VARCHAR(10)  NOT NULL DEFAULT 'INR',
    is_active     TINYINT(1)   NOT NULL DEFAULT 1,
    created_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
                               ON UPDATE CURRENT_TIMESTAMP,
    last_login    DATETIME,
    INDEX idx_users_username (username),
    INDEX idx_users_email    (email)
) ENGINE=InnoDB;

-- =============================================================================
-- 2. CATEGORIES TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS categories (
    id          INT          AUTO_INCREMENT PRIMARY KEY,
    user_id     INT          NOT NULL,
    name        VARCHAR(80)  NOT NULL,
    type        ENUM('income','expense') NOT NULL DEFAULT 'expense',
    color       VARCHAR(10)  DEFAULT '#4F6EF7',      -- hex colour for charts
    icon        VARCHAR(10)  DEFAULT '📦',
    is_default  TINYINT(1)   NOT NULL DEFAULT 0,     -- 1 = system default
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY  uq_user_category (user_id, name),
    CONSTRAINT fk_cat_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =============================================================================
-- 3. TRANSACTIONS TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS transactions (
    id            INT           AUTO_INCREMENT PRIMARY KEY,
    user_id       INT           NOT NULL,
    category_id   INT,                               -- NULL = uncategorised
    date          DATE          NOT NULL,
    description   VARCHAR(255),
    amount        DECIMAL(15,2) NOT NULL,            -- positive=income, negative=expense
    type          ENUM('income','expense') NOT NULL,
    payment_mode  VARCHAR(50)   DEFAULT 'Cash',      -- UPI / Cash / Card / Net Banking
    notes         TEXT,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                                ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_txn_user   (user_id),
    INDEX idx_txn_date   (date),
    INDEX idx_txn_type   (type),
    INDEX idx_txn_cat    (category_id),
    CONSTRAINT fk_txn_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_txn_cat  FOREIGN KEY (category_id)
        REFERENCES categories(id) ON DELETE SET NULL
) ENGINE=InnoDB;

-- =============================================================================
-- 4. BUDGET TABLE
-- =============================================================================
CREATE TABLE IF NOT EXISTS budgets (
    id          INT           AUTO_INCREMENT PRIMARY KEY,
    user_id     INT           NOT NULL,
    category_id INT           NOT NULL,
    month       CHAR(7)       NOT NULL,              -- format: 2025-01
    amount      DECIMAL(15,2) NOT NULL,
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP
                              ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY  uq_budget (user_id, category_id, month),
    CONSTRAINT fk_bud_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE,
    CONSTRAINT fk_bud_cat  FOREIGN KEY (category_id)
        REFERENCES categories(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =============================================================================
-- 5. SESSIONS TABLE  (server-side session store)
-- =============================================================================
CREATE TABLE IF NOT EXISTS sessions (
    id          VARCHAR(64)  PRIMARY KEY,            -- UUID token
    user_id     INT          NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at  DATETIME     NOT NULL,
    ip_address  VARCHAR(45),
    CONSTRAINT fk_sess_user FOREIGN KEY (user_id)
        REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB;

-- =============================================================================
-- SEED: default admin user  (password: admin123)
-- bcrypt hash of "admin123" — regenerate in production!
-- =============================================================================
INSERT IGNORE INTO users (username, email, password_hash, full_name, is_active)
VALUES (
    'admin',
    'admin@finance.local',
    '$2b$12$KIXWb0WVJRkXNqOpD3vR5uFvCJSMV1dSXKv.pZ.mL5vwJoGFnpX8W',
    'Admin User',
    1
);

INSERT IGNORE INTO users (username, email, password_hash, full_name, is_active)
VALUES (
    'demo',
    'demo@finance.local',
    '$2b$12$XT0FEUdO.KgkfLB5hR7iLOR6wMvX6JRe2IxDqTYg1VhGQQ5lFJM/u',
    'Demo User',
    1
);

-- =============================================================================
-- SEED: default categories for admin (user_id = 1)
-- =============================================================================
INSERT IGNORE INTO categories (user_id, name, type, color, icon, is_default) VALUES
(1, 'Salary',        'income',  '#22C58B', '💵', 1),
(1, 'Freelance',     'income',  '#4F6EF7', '💻', 1),
(1, 'Investment',    'income',  '#A78BFA', '📈', 1),
(1, 'Food',          'expense', '#F05C5C', '🍔', 1),
(1, 'Groceries',     'expense', '#F59E0B', '🛒', 1),
(1, 'Transport',     'expense', '#3B82F6', '🚗', 1),
(1, 'Shopping',      'expense', '#EC4899', '🛍️', 1),
(1, 'Entertainment', 'expense', '#8B5CF6', '🎬', 1),
(1, 'Rent',          'expense', '#EF4444', '🏠', 1),
(1, 'Utilities',     'expense', '#06B6D4', '⚡', 1),
(1, 'Health',        'expense', '#10B981', '🏥', 1),
(1, 'Education',     'expense', '#F97316', '📚', 1),
(1, 'Other',         'expense', '#9CA3AF', '📦', 1);

-- =============================================================================
-- SEED: default categories for demo user (user_id = 2)
-- =============================================================================
INSERT IGNORE INTO categories (user_id, name, type, color, icon, is_default) VALUES
(2, 'Salary',        'income',  '#22C58B', '💵', 1),
(2, 'Freelance',     'income',  '#4F6EF7', '💻', 1),
(2, 'Investment',    'income',  '#A78BFA', '📈', 1),
(2, 'Food',          'expense', '#F05C5C', '🍔', 1),
(2, 'Groceries',     'expense', '#F59E0B', '🛒', 1),
(2, 'Transport',     'expense', '#3B82F6', '🚗', 1),
(2, 'Shopping',      'expense', '#EC4899', '🛍️', 1),
(2, 'Entertainment', 'expense', '#8B5CF6', '🎬', 1),
(2, 'Rent',          'expense', '#EF4444', '🏠', 1),
(2, 'Utilities',     'expense', '#06B6D4', '⚡', 1),
(2, 'Health',        'expense', '#10B981', '🏥', 1),
(2, 'Education',     'expense', '#F97316', '📚', 1),
(2, 'Other',         'expense', '#9CA3AF', '📦', 1);
