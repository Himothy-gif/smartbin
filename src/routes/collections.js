const express = require('express');
const { v4: uuidv4 } = require('uuid');
const db = require('../config/database');
const { authenticate, authorize } = require('../middleware/auth');
const router = express.Router();

// Get collections by date
router.get('/', authenticate, async (req, res) => {
  try {
    const { date, estate_id, driver_id, status, page = 1, limit = 50 } = req.query;
    const offset = (page - 1) * limit;

    let query = `
      SELECT c.*, h.account_number, h.house_number, p.phase_number,
             e.name as estate_name, d.full_name as driver_name
      FROM collections c
      JOIN houses h ON c.house_id = h.id
      JOIN phases p ON h.phase_id = p.id
      JOIN estates e ON p.estate_id = e.id
      LEFT JOIN drivers d ON c.driver_id = d.id
      WHERE e.company_id = $1
    `;
    const params = [req.user.company_id];
    let paramIndex = 2;

    if (date) {
      query += ` AND c.scheduled_date = $${paramIndex}`;
      params.push(date);
      paramIndex++;
    }
    if (estate_id) {
      query += ` AND e.id = $${paramIndex}`;
      params.push(estate_id);
      paramIndex++;
    }
    if (driver_id) {
      query += ` AND c.driver_id = $${paramIndex}`;
      params.push(driver_id);
      paramIndex++;
    }
    if (status) {
      query += ` AND c.status = $${paramIndex}`;
      params.push(status);
      paramIndex++;
    }

    query += ` ORDER BY c.scheduled_date DESC LIMIT $${paramIndex} OFFSET $${paramIndex + 1}`;
    params.push(limit, offset);

    const result = await db.query(query, params);
    res.json({ collections: result.rows });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Mark collection complete
router.put('/:id/complete', authenticate, authorize('super_admin', 'admin', 'clerk'), async (req, res) => {
  try {
    const { weight_kg, waste_type, notes } = req.body;
    const result = await db.query(
      `UPDATE collections SET status = 'completed', completed_at = CURRENT_TIMESTAMP,
       weight_kg = $1, waste_type = $2, notes = $3 WHERE id = $4 RETURNING *`,
      [weight_kg, waste_type, notes, req.params.id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Collection not found' });
    }

    res.json({ collection: result.rows[0] });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Create collection schedule
router.post('/schedule', authenticate, authorize('super_admin', 'admin'), async (req, res) => {
  try {
    const { house_ids, scheduled_date, driver_id } = req.body;
    const collections = [];

    for (const house_id of house_ids) {
      const id = uuidv4();
      const result = await db.query(
        `INSERT INTO collections (id, house_id, driver_id, scheduled_date) 
         VALUES ($1, $2, $3, $4) RETURNING *`,
        [id, house_id, driver_id, scheduled_date]
      );
      collections.push(result.rows[0]);
    }

    res.status(201).json({ 
      message: `${collections.length} collections scheduled`,
      collections 
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
