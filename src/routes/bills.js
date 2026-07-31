const express = require('express');
const { v4: uuidv4 } = require('uuid');
const db = require('../config/database');
const { authenticate, authorize } = require('../middleware/auth');
const company = require('../config/company');
const router = express.Router();

// Get all bills (with filters)
router.get('/', authenticate, async (req, res) => {
  try {
    const { status, estate_id, overdue_only, page = 1, limit = 50 } = req.query;
    const offset = (page - 1) * limit;

    let query = `
      SELECT b.*, h.account_number, h.house_number, p.phase_number,
             e.name as estate_name, r.full_name as resident_name, r.phone_number
      FROM bills b
      JOIN houses h ON b.house_id = h.id
      JOIN phases p ON h.phase_id = p.id
      JOIN estates e ON p.estate_id = e.id
      LEFT JOIN residents r ON r.house_id = h.id AND r.is_primary = true
      WHERE e.company_id = $1
    `;
    const params = [req.user.company_id];
    let paramIndex = 2;

    if (status) {
      query += ` AND b.status = $${paramIndex}`;
      params.push(status);
      paramIndex++;
    }

    if (estate_id) {
      query += ` AND e.id = $${paramIndex}`;
      params.push(estate_id);
      paramIndex++;
    }

    if (overdue_only === 'true') {
      query += ` AND b.due_date < CURRENT_DATE AND b.status != 'paid'`;
    }

    query += ` ORDER BY b.created_at DESC LIMIT $${paramIndex} OFFSET $${paramIndex + 1}`;
    params.push(limit, offset);

    const result = await db.query(query, params);

    // Get total count
    const countResult = await db.query(
      `SELECT COUNT(*) FROM bills b
       JOIN houses h ON b.house_id = h.id
       JOIN phases p ON h.phase_id = p.id
       JOIN estates e ON p.estate_id = e.id
       WHERE e.company_id = $1`,
      [req.user.company_id]
    );

    res.json({ 
      bills: result.rows,
      pagination: {
        page: parseInt(page),
        limit: parseInt(limit),
        total: parseInt(countResult.rows[0].count),
        totalPages: Math.ceil(countResult.rows[0].count / limit)
      }
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get bills for a specific house
router.get('/house/:houseId', authenticate, async (req, res) => {
  try {
    const result = await db.query(
      `SELECT b.* FROM bills b
       JOIN houses h ON b.house_id = h.id
       WHERE h.id = $1
       ORDER BY b.created_at DESC`,
      [req.params.houseId]
    );
    res.json({ bills: result.rows });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Create single bill
router.post('/', authenticate, authorize('super_admin', 'admin', 'clerk'), async (req, res) => {
  try {
    const { house_id, amount, bill_period, due_date, description } = req.body;
    const id = uuidv4();

    const result = await db.query(
      `INSERT INTO bills (id, house_id, amount, balance, bill_period, due_date, description, created_by) 
       VALUES ($1, $2, $3, $3, $4, $5, $6, $7) RETURNING *`,
      [id, house_id, amount, bill_period, due_date, description, req.user.id]
    );

    res.status(201).json({ bill: result.rows[0] });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Bulk create bills for estate/phase
router.post('/bulk', authenticate, authorize('super_admin', 'admin'), async (req, res) => {
  try {
    const { estate_id, phase_id, amount, bill_period, due_date, description } = req.body;

    let housesQuery = `
      SELECT h.id FROM houses h
      JOIN phases p ON h.phase_id = p.id
      JOIN estates e ON p.estate_id = e.id
      WHERE e.company_id = $1 AND h.status = 'active'
    `;
    const params = [req.user.company_id];

    if (estate_id) {
      housesQuery += ` AND e.id = $2`;
      params.push(estate_id);
    }
    if (phase_id) {
      housesQuery += ` AND p.id = $${params.length + 1}`;
      params.push(phase_id);
    }

    const housesResult = await db.query(housesQuery, params);
    const billsCreated = [];

    for (const house of housesResult.rows) {
      const id = uuidv4();
      const result = await db.query(
        `INSERT INTO bills (id, house_id, amount, balance, bill_period, due_date, description, created_by) 
         VALUES ($1, $2, $3, $3, $4, $5, $6, $7) RETURNING *`,
        [id, house.id, amount, bill_period, due_date, description, req.user.id]
      );
      billsCreated.push(result.rows[0]);
    }

    res.status(201).json({ 
      message: `${billsCreated.length} bills created successfully`,
      bills: billsCreated 
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get overdue bills summary
router.get('/summary/overdue', authenticate, async (req, res) => {
  try {
    const result = await db.query(
      `SELECT 
        COUNT(*) as total_overdue,
        SUM(balance) as total_amount,
        COUNT(DISTINCT house_id) as affected_houses
       FROM bills b
       JOIN houses h ON b.house_id = h.id
       JOIN phases p ON h.phase_id = p.id
       JOIN estates e ON p.estate_id = e.id
       WHERE e.company_id = $1 AND b.due_date < CURRENT_DATE AND b.status != 'paid'`,
      [req.user.company_id]
    );

    res.json({ summary: result.rows[0] });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
