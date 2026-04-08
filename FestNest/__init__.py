try:
    import pymysql

    pymysql.install_as_MySQLdb()
except Exception:
    # Local/dev can still run with SQLite even if PyMySQL is not installed.
    pass
