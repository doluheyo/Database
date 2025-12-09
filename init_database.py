import pymysql
import pyodbc
from werkzeug.security import generate_password_hash


def init_database():
    print("🚀 開始初始化 MySQL 資料庫...")

    try:
        # 1. 先連線到 SQL Server (不指定 DB)
        conn = pyodbc.connect(
            r'DRIVER={ODBC Driver 17 for SQL Server};'
            r'SERVER=localhost\SQLEXPRESS;'
            #r'DATABASE=ExhibitionDB;'  # 初始化時先不指定，稍後建立
            r'UID=root;'
            r'PWD=wendy940704;',
            autocommit=True  # 建立資料庫時需要開啟自動提交模式
        )
        print("資料庫連線成功！")
        cursor = conn.cursor()

        # 2. 建立資料庫
        db_name = "ExhibitionTicketSystem" # 資料庫名稱
        cursor.execute(f"""
            IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{db_name}')
            BEGIN
                CREATE DATABASE {db_name};
            END
        """)
        cursor.execute(f"USE {db_name};")

        # 3. 清除舊資料表 (MySQL 語法: DROP TABLE IF EXISTS)
        print("🗑️  正在重置資料表...")
        tables = ['Tickets', 'Payments', 'Orders', 'TicketTypes', 'Sessions', 'Exhibitions', 'Members', 'Organizers']
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table};")

        # 4. 建立新資料表 (MySQL 語法)
        print("🏗️  正在建立新架構...")

        queries = [
            """CREATE TABLE Organizers (
                organizer_id INT PRIMARY KEY IDENTITY(1,1),
                name NVARCHAR(100) NOT NULL,
                contact_person NVARCHAR(50),
                phone VARCHAR(20),
                email VARCHAR(100)
            )""",
            """CREATE TABLE Members (
                member_id INT PRIMARY KEY IDENTITY(1,1),
                name NVARCHAR(50) NOT NULL,
                email VARCHAR(100) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                phone VARCHAR(20),
                role VARCHAR(20) DEFAULT 'user',
                created_at DATETIME DEFAULT GETDATE()
            )""",
            """CREATE TABLE Exhibitions (
                exhibition_id INT PRIMARY KEY IDENTITY(1,1),
                organizer_id INT,
                title NVARCHAR(200) NOT NULL,
                location NVARCHAR(200),
                description NVARCHAR(MAX),
                start_date DATE,
                end_date DATE,
                status VARCHAR(20) DEFAULT 'Draft',
                validation_pin VARCHAR(20) DEFAULT '1234',
                FOREIGN KEY (organizer_id) REFERENCES Organizers(organizer_id)
            )""",
            """CREATE TABLE Sessions (
                session_id INT PRIMARY KEY IDENTITY(1,1),
                exhibition_id INT NOT NULL,
                session_time DATETIME NOT NULL,
                capacity INT NOT NULL,
                FOREIGN KEY (exhibition_id) REFERENCES Exhibitions(exhibition_id)
            )""",
            """CREATE TABLE TicketTypes (
                ticket_type_id INT PRIMARY KEY IDENTITY(1,1),
                exhibition_id INT NOT NULL,
                name NVARCHAR(50) NOT NULL,
                price DECIMAL(10, 2) NOT NULL,
                FOREIGN KEY (exhibition_id) REFERENCES Exhibitions(exhibition_id)
            )""",
            """CREATE TABLE Orders (
                order_id INT PRIMARY KEY IDENTITY(1,1),
                member_id INT NOT NULL,
                total_amount DECIMAL(10, 2) NOT NULL,
                order_date DATETIME DEFAULT GETDATE(),
                status VARCHAR(20) DEFAULT 'Pending',
                FOREIGN KEY (member_id) REFERENCES Members(member_id)
            )""",
            """CREATE TABLE Tickets (
                ticket_uuid VARCHAR(36) PRIMARY KEY,
                order_id INT NOT NULL,
                ticket_type_id INT NOT NULL,
                session_id INT,
                status VARCHAR(20) DEFAULT 'Unused',
                used_at DATETIME,
                FOREIGN KEY (order_id) REFERENCES Orders(order_id),
                FOREIGN KEY (ticket_type_id) REFERENCES TicketTypes(ticket_type_id),
                FOREIGN KEY (session_id) REFERENCES Sessions(session_id)
            )""",
            """CREATE TABLE Payments (
                payment_id INT PRIMARY KEY IDENTITY(1,1),
                order_id INT NOT NULL,
                payment_method VARCHAR(50),
                transaction_code VARCHAR(100),
                amount DECIMAL(10, 2) NOT NULL,
                paid_at DATETIME DEFAULT GETDATE(),
                status VARCHAR(20) DEFAULT 'Success',
                FOREIGN KEY (order_id) REFERENCES Orders(order_id)
            )"""
        ]

        for query in queries:
            cursor.execute(query)

        # 5. 寫入種子資料 (預留位置用 ?)
        print("🌱  正在寫入範例資料...")

        admin_pw = generate_password_hash('admin')
        user_pw = generate_password_hash('user')

        cursor.execute("""
            INSERT INTO Members (name, email, password_hash, phone, role) VALUES 
            (?, ?, ?, ?, ?),
            (?, ?, ?, ?, ?)
        """, ('系統管理員', 'admin@example.com', admin_pw, '0900000000', 'admin',
              '測試會員', 'user@example.com', user_pw, '0911222333', 'user'))

        cursor.execute("INSERT INTO Organizers (name, contact_person, email) VALUES (?, ?, ?)", 
                       ('台北當代美術館', '陳館長', 'contact@mocataipei.org.tw'))
        cursor.execute("INSERT INTO Organizers (name, contact_person, email) VALUES (?, ?, ?)", 
                       ('台灣人工智慧協會', '李博士', 'service@ai-taiwan.org'))
        cursor.execute("INSERT INTO Organizers (name, contact_person, email) VALUES (?, ?, ?)", 
                       ('必應創造', '王經理', 'event@bin-live.com'))

        # 在中文字串前面加上 N ，避免 SQL Server 在處理中文字時出現亂碼
        cursor.execute("""
            INSERT INTO Exhibitions (organizer_id, title, location, description, start_date, end_date, status, validation_pin) VALUES 
            (1, N'2025 印象派光影藝術展', N'松山文創園區 1號倉庫', N'沉浸式體驗莫內與梵谷的畫作。', '2025-12-20', '2026-03-31', 'Published', '1234'),
            (2, N'Generative AI 未來年會', N'南港展覽館 2館', N'探討 ChatGPT 與生成式 AI 的最新應用。', '2026-01-10', '2026-01-12', 'Published', '1234'),
            (3, N'宇宙人 [α：回到未來] 演唱會', N'台北小巨蛋', N'宇宙人 20 週年紀念演唱會。', '2025-12-31', '2025-12-31', 'Published', '1234');
        """)

        cursor.execute("""
            INSERT INTO Sessions (exhibition_id, session_time, capacity) VALUES 
            (1, '2025-12-25 10:00:00', 100), (1, '2025-12-25 14:00:00', 100),
            (2, '2026-01-10 09:00:00', 500),
            (3, '2025-12-31 19:30:00', 10000)
        """)

        cursor.execute("""
            INSERT INTO TicketTypes (exhibition_id, name, price) VALUES 
            (1, N'全票', 450), (1, N'學生票', 350),
            (2, N'一般與會證', 2500), (2, N'VIP', 5000),
            (3, N'搖滾區', 3800), (3, N'看台區', 2800)
        """)

        conn.commit()
        print("✅  MySQL 資料庫初始化完成！")

    except Exception as e:
        print(f"❌ 初始化失敗: {e}")
        if conn: conn.rollback()
    finally:
        if conn: conn.close()


if __name__ == '__main__':
    init_database()