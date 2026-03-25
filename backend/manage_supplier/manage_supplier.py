from flask import Flask, request, jsonify
from flask_cors import CORS
import sys, os

from invokes import invoke_http

app = Flask(__name__)
CORS(app)


# ─────────────────────────────────────────────────────────────────────────────
# Health
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "manage_supplier"}), 200


# ─────────────────────────────────────────────────────────────────────────────
# Supplier
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/supplier", methods=["POST"])
def create_supplier():
    if request.is_json:
        try:
            data = request.get_json()
            print("\nReceived create supplier request:", data)

            result, http_status = createSupplier(data)
            if http_status >= 400:
                return jsonify(result), http_status

            print("Successfully created supplier")
            return jsonify({"code": 201, "supplier": result.get("supplier", {})}), 201

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
            print("Error: {}".format(ex_str))
            return jsonify({"code": 500, "message": "manage_supplier.py internal error:", "exception": ex_str}), 500

    return jsonify({"code": 400, "message": "Invalid JSON input: " + str(request.get_data())}), 400


@app.route("/supplier/<int:supplier_id>", methods=["GET"])
def get_supplier(supplier_id):
    try:
        print(f"\nFetching details for supplier {supplier_id}...")

        supplier_result, http_status = getSupplier(supplier_id)
        if http_status >= 400:
            return jsonify(supplier_result), http_status

        inventory_result, http_status = getSupplierInventory(supplier_id)
        if http_status >= 400:
            print(f"Warning: Could not fetch inventory for supplier {supplier_id}")
            inventory_result = []

        return jsonify({
            "code":      200,
            "supplier":  supplier_result,
            "inventory": inventory_result,
        }), 200

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return jsonify({"code": 500, "message": "manage_supplier.py internal error:", "exception": ex_str}), 500


@app.route("/supplier/<int:supplier_id>", methods=["PUT"])
def update_supplier(supplier_id):
    if request.is_json:
        try:
            data = request.get_json()
            print(f"\nReceived update request for supplier {supplier_id}:", data)

            result, http_status = updateSupplier(supplier_id, data)
            if http_status >= 400:
                return jsonify(result), http_status

            print(f"Successfully updated supplier {supplier_id}")
            return jsonify({"code": 200, "supplier": result.get("supplier", {})}), 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
            print("Error: {}".format(ex_str))
            return jsonify({"code": 500, "message": "manage_supplier.py internal error:", "exception": ex_str}), 500

    return jsonify({"code": 400, "message": "Invalid JSON input: " + str(request.get_data())}), 400


# ─────────────────────────────────────────────────────────────────────────────
# Inventory — supplier manages their own items
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/supplier/<int:supplier_id>/inventory", methods=["POST"])
def create_inventory_item(supplier_id):
    if request.is_json:
        try:
            data = request.get_json()
            data["supplier_id"] = supplier_id
            print(f"\nCreating inventory item for supplier {supplier_id}:", data)

            result, http_status = createInventoryItem(data)
            if http_status >= 400:
                return jsonify(result), http_status

            print("Successfully created inventory item")
            return jsonify({"code": 201, "item": result}), 201

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
            print("Error: {}".format(ex_str))
            return jsonify({"code": 500, "message": "manage_supplier.py internal error:", "exception": ex_str}), 500

    return jsonify({"code": 400, "message": "Invalid JSON input: " + str(request.get_data())}), 400


@app.route("/supplier/<int:supplier_id>/inventory", methods=["GET"])
def get_inventory_items(supplier_id):
    try:
        print(f"\nFetching inventory for supplier {supplier_id}...")

        result, http_status = getSupplierInventory(supplier_id)
        if http_status >= 400:
            return jsonify(result), http_status

        return jsonify({"code": 200, "supplier_id": supplier_id, "inventory": result}), 200

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return jsonify({"code": 500, "message": "manage_supplier.py internal error:", "exception": ex_str}), 500


@app.route("/supplier/<int:supplier_id>/inventory/<int:item_id>", methods=["GET"])
def get_inventory_item(supplier_id, item_id):
    try:
        print(f"\nFetching item {item_id} for supplier {supplier_id}...")

        result, http_status = getInventoryItem(item_id)
        if http_status >= 400:
            return jsonify(result), http_status

        return jsonify({"code": 200, "item": result}), 200

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return jsonify({"code": 500, "message": "manage_supplier.py internal error:", "exception": ex_str}), 500


@app.route("/supplier/<int:supplier_id>/inventory/<int:item_id>", methods=["PUT"])
def update_inventory_item(supplier_id, item_id):
    if request.is_json:
        try:
            data = request.get_json()
            print(f"\nUpdating item {item_id} for supplier {supplier_id}:", data)

            result, http_status = updateInventoryItem(item_id, data)
            if http_status >= 400:
                return jsonify(result), http_status

            print(f"Successfully updated item {item_id}")
            return jsonify({"code": 200, "item": result}), 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
            print("Error: {}".format(ex_str))
            return jsonify({"code": 500, "message": "manage_supplier.py internal error:", "exception": ex_str}), 500

    return jsonify({"code": 400, "message": "Invalid JSON input: " + str(request.get_data())}), 400


# ─────────────────────────────────────────────────────────────────────────────
# Orders — supplier views and cancels buyer orders
# ─────────────────────────────────────────────────────────────────────────────

@app.route("/supplier/<int:supplier_id>/orders", methods=["GET"])
def get_supplier_orders(supplier_id):
    """Get all orders that contain items from this supplier."""
    try:
        print(f"\nFetching orders for supplier {supplier_id}...")

        result, http_status = getOrdersBySupplier(supplier_id)
        if http_status >= 400:
            return jsonify(result), http_status

        return jsonify({
            "code":        200,
            "supplier_id": supplier_id,
            "orders":      result,
        }), 200

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return jsonify({"code": 500, "message": "manage_supplier.py internal error:", "exception": ex_str}), 500


@app.route("/supplier/<int:supplier_id>/orders/<int:order_id>/cancel", methods=["PUT"])
def cancel_buyer_order(supplier_id, order_id):
    """
    Supplier cancels a buyer's order — triggers full cancel order flow.
    Buyer email and name are fetched automatically by the cancel order service.
    No request body needed.
    """
    if request.is_json:
        try:
            data = request.get_json()
            print(f"\nSupplier {supplier_id} cancelling order {order_id}...")

                # Fetch intent_id from payment service using order_id
            payment_result, http_status = getPaymentByOrder(order_id)
            if http_status >= 400:
                print(f"Warning: Could not fetch intent_id for order {order_id}: {payment_result}")
                intent_id = ""
            else:
                intent_id = payment_result.get("IntentID", "")

            result, http_status = cancelBuyerOrder(order_id, intent_id)
            if http_status >= 400:
                return jsonify(result), http_status

            print(f"Successfully cancelled order {order_id}")
            return jsonify({
                "code":    200,
                "message": f"Order {order_id} cancelled successfully",
                "result":  result,
            }), 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
            print("Error: {}".format(ex_str))
            return jsonify({"code": 500, "message": "manage_supplier.py internal error:", "exception": ex_str}), 500

    return jsonify({"code": 400, "message": "Invalid JSON input: " + str(request.get_data())}), 400


# ─────────────────────────────────────────────────────────────────────────────
# Service helper functions
# ─────────────────────────────────────────────────────────────────────────────

def createSupplier(data):
    print("Invoking supplier microservice...")
    try:
        result, http_status = invoke_http('http://localhost:5011/supplier', method='POST', json=data)
        if http_status >= 400:
            return {"code": http_status, "message": "Create supplier failed", "details": result}, http_status
        return result, http_status
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "createSupplier internal error", "exception": ex_str}, 500


def getSupplier(supplier_id):
    print("Invoking supplier microservice...")
    try:
        result, http_status = invoke_http('http://localhost:5011/supplier/' + str(supplier_id), method='GET')
        if http_status >= 400:
            return {"code": http_status, "message": "Get supplier failed", "details": result}, http_status
        return result, http_status
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "getSupplier internal error", "exception": ex_str}, 500


def updateSupplier(supplier_id, data):
    print("Invoking supplier microservice...")
    try:
        result, http_status = invoke_http('http://localhost:5011/supplier/' + str(supplier_id), method='PUT', json=data)
        if http_status >= 400:
            return {"code": http_status, "message": "Update supplier failed", "details": result}, http_status
        return result, http_status
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "updateSupplier internal error", "exception": ex_str}, 500


def createInventoryItem(data):
    print("Invoking inventory microservice...")
    try:
        result, http_status = invoke_http('http://localhost:5001/api/inventory/items', method='POST', json=data)
        if http_status >= 400:
            return {"code": http_status, "message": "Create inventory item failed", "details": result}, http_status
        return result, http_status
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "createInventoryItem internal error", "exception": ex_str}, 500


def getSupplierInventory(supplier_id):
    print("Invoking inventory microservice...")
    try:
        result, http_status = invoke_http(
            'http://localhost:5001/api/inventory/items?supplier_id=' + str(supplier_id),
            method='GET',
        )
        if http_status >= 400:
            return {"code": http_status, "message": "Get inventory failed", "details": result}, http_status
        return result, http_status
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "getSupplierInventory internal error", "exception": ex_str}, 500


def getInventoryItem(item_id):
    print("Invoking inventory microservice...")
    try:
        result, http_status = invoke_http(
            'http://localhost:5001/api/inventory/items/' + str(item_id),
            method='GET',
        )
        if http_status >= 400:
            return {"code": http_status, "message": "Get inventory item failed", "details": result}, http_status
        return result, http_status
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "getInventoryItem internal error", "exception": ex_str}, 500


def updateInventoryItem(item_id, data):
    print("Invoking inventory microservice...")
    try:
        result, http_status = invoke_http(
            'http://localhost:5001/inventory/items/' + str(item_id),
            method='PUT',
            json=data,
        )
        if http_status >= 400:
            return {"code": http_status, "message": "Update inventory item failed", "details": result}, http_status
        return result, http_status
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "updateInventoryItem internal error", "exception": ex_str}, 500


def getOrdersBySupplier(supplier_id):
    print("Invoking order microservice...")
    try:
        result, http_status = invoke_http('http://localhost:5002/orders', method='GET')
        if http_status >= 400:
            return {"code": http_status, "message": "Get orders failed", "details": result}, http_status

        all_orders = result if isinstance(result, list) else []
        supplier_orders = [o for o in all_orders if o.get("SupplierId") == supplier_id]
        return supplier_orders, 200

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "getOrdersBySupplier internal error", "exception": ex_str}, 500


def getPaymentByOrder(order_id):
    print("Invoking payment microservice...")
    try:
        result, http_status = invoke_http(
            'http://localhost:5004/payment/order/' + str(order_id),
            method='GET',
        )
        if http_status >= 400:
            return {"code": http_status, "message": "Get payment failed", "details": result}, http_status
        return result, http_status
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "getPaymentByOrder internal error", "exception": ex_str}, 500


def cancelBuyerOrder(order_id, intent_id):
    print("Invoking cancel order composite service...")
    try:
        result, http_status = invoke_http(
            'http://localhost:5009/cancelorder/' + str(order_id),
            method='PUT',
            json={
                "intent_id": intent_id,
            },
        )
        if http_status >= 400:
            return {"code": http_status, "message": "Cancel order failed", "details": result}, http_status
        return result, http_status
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "cancelBuyerOrder internal error", "exception": ex_str}, 500


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("This is flask " + os.path.basename(__file__) + " for managing a supplier...")
    app.run(host="0.0.0.0", port=5010, debug=True)