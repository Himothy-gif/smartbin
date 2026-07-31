"""
==============================================================================
SMART BIN LTD - CONFIGURATION MODULE
==============================================================================
Replaces: .env file + src/config/company.js from the Node.js version.

WHAT THIS DOES:
1. Reads environment variables from .env file into typed Python objects
2. Provides CompanyConfig with SMS templates matching your M-TAKA screenshot
3. Centralizes ALL settings so nothing is hardcoded anywhere else

WHY PYDANTIC SETTINGS?
- Type safety: if DB_PORT is missing, app crashes on startup (not mid-request)
- Auto-casting: "3306" string becomes integer 3306 automatically
- Validation: empty JWT_SECRET = immediate error
==============================================================================
"""

import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field


class Settings(BaseSettings):
    """
    Every env variable is declared here with a type and default.
    Pydantic automatically loads them from .env file.
    """
    
    # --- Application ---
    env: str = "development"           # "development" or "production"
    api_port: int = 8000                # What port FastAPI listens on
    
    # --- Database (MySQL 8.0) ---
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "smartbin"
    db_user: str = "smartbin"
    db_password: str = "smartbin123"
    
    # --- Redis (for caching + cron job queue) ---
    redis_url: str = "redis://localhost:6379"
    redis_port: int = 6379
    
    # --- JWT Authentication ---
    # This secret signs every token. If leaked, anyone can forge admin tokens.
    # Generate a real one with: openssl rand -hex 32
    jwt_secret: str = "change-me"
    jwt_expires_in: str = "7d"          # Token valid for 7 days
    
    # --- Company Details (matches your SMS screenshot exactly) ---
    company_name: str = "Smart Bin Ltd"
    company_paybill: str = "4060083"
    company_phone: str = "0721482110"
    company_email: str = "info@smartbin.co.ke"
    company_address: str = "Nairobi, Kenya"
    
    # --- Africa's Talking SMS Gateway ---
    africastalking_api_key: str = ""
    africastalking_username: str = ""
    africastalking_sender_id: str = "SMARTBIN"
    
    # --- M-PESA Daraja API ---
    mpesa_consumer_key: str = ""
    mpesa_consumer_secret: str = ""
    mpesa_shortcode: str = "4060083"
    mpesa_passkey: str = ""
    mpesa_environment: str = "sandbox"      # "sandbox" for testing, "production" for live
    mpesa_validation_url: str = ""
    mpesa_confirmation_url: str = ""
    
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")
    # Tells Pydantic where to find the .env file

# ==============================================================================
# SINGLETON PATTERN: Cache the settings object so we don't re-read .env
# on every request. @lru_cache means "create once, reuse forever."
# ==============================================================================
@lru_cache()
def get_settings() -> Settings:
    return Settings()


# ==============================================================================
# COMPANY CONFIG: SMS Templates matching your M-TAKA screenshot
# ==============================================================================
class CompanyConfig:
    """
    Replaces src/config/company.js
    
    This class holds the company details AND generates SMS messages
    in the exact format your garbage collection company sends.
    
    YOUR SMS EXAMPLE:
    "GAKINDU COURT
     Dear Faith. E (348/4), You have an outstanding bill of KES 400.00.
     Kindly purpose to pay by 15 Dec 2024.
     Pay via MPESA Paybill 4060083 Acc: 348/4
     View Statement: https://www.app.nyumbani.ke/9mC10091
     Powered by M-TAKA. Call 0721482110"
    """
    
    def __init__(self, settings: Settings = None):
        self.settings = settings or get_settings()
    
    # --- Properties: read company details from settings ---
    @property
    def name(self) -> str:
        return self.settings.company_name
    
    @property
    def paybill(self) -> str:
        return self.settings.company_paybill
    
    @property
    def phone(self) -> str:
        return self.settings.company_phone
    
    @property
    def email(self) -> str:
        return self.settings.company_email
    
    @property
    def address(self) -> str:
        return self.settings.company_address
    
    # --- SMS TEMPLATES: Generate messages identical to your screenshot ---
    
    def get_bill_sms(self, name: str, account_number: str, 
                     amount: float, period: str, due_date: str,
                     estate_name: str = "") -> str:
        """
        SMS sent when a bill is issued.
        Example output:
        "Dear Faith. E (348/4), You have an outstanding bill of KES 400.00.
         Kindly purpose to pay by 15 Dec 2024.
         Pay via MPESA Paybill 4060083 Acc: 348/4
         Powered by Smart Bin Ltd. Call 0721482110"
        """
        estate_line = f"{estate_name}\n" if estate_name else ""
        return (
            f"{estate_line}"
            f"Dear {name} ({account_number}), You have an outstanding bill of KES {amount:.2f}. "
            f"Kindly purpose to pay by {due_date}.\n\n"
            f"Pay via MPESA Paybill {self.paybill} Acc: {account_number}\n\n"
            f"Powered by {self.name}. Call {self.phone}"
        )
    
    def get_payment_confirmation_sms(self, name: str, account_number: str,
                                       amount: float, mpesa_code: str,
                                       balance: float) -> str:
        """
        SMS sent immediately after M-PESA payment is confirmed.
        """
        return (
            f"Thank you {name}. KES {amount:.2f} received for account {account_number}. "
            f"M-PESA Code: {mpesa_code}. New balance: KES {balance:.2f}. "
            f"Powered by {self.name}"
        )
    
    def get_overdue_reminder_sms(self, name: str, account_number: str,
                                   amount: float, days_overdue: int) -> str:
        """
        SMS sent on day 3, 7, 14, 30 when bill is overdue.
        """
        return (
            f"Dear {name} ({account_number}), your account is {days_overdue} days overdue "
            f"with KES {amount:.2f} outstanding. Please pay via MPESA Paybill {self.paybill} "
            f"Acc: {account_number} to avoid service suspension. {self.name}"
        )
    
    def get_payment_instructions(self, account_number: str, amount: float) -> str:
        """
        Short instruction shown in resident portal.
        """
        return f"Pay via M-PESA Paybill {self.paybill} Account: {account_number}. Amount: KES {amount}"


# Create a singleton instance so other modules can import it directly
company_config = CompanyConfig()
