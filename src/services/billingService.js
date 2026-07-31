const cron = require('node-cron');
const db = require('../config/database');
const smsService = require('./smsService');

class BillingService {
  constructor() {
    this.jobs = [];
  }

  start() {
    console.log('Starting billing cron jobs...');

    // Daily: Check for overdue bills and update status
    this.jobs.push(cron.schedule('0 6 * * *', async () => {
      console.log('[CRON] Checking overdue bills...');
      await this.updateOverdueStatus();
    }));

    // Daily: Send overdue reminders (3-day, 7-day, 14-day)
    this.jobs.push(cron.schedule('0 9 * * *', async () => {
      console.log('[CRON] Sending overdue reminders...');
      await this.sendOverdueReminders();
    }));

    // Monthly: Auto-generate bills (1st of every month at 6 AM)
    this.jobs.push(cron.schedule('0 6 1 * *', async () => {
      console.log('[CRON] Generating monthly bills...');
      await this.generateMonthlyBills();
    }));

    console.log('[CRON] All billing jobs scheduled');
  }

  async updateOverdueStatus() {
    const result = await db.query(
      `UPDATE bills SET status = 'overdue' 
       WHERE due_date < CURRENT_DATE AND status = 'pending'
       RETURNING id`
    );
    console.log(`[CRON] ${result.rowCount} bills marked as overdue`);
  }

  async sendOverdueReminders() {
    const overdueBills = await db.query(
      `SELECT b.id, b.balance, b.due_date, h.account_number,
              r.full_name, r.phone_number, CURRENT_DATE - b.due_date as days_overdue
       FROM bills b
       JOIN houses h ON b.house_id = h.id
       JOIN phases p ON h.phase_id = p.id
       JOIN estates e ON p.estate_id = e.id
       LEFT JOIN residents r ON r.house_id = h.id AND r.is_primary = true
       WHERE b.status = 'overdue' 
         AND b.balance > 0
         AND (CURRENT_DATE - b.due_date) IN (3, 7, 14, 30)`
    );

    for (const bill of overdueBills.rows) {
      if (bill.phone_number) {
        await smsService.sendOverdueReminder(
          bill.phone_number,
          bill.full_name || 'Resident',
          bill.account_number,
          bill.balance,
          bill.days_overdue,
          bill.house_id
        );
      }
    }

    console.log(`[CRON] Sent ${overdueBills.rowCount} overdue reminders`);
  }

  async generateMonthlyBills() {
    const period = new Date().toLocaleString('en-US', { month: 'long', year: 'numeric' });
    const dueDate = new Date();
    dueDate.setDate(dueDate.getDate() + 15);

    // Get default billing amount from settings
    const settingsResult = await db.query(
      "SELECT setting_value FROM settings WHERE setting_key = 'default_bill_amount' LIMIT 1"
    );
    const defaultAmount = settingsResult.rows[0]?.setting_value || 400;

    // Get all active houses
    const housesResult = await db.query(
      `SELECT h.id FROM houses h
       JOIN phases p ON h.phase_id = p.id
       JOIN estates e ON p.estate_id = e.id
       WHERE h.status = 'active'`
    );

    let created = 0;
    for (const house of housesResult.rows) {
      try {
        await db.query(
          `INSERT INTO bills (id, house_id, amount, balance, bill_period, due_date, description)
           VALUES (gen_random_uuid(), $1, $2, $2, $3, $4, $5)`,
          [house.id, defaultAmount, period, dueDate.toISOString().split('T')[0], `Monthly garbage collection fee for ${period}`]
        );
        created++;
      } catch (err) {
        console.error(`Failed to create bill for house ${house.id}:`, err.message);
      }
    }

    console.log(`[CRON] Generated ${created} bills for ${period}`);
  }

  stop() {
    this.jobs.forEach(job => job.stop());
    console.log('[CRON] All billing jobs stopped');
  }
}

module.exports = new BillingService();
