const AfricasTalking = require('africastalking');
const db = require('../config/database');
const company = require('../config/company');

class SMSService {
  constructor() {
    this.client = null;
    this.initialized = false;

    if (process.env.AFRICASTALKING_API_KEY && process.env.AFRICASTALKING_USERNAME) {
      this.client = AfricasTalking({
        apiKey: process.env.AFRICASTALKING_API_KEY,
        username: process.env.AFRICASTALKING_USERNAME,
      });
      this.initialized = true;
    }
  }

  async sendSMS(phoneNumber, message, smsType = 'general', houseId = null) {
    try {
      // Log SMS attempt
      const logResult = await db.query(
        `INSERT INTO sms_logs (id, house_id, phone_number, message, sms_type, status)
         VALUES (gen_random_uuid(), $1, $2, $3, $4, 'pending') RETURNING id`,
        [houseId, phoneNumber, message, smsType]
      );
      const logId = logResult.rows[0].id;

      if (!this.initialized) {
        console.log(`[SMS MOCK] To: ${phoneNumber}`);
        console.log(`[SMS MOCK] Message: ${message}`);
        await db.query(`UPDATE sms_logs SET status = 'sent', sent_at = CURRENT_TIMESTAMP WHERE id = $1`, [logId]);
        return { success: true, mock: true };
      }

      const sms = this.client.SMS;
      const response = await sms.send({
        to: phoneNumber,
        message: message,
        from: process.env.AFRICASTALKING_SENDER_ID || company.name,
      });

      await db.query(
        `UPDATE sms_logs SET status = 'sent', sent_at = CURRENT_TIMESTAMP, provider_response = $1 WHERE id = $2`,
        [JSON.stringify(response), logId]
      );

      return { success: true, response };
    } catch (error) {
      console.error('SMS send failed:', error);
      return { success: false, error: error.message };
    }
  }

  async sendBillIssue(phoneNumber, name, accountNumber, amount, period, dueDate, houseId) {
    const message = company.getBillSms(name, accountNumber, amount, period, dueDate);
    return this.sendSMS(phoneNumber, message, 'bill_issue', houseId);
  }

  async sendPaymentConfirmation(phoneNumber, name, accountNumber, amount, mpesaCode, balance, houseId) {
    const message = company.getPaymentConfirmationSms(name, accountNumber, amount, mpesaCode, balance);
    return this.sendSMS(phoneNumber, message, 'payment_confirmation', houseId);
  }

  async sendOverdueReminder(phoneNumber, name, accountNumber, amount, daysOverdue, houseId) {
    const message = company.getOverdueReminderSms(name, accountNumber, amount, daysOverdue);
    return this.sendSMS(phoneNumber, message, 'overdue_reminder', houseId);
  }

  async getSMSHistory(houseId = null, limit = 50) {
    let query = 'SELECT * FROM sms_logs';
    const params = [];

    if (houseId) {
      query += ' WHERE house_id = $1';
      params.push(houseId);
    }

    query += ' ORDER BY created_at DESC LIMIT $' + (params.length + 1);
    params.push(limit);

    const result = await db.query(query, params);
    return result.rows;
  }
}

module.exports = new SMSService();
