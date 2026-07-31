const express = require('express');
const { v4: uuidv4 } = require('uuid');
const db = require('../config/database');
const { authenticate, authorize } = require('../middleware/auth');
const router = express.Router();

// Get residents by house
router.get('/house/:houseId', authenticate, async (req, res) => {
  try {
    const result = await db.query(
      'SELECT * FROM residents WHERE house_id = $1 ORDER BY is_primary DESC, created_at',
      [req.params.houseId]
    );
    res.json({ residents: result.rows });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Create resident
router.post('/', authenticate, authorize('super_admin', 'admin', 'clerk'), async (req, res) => {
  try {
    const { house_id, full_name, phone_number, email, id_number, is_primary = true } = req.body;
    const id = uuidv4();

    const result = await db.query(
      `INSERT INTO residents (id, house_id, full_name, phone_number, email, id_number, is_primary) 
       VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING *`,
      [id, house_id, full_name, phone_number, email, id_number, is_primary]
    );

    res.status(201).json({ resident: result.rows[0] });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Update resident
router.put('/:id', authenticate, authorize('super_admin', 'admin', 'clerk'), async (req, res) => {
  try {
    const { full_name, phone_number, email, id_number, is_primary, is_active } = req.body;
    const result = await db.query(
      `UPDATE residents SET full_name = $1, phone_number = $2, email = $3, 
       id_number = $4, is_primary = $5, is_active = $6 WHERE id = $7 RETURNING *`,
      [full_name, phone_number, email, id_number, is_primary, is_active, req.params.id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Resident not found' });
    }

    res.json({ resident: result.rows[0] });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
