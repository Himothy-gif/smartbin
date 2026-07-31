const express = require('express');
const { v4: uuidv4 } = require('uuid');
const db = require('../config/database');
const { authenticate, authorize } = require('../middleware/auth');
const router = express.Router();

// Get all estates
router.get('/', authenticate, async (req, res) => {
  try {
    const result = await db.query(
      `SELECT e.*, c.name as company_name 
       FROM estates e 
       JOIN companies c ON e.company_id = c.id 
       WHERE e.company_id = $1 
       ORDER BY e.created_at DESC`,
      [req.user.company_id]
    );
    res.json({ estates: result.rows });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Get single estate with phases
router.get('/:id', authenticate, async (req, res) => {
  try {
    const estateResult = await db.query(
      'SELECT * FROM estates WHERE id = $1 AND company_id = $2',
      [req.params.id, req.user.company_id]
    );

    if (estateResult.rows.length === 0) {
      return res.status(404).json({ error: 'Estate not found' });
    }

    const phasesResult = await db.query(
      'SELECT * FROM phases WHERE estate_id = $1 ORDER BY phase_number',
      [req.params.id]
    );

    res.json({ 
      estate: estateResult.rows[0],
      phases: phasesResult.rows 
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Create estate
router.post('/', authenticate, authorize('super_admin', 'admin'), async (req, res) => {
  try {
    const { name, location, total_phases = 1 } = req.body;
    const id = uuidv4();

    const result = await db.query(
      `INSERT INTO estates (id, company_id, name, location, total_phases) 
       VALUES ($1, $2, $3, $4, $5) RETURNING *`,
      [id, req.user.company_id, name, location, total_phases]
    );

    // Auto-create phases
    for (let i = 1; i <= total_phases; i++) {
      await db.query(
        `INSERT INTO phases (id, estate_id, phase_number, phase_name) 
         VALUES ($1, $2, $3, $4)`,
        [uuidv4(), id, i, `Phase ${i}`]
      );
    }

    res.status(201).json({ estate: result.rows[0], message: 'Estate created with phases' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Update estate
router.put('/:id', authenticate, authorize('super_admin', 'admin'), async (req, res) => {
  try {
    const { name, location, status } = req.body;
    const result = await db.query(
      `UPDATE estates SET name = $1, location = $2, status = $3 
       WHERE id = $4 AND company_id = $5 RETURNING *`,
      [name, location, status, req.params.id, req.user.company_id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Estate not found' });
    }

    res.json({ estate: result.rows[0] });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Delete estate
router.delete('/:id', authenticate, authorize('super_admin'), async (req, res) => {
  try {
    const result = await db.query(
      'DELETE FROM estates WHERE id = $1 AND company_id = $2 RETURNING *',
      [req.params.id, req.user.company_id]
    );

    if (result.rows.length === 0) {
      return res.status(404).json({ error: 'Estate not found' });
    }

    res.json({ message: 'Estate deleted successfully' });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
