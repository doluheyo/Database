import pyodbc
from werkzeug.security import generate_password_hash
import uuid
from datetime import datetime


def init_database():
    print("開始初始化 SQL Server 資料庫")

    try:
        # 1. 先連線到 SQL Server (不指定 DB)
        conn = pyodbc.connect(
            r'DRIVER={ODBC Driver 17 for SQL Server};'
            r'SERVER=localhost\SQLEXPRESS;'
            r'UID=root;'
            r'PWD=wendy940704;',
            autocommit=True
        )
        print("資料庫連線成功")
        cursor = conn.cursor()

        # 2. 建立資料庫
        db_name = "ExhibitionTicketSystem"
        cursor.execute(f"""
            IF NOT EXISTS (SELECT * FROM sys.databases WHERE name = '{db_name}')
            BEGIN
                CREATE DATABASE {db_name};
            END
        """)
        cursor.execute(f"USE {db_name};")

        # 3. 清除舊資料表
        print("正在重置資料表")
        tables = ['Tickets', 'Payments', 'Orders', 'TicketTypes', 'Sessions', 'Exhibitions', 'Members', 'Organizers']
        for table in tables:
            cursor.execute(f"DROP TABLE IF EXISTS {table};")

        # 4. 建立新資料表
        print("正在建立新架構")

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
                image_path NVARCHAR(500),
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
            )"""
        ]

        for query in queries:
            cursor.execute(query)

        print("寫入初始化資料")

        print("新增會員")
        members_data = [
            ('系統管理員', 'admin@example.com', generate_password_hash('admin'), '0900000000', 'admin'),
            ('王小明', 'ming.wang@gmail.com', generate_password_hash('user123'), '0912345678', 'user'),
            ('李美華', 'meihua.lee@yahoo.com.tw', generate_password_hash('user123'), '0923456789', 'user'),
            ('張志豪', 'zhihao.chang@hotmail.com', generate_password_hash('user123'), '0934567890', 'user'),
            ('陳雅婷', 'yating.chen@gmail.com', generate_password_hash('user123'), '0945678901', 'user'),
            ('林建宏', 'jianhong.lin@outlook.com', generate_password_hash('user123'), '0956789012', 'user'),
            ('黃淑芬', 'shufen.huang@gmail.com', generate_password_hash('user123'), '0967890123', 'user'),
            ('劉家銘', 'jiaming.liu@yahoo.com.tw', generate_password_hash('user123'), '0978901234', 'user'),
            ('吳佩珊', 'peishan.wu@gmail.com', generate_password_hash('user123'), '0989012345', 'user'),
            ('蔡宗翰', 'zonghan.tsai@hotmail.com', generate_password_hash('user123'), '0990123456', 'user'),
        ]
        
        for member in members_data:
            cursor.execute("""
                INSERT INTO Members (name, email, password_hash, phone, role) 
                VALUES (?, ?, ?, ?, ?)
            """, member)


        print("新增主辦單位")
        organizers_data = [
            ('國立故宮博物院', '王館長', '02-28812021', 'service@npm.gov.tw'),
            ('台北市立美術館', '陳副館長', '02-25957656', 'info@tfam.museum'),
            ('國立台灣美術館', '林主任', '04-23723552', 'service@ntmofa.gov.tw'),
            ('高雄市立美術館', '張館長', '07-5550331', 'service@kmfa.gov.tw'),
            ('奇美博物館', '許執行長', '06-2660808', 'info@chimeimuseum.org'),
            ('聯合數位文創', '李經理', '02-77210772', 'service@udnfunlife.com'),
            ('寬宏藝術', '黃總監', '07-7809900', 'service@kharts.com.tw'),
            ('時藝多媒體', '周專員', '02-66169928', 'info@mediasphere.com.tw'),
            ('華山1914文創園區', '吳園長', '02-23581914', 'service@huashan1914.com'),
            ('松山文創園區', '蔡主任', '02-27651388', 'info@songshanculturalpark.org'),
            ('國立歷史博物館', '鄭館長', '02-23610270', 'service@nmh.gov.tw'),
            ('台北當代藝術館', '劉策展人', '02-25523721', 'info@mocataipei.org.tw'),
            ('朱銘美術館', '朱執行長', '02-24989940', 'service@juming.org.tw'),
            ('野獸國', '王企劃', '02-87719900', 'info@beastcommunity.com'),
            ('異想創造', '陳創意長', '02-27001234', 'service@imagination.com.tw'),
            ('閣林文創', '林總編', '02-23456789', 'info@greenlin.com.tw'),
            ('新光三越文教基金會', '李主任', '02-23891234', 'culture@skm.com.tw'),
            ('中正紀念堂管理處', '張處長', '02-23431100', 'service@cksmh.gov.tw'),
            ('台灣創意設計中心', '吳總監', '02-27458199', 'info@tdc.org.tw'),
            ('國立科學工藝博物館', '蘇館長', '07-3800089', 'service@nstm.gov.tw'),
        ]
        
        for org in organizers_data:
            cursor.execute("""
                INSERT INTO Organizers (name, contact_person, phone, email) 
                VALUES (?, ?, ?, ?)
            """, org)

        
        print("新增展覽")
        exhibitions_data = [
            # (organizer_id, title, location, description, start_date, end_date, status, validation_pin)
            # 過期展覽 (5場)
            (1, '翠玉白菜：國寶的故事', '國立故宮博物院 正館', 
             '深入探索故宮最具代表性的國寶翠玉白菜，透過科技互動了解其雕刻工藝與文化意涵。', 
             '2024-06-01', '2024-12-31', 'Ended', '1234'),
            (6, '草間彌生：圓點宇宙', '華山1914文創園區 東2館', 
             '日本當代藝術大師草間彌生的沉浸式體驗展，走進無限圓點的奇幻世界。', 
             '2024-09-15', '2025-01-15', 'Ended', '1234'),
            (8, '哆啦A夢50週年紀念展', '松山文創園區 二號倉庫', 
             '慶祝哆啦A夢誕生50週年，重現經典場景，展出珍貴手稿與道具。', 
             '2024-07-01', '2024-11-30', 'Ended', '1234'),
            (7, '航海王：海賊王的寶藏', '高雄駁二藝術特區 P2倉庫', 
             '航海王25週年特展，重現偉大航道經典場景，與草帽海賊團一同冒險！', 
             '2024-08-10', '2024-12-15', 'Ended', '1234'),
            (2, '畢卡索：藍色時期特展', '台北市立美術館 地下樓', 
             '聚焦畢卡索創作生涯中最動人的藍色時期，展出30幅珍貴原作。', 
             '2024-05-20', '2024-10-20', 'Ended', '1234'),
            
            # 進行中展覽 (15場)
            (6, '莫內：光影印象派大展', '中正紀念堂 一展廳', 
             '全球獨家沉浸式體驗，以360度環繞投影重現莫內花園，漫步在睡蓮池畔。', 
             '2025-10-01', '2026-03-31', 'Published', '1234'),
            (8, '梵谷：星空夜色沉浸展', '華山1914文創園區 東3館', 
             '穿越時空走進梵谷的畫作，體驗星夜的璀璨與向日葵的熱情。', 
             '2025-11-15', '2026-04-15', 'Published', '1234'),
            (3, '會動的文藝復興', '國立台灣美術館 大廳', 
             '運用AI動態技術讓文藝復興名作「動」起來，達文西、米開朗基羅作品全新詮釋。', 
             '2025-09-20', '2026-02-28', 'Published', '1234'),
            (12, '奈良美智：夢遊娃娃世界', '台北當代藝術館', 
             '日本人氣藝術家奈良美智台灣首展，展出經典大眼娃娃系列與全新創作。', 
             '2025-12-01', '2026-05-31', 'Published', '1234'),
            (14, '蠟筆小新30週年特展', '松山文創園區 一號倉庫', 
             '跟著小新一家展開爆笑冒險，重現春日部場景，限定周邊商品獨家販售。', 
             '2025-11-01', '2026-02-28', 'Published', '1234'),
            (15, '角落小夥伴的夢幻假期', '新光三越信義新天地 A11 6F', 
             '超療癒角落小夥伴主題展，打造夢幻度假場景，與白熊、炸蝦尾一起放鬆。', 
             '2025-12-15', '2026-03-15', 'Published', '1234'),
            (14, '吉卜力動畫世界特展', '華山1914文創園區 中4館', 
             '走進宮崎駿的動畫世界，龍貓森林、神隱少女湯屋等經典場景1:1重現。', 
             '2025-10-20', '2026-04-20', 'Published', '1234'),
            (6, '迪士尼百年經典展', '中正紀念堂 二展廳', 
             '慶祝迪士尼100週年，從米奇到冰雪奇緣，回顧百年動畫魔法。', 
             '2025-11-20', '2026-05-20', 'Published', '1234'),
            (7, '冰雪奇緣夢幻特展', '高雄市立美術館 特展區', 
             '艾莎與安娜帶你走進艾倫戴爾王國，體驗冰雪魔法的奇幻世界。', 
             '2025-12-01', '2026-03-01', 'Published', '1234'),
            (15, '名偵探柯南科學搜查展', '國立科學工藝博物館', 
             '化身小小偵探，運用科學辦案！體驗指紋採集、彈道分析等鑑識技術。', 
             '2025-10-15', '2026-01-15', 'Published', '1234'),
            (14, '寶可夢訓練家大集結', '南港展覽館 一館', 
             '超大型寶可夢主題樂園，與皮卡丘互動、挑戰道館，捕捉專屬回憶！', 
             '2025-12-20', '2026-04-30', 'Published', '1234'),
            (6, '米奇與好朋友主題特展', '台北101 4F', 
             '米奇95週年慶典，經典卡通場景重現，米妮、唐老鴨、高飛齊聚一堂。', 
             '2025-11-25', '2026-02-25', 'Published', '1234'),
            (8, '達文西：曠世奇才展', '奇美博物館 特展廳', 
             '文藝復興巨匠達文西的科學與藝術，展出手稿複製品與機械模型。', 
             '2025-09-01', '2026-01-31', 'Published', '1234'),
            (19, '安藤忠雄：建築的詩學', '台北市立美術館 二樓', 
             '日本建築大師安藤忠雄回顧展，光與影的詩意空間，1:1清水模體驗區。', 
             '2025-10-10', '2026-03-10', 'Published', '1234'),
            (9, 'teamLab：未來遊樂園', '華山1914文創園區 中5館', 
             '日本超人氣數位藝術團隊teamLab互動體驗展，打造光影交織的奇幻世界。', 
             '2025-12-01', '2026-06-30', 'Published', '1234'),
        ]
        
        for ex in exhibitions_data:
            cursor.execute("""
                INSERT INTO Exhibitions (organizer_id, title, location, description, start_date, end_date, status, validation_pin) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, ex)


        print("新增每場展覽的場次")
        sessions_data = [
            # exhibition_id, session_time, capacity
            # 展覽1: 翠玉白菜 (過期)
            (1, '2024-08-15 10:00:00', 200),
            (1, '2024-08-15 14:00:00', 200),
            # 展覽2: 草間彌生 (過期)
            (2, '2024-11-20 10:00:00', 150),
            (2, '2024-11-20 14:00:00', 150),
            (2, '2024-11-20 18:00:00', 150),
            # 展覽3: 哆啦A夢 (過期)
            (3, '2024-10-01 10:00:00', 300),
            (3, '2024-10-01 14:00:00', 300),
            # 展覽4: 航海王 (過期)
            (4, '2024-10-20 10:00:00', 250),
            (4, '2024-10-20 14:00:00', 250),
            (4, '2024-10-20 18:00:00', 250),
            # 展覽5: 畢卡索 (過期)
            (5, '2024-09-15 10:00:00', 100),
            (5, '2024-09-15 14:00:00', 100),
            # 展覽6: 莫內
            (6, '2025-12-25 10:00:00', 200),
            (6, '2025-12-25 14:00:00', 200),
            (6, '2025-12-25 18:00:00', 200),
            # 展覽7: 梵谷
            (7, '2025-12-28 10:00:00', 180),
            (7, '2025-12-28 14:00:00', 180),
            # 展覽8: 會動的文藝復興
            (8, '2025-12-30 10:00:00', 250),
            (8, '2025-12-30 14:00:00', 250),
            (8, '2025-12-30 18:00:00', 250),
            # 展覽9: 奈良美智
            (9, '2026-01-05 10:00:00', 120),
            (9, '2026-01-05 14:00:00', 120),
            # 展覽10: 蠟筆小新
            (10, '2025-12-27 10:00:00', 300),
            (10, '2025-12-27 14:00:00', 300),
            (10, '2025-12-27 18:00:00', 300),
            # 展覽11: 角落小夥伴
            (11, '2026-01-10 10:00:00', 200),
            (11, '2026-01-10 14:00:00', 200),
            # 展覽12: 吉卜力
            (12, '2026-01-15 10:00:00', 250),
            (12, '2026-01-15 14:00:00', 250),
            (12, '2026-01-15 18:00:00', 250),
            # 展覽13: 迪士尼百年
            (13, '2026-01-20 10:00:00', 300),
            (13, '2026-01-20 14:00:00', 300),
            # 展覽14: 冰雪奇緣
            (14, '2026-01-25 10:00:00', 200),
            (14, '2026-01-25 14:00:00', 200),
            (14, '2026-01-25 18:00:00', 200),
            # 展覽15: 名偵探柯南
            (15, '2026-01-08 10:00:00', 220),
            (15, '2026-01-08 14:00:00', 220),
            # 展覽16: 寶可夢
            (16, '2026-01-30 10:00:00', 500),
            (16, '2026-01-30 14:00:00', 500),
            (16, '2026-01-30 18:00:00', 500),
            # 展覽17: 米奇
            (17, '2026-02-01 10:00:00', 200),
            (17, '2026-02-01 14:00:00', 200),
            # 展覽18: 達文西
            (18, '2026-01-12 10:00:00', 180),
            (18, '2026-01-12 14:00:00', 180),
            (18, '2026-01-12 18:00:00', 180),
            # 展覽19: 安藤忠雄
            (19, '2026-02-05 10:00:00', 150),
            (19, '2026-02-05 14:00:00', 150),
            # 展覽20: teamLab
            (20, '2026-02-10 10:00:00', 250),
            (20, '2026-02-10 14:00:00', 250),
            (20, '2026-02-10 18:00:00', 250),
        ]
        
        for session in sessions_data:
            cursor.execute("""
                INSERT INTO Sessions (exhibition_id, session_time, capacity) 
                VALUES (?, ?, ?)
            """, session)


        print("新增每場展覽的票種")
        ticket_types_data = [
            # exhibition_id, name, price
            # 展覽1: 翠玉白菜
            (1, '全票', 350), (1, '優待票', 250),
            # 展覽2: 草間彌生
            (2, '全票', 450), (2, '學生票', 350),
            # 展覽3: 哆啦A夢
            (3, '全票', 380), (3, '兒童票', 280),
            # 展覽4: 航海王
            (4, '全票', 400), (4, '學生票', 320),
            # 展覽5: 畢卡索
            (5, '全票', 500), (5, '敬老票', 250),
            # 展覽6: 莫內
            (6, '全票', 450), (6, '學生票', 350),
            # 展覽7: 梵谷
            (7, '全票', 480), (7, '優待票', 380),
            # 展覽8: 會動的文藝復興
            (8, '全票', 420), (8, '學生票', 320),
            # 展覽9: 奈良美智
            (9, '全票', 500), (9, '敬老票', 300),
            # 展覽10: 蠟筆小新
            (10, '全票', 350), (10, '兒童票', 250),
            # 展覽11: 角落小夥伴
            (11, '全票', 380), (11, '兒童票', 280),
            # 展覽12: 吉卜力
            (12, '全票', 450), (12, '學生票', 350),
            # 展覽13: 迪士尼百年
            (13, '全票', 480), (13, '兒童票', 350),
            # 展覽14: 冰雪奇緣
            (14, '全票', 420), (14, '兒童票', 300),
            # 展覽15: 名偵探柯南
            (15, '全票', 380), (15, '學生票', 280),
            # 展覽16: 寶可夢
            (16, '全票', 450), (16, '兒童票', 320),
            # 展覽17: 米奇
            (17, '全票', 400), (17, '兒童票', 280),
            # 展覽18: 達文西
            (18, '全票', 420), (18, '學生票', 300),
            # 展覽19: 安藤忠雄
            (19, '全票', 380), (19, '敬老票', 200),
            # 展覽20: teamLab
            (20, '全票', 550), (20, '學生票', 450),
        ]
        
        for tt in ticket_types_data:
            cursor.execute("""
                INSERT INTO TicketTypes (exhibition_id, name, price) 
                VALUES (?, ?, ?)
            """, tt)


        print("新增訂單")
        # 初始化就新增一些訂單內容，方便展示資料表功能
        # member_id 2=王小明, 3=李美華, 4=張志豪
        orders_data = [
            # order_id, member_id, total_amount, order_date, status
            # 王小明 (member_id=2) 的訂單: 3筆
            (2, 900, '2025-12-01 10:30:00', 'Paid'),    # order_id=1: 莫內展 全票x2
            (2, 700, '2025-12-05 14:20:00', 'Paid'),    # order_id=2: 蠟筆小新 全票x2
            (2, 450, '2025-12-10 09:15:00', 'Pending'), # order_id=3: 吉卜力 全票x1 (未付款)
            
            # 李美華 (member_id=3) 的訂單: 2筆
            (3, 960, '2025-12-03 16:45:00', 'Paid'),    # order_id=4: 梵谷展 全票x2
            (3, 550, '2025-12-08 11:30:00', 'Paid'),    # order_id=5: teamLab 全票x1
            
            # 張志豪 (member_id=4) 的訂單: 2筆
            (4, 660, '2025-12-02 13:00:00', 'Paid'),    # order_id=6: 角落小夥伴 全票x1+兒童票x1
            (4, 800, '2025-12-07 15:30:00', 'Cancelled'), # order_id=7: 寶可夢 全票x1+兒童票x1 (已取消)
        ]
        
        for order in orders_data:
            cursor.execute("""
                INSERT INTO Orders (member_id, total_amount, order_date, status) 
                VALUES (?, ?, ?, ?)
            """, order)


        print("新增票券")
        # 根據訂單內容生成對應票券
        tickets_data = [
            # ticket_uuid, order_id, ticket_type_id, session_id, status, used_at
            
            # 訂單1 (王小明): 莫內展 全票x2, session_id=13 (12/25 10:00), ticket_type_id=11 (莫內全票)
            (str(uuid.uuid4()), 1, 11, 13, 'Unused', None),
            (str(uuid.uuid4()), 1, 11, 13, 'Unused', None),
            
            # 訂單2 (王小明): 蠟筆小新 全票x2, session_id=23 (12/27 10:00), ticket_type_id=19 (蠟筆小新全票)
            (str(uuid.uuid4()), 2, 19, 23, 'Unused', None),
            (str(uuid.uuid4()), 2, 19, 23, 'Unused', None),
            
            # 訂單3 (王小明): 吉卜力 全票x1, session_id=29 (1/15 10:00), ticket_type_id=23 (吉卜力全票)
            # 注意: 這筆訂單未付款，但票券仍會生成 (狀態可能不同，視系統設計)
            (str(uuid.uuid4()), 3, 23, 29, 'Unused', None),
            
            # 訂單4 (李美華): 梵谷展 全票x2, session_id=16 (12/28 10:00), ticket_type_id=13 (梵谷全票)
            (str(uuid.uuid4()), 4, 13, 16, 'Unused', None),
            (str(uuid.uuid4()), 4, 13, 16, 'Unused', None),
            
            # 訂單5 (李美華): teamLab 全票x1, session_id=51 (2/10 10:00), ticket_type_id=39 (teamLab全票)
            (str(uuid.uuid4()), 5, 39, 48, 'Unused', None),
            
            # 訂單6 (張志豪): 角落小夥伴 全票x1+兒童票x1, session_id=27 (1/10 10:00)
            # ticket_type_id=21 (角落全票), ticket_type_id=22 (角落兒童票)
            (str(uuid.uuid4()), 6, 21, 27, 'Unused', None),
            (str(uuid.uuid4()), 6, 22, 27, 'Unused', None),
        ]
        
        for ticket in tickets_data:
            cursor.execute("""
                INSERT INTO Tickets (ticket_uuid, order_id, ticket_type_id, session_id, status, used_at) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, ticket)

        conn.commit()
        print("資料庫初始化完成")

    except Exception as e:
        print(f"初始化失敗: {e}")
        import traceback
        traceback.print_exc()
        if 'conn' in locals() and conn: 
            conn.rollback()
    finally:
        if 'conn' in locals() and conn: 
            conn.close()


if __name__ == '__main__':
    init_database()
