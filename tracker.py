import os
import re
import sqlite3
import datetime
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL")
DB_NAME = "prices.db"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "en-IN,en;q=0.9,en-US;q=0.8",
}

def get_db():
    return sqlite3.connect(DB_NAME)

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tracked_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            url TEXT NOT NULL,
            currency TEXT DEFAULT '₹',
            target_price REAL NOT NULL,
            last_price REAL,
            last_checked TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

def add_product(name: str, url: str, target_price: float, currency: str = "₹"):
    """Add a new item with designated currency."""
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO tracked_items (name, url, currency, target_price, last_price, last_checked)
        VALUES (?, ?, ?, ?, NULL, ?)
    """, (name, url, currency, target_price, datetime.datetime.now()))
    conn.commit()
    conn.close()
    print(f"\n[+] Added '{name}' (Target: {currency}{target_price:,.2f}) to tracking list.")

def list_products():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, currency, target_price, last_price FROM tracked_items")
    items = cursor.fetchall()
    conn.close()

    print("\n--- Tracked Products ---")
    if not items:
        print("No items currently being tracked.")
        return

    for item in items:
        curr = item[2] or "₹"
        last = f"{curr}{item[4]:,.2f}" if item[4] is not None else "Not checked yet"
        print(f"[{item[0]}] {item[1]} | Target: {curr}{item[3]:,.2f} | Last Seen: {last}")

def fetch_live_price(url: str):
    """Extracts both numeric price and auto-detected currency symbol."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            return None, None

        soup = BeautifulSoup(response.text, "html.parser")
        selectors = [
            ".a-price-whole", ".price_color", ".product-price",
            "[data-price]", ".current-price", ".price", ".offer-price"
        ]

        raw_price_text = None
        for selector in selectors:
            match = soup.select_one(selector)
            if match:
                raw_price_text = match.get_text()
                break

        if not raw_price_text:
            # Match currency symbol and number pattern
            match = re.search(r"([₹\$€£]|Rs\.?|INR)\s?(\d+(?:,\d+)*(?:\.\d{2})?)", response.text)
            if match:
                detected_currency = match.group(1)
                cleaned_price = float(re.sub(r"[^\d.]", "", match.group(2).replace(",", "")))
                return cleaned_price, detected_currency

        if raw_price_text:
            # Extract currency if present in class text
            curr_match = re.search(r"([₹\$€£]|Rs\.?|INR)", raw_price_text)
            currency_symbol = curr_match.group(1) if curr_match else "₹"
            cleaned_price = float(re.sub(r"[^\d.]", "", raw_price_text.replace(",", "")))
            return cleaned_price, currency_symbol

    except Exception as e:
        print(f"Scrape warning for {url}: {e}")
    
    return None, None

def check_all_prices():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, url, currency, target_price, last_price FROM tracked_items")
    items = cursor.fetchall()
    conn.close()

    if not items:
        print("\n[!] No products in database to check.")
        return

    print("\n=== Running Price Check Cycle ===")
    for item_id, name, url, default_currency, target_price, last_price in items:
        current_price, detected_currency = fetch_live_price(url)
        currency = detected_currency or default_currency or "₹"

        if current_price is None:
            print(f"[-] {name}: Could not extract price from page.")
            continue

        print(f"[*] {name}: Current = {currency}{current_price:,.2f} | Target = {currency}{target_price:,.2f}")

        if current_price <= target_price:
            print(f"🚨 PRICE DROP ALERT: {name} is now {currency}{current_price:,.2f}!")

        # Update last price & currency in database
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("UPDATE tracked_items SET last_price = ?, currency = ?, last_checked = ? WHERE id = ?",
                       (current_price, currency, datetime.datetime.now(), item_id))
        conn.commit()
        conn.close()

def main():
    init_db()
    while True:
        print("\n===============================")
        print("    PRICE TRACKER (MULTI-CURRENCY)")
        print("===============================")
        print("1. Check prices for all tracked products")
        print("2. Add a new product to track")
        print("3. List all tracked products")
        print("4. Exit")
        choice = input("Select an option (1-4): ").strip()

        if choice == "1":
            check_all_prices()
        elif choice == "2":
            name = input("Enter product name: ").strip()
            url = input("Enter product URL: ").strip()
            curr = input("Enter currency symbol (default ₹, or $, €, £): ").strip() or "₹"
            try:
                target = float(input(f"Enter target alert price (in {curr}): ").strip())
                add_product(name, url, target, curr)
            except ValueError:
                print("[!] Invalid price format.")
        elif choice == "3":
            list_products()
        elif choice == "4":
            print("Exiting tracker.")
            break
        else:
            print("Invalid choice, select 1-4.")

if __name__ == "__main__":
    main()