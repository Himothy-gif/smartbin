"""
Seed script: Creates default company and admin user.
Run once after schema is applied.
"""
import uuid
from passlib.context import CryptContext
import pymysql

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
password_hash = pwd.hash("admin123")

conn = pymysql.connect(
    host="localhost", port=3306, user="smartbin",
    password="smartbin123", database="smartbin",
    charset="utf8mb4"
)

company_id = str(uuid.uuid4())
user_id = str(uuid.uuid4())

with conn.cursor() as cur:
    # Insert Smart Bin Ltd company
    cur.execute("""
        INSERT INTO companies (id, name, paybill_number, contact_phone, contact_email, address)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (company_id, "Smart Bin Ltd", "4060083", "0721482110", "info@smartbin.co.ke", "Nairobi, Kenya"))
    
    # Insert admin user (password: admin123)
    cur.execute("""
        INSERT INTO users (id, company_id, full_name, email, password_hash, role)
        VALUES (%s, %s, %s, %s, %s, %s)
    """, (user_id, company_id, "System Administrator", "admin@smartbin.co.ke", password_hash, "super_admin"))
    
    # Insert default bill amount setting
    setting_id = str(uuid.uuid4())
    cur.execute("""
        INSERT INTO settings (id, company_id, setting_key, setting_value, description)
        VALUES (%s, %s, %s, %s, %s)
    """, (setting_id, company_id, "default_bill_amount", "400", "Default monthly garbage collection fee in KES"))
    
    conn.commit()
    print(f"[SEED] Company: {company_id}")
    print(f"[SEED] Admin user: {user_id}")
    print(f"[SEED] Password hash: {password_hash[:30]}...")
    print("[SEED] Done!")

conn.close()
