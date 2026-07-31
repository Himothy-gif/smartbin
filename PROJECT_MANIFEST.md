# Smart Bin Ltd — Project Manifest
# This file documents every component for portfolio review

## Project Overview
- Name: Smart Bin Ltd — Enterprise Garbage Collection Management System
- Type: Backend API (REST)
- Language: JavaScript (Node.js)
- Database: PostgreSQL 15+ with PostGIS
- Cache: Redis 7
- Containerization: Docker + Docker Compose
- Target Market: Kenyan garbage collection companies

## Problem Solved
Manual garbage collection billing and M-PESA reconciliation causes:
- Revenue leakage from missed/misallocated payments
- Hours of staff time on spreadsheets
- Resident complaints about lost payments
- No real-time visibility into operations

## Solution
Automated digital platform with:
- Real-time M-PESA payment reconciliation
- Automated SMS notifications
- Resident self-service portal
- Admin dashboard with analytics
- Driver mobile app API

## File Inventory

### Configuration (3 files)
- src/config/database.js      — PostgreSQL connection pool
- src/config/redis.js         — Redis client setup
- src/config/company.js       — Company details & SMS templates

### Middleware (2 files)
- src/middleware/auth.js      — JWT authentication + RBAC
- src/middleware/validation.js — Joi schema validation

### Routes (10 files)
- src/routes/auth.js          — Login, current user
- src/routes/estates.js       — Estate CRUD + auto-phase creation
- src/routes/houses.js        — House CRUD + account lookup
- src/routes/residents.js     — Resident CRUD
- src/routes/bills.js         — Billing + bulk operations
- src/routes/payments.js      — M-PESA validation/confirmation
- src/routes/collections.js   — Collection scheduling
- src/routes/drivers.js       — Driver CRUD
- src/routes/dashboard.js     — Analytics & reporting
- src/routes/portal.js        — Public resident portal

### Services (3 files)
- src/services/smsService.js      — Africa's Talking integration
- src/services/mpesaService.js    — Safaricom Daraja API
- src/services/billingService.js  — Cron jobs (overdue, reminders, monthly bills)

### Utilities (2 files)
- src/utils/logger.js         — Winston structured logging
- src/utils/migrate.js        — Database migration runner

### Infrastructure (6 files)
- docker-compose.yml          — Full stack orchestration
- Dockerfile                  — Production container
- migrations/001_initial_schema.sql — 14 tables, indexes, triggers
- seeds/seed.js               — Demo data (Gakindu Court, Faith E.)
- .env.example                — Environment variable template
- .env                        — Development defaults

### Documentation (5 files)
- README.md                   — Technical documentation
- GITHUB_README.md            — Portfolio README
- FEDORA_SETUP.md             — Fedora Linux setup guide
- API_TESTS.sh                — Curl command reference
- start.sh                    — One-command startup script

### DevOps (3 files)
- Makefile                    — Common commands
- .github/workflows/ci.yml    — GitHub Actions CI/CD
- LICENSE                     — MIT License

### Project Config (3 files)
- package.json                — Dependencies & scripts
- .gitignore                  — Git ignore rules
- server.js                   — Express app entry point

## Database Schema (14 Tables)
1. companies       — Multi-tenant support
2. users           — Admin staff (super_admin, admin, clerk)
3. estates         — Estate/court management
4. phases          — Phase/block within estate
5. houses          — Households with auto-generated account numbers
6. residents       — Tenant profiles
7. bills           — Monthly billing
8. payments        — M-PESA & manual payments
9. collections     — Garbage pickup records
10. drivers        — Fleet management
11. routes         — Daily collection routes
12. sms_logs       — SMS audit trail
13. audit_logs     — Change tracking
14. settings       — Per-company config

## Key Features Implemented
✅ JWT Authentication with Role-Based Access Control
✅ PostgreSQL Triggers (auto-account numbers, auto-balances, auto-counts)
✅ M-PESA C2B Integration (Validation + Confirmation URLs)
✅ Africa's Talking SMS (bill issue, payment confirmation, overdue reminders)
✅ Automated Cron Jobs (overdue checks, reminders, monthly billing)
✅ Public Resident Portal (no auth required)
✅ Admin Dashboard API (real-time stats, revenue, aging reports)
✅ Docker Containerization (one-command startup)
✅ Database Migrations & Seeding
✅ Input Validation (Joi schemas)
✅ Rate Limiting & Security Headers (Helmet)
✅ Structured Logging (Winston)
✅ GitHub Actions CI/CD

## API Endpoint Count: 35+
## Total Lines of Code: ~3,500+
## Test Coverage: Ready for Jest implementation
## Deployment Targets: Render, Railway, Hetzner, AWS

## Demo Data
- Company: Smart Bin Ltd
- Estate: GAKINDU COURT (4 phases, 84 houses)
- Sample Resident: Faith E. (Account: 348/4)
- Sample Bill: KES 400 (Dec 2024)
- Sample Payment: KES 400 (M-PESA code: ABC123XYZ)
- Sample Driver: James Mwangi

## What Makes This Portfolio-Worthy
1. Real-world problem (garbage collection billing in Kenya)
2. Production-ready architecture (Docker, PostgreSQL, Redis)
3. Third-party integrations (M-PESA, Africa's Talking)
4. Automated processes (cron jobs, triggers)
5. Security best practices (JWT, RBAC, validation, rate limiting)
6. Complete documentation (README, setup guides, API tests)
7. CI/CD pipeline (GitHub Actions)
8. Multi-tenant design (supports multiple companies)

## Next Steps for Portfolio Enhancement
- [ ] Add Jest test suites (auth, estates, bills, payments)
- [ ] Add API documentation (Swagger/OpenAPI)
- [ ] Add frontend admin dashboard (React)
- [ ] Add driver mobile PWA
- [ ] Deploy to Render/Railway with live demo
- [ ] Add Postman collection
- [ ] Add database diagram to README
- [ ] Record demo video (Loom/YouTube)
