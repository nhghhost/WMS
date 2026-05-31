import sqlite3

DB_NAME = "wms.db"


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row

    # Biar foreign key SQLite aktif
    conn.execute("PRAGMA foreign_keys = ON")

    return conn


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS barang (
            id_barang INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_barang TEXT NOT NULL,
            stok INTEGER NOT NULL DEFAULT 0,
            satuan TEXT NOT NULL,
            stok_minimal INTEGER NOT NULL DEFAULT 20,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS barang_masuk (
            id_masuk INTEGER PRIMARY KEY AUTOINCREMENT,
            id_barang INTEGER NOT NULL,
            jumlah INTEGER NOT NULL,
            tanggal TEXT DEFAULT CURRENT_TIMESTAMP,
            keterangan TEXT,
            FOREIGN KEY (id_barang) REFERENCES barang(id_barang) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS barang_keluar (
            id_keluar INTEGER PRIMARY KEY AUTOINCREMENT,
            id_barang INTEGER NOT NULL,
            jumlah INTEGER NOT NULL,
            tanggal TEXT DEFAULT CURRENT_TIMESTAMP,
            keterangan TEXT,
            FOREIGN KEY (id_barang) REFERENCES barang(id_barang) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS barang_masuk (
            id_masuk INTEGER PRIMARY KEY AUTOINCREMENT,
            id_barang INTEGER NOT NULL,
            jumlah INTEGER NOT NULL,
            tanggal TEXT DEFAULT CURRENT_TIMESTAMP,
            keterangan TEXT,
            FOREIGN KEY (id_barang) REFERENCES barang(id_barang) ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS barang_keluar (
            id_keluar INTEGER PRIMARY KEY AUTOINCREMENT,
            id_barang INTEGER NOT NULL,
            jumlah INTEGER NOT NULL,
            tanggal TEXT DEFAULT CURRENT_TIMESTAMP,
            keterangan TEXT,
            FOREIGN KEY (id_barang) REFERENCES barang(id_barang) ON DELETE CASCADE
        )
    """)

    conn.commit()
    conn.close()


def tambah_barang(nama_barang, stok, satuan, stok_minimal=10):
    nama_barang = nama_barang.strip()
    satuan = satuan.strip()

    if cek_barang_sudah_ada(nama_barang):
        return False, "Barang sudah ada di database"

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO barang (nama_barang, stok, satuan, stok_minimal)
            VALUES (?, ?, ?, ?)
        """, (nama_barang, stok, satuan, stok_minimal))

        conn.commit()
        return True, "Barang berhasil ditambahkan"

    except sqlite3.IntegrityError:
        return False, "Barang sudah ada di database"

    finally:
        conn.close()


def ambil_semua_barang():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id_barang, nama_barang, stok, satuan, stok_minimal
        FROM barang
        ORDER BY id_barang DESC
    """)

    data = cursor.fetchall()

    conn.close()
    return data


def hapus_barang(id_barang):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM barang
        WHERE id_barang = ?
    """, (id_barang,))

    conn.commit()
    conn.close()


def barang_masuk(id_barang, jumlah, keterangan=""):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO barang_masuk (id_barang, jumlah, keterangan)
        VALUES (?, ?, ?)
    """, (id_barang, jumlah, keterangan))

    cursor.execute("""
        UPDATE barang
        SET stok = stok + ?
        WHERE id_barang = ?
    """, (jumlah, id_barang))

    conn.commit()
    conn.close()


def tambah_barang_keluar(id_barang, jumlah):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT stok
        FROM barang
        WHERE id_barang = ?
    """, (id_barang,))

    barang = cursor.fetchone()

    if barang is None:
        conn.close()
        return False, "Barang tidak ditemukan"

    if barang["stok"] < jumlah:
        conn.close()
        return False, "Stok tidak cukup untuk barang keluar"

    cursor.execute("""
        INSERT INTO barang_keluar (id_barang, jumlah)
        VALUES (?, ?)
    """, (id_barang, jumlah))

    cursor.execute("""
        UPDATE barang
        SET stok = stok - ?
        WHERE id_barang = ?
    """, (jumlah, id_barang))

    conn.commit()
    conn.close()

    return True, "Barang keluar berhasil ditambahkan"


def ambil_semua_barang_keluar():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            barang_keluar.id_keluar,
            barang_keluar.tanggal,
            barang_keluar.jumlah,
            barang.nama_barang,
            barang.satuan
        FROM barang_keluar
        JOIN barang ON barang_keluar.id_barang = barang.id_barang
        ORDER BY barang_keluar.id_keluar DESC
    """)

    data = cursor.fetchall()

    conn.close()
    return data

def hitung_total_jenis_barang():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM barang
    """)

    hasil = cursor.fetchone()
    conn.close()

    return hasil["total"]


def hitung_barang_masuk_hari_ini():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(jumlah), 0) AS total
        FROM barang_masuk
        WHERE DATE(tanggal) = DATE('now', 'localtime')
    """)

    hasil = cursor.fetchone()
    conn.close()

    return hasil["total"]


def hitung_barang_keluar_hari_ini():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COALESCE(SUM(jumlah), 0) AS total
        FROM barang_keluar
        WHERE DATE(tanggal) = DATE('now', 'localtime')
    """)

    hasil = cursor.fetchone()
    conn.close()

    return hasil["total"]


def hitung_stok_menipis():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM barang
        WHERE stok > 0 AND stok <= stok_minimal
    """)

    hasil = cursor.fetchone()
    conn.close()

    return hasil["total"]


def hitung_stok_habis():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM barang
        WHERE stok = 0
    """)

    hasil = cursor.fetchone()
    conn.close()

    return hasil["total"]


def ambil_barang_stok_bermasalah():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id_barang, nama_barang, stok, satuan, stok_minimal
        FROM barang
        WHERE stok = 0 OR stok <= stok_minimal
        ORDER BY stok ASC, nama_barang ASC
    """)

    data = cursor.fetchall()
    conn.close()

    return data

def tambah_barang_masuk(id_barang, jumlah):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO barang_masuk (id_barang, jumlah)
        VALUES (?, ?)
    """, (id_barang, jumlah))

    cursor.execute("""
        UPDATE barang
        SET stok = stok + ?
        WHERE id_barang = ?
    """, (jumlah, id_barang))

    conn.commit()
    conn.close()


def ambil_semua_barang_masuk():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT 
            barang_masuk.id_masuk,
            barang_masuk.tanggal,
            barang_masuk.jumlah,
            barang.nama_barang,
            barang.satuan
        FROM barang_masuk
        JOIN barang ON barang_masuk.id_barang = barang.id_barang
        ORDER BY barang_masuk.id_masuk DESC
    """)

    data = cursor.fetchall()

    conn.close()
    return data

def cek_barang_sudah_ada(nama_barang):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id_barang
        FROM barang
        WHERE LOWER(TRIM(nama_barang)) = LOWER(TRIM(?))
    """, (nama_barang,))

    data = cursor.fetchone()
    conn.close()

    return data is not None