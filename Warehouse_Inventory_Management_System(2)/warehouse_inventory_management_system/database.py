import os
import hashlib
import hmac
import secrets
import pandas as pd
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

load_dotenv()

def _config(include_database=True):
    cfg = {
        "host": os.getenv("MYSQL_HOST", "localhost"),
        "port": int(os.getenv("MYSQL_PORT", "3306")),
        "user": os.getenv("MYSQL_USER", "root"),
        "password": os.getenv("MYSQL_PASSWORD", "Root"),
        "charset": "utf8mb4",
        "use_unicode": True,
    }
    if include_database:
        cfg["database"] = os.getenv("MYSQL_DATABASE", "warehouse_inventory")
    return cfg

def get_connection():
    return mysql.connector.connect(**_config(True))

def initialize_database():
    # Create the configured database if it does not exist.
    cfg = _config(False)
    database = os.getenv("MYSQL_DATABASE", "warehouse_inventory")
    conn = mysql.connector.connect(**cfg)
    cur = conn.cursor()
    cur.execute(f"CREATE DATABASE IF NOT EXISTS `{database.replace('`', '')}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    cur.close()
    conn.close()

    conn = get_connection()
    cur = conn.cursor()
    statements = [
        """CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            full_name VARCHAR(120) NOT NULL,
            username VARCHAR(80) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            role ENUM('Admin','Storekeeper') NOT NULL DEFAULT 'Storekeeper',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB""",
        """CREATE TABLE IF NOT EXISTS categories (
            id INT AUTO_INCREMENT PRIMARY KEY,
            category_name VARCHAR(100) NOT NULL UNIQUE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB""",
        """CREATE TABLE IF NOT EXISTS products (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_name VARCHAR(150) NOT NULL,
            sku VARCHAR(80) NOT NULL UNIQUE,
            category_id INT NULL,
            quantity INT NOT NULL DEFAULT 0,
            reorder_level INT NOT NULL DEFAULT 10,
            bin_location VARCHAR(100) DEFAULT '',
            unit_price DECIMAL(12,2) NOT NULL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            CONSTRAINT fk_product_category FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
        ) ENGINE=InnoDB""",
        """CREATE TABLE IF NOT EXISTS stock_transactions (
            id INT AUTO_INCREMENT PRIMARY KEY,
            product_id INT NOT NULL,
            transaction_type ENUM('IN','OUT') NOT NULL,
            quantity INT NOT NULL,
            user_id INT NULL,
            notes VARCHAR(255) DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_tx_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
            CONSTRAINT fk_tx_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
        ) ENGINE=InnoDB""",
        """CREATE TABLE IF NOT EXISTS orders (
            id INT AUTO_INCREMENT PRIMARY KEY,
            order_code VARCHAR(100) NOT NULL UNIQUE,
            order_type ENUM('Supplier Shipment','Customer Dispatch') NOT NULL,
            counterparty VARCHAR(150) DEFAULT '',
            product_id INT NOT NULL,
            quantity INT NOT NULL,
            order_date DATE NOT NULL,
            status ENUM('Pending','In Transit','Completed','Cancelled') NOT NULL DEFAULT 'Pending',
            notes VARCHAR(255) DEFAULT '',
            created_by INT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            CONSTRAINT fk_order_product FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT,
            CONSTRAINT fk_order_user FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
        ) ENGINE=InnoDB""",
    ]
    for sql in statements:
        cur.execute(sql)
    conn.commit()
    cur.close()
    conn.close()
    return True

def _hash_password(password, salt=None):
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 260000).hex()
    return f"pbkdf2_sha256${salt}${digest}"

def _verify_password(password, stored):
    try:
        algorithm, salt, digest = stored.split("$", 2)
        if algorithm != "pbkdf2_sha256":
            return False
        calculated = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 260000).hex()
        return hmac.compare_digest(calculated, digest)
    except (ValueError, AttributeError):
        return False

def get_user_count():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    count = cur.fetchone()[0]
    cur.close()
    conn.close()
    return count

def create_first_admin(full_name, username, password):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    if cur.fetchone()[0] != 0:
        cur.close()
        conn.close()
        raise ValueError("An account already exists.")
    cur.execute("INSERT INTO users (full_name, username, password_hash, role) VALUES (%s,%s,%s,'Admin')",
                (full_name, username, _hash_password(password)))
    conn.commit()
    cur.close()
    conn.close()

def authenticate_user(username, password):
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT id, full_name, username, password_hash, role FROM users WHERE username=%s", (username,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    if row and _verify_password(password, row["password_hash"]):
        row.pop("password_hash", None)
        return row
    return None

def _read_df(sql, params=None):
    conn = get_connection()
    try:
        return pd.read_sql(sql, conn, params=params)
    finally:
        conn.close()

def get_dashboard_stats():
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    cur.execute("SELECT COUNT(*) AS product_types, COALESCE(SUM(quantity),0) AS units_in_stock FROM products")
    p = cur.fetchone()
    cur.execute("SELECT COUNT(*) AS categories FROM categories")
    c = cur.fetchone()
    cur.close()
    conn.close()
    return {"product_types": int(p["product_types"]), "units_in_stock": int(p["units_in_stock"]), "categories": int(c["categories"])}

def get_low_stock_products():
    return _read_df("""SELECT id, product_name, sku, quantity, reorder_level, bin_location
                       FROM products WHERE quantity <= reorder_level ORDER BY quantity ASC, product_name ASC""")

def get_products():
    return _read_df("""SELECT p.id, p.product_name, p.sku, COALESCE(c.category_name,'Uncategorized') AS category_name,
                       p.quantity, p.reorder_level, p.bin_location, p.unit_price, p.created_at, p.updated_at
                       FROM products p LEFT JOIN categories c ON p.category_id=c.id
                       ORDER BY p.product_name""")

def get_categories():
    return _read_df("SELECT id, category_name, created_at FROM categories ORDER BY category_name")

def add_category(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO categories (category_name) VALUES (%s)", (name,))
    conn.commit()
    cur.close()
    conn.close()

def add_product(name, sku, category_id, quantity, reorder_level, bin_location, unit_price):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""INSERT INTO products (product_name, sku, category_id, quantity, reorder_level, bin_location, unit_price)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (name, sku, category_id, quantity, reorder_level, bin_location, unit_price))
    pid = cur.lastrowid
    conn.commit()
    cur.close()
    conn.close()
    return pid

def update_product(pid, name, sku, category_id, reorder_level, bin_location, unit_price):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""UPDATE products SET product_name=%s, sku=%s, category_id=%s, reorder_level=%s,
                   bin_location=%s, unit_price=%s WHERE id=%s""",
                (name, sku, category_id, reorder_level, bin_location, unit_price, pid))
    conn.commit()
    cur.close()
    conn.close()

def delete_product(pid):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM products WHERE id=%s", (pid,))
    conn.commit()
    cur.close()
    conn.close()

def record_stock_transaction(product_id, transaction_type, quantity, user_id, notes=""):
    if transaction_type not in ("IN", "OUT"):
        raise ValueError("Transaction type must be IN or OUT.")
    if int(quantity) <= 0:
        raise ValueError("Quantity must be greater than zero.")
    conn = get_connection()
    try:
        conn.start_transaction()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT quantity FROM products WHERE id=%s FOR UPDATE", (product_id,))
        row = cur.fetchone()
        if not row:
            raise ValueError("Product not found.")
        current = int(row["quantity"])
        if transaction_type == "OUT" and int(quantity) > current:
            raise ValueError(f"Not enough stock. Available quantity: {current}.")
        new_qty = current + int(quantity) if transaction_type == "IN" else current - int(quantity)
        cur.execute("UPDATE products SET quantity=%s WHERE id=%s", (new_qty, product_id))
        cur.execute("""INSERT INTO stock_transactions (product_id, transaction_type, quantity, user_id, notes)
                       VALUES (%s,%s,%s,%s,%s)""",
                    (product_id, transaction_type, int(quantity), user_id, notes))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_transactions(limit=None):
    sql = """SELECT t.id, t.created_at, p.product_name, p.sku, t.transaction_type, t.quantity,
                    COALESCE(u.username,'Deleted user') AS username, t.notes
             FROM stock_transactions t JOIN products p ON p.id=t.product_id
             LEFT JOIN users u ON u.id=t.user_id ORDER BY t.created_at DESC, t.id DESC"""
    if limit:
        sql += " LIMIT %s"
        return _read_df(sql, params=(int(limit),))
    return _read_df(sql)

def get_orders():
    return _read_df("""SELECT o.id, o.order_code, o.order_type, o.counterparty, p.product_name, p.sku,
                       o.quantity, o.order_date, o.status, o.notes, COALESCE(u.username,'Deleted user') AS created_by,
                       o.created_at
                       FROM orders o JOIN products p ON p.id=o.product_id
                       LEFT JOIN users u ON u.id=o.created_by
                       ORDER BY o.created_at DESC, o.id DESC""")

def add_order(order_code, order_type, counterparty, product_id, quantity, order_date, notes, created_by):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""INSERT INTO orders (order_code, order_type, counterparty, product_id, quantity, order_date, notes, created_by)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
                (order_code, order_type, counterparty, product_id, quantity, order_date, notes, created_by))
    conn.commit()
    cur.close()
    conn.close()

def update_order_status(order_id, status):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE orders SET status=%s WHERE id=%s", (status, order_id))
    conn.commit()
    cur.close()
    conn.close()

def get_users():
    return _read_df("SELECT id, full_name, username, role, created_at FROM users ORDER BY created_at DESC")

def add_user(full_name, username, password, role):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO users (full_name, username, password_hash, role) VALUES (%s,%s,%s,%s)",
                (full_name, username, _hash_password(password), role))
    conn.commit()
    cur.close()
    conn.close()

def update_user_role(user_id, role):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("UPDATE users SET role=%s WHERE id=%s", (role, user_id))
    conn.commit()
    cur.close()
    conn.close()
