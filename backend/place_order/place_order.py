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
            check_result, http_status = checkInventory(order["OrderItems"])
            
            for item in check_result['data']:
                if not item['enough stock']:
                    return jsonify({
                        "ItemID": item['ItemID'],
                        "Error": "Not enough stock"
                    }), 404
                
            order_result, http_status = createOrder(order)
            
            return jsonify({
                "Message": "Proceed to make order"
            }), 200

        

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


def checkInventory(items):
    # Send the order info to inventory microservice
    print("Invoking inventory microservice... ")
    check_result = []
    try:
        for item in items:
            item_result, http_status = invoke_http('http://localhost:5000/inventory/check-availability/' + str(item["ItemID"]), method='GET')
            # print(f"http status: {http_status}\ncheck result: {item_result}\n")

            if item['Quantity'] <= item_result['stock available']:
                check_result.append({'ItemID': item['ItemID'], 'enough stock': True})
            else:
                check_result.append({'ItemID': item['ItemID'], 'enough stock': False})

        return {
            "code": http_status,
            "data": check_result,
        }, http_status
    
    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))

        return jsonify(
                {
                    "code": 500,
                    "message": "check inventory internal error:",
                    "exception": ex_str,
                }
        ), 500

def createOrder(orderItems):
    print("Invoking the order microservice...")

    try:
        order_result, http_status = invoke_http('/orders', method='POST', json=orderItems)

        print(f"Status: {http_status}\nOrder Result: {order_result}")

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))

        return jsonify(
                {
                    "code": 500,
                    "message": "check order internal error:",
                    "exception": ex_str,
                }
        ), 500

# Execute this program if it is run as a main script (not by 'import')
if __name__ == "__main__":
    print("This is flask " + os.path.basename(__file__) + " for placing an order...")
    app.run(host="0.0.0.0", port=5001, debug=True)
