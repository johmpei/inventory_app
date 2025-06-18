from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

@app.route('/add', methods=['GET', 'POST'])
def add_item():
    message = None
    if request.method == 'POST':
        name = request.form['name']
        quantity = int(request.form['quantity'])
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()

        # 1. すでに同じ商品名があるかチェック
        cursor.execute('SELECT id FROM items WHERE name = ?', (name,))
        item = cursor.fetchone()
        if item:
            # 2. 既存アイテムなら在庫数を取得し加算
            item_id = item[0]
            cursor.execute('SELECT quantity FROM inventory WHERE item_id = ?', (item_id,))
            inv = cursor.fetchone()
            if inv:
                current_quantity = inv[0]
                new_quantity = current_quantity + quantity
                cursor.execute('UPDATE inventory SET quantity = ? WHERE item_id = ?', (new_quantity, item_id))
            else:
                # 万一inventoryが空ならinsert
                cursor.execute('INSERT INTO inventory (item_id, quantity) VALUES (?, ?)', (item_id, quantity))
            conn.commit()
            message = f'「{name}」は既にあるので在庫を{quantity}個加算しました。'
            conn.close()
            return redirect(url_for('index'))
        else:
            # 3. なければ新規追加
            cursor.execute('INSERT INTO items (name) VALUES (?)', (name,))
            item_id = cursor.lastrowid
            cursor.execute('INSERT INTO inventory (item_id, quantity) VALUES (?, ?)', (item_id, quantity))
            conn.commit()
            conn.close()
            return redirect(url_for('index'))
    return render_template('add_item.html', message=message)



def get_inventory_list():
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT items.id, items.name, inventory.quantity
        FROM items
        LEFT JOIN inventory ON items.id = inventory.item_id
        WHERE items.delete_flag = 0
        ORDER BY items.id
    ''')
    results = cursor.fetchall()
    conn.close()
    inventory_list = []
    for row in results:
        inventory_list.append({
            'id': row[0],
            'name': row[1],
            'quantity': row[2] if row[2] is not None else 0
        })
    return inventory_list


# 削除ボタンを作った
@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute('UPDATE items SET delete_flag = 1 WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))



# 在庫数を増減させるエンドポイント
@app.route('/update_quantity/<int:item_id>/<action>', methods=['POST'])
def update_quantity(item_id, action):
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    # まず現在の数量を取得
    cursor.execute('SELECT quantity FROM inventory WHERE item_id = ?', (item_id,))
    result = cursor.fetchone()
    if result:
        current_quantity = result[0]
    else:
        # inventoryにデータがなければ0として登録
        current_quantity = 0
        cursor.execute('INSERT INTO inventory (item_id, quantity) VALUES (?, ?)', (item_id, 0))
        conn.commit()
    
    # 数量を増減
    if action == 'plus':
        new_quantity = current_quantity + 1
    elif action == 'minus':
        new_quantity = max(current_quantity - 1, 0)
    else:
        new_quantity = current_quantity  # 念のため

    cursor.execute('UPDATE inventory SET quantity = ? WHERE item_id = ?', (new_quantity, item_id))
    conn.commit()
    conn.close()
    return redirect(url_for('index'))

@app.route('/')
def index():
    inventory_list = get_inventory_list()
    return render_template('index.html', inventory_list=inventory_list)

if __name__ == '__main__':
    app.run(debug=True)
