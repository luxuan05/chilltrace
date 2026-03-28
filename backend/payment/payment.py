from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from invokes import invoke_http
import os
import stripe
import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env", override=True)

class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    PORT = int(os.getenv("PORT", 5002))
    SSL_CA = os.getenv("SSL_CA")

    if not SQLALCHEMY_DATABASE_URI:
        raise ValueError("DATABASE_URL is not set in .env")

    if SSL_CA:
        SQLALCHEMY_ENGINE_OPTIONS = {
            "connect_args": {"ssl": {"ca": SSL_CA}},
            "pool_pre_ping": True
        }
    else:
        SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}


app = Flask(__name__)
app.config.from_object(Config)
CORS(app)

db = SQLAlchemy()
db.init_app(app)

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
CURR = 'SGD'

class Payment(db.Model):
    __tablename__ = "Payment"

    orderID = db.Column(db.Integer, primary_key=True)
    intentID = db.Column(db.String(255), primary_key=True)
    status = db.Column(db.String(50))

    def to_dict(self):
        return {
            "OrderID": self.orderID,
            "IntentID": self.intentID,
            "Status": self.status
        }

with app.app_context():
    db.create_all()

@app.route("/payment/create-intent", methods=['POST'])
def create_intent():
    cid = request.json.get('CustomerID', None)
    oid = request.json.get('OrderID', None)
    # total amount should be in cents
    amt = request.json.get('Amount', None)
    orderItems = request.json.get('OrderItems', None)
    scheduledDate = request.json.get('ScheduledDate', None)
    address = request.json.get('Address', None)

    try:
        
        # create PaymentIntent with amount and currency (default USD)
        intent = stripe.PaymentIntent.create(
            amount=amt,
            currency=CURR,

            metadata={
                "CustomerID": cid,
                "OrderID": oid,
                "OrderItems": json.dumps(orderItems),
                "ScheduledDate": scheduledDate,
                "Address": address
            },

            # allows Stripe to manage payment methods from your dashboard
            automatic_payment_methods= {
                'enabled': True
            }
        )

        new_intentID = Payment(
            intentID=intent.client_secret.split("_secret_")[0],
            orderID=oid,
            status=''
        )

        db.session.add(new_intentID)
        db.session.commit()


        # return client secret to frontend
        return jsonify(
            {
                "code": 201,
                "data": {
                    'CustomerID': cid,
                    'OrderID': oid,
                    'Amount': amt,
                    'client_secret': intent.client_secret.split("_secret_")[0]
                }
            }
        ), 201
    
    except Exception as e:
        return jsonify(
            {
                "code": 500,
                "message": "An error occurred while creating the payment: " + str(e)
            }
        ), 500
    
# receives payment_intent_succeeded event directly from Stripe
@app.route('/payment/webhook', methods =['POST'])
def stripe_webhook():
    payload = request.data
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    event = None

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, endpoint_secret
        )
    
    except ValueError as e:
        return {"Error": 'Invalid payload'}, 400
    
    except stripe.error.SignatureVerificationError as e:
        return {"Error": 'Invalid signature'}, 400
    
    if event['type'] == 'payment_intent.succeeded':

        payment_intent = event['data']['object']

        metadata = payment_intent.get('metadata', {})
        orderID = metadata.get('OrderID')
        customerID = metadata.get('CustomerID')
        scheduledDate = metadata.get('ScheduledDate')
        address = metadata.get('Address')
        orderItems = json.loads(metadata.get('OrderItems'))

        payload = {
            "OrderID": orderID,
            "CustomerID": customerID,
            "Amount": payment_intent['amount'],
            "OrderItems": orderItems,
            "ScheduledDate": scheduledDate,
            "Address": address,
            "Payment Status": "success"
        }

        print(f"Payment for {payment_intent['amount']} succeeded!")
        print(f"Sending orderID and customerID back to place order service...")
        request_data, status = invoke_http('http://localhost:5006/placeorder/receive-payment-status', method='POST', json=payload)
        print(f"{request_data}\nStatus: {status}")

    elif event['type'] == 'payment_intent.payment_failed':
        payment_intent = event['data']['object']
        print(f"Payment failed: {payment_intent['last_payment_error']['message']}")
    
    elif event['type'] == 'charge.refunded':
        charge = event['data']['object']

        refunded_amount = charge['amount_refunded']
        intent_id = charge['payment_intent']
        # charge_id = charge['id']

        print(f"Refund of {refunded_amount} cents processed for Intent: {intent_id}")
    
    else:
        print(f"Unhandled event type {event['type']}")

    return jsonify({'status': 'success'}), 200


# retrieve specific payment transaction
@app.route('/payment/intent/<intent_id>', methods=['GET'])
def get_payment_info(intent_id):
    try: 
        # get complete PaymentIntent object from Stripe
        payment_intent = stripe.PaymentIntent.retrieve(intent_id, expand=['latest_charge'])

        receipt_url = None
        card_last4 = None

        charge = payment_intent.latest_charge
        if charge:
            receipt_url = charge.receipt_url

            if charge.payment_method_details and charge.payment_method_details.type == 'card':
                card_info = charge.payment_method_details.card 
                card_last4 = card_info.last4

        # parse out specific fields to return
        return jsonify({
            'id': payment_intent.id,
            'status': payment_intent.status,
            'amount': payment_intent.amount,
            'amount_received': payment_intent.amount_received,
            'currency': payment_intent.currency,
            'receipt_url': receipt_url,
            'card_ending_with': card_last4,
        }), 200
    
    except stripe.error.StripeError as e:
        return jsonify({'error': str(e)}), 404

# retrieve intentID using orderID
@app.route('/payment/order/<order_id>', methods=['GET'])
def getIntentID(order_id):
    try:
        intent_id = Payment.query.filter_by(orderID=order_id).first()
        if not intent_id:
            return jsonify({"error": "Order ID not found."}), 404
        intent_id = intent_id.to_dict()
        return jsonify({"IntentID": intent_id['IntentID']}), 200
    

    except Exception as e:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
        ex_str = str(e) + " at " + str(exc_type) + ": " + fname + ": line " + str(exc_tb.tb_lineno)
        print("Error: {}".format(ex_str))

        return {
                    "code": 500,
                    "message": "check payment internal error:",
                    "exception": ex_str,
                }, 500

# create refunds
@app.route('/payment/refund', methods=['POST'])
def create_refund():
    try:
        data = request.json
        intent_id = data.get('intent_id')

        if not intent_id:
            return jsonify({'error': 'intent_id is required'}), 400
        
        # set up params for Stripe call
        refund_params = {
            'payment_intent': intent_id
        }

        # execute Stripe call
        refund = stripe.Refund.create(**refund_params)

        return jsonify({
            'message': 'Refund processed successfully',
            'refund_id': refund.id,
            'amount_refunded': refund.amount,
            'status': refund.status,
        }), 201
    
    except stripe.error.StripeError as e:
        return jsonify({'error': str(e.user_message)}), 400
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred.'}), 500
    
# retrieve refunds
@app.route('/payment/refund/<refund_id>', methods=['GET'])
def get_refunds(refund_id):

    try: 
        # get refund object from Stripe
        refund = stripe.Refund.retrieve(refund_id)

        return jsonify({
            'id': refund.id,
            'amount': refund.amount,
            'status': refund.status,
            'payment_intent': refund.payment_intent,
            # 'reason': refund.reason,
            'receipt_number': refund.receipt_number
        }), 200
    
    except stripe.error.StripeError as e:
        return jsonify({'error': str(e.user_message)}), 404
    
    except Exception as e:
        return jsonify({'error': 'An unexpected error occurred.'}), 500

if __name__ == '__main__':
    print("This flask is for " + os.path.basename(__file__) + ": payments ...")
    app.run(host='0.0.0.0', port=5004, debug=True)