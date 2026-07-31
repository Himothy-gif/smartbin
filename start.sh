#!/bin/bash

echo "=========================================="
echo "  SMART BIN LTD - QUICK START"
echo "=========================================="
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    exit 1
fi

echo "🚀 Step 1: Starting PostgreSQL and Redis..."
docker-compose up -d postgres redis

echo ""
echo "⏳ Waiting for database to be ready..."
sleep 5

echo ""
echo "📦 Step 2: Installing dependencies..."
npm install

echo ""
echo "🏗️  Step 3: Running database migrations..."
npm run db:migrate

echo ""
echo "🌱 Step 4: Seeding demo data..."
npm run db:seed

echo ""
echo "🔥 Step 5: Starting API server..."
echo ""
echo "Server will start at: http://localhost:3000"
echo ""
echo "Test endpoints:"
echo "  Health:     curl http://localhost:3000/health"
echo "  Login:      curl -X POST http://localhost:3000/api/auth/login \"
echo "              -H 'Content-Type: application/json' \"
echo "              -d '{"email":"admin@smartbin.co.ke","password":"admin123"}'"
echo "  Statement:  curl http://localhost:3000/api/portal/statement/348/4"
echo ""
echo "=========================================="

npm run dev
