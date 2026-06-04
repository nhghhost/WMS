from flask import Flask, render_template, request, redirect, url_for, flash
from datetime import datetime

from Database import (
    init_database,
    tambah_barang,
    ambil_semua_barang,
    hapus_barang,
    tambah_barang_masuk,
    ambil_semua_barang_masuk,
    hitung_total_jenis_barang,
    hitung_barang_masuk_hari_ini,
    hitung_barang_keluar_hari_ini,
    hitung_stok_menipis,
    hitung_stok_habis,
    ambil_barang_stok_bermasalah,
    tambah_barang_keluar,
    ambil_semua_barang_keluar,
    hapus_barang_masuk,
    update_barang_masuk,
    ambil_barang_masuk_by_id,
    hapus_barang_keluar
)

app = Flask(__name__)
app.secret_key = "vjs_wms_secret_key"


@app.route("/")
def dashboard():
    total_jenis_barang = hitung_total_jenis_barang()
    barang_masuk_hari_ini = hitung_barang_masuk_hari_ini()
    barang_keluar_hari_ini = hitung_barang_keluar_hari_ini()

    total_stok_menipis = hitung_stok_menipis()
    total_stok_habis = hitung_stok_habis()
    total_stok_bermasalah = total_stok_menipis + total_stok_habis

    barang_bermasalah = ambil_barang_stok_bermasalah()

    return render_template(
        "index.html",
        total_jenis_barang=total_jenis_barang,
        barang_masuk_hari_ini=barang_masuk_hari_ini,
        barang_keluar_hari_ini=barang_keluar_hari_ini,
        total_stok_menipis=total_stok_menipis,
        total_stok_habis=total_stok_habis,
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

    if sukses:
        flash(pesan, "success")
    else:
        flash(pesan, "error")

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
        print(e)
        return redirect(url_for("barang_masuk"))

    if jumlah <= 0:
        return redirect(url_for("barang_masuk"))

    tambah_barang_masuk(id_barang, jumlah, tanggal)

    return redirect(url_for("barang_masuk"))


@app.route("/hapus-barang-masuk/<int:id_masuk>")
def hapus_barang_masuk_route(id_masuk):
    hapus_barang_masuk(id_masuk)

    return redirect(url_for("barang_masuk"))

@app.route("/hapus-barang-keluar/<int:id_keluar>")
def hapus_barang_keluar_route(id_keluar):
    hapus_barang_keluar(id_keluar)

    return redirect(url_for("barang_keluar"))


@app.route("/barang-keluar")
def barang_keluar():
    barang_list = ambil_semua_barang()
    barang_keluar_list = ambil_semua_barang_keluar()

    return render_template(
        "barang_keluar.html",
        barang_list=barang_list,
        barang_keluar_list=barang_keluar_list
    )

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

    sukses, pesan = update_barang_masuk(
        id_masuk,
        jumlah,
        tanggal
    )

    flash(pesan)

    return redirect(url_for("barang_masuk"))


@app.route("/tambah-barang-keluar", methods=["POST"])
def tambah_barang_keluar_route():
    id_barang = request.form.get("id_barang")
    jumlah = request.form.get("jumlah")
    tanggal = request.form.get("tanggal")
    jenis_keluar = request.form.get("jenis_keluar")
    nama = request.form.get("nama")

    if not id_barang or not jumlah or not tanggal or not jenis_keluar or not nama:
        flash("Data barang keluar belum lengkap", "error")
        return redirect(url_for("barang_keluar"))

    try:
        id_barang = int(id_barang)
        jumlah = int(jumlah)
        tanggal = datetime.fromisoformat(tanggal) 
        jenis_keluar = str(jenis_keluar)
        nama = str(nama)
    except ValueError:
        flash("Data Bermasalah", "error")
        return redirect(url_for("barang_keluar"))

    if jumlah <= 0:
        flash("Jumlah barang keluar harus lebih dari 0", "error")
        return redirect(url_for("barang_keluar"))

    sukses, pesan = tambah_barang_keluar(id_barang, jumlah, tanggal, jenis_keluar, nama)

    if sukses:
        flash(pesan, "success")
    else:
        flash(pesan, "error")

    return redirect(url_for("barang_keluar"))


# Buat tabel database saat app dijalankan oleh Heroku/Gunicorn
init_database()

if __name__ == "__main__":
    app.run(debug=True)