import pymysql
from werkzeug.security import generate_password_hash

# ==========================================
# MySQL 資料庫設定
# ==========================================
DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'root',  # MySQL 預設帳號
    'password': 'wendy940704',  # 【請填入你的 MySQL 密碼，若無則留空】
    # 'database': 'ExhibitionTicketSystem', # 初始化時先不指定，稍後建立
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor  # ★ 讓查詢結果變成 Dictionary
}


def init_database():
    print("🚀 開始初始化 MySQL 資料庫...")

    try:
        # 1. 先連線到 MySQL Server (不指定 DB)
        conn = pymysql.connect(host=DB_CONFIG['host'], user=DB_CONFIG['user'], password=DB_CONFIG['password'])
        cursor = conn.cursor()

        # 2. 建立資料庫
        cursor.execute(
            "CREATE DATABASE IF NOT EXISTS ExhibitionTicketSystem CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;")
        cursor.execute("USE ExhibitionTicketSystem;")
        conn.select_db('ExhibitionTicketSystem')  # 切換過去

        # 3. 清除舊資料表 (MySQL 語法: DROP TABLE IF EXISTS)
        print("🗑️  正在重置資料表...")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")  # 暫時關閉外鍵檢查以免報錯
        tables = ['Tickets', 'Payments', 'Orders', 'TicketTypes', 'Sessions', 'Exhibitions', 'Members', 'Organizers']
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table};")
        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

        # 4. 建立新資料表 (MySQL 語法)
        print("🏗️  正在建立新架構...")

        create_sql = """
        CREATE TABLE Organizers (
            organizer_id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(100) NOT NULL,
            contact_person VARCHAR(50),
            phone VARCHAR(20),
            email VARCHAR(100)
        );

        CREATE TABLE Members (
            member_id INT PRIMARY KEY AUTO_INCREMENT,
            name VARCHAR(50) NOT NULL,
            email VARCHAR(100) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            phone VARCHAR(20),
            role VARCHAR(20) DEFAULT 'user',
            created_at DATETIME DEFAULT NOW()
        );

        CREATE TABLE Exhibitions (
            exhibition_id INT PRIMARY KEY AUTO_INCREMENT,
            organizer_id INT,
            title VARCHAR(200) NOT NULL,
            location VARCHAR(200),
            description TEXT,
            start_date DATE,
            end_date DATE,
            status VARCHAR(20) DEFAULT 'Draft',
            validation_pin VARCHAR(20) DEFAULT '1234',
            FOREIGN KEY (organizer_id) REFERENCES Organizers(organizer_id)
        );

        CREATE TABLE Sessions (
            session_id INT PRIMARY KEY AUTO_INCREMENT,
            exhibition_id INT NOT NULL,
            session_time DATETIME NOT NULL,
            capacity INT NOT NULL,
            FOREIGN KEY (exhibition_id) REFERENCES Exhibitions(exhibition_id)
        );

        CREATE TABLE TicketTypes (
            ticket_type_id INT PRIMARY KEY AUTO_INCREMENT,
            exhibition_id INT NOT NULL,
            name VARCHAR(50) NOT NULL,
            price DECIMAL(10, 2) NOT NULL,
            FOREIGN KEY (exhibition_id) REFERENCES Exhibitions(exhibition_id)
        );

        CREATE TABLE Orders (
            order_id INT PRIMARY KEY AUTO_INCREMENT,
            member_id INT NOT NULL,
            total_amount DECIMAL(10, 2) NOT NULL,
            order_date DATETIME DEFAULT NOW(),
            status VARCHAR(20) DEFAULT 'Pending',
            FOREIGN KEY (member_id) REFERENCES Members(member_id)
        );

        CREATE TABLE Tickets (
            ticket_uuid VARCHAR(36) PRIMARY KEY,
            order_id INT NOT NULL,
            ticket_type_id INT NOT NULL,
            session_id INT,
            status VARCHAR(20) DEFAULT 'Unused',
            used_at DATETIME,
            FOREIGN KEY (order_id) REFERENCES Orders(order_id),
            FOREIGN KEY (ticket_type_id) REFERENCES TicketTypes(ticket_type_id),
            FOREIGN KEY (session_id) REFERENCES Sessions(session_id)
        );

        CREATE TABLE Payments (
            payment_id INT PRIMARY KEY AUTO_INCREMENT,
            order_id INT NOT NULL,
            payment_method VARCHAR(50),
            transaction_code VARCHAR(100),
            amount DECIMAL(10, 2) NOT NULL,
            paid_at DATETIME DEFAULT NOW(),
            status VARCHAR(20) DEFAULT 'Success',
            FOREIGN KEY (order_id) REFERENCES Orders(order_id)
        );
        """
        # pymysql 不支援一次執行多個 CREATE，需依 ; 切割或分開執行
        # 這裡簡單處理：直接執行上面的一大串，若報錯則改用迴圈
        for statement in create_sql.split(';'):
            if statement.strip():
                cursor.execute(statement)

        conn.commit()

        # 5. 寫入種子資料 (預留位置改用 %s)
        print("🌱  正在寫入範例資料...")

        admin_pw = generate_password_hash('admin')
        user_pw = generate_password_hash('user')

        cursor.execute("""
            INSERT INTO Members (name, email, password_hash, phone, role) VALUES 
            ('系統管理員', 'admin@example.com', %s, '0900000000', 'admin'),
            ('測試會員', 'user@example.com', %s, '0911222333', 'user');
        """, (admin_pw, user_pw))

        cursor.execute("""
            INSERT INTO Organizers (name, contact_person, email) VALUES 
            ('台北當代美術館', '陳館長', 'contact@mocataipei.org.tw'),
            ('台灣人工智慧協會', '李博士', 'service@ai-taiwan.org'),
            ('必應創造', '王經理', 'event@bin-live.com');
        """)

        cursor.execute("""
            INSERT INTO Exhibitions (organizer_id, title, location, description, start_date, end_date, status, validation_pin) VALUES 
            (1, '2025 印象派光影藝術展', '松山文創園區 1號倉庫', '沉浸式體驗莫內與梵谷的畫作。', '2025-12-20', '2026-03-31', 'Published', '1234'),
            (2, 'Generative AI 未來年會', '南港展覽館 2館', '探討 ChatGPT 與生成式 AI 的最新應用。', '2026-01-10', '2026-01-12', 'Published', '1234'),
            (3, '宇宙人 [α：回到未來] 演唱會', '台北小巨蛋', '宇宙人 20 週年紀念演唱會。', '2025-12-31', '2025-12-31', 'Published', '1234');
        """)

        cursor.execute("""
            INSERT INTO Sessions (exhibition_id, session_time, capacity) VALUES 
            (1, '2025-12-25 10:00:00', 100), (1, '2025-12-25 14:00:00', 100),
            (2, '2026-01-10 09:00:00', 500),
            (3, '2025-12-31 19:30:00', 10000);
        """)

        cursor.execute("""
            INSERT INTO TicketTypes (exhibition_id, name, price) VALUES 
            (1, '全票', 450), (1, '學生票', 350),
            (2, '一般與會證', 2500), (2, 'VIP', 5000),
            (3, '搖滾區', 3800), (3, '看台區', 2800);
        """)

        conn.commit()
        print("✅  MySQL 資料庫初始化完成！")

    except Exception as e:
        print(f"❌ 初始化失敗: {e}")
        if 'conn' in locals(): conn.rollback()
    finally:
        if 'conn' in locals(): conn.close()


if __name__ == '__main__':
    init_database()