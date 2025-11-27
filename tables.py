import mysql.connector
import os
from mysql.connector import errorcode
import sys
sys.stdout.reconfigure(encoding='utf-8')

DB_CONFIG = {
    'host': '127.0.0.1',
    'user': 'admin', 
    'password': '976431', 
    'database': 'local_stats',
    'allow_local_infile': True,
    'auth_plugin':'caching_sha2_password'
}

CSV_FOLDER = 'csvfiles'

TABLES = ['users', 'posts', 'badges', 'comments', 'postHistory', 'postLinks', 'tags', 'votes']

SQL_SCHEMA = """
USE local_stats;
SET FOREIGN_KEY_CHECKS = 0;

DROP TABLE IF EXISTS Votes;
DROP TABLE IF EXISTS PostLinks;
DROP TABLE IF EXISTS PostHistory;
DROP TABLE IF EXISTS Comments;
DROP TABLE IF EXISTS Badges;
DROP TABLE IF EXISTS Tags;
DROP TABLE IF EXISTS Posts;
DROP TABLE IF EXISTS Users;

CREATE TABLE Users (
    Id INT NOT NULL PRIMARY KEY,
    Reputation INT NOT NULL,
    CreationDate DATETIME NOT NULL,
    DisplayName VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    LastAccessDate DATETIME NOT NULL,
    WebsiteUrl VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    Location VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    AboutMe TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    Views INT NOT NULL,
    UpVotes INT NOT NULL,
    DownVotes INT NOT NULL,
    AccountId INT,
    Age INT,
    ProfileImageUrl VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE Posts (
    Id INT NOT NULL PRIMARY KEY,
    PostTypeId INT NOT NULL,
    AcceptedAnswerId INT,
    CreaionDate DATETIME NOT NULL,
    Score INT NOT NULL,
    ViewCount INT,
    Body LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    OwnerUserId INT,
    LasActivityDate DATETIME,
    Title VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    Tags VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    AnswerCount INT,
    CommentCount INT,
    FavoriteCount INT,
    LastEditorUserId INT,
    LastEditDate DATETIME,
    CommunityOwnedDate DATETIME,
    ParentId INT,
    ClosedDate DATETIME,
    OwnerDisplayName VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    LastEditorDisplayName VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    FOREIGN KEY (OwnerUserId) REFERENCES Users(Id),
    FOREIGN KEY (LastEditorUserId) REFERENCES Users(Id),
    FOREIGN KEY (AcceptedAnswerId) REFERENCES Posts(Id),
    FOREIGN KEY (ParentId) REFERENCES Posts(Id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE Badges (
    Id INT NOT NULL PRIMARY KEY,
    UserId INT NOT NULL,
    Name VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
    Date DATETIME NOT NULL,
    FOREIGN KEY (UserId) REFERENCES Users(Id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE Comments (
    Id INT NOT NULL PRIMARY KEY,
    PostId INT NOT NULL,
    Score INT NOT NULL,
    Text TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
    CreationDate DATETIME NOT NULL,
    UserId INT,
    UserDisplayName VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    FOREIGN KEY (PostId) REFERENCES Posts(Id),
    FOREIGN KEY (UserId) REFERENCES Users(Id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE PostHistory (
    Id INT NOT NULL PRIMARY KEY,
    PostHistoryTypeId INT NOT NULL,
    PostId INT NOT NULL,
    RevisionGUID CHAR(36) NOT NULL,
    CreationDate DATETIME NOT NULL,
    UserId INT,
    Text LONGTEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    Comment TEXT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    UserDisplayName VARCHAR(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
    FOREIGN KEY (PostId) REFERENCES Posts(Id),
    FOREIGN KEY (UserId) REFERENCES Users(Id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE PostLinks (
    Id INT NOT NULL PRIMARY KEY,
    CreationDate DATETIME NOT NULL,
    PostId INT NOT NULL,
    RelatedPostId INT NOT NULL,
    LinkTypeId INT NOT NULL,
    FOREIGN KEY (PostId) REFERENCES Posts(Id),
    FOREIGN KEY (RelatedPostId) REFERENCES Posts(Id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE Tags (
    Id INT NOT NULL PRIMARY KEY,
    TagName VARCHAR(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL UNIQUE,
    Count INT NOT NULL,
    ExcerptPostId INT,
    WikiPostId INT,
    FOREIGN KEY (ExcerptPostId) REFERENCES Posts(Id),
    FOREIGN KEY (WikiPostId) REFERENCES Posts(Id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE Votes (
    Id INT NOT NULL PRIMARY KEY,
    PostId INT NOT NULL,
    VoteTypeId INT NOT NULL,
    CreationDate DATETIME NOT NULL,
    UserId INT,
    BountyAmount INT,
    FOREIGN KEY (PostId) REFERENCES Posts(Id),
    FOREIGN KEY (UserId) REFERENCES Users(Id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
"""

def load_data_from_csv():
    cnx = None
    cursor = None
    try:
        print("Veritabanına bağlanılıyor...")
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        print("Bağlantı başarılı.")

        print("Tablolar siliniyor ve yeniden oluşturuluyor...")
        
        # ⚠️ Hata Çözümü: SQL komutlarını noktalı virgülle ayırıp tek tek çalıştırıyoruz
        sql_commands = [cmd.strip() for cmd in SQL_SCHEMA.split(';') if cmd.strip()]
        for command in sql_commands:
            cursor.execute(command)
        
        print("Tablolar başarıyla oluşturuldu.")
        
        print("\nCSV dosyalarından veri yükleme başlatılıyor...")
        
        for table_name in TABLES:
            csv_file_path = os.path.join(CSV_FOLDER, f'{table_name}.csv').replace('\\', '/')
            
            full_path = csv_file_path 
            
            print(f"-> Yükleniyor: {table_name.capitalize()} ({full_path})")

            load_sql = f"""
            LOAD DATA LOCAL INFILE '{full_path}'
            INTO TABLE local_stats.{table_name.capitalize()}
            FIELDS TERMINATED BY ',' 
            ENCLOSED BY '"'
            LINES TERMINATED BY '\\n'
            IGNORE 1 ROWS;
            """
            
            cursor.execute(load_sql)
            cnx.commit()
            print(f"-> {table_name.capitalize()} başarıyla yüklendi.")


        cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
        print("\nVeri yükleme işlemi tamamlandı.")
        
        print("\n--- YÜKLENEN SATIR SAYILARI ---")
        for table_name in TABLES:
            cursor.execute(f"SELECT COUNT(*) FROM {table_name.capitalize()}")
            count = cursor.fetchone()[0]
            print(f"{table_name.capitalize()}: {count} satır")


    except mysql.connector.Error as err:
        print("\nVeritabanı Hatası:")
        if err.errno == errorcode.ER_ACCESS_DENIED_ERROR:
            print("Kullanıcı adı veya şifre yanlış.")
        elif err.errno == errorcode.ER_BAD_DB_ERROR:
            print(f"Veritabanı ({DB_CONFIG['database']}) mevcut değil.")
        elif err.errno == 3948:
             print("HATA 3948: 'local-infile' özelliği sunucu tarafında (my.ini) etkin değil.")
             print("Lütfen MySQL hizmetini manuel olarak yeniden başlattığınızdan emin olun.")
        else:
            print(err)
            
    finally:
        if cursor:
            cursor.close()
        if cnx and cnx.is_connected():
            cnx.close()
            print("MySQL bağlantısı kapatıldı.")

if __name__ == "__main__":
    load_data_from_csv()