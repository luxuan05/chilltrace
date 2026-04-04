from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy.engine.url import make_url
from flask_cors import CORS

app = Flask(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip().strip('"').strip("'")
SSL_CA = (os.getenv("SSL_CA") or "").strip().strip('"').strip("'")

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL missing in .env")

try:
    make_url(DATABASE_URL)
except Exception:
    raise RuntimeError(f"Invalid DATABASE_URL value: {DATABASE_URL!r}")

app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {'ssl': {'ca': SSL_CA}} if SSL_CA and os.path.exists(SSL_CA) else {},
    'pool_pre_ping': True,
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

CORS(app)
db = SQLAlchemy(app)

# ============================================================================
# DATABASE MODEL
# ============================================================================

class Inventory(db.Model):
    __tablename__ = 'Inventory'

    ItemID          = db.Column('ItemID',          db.Integer, primary_key=True)
    SupplierID      = db.Column('SupplierID',      db.Integer, nullable=False)
    Name            = db.Column('Name',            db.String(255), nullable=False)
    Qty             = db.Column('Qty',             db.Integer, nullable=False)
    Price           = db.Column('Price',           db.Float, nullable=False)
    Category        = db.Column('Category',        db.String(100))
    Unit            = db.Column('Unit',            db.String(50))
    Description     = db.Column('Description',     db.Text)
    MinTemperature  = db.Column('MinTemperature',  db.Float)
    MaxTemperature  = db.Column('MaxTemperature',  db.Float)

    def to_dict(self):
        return {
            'item_id':          self.ItemID,
            'supplier_id':      self.SupplierID,
            'name':             self.Name,
            'quantity':         self.Qty,
            'price':            self.Price,
            'category':         self.Category,
            'unit':             self.Unit,
            'description':      self.Description,
            'min_temperature':  self.MinTemperature,
            'max_temperature':  self.MaxTemperature,
        }

# ============================================================================
# ITEMS — CRUD
# ============================================================================

@app.route('/api/inventory/items', methods=['GET'])
def get_items():
    """Get all items with optional filters: category, supplier_id"""
    category    = request.args.get('category')
    supplier_id = request.args.get('supplier_id', type=int)

    query = Inventory.query
    if category:
        query = query.filter_by(Category=category)
    if supplier_id:
        query = query.filter_by(SupplierID=supplier_id)

    return jsonify([item.to_dict() for item in query.all()]), 200


@app.route('/api/inventory/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    """Get a single item by ID"""
    item = Inventory.query.get_or_404(item_id)
    return jsonify(item.to_dict()), 200


@app.route('/api/inventory/items', methods=['POST'])
def create_item():
    """Create a new inventory item"""
    data = request.json
    item = Inventory(
        SupplierID     = data['supplier_id'],
        Name           = data['name'],
        Qty            = data['quantity'],
        Price          = data['price'],
        Category       = data.get('category'),
        Unit           = data.get('unit'),
        Description    = data.get('description'),
        MinTemperature = data.get('min_temperature'),
        MaxTemperature = data.get('max_temperature'),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201


@app.route('/api/inventory/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    """Update an existing inventory item"""
    item = Inventory.query.get_or_404(item_id)
    data = request.json

    if 'name'            in data: item.Name           = data['name']
    if 'category'        in data: item.Category       = data['category']
    if 'unit'            in data: item.Unit           = data['unit']
    if 'price'           in data: item.Price          = data['price']
    if 'quantity'        in data: item.Qty            = data['quantity']
    if 'min_temperature' in data: item.MinTemperature = data['min_temperature']
    if 'max_temperature' in data: item.MaxTemperature = data['max_temperature']
    if 'description'     in data: item.Description    = data['description']

    db.session.commit()
    return jsonify(item.to_dict()), 200


@app.route('/api/inventory/items/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    """Delete an inventory item"""
    item = Inventory.query.get_or_404(item_id)
    db.session.delete(item)
    db.session.commit()
    return jsonify({'success': True, 'message': f'Item {item_id} deleted'}), 200

# ============================================================================
# STOCK OPERATIONS
# ============================================================================

@app.route('/inventory/check-availability/<int:item_id>', methods=['GET'])
def check_availability(item_id):
    """
    Check if an item has sufficient stock.
    Query param: ?quantity=N (default 1)
    """
    quantity_requested = request.args.get('quantity', type=int, default=1)
    item = Inventory.query.get(item_id)

    if not item:
        return jsonify({'error': 'Item not found'}), 404

    return jsonify({
        'item_id':            item_id,
        'item_name':          item.Name,
        'stock_available':    item.Qty,
        'quantity_requested': quantity_requested,
        'available':          item.Qty >= quantity_requested,
        'unit_price':         item.Price,
        'supplier_id':        item.SupplierID,
        'temperature_range': {
            'min': item.MinTemperature,
            'max': item.MaxTemperature,
        } if item.MinTemperature is not None else None,
    }), 200


@app.route('/inventory/deduct', methods=['POST'])
def deduct_stock():
    """
    Deduct stock when an order is PAID.
    Expected body: { "item_id": int, "quantity": int }
    Call this endpoint once per order item upon payment confirmation.
    """
    data     = request.json or {}
    item_id  = data.get('item_id')
    quantity = data.get('quantity')

    if not item_id or not quantity:
        return jsonify({'success': False, 'error': 'item_id and quantity are required'}), 400

    item = Inventory.query.get(item_id)

    if not item:
        return jsonify({'success': False, 'error': 'Item not found'}), 404

    if item.Qty < quantity:
        return jsonify({
            'success':            False,
            'error':              'Insufficient stock',
            'stock_available':    item.Qty,
            'quantity_requested': quantity,
        }), 409

    item.Qty -= quantity
    db.session.commit()

    print(f"✅ Deducted {quantity} units from '{item.Name}'. Remaining stock: {item.Qty}")

    return jsonify({
        'success':           True,
        'item_id':           item_id,
        'item_name':         item.Name,
        'quantity_deducted': quantity,
        'remaining_stock':   item.Qty,
    }), 200


@app.route('/inventory/restock', methods=['POST'])
def restock():
    """
    Add stock to an existing item (e.g. supplier delivery received).
    Expected body: { "item_id": int, "quantity": int }
    """
    data     = request.json or {}
    item_id  = data.get('item_id')
    quantity = data.get('quantity')

    if not item_id or not quantity:
        return jsonify({'success': False, 'error': 'item_id and quantity are required'}), 400

    item = Inventory.query.get(item_id)

    if not item:
        return jsonify({'success': False, 'error': 'Item not found'}), 404

    item.Qty += quantity
    db.session.commit()

    print(f"📦 Restocked '{item.Name}' by {quantity} units. New stock: {item.Qty}")

    return jsonify({
        'success':           True,
        'item_id':           item_id,
        'item_name':         item.Name,
        'quantity_added':    quantity,
        'new_stock':         item.Qty,
    }), 200

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/api/inventory/health', methods=['GET'])
def health_check():
    try:
        db.session.execute('SELECT 1')
        total_items = Inventory.query.count()
        low_stock   = Inventory.query.filter(Inventory.Qty < 10).count()

        return jsonify({
            'status':   'healthy',
            'service':  'inventory-service',
            'database': 'connected',
            'stats': {
                'total_items': total_items,
                'low_stock_items': low_stock,
            },
            'timestamp': datetime.utcnow().isoformat(),
        }), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# ============================================================================
# RUN
# ============================================================================

if __name__ == '__main__':
    print(f"Starting inventory service on port 5001...")
    app.run(host='0.0.0.0', port=5001, debug=True)