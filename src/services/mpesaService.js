const axios = require('axios');
const db = require('../config/database');

class MpesaService {
  constructor() {
    this.baseUrl = process.env.MPESA_ENVIRONMENT === 'production' 
      ? 'https://api.safaricom.co.ke'
      : 'https://sandbox.safaricom.co.ke';
  }

  async getAccessToken() {
    const auth = Buffer.from(
      `${process.env.MPESA_CONSUMER_KEY}:${process.env.MPESA_CONSUMER_SECRET}`
    ).toString('base64');

    const response = await axios.get(
      `${this.baseUrl}/oauth/v1/generate?grant_type=client_credentials`,
      { headers: { Authorization: `Basic ${auth}` } }
    );

    return response.data.access_token;
  }

  async registerUrls() {
    try {
      const token = await this.getAccessToken();

      const response = await axios.post(
        `${this.baseUrl}/mpesa/c2b/v1/registerurl`,
        {
          ShortCode: process.env.MPESA_SHORTCODE,
          ResponseType: 'Completed',
          ConfirmationURL: process.env.MPESA_CONFIRMATION_URL,
          ValidationURL: process.env.MPESA_VALIDATION_URL,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      return response.data;
    } catch (error) {
      console.error('M-PESA URL registration failed:', error.response?.data || error.message);
      throw error;
    }
  }

  async simulatePayment(phoneNumber, amount, accountNumber) {
    try {
      const token = await this.getAccessToken();

      const response = await axios.post(
        `${this.baseUrl}/mpesa/c2b/v1/simulate`,
        {
          ShortCode: process.env.MPESA_SHORTCODE,
          CommandID: 'CustomerPayBillOnline',
          Amount: amount,
          Msisdn: phoneNumber,
          BillRefNumber: accountNumber,
        },
        { headers: { Authorization: `Bearer ${token}` } }
      );

      return response.data;
    } catch (error) {
      console.error('M-PESA simulation failed:', error.response?.data || error.message);
      throw error;
    }
  }
}

module.exports = new MpesaService();
