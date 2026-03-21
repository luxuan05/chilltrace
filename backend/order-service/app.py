from datetime import datetime
from flask import Flask, jsonify, request

from config import Config
from database import db
from models import Orders, OrderItem

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

VALID_STATUSES = {
    "PENDING",
    "RECEIVED",
    "PAID",
    "SCHEDULED",
    "IN_TRANSIT",
    "DELIVERED",
    "CANCELLED",
    "FAILED",
    "FAILED_TEMP_BREACH"
}


with app.app_context():
    db.create_all()


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Order service is running"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/orders", methods=["POST"])
def create_order():
    try:
        data = request.get_json()

        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        customer_id = data.get("CustomerID")
        supplier_id = data.get("SupplierId")
        scheduled_date_str = data.get("ScheduledDate")
        items = data.get("OrderItems", [])

        if customer_id is None:
            return jsonify({"error": "CustomerID is required"}), 400

        if supplier_id is None:
            return jsonify({"error": "SupplierId is required"}), 400

        if not isinstance(items, list) or len(items) == 0:
            return jsonify({"error": "OrderItems must be a non-empty list"}), 400

        scheduled_date = None
        if scheduled_date_str:
            try:
                scheduled_date = datetime.strptime(scheduled_date_str, "%Y-%m-%d").date()
            except ValueError:
                return jsonify({"error": "ScheduledDate must be in YYYY-MM-DD format"}), 400

        total_price = 0.0
        parsed_items = []

        for item in items:
            item_id = item.get("ItemID")
            quantity = item.get("Quantity")
            unit_price = item.get("UnitPrice")

            if item_id is None:
                return jsonify({"error": "Each item must have ItemID"}), 400

            if quantity is None or not isinstance(quantity, int) or quantity <= 0:
                return jsonify({"error": "Each item must have Quantity as integer > 0"}), 400

            if unit_price is None or unit_price < 0:
                return jsonify({"error": "Each item must have UnitPrice >= 0"}), 400

            total_price += quantity * unit_price
            parsed_items.append({
                "ItemID": item_id,
                "Quantity": quantity,
                "UnitPrice": unit_price
            })

        new_order = Orders(
            CustomerID=customer_id,
            SupplierId=supplier_id,
            OrderStatus="RECEIVED",
            TotalPrice=total_price,
            ScheduledDate=scheduled_date
        )

        db.session.add(new_order)
        db.session.flush()

        for item in parsed_items:
            order_item = OrderItem(
                OrderID=new_order.ID,
                ItemID=item["ItemID"],
                Quantity=item["Quantity"],
                UnitPrice=item["UnitPrice"]
            )
            db.session.add(order_item)

        db.session.commit()

        return jsonify({
            "message": "Order created successfully",
            "order": new_order.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "Failed to create order",
            "details": str(e)
        }), 500


@app.route("/orders", methods=["GET"])
def get_all_orders():
    try:
        orders = Orders.query.all()
        return jsonify([order.to_dict() for order in orders]), 200
    except Exception as e:
        return jsonify({
            "error": "Failed to retrieve orders",
            "details": str(e)
        }), 500


@app.route("/orders/<int:order_id>", methods=["GET"])
def get_order_by_id(order_id):
    try:
        order = Orders.query.get(order_id)

        if not order:
            return jsonify({"error": "Order not found"}), 404

        return jsonify(order.to_dict()), 200

    except Exception as e:
        return jsonify({
            "error": "Failed to retrieve order",
            "details": str(e)
        }), 500


@app.route("/orders/<int:order_id>/status", methods=["PUT"])
def update_order_status(order_id):
    try:
        order = Orders.query.get(order_id)

        if not order:
            return jsonify({"error": "Order not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        new_status = data.get("OrderStatus")
        if not new_status:
            return jsonify({"error": "OrderStatus is required"}), 400

        new_status = str(new_status).upper()

        if new_status not in VALID_STATUSES:
            return jsonify({
                "error": "Invalid OrderStatus",
                "allowed_statuses": sorted(list(VALID_STATUSES))
            }), 400

        order.OrderStatus = new_status
        db.session.commit()

        return jsonify({
            "message": "Order status updated successfully",
            "order": order.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "Failed to update order status",
            "details": str(e)
        }), 500


@app.route("/orders/<int:order_id>/cancel", methods=["PUT"])
def cancel_order(order_id):
    try:
        order = Orders.query.get(order_id)

        if not order:
            return jsonify({"error": "Order not found"}), 404

        if order.OrderStatus in {"DELIVERED", "CANCELLED"}:
            return jsonify({
                "error": f"Cannot cancel order with status {order.OrderStatus}"
            }), 400

        order.OrderStatus = "CANCELLED"
        db.session.commit()

        return jsonify({
            "message": "Order cancelled successfully",
            "order": order.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "Failed to cancel order",
            "details": str(e)
        }), 500


@app.route("/orders/<int:order_id>/items", methods=["GET"])
def get_order_items(order_id):
    try:
        order = Orders.query.get(order_id)

        if not order:
            return jsonify({"error": "Order not found"}), 404

        items = OrderItem.query.filter_by(OrderID=order_id).all()

        return jsonify({
            "OrderID": order_id,
            "OrderItems": [item.to_dict() for item in items]
        }), 200

    except Exception as e:
        return jsonify({
            "error": "Failed to retrieve order items",
            "details": str(e)
        }), 500


@app.route("/orders/<int:order_id>/items", methods=["POST"])
def add_order_item(order_id):
    try:
        order = Orders.query.get(order_id)

        if not order:
            return jsonify({"error": "Order not found"}), 404

        data = request.get_json()
        if not data:
            return jsonify({"error": "Request body must be JSON"}), 400

        item_id = data.get("ItemID")
        quantity = data.get("Quantity")
        unit_price = data.get("UnitPrice")

        if item_id is None:
            return jsonify({"error": "ItemID is required"}), 400

        if quantity is None or not isinstance(quantity, int) or quantity <= 0:
            return jsonify({"error": "Quantity must be an integer > 0"}), 400

        if unit_price is None or unit_price < 0:
            return jsonify({"error": "UnitPrice must be >= 0"}), 400

        new_item = OrderItem(
            OrderID=order_id,
            ItemID=item_id,
            Quantity=quantity,
            UnitPrice=unit_price
        )

        db.session.add(new_item)
        order.TotalPrice += quantity * unit_price
        db.session.commit()

        return jsonify({
            "message": "Order item added successfully",
            "order": order.to_dict()
        }), 201

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "Failed to add order item",
            "details": str(e)
        }), 500


@app.route("/orders/<int:order_id>/items/<int:order_item_id>", methods=["DELETE"])
def delete_order_item(order_id, order_item_id):
    try:
        order = Orders.query.get(order_id)

        if not order:
            return jsonify({"error": "Order not found"}), 404

        item = OrderItem.query.filter_by(ID=order_item_id, OrderID=order_id).first()

        if not item:
            return jsonify({"error": "Order item not found"}), 404

        order.TotalPrice -= item.Quantity * item.UnitPrice
        if order.TotalPrice < 0:
            order.TotalPrice = 0

        db.session.delete(item)
        db.session.commit()

        return jsonify({
            "message": "Order item deleted successfully",
            "order": order.to_dict()
        }), 200

    except Exception as e:
        db.session.rollback()
        return jsonify({
            "error": "Failed to delete order item",
            "details": str(e)
        }), 500


if __name__ == "__main__":
    app.run(debug=True, port=Config.PORT)