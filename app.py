import io
import os
import uuid
import qrcode
import pymysql.cursors
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, session, flash, send_file
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = os.urandom(24)  # 請修改為隨機字串以確保安全
app.permanent_session_lifetime = timedelta(minutes=30)  # 設定閒置 30 分鐘自動登出

# ==========================================
# MySQL 資料庫連線設定
# ==========================================
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',  # MySQL 預設帳號
    'password': 'wendy940704',  # 【請填入你的 MySQL 密碼，若無則留空】
    'database': 'ExhibitionTicketSystem',
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor  # 讓查詢結果變成 Dictionary (例如 row['title'])
}


def get_db_connection():
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as e:
        print(f"資料庫連線失敗: {e}")
        return None


# 輔助函式：檢查是否為管理員
def is_admin():
    return session.get('role') == 'admin'


# Context Processor: 讓所有 Template 都能讀到購物車數量
@app.context_processor
def inject_cart_count():
    cart = session.get('cart', [])
    return dict(cart_count=len(cart))


# ==========================================
# 前台路由 (Front-end)
# ==========================================

# --- 首頁：展覽列表 (含搜尋 & 時間檢查) ---
@app.route('/')
def index():
    keyword = request.args.get('q', '')  # 取得搜尋關鍵字

    conn = get_db_connection()
    if not conn: return "DB Connection Error", 500
    try:
        with conn.cursor() as cursor:
            if keyword:
                # 搜尋標題或地點
                sql = "SELECT * FROM Exhibitions WHERE status = 'Published' AND (title LIKE %s OR location LIKE %s)"
                search_term = f"%{keyword}%"
                cursor.execute(sql, (search_term, search_term))
            else:
                cursor.execute("SELECT * FROM Exhibitions WHERE status = 'Published'")

            exhibitions = cursor.fetchall()

        # ★ 傳入 now 讓前端判斷是否顯示「已結束」
        return render_template('index.html', exhibitions=exhibitions, keyword=keyword, now=datetime.now())
    finally:
        conn.close()


# --- 註冊 ---
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        password = request.form.get('password')
        phone = request.form.get('phone')

        if not name or not email or not password:
            flash('請填寫完整資訊')
            return redirect(url_for('register'))

        hashed_pw = generate_password_hash(password)

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                # 預設 role 為 'user'
                cursor.execute(
                    "INSERT INTO Members (name, email, password_hash, phone, role) VALUES (%s, %s, %s, %s, 'user')",
                    (name, email, hashed_pw, phone)
                )
            conn.commit()
            flash('註冊成功，請登入！')
            return redirect(url_for('login'))
        except Exception as e:
            flash('註冊失敗 (Email 可能已存在)')
            print(e)
        finally:
            conn.close()
    return render_template('register.html')


# --- 登入 (含權限判斷) ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')

        conn = get_db_connection()
        try:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM Members WHERE email = %s", (email,))
                user = cursor.fetchone()

            if user and check_password_hash(user['password_hash'], password):
                # 登入成功，設定 Session
                session.permanent = True  # 啟用自動過期
                session['user_id'] = user['member_id']
                session['user_name'] = user['name']
                session['role'] = user['role']  # 儲存身分

                # 根據身分導向不同頁面
                if user['role'] == 'admin':
                    return redirect(url_for('admin_dashboard'))
                else:
                    return redirect(url_for('index'))
            else:
                flash('帳號或密碼錯誤')
        finally:
            conn.close()
    return render_template('login.html')


# --- 登出 ---
@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))


# --- 展覽詳細頁 (加入購物車 - 含嚴格過期檢查) ---
@app.route('/exhibition/<int:id>', methods=['GET', 'POST'])
def detail(id):
    conn = get_db_connection()
    if not conn: return "DB Error", 500

    try:
        with conn.cursor() as cursor:
            # === POST: 加入購物車 ===
            if request.method == 'POST':
                try:
                    quantity = int(request.form.get('quantity', 1))
                except ValueError:
                    quantity = 1

                if quantity <= 0:
                    flash("購買數量必須大於 0")
                    return redirect(request.url)

                session_id = request.form.get('session_id')

                # ★ 後端防呆：嚴格檢查過期
                # 同時查詢「場次時間」與「展覽結束日期」
                sql = """
                    SELECT S.session_time, E.end_date 
                    FROM Sessions S
                    JOIN Exhibitions E ON S.exhibition_id = E.exhibition_id
                    WHERE S.session_id = %s
                """
                cursor.execute(sql, (session_id,))
                row = cursor.fetchone()

                if not row:
                    flash("❌ 錯誤：找不到場次資訊")
                    return redirect(request.url)

                # 1. 檢查展覽是否已結束
                if row['end_date'] < datetime.now().date():
                    flash("❌ 很抱歉，此展覽活動已完全結束，無法購票！")
                    return redirect(request.url)

                # 2. 檢查場次時間是否已過
                if row['session_time'] < datetime.now():
                    flash("❌ 錯誤：該場次時間已過，無法購買！")
                    return redirect(request.url)

                # 建立商品物件
                item_template = {
                    'exhibition_id': id,
                    'exhibition_title': request.form.get('exhibition_title'),
                    'session_id': session_id,
                    'session_time_str': request.form.get('session_time_str'),
                    'ticket_type_id': request.form.get('ticket_type'),
                    'ticket_name': request.form.get('ticket_name'),
                    'price': float(request.form.get('price'))
                }

                cart = session.get('cart', [])
                # 依數量重複加入
                for _ in range(quantity):
                    cart.append(item_template.copy())

                session['cart'] = cart
                flash(f'已將 {quantity} 張票加入購物車 🛒')
                return redirect(url_for('index'))

            # === GET: 顯示頁面 ===
            cursor.execute("SELECT * FROM Exhibitions WHERE exhibition_id = %s", (id,))
            exhibition = cursor.fetchone()

            cursor.execute("SELECT * FROM Sessions WHERE exhibition_id = %s ORDER BY session_time", (id,))
            sessions = cursor.fetchall()

            cursor.execute("SELECT * FROM TicketTypes WHERE exhibition_id = %s", (id,))
            ticket_types = cursor.fetchall()

            if not exhibition: return "找不到該展覽", 404

            # ★ 傳入 now 給前端做按鈕停用判斷
            return render_template('detail.html',
                                   ex=exhibition,
                                   sessions=sessions,
                                   types=ticket_types,
                                   now=datetime.now())

    finally:
        conn.close()


# --- 查看購物車 ---
@app.route('/cart')
def view_cart():
    cart = session.get('cart', [])
    total_price = sum(item['price'] for item in cart)
    return render_template('cart.html', cart=cart, total=total_price)


# --- 清空購物車 ---
@app.route('/clear_cart')
def clear_cart():
    session.pop('cart', None)
    return redirect(url_for('view_cart'))


# --- 結帳 (交易處理 + 原子性扣庫存) ---
@app.route('/checkout', methods=['POST'])
def checkout():
    if 'user_id' not in session:
        flash('請先登入才能結帳')
        return redirect(url_for('login'))

    cart = session.get('cart', [])
    if not cart:
        flash('購物車是空的')
        return redirect(url_for('index'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            total_amount = sum(item['price'] for item in cart)

            # 1. 建立訂單
            cursor.execute("INSERT INTO Orders (member_id, total_amount, status) VALUES (%s, %s, 'Paid')",
                           (session['user_id'], total_amount))
            order_id = cursor.lastrowid  # MySQL 取得 ID 的方式

            # 2. 建立支付紀錄
            cursor.execute(
                "INSERT INTO Payments (order_id, payment_method, amount, status) VALUES (%s, 'Credit Card', %s, 'Success')",
                (order_id, total_amount))

            # 3. 處理每一張票 (扣庫存 + 建票)
            for item in cart:
                session_id = item['session_id']
                ticket_type_id = item['ticket_type_id']

                # [關鍵] 扣除庫存，若庫存不足會影響行數為 0 (防止超賣)
                cursor.execute("""
                    UPDATE Sessions 
                    SET capacity = capacity - 1 
                    WHERE session_id = %s AND capacity > 0
                """, (session_id,))

                if cursor.rowcount == 0:
                    raise Exception(f"很抱歉，場次「{item['session_time_str']}」已額滿，無法購買。")

                ticket_uuid = str(uuid.uuid4())
                cursor.execute("""
                    INSERT INTO Tickets (ticket_uuid, order_id, ticket_type_id, session_id, status)
                    VALUES (%s, %s, %s, %s, 'Unused')
                """, (ticket_uuid, order_id, ticket_type_id, session_id))

        conn.commit()
        session.pop('cart', None)
        flash(f'結帳成功！共購買 {len(cart)} 張票券')
        return redirect(url_for('my_tickets'))

    except Exception as e:
        conn.rollback()
        flash(f'結帳失敗: {e}')
        return redirect(url_for('view_cart'))
    finally:
        conn.close()


# --- 我的票券 ---
@app.route('/my_tickets')
def my_tickets():
    if 'user_id' not in session: return redirect(url_for('login'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT T.ticket_uuid, E.title, S.session_time, TT.name, T.status
                FROM Tickets T
                JOIN Orders O ON T.order_id = O.order_id
                JOIN TicketTypes TT ON T.ticket_type_id = TT.ticket_type_id
                JOIN Sessions S ON T.session_id = S.session_id
                JOIN Exhibitions E ON TT.exhibition_id = E.exhibition_id
                WHERE O.member_id = %s
                ORDER BY O.order_date DESC
            """
            cursor.execute(sql, (session['user_id'],))
            tickets = cursor.fetchall()
            return render_template('my_tickets.html', tickets=tickets)
    finally:
        conn.close()


# --- QR Code API ---
@app.route('/qrcode/<uuid>')
def serve_qrcode(uuid):
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(uuid)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white").convert('RGB')
    buf = io.BytesIO()
    img.save(buf, format='PNG')
    buf.seek(0)
    return send_file(buf, mimetype='image/png')


# --- 現場核銷 API (輸入 PIN 碼) ---
@app.route('/api/use_ticket', methods=['POST'])
def api_use_ticket():
    data = request.get_json()
    uuid = data.get('uuid')
    input_pin = data.get('pin')

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            sql = """
                SELECT T.status, E.validation_pin 
                FROM Tickets T
                JOIN TicketTypes TT ON T.ticket_type_id = TT.ticket_type_id
                JOIN Exhibitions E ON TT.exhibition_id = E.exhibition_id
                WHERE T.ticket_uuid = %s
            """
            cursor.execute(sql, (uuid,))
            row = cursor.fetchone()

            if not row: return {"success": False, "message": "找不到票券"}, 404

            if row['status'] == 'Used':
                return {"success": False, "message": "此票券已經使用過了"}

            if input_pin != row['validation_pin']:
                return {"success": False, "message": "核銷碼錯誤"}

            cursor.execute("UPDATE Tickets SET status = 'Used', used_at = NOW() WHERE ticket_uuid = %s", (uuid,))
            conn.commit()
            return {"success": True, "message": "驗證成功，歡迎入場！"}
    except Exception as e:
        conn.rollback()
        return {"success": False, "message": str(e)}, 500
    finally:
        conn.close()


# ==========================================
# 後台管理路由 (Admin Dashboard)
# ==========================================

@app.route('/admin')
def admin_dashboard():
    # 檢查是否為管理員
    if 'user_id' not in session or not is_admin():
        flash("權限不足，請以管理員身分登入")
        return redirect(url_for('login'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM Exhibitions ORDER BY exhibition_id DESC")
            exhibitions = cursor.fetchall()
        return render_template('admin/dashboard.html', exhibitions=exhibitions)
    finally:
        conn.close()


# --- 新增展覽 (自動新增主辦單位) ---
@app.route('/admin/create', methods=['GET', 'POST'])
def admin_create_exhibition():
    if not is_admin(): return redirect(url_for('index'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == 'POST':
                # 1. 處理主辦單位 (輸入名稱 -> 自動判斷ID)
                org_name = request.form['organizer_name'].strip()
                cursor.execute("SELECT organizer_id FROM Organizers WHERE name = %s", (org_name,))
                existing_org = cursor.fetchone()

                if existing_org:
                    organizer_id = existing_org['organizer_id']
                else:
                    cursor.execute("INSERT INTO Organizers (name) VALUES (%s)", (org_name,))
                    organizer_id = cursor.lastrowid

                # 2. 新增展覽
                cursor.execute("""
                    INSERT INTO Exhibitions (organizer_id, title, location, description, start_date, end_date, status, validation_pin)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    organizer_id,
                    request.form['title'],
                    request.form['location'],
                    request.form['description'],
                    request.form['start_date'],
                    request.form['end_date'],
                    request.form['status'],
                    request.form.get('validation_pin', '1234')
                ))
                conn.commit()
                flash(f'新增成功 (主辦: {org_name})')
                return redirect(url_for('admin_dashboard'))

            cursor.execute("SELECT * FROM Organizers")
            organizers = cursor.fetchall()
            return render_template('admin/create.html', organizers=organizers)
    finally:
        conn.close()


# --- 編輯展覽 (修改內容與上下架) ---
@app.route('/admin/edit/<int:id>', methods=['GET', 'POST'])
def admin_edit_exhibition(id):
    if not is_admin(): return redirect(url_for('index'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            # POST: 更新資料
            if request.method == 'POST':
                cursor.execute("""
                    UPDATE Exhibitions 
                    SET title=%s, location=%s, description=%s, 
                        start_date=%s, end_date=%s, status=%s, validation_pin=%s
                    WHERE exhibition_id=%s
                """, (
                    request.form['title'], request.form['location'], request.form['description'],
                    request.form['start_date'], request.form['end_date'], request.form['status'],
                    request.form['validation_pin'], id
                ))
                conn.commit()
                flash('展覽修改成功！')
                return redirect(url_for('admin_dashboard'))

            # GET: 顯示資料 (JOIN 主辦單位名稱)
            sql = """
                SELECT E.*, O.name as organizer_name 
                FROM Exhibitions E
                LEFT JOIN Organizers O ON E.organizer_id = O.organizer_id
                WHERE E.exhibition_id = %s
            """
            cursor.execute(sql, (id,))
            exhibition = cursor.fetchone()

            if not exhibition:
                flash('找不到該展覽')
                return redirect(url_for('admin_dashboard'))

            return render_template('admin/edit.html', ex=exhibition)
    finally:
        conn.close()


# --- 管理展覽細項 (場次與票種) ---
@app.route('/admin/manage/<int:id>', methods=['GET', 'POST'])
def admin_manage_exhibition(id):
    if not is_admin(): return redirect(url_for('index'))

    conn = get_db_connection()
    try:
        with conn.cursor() as cursor:
            if request.method == 'POST':
                # 新增場次
                if 'add_session' in request.form:
                    cursor.execute("INSERT INTO Sessions (exhibition_id, session_time, capacity) VALUES (%s, %s, %s)",
                                   (id, request.form['session_time'], request.form['capacity']))
                    flash('場次已新增')

                # 新增票種
                if 'add_ticket_type' in request.form:
                    cursor.execute("INSERT INTO TicketTypes (exhibition_id, name, price) VALUES (%s, %s, %s)",
                                   (id, request.form['name'], request.form['price']))
                    flash('票種已新增')
                conn.commit()

            cursor.execute("SELECT * FROM Exhibitions WHERE exhibition_id = %s", (id,))
            exhibition = cursor.fetchone()
            cursor.execute("SELECT * FROM Sessions WHERE exhibition_id = %s", (id,))
            sessions = cursor.fetchall()
            cursor.execute("SELECT * FROM TicketTypes WHERE exhibition_id = %s", (id,))
            ticket_types = cursor.fetchall()
            return render_template('admin/manage.html', ex=exhibition, sessions=sessions, types=ticket_types)
    finally:
        conn.close()


if __name__ == '__main__':
    app.run(debug=True, port=5000)