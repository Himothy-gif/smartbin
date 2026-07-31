require('dotenv').config();

module.exports = {
  name: process.env.COMPANY_NAME || 'Smart Bin Ltd',
  paybill: process.env.COMPANY_PAYBILL || '4060083',
  phone: process.env.COMPANY_PHONE || '0721482110',
  email: process.env.COMPANY_EMAIL || 'info@smartbin.co.ke',
  address: process.env.COMPANY_ADDRESS || 'Nairobi, Kenya',

  getPaymentInstructions(accountNumber, amount) {
    return `Pay via M-PESA Paybill ${this.paybill} Account: ${accountNumber}. Amount: KES ${amount}`;
  },

  getBillSms(name, accountNumber, amount, period, dueDate) {
    return `Dear ${name} (${accountNumber}), You have an outstanding bill of KES ${amount}.00 for ${period}. Kindly purpose to pay by ${dueDate}. Pay via MPESA Paybill ${this.paybill} Acc: ${accountNumber}. Powered by ${this.name}. Call ${this.phone}`;
  },

  getPaymentConfirmationSms(name, accountNumber, amount, mpesaCode, balance) {
    return `Thank you ${name}. KES ${amount}.00 received for account ${accountNumber}. M-PESA Code: ${mpesaCode}. New balance: KES ${balance}.00. Powered by ${this.name}`;
  },

  getOverdueReminderSms(name, accountNumber, amount, daysOverdue) {
    return `Dear ${name} (${accountNumber}), your account is ${daysOverdue} days overdue with KES ${amount}.00 outstanding. Please pay via MPESA Paybill ${this.paybill} Acc: ${accountNumber} to avoid service suspension. ${this.name}`;
  }
};
