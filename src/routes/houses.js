const express = require('express');
const { v4: uuidv4 } = require('uuid');
const db = require('../config/database');
const { authenticate, authorize } = require('../middleware/auth');
const router = express.Router();

// Get houses by phase
router.get('/phase/:phaseId', authenticate, async (req, res) => {
  try {
    const result = await db.query(
      `SELECT h.*, p.phase_number, e.name as estate_name
       FROM houses h
       JOIN phases p ON h.phase_id = p.id
       JOIN estates e ON p.estate_id = e.id
       WHERE h.phase_id = $1 AND e.company_id = $2
       ORDER BY h.house_number::int`,
      [req.params.phaseId, req.user.company_id]
    );
    res.json({ houses: result.rows });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get house by account number
router.get('/account/:accountNumber', authenticate, async (req, res) => {
  try {
    const result = await db.query(
      `SELECT h.*, p.phase_number, e.name as estate_name,
        r.full_name as resident_name, r.phone_number as resident_phone
       FROM houses h
       JOIN phases p ON h.phase_id = p.id
       JOIN estates e ON p.estate_id = e.id
       LEFT JOIN residents r ON r.house_id = h.id AND r.is_primary = true
       WHERE h.account_number = $1 AND e.company_id = $2`,
      [req.params.accountNumber, req.user.company_id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'House not found' });
    }

    res.json({ house: result.rows[0] });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Create house
router.post('/', authenticate, authorize('super_admin', 'admin', 'clerk'), async (req, res) => {
  try {
    const { phase_id, house_number, gps_coordinates, bin_count = 1 } = req.body;
    const id = uuidv4();

    const result = await db.query(
      `INSERT INTO houses (id, phase_id, house_number, gps_coordinates, bin_count) 
       VALUES ($1, $2, $3, $4, $5) RETURNING *`,
      [id, phase_id, house_number, gps_coordinates, bin_count]
    );

    res.status(201).json({ house: result.rows[0] });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Update house
router.put('/:id', authenticate, authorize('super_admin', 'admin', 'clerk'), async (req, res) => {
  try {
    const { house_number, gps_coordinates, bin_count, status } = req.body;
    const result = await db.query(
      `UPDATE houses SET house_number = $1, gps_coordinates = $2, 
       bin_count = $3, status = $4 WHERE id = $5 RETURNING *`,
      [house_number, gps_coordinates, bin_count, status, req.params.id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'House not found' });
    }

    res.json({ house: result.rows[0] });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
