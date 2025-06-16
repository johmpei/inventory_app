from flask import Flask, render_template
import sqlite3

app = Flask(__name__)

# データベース接続用の関数
def get_inventory_list():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    # itemsとinventoryを結合して一覧を取得
    cursor.execute('''
        SELECT items.id, items.name, inventory.quantity
        FROM items
        LEFT JOIN inventory ON items.id = inventory.item_id
        ORDER BY items.id
    ''')
    results = cursor.fetchall()
    print("===========")
    print(results)

    conn.close()
    #データベースの接続の終わり

    # [{"id": 1, "name": "コーヒー豆", "quantity": 10}, ...] みたいなリストに変換
    inventory_list = []
    for row in results:
        inventory_list.append({
            'id': row[0],
            'name': row[1],
            'quantity': row[2] if row[2] is not None else 0  # quantityがNULLなら0に
        })
    return inventory_list

@app.route('/')
def index():
    inventory_list = get_inventory_list()
    return render_template('index.html', inventory_list=inventory_list)

if __name__ == '__main__':
    app.run(debug=True)
