import os
import sys
import subprocess
import mysql.connector
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

os.environ["PYTHONUTF8"] = "1"

load_dotenv()

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "127.0.0.1"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
}

TARGET_DB = os.getenv("MYSQL_DB", "local_stats")
DUMP_FILE = os.getenv("MYSQL_DUMP_FILE", "stats_yedek.sql")

POST_IMPORT_SQL = [
    "ALTER TABLE `posts` DROP COLUMN `CommunityOwnedDate`;",
]


def create_db_if_not_exists():
    try:
        cnx = mysql.connector.connect(**DB_CONFIG)
        cursor = cnx.cursor()
        cursor.execute(
            f"CREATE DATABASE IF NOT EXISTS `{TARGET_DB}` "
            "DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
        )
        cursor.close()
        cnx.close()
        print(f"[OK] Database ready: {TARGET_DB}")
    except mysql.connector.Error as err:
        print(f"[ERR] Database creation error: {err}")
        sys.exit(1)


MYSQL_BIN = r"C:\Program Files\MySQL\MySQL Workbench 8.0 CE\mysql.exe"


def import_dump_with_mysql_cli():
    if not os.path.exists(DUMP_FILE):
        print(f"[ERR] Dump file not found: {DUMP_FILE}")
        return False

    command = [
        MYSQL_BIN,
        "-h", DB_CONFIG["host"],
        "-u", DB_CONFIG["user"],
        f"-p{DB_CONFIG['password']}",
        "-P", str(DB_CONFIG["port"]),
        "--default-character-set=utf8mb4",
        TARGET_DB
    ]

    print(f"[INFO] Dump import started: {DUMP_FILE}")

    try:
        with open(DUMP_FILE, "r", encoding="utf-8", errors="ignore") as f:
            subprocess.run(
                command,
                stdin=f,
                capture_output=True,
                text=True,
                check=True
            )
        print("[OK] Dump successfully imported.")
        return True

    except FileNotFoundError:
        print("[ERR] mysql executable not found. Is MySQL Client installed and available?")
        return False

    except subprocess.CalledProcessError as e:
        print("[ERR] MySQL CLI error:")
        print(e.stderr)
        return False


def run_post_import_changes():
    print("[INFO] Post-import SQL operations started...")
    cnx = None
    try:
        cnx = mysql.connector.connect(**DB_CONFIG, database=TARGET_DB)
        cursor = cnx.cursor()

        cursor.execute("SET FOREIGN_KEY_CHECKS=0;")
        for stmt in POST_IMPORT_SQL:
            try:
                cursor.execute(stmt)
                print(f"[OK] {stmt}")
            except mysql.connector.Error as err:
                msg = str(err).lower()
                if ("unknown column" in msg) or ("can't drop" in msg) or ("doesn't exist" in msg):
                    print(f"[SKIP] {stmt} ({err})")
                    continue
                else:
                    print(f"[ERR] {stmt} -> {err}")

        cursor.execute("SET FOREIGN_KEY_CHECKS=1;")
        cnx.commit()
        cursor.close()

        print("[OK] Post-import operations completed.")
        return True

    except mysql.connector.Error as err:
        print(f"[ERR] Connection/SQL error: {err}")
        return False

    finally:
        if cnx:
            cnx.close()
            print("[INFO] MySQL connection closed.")


def main():
    create_db_if_not_exists()

    ok = import_dump_with_mysql_cli()
    if not ok:
        sys.exit(1)

    run_post_import_changes()
    print("[DONE] Setup finished.")


if __name__ == "__main__":
    main()
