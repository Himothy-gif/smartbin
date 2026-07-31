const express = require('express');
const db = require('../config/database');
const company = require('../config/company');
const router = express.Router();

// Get statement by account number
router.get('/statement/:accountNumber', async (req, res) => {
  try {
    const { accountNumber } = req.params;

    // Get house and resident info
    const houseResult = await db.query(
      `SELECT h.*, p.phase_number, e.name as estate_name,
              r.full_name, r.phone_number, r.email
       FROM houses h
       JOIN phases p ON h.phase_id = p.id
       JOIN estates e ON p.estate_id = e.id
       LEFT JOIN residents r ON r.house_id = h.id AND r.is_primary = true
       WHERE h.account_number = $1`,
      [accountNumber]
    );

    if (houseResult.rows.length === 0) {
      return res.status(404).json({ error: 'Account not found' });
    }

    const house = houseResult.rows[0];

    // Get bills
    const billsResult = await db.query(
      `SELECT * FROM bills WHERE house_id = $1 ORDER BY created_at DESC`,
      [house.id]
    );

    // Get payments
    const paymentsResult = await db.query(
      `SELECT * FROM payments WHERE house_id = $1 ORDER BY paid_at DESC`,
      [house.id]
    );

    // Calculate totals
    const totalBilled = billsResult.rows.reduce((sum, b) => sum + parseFloat(b.amount), 0);
    const totalPaid = paymentsResult.rows.reduce((sum, p) => sum + parseFloat(p.amount), 0);
    const balance = totalBilled - totalPaid;

    res.json({
      account: {
        account_number: house.account_number,
        house_number: house.house_number,
        phase: house.phase_number,
        estate: house.estate_name,
        resident_name: house.full_name,
        phone: house.phone_number,
      },
      summary: {
        total_billed: totalBilled,
        total_paid: totalPaid,
        balance: balance,
        status: balance > 0 ? 'outstanding' : 'paid'
      },
      bills: billsResult.rows,
      payments: paymentsResult.rows,
      payment_instructions: company.getPaymentInstructions(accountNumber, balance > 0 ? balance : 0)
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get payment history
router.get('/payments/:accountNumber', async (req, res) => {
  try {
    const houseResult = await db.query(
      'SELECT id FROM houses WHERE account_number = $1',
      [req.params.accountNumber]
    );

    if (houseResult.rows.length === 0) {
      return res.status(404).json({ error: 'Account not found' });
    }

    const result = await db.query(
      `SELECT p.*, b.bill_period 
       FROM payments p
       LEFT JOIN bills b ON p.bill_id = b.id
       WHERE p.house_id = $1
       ORDER BY p.paid_at DESC`,
      [houseResult.rows[0].id]
    );

    res.json({ payments: result.rows });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
