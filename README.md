# Smart Bin Ltd — Enterprise Garbage Collection Management System

## Overview
A comprehensive digital platform for managing garbage collection operations across multiple estates and courts. Features automated billing, M-PESA payment reconciliation, SMS notifications, driver route management, and real-time analytics.

## Tech Stack
- **Backend:** Node.js + Express.js
- **Database:** PostgreSQL 15+ with PostGIS
- **Cache/Queue:** Redis
- **Auth:** JWT (JSON Web Tokens)
- **SMS:** Africa's Talking API
- **Payments:** Safaricom M-PESA Daraja API
- **Containerization:** Docker + Docker Compose

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Node.js 18+ (for local development)

### 1. Clone & Setup
```bash
git clone <repo-url>
cd smart-bin-backend
cp .env.example .env
# Edit .env with your actual credentials
```

### 2. Start Infrastructure
```bash
docker-compose up -d postgres redis
```

### 3. Run Migrations
```bash
npm install
npm run db:migrate
```

### 4. Seed Demo Data
```bash
npm run db:seed
```

### 5. Start API Server
```bash
npm run dev
```

The API will be available at `http://localhost:3000`

### 6. Full Docker Stack (Production)
```bash
docker-compose up -d
```

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Admin login |
| GET | `/api/auth/me` | Get current user |

### Estates
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/estates` | List all estates |
| GET | `/api/estates/:id` | Get estate with phases |
| POST | `/api/estates` | Create estate (auto-creates phases) |
| PUT | `/api/estates/:id` | Update estate |
| DELETE | `/api/estates/:id` | Delete estate |

### Houses
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/houses/phase/:phaseId` | List houses in phase |
| GET | `/api/houses/account/:accountNumber` | Lookup by account (e.g., 348/4) |
| POST | `/api/houses` | Create house (auto-generates account number) |
| PUT | `/api/houses/:id` | Update house |

### Residents
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/residents/house/:houseId` | List residents |
| POST | `/api/residents` | Create resident |
| PUT | `/api/residents/:id` | Update resident |

### Bills
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/bills` | List bills (with filters) |
| GET | `/api/bills/house/:houseId` | Bills for specific house |
| POST | `/api/bills` | Create single bill |
| POST | `/api/bills/bulk` | Bulk create for estate/phase |
| GET | `/api/bills/summary/overdue` | Overdue summary |

### Payments (M-PESA)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/payments/validate` | M-PESA Validation URL |
| POST | `/api/payments/confirm` | M-PESA Confirmation URL |
| GET | `/api/payments/house/:houseId` | Payment history |
| POST | `/api/payments/manual` | Manual payment entry |

### Collections
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/collections` | List collections |
| POST | `/api/collections/schedule` | Schedule collections |
| PUT | `/api/collections/:id/complete` | Mark complete |

### Drivers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/drivers` | List drivers |
| POST | `/api/drivers` | Create driver |
| PUT | `/api/drivers/:id` | Update driver |

### Dashboard
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/dashboard/stats` | Main dashboard stats |
| GET | `/api/dashboard/revenue-by-estate` | Revenue breakdown |
| GET | `/api/dashboard/collection-performance` | Collection metrics |
| GET | `/api/dashboard/overdue-aging` | Overdue aging report |

### Public Portal
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/portal/statement/:accountNumber` | Resident statement |
| GET | `/api/portal/payments/:accountNumber` | Payment history |

## M-PESA Integration Setup

1. Register at [Safaricom Developer Portal](https://developer.safaricom.co.ke)
2. Create an app and get Consumer Key & Secret
3. Configure `.env` with your credentials
4. Register your Validation & Confirmation URLs:
```bash
curl -X POST http://localhost:3000/api/payments/register-urls
```

## SMS Setup

1. Register at [Africa's Talking](https://africastalking.com)
2. Get API Key and Username
3. Configure `.env` with your credentials
4. SMS will work in mock mode without credentials (logs to console)

## Database Schema

See `migrations/001_initial_schema.sql` for the complete schema including:
- 14 tables (companies, users, estates, phases, houses, residents, bills, payments, collections, drivers, routes, sms_logs, audit_logs, settings)
- Indexes for performance
- Triggers for auto-updating timestamps, account numbers, balances, and house counts

## Cron Jobs (Automated)

| Schedule | Job | Description |
|----------|-----|-------------|
| Daily 6 AM | Update overdue status | Marks past-due bills as overdue |
| Daily 9 AM | Send reminders | SMS to 3/7/14/30-day overdue accounts |
| Monthly 1st 6 AM | Generate bills | Auto-creates bills for all active houses |

## Environment Variables

See `.env.example` for all required variables. Key ones:

```env
# Company (change per client)
COMPANY_NAME=Smart Bin Ltd
COMPANY_PAYBILL=4060083
COMPANY_PHONE=0721482110

# M-PESA
MPESA_CONSUMER_KEY=your-key
MPESA_CONSUMER_SECRET=your-secret
MPESA_SHORTCODE=4060083

# SMS
AFRICASTALKING_API_KEY=your-key
AFRICASTALKING_USERNAME=your-username
```

## Testing

```bash
# Run tests
npm test

# Health check
curl http://localhost:3000/health

# Login
curl -X POST http://localhost:3000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@smartbin.co.ke","password":"admin123"}'

# Get estates
curl http://localhost:3000/api/estates \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Project Structure
```
smart-bin-backend/
├── src/
│   ├── config/         # Database, Redis, Company config
│   ├── middleware/     # Auth, Validation
│   ├── models/         # Data models
│   ├── routes/         # API routes
│   ├── services/       # Business logic (SMS, M-PESA, Billing)
│   ├── utils/          # Logger, Migrations
│   └── server.js       # Entry point
├── migrations/         # Database schema
├── seeds/              # Demo data
├── docker-compose.yml
├── Dockerfile
└── package.json
```

## License
MIT

## Support
For issues or questions, contact the development team.
