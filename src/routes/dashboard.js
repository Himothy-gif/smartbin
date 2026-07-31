const express = require('express');
const db = require('../config/database');
const { authenticate } = require('../middleware/auth');
const router = express.Router();

// Main dashboard stats
router.get('/stats', authenticate, async (req, res) => {
  try {
    const companyId = req.user.company_id;

    // Today's collections
    const todayCollections = await db.query(
      `SELECT COUNT(*) as total, 
        COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed
       FROM collections c
       JOIN houses h ON c.house_id = h.id
       JOIN phases p ON h.phase_id = p.id
       JOIN estates e ON p.estate_id = e.id
       WHERE e.company_id = $1 AND c.scheduled_date = CURRENT_DATE`,
      [companyId]
    );

    // Today's revenue
    const todayRevenue = await db.query(
      `SELECT COALESCE(SUM(amount), 0) as total
       FROM payments p
       JOIN houses h ON p.house_id = h.id
       JOIN phases ph ON h.phase_id = ph.id
       JOIN estates e ON ph.estate_id = e.id
       WHERE e.company_id = $1 AND DATE(p.paid_at) = CURRENT_DATE`,
      [companyId]
    );

    // Monthly revenue
    const monthlyRevenue = await db.query(
      `SELECT COALESCE(SUM(amount), 0) as total
       FROM payments p
       JOIN houses h ON p.house_id = h.id
       JOIN phases ph ON h.phase_id = ph.id
       JOIN estates e ON ph.estate_id = e.id
       WHERE e.company_id = $1 AND DATE_TRUNC('month', p.paid_at) = DATE_TRUNC('month', CURRENT_DATE)`,
      [companyId]
    );

    // Outstanding balance
    const outstanding = await db.query(
      `SELECT COALESCE(SUM(balance), 0) as total, COUNT(*) as count
       FROM bills b
       JOIN houses h ON b.house_id = h.id
       JOIN phases p ON h.phase_id = p.id
       JOIN estates e ON p.estate_id = e.id
       WHERE e.company_id = $1 AND b.status != 'paid'`,
      [companyId]
    );

    // Overdue count
    const overdue = await db.query(
      `SELECT COUNT(*) as count, COALESCE(SUM(balance), 0) as amount
       FROM bills b
       JOIN houses h ON b.house_id = h.id
       JOIN phases p ON h.phase_id = p.id
       JOIN estates e ON p.estate_id = e.id
       WHERE e.company_id = $1 AND b.due_date < CURRENT_DATE AND b.status != 'paid'`,
      [companyId]
    );

    // Estate counts
    const estates = await db.query(
      `SELECT COUNT(*) as total FROM estates WHERE company_id = $1 AND status = 'active'`,
      [companyId]
    );

    const houses = await db.query(
      `SELECT COUNT(*) as total FROM houses h
       JOIN phases p ON h.phase_id = p.id
       JOIN estates e ON p.estate_id = e.id
       WHERE e.company_id = $1 AND h.status = 'active'`,
      [companyId]
    );

    res.json({
      today: {
        collections: parseInt(todayCollections.rows[0].total),
        collectionsCompleted: parseInt(todayCollections.rows[0].completed),
        revenue: parseFloat(todayRevenue.rows[0].total)
      },
      monthly: {
        revenue: parseFloat(monthlyRevenue.rows[0].total)
      },
      outstanding: {
        amount: parseFloat(outstanding.rows[0].total),
        count: parseInt(outstanding.rows[0].count)
      },
      overdue: {
        count: parseInt(overdue.rows[0].count),
        amount: parseFloat(overdue.rows[0].amount)
      },
      estates: parseInt(estates.rows[0].total),
      houses: parseInt(houses.rows[0].total)
    });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Revenue by estate
router.get('/revenue-by-estate', authenticate, async (req, res) => {
  try {
    const result = await db.query(
      `SELECT e.name, COALESCE(SUM(p.amount), 0) as revenue, COUNT(DISTINCT p.id) as transactions
       FROM estates e
       LEFT JOIN phases ph ON ph.estate_id = e.id
       LEFT JOIN houses h ON h.phase_id = ph.id
       LEFT JOIN payments p ON p.house_id = h.id 
         AND DATE_TRUNC('month', p.paid_at) = DATE_TRUNC('month', CURRENT_DATE)
       WHERE e.company_id = $1 AND e.status = 'active'
       GROUP BY e.id, e.name
       ORDER BY revenue DESC`,
      [req.user.company_id]
    );
    res.json({ estates: result.rows });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Collection performance
router.get('/collection-performance', authenticate, async (req, res) => {
  try {
    const { days = 30 } = req.query;
    const result = await db.query(
      `SELECT 
        DATE(c.scheduled_date) as date,
        COUNT(*) as scheduled,
        COUNT(CASE WHEN c.status = 'completed' THEN 1 END) as completed,
        COUNT(CASE WHEN c.status = 'missed' THEN 1 END) as missed
       FROM collections c
       JOIN houses h ON c.house_id = h.id
       JOIN phases p ON h.phase_id = p.id
       JOIN estates e ON p.estate_id = e.id
       WHERE e.company_id = $1 
         AND c.scheduled_date >= CURRENT_DATE - INTERVAL '${days} days'
       GROUP BY DATE(c.scheduled_date)
       ORDER BY date DESC`,
      [req.user.company_id]
    );
    res.json({ performance: result.rows });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

// Overdue aging report
router.get('/overdue-aging', authenticate, async (req, res) => {
  try {
    const result = await db.query(
      `SELECT 
        CASE 
          WHEN CURRENT_DATE - b.due_date <= 7 THEN '1-7 days'
          WHEN CURRENT_DATE - b.due_date <= 14 THEN '8-14 days'
          WHEN CURRENT_DATE - b.due_date <= 30 THEN '15-30 days'
          ELSE '30+ days'
        END as aging_bucket,
        COUNT(*) as count,
        COALESCE(SUM(b.balance), 0) as amount
       FROM bills b
       JOIN houses h ON b.house_id = h.id
       JOIN phases p ON h.phase_id = p.id
       JOIN estates e ON p.estate_id = e.id
       WHERE e.company_id = $1 AND b.due_date < CURRENT_DATE AND b.status != 'paid'
       GROUP BY aging_bucket
       ORDER BY MIN(CURRENT_DATE - b.due_date)`,
      [req.user.company_id]
    );
    res.json({ aging: result.rows });
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

module.exports = router;
