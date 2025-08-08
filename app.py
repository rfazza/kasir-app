from flask import Flask, render_template, request, redirect, jsonify
from flask_sqlalchemy import SQLAlchemy
import os

app = Flask(__name__)

# Ganti ini dengan DATABASE_URL dari Railway
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL", "postgresql://user:pass@host:port/dbname")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Model Database
class Produk(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nama = db.Column(db.String(100), nullable=False)
    harga = db.Column(db.Integer, nullable=False)

class Transaksi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    produk_id = db.Column(db.Integer, db.ForeignKey('produk.id'), nullable=False)
    jumlah = db.Column(db.Integer, nullable=False)

@app.route('/')
def index():
    produk_list = Produk.query.all()
    return render_template('code.html', produk_list=produk_list)

@app.route('/tambah_produk', methods=['POST'])
def tambah_produk():
    nama = request.form.get('nama')
    harga = request.form.get('harga')

    if nama and harga:
        produk = Produk(nama=nama, harga=int(harga))
        db.session.add(produk)
        db.session.commit()
    return redirect('/')

@app.route('/tambah_transaksi', methods=['POST'])
def tambah_transaksi():
    produk_id = request.form.get('produk_id')
    jumlah = request.form.get('jumlah')

    if produk_id and jumlah:
        transaksi = Transaksi(produk_id=int(produk_id), jumlah=int(jumlah))
        db.session.add(transaksi)
        db.session.commit()
    return redirect('/')

@app.route('/api/produk')
def api_produk():
    produk_list = Produk.query.all()
    return jsonify([{"id": p.id, "nama": p.nama, "harga": p.harga} for p in produk_list])

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000)
