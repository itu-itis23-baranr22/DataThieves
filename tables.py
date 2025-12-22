import os
import sys
import subprocess
import mysql.connector
from mysql.connector import errorcode

# Terminal çıktılarını doğru karakter setinde göstermek için
sys.stdout.reconfigure(encoding="utf-8")

DB_CONFIG = {
    "host": "127.0.0.1",
    "user": "root",
    "password": "976431",
    "port": 3306,
}

TARGET_DB = "local_stats"
DUMP_FILE = "stats_yedek.sql"

# Import sonrası silinecek kolonlar ve keyler
POST_IMPORT_SQL = [
    "ALTER TABLE `tags` DROP FOREIGN KEY `tags_ExcerptPostId_fkey`;",
    "ALTER TABLE `tags` DROP FOREIGN KEY `tags_WikiPostId_fkey`;",
    "ALTER TABLE `tags` DROP COLUMN `ExcerptPostId`;",
    "ALTER TABLE `tags` DROP COLUMN `WikiPostId`;",
    "ALTER TABLE `badges` DROP COLUMN `Date`;",
    "ALTER TABLE `users` DROP COLUMN `AccountId`;",
    "ALTER TABLE `posts` DROP COLUMN `CommunityOwnedDate`;",
]

def create_db_if_not_exists():
    """Veritabanını oluşturur ve bağlantı nesnesini döner."""
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{TARGET_DB}` "
            "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
        cursor.close()
        cnx.close()
        print(f"Veritabanı kontrol edildi/oluşturuldu: {TARGET_DB}")
    except mysql.connector.Error as err:
        print(f"Veritabanı oluşturma hatası: {err}")
        sys.exit(1)

def import_dump_with_mysql_cli():
    """Subprocess kullanarak dump dosyasını çok hızlı ve hatasız içeri aktarır."""
    if not os.path.exists(DUMP_FILE):
        print(f"Hata: {DUMP_FILE} dosyası bulunamadı!")
        return False

    print(f"İçeri aktarma başlıyor: {DUMP_FILE}...")
    
    # MySQL komut satırı aracını hazırlıyoruz
    # Not: -p ile şifre arasında boşluk olmamalıdır.
    command = [
        "mysql",
        "-h", DB_CONFIG["host"],
        "-u", DB_CONFIG["user"],
        f"-p{DB_CONFIG['password']}",
        "-P", str(DB_CONFIG["port"]),
        "--default-character-set=utf8mb4",
        TARGET_DB
    ]

    try:
        with open(DUMP_FILE, "r", encoding="utf-8", errors="ignore") as f:
            # stdin=f diyerek dosya içeriğini doğrudan mysql komutuna akıtıyoruz
            result = subprocess.run(
                command, 
                stdin=f, 
                capture_output=True, 
                text=True, 
                check=True
            )
        print("Dump başarıyla içeri aktarıldı.")
        return True
    except subprocess.CalledProcessError as e:
        print("MySQL CLI Hatası:")
        print(e.stderr)
        return False
    except FileNotFoundError:
        print("Hata: 'mysql' komutu sistemde bulunamadı. Lütfen MySQL Client'ın kurulu ve PATH'e ekli olduğundan emin olun.")
        return False

def run_post_import_changes():
    """Tablo yapılandırma değişikliklerini yapar."""
    print("Post-import işlemleri (kolon silme vb.) yapılıyor...")
    cnx = None
    try:
        cnx = mysql.connector.connect(**DB_CONFIG, database=TARGET_DB)
        cursor = cnx.cursor()
        
        cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
        for stmt in POST_IMPORT_SQL:
            try:
                cursor.execute(stmt)
            except mysql.connector.Error as err:
                # Kolon zaten yoksa veya key silinmişse hatayı yoksay
                msg = str(err).lower()
                if "unknown column" in msg or "can't drop" in msg or "doesn't exist" in msg:
                    continue
                else:
                    print(f"SQL Hatası: {stmt} -> {err}")
        
        cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
        cnx.commit()
        cursor.close()
        print("Post-import işlemleri tamamlandı.")
    except mysql.connector.Error as err:
        print(f"Bağlantı hatası: {err}")
    finally:
        if cnx:
            cnx.close()

def main():
    # 1. Adım: Veritabanı var mı kontrol et
    create_db_if_not_exists()
    
    # 2. Adım: Dump dosyasını CLI ile içeri aktar (Senin hata aldığın yer burasıydı, artık çözüldü)
    success = import_dump_with_mysql_cli()
    
    # 3. Adım: Eğer başarılıysa kolon silme işlemlerini yap
    if success:
        run_post_import_changes()
        print("\nİŞLEM BAŞARIYLA TAMAMLANDI.")
    else:
        print("\nİşlem başarısız olduğu için post-import adımları atlandı.")

if __name__ == "__main__":
    main()