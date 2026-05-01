import sqlite3
from datetime import datetime
import os
from flask import Flask, send_file, jsonify, request
from flask_cors import CORS
import threading
import time
import requests

def keep_alive():
    while True:
        time.sleep(840)
        try:
            requests.get("https://URL-YAKO-HALISI.onrender.com/api/health")
        except:
            pass

threading.Thread(target=keep_alive, daemon=True).start()
 
app = Flask(__name__)
CORS(app)  # Ruhusu maombi kutoka frontend yoyote
@app.route('/')
def home():
    return send_file('index.html')
 
# ============ DATABASE SETUP ============
def setup_database():
    conn = sqlite3.connect('restaurant.db')
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_number TEXT UNIQUE,
            customer_name TEXT,
            table_number TEXT,
            items TEXT,
            total_price REAL,
            payment_method TEXT,
            status TEXT,
            order_time TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS menu (
            id INTEGER PRIMARY KEY,
            name TEXT,
            category TEXT,
            price REAL,
            available INTEGER DEFAULT 1
        )
    ''')
    
    cursor.execute("SELECT COUNT(*) FROM menu")
    if cursor.fetchone()[0] == 0:
        default_menu = [
            ("Wali maharage", "Chakula", 2000),
            ("Wali Kuku", "Chakula", 2500),
            ("Wali Nyama", "Chakula", 2500),
            ("Wali dagaa", "Chakula", 2000),
            ("Pilau", "Chakula", 3000),
            ("Biriani", "Chakula", 3500),
            ("Sembe", "Chakula", 1500),
            ("Ndizi", "Chakula", 2500),
            ("Juice ya matunda", "Kinywaji", 500),
            ("Maji ndogo", "Kinywaji", 500),
            ("Maji kubwa", "Kinywaji", 1000),
            ("Fanta ndogo", "Kinywaji", 700),
            ("Fanta kubwa", "Kinywaji", 1200),
            ("Sprite ndogo", "Kinywaji", 700),
            ("Sprite kubwa", "Kinywaji", 1200),
            ("Novida ndogo", "Kinywaji", 700),
            ("Novida kubwa", "Kinywaji", 1200),
            ("Shany", "Kinywaji", 1500),
            ("Orange", "Kinywaji", 700),
            ("Energy", "Kinywaji", 700)
        ]
        for item in default_menu:
            cursor.execute("INSERT INTO menu (name, category, price) VALUES (?, ?, ?)", item)
    
    conn.commit()
    conn.close()
 
def get_db():
    conn = sqlite3.connect('restaurant.db')
    conn.row_factory = sqlite3.Row
    return conn
 
# ============ API ENDPOINTS ============
 
# 1. Pata Menu yote
@app.route('/api/menu', methods=['GET'])
def get_menu():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM menu WHERE available = 1 ORDER BY category, name")
    items = cursor.fetchall()
    conn.close()
    
    menu = [dict(item) for item in items]
    return jsonify({"success": True, "menu": menu})
 
# 2. Pata Menu kwa Category
@app.route('/api/menu/<category>', methods=['GET'])
def get_menu_by_category(category):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM menu WHERE category = ? AND available = 1", (category,))
    items = cursor.fetchall()
    conn.close()
    
    menu = [dict(item) for item in items]
    return jsonify({"success": True, "menu": menu})
 
# 3. Tuma Order mpya
@app.route('/api/orders', methods=['POST'])
def create_order():
    data = request.json
    
    # Validate data
    if not data or 'items' not in data or len(data['items']) == 0:
        return jsonify({"success": False, "error": "Hakuna vitu kwenye order!"}), 400
    
    customer_name = data.get('customer_name', 'Guest')
    table_number = data.get('table_number', 'Takeaway')
    items = data['items']  # List ya {"name": ..., "price": ...}
    payment_method = data.get('payment_method', 'Cash')
    
    # Hesabu total
    total_price = sum(item['price'] for item in items)
    
    # Unda order number
    order_number = datetime.now().strftime("%Y%m%d%H%M%S")
    
    # Badilisha items kuwa string
    items_str = ", ".join([f"{item['name']}(Tsh{item['price']})" for item in items])
    
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO orders (order_number, customer_name, table_number, items, 
                               total_price, payment_method, status, order_time)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (order_number, customer_name, table_number, items_str,
              total_price, payment_method, "Completed", datetime.now()))
        
        conn.commit()
        conn.close()
        
        return jsonify({
            "success": True,
            "message": "Order imesajiliwa!",
            "order": {
                "order_number": order_number,
                "customer_name": customer_name,
                "table_number": table_number,
                "items": items,
                "total_price": total_price,
                "payment_method": payment_method,
                "status": "Completed",
                "order_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
        })
    except Exception as e:
        conn.close()
        return jsonify({"success": False, "error": str(e)}), 500
 
# 4. Pata Orders zote (History)
@app.route('/api/orders', methods=['GET'])
def get_orders():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT * FROM orders ORDER BY order_time DESC
    ''')
    orders = cursor.fetchall()
    conn.close()
    
    orders_list = [dict(order) for order in orders]
    return jsonify({"success": True, "orders": orders_list})
 
# 5. Sales Report
@app.route('/api/sales-report', methods=['GET'])
def sales_report():
    conn = get_db()
    cursor = conn.cursor()
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Leo
    cursor.execute('''
        SELECT COUNT(*), SUM(total_price) FROM orders 
        WHERE DATE(order_time) = DATE(?)
    ''', (today,))
    row = cursor.fetchone()
    today_orders = row[0] or 0
    today_sales = row[1] or 0
    
    # Jumla yote
    cursor.execute("SELECT COUNT(*), SUM(total_price) FROM orders")
    row = cursor.fetchone()
    total_orders = row[0] or 0
    total_sales = row[1] or 0
    
    # Sales za wiki hii
    cursor.execute('''
        SELECT DATE(order_time) as date, COUNT(*) as count, SUM(total_price) as total
        FROM orders 
        WHERE order_time >= DATE('now', '-7 days')
        GROUP BY DATE(order_time)
        ORDER BY date DESC
    ''')
    weekly = cursor.fetchall()
    
    conn.close()
    
    return jsonify({
        "success": True,
        "report": {
            "today": {
                "date": today,
                "orders": today_orders,
                "sales": today_sales
            },
            "overall": {
                "total_orders": total_orders,
                "total_sales": total_sales
            },
            "weekly": [dict(row) for row in weekly]
        }
    })
 
# 6. Health check
@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({"status": "ok", "restaurant": "Om Restaurant"})
 
# ============ RUN ============
setup_database()
 
if __name__ == '__main__':
    app.run(debug=True)
