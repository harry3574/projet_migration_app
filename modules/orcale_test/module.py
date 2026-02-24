import oracledb
from pathlib import Path

ORACLE_CLIENT = r"C:\oracle\instantclient_11_2"


def run(payload: dict):

    dsn = payload.get("dsn", "LAVAUR_PROD")
    user = payload.get("user", "LAVAUR")
    password = payload.get("password", "LAVAUR")

    try:
        # initialize thick mode
        oracledb.init_oracle_client(lib_dir=ORACLE_CLIENT)

        conn = oracledb.connect(
            user=user,
            password=password,
            dsn=dsn
        )

        cur = conn.cursor()

        cur.execute("""
            SELECT table_name
            FROM user_tables
            ORDER BY table_name
        """)

        tables = [name for (name,) in cur.fetchall()]

        result = {
            "success": True,
            "dsn": dsn,
            "oracle_version": conn.version,
            "table_count": len(tables),
            "tables_preview": tables[:10]
        }

        cur.close()
        conn.close()

        return result

    except Exception as e:

        return {
            "success": False,
            "error": str(e)
        }
