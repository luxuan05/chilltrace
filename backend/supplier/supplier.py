import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)


# ── Config ────────────────────────────────────────────────────────────────────

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PORT = int(os.getenv("PORT", 5011))
    SSL_CA = os.getenv("SSL_CA")

    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URL is not set in .env")

    if SSL_CA:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {"ssl": {"ca": SSL_CA}},
            "pool_pre_ping": True
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}


# ── App & DB ──────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config.from_object(Config)

db = SQLAlchemy()
db.init_app(app)


# ── Model ─────────────────────────────────────────────────────────────────────

class Supplier(db.Model):
    __tablename__ = "Supplier"

    ID           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    CompanyName  = db.Column(db.String(255), nullable=False)
    Phone        = db.Column(db.String(50), nullable=True)
    PasswordHash = db.Column(db.String(255), nullable=False)
    Address      = db.Column(db.String(255), nullable=True)

    def to_dict(self):
        return {
            "ID":          self.ID,
            "CompanyName": self.CompanyName,
            "Phone":       self.Phone,
            "Address":     self.Address,
        }


with app.app_context():
    db.create_all()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Supplier service is running"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/supplier", methods=["POST"])
def create_supplier():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        company_name  = data.get("CompanyName")
        phone         = data.get("Phone")
        password_hash = data.get("PasswordHash")
        address       = data.get("Address")

        if not company_name:
            return jsonify({"error": "CompanyName is required"}), 400
        if not password_hash:
            return jsonify({"error": "PasswordHash is required"}), 400

        supplier = Supplier(
            CompanyName  = company_name,
            Phone        = phone,
            PasswordHash = password_hash,
            Address      = address,
        )
        db.session.add(supplier)
        db.session.commit()
        return jsonify({"message": "Supplier created successfully", "supplier": supplier.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create supplier", "details": str(e)}), 500


@app.route("/supplier", methods=["GET"])
def get_all_suppliers():
    try:
        suppliers = Supplier.query.all()
        return jsonify([s.to_dict() for s in suppliers]), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve suppliers", "details": str(e)}), 500


@app.route("/supplier/<int:supplier_id>", methods=["GET"])
def get_supplier(supplier_id):
    try:
        supplier = db.session.get(Supplier, supplier_id)
        if not supplier:
            return jsonify({"error": "Supplier not found"}), 404
        return jsonify(supplier.to_dict()), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve supplier", "details": str(e)}), 500


@app.route("/supplier/<int:supplier_id>", methods=["PUT"])
def update_supplier(supplier_id):
    try:
        supplier = db.session.get(Supplier, supplier_id)
        if not supplier:
            return jsonify({"error": "Supplier not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        if "CompanyName" in data:
            supplier.CompanyName = data["CompanyName"]
        if "Phone" in data:
            supplier.Phone = data["Phone"]
        if "PasswordHash" in data:
            supplier.PasswordHash = data["PasswordHash"]
        if "Address" in data:
            supplier.Address = data["Address"]

        db.session.commit()
        return jsonify({"message": "Supplier updated successfully", "supplier": supplier.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update supplier", "details": str(e)}), 500


if __name__ == "__main__":
    print("This flask is for " + os.path.basename(__file__) + ": supplier service...")
    app.run(host="0.0.0.0", port=5011, debug=True)