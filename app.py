from flask import Flask, render_template, request, redirect, url_for, flash

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
    ambil_semua_barang_keluar
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

    if not id_barang or not jumlah:
        return redirect(url_for("barang_masuk"))

    try:
        id_barang = int(id_barang)
        jumlah = int(jumlah)
    except ValueError:
        return redirect(url_for("barang_masuk"))

    if jumlah <= 0:
        return redirect(url_for("barang_masuk"))

    tambah_barang_masuk(id_barang, jumlah)

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
    id_barang = request.form.get("id_barang")
    jumlah = request.form.get("jumlah")

    if not id_barang or not jumlah:
        flash("Data barang keluar belum lengkap", "error")
        return redirect(url_for("barang_keluar"))

    try:
        id_barang = int(id_barang)
        jumlah = int(jumlah)
    except ValueError:
        flash("Data barang keluar tidak valid", "error")
        return redirect(url_for("barang_keluar"))

    if jumlah <= 0:
        flash("Jumlah barang keluar harus lebih dari 0", "error")
        return redirect(url_for("barang_keluar"))

    sukses, pesan = tambah_barang_keluar(id_barang, jumlah)

    if sukses:
        flash(pesan, "success")
    else:
        flash(pesan, "error")

    return redirect(url_for("barang_keluar"))


# Buat tabel database saat app dijalankan oleh Heroku/Gunicorn
init_database()

if __name__ == "__main__":
    app.run(debug=True)