from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from os import environ
from dotenv import load_dotenv
import os
import stripe

load_dotenv()
app = Flask(__name__)

CORS(app)

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')
CURR = 'SGD'

@app.route("/payment/create-intent", methods=['POST'])
def create_intent():
    cid = request.json.get('customer_id', None)

    # total amount should be in cents
    amt = request.json.get('amount', None)

    try:
        
        # create PaymentIntent with amount and currency (default USD)
        intent = stripe.PaymentIntent.create(
            amount=amt,
            currency=CURR,

            # allows Stripe to manage payment methods from your dashboard
            automatic_payment_methods= {
                'enabled': True
            }
        )

        # return client secret to frontend
        return jsonify(
            {
                "code": 201,
                "data": {
                    'customer_id': cid,
                    'amount': amt,
                    'client_secret': intent.client_secret
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
        return 'Invalid payload', 400
    
    except stripe.error.SignatureVerificationError as e:
        return 'Invalid signature', 400
    
    if event['type'] == 'payment_intent.succeeded':
        payment_intent = event['data']['object']
        print(f"Payment for {payment_intent['amount']} succeeded!")
    
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
@app.route('/payment/<intent_id>', methods=['GET'])
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