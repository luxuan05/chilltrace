import json
import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

from clients.delivery_client import get_delivery, update_delivery
from clients.order_client import get_order, update_order_status
from clients.notification_client import publish_delivery_accepted

load_dotenv()


# ---- Config -----------------------------------------------------------------

DELIVERY_SERVICE_URL = os.getenv("DELIVERY_SERVICE_URL", "http://localhost:5003")
ORDER_SERVICE_URL = os.getenv("ORDER_SERVICE_URL", "http://localhost:5002")
PORT = int(os.getenv("PORT", "5007"))

# Driver acceptance behavior:
# - delivery-service: transition deliveryStatus (default ACCEPTED) and assign `driver`
# - order-service: update OrderStatus (default IN_TRANSIT) to reflect that a driver is taking over
DELIVERY_STATUS_ON_ACCEPT = os.getenv("DELIVERY_STATUS_ON_ACCEPT", "ACCEPTED").upper()
ORDER_STATUS_ON_ACCEPT = os.getenv("ORDER_STATUS_ON_ACCEPT", "IN_TRANSIT").upper()
DELIVERY_ACCEPTABLE_CURRENT_STATUSES = {
    s.strip().upper()
    for s in os.getenv("DELIVERY_ACCEPTABLE_CURRENT_STATUSES", "SCHEDULED").split(",")
    if s.strip()
}


# ---- App --------------------------------------------------------------------

app = Flask(__name__)
CORS(app)


# ---- Routes -----------------------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Accept Delivery service is running"}), 200


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/deliveries/<int:delivery_id>/accept", methods=["PUT"])
def accept_delivery(delivery_id):
    """
    Driver accepts a delivery job.

    Flow:
    Flow should be: SCHEDULED -> ACCEPTED -> IN_TRANSIT -> DELIVERED

    1) Validate delivery exists and is currently SCHEDULED.
    2) Assign driver and set deliveryStatus to DELIVERY_STATUS_ON_ACCEPT (default ACCEPTED).
    3) Update order status to ORDER_STATUS_ON_ACCEPT (default IN_TRANSIT).
    4) Publish acceptance event for notifications/audit.
    """
    data = request.get_json(silent=True) or {}
    # to check/modify
    accepted_by = str(data.get("acceptedBy", "driver")).strip() or "driver"
    note = data.get("note", "")

    driver_id = (
        data.get("driverId")
        or data.get("DriverId")
        or data.get("driver_id")
        or data.get("DriverID")
        or data.get("driver")
        or data.get("Driver")
    )

    if driver_id is None:
        return jsonify({"error": "driverId is required"}), 400

    try:
        driver_id = int(driver_id)
    except (TypeError, ValueError):
        return jsonify({"error": "driverId must be an integer"}), 400

    subject = data.get("subject") or "Delivery accepted by driver"
    body = data.get("body")
    if not body:
        body = (
            f"Your delivery job has been accepted by driver {driver_id}."
            + (f" Note: {note}" if note else "")
        )

    try:
        # IMPORTANT: DeliveryAPI uses deliveryId, not orderId.
        delivery = get_delivery(delivery_id)
        current_delivery_status = str(delivery.get("deliveryStatus", "")).upper()

        if current_delivery_status not in DELIVERY_ACCEPTABLE_CURRENT_STATUSES:
            return jsonify(
                {
                    "error": "Delivery cannot be accepted.",
                    "deliveryId": delivery_id,
                    "current_delivery_status": current_delivery_status or None,
                    "required_statuses": sorted(DELIVERY_ACCEPTABLE_CURRENT_STATUSES),
                }
            ), 409

        # Delivery record contains the orderId used by order-service.
        order_id = delivery.get("orderId")
        if order_id is None:
            return jsonify(
                {
                    "error": "Delivery record missing orderId; cannot accept delivery.",
                    "deliveryId": delivery_id,
                }
            ), 502

        try:
            order_id = int(order_id)
        except (TypeError, ValueError):
            return jsonify(
                {
                    "error": "Delivery record has invalid orderId; cannot accept delivery.",
                    "deliveryId": delivery_id,
                    "orderId": order_id,
                }
            ), 502

        # Read order to verify it exists and to derive CustomerID for notifications.
        order = get_order(order_id)
        customer_id = order.get("CustomerID") or order.get("CustomerId") or order.get("customer_id")

        # Assign driver + advance delivery state in the external DeliveryAPI (deliveryId).
        assign_result = update_delivery(
            delivery_id,
            {
                "address": delivery.get("address", ""),
                "deliveryDate": delivery.get("deliveryDate", ""),
                "deliveryStatus": DELIVERY_STATUS_ON_ACCEPT,
                "driver": driver_id,
                # No default value
                "initialTemperature": delivery.get("initialTemperature"),
                "finalTemperature": delivery.get("finalTemperature"),
            },
        )

        # Update your local order state so other parts of the system know the driver has taken over.
        order_update_result = update_order_status(order_id, ORDER_STATUS_ON_ACCEPT)

        notification_sent = False
        if customer_id is not None:
            publish_delivery_accepted(
                order_id=order_id,
                customer_id=customer_id,
                driver_id=driver_id,
                note=note
            )
            notification_sent = True

        return jsonify(
            {
                "message": "Delivery accepted successfully.",
                "deliveryId": delivery_id,
                "orderId": order_id,
                "delivery_status": current_delivery_status,
                "order_status": ORDER_STATUS_ON_ACCEPT,
                "delivery_assigned_status": DELIVERY_STATUS_ON_ACCEPT,
                "driver_id": driver_id,
                "accepted_by": accepted_by,
                "assign_result": assign_result,
                "order_update_result": order_update_result,
                "notification_sent": notification_sent,
            }
        ), 200

    except ValueError as e:
        return jsonify({"error": str(e)}), 404
    except RuntimeError as e:
        return jsonify({"error": str(e)}), 502
    except Exception as e:
        return jsonify({"error": "Internal server error", "details": str(e)}), 500


if __name__ == "__main__":
    print("This flask is for " + os.path.basename(__file__) + ": accept delivery ...")
    app.run(host="0.0.0.0", port=PORT, debug=True)
