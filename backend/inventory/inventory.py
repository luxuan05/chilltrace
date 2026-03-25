from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timedelta
import os
import uuid
from dotenv import load_dotenv
from pathlib import Path
from sqlalchemy.engine.url import make_url

app = Flask(__name__)

from flask_cors import CORS
CORS(app)

# Read from environment variables
# DATABASE_URL = os.getenv('DATABASE_URL')
# SSL_CA = os.getenv('SSL_CA')
# PORT = int(os.getenv('PORT', 5000))

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)   # single call, force local .env

DATABASE_URL = (os.getenv("DATABASE_URL") or "").strip().strip('"').strip("'")
SSL_CA = (os.getenv("SSL_CA") or "").strip().strip('"').strip("'")
PORT = int((os.getenv("PORT") or "5000").strip())

if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL missing in backend/inventory/.env")

# Validate URL early
try:
    make_url(DATABASE_URL)
except Exception:
    raise RuntimeError(f"Invalid DATABASE_URL value: {DATABASE_URL!r}")

# Configure Flask app
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'connect_args': {
        'ssl': {
            'ca': SSL_CA
        }
    }
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')

db = SQLAlchemy(app)

# ============================================================================
# DATABASE MODELS
# ============================================================================

class Inventory(db.Model):
    """Maps to your existing 'Inventory' table"""
    __tablename__ = 'Inventory'
    
    ItemID = db.Column('ItemID', db.Integer, primary_key=True)
    SupplierID = db.Column('SupplierID', db.Integer, nullable=False)
    Name = db.Column('Name', db.String(255), nullable=False)
    Qty = db.Column('Qty', db.Integer, nullable=False)
    Price = db.Column('Price', db.Float, nullable=False)
    Category = db.Column('Category', db.String(100))
    Unit = db.Column('Unit', db.String(50))
    Description = db.Column('Description', db.Text)
    MinTemperature = db.Column('MinTemperature', db.Float)
    MaxTemperature = db.Column('MaxTemperature', db.Float)
    
    # Additional columns for inventory management
    # qty_reserved = db.Column('qty_reserved', db.Integer, default=0)
    # status = db.Column('status', db.String(50), default='AVAILABLE')
    # spoiled_reason = db.Column('spoiled_reason', db.String(255))
    # spoiled_at = db.Column('spoiled_at', db.DateTime)
    # spoiled_by_delivery_id = db.Column('spoiled_by_delivery_id', db.String(100))
    
    def to_dict(self):
        return {
            'item_id': self.ItemID,
            'supplier_id': self.SupplierID,
            'name': self.Name,
            'quantity_available': self.Qty,
            'price': self.Price,
            'category': self.Category,
            'unit': self.Unit,
            'description': self.Description,
            'min_temperature': self.MinTemperature,
            'max_temperature': self.MaxTemperature,
            # 'status': self.status,
            # 'spoiled_reason': self.spoiled_reason,
            # 'spoiled_at': self.spoiled_at.isoformat() if self.spoiled_at else None,
            # 'spoiled_by_delivery_id': self.spoiled_by_delivery_id
        }

# class Reservation(db.Model):
#     """Tracks stock reservations for orders"""
#     __tablename__ = 'reservations'
    
#     id = db.Column(db.String(100), primary_key=True)
#     item_id = db.Column(db.Integer, db.ForeignKey('items.ItemID'), nullable=False)
#     order_id = db.Column(db.String(100), nullable=False)
#     quantity_reserved = db.Column(db.Integer, nullable=False)
#     status = db.Column(db.String(50), default='ACTIVE')
#     expires_at = db.Column(db.DateTime, nullable=False)
#     created_at = db.Column(db.DateTime, default=datetime.utcnow)
#     committed_at = db.Column(db.DateTime)
    
#     def to_dict(self):
#         return {
#             'reservation_id': self.id,
#             'item_id': self.item_id,
#             'order_id': self.order_id,
#             'quantity_reserved': self.quantity_reserved,
#             'status': self.status,
#             'expires_at': self.expires_at.isoformat(),
#             'created_at': self.created_at.isoformat() if self.created_at else None
#         }

# ============================================================================
# API ENDPOINTS - ITEMS
# ============================================================================

@app.route('/api/inventory/items', methods=['GET'])
def get_items():
    """Get all items with optional filters"""
    category = request.args.get('category')
    status = request.args.get('status')
    supplier_id = request.args.get('supplier_id', type=int)
    
    query = Inventory.query
    if category:
        query = query.filter_by(Category=category)
    if status:
        query = query.filter_by(status=status)
    if supplier_id:
        query = query.filter_by(SupplierID=supplier_id)
    
    items = query.all()
    return jsonify([item.to_dict() for item in items]), 200

@app.route('/inventory/items/<int:item_id>', methods=['GET'])
def get_item(item_id):
    """Get single item by ID"""
    item = Inventory.query.get_or_404(item_id)
    return jsonify(item.to_dict()), 200

@app.route('/api/inventory/items', methods=['POST'])
def create_item():
    """Create new item"""
    data = request.json
    item = Inventory(
        SupplierID=data['supplier_id'],
        Name=data['name'],
        Qty=data['quantity'],
        Price=data['price'],
        Category=data.get('category'),
        Unit=data.get('unit'),
        Description=data.get('description'),
        MinTemperature=data.get('min_temperature'),
        MaxTemperature=data.get('max_temperature'),
        qty_reserved=0,
        status='AVAILABLE'
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(item.to_dict()), 201

@app.route('/inventory/items/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    """Update item"""
    item = Inventory.query.get_or_404(item_id)
    data = request.json
    
    if 'Quantity' in data:
        if 'Operation' in data and data['Operation'] == 'minus':
            item.Qty -= data['Quantity']
    if 'Price' in data:
        item.Price = data['price']
    if 'status' in data:
        item.status = data['status']
    if 'name' in data:
        item.Name = data['name']
    
    db.session.commit()
    return jsonify(item.to_dict()), 200

# ============================================================================
# API ENDPOINTS - STOCK OPERATIONS
# ============================================================================

@app.route('/inventory/check-availability/<string:item_id>', methods=['GET'])
def check_availability(item_id):
    """Check if item has sufficient stock"""
    # data = request.json
    print(item_id)
    item = Inventory.query.get(item_id)
    
    if not item:
        return {'error': 'Item not found'}, 404
    else: 
        return {'ItemID': item_id, 'stock available': item.Qty, "UnitPrice": item.Price, "SupplierID": item.SupplierID}, 200
    # available_qty = item.Qty - item.qty_reserved
    
    # return jsonify({
    #     'available': available_qty >= data['quantity'] and item.status == 'AVAILABLE',
    #     'item': item.to_dict(),
    #     'quantity_available': available_qty,
    #     'quantity_requested': data['quantity'],
    #     'requires_cold_chain': item.MinTemperature is not None,
    #     'temperature_range': {
    #         'min': item.MinTemperature,
    #         'max': item.MaxTemperature
    #     } if item.MinTemperature is not None else None
    # }), 200

@app.route('/api/inventory/reserve', methods=['POST'])
def reserve_stock():
    """Reserve stock for an order"""
    data = request.json
    item = Inventory.query.get(data['item_id'])
    
    if not item:
        return jsonify({'success': False, 'error': 'Item not found'}), 404
    
    available_qty = item.Qty - item.qty_reserved
    
    if available_qty < data['quantity']:
        return jsonify({
            'success': False,
            'error': f'Insufficient stock. Requested: {data["quantity"]}, Available: {available_qty}',
            'quantity_requested': data['quantity'],
            'quantity_available': available_qty
        }), 409
    
    if item.status != 'AVAILABLE':
        return jsonify({
            'success': False,
            'error': f'Item not available. Status: {item.status}'
        }), 409
    
    reservation_id = f"RES-{datetime.utcnow().strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
    
    reservation = Reservation(
        id=reservation_id,
        item_id=data['item_id'],
        order_id=data['order_id'],
        quantity_reserved=data['quantity'],
        status='ACTIVE',
        expires_at=datetime.utcnow() + timedelta(minutes=15)
    )
    
    item.qty_reserved += data['quantity']
    
    db.session.add(reservation)
    db.session.commit()
    
    print(f"✅ Reserved {data['quantity']} units of {item.Name} for order {data['order_id']}")
    
    return jsonify({
        'success': True,
        'reservation_id': reservation_id,
        'item_id': item.ItemID,
        'item_name': item.Name,
        'quantity_reserved': data['quantity'],
        'expires_at': reservation.expires_at.isoformat(),
        'temperature_requirements': {
            'min': item.MinTemperature,
            'max': item.MaxTemperature
        } if item.MinTemperature is not None else None
    }), 200

@app.route('/api/inventory/commit', methods=['POST'])
def commit_reservation():
    """Commit reservation (permanently deduct stock)"""
    data = request.json
    reservation = Reservation.query.get(data['reservation_id'])
    
    if not reservation:
        return jsonify({'success': False, 'error': 'Reservation not found'}), 404
    
    if reservation.status != 'ACTIVE':
        return jsonify({'success': False, 'error': f'Reservation not active. Status: {reservation.status}'}), 400
    
    if reservation.expires_at < datetime.utcnow():
        return jsonify({'success': False, 'error': 'Reservation has expired'}), 400
    
    item = Item.query.get(reservation.item_id)
    item.Qty -= reservation.quantity_reserved
    item.qty_reserved -= reservation.quantity_reserved
    reservation.status = 'COMMITTED'
    reservation.committed_at = datetime.utcnow()
    
    db.session.commit()
    
    print(f"✅ Committed reservation {reservation.id}")
    
    return jsonify({
        'success': True,
        'message': 'Reservation committed',
        'item_id': item.ItemID,
        'item_name': item.Name,
        'quantity_committed': reservation.quantity_reserved,
        'remaining_stock': item.Qty
    }), 200

@app.route('/api/inventory/cancel-reservation', methods=['POST'])
def cancel_reservation():
    """Cancel reservation (return stock)"""
    data = request.json
    reservation = Reservation.query.get(data['reservation_id'])
    
    if not reservation:
        return jsonify({'success': False, 'error': 'Reservation not found'}), 404
    
    if reservation.status != 'ACTIVE':
        return jsonify({'success': False, 'error': f'Reservation already {reservation.status}'}), 400
    
    item = Item.query.get(reservation.item_id)
    item.qty_reserved -= reservation.quantity_reserved
    reservation.status = 'CANCELLED'
    
    db.session.commit()
    
    print(f"✅ Cancelled reservation {reservation.id}")
    
    return jsonify({
        'success': True,
        'message': 'Reservation cancelled',
        'quantity_returned': reservation.quantity_reserved
    }), 200

# ============================================================================
# API ENDPOINTS - TEMPERATURE BREACH
# ============================================================================

@app.route('/api/inventory/items/<int:item_id>/spoil', methods=['PUT'])
def mark_item_spoiled(item_id):
    """Mark item as spoiled due to temperature breach"""
    data = request.json
    item = Inventory.query.get_or_404(item_id)
    
    if item.status == 'SPOILED':
        return jsonify({'success': False, 'error': 'Item already spoiled', 'item': item.to_dict()}), 400
    
    reason = data.get('reason', 'Temperature breach')
    if data.get('current_temp') and data.get('max_allowed'):
        reason = f"{reason} (Temp: {data['current_temp']}°C exceeded max {data['max_allowed']}°C)"
    
    old_status = item.status
    item.status = 'SPOILED'
    item.spoiled_reason = reason
    item.spoiled_at = datetime.utcnow()
    item.spoiled_by_delivery_id = data.get('delivery_id')
    
    db.session.commit()
    
    print(f"🔥 Item {item_id} ({item.Name}) marked as SPOILED")
    print(f"   Previous status: {old_status}")
    print(f"   Reason: {reason}")
    
    return jsonify({
        'success': True,
        'message': f'Item {item_id} marked as spoiled',
        'item': item.to_dict()
    }), 200

@app.route('/api/inventory/items/<int:item_id>/active-orders', methods=['GET'])
def get_active_orders_for_item(item_id):
    """Get all active orders using this item"""
    item = Item.query.get_or_404(item_id)
    
    active_reservations = Reservation.query.filter(
        Reservation.item_id == item_id,
        Reservation.status.in_(['ACTIVE', 'COMMITTED'])
    ).all()
    
    active_orders = [
        {
            'order_id': r.order_id,
            'quantity': r.quantity_reserved,
            'reservation_status': r.status,
            'reservation_id': r.id,
            'created_at': r.created_at.isoformat() if r.created_at else None
        }
        for r in active_reservations
    ]
    
    return jsonify({
        'item_id': item_id,
        'item_name': item.Name,
        'item_status': item.status,
        'active_orders': active_orders,
        'total_active_orders': len(active_orders)
    }), 200

# ============================================================================
# HEALTH CHECK
# ============================================================================

@app.route('/api/inventory/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        db.session.execute('SELECT 1')
        total_items = Item.query.count()
        available_items = Item.query.filter_by(status='AVAILABLE').count()
        spoiled_items = Item.query.filter_by(status='SPOILED').count()
        
        return jsonify({
            'status': 'healthy',
            'service': 'inventory-service',
            'database': 'connected',
            'database_host': 'mysql-28cb5b78-computing-4811.i.aivencloud.com',
            'stats': {
                'total_items': total_items,
                'available_items': available_items,
                'spoiled_items': spoiled_items
            },
            'timestamp': datetime.utcnow().isoformat()
        }), 200
    except Exception as e:
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

# ============================================================================
# DATABASE INITIALIZATION
# ============================================================================

def init_db():
    """Initialize database - add new columns if needed"""
    with app.app_context():
        try:
            # Try to select new columns
            db.session.execute('SELECT qty_reserved FROM items LIMIT 1')
            print("✅ Database columns already exist")
        except:
            # Columns don't exist, add them
            print("📝 Adding new columns to items table...")
            try:
                db.session.execute('''
                    ALTER TABLE items 
                    ADD COLUMN qty_reserved INT DEFAULT 0,
                    ADD COLUMN status VARCHAR(50) DEFAULT 'AVAILABLE',
                    ADD COLUMN spoiled_reason VARCHAR(255),
                    ADD COLUMN spoiled_at DATETIME,
                    ADD COLUMN spoiled_by_delivery_id VARCHAR(100)
                ''')
                db.session.commit()
                print("✅ New columns added successfully")
            except Exception as e:
                print(f"⚠️  Could not add columns: {e}")
                db.session.rollback()
        
        # Create reservations table
        try:
            db.create_all()
            print("✅ Database tables ready")
        except Exception as e:
            print(f"⚠️  Error creating tables: {e}")

# ============================================================================
# RUN APPLICATION
# ============================================================================

if __name__ == '__main__':
    print("This flask is for " + os.path.basename(__file__) + ": payments ...")
    app.run(host='0.0.0.0', port=5001, debug=True)