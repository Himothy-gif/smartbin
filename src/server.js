const express = require('express');
const cors = require('cors');
const helmet = require('helmet');
const rateLimit = require('express-rate-limit');
require('dotenv').config();

const db = require('./config/database');
const redis = require('./config/redis');
const logger = require('./utils/logger');
const billingService = require('./services/billingService');

// Routes
const authRoutes = require('./routes/auth');
const estateRoutes = require('./routes/estates');
const houseRoutes = require('./routes/houses');
const residentRoutes = require('./routes/residents');
const billRoutes = require('./routes/bills');
const paymentRoutes = require('./routes/payments');
const collectionRoutes = require('./routes/collections');
const driverRoutes = require('./routes/drivers');
const dashboardRoutes = require('./routes/dashboard');

const app = express();
const PORT = process.env.API_PORT || 3000;

// Security middleware
app.use(helmet());
app.use(cors({
  origin: process.env.CORS_ORIGIN || '*',
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'],
  allowedHeaders: ['Content-Type', 'Authorization'],
}));

// Rate limiting
const limiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // limit each IP to 100 requests per windowMs
  message: { error: 'Too many requests, please try again later.' }
});
app.use('/api/', limiter);

// Body parsing
app.use(express.json({ limit: '10mb' }));
app.use(express.urlencoded({ extended: true }));

// Request logging
app.use((req, res, next) => {
  logger.info(`${req.method} ${req.path} - ${req.ip}`);
  next();
});

// Health check
app.get('/health', async (req, res) => {
  try {
    await db.query('SELECT 1');
    const redisHealth = redis.isReady ? 'connected' : 'disconnected';
    res.json({ 
      status: 'healthy', 
      database: 'connected',
      redis: redisHealth,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    res.status(503).json({ 
      status: 'unhealthy', 
      database: 'disconnected',
      error: error.message 
    });
  }
});

// API Routes
app.use('/api/auth', authRoutes);
app.use('/api/estates', estateRoutes);
app.use('/api/houses', houseRoutes);
app.use('/api/residents', residentRoutes);
app.use('/api/bills', billRoutes);
app.use('/api/payments', paymentRoutes);
app.use('/api/collections', collectionRoutes);
app.use('/api/drivers', driverRoutes);
app.use('/api/dashboard', dashboardRoutes);

// Public resident portal routes (no auth required)
app.use('/api/portal', require('./routes/portal'));

// Error handling
app.use((err, req, res, next) => {
  logger.error(err.stack);
  res.status(500).json({ 
    error: process.env.NODE_ENV === 'production' 
      ? 'Internal server error' 
      : err.message 
  });
});

// 404 handler
app.use((req, res) => {
  res.status(404).json({ error: 'Route not found' });
});

// Start server
app.listen(PORT, () => {
  console.log(`============================================`);
  console.log(`  SMART BIN LTD API SERVER`);
  console.log(`  Port: ${PORT}`);
  console.log(`  Environment: ${process.env.NODE_ENV || 'development'}`);
  console.log(`  Company: ${process.env.COMPANY_NAME || 'Smart Bin Ltd'}`);
  console.log(`============================================`);

  // Start billing cron jobs
  if (process.env.NODE_ENV === 'production') {
    billingService.start();
  }
});

// Graceful shutdown
process.on('SIGTERM', () => {
  console.log('SIGTERM received, shutting down gracefully');
  billingService.stop();
  process.exit(0);
});

process.on('SIGINT', () => {
  console.log('SIGINT received, shutting down gracefully');
  billingService.stop();
  process.exit(0);
});

module.exports = app;
