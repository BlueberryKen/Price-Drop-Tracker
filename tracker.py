import os
import sqlite3
import datetime
import requests
from dotenv import load_dotenv

load_dotenv()
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DB_NAME = "prices.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tracked_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            target_price REAL NOT NULL,
            last_price REAL,
            last_checked TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def check_items():
    init_db()
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Seed sample item if empty
    cursor.execute("SELECT COUNT(*) FROM tracked_items")
    if cursor.fetchone()[0] == 0:
        cursor.execute("""
            INSERT INTO tracked_items (name, url, target_price, last_price, last_checked)
            VALUES (?, ?, ?, ?, ?)
        """, ("Gaming Headset", "https://example.com/item1", 99.99, 120.00, datetime.datetime.now()))
        conn.commit()
        print("[*] Sample tracking item created.")

    cursor.execute("SELECT name, target_price, last_price FROM tracked_items")
    items = cursor.fetchall()
    conn.close()

    for name, target, last in items:
        simulated_current_price = 89.99  # Simulated price drop below target
        print(f"Checking '{name}': Current = ${simulated_current_price} | Target = ${target}")
        if simulated_current_price <= target:
            print(f"🚨 PRICE DROP ALERT: {name} dropped to ${simulated_current_price}!")

if __name__ == "__main__":
    print("=== Price Drop Tracker Started ===")
    check_items()