from contextlib import contextmanager
import os
import psycopg2
import psycopg2.extras

# Ambil URL Database dari Environment Vercel atau Gunakan Localhost jika kosong
DATABASE_URL = os.environ.get("DATABASE_URL")


def get_raw_connection():
    """Fungsi helper untuk membuat koneksi ke PostgreSQL."""
    if DATABASE_URL:
        # Menangani format URI postgres:// jika dari platform cloud tua
        db_url = DATABASE_URL
        if db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)

        return psycopg2.connect(db_url, sslmode="require")
    else:
        # Fallback koneksi lokal jika dijalankan di PC sendiri
        return psycopg2.connect(
            host="localhost",
            database="wms",
            user="postgres",
            password="245677",
            port=5432,
        )


@contextmanager
def get_db():
    """Context Manager untuk menggantikan connection_pool.

    Membuka koneksi baru per-request dan menutupnya secara otomatis di
    Serverless Vercel.
    """
    conn = get_raw_connection()
    cursor = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        yield conn, cursor
    except Exception:
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()  # Di Serverless, koneksi wajib ditutup rapat


def init_database():
    with get_db() as (conn, cursor):
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS barang (
                id_barang    SERIAL PRIMARY KEY,
                nama_barang  TEXT    NOT NULL UNIQUE,
                stok         INTEGER NOT NULL DEFAULT 0,
                satuan       TEXT    NOT NULL,
                jenis_keluar VARCHAR(20),
                stok_minimal INTEGER NOT NULL DEFAULT 20,
                created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS barang_masuk (
                id_masuk  SERIAL PRIMARY KEY,
                id_barang INTEGER NOT NULL
                    REFERENCES barang(id_barang) ON DELETE CASCADE,
                jumlah    INTEGER NOT NULL,
                tanggal   TIMESTAMP NOT NULL
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS barang_keluar (
                id_keluar    SERIAL PRIMARY KEY,
                id_barang    INTEGER NOT NULL
                    REFERENCES barang(id_barang) ON DELETE CASCADE,
                jumlah       INTEGER NOT NULL,
                tanggal      TIMESTAMP NOT NULL,
                nama         VARCHAR(50) NOT NULL,
                jenis_keluar VARCHAR(20) NOT NULL
            )
        """)

        # Migrasi idempotent
        cursor.execute(
            "ALTER TABLE barang_keluar ADD COLUMN IF NOT EXISTS nama"
            " VARCHAR(50)"
        )
        cursor.execute(
            "ALTER TABLE barang_keluar ADD COLUMN IF NOT EXISTS jenis_keluar"
            " VARCHAR(20)"
        )
        cursor.execute(
            "ALTER TABLE barang_masuk DROP COLUMN IF EXISTS nama_barang"
        )

        cursor.execute("""
            ALTER TABLE barang
            ADD COLUMN IF NOT EXISTS jenis_keluar VARCHAR(20)
        """)

        conn.commit()


# ---------------------------------------------------------------------------
# Barang
# ---------------------------------------------------------------------------


def cek_barang_sudah_ada(nama_barang):
    with get_db() as (_, cursor):
        cursor.execute(
            """
            SELECT 1 FROM barang
            WHERE LOWER(TRIM(nama_barang)) = LOWER(TRIM(%s))
        """,
            (nama_barang,),
        )
        return cursor.fetchone() is not None


def tambah_barang(nama_barang, stok, satuan, stok_minimal=5):
    nama_barang = nama_barang.strip()
    satuan = satuan.strip()

    if cek_barang_sudah_ada(nama_barang):
        return False, "Barang sudah ada di database"

    try:
        with get_db() as (conn, cursor):
            cursor.execute(
                """
                INSERT INTO barang (nama_barang, stok, satuan, stok_minimal)
                VALUES (%s, %s, %s, %s)
            """,
                (nama_barang, stok, satuan, stok_minimal),
            )
            conn.commit()
        return True, "Barang berhasil ditambahkan"
    except psycopg2.IntegrityError:
        return False, "Barang sudah ada di database"


def ambil_semua_barang():
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT id_barang, nama_barang, stok, satuan, stok_minimal,
                   jenis_keluar
            FROM barang
            ORDER BY nama_barang ASC
        """)
        return cursor.fetchall()


def hapus_barang(id_barang):
    with get_db() as (conn, cursor):
        cursor.execute("DELETE FROM barang WHERE id_barang = %s", (id_barang,))
        conn.commit()


def update_jenis_keluar_default(id_barang, jenis_keluar):
    with get_db() as (conn, cursor):
        cursor.execute(
            """
            UPDATE barang
            SET jenis_keluar = %s
            WHERE id_barang = %s
        """,
            (jenis_keluar or None, id_barang),
        )
        conn.commit()


# ---------------------------------------------------------------------------
# Dashboard
# ---------------------------------------------------------------------------


def ambil_data_dashboard():
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM barang) AS total_jenis_barang,

                (SELECT COALESCE(SUM(jumlah), 0)
                 FROM barang_masuk
                 WHERE DATE(tanggal) = CURRENT_DATE) AS barang_masuk_hari_ini,

                (SELECT COALESCE(SUM(jumlah), 0)
                 FROM barang_keluar
                 WHERE DATE(tanggal) = CURRENT_DATE) AS barang_keluar_hari_ini,

                (SELECT COUNT(*)
                 FROM barang
                 WHERE stok > 0 AND stok <= stok_minimal) AS total_stok_menipis,

                (SELECT COUNT(*)
                 FROM barang
                 WHERE stok = 0) AS total_stok_habis
        """)
        return cursor.fetchone()


def ambil_barang_stok_bermasalah():
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT id_barang, nama_barang, stok, satuan, stok_minimal
            FROM barang
            WHERE stok = 0 OR stok <= stok_minimal
            ORDER BY stok ASC, nama_barang ASC
        """)
        return cursor.fetchall()


def ambil_laporan_stok(tanggal_awal, tanggal_akhir):
    with get_db() as (_, cursor):
        cursor.execute(
            """
            SELECT
                b.id_barang,
                b.nama_barang,
                b.stok AS stok_aktual,

                COALESCE((
                    SELECT SUM(bm.jumlah)
                    FROM barang_masuk bm
                    WHERE bm.id_barang = b.id_barang
                      AND DATE(bm.tanggal) BETWEEN %s AND %s
                ), 0) AS jumlah_masuk,

                COALESCE((
                    SELECT SUM(bk.jumlah)
                    FROM barang_keluar bk
                    WHERE bk.id_barang = b.id_barang
                      AND bk.jenis_keluar = 'habis'
                      AND DATE(bk.tanggal) BETWEEN %s AND %s
                ), 0) AS jumlah_keluar

            FROM barang b
            ORDER BY b.nama_barang
        """,
            (tanggal_awal, tanggal_akhir, tanggal_awal, tanggal_akhir),
        )
        return cursor.fetchall()


# ---------------------------------------------------------------------------
# Barang Masuk
# ---------------------------------------------------------------------------


def tambah_barang_masuk(id_barang, jumlah, tanggal):
    with get_db() as (conn, cursor):
        cursor.execute(
            """
            INSERT INTO barang_masuk (id_barang, jumlah, tanggal)
            VALUES (%s, %s, %s)
        """,
            (id_barang, jumlah, tanggal),
        )
        cursor.execute(
            """
            UPDATE barang SET stok = stok + %s WHERE id_barang = %s
        """,
            (jumlah, id_barang),
        )
        conn.commit()


def ambil_semua_barang_masuk():
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT
                bm.id_masuk,
                TO_CHAR(bm.tanggal, 'DD-MM-YYYY') AS tanggal,
                bm.jumlah,
                b.nama_barang,
                b.satuan
            FROM barang_masuk bm
            JOIN barang b ON bm.id_barang = b.id_barang
            ORDER BY bm.tanggal DESC
        """)
        return cursor.fetchall()


def ambil_barang_masuk_by_id(id_masuk):
    with get_db() as (_, cursor):
        cursor.execute(
            "SELECT * FROM barang_masuk WHERE id_masuk = %s", (id_masuk,)
        )
        return cursor.fetchone()


def update_barang_masuk(id_masuk, jumlah_baru, tanggal_baru):
    try:
        with get_db() as (conn, cursor):
            cursor.execute(
                "SELECT * FROM barang_masuk WHERE id_masuk = %s", (id_masuk,)
            )
            data_lama = cursor.fetchone()

            if not data_lama:
                return False, "Data tidak ditemukan"

            id_barang = data_lama["id_barang"]
            jumlah_lama = data_lama["jumlah"]

            cursor.execute(
                """
                UPDATE barang SET stok = stok - %s + %s WHERE id_barang = %s
            """,
                (jumlah_lama, jumlah_baru, id_barang),
            )

            cursor.execute(
                """
                UPDATE barang_masuk SET jumlah = %s, tanggal = %s WHERE id_masuk = %s
            """,
                (jumlah_baru, tanggal_baru, id_masuk),
            )

            conn.commit()
        return True, "Data berhasil diubah"
    except Exception as e:
        return False, str(e)


def hapus_barang_masuk(id_masuk):
    with get_db() as (conn, cursor):
        cursor.execute(
            "SELECT * FROM barang_masuk WHERE id_masuk = %s", (id_masuk,)
        )
        data = cursor.fetchone()
        if data:
            cursor.execute(
                """
                UPDATE barang SET stok = stok - %s WHERE id_barang = %s
            """,
                (data["jumlah"], data["id_barang"]),
            )
            cursor.execute(
                "DELETE FROM barang_masuk WHERE id_masuk = %s", (id_masuk,)
            )
            conn.commit()


# ---------------------------------------------------------------------------
# Barang Keluar
# ---------------------------------------------------------------------------


def tambah_barang_keluar(id_barang, jumlah, tanggal, jenis_keluar, nama):
    if jenis_keluar not in ("habis", "pinjam", "sebagian"):
        return False, "Jenis keluar tidak valid"

    with get_db() as (conn, cursor):
        cursor.execute(
            "SELECT stok FROM barang WHERE id_barang = %s", (id_barang,)
        )
        barang = cursor.fetchone()

        if barang is None:
            return False, "Barang tidak ditemukan"

        if jenis_keluar in ("habis", "pinjam") and barang["stok"] < jumlah:
            return False, "Stok tidak cukup untuk barang keluar"

        cursor.execute(
            """
            INSERT INTO barang_keluar (id_barang, jumlah, tanggal, jenis_keluar, nama)
            VALUES (%s, %s, %s, %s, %s)
        """,
            (id_barang, jumlah, tanggal, jenis_keluar, nama),
        )

        if jenis_keluar in ("habis", "pinjam"):
            cursor.execute(
                """
                UPDATE barang SET stok = stok - %s WHERE id_barang = %s
            """,
                (jumlah, id_barang),
            )

        conn.commit()

    return True, "Barang keluar berhasil ditambahkan"


def ambil_semua_barang_keluar():
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT
                bk.id_keluar,
                TO_CHAR(bk.tanggal, 'DD-MM-YYYY HH24:MI:SS') AS tanggal,
                bk.jumlah,
                bk.jenis_keluar,
                bk.nama,
                b.nama_barang,
                b.satuan
            FROM barang_keluar bk
            JOIN barang b ON bk.id_barang = b.id_barang
            ORDER BY bk.id_keluar DESC
        """)
        return cursor.fetchall()


def hapus_barang_keluar(id_keluar):
    with get_db() as (conn, cursor):
        cursor.execute(
            "SELECT * FROM barang_keluar WHERE id_keluar = %s", (id_keluar,)
        )
        data = cursor.fetchone()
        if data:
            cursor.execute(
                """
                UPDATE barang SET stok = stok + %s WHERE id_barang = %s
            """,
                (data["jumlah"], data["id_barang"]),
            )
            cursor.execute(
                "DELETE FROM barang_keluar WHERE id_keluar = %s", (id_keluar,)
            )
            conn.commit()


# ---------------------------------------------------------------------------
# Laporan
# ---------------------------------------------------------------------------


def ambil_laporan_barang_masuk(tanggal_awal, tanggal_akhir):
    with get_db() as (_, cursor):
        cursor.execute(
            """
            SELECT bm.tanggal, b.nama_barang, bm.jumlah, b.satuan
            FROM barang_masuk bm
            JOIN barang b ON bm.id_barang = b.id_barang
            WHERE DATE(bm.tanggal) BETWEEN %s AND %s
            ORDER BY bm.tanggal ASC
        """,
            (tanggal_awal, tanggal_akhir),
        )
        return cursor.fetchall()


def ambil_laporan_barang_keluar(tanggal_awal, tanggal_akhir):
    with get_db() as (_, cursor):
        cursor.execute(
            """
            SELECT bk.tanggal, b.nama_barang, bk.jumlah, b.satuan, bk.nama, bk.jenis_keluar
            FROM barang_keluar bk
            JOIN barang b ON bk.id_barang = b.id_barang
            WHERE DATE(bk.tanggal) BETWEEN %s AND %s
              AND bk.jenis_keluar = 'habis'
            ORDER BY bk.tanggal ASC
        """,
            (tanggal_awal, tanggal_akhir),
        )
        return cursor.fetchall()


# ---------------------------------------------------------------------------
# Fungsi hitung individual
# ---------------------------------------------------------------------------


def hitung_total_jenis_barang():
    with get_db() as (_, cursor):
        cursor.execute("SELECT COUNT(*) AS total FROM barang")
        return cursor.fetchone()["total"]


def hitung_barang_masuk_hari_ini():
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT COALESCE(SUM(jumlah), 0) AS total
            FROM barang_masuk WHERE DATE(tanggal) = CURRENT_DATE
        """)
        return cursor.fetchone()["total"]


def hitung_barang_keluar_hari_ini():
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT COALESCE(SUM(jumlah), 0) AS total
            FROM barang_keluar WHERE DATE(tanggal) = CURRENT_DATE
        """)
        return cursor.fetchone()["total"]


def hitung_stok_menipis():
    with get_db() as (_, cursor):
        cursor.execute("""
            SELECT COUNT(*) AS total FROM barang
            WHERE stok > 0 AND stok <= stok_minimal
        """)
        return cursor.fetchone()["total"]


def hitung_stok_habis():
    with get_db() as (_, cursor):
        cursor.execute(
            "SELECT COUNT(*) AS total FROM barang WHERE stok = 0"
        )
        return cursor.fetchone()["total"]
