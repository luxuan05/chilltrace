from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
import json
import pika
import sys, os
import amqp_lib
from os import environ
from pathlib import Path
from invokes import invoke_http
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)

CORS(app)

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

# RabbitMQ
rabbit_host = environ.get("RABBITMQ_HOST") or "rabbitmq"
rabbit_port = environ.get("RABBITMQ_PORT") or 5672
exchange_name = environ.get("exchange_name") or "order_topic"
exchange_type = environ.get("exchange_type") or "topic"

# Service endpoints (Docker-friendly defaults, override via .env for local runs)
INVENTORY_SERVICE_URL = environ.get("INVENTORY_SERVICE_URL") or "http://inventory:5001"
ORDER_SERVICE_URL = environ.get("ORDER_SERVICE_URL") or "http://order:5002"
PAYMENT_SERVICE_URL = environ.get("PAYMENT_SERVICE_URL") or "http://payment:5004"
BUYER_SERVICE_URL = environ.get("BUYER_SERVICE_URL") or "http://buyer:5012"

connection = None 
channel = None

def connectAMQP():
    # Use global variables to reduce number of reconnection to RabbitMQ
    # There are better ways but this suffices for our lab
    global connection
    global channel

    print("Connecting to AMQP broker...")
    try:
        connection, channel = amqp_lib.connect(
                hostname=rabbit_host,
                port=rabbit_port,
                exchange_name=exchange_name,
                exchange_type=exchange_type,
        )
    except Exception as exception:
        print(f"Unable to connect to RabbitMQ.\n     {exception=}\n")
        exit(1) # terminate

@app.route("/placeorder", methods=["POST"])
def place_order():
    # check if input format and data of request are JSON
    if request.is_json:
        try: 
            order = request.get_json()
            print("\nReceived an order in JSON: ", order)

            # Send over to inventory microservice
            check_result = []
            check_result, http_status = checkInventory(order["OrderItems"])
            
            # return error
            if http_status >= 400:
                return jsonify(check_result), http_status

            print(f"Successfully checked inventory")
            # check if enough stock
            for item in check_result['data']:
                if not item['enough stock']:
                    return jsonify({
                        "ItemID": item['ItemID'],
                        "Error": "Not enough stock"
                    }), 404
                else:
                    # add UnitPrice and SupplierID to OrderItems
                    for cartItem in order["OrderItems"]:
                        if item['ItemID'] == cartItem['ItemID']:
                            cartItem['UnitPrice'] = item['UnitPrice']
                            # cartItem['SupplierID'] = item['SupplierID']

            # Send request to order microservice
            order_result, http_status = createOrder(order)

            # return error
            if http_status >= 400:
                return jsonify(order_result), http_status
            
            print(f"Successfully created order")
            print(order_result)
            customerID = order_result['order']['CustomerID']
            orderID = order_result['order']['ID']
            payment_amount = int(order_result['order']['TotalPrice']*100)
            scheduledDate = order_result['order']['ScheduledDate']
            address = order['Address']

            # Update inventory with new quantity for reach order item
            update_result, http_status = updateInventory(order['OrderItems'])
            
            print("Successfully updated inventory")

            # Send payment details to payment microservice
            payment_details = {
                "CustomerID": customerID,
                "OrderID": orderID,
                "Amount": payment_amount,
                "OrderItems": order_result['order']['OrderItems'],
                "ScheduledDate": scheduledDate,
                "Address": address
            }
            
            print(f"Code:{200}\nMessage: Make payment\nAmount: {payment_amount}\nOrderID:{orderID}")

            payment_result, http_status = makePayment(payment_details)

            # Ensure frontend can reliably read result.data.OrderID.
            if isinstance(payment_result, dict):
                if not isinstance(payment_result.get("data"), dict):
                    payment_result["data"] = {}
                payment_result["data"]["OrderID"] = orderID

            return jsonify({
                "code": 201,
                "result": payment_result
            }), 201
        

        except Exception as e:
            # Unexpected error in code
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
            print("Error: {}".format(ex_str))

            return jsonify(
                    {
                        "code": 500,
                        "message": "place_order.py internal error:",
                        "exception": ex_str,
                    }
            ), 500
        
    # if reach here, not a JSON request
    return jsonify(
        {
            "code": 400,
            "message": "Invalid JSON input: " + str(request.get_data())
        }
    ), 400

@app.route('/placeorder/receive-payment-status', methods=['POST'])
def receivePayment():
    global connection, channel
    try:
        data = request.get_json(silent=True) or {}

        orderID = data.get('OrderID')
        customerID = data.get('CustomerID')
        paymentStatus = data.get('Payment Status')
        orderItems = data.get('OrderItems')
        amount = int(data.get('Amount'))/100
        scheduledDate = data.get('ScheduledDate')
        address = data.get('Address')

        if not orderID or paymentStatus != 'success':
            return jsonify({'Error': 'Invalid data or payment not successful'}), 400

        print(f"Orchestrator received success message for Order ID: {orderID}")

        # update order status to PAID
        update_result, status = invoke_http(ORDER_SERVICE_URL + '/orders/' + str(orderID) + "/status", method='PUT', json={'OrderStatus': "PAID"})
        print(f"result: {update_result}\nStatus: {status}")

        # get datils for each item from inventory

        receipt = "Your order has been received and payment was successful.\nOrder Items:\n" 
        for item in orderItems:
            itemID = item['ItemID']
            details = getItem(itemID)
            receipt+= f"\t{details['name']}\t${details['price']:.2f}\n"

        receipt+= f"Total:\t${amount:.2f}\nScheduled delivery date: {scheduledDate}\nDelivery Address: {address}\nThank you!"
        
        # Fetch buyer email and ChatID for notification
        buyer_result, buyer_status = invoke_http(
            BUYER_SERVICE_URL + '/buyer/' + str(customerID), method='GET'
        )
        recipient_email = buyer_result.get("Email", "") if buyer_status == 200 else ""
        chat_id         = buyer_result.get("ChatID", "") if buyer_status == 200 else ""

        print("Publish message to AMQP Exchange for Notification")
        message = {
            "recipient_email": recipient_email,
            "chat_id":         chat_id,
            "subject":         "Order " + str(orderID),
            "body":            receipt
        }

        message_body = json.dumps(message)

        # Reconnect if channel/connection is closed
        if not connection or connection.is_closed or channel.is_closed:
            connection, channel = amqp_lib.connect(
                hostname=rabbit_host,
                port=rabbit_port,
                exchange_name=exchange_name,
                exchange_type=exchange_type,
            )

        channel.basic_publish(
            exchange=exchange_name, routing_key='order.paid', body=message_body,
            properties=pika.BasicProperties(delivery_mode=2)
        )

        delivery_json = {
            "orderId": orderID,
            "customerId": customerID,
            "address": address,
            "deliveryDate": scheduledDate
        }

        print("Invoking delivery service to create delivery job")

        delivery_result, http_status = invoke_http('https://personal-zsuepeep.outsystemscloud.com/IS213_ChillTrace/rest/DeliveryAPI/delivery', method='POST', json=delivery_json)
        
        if http_status != 201:
            return jsonify({
                "Error": "Failed to create delivery job"
            }), 500
    
        return jsonify({"code": 200, "Message": "Successfully placed order!"}), 200
    

    except Exception as e:
        # Unexpected error in code
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))

        return jsonify(
                {
                    "code": 500,
                    "message": "place_order.py internal error:",
                    "exception": ex_str,
                }
        ), 500

def checkInventory(items):
    # Send the order info to inventory microservice
    print("Invoking inventory microservice... ")
    check_result = []
    try:
        for item in items:
            item_result, http_status = invoke_http(INVENTORY_SERVICE_URL + '/inventory/check-availability/' + str(item["ItemID"]), method='GET')
            # print(f"http status: {http_status}\ncheck result: {item_result}\n")

            if http_status != 200 or "stock available" not in item_result:
                return {"code": http_status, "message": "Inventory check failed", "details": item_result}, http_status

            if item['Quantity'] <= item_result['stock available']:
                check_result.append({'ItemID': item['ItemID'], 'enough stock': True, "UnitPrice": item_result['UnitPrice'], "SupplierID": item_result['SupplierID']})
            else:
                check_result.append({'ItemID': item['ItemID'], 'enough stock': False, "UnitPrice": item_result['UnitPrice'], "SupplierID": item_result['SupplierID']})

        return {
            "code": 200,
            "data": check_result,
        }, 200
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))

        return {
                    "code": 500,
                    "message": "check inventory internal error:",
                    "exception": ex_str,
                }, 500

def createOrder(orderItems):
    print("Invoking the order microservice...")

    try:
        order_result, http_status = invoke_http(ORDER_SERVICE_URL + '/orders', method='POST', json=orderItems)

        # print(f"Status: {http_status}\nOrder Result: {order_result}")
        
        if http_status != 201:
            return {"code": http_status, "message": "Create Order failed", "details": order_result}, http_status

        return order_result, http_status
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))

        return {
                    "code": 500,
                    "message": "check order internal error",
                    "exception": ex_str,
            }, 500
    

def updateInventory(orderItems):
    print("Invoking the inventory microservice...")
    
    try:
        for item in orderItems:
            item['Operation'] = "minus"
            update_result, http_status = invoke_http(INVENTORY_SERVICE_URL + '/inventory/items/' + str(item['ItemID']), method='PUT', json=item)

        return jsonify({"code": 200, "message": "successfully updated inventory"}), 200

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))

        return jsonify({
                    "code": 500,
                    "message": "check Inventory internal error",
                    "exception": ex_str,
                }), 500
    
def makePayment(paymentDetails):
    print("Invoking payment microservice...")
    
    try:
        secret, http_status = invoke_http(PAYMENT_SERVICE_URL + '/payment/create-intent', method='POST', json=paymentDetails)

        return secret, http_status

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))

        return {
                    "code": 500,
                    "message": "check Payment internal error",
                    "exception": ex_str,
            }, 500
    

def getItem(itemID):
    print(f"Fetching info from Inventory for itemID: {itemID}")

    try:

        item, status = invoke_http(INVENTORY_SERVICE_URL + '/inventory/items/' + str(itemID), method='GET')

        if status != 200:
            return {
                "Message": "failed to retrieve item. Check if item exists"
            }, status

        return item
        
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))

        return {
                    "code": 500,
                    "message": "check Inventory internal error",
                    "exception": ex_str,
            }, 500

# Execute this program if it is run as a main script (not by 'import')
if __name__ == "__main__":
    print("This is flask " + os.path.basename(__file__) + " for placing an order...")
    connectAMQP()
    app.run(host="0.0.0.0", port=5006, debug=True)
