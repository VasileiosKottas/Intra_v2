"""
JotForm Webhook Controller
"""

from flask import request, jsonify
from app.controllers.base import BaseController
from app.services.webhook_service import WebhookService
import hmac
import hashlib
import json
from datetime import datetime

class WebhookController(BaseController):
    """Handles JotForm webhook endpoints"""
    
    def register_routes(self):
        """Register webhook routes"""
        # JotForm webhooks - no authentication required for webhooks
        self.app.add_url_rule('/webhooks/jotform/submissions', 'webhook.submissions', 
                             self.handle_submission_webhook, methods=['POST'])
        self.app.add_url_rule('/webhooks/jotform/paid-cases', 'webhook.paid_cases',
                             self.handle_paid_case_webhook, methods=['POST'])
        
        # Test endpoint to verify webhooks are working
        self.app.add_url_rule('/webhooks/test', 'webhook.test',
                             self.test_webhook, methods=['GET', 'POST'])
    
    def handle_submission_webhook(self):
        """Handle incoming submission webhooks from JotForm"""
        try:
            # Get raw data
            raw_data = request.get_data(as_text=True)
            
            # JotForm sends data as form-encoded, but sometimes as JSON
            if request.content_type and 'application/json' in request.content_type:
                submission_data = request.get_json()
            else:
                # JotForm typically sends as rawRequest parameter
                submission_data = json.loads(request.form.get('rawRequest', '{}'))
            
            print(f"Received submission webhook: {submission_data.get('submissionID', 'unknown')}")
            
            # Process the webhook
            webhook_service = WebhookService()
            success, message = webhook_service.process_submission_webhook(submission_data)
            
            if success:
                return jsonify({'status': 'success', 'message': message}), 200
            else:
                return jsonify({'status': 'error', 'message': message}), 400
                
        except Exception as e:
            print(f"Error processing submission webhook: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def handle_paid_case_webhook(self):
        """Handle incoming paid case webhooks from JotForm"""
        try:
            # Get raw data
            raw_data = request.get_data(as_text=True)
            
            if request.content_type and 'application/json' in request.content_type:
                paid_case_data = request.get_json()
            else:
                paid_case_data = json.loads(request.form.get('rawRequest', '{}'))
            
            print(f"Received paid case webhook: {paid_case_data.get('submissionID', 'unknown')}")
            
            # Process the webhook
            webhook_service = WebhookService()
            success, message = webhook_service.process_paid_case_webhook(paid_case_data)
            
            if success:
                return jsonify({'status': 'success', 'message': message}), 200
            else:
                return jsonify({'status': 'error', 'message': message}), 400
                
        except Exception as e:
            print(f"Error processing paid case webhook: {str(e)}")
            return jsonify({'status': 'error', 'message': str(e)}), 500
    
    def test_webhook(self):
        """Test endpoint to verify webhooks are working"""
        if request.method == 'GET':
            return jsonify({
                'status': 'webhook_endpoint_active',
                'timestamp': str(datetime.now()),
                'message': 'Webhook endpoints are ready to receive JotForm data'
            })
        else:
            # POST test
            data = request.get_json() or request.form.to_dict()
            print(f"Test webhook received: {data}")
            return jsonify({'status': 'test_successful', 'received_data': data})