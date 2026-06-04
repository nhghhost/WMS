import os
import psycopg2
import psycopg2.extras


DATABASE_URL = os.environ.get("DATABASE_URL")


import os
import psycopg2
import psycopg2.extras

DATABASE_URL = os.environ.get("DATABASE_URL")

def get_connection():

    if DATABASE_URL:
        return psycopg2.connect(
            DATABASE_URL,
            sslmode="require"
        )

    return psycopg2.connect(
        host="localhost",
        database="wms",
        user="postgres",
        password="245677"
    )


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

            id_barang INTEGER NOT NULL
                REFERENCES barang(id_barang)
                ON DELETE CASCADE,

            jumlah INTEGER NOT NULL,

            tanggal TIMESTAMP NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS barang_keluar (
            id_keluar SERIAL PRIMARY KEY,

            id_barang INTEGER NOT NULL
                REFERENCES barang(id_barang)
                ON DELETE CASCADE,

            jumlah INTEGER NOT NULL,

            tanggal TIMESTAMP NOT NULL,
                   
            nama VARCHAR(50) NOT NULL,

            jenis_keluar VARCHAR(20) NOT NULL
        )
    """)

    cursor.execute("""
        ALTER TABLE barang_keluar
        ADD COLUMN IF NOT EXISTS nama VARCHAR(50)
        ADD COLUMN IF NOT EXISTS jenis_keluar VARCHAR(20)
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

        cursor.close()
        conn.close()

        return True, "Barang berhasil ditambahkan"

    except psycopg2.IntegrityError:
        conn.rollback()
        cursor.close()
        conn.close()

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


def tambah_barang_masuk(id_barang, jumlah, tanggal):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        INSERT INTO barang_masuk (
            id_barang,
            jumlah,
            tanggal
        )
        VALUES (%s, %s, %s)
    """, (id_barang, jumlah, tanggal)
    )

    cursor.execute("""
        UPDATE barang
        SET stok = stok + %s
        WHERE id_barang = %s
    """, (jumlah, id_barang)
    )

    conn.commit()

    cursor.close()
    conn.close()


def ambil_semua_barang_masuk():
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT 
            barang_masuk.id_masuk,
            TO_CHAR(barang_masuk.tanggal, 'DD-MM-YYYY') AS tanggal,
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

def update_barang_masuk(id_masuk, jumlah_baru, tanggal_baru):

    conn = get_connection()

    cursor = conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    )

    try:

        cursor.execute("""
            SELECT *
            FROM barang_masuk
            WHERE id_masuk = %s
        """, (id_masuk,))

        data_lama = cursor.fetchone()

        if not data_lama:
            cursor.close()
            conn.close()

            return False, "Data tidak ditemukan"

        id_barang = data_lama["id_barang"]
        jumlah_lama = data_lama["jumlah"]

        # rollback stok lama
        cursor.execute("""
            UPDATE barang
            SET stok = stok - %s
            WHERE id_barang = %s
        """, (jumlah_lama, id_barang))

        # update transaksi
        cursor.execute("""
            UPDATE barang_masuk
            SET jumlah = %s,
                tanggal = %s
            WHERE id_masuk = %s
        """, (
            jumlah_baru,
            tanggal_baru,
            id_masuk
        ))

        # tambah stok baru
        cursor.execute("""
            UPDATE barang
            SET stok = stok + %s
            WHERE id_barang = %s
        """, (
            jumlah_baru,
            id_barang
        ))

        conn.commit()

        cursor.close()
        conn.close()

        return True, "Data berhasil diubah"

    except Exception as e:
        conn.rollback()

        cursor.close()
        conn.close()

        return False, str(e)

    finally:
        cursor.close()
        conn.close()

def ambil_barang_masuk_by_id(id_masuk):
    conn = get_connection()

    cursor = conn.cursor(
        cursor_factory=psycopg2.extras.RealDictCursor
    )

    cursor.execute("""
        SELECT *
        FROM barang_masuk
        WHERE id_masuk = %s
    """, (id_masuk,))

    data = cursor.fetchone()

    cursor.close()
    conn.close()

    return data

def hapus_barang_masuk(id_masuk):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT *
        FROM barang_masuk
        WHERE id_masuk = %s
    """, (id_masuk,))

    data = cursor.fetchone()

    if data:
        cursor.execute("""
            UPDATE barang
            SET stok = stok - %s
            WHERE id_barang = %s
        """, (data["jumlah"], data["id_barang"]))

        cursor.execute("""
            DELETE FROM barang_masuk
            WHERE id_masuk = %s
        """, (id_masuk,))

    conn.commit()

    cursor.close()
    conn.close()


def hapus_barang_keluar(id_keluar):
    conn = get_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cursor.execute("""
        SELECT *
        FROM barang_keluar
        WHERE id_keluar = %s
    """, (id_keluar,))

    data = cursor.fetchone()

    if data:
        cursor.execute("""
            UPDATE barang
            SET stok = stok + %s
            WHERE id_barang = %s
        """, (data["jumlah"], data["id_barang"]))

        cursor.execute("""
            DELETE FROM barang_keluar
            WHERE id_keluar = %s
        """, (id_keluar,))

    conn.commit()

    cursor.close()
    conn.close()



def tambah_barang_keluar(id_barang, jumlah, tanggal, jenis_keluar, nama):
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
        INSERT INTO barang_keluar (id_barang, jumlah, tanggal, jenis_keluar, nama)
        VALUES (%s, %s, %s, %s, %s)
    """, (id_barang, jumlah, tanggal, jenis_keluar, nama))

    if jenis_keluar == "sebagian":
        cursor.execute("""
            UPDATE barang
            SET stok = stok
            WHERE id_barang = %s
        """, (id_barang,))
    elif jenis_keluar == "pinjam":
        cursor.execute("""
            UPDATE barang
            SET stok = stok - %s
            WHERE id_barang = %s
        """, (jumlah, id_barang))
    elif jenis_keluar == "habis":
        cursor.execute("""
            UPDATE barang
            SET stok = stok - %s
            WHERE id_barang = %s
        """, (jumlah, id_barang))
    else:
        cursor.close()
        conn.close()
        return False, "Data Bermasalah"

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
            TO_CHAR(barang_keluar.tanggal, 'DD-MM-YYYY HH24:MI:SS') AS tanggal,
            barang_keluar.jumlah,
            barang_keluar.jenis_keluar,
            barang_keluar.nama,
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