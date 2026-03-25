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

from flask_cors import CORS

app = Flask(__name__)
app.config.from_object(Config)
CORS(app) 

db = SQLAlchemy()
db.init_app(app)


# ── Model ─────────────────────────────────────────────────────────────────────

class Driver(db.Model):
    __tablename__ = "Driver"

    ID        = db.Column(db.Integer,      primary_key=True, autoincrement=True)
    Name      = db.Column(db.String(255),  nullable=False)
    VehicleNo = db.Column(db.String(100),  nullable=True)
    Phone     = db.Column(db.String(50),   nullable=True)
    Address   = db.Column(db.String(255),  nullable=True)
    Email        = db.Column(db.String(255), nullable=True, unique=True)   # add
    PasswordHash = db.Column(db.String(255), nullable=True)        

    def to_dict(self):
        return {
            "ID":        self.ID,
            "Name":      self.Name,
            "VehicleNo": self.VehicleNo,
            "Phone":     self.Phone,
            "Address":   self.Address,
            "Email":     self.Email,
        }


with app.app_context():
    db.create_all()


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Driver service is running"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/driver", methods=["POST"])
def create_driver():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        name       = data.get("Name")
        vehicle_no = data.get("VehicleNo")
        phone      = data.get("Phone")
        address    = data.get("Address")
        email      = data.get("Email")
        password   = data.get("Password")

        if not name:
            return jsonify({"error": "Name is required"}), 400
        if not email:
            return jsonify({"error": "Email is required"}), 400
        if not password:
            return jsonify({"error": "Password is required"}), 400

        if Driver.query.filter_by(Email=email).first():
            return jsonify({"error": "Email already registered"}), 409

        password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

        driver = Driver(
            Name      = name,
            VehicleNo = vehicle_no,
            Phone     = phone,
            Address   = address,
            Email    = email,
            Password_Hash = password_hash,
        )
        db.session.add(driver)
        db.session.commit()
        return jsonify({"message": "Driver created successfully", "driver": driver.to_dict()}), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to create driver", "details": str(e)}), 500


@app.route("/driver", methods=["GET"])
def get_all_drivers():
    try:
        drivers = Driver.query.all()
        return jsonify([d.to_dict() for d in drivers]), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve drivers", "details": str(e)}), 500


@app.route("/driver/<int:driver_id>", methods=["GET"])
def get_driver(driver_id):
    try:
        driver = db.session.get(Driver, driver_id)
        if not driver:
            return jsonify({"error": "Driver not found"}), 404
        return jsonify(driver.to_dict()), 200
    except Exception as e:
        return jsonify({"error": "Failed to retrieve driver", "details": str(e)}), 500


@app.route("/driver/<int:driver_id>", methods=["PUT"])
def update_driver(driver_id):
    try:
        driver = db.session.get(Driver, driver_id)
        if not driver:
            return jsonify({"error": "Driver not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        if "Name" in data:
            driver.Name = data["Name"]
        if "VehicleNo" in data:
            driver.VehicleNo = data["VehicleNo"]
        if "Phone" in data:
            driver.Phone = data["Phone"]
        if "Address" in data:
            driver.Address = data["Address"]

        db.session.commit()
        return jsonify({"message": "Driver updated successfully", "driver": driver.to_dict()}), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": "Failed to update driver", "details": str(e)}), 500
    
@app.route("/driver/login", methods=["POST"])
def login_driver():
    try:
        data = request.get_json()
        email    = data.get("Email")
        password = data.get("Password")

        if not email or not password:
            return jsonify({"error": "Email and Password are required"}), 400

        driver = Driver.query.filter_by(Email=email).first()
        if not driver:
            return jsonify({"error": "Invalid credentials"}), 401

        import bcrypt
        if not bcrypt.checkpw(password.encode("utf-8"), driver.PasswordHash.encode("utf-8")):
            return jsonify({"error": "Invalid credentials"}), 401

        return jsonify({"message": "Login successful", "role": "driver", "user": driver.to_dict()}), 200

    except Exception as e:
        return jsonify({"error": "Login failed", "details": str(e)}), 500

if __name__ == "__main__":
    print("This flask is for " + os.path.basename(__file__) + ": driver service...")
    app.run(host="0.0.0.0", port=5013, debug=True)