"""
seed.py — Database seeding script
"""

import os
import datetime
from app import app, db, User, Order, Payment, StatusHistory, Setting
from werkzeug.security import generate_password_hash
from sqlalchemy import text

with app.app_context():

    # ---- ADD ALL MISSING COLUMNS ----
    # Safely adds any columns our app needs that don't exist in CustomFlow.sql
    with db.engine.connect() as conn:
        migrations = [
            # users table
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(512);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_email BOOLEAN DEFAULT TRUE;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS notify_sms BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS phone VARCHAR(255);",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE;",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS customer_type VARCHAR(50) DEFAULT 'individual';",
            "ALTER TABLE users ADD COLUMN IF NOT EXISTS influencer_status VARCHAR(20);",
            # orders table
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS customer_notes TEXT;",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS admin_notes TEXT;",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS rush_fee NUMERIC(8,2) DEFAULT 0;",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS rush_approved BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS has_cleaning_fee BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS inbound_tracking VARCHAR(255);",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS outbound_tracking VARCHAR(255);",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS outbound_carrier VARCHAR(255);",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS booking_fee_paid BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT NOW();",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS is_archived BOOLEAN DEFAULT FALSE;",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS archived_at TIMESTAMP;",
            "ALTER TABLE orders ADD COLUMN IF NOT EXISTS order_number VARCHAR(20);",
            # payments table
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS external_txn_id VARCHAR(255);",
            "ALTER TABLE payments ADD COLUMN IF NOT EXISTS method VARCHAR(255);",
            # revisions table
            "ALTER TABLE revisions ADD COLUMN IF NOT EXISTS charge_amount NUMERIC(8,2) DEFAULT 0;",
            "ALTER TABLE revisions ADD COLUMN IF NOT EXISTS mockup_id INTEGER;",
            "ALTER TABLE revisions ADD COLUMN IF NOT EXISTS completed BOOLEAN DEFAULT FALSE;",
            # invoices table — create then add new columns
            """CREATE TABLE IF NOT EXISTS invoices (
                id SERIAL PRIMARY KEY,
                order_id INTEGER REFERENCES orders(id),
                type VARCHAR(255),
                label VARCHAR(255),
                amount NUMERIC(10,2),
                status VARCHAR(255) DEFAULT 'draft',
                file_url TEXT,
                uploaded_at TIMESTAMP DEFAULT NOW(),
                sent_at TIMESTAMP
            );""",
            "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS doc_type VARCHAR(20) DEFAULT 'invoice';",
            "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS doc_number VARCHAR(50);",
            "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS line_items TEXT;",
            "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS subtotal NUMERIC(10,2);",
            "ALTER TABLE invoices ADD COLUMN IF NOT EXISTS notes TEXT;",
            # faqs table
            """CREATE TABLE IF NOT EXISTS faqs (
                id SERIAL PRIMARY KEY,
                question TEXT,
                answer TEXT,
                sort_order INTEGER DEFAULT 0
            );""",
            # pricing_tiers table
            """CREATE TABLE IF NOT EXISTS pricing_tiers (
                id SERIAL PRIMARY KEY,
                name TEXT,
                price_from INTEGER DEFAULT 0,
                price_label TEXT,
                description TEXT,
                sort_order INTEGER DEFAULT 0,
                is_active BOOLEAN DEFAULT TRUE
            );""",
            # settings table
            """CREATE TABLE IF NOT EXISTS settings (
                key VARCHAR(255) PRIMARY KEY,
                value TEXT
            );""",
            # Set order ID sequence to start at 1001 (only takes effect if no orders exist yet,
            # or bumps it up if current max is below 1000)
            "SELECT setval('orders_id_seq', GREATEST(1000, (SELECT COALESCE(MAX(id), 1000) FROM orders)));",
        ]
        for sql in migrations:
            try:
                conn.execute(text(sql))
                print(f"  ✓ {sql.strip()[:60]}...")
            except Exception as e:
                print(f"  - Skipped ({e})")
        conn.commit()

    print("All migrations applied.")

    # Create any remaining tables our models define
    db.create_all()
    print("Tables created/verified.")

    # ---- CREATE ADMIN (BUFFY) ----
    try:
        buffy = User.query.filter_by(email='admin@copeaesthetic.com').first()
        if not buffy:
            buffy = User(
                email         = 'admin@copeaesthetic.com',
                name          = 'Buffy Cope',
                role          = 'owner',
                phone         = '(919) 295-2569',
                password_hash = generate_password_hash('admin123'),
                notify_email  = True,
                notify_sms    = False,
            )
            db.session.add(buffy)
            db.session.flush()
            print("Created admin: admin@copeaesthetic.com / admin123")
        else:
            buffy.password_hash = generate_password_hash('admin123')
            db.session.flush()
            print("Admin exists — password updated.")
    except Exception as e:
        print(f"Admin error: {e}")
        db.session.rollback()
        raise

    # ---- CREATE SAMPLE CUSTOMER ----
    try:
        customer = User.query.filter_by(email='customer@email.com').first()
        if not customer:
            customer = User(
                email         = 'customer@email.com',
                name          = 'James Carter',
                role          = 'customer',
                phone         = '(803) 555-1234',
                password_hash = generate_password_hash('customer123'),
                notify_email  = True,
            )
            db.session.add(customer)
            db.session.flush()
            print("Created customer: customer@email.com / customer123")
        else:
            customer.password_hash = generate_password_hash('customer123')
            db.session.flush()
            print("Customer exists — password updated.")
    except Exception as e:
        print(f"Customer error: {e}")
        db.session.rollback()
        raise

    # ---- CREATE SAMPLE ORDERS ----
    try:
        order_count = db.session.execute(text("SELECT COUNT(*) FROM orders")).scalar()
        if order_count == 0:
            db.session.execute(text("""
                INSERT INTO orders (user_id, pricing_tier, item_type, status,
                    is_rush, rush_approved, booking_fee_paid, customer_notes,
                    admin_notes, created_at, updated_at)
                VALUES
                (:uid, 'premium', 'Sneakers', 'painting',
                    false, false, true,
                    'Deep space purples, blues and pinks. Constellation patterns.',
                    'Jordan 1 Bred. Galaxy theme.',
                    '2026-03-01', NOW()),
                (:uid, 'standard', 'Sneakers', 'free_waitlist',
                    false, false, false,
                    'Simple custom Vans — Buffy the Vampire Slayer theme.',
                    '',
                    '2026-03-15', NOW())
            """), {'uid': customer.id})
            print("Created 2 sample orders.")
        else:
            print(f"Orders already exist ({order_count} total).")
    except Exception as e:
        print(f"Orders error: {e}")

    # ---- DEFAULT SETTINGS ----
    try:
        defaults = {
            'booking_status':  'waitlist',
            'booked_until':    '2026-05-18',
            'booking_message': 'Currently booked through May 18, 2026 — Join the waitlist!',
            'prod_start':      'May 18, 2026',
        }
        for key, value in defaults.items():
            db.session.execute(text(
                "INSERT INTO settings (key, value) VALUES (:k, :v) ON CONFLICT (key) DO NOTHING"
            ), {'k': key, 'v': value})
        print("Settings applied.")
    except Exception as e:
        print(f"Settings error: {e}")

    try:
        db.session.commit()
        print("\n✅ Seed complete!")
        print("  Admin:    admin@copeaesthetic.com / admin123")
        print("  Customer: customer@email.com / customer123")
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ Commit failed: {e}")
