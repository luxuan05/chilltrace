from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import pika
import sys, os
from dotenv import load_dotenv
from pathlib import Path

from invokes import invoke_http

# Load environment
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

# RabbitMQ config
RABBITMQ_HOST = os.environ.get("RABBITMQ_HOST") or os.environ.get("rabbit_host") or "rabbitmq"
RABBITMQ_PORT = int(os.environ.get("RABBITMQ_PORT") or os.environ.get("rabbit_port") or 5672)

app = Flask(__name__)
CORS(app)

@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "service": "cancel_order"}), 200


@app.route("/cancelorder/<int:order_id>", methods=["PUT"])
def cancel_order(order_id):
    if request.is_json:
        try:
            data = request.get_json()
            print("\nReceived cancel request for order:", order_id, data)

            # Fetch intent_id from Payment table via payment service
            # payment service returns plain string (not JSON)
            payment_result, payment_status = getPaymentByOrder(order_id)
            if payment_status >= 400 or not payment_result:
                print(f"Warning: Could not fetch intent_id for order {order_id}")
                intent_id = ""
            else:
                intent_id = payment_result
            #Cancel order
            cancel_result, http_status = cancelOrder(order_id)

            if http_status >= 400:
                return jsonify(cancel_result), http_status

            print("Successfully cancelled order")

            order_data   = cancel_result.get("order", {})
            order_items  = order_data.get("OrderItems", [])
            total_price  = order_data.get("TotalPrice", 0)
            customer_id  = order_data.get("CustomerID")

            # Fetch buyer email and name from Buyer service
            buyer_result, buyer_status = getBuyer(customer_id)
            if buyer_status >= 400:
                print(f"Warning: Could not fetch buyer for CustomerID {customer_id}: {buyer_result}")
                recipient_email = ""
                customer_name   = "Customer"
            else:
                recipient_email = buyer_result.get("Email", "")
                customer_name   = buyer_result.get("CompanyName", "Customer")

            #Release inventory
            release_result, http_status = releaseInventory(order_items)

            if http_status >= 400:
                print(f"Warning: Inventory release failed: {release_result}")

            print("Successfully released inventory")

            #Refund payment
            if intent_id:
                refund_result, http_status = refundPayment(intent_id)

                if http_status >= 400:
                    print(f"Warning: Refund failed: {refund_result}")
                else:
                    print("Successfully processed refund")
            else:
                print("Skipping refund — no intent_id provided")

            #Cancel delivery
            delivery_result, http_status = cancelDelivery(order_id)

            if http_status >= 400:
                print(f"Warning: Delivery cancellation failed: {delivery_result}")
            else:
                print("Successfully cancelled delivery")

            #Notify buyer via RabbitMQ
            if recipient_email:
                refund_line = (
                    "A refund has been initiated and will be reflected within 5-10 business days.\n"
                    if intent_id
                    else "Please contact support if a refund is required.\n"
                )
                subject = f"Order Cancelled - #{order_id}"
                body = (
                    f"Hi {customer_name},\n\n"
                    f"Your order #{order_id} has been successfully cancelled.\n\n"
                    f"Order ID     : {order_id}\n"
                    f"Total Amount : ${total_price:.2f}\n\n"
                    f"{refund_line}\n"
                    f"We're sorry to see you go. If you have any questions, "
                    f"please contact our support team."
                )
                publishNotification(recipient_email, subject, body)
                print("Successfully published notification")

            return jsonify({
                "code":     200,
                "message":  "Order cancellation processed successfully",
                "order_id": order_id,
                "order":    order_data,
            }), 200

        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
            print("Error: {}".format(ex_str))

            return jsonify({
                "code":      500,
                "message":   "cancel_order.py internal error:",
                "exception": ex_str,
            }), 500

    return jsonify({
        "code":    400,
        "message": "Invalid JSON input: " + str(request.get_data())
    }), 400

def getPaymentByOrder(order_id):
    print("Invoking payment microservice to get intent_id...")
    try:
        import requests as req
        response = req.get('http://payment:5004/payment/order/' + str(order_id), timeout=10)
        if response.status_code >= 400:
            return None, response.status_code
        # payment service returns plain string (not JSON)
        return response.text.strip(), response.status_code
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return None, 500


def getBuyer(customer_id):
    print("Invoking buyer microservice...")
    try:
        result, http_status = invoke_http(
            'http://buyer:5012/buyer/' + str(customer_id),
            method='GET',
        )
        if http_status >= 400:
            return {"code": http_status, "message": "Get buyer failed", "details": result}, http_status
        return result, http_status
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "getBuyer internal error", "exception": ex_str}, 500


def cancelOrder(order_id):
    print("Invoking order microservice...")
    try:
        result, http_status = invoke_http(
            'http://order:5002/orders/' + str(order_id) + '/cancel',
            method='PUT',
        )
        if http_status >= 400:
            return {"code": http_status, "message": "Cancel order failed", "details": result}, http_status
        return result, http_status

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "cancelOrder internal error", "exception": ex_str}, 500


def releaseInventory(order_items):
    """
    Add back stock for each cancelled order item.
    Fetches current qty first then sets new qty = current + cancelled quantity.
    """
    print("Invoking inventory microservice to release stock...")
    try:
        for item in order_items:
            item_id  = item.get("ItemID")
            quantity = item.get("Quantity")

            # GET current stock
            current, http_status = invoke_http(
                'http://inventory:5001/inventory/check-availability/' + str(item_id),
                method='GET',
            )
            if http_status != 200:
                return {"code": http_status, "message": "Failed to get item " + str(item_id), "details": current}, http_status

            new_qty = current.get("stock available", 0) + quantity

            # PUT new absolute qty back
            update_result, http_status = invoke_http(
                'http://inventory:5001/api/inventory/items/' + str(item_id),
                method='PUT',
                json={"quantity": new_qty},
            )
            if http_status >= 400:
                return {"code": http_status, "message": "Failed to release item " + str(item_id), "details": update_result}, http_status

            print(f"Released {quantity} units of item {item_id} (new qty: {new_qty})")

        return {"code": 200, "message": "successfully released inventory"}, 200

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "releaseInventory internal error", "exception": ex_str}, 500


def refundPayment(intent_id):
    print("Invoking payment microservice...")
    try:
        result, http_status = invoke_http(
            'http://payment:5004/payment/refund',
            method='POST',
            json={"intent_id": intent_id},
        )
        if http_status >= 400:
            return {"code": http_status, "message": "Refund failed", "details": result}, http_status
        return result, http_status

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))
        return {"code": 500, "message": "refundPayment internal error", "exception": ex_str}, 500


def cancelDelivery(order_id):
    print("Invoking delivery microservice...")
    try:
        delivery_base = 'https://personal-zsuepeep.outsystemscloud.com/IS213_ChillTrace/rest/DeliveryAPI'

        # GET existing delivery details to preserve driver and other fields
        existing, http_status = invoke_http(
            delivery_base + '/delivery/' + str(order_id) + '/',
            method='GET',
        )
        if http_status >= 400:
            return {"code": http_status, "message": "Get delivery failed", "details": existing}, http_status

        # Use actual driver and fields from existing delivery record
        result, http_status = invoke_http(
            delivery_base + '/delivery/' + str(order_id) + '/',
            method='PUT',
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
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
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
        print(f"Failed to publish notification: {e=}")

if __name__ == "__main__":
    print("This is flask " + os.path.basename(__file__) + " for cancelling an order...")
    app.run(host="0.0.0.0", port=5009, debug=True)