from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import pika
import sys, os
from os import environ

from invokes import invoke_http

app = Flask(__name__)

CORS(app)


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
            
            customerID = order_result['order']['CustomerID']
            orderID = order_result['order']['ID']
            payment_amount = int(order_result['order']['TotalPrice']*100)
            

            # Update inventory with new quantity for reach order item
            update_result, http_status = updateInventory(order['OrderItems'])
            
            print("Successfully updated inventory")

            # Send payment details to payment microservice
            payment_details = {
                "CustomerID": customerID,
                "OrderID": orderID,
                "Amount": payment_amount
            }
            
            print(f"Code:{200}\nMessage: Make payment\nAmount: {payment_amount}\nOrderID:{orderID}")

            payment_result, http_status = makePayment(payment_details)

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
    try:
        data = request.get_json(silent=True) or {}

        orderID = data.get('OrderID')
        customerID = data.get('CustomerID')
        paymentStatus = data.get('Payment Status')

        if not orderID or paymentStatus != 'success':
            return jsonify({'error': 'Invalid data or payment not successful'}), 400


        print(f"Orchestrator received success message for Order ID: {orderID}")

        update_result, status = invoke_http('http://localhost:5002/orders/' + str(orderID) + "/status", method='PUT', json={'OrderStatus': "PAID"})
        return jsonify(update_result), status
    

    except Exception as e:
        print(f"Error processing payment update: {e}")
        return jsonify({'error': 'Internal server error'}), 500

def checkInventory(items):
    # Send the order info to inventory microservice
    print("Invoking inventory microservice... ")
    check_result = []
    try:
        for item in items:
            item_result, http_status = invoke_http('http://localhost:5001/inventory/check-availability/' + str(item["ItemID"]), method='GET')
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
        order_result, http_status = invoke_http('http://localhost:5002/orders', method='POST', json=orderItems)

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
            update_result, http_status = invoke_http('http://localhost:5001/inventory/items/' + str(item['ItemID']), method='PUT', json=item)

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
        secret, http_status = invoke_http('http://localhost:5004/payment/create-intent', method='POST', json=paymentDetails)

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

# Execute this program if it is run as a main script (not by 'import')
if __name__ == "__main__":
    print("This is flask " + os.path.basename(__file__) + " for placing an order...")
    app.run(host="0.0.0.0", port=5006, debug=True)
