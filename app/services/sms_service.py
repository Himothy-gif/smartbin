"""
SMART BIN LTD - SMS SERVICE (Africa's Talking)
"""
import uuid
from datetime import datetime
import africastalking
from sqlalchemy.orm import Session
from app.config import get_settings
from app.models import SMSLog

settings = get_settings()

class SMSService:
    def __init__(self):
        self.username = settings.africastalking_username
        self.api_key = settings.africastalking_api_key
        self.sender = settings.africastalking_sender_id
        self.mock_mode = not self.api_key or self.api_key == "your-api-key"

        if not self.mock_mode:
            africastalking.initialize(self.username, self.api_key)
            self.sms = africastalking.SMS
        else:
            self.sms = None
            print("[SMS] MOCK MODE: No API key. SMS log to console only.")

    def send(self, phone: str, message: str, sms_type: str, house_id: str = None, db: Session = None) -> dict:
        log = SMSLog(
            id=str(uuid.uuid4()),
            house_id=house_id,
            phone_number=phone,
            message=message,
            sms_type=sms_type,
            status="pending"
        )
        if db:
            db.add(log)
            db.commit()

        if self.mock_mode:
            print(f"\n[SMS MOCK] To: {phone}")
            print(f"[SMS MOCK] Type: {sms_type}")
            print(f"[SMS MOCK] Message: {message}\n")
            result = {
                "status": "sent",
                "messageId": f"mock-{uuid.uuid4().hex[:8]}",
                "cost": "KES 0.00 (mock)"
            }
        else:
            try:
                response = self.sms.send(message, [phone], self.sender)
                result = {
                    "status": response["SMSMessageData"]["Recipients"][0]["status"],
                    "messageId": response["SMSMessageData"]["Recipients"][0]["messageId"],
                    "cost": response["SMSMessageData"]["Recipients"][0]["cost"]
                }
            except Exception as e:
                result = {"status": "failed", "error": str(e)}

        if db:
            log.status = result["status"] if result["status"] in ("sent", "delivered", "failed") else "sent"
            log.provider_response = result
            log.sent_at = datetime.utcnow()
            db.commit()

        return result

    def send_bill_sms(self, phone: str, name: str, account_number: str,
                      amount: float, period: str, due_date: str,
                      estate_name: str = "", house_id: str = None, db: Session = None):
        from app.config import company_config
        msg = company_config.get_bill_sms(name, account_number, amount, period, due_date, estate_name)
        return self.send(phone, msg, "bill_issue", house_id, db)

    def send_payment_confirmation(self, phone: str, name: str, account_number: str,
                                   amount: float, mpesa_code: str, balance: float,
                                   house_id: str = None, db: Session = None):
        from app.config import company_config
        msg = company_config.get_payment_confirmation_sms(name, account_number, amount, mpesa_code, balance)
        return self.send(phone, msg, "payment_confirmation", house_id, db)

    def send_overdue_reminder(self, phone: str, name: str, account_number: str,
                               amount: float, days_overdue: int,
                               house_id: str = None, db: Session = None):
        from app.config import company_config
        msg = company_config.get_overdue_reminder_sms(name, account_number, amount, days_overdue)
        return self.send(phone, msg, "overdue_reminder", house_id, db)

sms_service = SMSService()
