from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3, datetime


app = Flask(__name__)
app.secret_key = 'happyicecream'  # 好きなランダムな文字列

@app.route('/add', methods=['GET', 'POST'])
def add_item():
    if not is_logged_in():
        return redirect(url_for('login'))
    message = None
    if request.method == 'POST':
        name = request.form['name']  # 入力された商品名を取得
        quantity = int(request.form['quantity'])  # 入力された数量を取得（int型に変換）
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()

        # すでに同じ商品名があるかチェック
        cursor.execute('SELECT id FROM items WHERE name = ?', (name,))
        item = cursor.fetchone()
        if item:
            # 既存アイテムの場合：在庫を加算
            item_id = item[0]
            cursor.execute('SELECT quantity FROM inventory WHERE item_id = ?', (item_id,))
            inv = cursor.fetchone()
            if inv:
                current_quantity = inv[0]
                new_quantity = current_quantity + quantity
                cursor.execute('UPDATE inventory SET quantity = ? WHERE item_id = ?', (new_quantity, item_id))
            else:
                # inventoryテーブルにまだ登録がない場合は新規登録
                cursor.execute('INSERT INTO inventory (item_id, quantity) VALUES (?, ?)', (item_id, quantity))
            conn.commit()
            # --- 操作履歴に追加 ---
            insert_log(
                item_id=item_id,                # 商品ID
                quantity_change=quantity,       # 追加した数量
                action='add',                   # アクション名（例: 'add'）
                user_id=session.get('user_id')  # 現在ログイン中のユーザーID
            )
            conn.close()
            return redirect(url_for('index'))
        else:
            # 新しい商品を追加
            cursor.execute('INSERT INTO items (name) VALUES (?)', (name,))
            item_id = cursor.lastrowid
            cursor.execute('INSERT INTO inventory (item_id, quantity) VALUES (?, ?)', (item_id, quantity))
            conn.commit()
            # --- 操作履歴に追加 ---
            insert_log(
                item_id=item_id,
                quantity_change=quantity,
                action='add_new',               # 新規追加は区別したい場合
                user_id=session.get('user_id')
            )
            conn.close()
            return redirect(url_for('index'))
    return render_template('add_item.html', message=message)

@app.route('/update_quantity/<int:item_id>/<action>', methods=['POST'])
def update_quantity(item_id, action):
    if not is_logged_in():
        return redirect(url_for('login'))
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    # 現在の在庫数を取得
    cursor.execute('SELECT quantity FROM inventory WHERE item_id = ?', (item_id,))
    result = cursor.fetchone()
    if result:
        current_quantity = result[0]
    else:
        # 在庫データがなければ0で新規登録
        current_quantity = 0
        cursor.execute('INSERT INTO inventory (item_id, quantity) VALUES (?, ?)', (item_id, 0))
        conn.commit()

    # アクションごとに増減を計算
    if action == 'plus':
        new_quantity = current_quantity + 1
        quantity_change = 1    # 1個増やす
    elif action == 'minus':
        new_quantity = max(current_quantity - 1, 0)
        quantity_change = -1   # 1個減らす
    else:
        new_quantity = current_quantity
        quantity_change = 0    # 変化なし

    # 在庫数を更新
    cursor.execute('UPDATE inventory SET quantity = ? WHERE item_id = ?', (new_quantity, item_id))
    conn.commit()
    conn.close()
    # --- 操作履歴に追加 ---
    insert_log(
        item_id=item_id,                # 商品ID
        quantity_change=quantity_change,# 増減数
        action=action,                  # アクション名（'plus' or 'minus'）
        user_id=session.get('user_id')  # ログインユーザーID
    )
    return redirect(url_for('index'))


@app.route('/delete/<int:item_id>', methods=['POST'])
def delete_item(item_id):
    if not is_logged_in():
        return redirect(url_for('login'))
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    # 削除フラグを立てる（実際のデータは消さない）
    cursor.execute('UPDATE items SET delete_flag = 1 WHERE id = ?', (item_id,))
    conn.commit()
    conn.close()
    # --- 操作履歴に追加 ---
    insert_log(
        item_id=item_id,                # 商品ID
        quantity_change=0,              # 削除時は0で記録
        action='delete',                # アクション名
        user_id=session.get('user_id')  # ログインユーザーID
    )
    return redirect(url_for('index'))




def get_inventory_list():
    if not is_logged_in():
        return redirect(url_for('login'))
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

def is_logged_in():
    return 'user_id' in session

@app.route('/')
def index():
    #loginしてなかったらログイン画面へ
    if not is_logged_in():
        return redirect(url_for('login'))
    inventory_list = get_inventory_list()
    return render_template('index.html', inventory_list=inventory_list)


#在庫履歴操作履歴
@app.route('/logs')
def show_log():
    if not is_logged_in():
        return redirect(url_for('login'))
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT 
            log_inventory.id, 
            log_inventory.time_log, 
            users.name as user_name,
            log_inventory.action,
            log_inventory.quantity_change,
            items.name as item_name
        FROM log_inventory
        LEFT JOIN users ON log_inventory.user_id = users.id
        LEFT JOIN items ON log_inventory.item_id = items.id
        ORDER BY log_inventory.time_log DESC
        LIMIT 100
    ''')
    logs = cursor.fetchall()
    conn.close()
    log_list = []
    for row in logs:
        log_list.append({
            'id': row[0],
            'time_log': row[1],
            'user_name': row[2],
            'action': row[3],
            'quantity_change': row[4],
            'item_name': row[5],
        })
    return render_template('logs.html', log_list=log_list)


#ユーザー登録画面
@app.route('/register', methods=['GET', 'POST'])
def register():
    if not is_logged_in():
        return redirect(url_for('login'))
    # 「owner」か「staff」以外はTOPへ戻す
    if session.get('role') not in ['owner', 'staff']:
        return redirect(url_for('index'))  # または「権限がありません」画面でもOK
    message = None
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        role = request.form['role'] if 'role' in request.form else 'parttime'
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM users WHERE name = ?', (name,))
        if cursor.fetchone():
            message = 'このユーザー名は既に登録されています。'
            conn.close()
        else:
            cursor.execute(
                'INSERT INTO users (name, password, role) VALUES (?, ?, ?)',
                (name, password, role)
            )
            conn.commit()
            conn.close()
            return redirect(url_for('index'))
    return render_template('register.html', message=message)


#login画面
@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():  # ←追加（ログイン済みなら/にリダイレクト）
        return redirect(url_for('index'))
    message = None
    if request.method == 'POST':
        name = request.form['name']
        password = request.form['password']
        conn = sqlite3.connect('inventory.db')
        cursor = conn.cursor()
        cursor.execute('SELECT id, role FROM users WHERE name = ? AND password = ?', (name, password))
        user = cursor.fetchone()
        conn.close()
        if user:
            session['user_id'] = user[0]
            session['user_name'] = name
            session['role'] = user[1]
            return redirect(url_for('index'))
        else:
            message = "ユーザー名またはパスワードが違います"
    return render_template('login.html', message=message)


#ログアウト
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

# 操作履歴（log_inventory）に新しいログを追加する関数
def insert_log(item_id, quantity_change, action, user_id):
    # データベースに接続
    conn = sqlite3.connect('inventory.db')
    cursor = conn.cursor()
    # 現在時刻を「YYYY-MM-DD HH:MM:SS」形式で取得
    now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    # log_inventoryテーブルにログを追加
    cursor.execute(
        'INSERT INTO log_inventory (item_id, quantity_change, action, user_id, time_log) VALUES (?, ?, ?, ?, ?)',
        (item_id, quantity_change, action, user_id, now)
    )
    # 変更を保存
    conn.commit()
    # データベース接続を閉じる
    conn.close()


if __name__ == '__main__':
    app.run(debug=True)
