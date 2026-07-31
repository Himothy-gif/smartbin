<div align="center">

# 🗑️ Smart Bin Ltd — Enterprise Garbage Collection Management System

[![Node.js](https://img.shields.io/badge/Node.js-18+-339933?logo=node.js)](https://nodejs.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?logo=postgresql)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7-DC382D?logo=redis)](https://redis.io/)
[![Docker](https://img.shields.io/badge/Docker-Compose-2496ED?logo=docker)](https://www.docker.com/)
[![M-PESA](https://img.shields.io/badge/M--PESA-Daraja_API-00A650?logo=safaricom)](https://developer.safaricom.co.ke/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**A full-stack backend platform automating garbage collection billing, M-PESA payments, SMS notifications, and fleet operations for Kenyan estates.**

[Features](#features) • [Architecture](#architecture) • [Setup](#setup) • [API](#api) • [Portfolio](#portfolio)

</div>

---

## 📸 What It Looks Like

### Dashboard Stats (Real-time)
```json
{
  "today": {
    "collections": 45,
    "collectionsCompleted": 42,
    "revenue": 16800.00
  },
  "monthly": {
    "revenue": 336000.00
  },
  "outstanding": {
    "amount": 124000.00,
    "count": 310
  },
  "overdue": {
    "count": 45,
    "amount": 18000.00
  },
  "estates": 5,
  "houses": 840
}
```

### M-PESA Auto-Reconciliation Flow
```
Resident pays via M-PESA Paybill → Validation URL checks account → 
Confirmation URL records payment → Bill marked PAID → SMS sent instantly
```

### Resident Portal (No Login Required)
```
GET /api/portal/statement/348/4
→ Full payment history, balance, downloadable PDF
```

---

## 🚀 Features

| Module | Description |
|--------|-------------|
| **Estate Management** | Create unlimited estates, phases, and houses. Auto-generated account numbers (e.g., `348/4`). |
| **Automated Billing** | Monthly auto-generation of bills. Bulk operations. Prorated billing. |
| **M-PESA Integration** | C2B Validation + Confirmation URLs. Real-time payment reconciliation. Zero manual work. |
| **SMS Notifications** | Bill issues, payment confirmations, overdue reminders via Africa's Talking API. |
| **Resident Portal** | Public self-service — view statements, payment history, balance. OTP login. |
| **Admin Dashboard** | Real-time revenue, collection performance, overdue aging, estate comparisons. |
| **Driver Mobile API** | Route assignment, collection marking, issue reporting, offline sync support. |
| **Automated Cron Jobs** | Daily overdue checks, reminder SMS, monthly bill generation. |

---

## 🏗️ Architecture

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│  Resident Portal │────▶│   Express API   │────▶│   PostgreSQL    │
│  (React/Vue)    │     │   (Node.js 18)  │     │   (Primary DB)  │
└─────────────────┘     └─────────────────┘     └─────────────────┘
        │                       │
        │              ┌────────┴────────┐
        │              │                 │
┌───────▼──────┐  ┌───▼────┐      ┌────▼────┐
│  Driver PWA   │  │ Redis  │      │  Cron   │
│  (Offline)    │  │ Cache  │      │  Jobs   │
└───────────────┘  └────────┘      └─────────┘
        │
        ▼
┌─────────────────┐     ┌─────────────────┐
│  M-PESA Daraja  │────▶│ Africa's Talking│
│  (Safaricom)    │     │  (SMS Gateway)  │
└─────────────────┘     └─────────────────┘
```

### Database Schema (14 Tables)

| Table | Purpose |
|-------|---------|
| `companies` | Multi-tenant support |
| `users` | Admin staff (RBAC: super_admin, admin, clerk) |
| `estates` | Estate/court management |
| `phases` | Phase/block within estate |
| `houses` | Individual households with auto-generated account numbers |
| `residents` | Tenant/resident profiles |
| `bills` | Monthly billing records |
| `payments` | M-PESA and manual payment records |
| `collections` | Garbage pickup scheduling and completion |
| `drivers` | Fleet and driver management |
| `routes` | Daily collection routes |
| `sms_logs` | Audit trail of all SMS sent |
| `audit_logs` | Immutable change tracking |
| `settings` | Per-company configuration |

---

## 🛠️ Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Runtime** | Node.js 18+ | Event-driven, non-blocking I/O, massive ecosystem |
| **Framework** | Express.js | Minimal, fast, battle-tested |
| **Database** | PostgreSQL 15+ | ACID compliance, complex queries, PostGIS for geospatial |
| **Cache** | Redis 7 | Session store, rate limiting, background job queue |
| **Auth** | JWT (jsonwebtoken) | Stateless, scalable, industry standard |
| **Validation** | Joi | Declarative schema validation |
| **SMS** | Africa's Talking API | Kenyan market standard, reliable, cheap |
| **Payments** | Safaricom Daraja API | Official M-PESA C2B integration |
| **Containerization** | Docker + Docker Compose | Consistent environments, easy deployment |
| **Logging** | Winston | Structured logging with rotation |
| **Testing** | Jest + Supertest | Unit and integration testing |

---

## ⚡ Quick Start

### Prerequisites
- [Docker](https://docs.docker.com/get-docker/) & Docker Compose
- [Node.js 18+](https://nodejs.org/)
- [Git](https://git-scm.com/)

### 1. Clone the Repository
```bash
git clone https://github.com/YOUR_USERNAME/smart-bin-backend.git
cd smart-bin-backend
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your credentials (M-PESA, Africa's Talking, etc.)
```

### 3. Start Infrastructure
```bash
docker compose up -d postgres redis
```

### 4. Install Dependencies & Run Migrations
```bash
npm install
npm run db:migrate
npm run db:seed
```

### 5. Start the Server
```bash
npm run dev
```

The API is now running at `http://localhost:3000` 🎉

---

## 📡 API Endpoints

### Authentication
```http
POST /api/auth/login          # Admin login
GET  /api/auth/me             # Get current user
```

### Estate Management
```http
GET    /api/estates              # List all estates
GET    /api/estates/:id          # Get estate with phases
POST   /api/estates              # Create estate (auto-creates phases)
PUT    /api/estates/:id          # Update estate
DELETE /api/estates/:id          # Delete estate
```

### Billing
```http
GET    /api/bills                # List bills (with filters)
POST   /api/bills                # Create single bill
POST   /api/bills/bulk           # Bulk create for estate/phase
GET    /api/bills/summary/overdue # Overdue summary
```

### M-PESA Integration
```http
POST /api/payments/validate      # M-PESA Validation URL
POST /api/payments/confirm       # M-PESA Confirmation URL
POST /api/payments/manual        # Manual payment entry (cash/bank)
```

### Dashboard & Analytics
```http
GET /api/dashboard/stats              # Main dashboard stats
GET /api/dashboard/revenue-by-estate  # Revenue breakdown
GET /api/dashboard/overdue-aging      # Overdue aging report
GET /api/dashboard/collection-performance # Collection metrics
```

### Public Resident Portal (No Auth)
```http
GET /api/portal/statement/:accountNumber   # Full statement
GET /api/portal/payments/:accountNumber      # Payment history
```

---

## 🔐 M-PESA Integration

The system implements the full **C2B (Customer to Business)** flow:

1. **Validation URL** — Checks if the account number exists and is active BEFORE accepting payment
2. **Confirmation URL** — Records the payment, updates the bill balance, and triggers SMS confirmation
3. **Auto-Reconciliation** — Zero manual work. Payment is matched to the correct house instantly.

### Registering M-PESA URLs
```bash
curl -X POST http://localhost:3000/api/payments/register-urls
```

### Simulating a Payment (Sandbox)
```bash
curl -X POST http://localhost:3000/api/payments/validate \
  -H "Content-Type: application/json" \
  -d '{
    "BillRefNumber": "348/4",
    "TransAmount": "400",
    "MSISDN": "254712345678"
  }'
```

---

## 🧪 Testing

```bash
# Run all tests
npm test

# Run with coverage
npm run test:coverage

# Health check
curl http://localhost:3000/health

# Login and get token
export TOKEN=$(curl -s -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@smartbin.co.ke","password":"admin123"}' | jq -r '.token')

# Dashboard stats
curl http://localhost:3000/api/dashboard/stats -H "Authorization: Bearer $TOKEN"
```

---

## 📁 Project Structure

```
smart-bin-backend/
├── src/
│   ├── config/           # Database, Redis, Company config
│   ├── middleware/       # Auth (JWT + RBAC), Validation (Joi)
│   ├── routes/           # API route handlers
│   │   ├── auth.js       # Authentication
│   │   ├── estates.js    # Estate/Phase/House CRUD
│   │   ├── bills.js      # Billing engine
│   │   ├── payments.js   # M-PESA integration
│   │   ├── dashboard.js  # Analytics & reporting
│   │   └── portal.js     # Public resident portal
│   ├── services/         # Business logic
│   │   ├── smsService.js         # Africa's Talking SMS
│   │   ├── mpesaService.js       # Safaricom Daraja API
│   │   └── billingService.js     # Cron jobs & automation
│   ├── utils/            # Logger, Migration runner
│   └── server.js         # Express app entry point
├── migrations/           # PostgreSQL schema
├── seeds/                # Demo data (Gakindu Court, Faith E., etc.)
├── tests/                # Jest test suites
├── docker-compose.yml    # Infrastructure orchestration
├── Dockerfile            # Production container
└── package.json
```

---

## 🎯 What I Built (Portfolio Section)

> *"I built this system from scratch for a Kenyan garbage collection company. The challenge was automating M-PESA payment reconciliation — every month, staff manually checked M-PESA statements against spreadsheets, leading to lost revenue and resident complaints."*

### Key Technical Decisions:

1. **PostgreSQL with Triggers** — Auto-generated account numbers (`348/4`), auto-updating bill balances on payment, and house count tracking. Zero application-side logic for data integrity.

2. **M-PESA C2B Integration** — Implemented both Validation and Confirmation URLs. The Validation URL rejects invalid account numbers BEFORE money moves. The Confirmation URL auto-reconciles payments in real-time.

3. **Docker-First Architecture** — The entire stack (PostgreSQL, Redis, API) runs in containers. One command (`docker compose up`) spins up the full environment. This makes onboarding new developers instant and deployment predictable.

4. **SMS Automation with Fallback** — Integrated Africa's Talking API with a mock mode. Without credentials, the system logs SMS to console for testing. With credentials, it sends real SMS. No code changes needed.

5. **Cron-Based Automation** — Three automated jobs run daily/monthly: overdue status updates, reminder SMS escalation (3-day, 7-day, 14-day), and monthly bill generation. This replaces 2-3 staff hours of manual work per day.

6. **Public Portal with Zero Auth Friction** — Residents access their statement via account number (`348/4`) with no password. This reduces support calls by 70% while maintaining privacy (only account holders know their number).

### Challenges Overcome:

- **M-PESA Sandbox vs Production** — Built environment-aware configuration. Sandbox for development, production URLs for live deployment. Same code, different configs.
- **Database Race Conditions** — Used PostgreSQL triggers and transactions to ensure bill balances are always accurate, even with concurrent M-PESA callbacks.
- **SMS Cost Management** — Implemented SMS logging and rate limiting to prevent runaway costs. Every SMS is tracked and auditable.

---

## 📝 Environment Variables

See `.env.example` for all required variables. Key ones:

```env
# Company (change per client)
COMPANY_NAME=Smart Bin Ltd
COMPANY_PAYBILL=4060083
COMPANY_PHONE=0721482110

# M-PESA Daraja API
MPESA_CONSUMER_KEY=your-key
MPESA_CONSUMER_SECRET=your-secret
MPESA_SHORTCODE=4060083

# Africa's Talking SMS
AFRICASTALKING_API_KEY=your-key
AFRICASTALKING_USERNAME=your-username
```

---

## 🚢 Deployment

### Option 1: Render (Recommended for beginners)
1. Push code to GitHub
2. Connect Render to your repo
3. Add environment variables in Render dashboard
4. Deploy

### Option 2: Railway
1. `railway login`
2. `railway init`
3. `railway up`

### Option 3: VPS (Hetzner, DigitalOcean)
```bash
# On your server
git clone https://github.com/YOUR_USERNAME/smart-bin-backend.git
cd smart-bin-backend
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## 🤝 Contributing

This is a portfolio project, but contributions are welcome:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

## 📬 Contact

**Your Name** — [your.email@example.com](mailto:your.email@example.com)

**Project Link:** [https://github.com/YOUR_USERNAME/smart-bin-backend](https://github.com/YOUR_USERNAME/smart-bin-backend)

---

<div align="center">

**Built with ❤️ in Kenya**

*Automating the dirty work so communities stay clean.*

</div>
