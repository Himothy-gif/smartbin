# Fedora Setup Guide — Smart Bin Backend
# Run these commands ONE AT A TIME. Read the output before proceeding.

# ==========================================
# STEP 0: SYSTEM PREP
# ==========================================

# Update your system first
sudo dnf update -y

# Install essential tools
sudo dnf install -y git curl wget vim htop

# ==========================================
# STEP 1: INSTALL NODE.JS 18 (LTS)
# ==========================================

# Option A: Via NodeSource (Recommended)
curl -fsSL https://rpm.nodesource.com/setup_18.x | sudo bash -
sudo dnf install -y nodejs

# Verify installation
node --version   # Should show v18.x.x
npm --version    # Should show 9.x.x or 10.x.x

# ==========================================
# STEP 2: INSTALL DOCKER & DOCKER COMPOSE
# ==========================================

# Fedora uses Podman by default, but Docker is more standard for portfolios
# Install Docker CE
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/fedora/docker-ce.repo
sudo dnf install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# Start and enable Docker
sudo systemctl start docker
sudo systemctl enable docker

# Add your user to docker group (so you don't need sudo every time)
sudo usermod -aG docker $USER

# IMPORTANT: Log out and log back in for group changes to take effect
# Or run: newgrp docker

# Verify Docker
docker --version
docker compose version

# Test Docker
docker run hello-world

# ==========================================
# STEP 3: INSTALL POSTGRESQL CLIENT (optional but useful)
# ==========================================

sudo dnf install -y postgresql15

# Verify
psql --version

# ==========================================
# STEP 4: CLONE / SETUP THE PROJECT
# ==========================================

# If you cloned from GitHub:
# git clone https://github.com/YOUR_USERNAME/smart-bin-backend.git
# cd smart-bin-backend

# If you're setting up from the files we built:
cd ~/smart-bin-backend   # or wherever you extracted the files

# Install Node dependencies
npm install

# ==========================================
# STEP 5: START THE INFRASTRUCTURE
# ==========================================

# Start PostgreSQL and Redis in Docker
docker compose up -d postgres redis

# Check if containers are running
docker ps

# You should see:
# - smartbin-db (postgres:15-alpine)
# - smartbin-redis (redis:7-alpine)

# ==========================================
# STEP 6: RUN DATABASE MIGRATIONS
# ==========================================

# This creates all 14 tables, indexes, and triggers
npm run db:migrate

# Expected output:
# Running database migrations...
#   → 001_initial_schema.sql
# ✅ All migrations completed successfully

# ==========================================
# STEP 7: SEED DEMO DATA
# ==========================================

# This creates Gakindu Court, Faith E., sample bills, etc.
npm run db:seed

# Expected output:
# ✅ Company created: Smart Bin Ltd
# ✅ Admin user created: admin@smartbin.co.ke / admin123
# ✅ Estate created: GAKINDU COURT
# ✅ 4 phases created
# ✅ 84 houses created
# ✅ 5 residents created
# ✅ Sample bill created for Faith E. (348/4) - KES 400
# ✅ Sample payment created for Faith E. - KES 400
# ✅ Sample driver created: James Mwangi
# ✅ Default settings created
# 🎉 Database seeded successfully!

# ==========================================
# STEP 8: START THE API SERVER
# ==========================================

npm run dev

# Expected output:
# ============================================
#   SMART BIN LTD API SERVER
#   Port: 3000
#   Environment: development
#   Company: Smart Bin Ltd
# ============================================

# The server is now running on http://localhost:3000

# ==========================================
# STEP 9: TEST THE API (Open a NEW terminal)
# ==========================================

# Test 1: Health Check
curl http://localhost:3000/health

# Expected: {"status":"healthy","database":"connected","redis":"connected",...}

# Test 2: Login
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@smartbin.co.ke","password":"admin123"}'

# Expected: {"token":"eyJ...","user":{"id":"...","email":"admin@smartbin.co.ke",...}}

# Test 3: Dashboard Stats (replace TOKEN with the one from login)
export TOKEN="eyJ..."
curl http://localhost:3000/api/dashboard/stats \
  -H "Authorization: Bearer $TOKEN"

# Test 4: List Estates
curl http://localhost:3000/api/estates \
  -H "Authorization: Bearer $TOKEN"

# Test 5: Public Portal — Resident Statement (NO AUTH NEEDED)
curl http://localhost:3000/api/portal/statement/348/4

# Expected: Full statement for Faith E. with bills, payments, balance

# Test 6: M-PESA Validation (simulated)
curl -X POST http://localhost:3000/api/payments/validate \
  -H "Content-Type: application/json" \
  -d '{
    "TransactionType":"Pay Bill",
    "TransID":"ABC123XYZ",
    "TransTime":"20240101120000",
    "TransAmount":"400",
    "BusinessShortCode":"4060083",
    "BillRefNumber":"348/4",
    "MSISDN":"254712345678",
    "FirstName":"Faith"
  }'

# Expected: {"ResultCode":0,"ResultDesc":"Accepted",...}

# Test 7: M-PESA Confirmation (simulated)
curl -X POST http://localhost:3000/api/payments/confirm \
  -H "Content-Type: application/json" \
  -d '{
    "TransactionType":"Pay Bill",
    "TransID":"ABC123XYZ",
    "TransTime":"20240101120000",
    "TransAmount":"400",
    "BusinessShortCode":"4060083",
    "BillRefNumber":"348/4",
    "MSISDN":"254712345678",
    "FirstName":"Faith"
  }'

# Expected: {"ResultCode":0,"ResultDesc":"Received"}

# ==========================================
# STEP 10: VERIFY DATABASE
# ==========================================

# Connect to PostgreSQL inside the Docker container
docker exec -it smartbin-db psql -U smartbin -d smartbin

# Run some queries:
\dt                    # List all tables
SELECT * FROM companies;           # Should show Smart Bin Ltd
SELECT * FROM estates;             # Should show GAKINDU COURT
SELECT * FROM houses WHERE account_number = '348/4';  # Faith's house
SELECT * FROM bills;               # Should show the KES 400 bill
SELECT * FROM payments;            # Should show the payment
\q                    # Quit psql

# ==========================================
# STEP 11: STOP EVERYTHING
# ==========================================

# Stop the API server: Press Ctrl+C in the terminal running the server

# Stop Docker containers
docker compose down

# To remove ALL data (including database):
docker compose down -v

# ==========================================
# TROUBLESHOOTING
# ==========================================

# Problem: "permission denied" when running docker commands
# Fix: You need to log out and back in after adding yourself to docker group
# Or run: newgrp docker

# Problem: "port 5432 already in use"
# Fix: You have PostgreSQL running locally. Stop it:
#   sudo systemctl stop postgresql
# Or change the port in .env: DB_PORT=5433

# Problem: "Cannot find module"
# Fix: Run npm install again
#   npm install

# Problem: Migration fails
# Fix: Reset everything
#   docker compose down -v
#   docker compose up -d postgres redis
#   npm run db:migrate
#   npm run db:seed

# Problem: Server won't start
# Fix: Check if port 3000 is in use
#   sudo lsof -i :3000
#   kill -9 <PID>
