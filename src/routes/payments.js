// ============================================================================
// PAYMENTS ROUTE — M-PESA Integration & Payment Management
// ============================================================================
// This file handles EVERYTHING related to money:
//   1. M-PESA Validation URL  — Safaricom asks "is this account valid?" BEFORE taking money
//   2. M-PESA Confirmation URL — Safaricom says "payment done" → we record it automatically
//   3. Manual payment entry    — For cash, bank transfer, etc.
//   4. Payment history lookup  — See all payments for a house
// ============================================================================

// --- IMPORTS ---
// express = the web framework. Router = mini-app for handling routes under /api/payments
const express = require('express');
const router = express.Router();

// v4:uuidv4 = generates unique IDs like "550e8400-e29b-41d4-a716-446655440000"
// We use these for every new record (payment, bill, etc.)
const { v4: uuidv4 } = require('uuid');

// db = our PostgreSQL connection pool. 
// db.query() sends SQL to the database and returns results
const db = require('../config/database');

// company = holds company details (name, paybill number, phone) 
// and SMS template functions (getBillSms, getPaymentConfirmationSms, etc.)
const company = require('../config/company');

// authenticate = middleware that checks JWT token on protected routes
// authorize = checks if user has the right role (super_admin, admin, clerk)
const { authenticate, authorize } = require('../middleware/auth');

// ============================================================================
// ROUTE 1: M-PESA VALIDATION URL (POST /api/payments/validate)
// ============================================================================
// WHEN DOES THIS FIRE?
//   When a resident opens M-PESA → Lipa na M-PESA → Paybill → enters account number
//   Safaricom sends a request HERE before taking the money
// 
// WHAT DOES IT DO?
//   1. Receives the account number (BillRefNumber) from Safaricom
//   2. Checks if that account exists in our database
//   3. Checks if the account is active (not suspended)
//   4. Returns "Accept" (ResultCode: 0) or "Reject" (ResultCode: 1)
// 
// WHY THIS MATTERS:
//   If we return "Reject", Safaricom CANCELS the payment. 
//   Resident gets "Invalid account" on their phone. No lost money.
// ============================================================================
router.post('/validate', async (req, res) => {
  try {
    // req.body = the JSON data Safaricom sends us
    // BillRefNumber = the account number the resident typed (e.g., "348/4")
    // TransAmount = how much they want to pay (e.g., "400")
    // MSISDN = their phone number (e.g., "254712345678")
    const { BillRefNumber, TransAmount, MSISDN } = req.body;
    
    // Log the validation request so we can debug later
    console.log('M-PESA Validation Request:', req.body);
    
    // --- STEP 1: FIND THE HOUSE BY ACCOUNT NUMBER ---
    // We JOIN with residents to get the resident's name for the response
    // LEFT JOIN = include house even if no resident is linked (rare but possible)
    const houseResult = await db.query(
      `SELECT h.id, h.status, r.full_name, r.phone_number
       FROM houses h
       LEFT JOIN residents r ON r.house_id = h.id AND r.is_primary = true
       WHERE h.account_number = $1`,
      [BillRefNumber]
    );
    
    // --- STEP 2: CHECK IF ACCOUNT EXISTS ---
    // If no rows returned = account number doesn't exist in our database
    if (houseResult.rows.length === 0) {
      console.log(`Validation FAILED: Account ${BillRefNumber} not found`);
      // ResultCode: 1 = REJECT. Safaricom will show "Invalid account" to resident
      return res.json({ ResultCode: 1, ResultDesc: 'Invalid account number' });
    }
    
    // --- STEP 3: CHECK IF ACCOUNT IS ACTIVE ---
    // Status can be: 'active', 'inactive', 'suspended', 'vacant'
    // Only 'active' accounts can receive payments
    const house = houseResult.rows[0];
    
    if (house.status !== 'active') {
      console.log(`Validation FAILED: Account ${BillRefNumber} is ${house.status}`);
      return res.json({ ResultCode: 1, ResultDesc: 'Account is not active' });
    }
    
    // --- STEP 4: ACCEPT THE PAYMENT ---
    // ResultCode: 0 = ACCEPT. Safaricom proceeds to take the money
    console.log(`Validation SUCCESS: Account ${BillRefNumber} found for ${house.full_name}`);
    
    res.json({ 
      ResultCode: 0, 
      ResultDesc: 'Accepted',
      accountNumber: BillRefNumber,
      houseId: house.id
    });
    
  } catch (error) {
    // If our server crashes during validation, we STILL return "Accept"
    // Why? Because rejecting valid payments is worse than accepting invalid ones
    // We can always refund, but we can't undo a rejected payment
    console.error('Validation error:', error);
    res.json({ ResultCode: 1, ResultDesc: 'System error' });
  }
});

// ============================================================================
// ROUTE 2: M-PESA CONFIRMATION URL (POST /api/payments/confirm)
// ============================================================================
// WHEN DOES THIS FIRE?
//   After Safaricom successfully takes the money from the resident
//   This is the "receipt" — Safaricom tells us the payment is DONE
// 
// WHAT DOES IT DO?
//   1. Receives the M-PESA transaction details
//   2. Finds the house by account number
//   3. Finds the most recent unpaid bill for that house
//   4. Records the payment in our database
//   5. Updates the bill balance (trigger handles this automatically)
//   6. Sends SMS confirmation to the resident
// 
// WHY THIS MATTERS:
//   This is where the MAGIC happens. Zero manual work.
//   Faith pays → this endpoint fires → bill marked PAID → SMS sent → done.
// ============================================================================
router.post('/confirm', async (req, res) => {
  try {
    // Same fields as validation, PLUS:
    // TransID = the M-PESA receipt number (e.g., "ABC123XYZ")
    // This is what residents reference when they call support
    const { BillRefNumber, TransAmount, TransID, MSISDN, TransTime } = req.body;
    
    console.log('M-PESA Confirmation:', req.body);
    
    // --- STEP 1: FIND THE HOUSE ---
    const houseResult = await db.query(
      `SELECT h.id, r.full_name, r.phone_number
       FROM houses h
       LEFT JOIN residents r ON r.house_id = h.id AND r.is_primary = true
       WHERE h.account_number = $1`,
      [BillRefNumber]
    );
    
    // If account not found, we still return "Received" to Safaricom
    // This prevents Safaricom from retrying and flooding us
    if (houseResult.rows.length === 0) {
      return res.json({ ResultCode: 0, ResultDesc: 'Received' });
    }
    
    const house = houseResult.rows[0];
    
    // --- STEP 2: FIND THE MOST RECENT UNPAID BILL ---
    // We look for bills with status: 'pending', 'partial', or 'overdue'
    // ORDER BY created_at DESC = newest bill first
    // LIMIT 1 = only the most recent one
    const billResult = await db.query(
      `SELECT id, balance FROM bills 
       WHERE house_id = $1 AND status IN ('pending', 'partial', 'overdue')
       ORDER BY created_at DESC LIMIT 1`,
      [house.id]
    );
    
    // If no unpaid bill found, we still record the payment
    // This handles cases where resident overpays or pays early
    const billId = billResult.rows.length > 0 ? billResult.rows[0].id : null;
    
    // --- STEP 3: RECORD THE PAYMENT ---
    // We insert into the payments table with ALL the M-PESA details
    // This creates an audit trail — every KES is traceable
    const paymentId = uuidv4();
    await db.query(
      `INSERT INTO payments (id, bill_id, house_id, amount, mpesa_code, mpesa_phone, payment_method, status)
       VALUES ($1, $2, $3, $4, $5, $6, 'mpesa', 'completed')`,
      [paymentId, billId, house.id, parseFloat(TransAmount), TransID, MSISDN]
    );
    
    // --- STEP 4: CALCULATE NEW BALANCE ---
    // We sum all unpaid bills for this house
    // COALESCE = if no unpaid bills, return 0 instead of NULL
    const balanceResult = await db.query(
      `SELECT COALESCE(SUM(balance), 0) as total_balance FROM bills WHERE house_id = $1 AND status != 'paid'`,
      [house.id]
    );
    const newBalance = parseFloat(balanceResult.rows[0].total_balance) - parseFloat(TransAmount);
    
    // --- STEP 5: SEND SMS CONFIRMATION ---
    // We try to send SMS. If it fails (no API key, no internet), we log it but don't crash
    try {
      const smsService = require('../services/smsService');
      await smsService.sendPaymentConfirmation(
        house.phone_number,           // Resident's phone
        house.full_name || 'Resident', // Resident's name (fallback if null)
        BillRefNumber,                // Account number
        TransAmount,                  // Amount paid
        TransID,                      // M-PESA receipt code
        Math.max(0, newBalance)       // New balance (can't be negative)
      );
    } catch (smsError) {
      // Log the error but DON'T crash the payment processing
      // SMS failure is annoying, but payment recording is critical
      console.error('SMS failed:', smsError);
    }
    
    // --- STEP 6: ACKNOWLEDGE TO SAFARICOM ---
    // We MUST return ResultCode: 0, or Safaricom will keep retrying
    res.json({ ResultCode: 0, ResultDesc: 'Received' });
    
  } catch (error) {
    // Even if everything crashes, tell Safaricom we got it
    console.error('Confirmation error:', error);
    res.json({ ResultCode: 0, ResultDesc: 'Received' });
  }
});

// ============================================================================
// ROUTE 3: GET PAYMENTS FOR A HOUSE (GET /api/payments/house/:houseId)
// ============================================================================
// PROTECTED ROUTE — requires admin login (JWT token)
// Shows all payments made for a specific house
// Used by admin dashboard to see payment history
// ============================================================================
router.get('/house/:houseId', authenticate, async (req, res) => {
  try {
    // req.params.houseId = the UUID from the URL
    // e.g., /api/payments/house/550e8400-e29b-41d4-a716-446655440000
    const result = await db.query(
      `SELECT p.*, b.bill_period 
       FROM payments p
       LEFT JOIN bills b ON p.bill_id = b.id
       WHERE p.house_id = $1
       ORDER BY p.paid_at DESC`,
      [req.params.houseId]
    );
    res.json({ payments: result.rows });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ============================================================================
// ROUTE 4: MANUAL PAYMENT ENTRY (POST /api/payments/manual)
// ============================================================================
// PROTECTED ROUTE — admin/clerk only
// For recording payments that did NOT come through M-PESA:
//   - Cash payments (resident pays driver or office directly)
//   - Bank transfers (resident sends money to company bank account)
//   - Other methods
// ============================================================================
router.post('/manual', authenticate, authorize('super_admin', 'admin', 'clerk'), async (req, res) => {
  try {
    // req.body contains all the payment details from the admin form
    const { house_id, amount, payment_method, payment_reference, bill_id } = req.body;
    const id = uuidv4();
    
    const result = await db.query(
      `INSERT INTO payments (id, bill_id, house_id, amount, payment_method, payment_reference, status)
       VALUES ($1, $2, $3, $4, $5, $6, 'completed') RETURNING *`,
      [id, bill_id, house_id, amount, payment_method, payment_reference]
    );
    
    res.status(201).json({ payment: result.rows[0] });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// ============================================================================
// EXPORT THE ROUTER
// ============================================================================
// This makes all the routes above available to server.js
// server.js does: app.use('/api/payments', paymentRoutes)
// So '/validate' becomes '/api/payments/validate'
// ============================================================================
module.exports = router;
