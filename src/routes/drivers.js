const express = require('express');
const { v4: uuidv4 } = require('uuid');
const db = require('../config/database');
const { authenticate, authorize } = require('../middleware/auth');
const router = express.Router();

// Get all drivers
router.get('/', authenticate, async (req, res) => {
  try {
    const result = await db.query(
      'SELECT * FROM drivers WHERE company_id = $1 ORDER BY full_name',
      [req.user.company_id]
    );
    res.json({ drivers: result.rows });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Create driver
router.post('/', authenticate, authorize('super_admin', 'admin'), async (req, res) => {
  try {
    const { full_name, phone_number, license_number, vehicle_plate } = req.body;
    const id = uuidv4();

    const result = await db.query(
      `INSERT INTO drivers (id, company_id, full_name, phone_number, license_number, vehicle_plate) 
       VALUES ($1, $2, $3, $4, $5, $6) RETURNING *`,
      [id, req.user.company_id, full_name, phone_number, license_number, vehicle_plate]
    );

    res.status(201).json({ driver: result.rows[0] });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Update driver
router.put('/:id', authenticate, authorize('super_admin', 'admin'), async (req, res) => {
  try {
    const { full_name, phone_number, license_number, vehicle_plate, is_active } = req.body;
    const result = await db.query(
      `UPDATE drivers SET full_name = $1, phone_number = $2, license_number = $3, 
       vehicle_plate = $4, is_active = $5 WHERE id = $6 AND company_id = $7 RETURNING *`,
      [full_name, phone_number, license_number, vehicle_plate, is_active, req.params.id, req.user.company_id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Driver not found' });
    }

    res.json({ driver: result.rows[0] });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
