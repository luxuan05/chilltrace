from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import pika
import sys, os
from dotenv import load_dotenv
from pathlib import Path
from invokes import invoke_http

# ── Environment ───────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

# ── Service URLs ──────────────────────────────────────────────────────────────
PAYMENT_SERVICE_URL   = os.environ.get("PAYMENT_SERVICE_URL")   or "http://payment:5004"
ORDER_SERVICE_URL     = os.environ.get("ORDER_SERVICE_URL")     or "http://order:5002"
INVENTORY_SERVICE_URL = os.environ.get("INVENTORY_SERVICE_URL") or "http://inventory:5001"
BUYER_SERVICE_URL     = os.environ.get("BUYER_SERVICE_URL")     or "http://buyer:5012"

# ── RabbitMQ ──────────────────────────────────────────────────────────────────
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST") or "rabbitmq"
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT") or 5672)

app = Flask(__name__)
CORS(app)

# ============================================================================
# HEALTH
# ============================================================================

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "cancel_order"}), 200

# ============================================================================
# CANCEL ORDER
# ============================================================================

@app.route("/cancelorder/<int:order_id>", methods=["PUT"])
def cancel_order(order_id):
    if not request.is_json:
        return jsonify({"code": 400, "message": "Invalid JSON input: " + str(request.get_data())}), 400

    try:
        data = request.get_json()
        print("\nReceived cancel request for order:", order_id, data)

        # 1. Fetch Stripe intent_id from payment service
        payment_result, payment_status = getPaymentByOrder(order_id)
        if payment_status >= 400 or not payment_result:
            print(f"Warning: Could not fetch intent_id for order {order_id}")
            intent_id = ""
        else:
            intent_id = payment_result

        # 2. Cancel order in order service
        cancel_result, http_status = cancelOrder(order_id)
        if http_status >= 400:
            return jsonify(cancel_result), http_status

        print("Successfully cancelled order")

        order_data  = cancel_result.get("order", {})
        order_items = order_data.get("OrderItems", [])
        total_price = order_data.get("TotalPrice", 0)
        customer_id = order_data.get("CustomerID")

        # 3. Fetch buyer details for notification
        buyer_result, buyer_status = getBuyer(customer_id)
        if buyer_status >= 400:
            print(f"Warning: Could not fetch buyer for CustomerID {customer_id}: {buyer_result}")
            recipient_email = ""
            customer_name   = "Customer"
        else:
            recipient_email = buyer_result.get("Email", "")
            customer_name   = buyer_result.get("CompanyName", "Customer")

        # 4. Release inventory (restock cancelled items)
        release_result, http_status = releaseInventory(order_items)
        if http_status >= 400:
            print(f"Warning: Inventory release failed: {release_result}")
        else:
            print("Successfully released inventory")

        # 5. Refund payment
        if intent_id:
            refund_result, http_status = refundPayment(intent_id)
            if http_status >= 400:
                print(f"Warning: Refund failed: {refund_result}")
            else:
                print("Successfully processed refund")
        else:
            print("Skipping refund — no intent_id available")

        # 6. Cancel delivery
        delivery_result, http_status = cancelDelivery(order_id)
        if http_status >= 400:
            print(f"Warning: Delivery cancellation failed: {delivery_result}")
        else:
            print("Successfully cancelled delivery")

        # 7. Notify buyer via RabbitMQ
        if recipient_email:
            refund_line = (
                "A refund has been initiated and will be reflected within 5-10 business days.\n"
                if intent_id
                else "Please contact support if a refund is required.\n"
            )
            publishNotification(
                recipient_email,
                subject=f"Order Cancelled - #{order_id}",
                body=(
                    f"Hi {customer_name},\n\n"
                    f"Your order #{order_id} has been successfully cancelled.\n\n"
                    f"Order ID     : {order_id}\n"
                    f"Total Amount : ${total_price:.2f}\n\n"
                    f"{refund_line}\n"
                    f"We're sorry to see you go. If you have any questions, "
                    f"please contact our support team."
                ),
            )
            print("Successfully published notification")

        return jsonify({
            "code":     200,
            "message":  "Order cancellation processed successfully",
            "order_id": order_id,
            "order":    order_data,
        }), 200

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname  = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return jsonify({"code": 500, "message": "cancel_order.py internal error", "exception": ex_str}), 500


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def getPaymentByOrder(order_id):
    print("Invoking payment microservice to get intent_id...")
    try:
        import requests as req
        # ✅ Uses env var instead of hardcoded Docker hostname
        response = req.get(PAYMENT_SERVICE_URL + "/payment/order/" + str(order_id), timeout=10)
        if response.status_code >= 400:
            return None, response.status_code
        return response.text.strip(), response.status_code
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname  = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return None, 500


def getBuyer(customer_id):
    print("Invoking buyer microservice...")
    try:
        # ✅ Uses env var
        result, http_status = invoke_http(
            BUYER_SERVICE_URL + "/buyer/" + str(customer_id), method="GET"
        )
        if http_status >= 400:
            return {"code": http_status, "message": "Get buyer failed", "details": result}, http_status
        return result, http_status
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname  = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "getBuyer internal error", "exception": ex_str}, 500


def cancelOrder(order_id):
    print("Invoking order microservice...")
    try:
        # ✅ Uses env var
        result, http_status = invoke_http(
            ORDER_SERVICE_URL + "/orders/" + str(order_id) + "/cancel", method="PUT"
        )
        if http_status >= 400:
            return {"code": http_status, "message": "Cancel order failed", "details": result}, http_status
        return result, http_status
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname  = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "cancelOrder internal error", "exception": ex_str}, 500


def releaseInventory(order_items):
    """Restock inventory for each cancelled order item using /inventory/restock."""
    print("Invoking inventory microservice to release stock...")
    try:
        for item in order_items:
            item_id  = item.get("ItemID")
            quantity = item.get("Quantity")

            # ✅ Uses new /inventory/restock endpoint instead of GET+PUT
            # ✅ Uses env var instead of hardcoded Docker hostname
            result, http_status = invoke_http(
                INVENTORY_SERVICE_URL + "/inventory/restock",
                method="POST",
                json={"item_id": item_id, "quantity": quantity},
            )

            if http_status >= 400:
                return {"code": http_status, "message": f"Failed to restock item {item_id}", "details": result}, http_status

            print(f"Restocked {quantity} units of item {item_id}")

        return {"code": 200, "message": "successfully released inventory"}, 200

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname  = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "releaseInventory internal error", "exception": ex_str}, 500


def refundPayment(intent_id):
    print("Invoking payment microservice for refund...")
    try:
        # ✅ Uses env var
        result, http_status = invoke_http(
            PAYMENT_SERVICE_URL + "/payment/refund",
            method="POST",
            json={"intent_id": intent_id},
        )
        if http_status >= 400:
            return {"code": http_status, "message": "Refund failed", "details": result}, http_status
        return result, http_status
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname  = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "refundPayment internal error", "exception": ex_str}, 500


def cancelDelivery(order_id):
    print("Invoking delivery microservice...")
    try:
        delivery_base = "https://personal-zsuepeep.outsystemscloud.com/IS213_ChillTrace/rest/DeliveryAPI"

        existing, http_status = invoke_http(
            delivery_base + "/delivery/" + str(order_id) + "/", method="GET"
        )
        if http_status >= 400:
            return {"code": http_status, "message": "Get delivery failed", "details": existing}, http_status

        result, http_status = invoke_http(
            delivery_base + "/delivery/" + str(order_id) + "/",
            method="PUT",
            json={
                "address":            existing.get("address", ""),
                "deliveryDate":       existing.get("deliveryDate", "2014-12-31"),
                "deliveryStatus":     "CANCELLED",
                "driver":             existing.get("driver", 0),
                "initialTemperature": existing.get("initialTemperature", 0.1),
                "finalTemperature":   existing.get("finalTemperature", 0.1),
            },
        )
        if http_status >= 400:
            return {"code": http_status, "message": "Cancel delivery failed", "details": result}, http_status
        return result, http_status

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname  = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "cancelDelivery internal error", "exception": ex_str}, 500


def publishNotification(recipient_email, subject, body):
    print("Publishing notification to RabbitMQ...")
    try:
        connection = pika.BlockingConnection(
            pika.ConnectionParameters(
                host=RABBITMQ_HOST,
                port=RABBITMQ_PORT,
                heartbeat=300,
                blocked_connection_timeout=300,
            )
        )
        channel = connection.channel()
        channel.basic_publish(
            exchange="order_topic",
            routing_key="order.error",
            body=json.dumps({
                "recipient_email": recipient_email,
                "subject":         subject,
                "body":            body,
            }),
            properties=pika.BasicProperties(delivery_mode=2),
        )
        connection.close()
        print(f"Notification published for {recipient_email}")
    except Exception as e:
        print(f"Failed to publish notification: {e}")


# ============================================================================
# RUN
# ============================================================================

if __name__ == "__main__":
    print("This is flask " + os.path.basename(__file__) + " for cancelling an order...")
    app.run(host="0.0.0.0", port=5009, debug=True)