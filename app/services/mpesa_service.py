"""
SMART BIN LTD - M-PESA SERVICE (Safaricom Daraja API)
"""
import base64
import json
from datetime import datetime
from typing import Optional
import requests
from app.config import get_settings

settings = get_settings()

class MpesaService:
    def __init__(self):
        self.consumer_key = settings.mpesa_consumer_key
        self.consumer_secret = settings.mpesa_consumer_secret
        self.shortcode = settings.mpesa_shortcode
        self.passkey = settings.mpesa_passkey
        self.environment = settings.mpesa_environment
        self.base_url = (
            "https://sandbox.safaricom.co.ke"
            if self.environment == "sandbox"
            else "https://api.safaricom.co.ke"
        )
        self.mock_mode = not self.consumer_key or self.consumer_key == "your-consumer-key"

        if self.mock_mode:
            print("[M-PESA] MOCK MODE: No credentials. Operations log to console only.")

    def get_access_token(self) -> Optional[str]:
        if self.mock_mode:
            return "mock-token"
        url = f"{self.base_url}/oauth/v1/generate?grant_type=client_credentials"
        try:
            resp = requests.get(url, auth=(self.consumer_key, self.consumer_secret), timeout=10)
            return resp.json().get("access_token")
        except Exception as e:
            print(f"[M-PESA] Token error: {e}")
            return None

    def register_urls(self, validation_url: str, confirmation_url: str) -> dict:
        if self.mock_mode:
            print(f"[M-PESA MOCK] Would register URLs:")
            print(f"  Validation: {validation_url}")
            print(f"  Confirmation: {confirmation_url}")
            return {"status": "mock-registered"}

        token = self.get_access_token()
        if not token:
            return {"error": "Could not get access token"}

        url = f"{self.base_url}/mpesa/c2b/v1/registerurl"
        headers = {"Authorization": f"Bearer {token}"}
        payload = {
            "ShortCode": self.shortcode,
            "ResponseType": "Completed",
            "ConfirmationURL": confirmation_url,
            "ValidationURL": validation_url
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=10)
        return resp.json()

    def validate_payment(self, account_number: str, amount: str, phone: str) -> dict:
        if self.mock_mode:
            print(f"[M-PESA MOCK] Validating: Acc={account_number}, Amount={amount}, Phone={phone}")
        return {"ResultCode": 0, "ResultDesc": "Accepted"}

    def confirm_payment(self, data: dict) -> dict:
        if self.mock_mode:
            print(f"[M-PESA MOCK] Confirmation received:")
            print(json.dumps(data, indent=2))
        return {"ResultCode": 0, "ResultDesc": "Success"}

mpesa_service = MpesaService()
