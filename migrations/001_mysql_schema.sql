-- SMART BIN LTD - MySQL 8.0 Schema (Fixed Order)

CREATE TABLE IF NOT EXISTS companies (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    name VARCHAR(255) NOT NULL,
    paybill_number VARCHAR(50) NOT NULL,
    contact_phone VARCHAR(20),
    contact_email VARCHAR(255),
    address TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS users (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    company_id CHAR(36) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('super_admin','admin','clerk') DEFAULT 'clerk',
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS estates (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    company_id CHAR(36) NOT NULL,
    name VARCHAR(255) NOT NULL,
    location VARCHAR(500),
    total_phases INT DEFAULT 1,
    total_houses INT DEFAULT 0,
    status ENUM('active','inactive','suspended') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS phases (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    estate_id CHAR(36) NOT NULL,
    phase_number INT NOT NULL,
    phase_name VARCHAR(255),
    total_houses INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (estate_id) REFERENCES estates(id) ON DELETE CASCADE,
    UNIQUE KEY unique_estate_phase (estate_id, phase_number)
);

CREATE TABLE IF NOT EXISTS houses (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    phase_id CHAR(36) NOT NULL,
    house_number VARCHAR(50) NOT NULL,
    account_number VARCHAR(50) NOT NULL,
    gps_coordinates VARCHAR(100),
    bin_count INT DEFAULT 1,
    status ENUM('active','inactive','suspended','vacant') DEFAULT 'active',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (phase_id) REFERENCES phases(id) ON DELETE CASCADE,
    UNIQUE KEY unique_phase_house (phase_id, house_number)
);

CREATE TABLE IF NOT EXISTS residents (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    house_id CHAR(36) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    email VARCHAR(255),
    id_number VARCHAR(50),
    password_hash VARCHAR(255),
    is_primary BOOLEAN DEFAULT TRUE,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (house_id) REFERENCES houses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS bills (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    house_id CHAR(36) NOT NULL,
    bill_period VARCHAR(50) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    amount_paid DECIMAL(10,2) DEFAULT 0.00,
    balance DECIMAL(10,2) NOT NULL,
    due_date DATE NOT NULL,
    status ENUM('pending','paid','overdue','partial','cancelled') DEFAULT 'pending',
    description TEXT,
    created_by CHAR(36),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (house_id) REFERENCES houses(id) ON DELETE CASCADE,
    FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS payments (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    bill_id CHAR(36),
    house_id CHAR(36) NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    mpesa_code VARCHAR(50),
    mpesa_phone VARCHAR(20),
    payment_method ENUM('mpesa','cash','bank_transfer','other') DEFAULT 'mpesa',
    payment_reference VARCHAR(255),
    status ENUM('pending','completed','failed','refunded') DEFAULT 'completed',
    paid_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (bill_id) REFERENCES bills(id) ON DELETE SET NULL,
    FOREIGN KEY (house_id) REFERENCES houses(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS drivers (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    company_id CHAR(36) NOT NULL,
    full_name VARCHAR(255) NOT NULL,
    phone_number VARCHAR(20) NOT NULL,
    license_number VARCHAR(100),
    vehicle_plate VARCHAR(50),
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS collections (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    house_id CHAR(36) NOT NULL,
    driver_id CHAR(36),
    scheduled_date DATE NOT NULL,
    completed_at TIMESTAMP NULL,
    weight_kg DECIMAL(8,2),
    waste_type ENUM('general','recyclable','organic','hazardous') DEFAULT 'general',
    status ENUM('scheduled','completed','missed','cancelled','skipped') DEFAULT 'scheduled',
    photo_url VARCHAR(500),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (house_id) REFERENCES houses(id) ON DELETE CASCADE,
    FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS routes (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    driver_id CHAR(36),
    estate_id CHAR(36) NOT NULL,
    route_date DATE NOT NULL,
    phase_ids JSON,
    total_houses INT DEFAULT 0,
    completed_houses INT DEFAULT 0,
    status ENUM('pending','in_progress','completed','cancelled') DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (driver_id) REFERENCES drivers(id) ON DELETE SET NULL,
    FOREIGN KEY (estate_id) REFERENCES estates(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS sms_logs (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    house_id CHAR(36),
    phone_number VARCHAR(20) NOT NULL,
    message TEXT NOT NULL,
    sms_type ENUM('bill_issue','payment_confirmation','overdue_reminder','service_alert','general') NOT NULL,
    status ENUM('pending','sent','failed','delivered') DEFAULT 'pending',
    provider_response JSON,
    sent_at TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (house_id) REFERENCES houses(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    table_name VARCHAR(100) NOT NULL,
    record_id CHAR(36) NOT NULL,
    action ENUM('create','update','delete') NOT NULL,
    old_data JSON,
    new_data JSON,
    performed_by CHAR(36),
    performed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (performed_by) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS settings (
    id CHAR(36) PRIMARY KEY DEFAULT (UUID()),
    company_id CHAR(36) NOT NULL,
    setting_key VARCHAR(100) NOT NULL,
    setting_value TEXT,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (company_id) REFERENCES companies(id) ON DELETE CASCADE,
    UNIQUE KEY unique_company_setting (company_id, setting_key)
);

CREATE INDEX idx_houses_account ON houses(account_number);
CREATE INDEX idx_houses_phase ON houses(phase_id);
CREATE INDEX idx_bills_house ON bills(house_id);
CREATE INDEX idx_bills_status ON bills(status);
CREATE INDEX idx_bills_due_date ON bills(due_date);
CREATE INDEX idx_payments_house ON payments(house_id);
CREATE INDEX idx_payments_mpesa ON payments(mpesa_code);
CREATE INDEX idx_collections_house ON collections(house_id);
CREATE INDEX idx_collections_date ON collections(scheduled_date);
CREATE INDEX idx_sms_house ON sms_logs(house_id);
CREATE INDEX idx_sms_phone ON sms_logs(phone_number);
CREATE INDEX idx_residents_phone ON residents(phone_number);
CREATE INDEX idx_audit_record ON audit_logs(record_id);

DELIMITER //

CREATE TRIGGER trigger_generate_account_number
BEFORE INSERT ON houses
FOR EACH ROW
BEGIN
    DECLARE v_phase_number INT;
    SET v_phase_number = (SELECT phase_number FROM phases WHERE id = NEW.phase_id);
    SET NEW.account_number = CONCAT(NEW.house_number, '/', v_phase_number);
END//

CREATE TRIGGER trigger_update_bill_balance
AFTER INSERT ON payments
FOR EACH ROW
BEGIN
    UPDATE bills
    SET amount_paid = amount_paid + NEW.amount,
        balance = balance - NEW.amount,
        status = CASE
            WHEN (balance - NEW.amount) <= 0 THEN 'paid'
            WHEN (balance - NEW.amount) < amount THEN 'partial'
            ELSE status
        END,
        updated_at = CURRENT_TIMESTAMP
    WHERE id = NEW.bill_id;
END//

CREATE TRIGGER trigger_update_estate_count_insert
AFTER INSERT ON houses
FOR EACH ROW
BEGIN
    UPDATE estates SET total_houses = total_houses + 1
    WHERE id = (SELECT estate_id FROM phases WHERE id = NEW.phase_id);
    UPDATE phases SET total_houses = total_houses + 1 WHERE id = NEW.phase_id;
END//

CREATE TRIGGER trigger_update_estate_count_delete
AFTER DELETE ON houses
FOR EACH ROW
BEGIN
    UPDATE estates SET total_houses = total_houses - 1
    WHERE id = (SELECT estate_id FROM phases WHERE id = OLD.phase_id);
    UPDATE phases SET total_houses = total_houses - 1 WHERE id = OLD.phase_id;
END//

DELIMITER ;
