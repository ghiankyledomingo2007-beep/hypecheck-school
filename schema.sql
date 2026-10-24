    -- HypeCheck database schema for MySQL 8.0.16 or newer
-- (CHECK constraints are enforced by MySQL from 8.0.16).
-- Six core tables: users, categories, wishlist_items, decision_logs, expenses, monthly_budgets.

CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    google_sub VARCHAR(255) CHARACTER SET ascii COLLATE ascii_bin UNIQUE,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE categories (
    category_id INT AUTO_INCREMENT PRIMARY KEY,
    category_name VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE wishlist_items (
    wishlist_item_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    category_id INT NOT NULL,
    item_name VARCHAR(150) NOT NULL,
    estimated_price DECIMAL(12, 2) NOT NULL,
    product_url VARCHAR(2048),
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    wait_until DATETIME NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'waiting',
    UNIQUE KEY uq_wishlist_user_item (user_id, wishlist_item_id),
    CONSTRAINT chk_wishlist_price CHECK (estimated_price >= 0),
    CONSTRAINT chk_wishlist_status CHECK (status IN ('waiting', 'bought', 'skipped')),
    CONSTRAINT chk_wishlist_wait CHECK (wait_until > created_at),
    CONSTRAINT fk_wishlist_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_wishlist_category FOREIGN KEY (category_id) REFERENCES categories(category_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE decision_logs (
    decision_id INT AUTO_INCREMENT PRIMARY KEY,
    wishlist_item_id INT NOT NULL,
    decision VARCHAR(20) NOT NULL,
    reflection TEXT,
    decided_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    new_wait_until DATETIME,
    CONSTRAINT chk_decision_value CHECK (decision IN ('buy', 'skip', 'wait_longer')),
    CONSTRAINT chk_decision_deadline CHECK (
        (decision = 'wait_longer' AND new_wait_until IS NOT NULL AND new_wait_until > decided_at)
        OR (decision IN ('buy', 'skip') AND new_wait_until IS NULL)
    ),
    CONSTRAINT fk_decision_item FOREIGN KEY (wishlist_item_id) REFERENCES wishlist_items(wishlist_item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE expenses (
    expense_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    category_id INT NOT NULL,
    wishlist_item_id INT UNIQUE,
    description VARCHAR(255) NOT NULL,
    amount DECIMAL(12, 2) NOT NULL,
    expense_date DATE NOT NULL,
    notes TEXT,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT chk_expense_amount CHECK (amount > 0),
    CONSTRAINT fk_expense_user FOREIGN KEY (user_id) REFERENCES users(user_id),
    CONSTRAINT fk_expense_category FOREIGN KEY (category_id) REFERENCES categories(category_id),
    -- a purchase expense must belong to the same user as the wishlist item it came from
    CONSTRAINT fk_expense_wishlist_owner FOREIGN KEY (user_id, wishlist_item_id)
        REFERENCES wishlist_items(user_id, wishlist_item_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE monthly_budgets (
    budget_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    budget_year INT NOT NULL,
    budget_month INT NOT NULL,
    budget_amount DECIMAL(12, 2) NOT NULL,
    UNIQUE KEY uq_budget_user_month (user_id, budget_year, budget_month),
    CONSTRAINT chk_budget_year CHECK (budget_year > 0),
    CONSTRAINT chk_budget_month CHECK (budget_month BETWEEN 1 AND 12),
    CONSTRAINT chk_budget_amount CHECK (budget_amount >= 0),
    CONSTRAINT fk_budget_user FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

-- Account support shared with the personal version; existing school rows are preserved.
CREATE TABLE IF NOT EXISTS sessions (
    session_id CHAR(64) CHARACTER SET ascii COLLATE ascii_bin PRIMARY KEY,
    user_id INT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    CONSTRAINT fk_session_user FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;

CREATE TABLE IF NOT EXISTS login_attempts (
    attempt_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    identifier VARCHAR(320) CHARACTER SET utf8mb4 COLLATE utf8mb4_bin NOT NULL,
    attempted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_login_attempts_recent (identifier, attempted_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
