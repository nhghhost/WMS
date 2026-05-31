import os
import psycopg2
import psycopg2.extras


DATABASE_URL = os.environ.get("DATABASE_URL")


def get_connection():
    if DATABASE_URL:
        conn = psycopg2.connect(DATABASE_URL, sslmode="require")
    else:
        # Untuk local testing kalau belum set DATABASE_URL
        conn = psycopg2.connect(
            host="localhost",
            database="wms_bjs",
            user="postgres",
            password="ISI_PASSWORD_POSTGRES_LOCAL_KAMU",
            port="5432"
        )

    return conn


def init_database():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS barang (
            id_barang SERIAL PRIMARY KEY,
            nama_barang TEXT NOT NULL UNIQUE,
            stok INTEGER NOT NULL DEFAULT 0,
            satuan TEXT NOT NULL,
            stok_minimal INTEGER NOT NULL DEFAULT 20,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS barang_masuk (
            id_masuk SERIAL PRIMARY KEY,
            id_barang INTEGER NOT NULL REFERENCES barang(id_barang) ON DELETE CASCADE,
            jumlah INTEGER NOT NULL,
            tanggal TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            keterangan TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS barang_keluar (
            id_keluar SERIAL PRIMARY KEY,
            id_barang INTEGER NOT NULL REFERENCES barang(id_barang) ON DELETE CASCADE,
            jumlah INTEGER NOT NULL,
            tanggal TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            keterangan TEXT
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


def cek_barang_sudah_ada(nama_barang):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT id_barang
        FROM barang
        WHERE LOWER(TRIM(nama_barang)) = LOWER(TRIM(%s))
    """, (nama_barang,))

    data = cursor.fetchone()

    cursor.close()
    conn.close()

    return data is not None


def tambah_barang(nama_barang, stok, satuan, stok_minimal=20):
    nama_barang = nama_barang.strip()
    satuan = satuan.strip()

    if cek_barang_sudah_ada(nama_barang):
        return False, "Barang sudah ada di database"

    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO barang (nama_barang, stok, satuan, stok_minimal)
            VALUES (%s, %s, %s, %s)
        """, (nama_barang, stok, satuan, stok_minimal))

        conn.commit()
        return True, "Barang berhasil ditambahkan"

    except psycopg2.IntegrityError:
        conn.rollback()
        return False, "Barang sudah ada di database"

    finally:
        cursor.close()
        conn.close()


def ambil_semua_barang():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT id_barang, nama_barang, stok, satuan, stok_minimal
        FROM barang
        ORDER BY id_barang DESC
    """)

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return data


def hapus_barang(id_barang):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        DELETE FROM barang
        WHERE id_barang = %s
    """, (id_barang,))

    conn.commit()

    cursor.close()
    conn.close()


def tambah_barang_masuk(id_barang, jumlah):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO barang_masuk (id_barang, jumlah)
        VALUES (%s, %s)
    """, (id_barang, jumlah))

    cursor.execute("""
        UPDATE barang
        SET stok = stok + %s
        WHERE id_barang = %s
    """, (jumlah, id_barang))

    conn.commit()

    cursor.close()
    conn.close()


def ambil_semua_barang_masuk():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT 
            barang_masuk.id_masuk,
            TO_CHAR(barang_masuk.tanggal, 'YYYY-MM-DD HH24:MI:SS') AS tanggal,
            barang_masuk.jumlah,
            barang.nama_barang,
            barang.satuan
        FROM barang_masuk
        JOIN barang ON barang_masuk.id_barang = barang.id_barang
        ORDER BY barang_masuk.id_masuk DESC
    """)

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return data


def tambah_barang_keluar(id_barang, jumlah):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT stok
        FROM barang
        WHERE id_barang = %s
    """, (id_barang,))

    barang = cursor.fetchone()

    if barang is None:
        cursor.close()
        conn.close()
        return False, "Barang tidak ditemukan"

    if barang["stok"] < jumlah:
        cursor.close()
        conn.close()
        return False, "Stok tidak cukup untuk barang keluar"

    cursor.execute("""
        INSERT INTO barang_keluar (id_barang, jumlah)
        VALUES (%s, %s)
    """, (id_barang, jumlah))

    cursor.execute("""
        UPDATE barang
        SET stok = stok - %s
        WHERE id_barang = %s
    """, (jumlah, id_barang))

    conn.commit()

    cursor.close()
    conn.close()

    return True, "Barang keluar berhasil ditambahkan"


def ambil_semua_barang_keluar():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT 
            barang_keluar.id_keluar,
            TO_CHAR(barang_keluar.tanggal, 'YYYY-MM-DD HH24:MI:SS') AS tanggal,
            barang_keluar.jumlah,
            barang.nama_barang,
            barang.satuan
        FROM barang_keluar
        JOIN barang ON barang_keluar.id_barang = barang.id_barang
        ORDER BY barang_keluar.id_keluar DESC
    """)

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return data


def hitung_total_jenis_barang():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM barang
    """)

    hasil = cursor.fetchone()

    cursor.close()
    conn.close()

    return hasil["total"]


def hitung_barang_masuk_hari_ini():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT COALESCE(SUM(jumlah), 0) AS total
        FROM barang_masuk
        WHERE DATE(tanggal) = CURRENT_DATE
    """)

    hasil = cursor.fetchone()

    cursor.close()
    conn.close()

    return hasil["total"]


def hitung_barang_keluar_hari_ini():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT COALESCE(SUM(jumlah), 0) AS total
        FROM barang_keluar
        WHERE DATE(tanggal) = CURRENT_DATE
    """)

    hasil = cursor.fetchone()

    cursor.close()
    conn.close()

    return hasil["total"]


def hitung_stok_menipis():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM barang
        WHERE stok > 0 AND stok <= stok_minimal
    """)

    hasil = cursor.fetchone()

    cursor.close()
    conn.close()

    return hasil["total"]


def hitung_stok_habis():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT COUNT(*) AS total
        FROM barang
        WHERE stok = 0
    """)

    hasil = cursor.fetchone()

    cursor.close()
    conn.close()

    return hasil["total"]


def ambil_barang_stok_bermasalah():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT id_barang, nama_barang, stok, satuan, stok_minimal
        FROM barang
        WHERE stok = 0 OR stok <= stok_minimal
        ORDER BY stok ASC, nama_barang ASC
    """)

    data = cursor.fetchall()

    cursor.close()
    conn.close()

    return data