from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from datetime import datetime
from openpyxl import Workbook
from io import BytesIO

from Database import (
    init_database,
    tambah_barang,
    ambil_semua_barang,
    hapus_barang,
    tambah_barang_masuk,
    ambil_semua_barang_masuk,
    ambil_data_dashboard,          # <- ganti 6 fungsi hitung dengan 1 query
    ambil_barang_stok_bermasalah,
    tambah_barang_keluar,
    ambil_semua_barang_keluar,
    hapus_barang_masuk,
    update_barang_masuk,
    ambil_barang_masuk_by_id,
    hapus_barang_keluar,
    ambil_laporan_barang_masuk,
    ambil_laporan_barang_keluar,
    ambil_laporan_stok

)

app = Flask(__name__)
app.secret_key = "vjs_wms_secret_key"


@app.route("/")
def dashboard():
    stats = ambil_data_dashboard()          # 1 query, bukan 6
    barang_bermasalah = ambil_barang_stok_bermasalah()

    total_stok_bermasalah = stats["total_stok_menipis"] + stats["total_stok_habis"]

    return render_template(
        "index.html",
        total_jenis_barang=stats["total_jenis_barang"],
        barang_masuk_hari_ini=stats["barang_masuk_hari_ini"],
        barang_keluar_hari_ini=stats["barang_keluar_hari_ini"],
        total_stok_menipis=stats["total_stok_menipis"],
        total_stok_habis=stats["total_stok_habis"],
        total_stok_bermasalah=total_stok_bermasalah,
        barang_bermasalah=barang_bermasalah
    )


@app.route("/stok-barang")
def stok_barang():
    barang_list = ambil_semua_barang()
    return render_template("stok_barang.html", barang_list=barang_list)


@app.route("/tambah-barang", methods=["POST"])
def tambah_barang_route():
    nama_barang = request.form.get("nama_barang")
    stok = request.form.get("stok")
    satuan = request.form.get("satuan")

    if not nama_barang or stok is None or not satuan:
        flash("Data barang belum lengkap", "error")
        return redirect(url_for("stok_barang"))

    try:
        stok = int(stok)
    except ValueError:
        stok = 0

    if stok < 0:
        stok = 0

    sukses, pesan = tambah_barang(nama_barang, stok, satuan)
    flash(pesan, "success" if sukses else "error")
    return redirect(url_for("stok_barang"))


@app.route("/hapus-barang/<int:id_barang>", methods=["POST"])
def hapus_barang_route(id_barang):
    hapus_barang(id_barang)
    return redirect(url_for("stok_barang"))


@app.route("/barang-masuk")
def barang_masuk():
    barang_list = ambil_semua_barang()
    barang_masuk_list = ambil_semua_barang_masuk()
    return render_template(
        "barang_masuk.html",
        barang_list=barang_list,
        barang_masuk_list=barang_masuk_list
    )


@app.route("/tambah-barang-masuk", methods=["POST"])
def tambah_barang_masuk_route():
    id_barang = request.form.get("id_barang")
    jumlah = request.form.get("jumlah")
    tanggal = request.form.get("tanggal")

    if not id_barang or not jumlah or not tanggal:
        return redirect(url_for("barang_masuk"))

    try:
        id_barang = int(id_barang)
        jumlah = int(jumlah)
        tanggal = datetime.strptime(tanggal, "%Y-%m-%d")
    except ValueError as e:
        flash(str(e), "error")
        return redirect(url_for("barang_masuk"))

    if jumlah <= 0:
        return redirect(url_for("barang_masuk"))

    tambah_barang_masuk(id_barang, jumlah, tanggal)
    return redirect(url_for("barang_masuk"))


@app.route("/hapus-barang-masuk/<int:id_masuk>")
def hapus_barang_masuk_route(id_masuk):
    hapus_barang_masuk(id_masuk)
    return redirect(url_for("barang_masuk"))


@app.route("/edit-barang-masuk/<int:id_masuk>")
def edit_barang_masuk(id_masuk):
    data = ambil_barang_masuk_by_id(id_masuk)

    if not data:
        flash("Data tidak ditemukan", "error")
        return redirect(url_for("barang_masuk"))

    barang_list = ambil_semua_barang()
    return render_template(
        "edit_barang_masuk.html",
        data=data,
        barang_list=barang_list
    )


@app.route("/update-barang-masuk/<int:id_masuk>", methods=["POST"])
def update_barang_masuk_route(id_masuk):
    jumlah = request.form.get("jumlah")
    tanggal = request.form.get("tanggal")

    try:
        jumlah = int(jumlah)
        tanggal = datetime.strptime(tanggal, "%Y-%m-%d")
    except ValueError:
        flash("Data tidak valid", "error")
        return redirect(url_for("barang_masuk"))

    sukses, pesan = update_barang_masuk(id_masuk, jumlah, tanggal)
    flash(pesan, "success" if sukses else "error")
    return redirect(url_for("barang_masuk"))


@app.route("/barang-keluar")
def barang_keluar():
    barang_list = ambil_semua_barang()
    barang_keluar_list = ambil_semua_barang_keluar()
    return render_template(
        "barang_keluar.html",
        barang_list=barang_list,
        barang_keluar_list=barang_keluar_list
    )


@app.route("/tambah-barang-keluar", methods=["POST"])
def tambah_barang_keluar_route():
    id_barang = request.form.getlist("id_barang")
    jumlah = request.form.getlist("jumlah")
    tanggal = request.form.get("tanggal")
    jenis_keluar = request.form.getlist("jenis_keluar")
    nama = request.form.get("nama")

    if not id_barang or not jumlah or not tanggal or not jenis_keluar or not nama:
        flash("Data barang keluar belum lengkap", "error")
        return redirect(url_for("barang_keluar"))

    try:
        tanggal = datetime.fromisoformat(tanggal)
    except ValueError:
        flash("Tanggal tidak valid", "error")
        return redirect(url_for("barang_keluar"))

    nama = nama.strip()

    for barang, qty, jenis in zip(id_barang, jumlah, jenis_keluar):
        qty = int(qty)

        if qty <= 0:
            flash("Jumlah harus lebih dari 0", "error")
            return redirect(url_for("barang_keluar"))

        sukses, pesan = tambah_barang_keluar(
            int(barang),
            int(qty),
            tanggal,
            jenis,
            nama
        )

    if not sukses:
        flash(pesan, "error")
        return redirect(url_for("barang_keluar"))
    flash(pesan, "success" if sukses else "error")
    return redirect(url_for("barang_keluar"))


@app.route("/hapus-barang-keluar/<int:id_keluar>")
def hapus_barang_keluar_route(id_keluar):
    hapus_barang_keluar(id_keluar)
    return redirect(url_for("barang_keluar"))


@app.route("/laporan")
def laporan():
    return render_template("laporan.html")

@app.route("/buat-laporan", methods=["POST"])
def buat_laporan_route():

    tanggalAwal = request.form.get("tanggalAwal")
    tanggalAkhir = request.form.get("tanggalAkhir")

    data = ambil_laporan_stok(
        tanggalAwal,
        tanggalAkhir
    )

    wb = Workbook()

    ws = wb.active
    ws.title = "Laporan"

    ws.append([
        "No",
        "Stok Awal",
        "Nama Barang",
        "Jumlah Masuk",
        "Jumlah Keluar",
        "Stok Akhir",
        "Stok Aktual"
    ])

    for i, item in enumerate(data, start=1):

        stok_awal = (
            item["stok_aktual"]
            - item["jumlah_masuk"]
            + item["jumlah_keluar"]
        )

        stok_akhir = (
            stok_awal
            + item["jumlah_masuk"]
            - item["jumlah_keluar"]
        )

        ws.append([
            i,
            stok_awal,
            item["nama_barang"],
            item["jumlah_masuk"],
            item["jumlah_keluar"],
            stok_akhir,
            item["stok_aktual"]
        ])

    output = BytesIO()
    wb.save(output)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=f"Laporan_{tanggalAwal}_{tanggalAkhir}.xlsx",
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# Inisialisasi tabel saat startup
init_database()

if __name__ == "__main__":
    app.run(debug=True)
