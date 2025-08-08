# app.py
import os
from datetime import datetime
from flask import Flask, jsonify, request, render_template, abort
from flask_sqlalchemy import SQLAlchemy
from urllib.parse import urlparse

app = Flask(__name__, template_folder="templates")

# DATABASE_URL environment variable expected (Postgres)
DATABASE_URL = os.environ.get("DATABASE_URL") or os.environ.get("DATABASE") or "sqlite:///kasir.db"
# SQLAlchemy expects 'postgresql://', sometimes provider returns 'postgres://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = DATABASE_URL
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

# Models
class Product(db.Model):
    __tablename__ = "products"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False, unique=True)
    price = db.Column(db.Integer, nullable=False)

class Sale(db.Model):
    __tablename__ = "sales"
    id = db.Column(db.Integer, primary_key=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    total = db.Column(db.Integer, nullable=False)
    paid = db.Column(db.Integer, nullable=True)
    change = db.Column(db.Integer, nullable=True)
    items = db.relationship("SaleItem", backref="sale", cascade="all, delete-orphan")

class SaleItem(db.Model):
    __tablename__ = "sale_items"
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey("sales.id"), nullable=False)
    product_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(200), nullable=False)
    price = db.Column(db.Integer, nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

# Create tables on startup (simple)
@app.before_first_request
def create_tables():
    db.create_all()
    # Seed minimal products if empty (keeps original names)
    if Product.query.count() == 0:
        seeds = [
            {"name": "Beras 5kg", "price": 50000},
            {"name": "Minyak Goreng", "price": 15000},
            {"name": "Gula 1kg", "price": 12000},
            {"name": "Telur 1kg", "price": 25000},
        ]
        for s in seeds:
            p = Product(name=s["name"], price=s["price"])
            db.session.add(p)
        db.session.commit()

# Routes
@app.route("/")
def index():
    return render_template("index.html")

# API: products
@app.route("/api/products", methods=["GET"])
def get_products():
    prods = Product.query.order_by(Product.id).all()
    data = [{"id": p.id, "name": p.name, "price": p.price} for p in prods]
    return jsonify(data)

@app.route("/api/products", methods=["POST"])
def create_product():
    j = request.get_json() or {}
    name = j.get("name")
    price = j.get("price")
    if not name or price is None:
        return jsonify({"error": "name and price required"}), 400
    # uniqueness check
    if Product.query.filter_by(name=name).first():
        return jsonify({"error": "product already exists"}), 400
    p = Product(name=name, price=int(price))
    db.session.add(p)
    db.session.commit()
    return jsonify({"id": p.id, "name": p.name, "price": p.price}), 201

@app.route("/api/products/<int:pid>", methods=["PUT"])
def update_product(pid):
    p = Product.query.get_or_404(pid)
    j = request.get_json() or {}
    name = j.get("name")
    price = j.get("price")
    if name:
        p.name = name
    if price is not None:
        p.price = int(price)
    db.session.commit()
    return jsonify({"id": p.id, "name": p.name, "price": p.price})

@app.route("/api/products/<int:pid>", methods=["DELETE"])
def delete_product(pid):
    p = Product.query.get_or_404(pid)
    db.session.delete(p)
    db.session.commit()
    return jsonify({"ok": True})

# API: checkout/save sale
@app.route("/api/checkout", methods=["POST"])
def checkout():
    """
    Expected JSON:
    {
      "items": [{"id": product_id, "name": "...", "price": 12000, "quantity": 2}, ...],
      "total": 24000,
      "paid": 30000   # optional
    }
    """
    j = request.get_json() or {}
    items = j.get("items", [])
    total = j.get("total", 0)
    paid = j.get("paid", None)
    if not items or total is None:
        return jsonify({"error": "items and total required"}), 400

    sale = Sale(total=int(total), paid=int(paid) if paid is not None else None,
                change=(int(paid) - int(total)) if paid is not None else None)
    db.session.add(sale)
    db.session.flush()  # get sale.id

    for it in items:
        si = SaleItem(
            sale_id=sale.id,
            product_id=it.get("id") or 0,
            name=it.get("name", ""),
            price=int(it.get("price", 0)),
            quantity=int(it.get("quantity", 1))
        )
        db.session.add(si)

    db.session.commit()
    return jsonify({"ok": True, "sale_id": sale.id}), 201

# Simple sales report endpoint (by date range)
@app.route("/api/sales", methods=["GET"])
def list_sales():
    # optional ?from=YYYY-MM-DD&to=YYYY-MM-DD
    fr = request.args.get("from")
    to = request.args.get("to")
    q = Sale.query
    if fr:
        try:
            dfr = datetime.fromisoformat(fr)
            q = q.filter(Sale.created_at >= dfr)
        except:
            pass
    if to:
        try:
            dto = datetime.fromisoformat(to)
            q = q.filter(Sale.created_at <= dto)
        except:
            pass
    sales = q.order_by(Sale.created_at.desc()).limit(200).all()
    out = []
    for s in sales:
        out.append({
            "id": s.id,
            "created_at": s.created_at.isoformat(),
            "total": s.total,
            "paid": s.paid,
            "change": s.change,
            "items": [{"name": it.name, "price": it.price, "quantity": it.quantity} for it in s.items]
        })
    return jsonify(out)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
