import sqlite3
import os
import hashlib
import json
from datetime import datetime

DATABASE_NAME = "idealize.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE_NAME)
    conn.row_factory = sqlite3.Row
    # Enable foreign keys
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    conn = get_db_connection()
    c = conn.cursor()

    # 1. Users
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Admin', 'Operator'))
        )
    ''')

    # 2. Suppliers
    c.execute('''
        CREATE TABLE IF NOT EXISTS suppliers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            contact_phone TEXT,
            contact_email TEXT,
            address TEXT
        )
    ''')

    # 3. Materials
    c.execute('''
        CREATE TABLE IF NOT EXISTS materials (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            type_thickness_color TEXT,
            unit TEXT NOT NULL CHECK(unit IN ('Plate', 'Sheet', 'Meter', 'Unit')),
            width_cm REAL,
            height_cm REAL,
            area_cm2 REAL,
            area_m2 REAL,
            notes TEXT,
            cost_per_cm2 REAL DEFAULT 0.0,
            cost_per_m2 REAL DEFAULT 0.0,
            loss_factor_override REAL
        )
    ''')

    # 4. Purchases
    c.execute('''
        CREATE TABLE IF NOT EXISTS purchases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            material_id INTEGER NOT NULL,
            supplier_id INTEGER NOT NULL,
            purchase_date TEXT NOT NULL,
            cost_price REAL NOT NULL,
            quantity REAL DEFAULT 1.0,
            lot_code TEXT,
            FOREIGN KEY(material_id) REFERENCES materials(id),
            FOREIGN KEY(supplier_id) REFERENCES suppliers(id)
        )
    ''')

    # 5. Customers
    c.execute('''
        CREATE TABLE IF NOT EXISTS customers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            phone TEXT,
            email TEXT,
            address TEXT
        )
    ''')

    # 6. Global Settings (Key-Value)
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        )
    ''')

    # 7. Pricing Profiles
    c.execute('''
        CREATE TABLE IF NOT EXISTS pricing_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            markup_multiplier REAL,
            profit_margin_percent REAL
        )
    ''')

    # 8. Quotes
    c.execute('''
        CREATE TABLE IF NOT EXISTS quotes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('Draft', 'Sent', 'Approved', 'Rejected')),
            total_cost REAL NOT NULL,
            total_price REAL NOT NULL,
            pricing_profile_id INTEGER,
            version INTEGER DEFAULT 1,
            original_quote_id INTEGER,
            FOREIGN KEY(customer_id) REFERENCES customers(id),
            FOREIGN KEY(pricing_profile_id) REFERENCES pricing_profiles(id),
            FOREIGN KEY(original_quote_id) REFERENCES quotes(id)
        )
    ''')

    # 9. Quote Items
    c.execute('''
        CREATE TABLE IF NOT EXISTS quote_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_id INTEGER NOT NULL,
            material_id INTEGER,
            description TEXT,
            width_cm REAL,
            height_cm REAL,
            machine_time_min REAL DEFAULT 0,
            manual_time_min REAL DEFAULT 0,
            extra_costs REAL DEFAULT 0,
            item_cost REAL NOT NULL,
            item_price REAL NOT NULL,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY(quote_id) REFERENCES quotes(id),
            FOREIGN KEY(material_id) REFERENCES materials(id)
        )
    ''')

    # 10. Products (Catalog)
    c.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            is_kit BOOLEAN DEFAULT 0,
            kit_discount_type TEXT CHECK(kit_discount_type IN ('Fixed', 'Percentage', NULL)),
            kit_discount_value REAL DEFAULT 0,
            base_price REAL,
            image_path TEXT
        )
    ''')

    # 11. Product Components (For variations and non-kits)
    c.execute('''
        CREATE TABLE IF NOT EXISTS product_components (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            product_id INTEGER NOT NULL,
            variation_name TEXT DEFAULT 'Standard',
            material_id INTEGER NOT NULL,
            width_cm REAL,
            height_cm REAL,
            machine_time_min REAL DEFAULT 0,
            manual_time_min REAL DEFAULT 0,
            extra_costs REAL DEFAULT 0,
            FOREIGN KEY(product_id) REFERENCES products(id),
            FOREIGN KEY(material_id) REFERENCES materials(id)
        )
    ''')

    # 12. Kit Items (For linking products inside a kit)
    c.execute('''
        CREATE TABLE IF NOT EXISTS kit_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kit_product_id INTEGER NOT NULL,
            component_product_id INTEGER NOT NULL,
            quantity INTEGER DEFAULT 1,
            FOREIGN KEY(kit_product_id) REFERENCES products(id),
            FOREIGN KEY(component_product_id) REFERENCES products(id)
        )
    ''')

    # 13. Orders (Kanban)
    c.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            quote_id INTEGER NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('To Do', 'In Production', 'In Finishing', 'Ready for Delivery', 'Completed')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            FOREIGN KEY(quote_id) REFERENCES quotes(id)
        )
    ''')

    conn.commit()

    # Seed initial data
    seed_initial_data(conn)

    conn.close()


def seed_initial_data(conn):
    c = conn.cursor()

    def hash_password(password):
        salt = os.urandom(16)
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return salt.hex(), pwd_hash.hex()

    # Check if admin exists
    c.execute("SELECT id FROM users WHERE username = 'admin'")
    if not c.fetchone():
        salt, pwd_hash = hash_password('admin')
        c.execute("INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
                  ('admin', pwd_hash, salt, 'Admin'))

    # Check if operator exists
    c.execute("SELECT id FROM users WHERE username = 'operator'")
    if not c.fetchone():
        salt, pwd_hash = hash_password('operator')
        c.execute("INSERT INTO users (username, password_hash, salt, role) VALUES (?, ?, ?, ?)",
                  ('operator', pwd_hash, salt, 'Operator'))

    # Default settings
    default_settings = {
        'global_loss_factor_percent': '10',
        'labor_minute_cost': '0.50',
        'machine_monthly_cost': '0',
        'machine_useful_life_months': '60',
        'machine_energy_kwh': '0',
        'kwh_cost': '0',
        'machine_monthly_hours': '160',
        'machine_maintenance_cost': '0',
        'other_fixed_costs': '0',
        'machine_minute_cost_cached': '0.00',
        'tax_rate_percent': '0'
    }

    for k, v in default_settings.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # Default Pricing Profiles
    c.execute("SELECT id FROM pricing_profiles WHERE name = 'Varejo (100% Margem)'")
    if not c.fetchone():
        c.execute("INSERT INTO pricing_profiles (name, markup_multiplier, profit_margin_percent) VALUES (?, ?, ?)",
                  ('Varejo (100% Margem)', 2.0, 100))

    c.execute("SELECT id FROM pricing_profiles WHERE name = 'Atacado (60% Margem)'")
    if not c.fetchone():
        c.execute("INSERT INTO pricing_profiles (name, markup_multiplier, profit_margin_percent) VALUES (?, ?, ?)",
                  ('Atacado (60% Margem)', 1.6, 60))

    conn.commit()

if __name__ == "__main__":
    init_db()
    print("Database initialized successfully.")
