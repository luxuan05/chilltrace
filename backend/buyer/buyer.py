import os
from pathlib import Path

import bcrypt
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)


# ── Config ────────────────────────────────────────────────────────────────────

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SSL_CA = (os.getenv("SSL_CA") or "").strip().strip('"').strip("'")

    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URL is not set in .env")

    if SSL_CA and os.path.exists(SSL_CA):
        SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {"ssl": {"ca": SSL_CA}},
            "pool_pre_ping": True
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}


# ── App & DB ──────────────────────────────────────────────────────────────────

app = Flask(__name__)
app.config.from_object(Config)

from flask_cors import CORS

app = Flask(__name__)
app.config.from_object(Config)
CORS(app) 

db = SQLAlchemy()
db.init_app(app)


# ── Model ─────────────────────────────────────────────────────────────────────

class Buyer(db.Model):
    __tablename__ = "Buyer"

    ID           = db.Column(db.Integer, primary_key=True, autoincrement=True)
    CompanyName  = db.Column(db.String(255), nullable=False)
    Phone        = db.Column(db.String(50),  nullable=True)
    PasswordHash = db.Column(db.String(255), nullable=False)
    Address      = db.Column(db.String(255), nullable=True)
    Email        = db.Column(db.String(255), nullable=False, unique=True)
    ChatID       = db.Column(db.String(45),  nullable=True)

    def to_dict(self):
        return {
            "ID":          self.ID,
            "CompanyName": self.CompanyName,
            "Phone":       self.Phone,
            "Address":     self.Address,
            "Email":       self.Email,
            "ChatID":      self.ChatID,
        }


with app.app_context():
    db.create_all()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Buyer service is running"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/buyer", methods=["POST"])
def create_buyer():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        company_name  = data.get("CompanyName")
        phone         = data.get("Phone")
        password      = data.get("Password")
        address       = data.get("Address")
        email         = data.get("Email")
        chat_id       = data.get("ChatID")

        if not company_name:
            return jsonify({"error": "CompanyName is required"}), 400
        if not email:
            return jsonify({"error": "Email is required"}), 400
        if not password:
            return jsonify({"error": "Password is required"}), 400

        if Buyer.query.filter_by(Email=email).first():
            return jsonify({"error": "Email already registered"}), 409
        
        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        buyer = Buyer(
            CompanyName  = company_name,
            Phone        = phone,
            PasswordHash = password_hash,
            Address      = address,
            Email        = email,
            ChatID       = chat_id,
        )
        db.session.add(buyer)
        db.session.commit()
        return jsonify({"message": "Buyer created successfully", "buyer": buyer.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create buyer", "details": str(e)}), 500


@app.route("/buyer", methods=["GET"])
def get_all_buyers():
    try:
        buyers = Buyer.query.all()
        return jsonify([b.to_dict() for b in buyers]), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve buyers", "details": str(e)}), 500


@app.route("/buyer/<int:buyer_id>", methods=["GET"])
def get_buyer(buyer_id):
    try:
        buyer = db.session.get(Buyer, buyer_id)
        if not buyer:
            return jsonify({"error": "Buyer not found"}), 404
        return jsonify(buyer.to_dict()), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve buyer", "details": str(e)}), 500


@app.route("/buyer/<int:buyer_id>", methods=["PUT"])
def update_buyer(buyer_id):
    try:
        buyer = db.session.get(Buyer, buyer_id)
        if not buyer:
            return jsonify({"error": "Buyer not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        if "CompanyName" in data:
            buyer.CompanyName = data["CompanyName"]
        if "Phone" in data:
            buyer.Phone = data["Phone"]
        if "PasswordHash" in data:
            buyer.PasswordHash = data["PasswordHash"]
        if "Address" in data:
            buyer.Address = data["Address"]
        if "Email" in data:
            buyer.Email = data["Email"]
        if "ChatID" in data:
            buyer.ChatID = data["ChatID"]

        db.session.commit()
        return jsonify({"message": "Buyer updated successfully", "buyer": buyer.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update buyer", "details": str(e)}), 500
    

@app.route("/buyer/login", methods=["POST"])
def login_buyer():
    try:
        data = request.get_json()
        email    = data.get("Email")
        password = data.get("Password")

        if not email or not password:
            return jsonify({"error": "Email and Password are required"}), 400

        buyer = Buyer.query.filter_by(Email=email).first()
        if not buyer:
            return jsonify({"error": "Invalid credentials"}), 401

        import bcrypt
        if not bcrypt.checkpw(password.encode("utf-8"), buyer.PasswordHash.encode("utf-8")):
            return jsonify({"error": "Invalid credentials"}), 401

        return jsonify({"message": "Login successful", "role": "buyer", "user": buyer.to_dict()}), 200

    except Exception as e:
        return jsonify({"error": "Login failed", "details": str(e)}), 500


if __name__ == "__main__":
    print("This flask is for " + os.path.basename(__file__) + ": buyer service...")
    app.run(host="0.0.0.0", port=5012, debug=True)