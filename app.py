'''
導入模組

Flask: 建立 Web 應用程序核心，負責路由分配與請求處理。
    render_template: 渲染 HTML 模板 (如 index.html)，並可傳遞後端變數 (如 user_name) 到前端顯示。
    request: 處理 HTTP 請求，主要用於接收前端傳來的 JSON 資料 (request.json)，例如註冊與購票資訊。
    redirect, url_for: 用於網頁重定向，在此專案中用於「登出」後自動跳轉回首頁。
    session: 處理伺服器端的會話數據，用於記錄使用者的登入狀態 (user_id, user_name) 以便跨頁面存取。
    jsonify: 將 Python 的字典或列表轉換為 JSON 格式，作為 API (如 /api/exhibitions) 的回傳結果。

werkzeug.security: 提供密碼安全性功能。
    generate_password_hash: 註冊時將使用者輸入的明碼密碼加密成雜湊值，再存入資料庫。
    check_password_hash: 登入時驗證使用者輸入的密碼是否與資料庫中的雜湊值相符。

flask_cors:
    CORS: 處理跨來源資源共享 (Cross-Origin Resource Sharing)，允許前端瀏覽器跨網域請求後端 API。

mysql.connector:
    connect: 用於建立 Python 與 MySQL/MariaDB 資料庫的連線 (取代 Windows 環境常用的 pyodbc，跟學姊的不一樣)。
             因為這裡我是在自己的 Linux 虛擬機環境連接資料庫，要在 Linux 連接資料庫的話用它內建的 MariaDB 比較方便，目前我就是用這個 MariaDB 直接在 Terminal 做資料庫的操作 (ex. 創建資料表、新增資料等)
             未來用系上的機器的時候再看怎麼改設定
uuid:
    uuid4: 生成隨機且唯一的通用識別碼 (UUID)，在此專案中用於產生每一張票券獨一無二的 QR Code 碼 (ticket_uuid)。
'''

from flask import Flask, request, session, jsonify, render_template, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_cors import CORS
import mysql.connector
import uuid


app = Flask(__name__)
CORS(app)                           # 啟用 CORS，允許跨網域請求 (方便開發時前後端分離測試)
app.secret_key = 'kali_secret_key'  # 設定 Session 加密密鑰，用於保護使用者登入狀態

# -------------------------- 資料庫連線設定 ----------------------------
def conn():
    """
    建立與 MariaDB/MySQL 資料庫的連線。
    (在 Kali Linux 上通常使用 MariaDB，語法操作與 MySQL 相同。)
    """
    try:
        connect = mysql.connector.connect(
            host='127.0.0.1',       # 資料庫就在 Kali 本機上，所以使用本地端 IP
            user='admin',           # 我在 MariaDB 建立的帳號
            password='123456',      # 我在 MariaDB 建立的密碼
            database='ExhibitionDB' # 我在 MariaDB 建立的資料庫名稱
            # --- 以上設定在拿到系上的機器之後再改成對應的 ---
        )
        return connect
    except Exception as e:
        print(f"連線失敗: {e}")
        return None


# ----- 開始撰寫功能，也就是整個展覽購票網站中，會需要用到資料庫的資料的動作(ex. 新增、刪除、查詢) ----------

# 1. 會員註冊，呼叫路徑 '/api/register'，就會使用這個功能
@app.route('/api/register', methods=['POST'])
def register():
    # 接收前端傳來的 JSON 資料，也就是使用者在註冊時填寫的資料，會以 JSON 的格式傳送
    data = request.json
    name = data.get('name')
    email = data.get('email')
    password = data.get('password')
    phone = data.get('phone')

    # 防呆機制：確保欄位不為空
    if not all([name, email, password]):
        return jsonify({"error": "請填寫完整資料"}), 400

    # 資安的相關操作，讓密碼用 hash(雜湊，無法逆推回原文) 的形式存入資料庫，而不是原本的明文，避免原始密碼被竊取
    # 登入時，會比對使用者輸入的密碼的雜湊值 是否與 資料庫儲存的雜湊值 相同，就不會用原本的明文密碼進行比對
    hashed_password = generate_password_hash(password)

    try:
        db_conn = conn()
        cursor = db_conn.cursor()
        # 依序將使用者填的資料寫入 Members 資料表 (執行 SQL 語法)
        cursor.execute(
            "INSERT INTO Members (name, email, password_hash, phone) VALUES (%s, %s, %s, %s)",
            (name, email, hashed_password, phone)
        )
        db_conn.commit()  # 提交交易，寫入資料庫
        return jsonify({"message": "註冊成功"}), 201  # 回應後端的處理情況，2 開頭的回應碼表示成功
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if db_conn: db_conn.close()



# 2. 會員登入
@app.route('/api/login', methods=['POST'])
def login():
    # 接收前端使用者填寫的資料
    data = request.json
    email = data.get('email')
    password = data.get('password')

    try:
        db_conn = conn()
        cursor = db_conn.cursor()
        # 使用者填寫的 Email 去資料庫查詢對應的資料
        cursor.execute("SELECT member_id, name, password_hash FROM Members WHERE email = %s", (email,))
        user = cursor.fetchone() # 將查到的資料存入 user，方便後續比對

        # 驗證密碼：比對輸入的密碼與資料庫中的雜湊值
        if user and check_password_hash(user[2], password):
            # 登入成功，將使用者資訊寫入 Session (伺服器記憶目前是這個帳號登入中，除非按登出，否則會持續保持登入狀態)
            session['user_id'] = user[0]  # 存入 Session
            session['user_name'] = user[1]
            return jsonify({"message": "登入成功"}), 200
        else:
            return jsonify({"error": "帳號或密碼錯誤"}), 401
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if db_conn: db_conn.close()



# 3. 取得所有展覽 (進入網站首頁時使用，在畫面上列出所有上架中的展覽)
@app.route('/api/exhibitions', methods=['GET'])
def get_exhibitions():
    try:
        db_conn = conn()
        cursor = db_conn.cursor()
        # 選擇上架中的展覽 (status = 'Published')
        cursor.execute("SELECT exhibition_id, title, start_date, end_date FROM Exhibitions WHERE status = 'Published'")
        rows = cursor.fetchall() # 存入 rows
        
        # 將資料庫的 Tuple 格式轉換為字典 (dict) 的格式，方便前端渲染
        exhibitions = []
        for row in rows:
            exhibitions.append({
                "id": row[0],
                "title": row[1],
                "date_range": f"{row[2]} ~ {row[3]}"
            })

        # 回傳展覽列表，交給前端瀏覽器呈現
        return jsonify(exhibitions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if db_conn: db_conn.close()



# 4. 取得單一展覽詳情 (包含場次與票種)
# 會同時查詢三個關聯表：展覽資訊、場次 (Sessions)、票種 (TicketTypes)
@app.route('/api/exhibitions/<int:exhibition_id>', methods=['GET']) # 路徑的 <int:exhibition_id> 會動態的用不同的 id 查詢不同的展覽
def get_exhibition_detail(exhibition_id):
    try:
        db_conn = conn()
        cursor = db_conn.cursor()
        
        # 查詢展覽基本資料
        cursor.execute("SELECT title, description, location FROM Exhibitions WHERE exhibition_id = %s", (exhibition_id,))
        exhibition = cursor.fetchone()
        
        # 查詢該展覽的場次 (Sessions)
        cursor.execute("SELECT session_id, session_time, capacity FROM Sessions WHERE exhibition_id = %s", (exhibition_id,))
        sessions = [{"id": row[0], "time": row[1], "capacity": row[2]} for row in cursor.fetchall()]

        # 查詢該展覽的票種 (TicketTypes)
        cursor.execute("SELECT ticket_type_id, name, price FROM TicketTypes WHERE exhibition_id = %s", (exhibition_id,))
        ticket_types = [{"id": row[0], "name": row[1], "price": float(row[2])} for row in cursor.fetchall()]

        # 整合所有資料後回傳
        return jsonify({
            "title": exhibition[0],
            "description": exhibition[1],
            "location": exhibition[2],
            "sessions": sessions,
            "ticket_types": ticket_types
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if db_conn: db_conn.close()



# 5. 建立訂單 (購票)
@app.route('/api/create_order', methods=['POST'])
def create_order():
    # 權限檢查：未登入者不可購票
    if 'user_id' not in session:
        return jsonify({"error": "未登入"}), 401

    user_id = session['user_id']
    data = request.json
    # 前端傳來的結構範例: 
    # { "items": [ {"session_id": 1, "ticket_type_id": 2, "quantity": 1} ] }
    items = data.get('items', []) 
    
    if not items:
        return jsonify({"error": "購物車為空"}), 400

    try:
        db_conn = conn()
        cursor = db_conn.cursor()
        
        # 1. 計算總金額
        total_amount = 0
        for item in items:
            cursor.execute("SELECT price FROM TicketTypes WHERE ticket_type_id = %s", (item['ticket_type_id'],))
            price = cursor.fetchone()[0]
            total_amount += price * item['quantity']

        # 2. 建立訂單，加入 Orders 資料表，保存這筆訂單的資訊
        cursor.execute("""
            INSERT INTO Orders (member_id, total_amount, order_date, status)
            VALUES (%s, %s, NOW(), 'Paid') 
        """, (user_id, total_amount))
        # 註: 還沒做付款的功能，為了簡化，這裡假設直接付款成功 (status='Paid')
        
        # 取得剛剛插入的訂單 ID (MySQL 特有寫法，之後換機器可能要改)
        order_id = cursor.lastrowid

        # 3. 生成票券 (Tickets)
        # 為每張購買的票，生成各自的、獨一無二的 UUID (QR Code 用)
        generated_tickets = []
        for item in items:
            for _ in range(item['quantity']):
                ticket_uuid = str(uuid.uuid4()) # 生成隨機 UUID
                cursor.execute("""
                    INSERT INTO Tickets (ticket_uuid, order_id, ticket_type_id, session_id, status)
                    VALUES (%s, %s, %s, %s, 'Unused')
                """, (ticket_uuid, order_id, item['ticket_type_id'], item['session_id']))
                generated_tickets.append(ticket_uuid)

        db_conn.commit() # 全部成功才提交
        return jsonify({"message": "訂單建立成功", "order_id": order_id, "tickets": generated_tickets}), 201

    except Exception as e:
        db_conn.rollback() # 發生任何錯誤則回滾 (Rollback)，避免資料不一致 (只有訂單卻沒票)
        print(f"Error: {e}") # 建議印出錯誤以便除錯
        return jsonify({"error": str(e)}), 500
    finally:
        if db_conn: db_conn.close()



# 6. 查看我的票券
@app.route('/api/my_tickets', methods=['GET'])
def my_tickets():
    if 'user_id' not in session:
        return jsonify({"error": "未登入"}), 401
    
    user_id = session['user_id']

    try:
        db_conn = conn()
        cursor = db_conn.cursor()
        
        # 關聯查詢：從 Orders 找到 Tickets，再關聯出展覽名稱與場次時間
        # (使用 JOIN 連接 Tickets, Orders, Sessions, Exhibitions, TicketTypes 五張表)
        # 一次撈出票券的所有詳細資訊 (包含展覽名、時間、QR Code UUID)
        query = """
            SELECT t.ticket_uuid, t.status, e.title, s.session_time, tt.name
            FROM Tickets t
            JOIN Orders o ON t.order_id = o.order_id
            JOIN Sessions s ON t.session_id = s.session_id
            JOIN Exhibitions e ON s.exhibition_id = e.exhibition_id
            JOIN TicketTypes tt ON t.ticket_type_id = tt.ticket_type_id
            WHERE o.member_id = %s
            ORDER BY s.session_time DESC
        """
        cursor.execute(query, (user_id,))
        tickets = []
        for row in cursor.fetchall():
            tickets.append({
                "uuid": row[0],        # 前端可用此字串生成 QR Code
                "status": row[1],      # 狀態 (Unused/Used)
                "exhibition": row[2],
                "time": row[3],
                "type": row[4]
            })
            
        return jsonify(tickets)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if db_conn: db_conn.close()



# -------------------------- 網頁路由區 (負責顯示畫面) ----------------------------
# 如果想要只使用ip網址(ex. 192.168.134.130:5000)，就能導入到首頁，就需要像這樣指定 route 並用 render_template 表示要去開啟哪一份前端網頁檔案---
# 如果把這區註解的話就需要直接用檔案路徑去開啟指定頁面的 html 檔案，ex. 一開始要進首頁的話要使用類似於這樣的網址 192.168.134.130:5000/static/index.html
#     且 index.html 等在網頁 (html檔案) 內跳轉去其他頁面的 href 路徑也要改成檔案路徑
# 註: 學姊那邊就沒有寫這區，所以在網址都能看到現在的頁面所使用的檔案，兩種方法各有優缺

@app.route('/')
def index_page():
    # 首頁：傳遞 user_name 給前端，用於顯示 「Hi, xxx」 或 「登入/註冊」
    # 從 session 取得使用者名稱，如果沒登入會拿到 None
    user_name = session.get('user_name')

    # 將 user_name 變數傳送給 index.html，在首頁顯示當前登入的使用者名稱
    return render_template('index.html', user_name=user_name)

@app.route('/register_page')
def register_page():
    # 註冊頁面
    return render_template('register.html')

@app.route('/login_page')
def login_page():
    # 登入頁面
    return render_template('login.html')

@app.route('/logout')
def logout():
    # 登出功能
    session.clear()  # 清空 session (包含 user_id 和 user_name)
    return redirect(url_for('index_page'))  # 導回首頁

@app.route('/detail_page')
def detail_page():
    # 展覽詳情頁
    # 這裡不需要傳參數，因為 HTML 裡的 JS 會去抓網址的 ?id=...
    return render_template('detail.html')

@app.route('/my_tickets_page')
def my_tickets_page():
    # 我的票券頁
    return render_template('my_tickets.html')


# -------------------------- 程式啟動點 ----------------------------
if __name__ == '__main__':
    # host='0.0.0.0' 代表監聽所有網路介面，允許外部電腦 (Client) 連線，而不只有本機 (這裡的本機是我的 kali 虛擬機)
    # debug=True：開啟除錯模式，程式碼修改後會自動重啟
    app.run(debug=True, host='0.0.0.0', port=5000)
