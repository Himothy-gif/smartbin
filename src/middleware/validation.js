const Joi = require('joi');

const validate = (schema) => {
  return (req, res, next) => {
    const { error } = schema.validate(req.body);
    if (error) {
      return res.status(400).json({ 
        error: 'Validation failed', 
        details: error.details.map(d => d.message) 
      });
    }
    next();
  };
};

const schemas = {
  login: Joi.object({
    email: Joi.string().email().required(),
    password: Joi.string().min(6).required(),
  }),

  createEstate: Joi.object({
    name: Joi.string().min(2).max(255).required(),
    location: Joi.string().max(500).optional(),
    total_phases: Joi.number().integer().min(1).default(1),
  }),

  createPhase: Joi.object({
    estate_id: Joi.string().uuid().required(),
    phase_number: Joi.number().integer().min(1).required(),
    phase_name: Joi.string().max(255).optional(),
  }),

  createHouse: Joi.object({
    phase_id: Joi.string().uuid().required(),
    house_number: Joi.string().max(50).required(),
    gps_coordinates: Joi.string().max(100).optional(),
    bin_count: Joi.number().integer().min(0).default(1),
  }),

  createResident: Joi.object({
    house_id: Joi.string().uuid().required(),
    full_name: Joi.string().min(2).max(255).required(),
    phone_number: Joi.string().pattern(/^254[0-9]{9}$/).required()
      .messages({ 'string.pattern.base': 'Phone must be in format 2547XXXXXXXX' }),
    email: Joi.string().email().optional(),
    id_number: Joi.string().max(50).optional(),
    is_primary: Joi.boolean().default(true),
  }),

  createBill: Joi.object({
    house_id: Joi.string().uuid().required(),
    amount: Joi.number().positive().required(),
    bill_period: Joi.string().max(50).required(),
    due_date: Joi.date().required(),
    description: Joi.string().max(500).optional(),
  }),

  mpesaValidation: Joi.object({
    TransactionType: Joi.string().required(),
    TransID: Joi.string().required(),
    TransTime: Joi.string().required(),
    TransAmount: Joi.string().required(),
    BusinessShortCode: Joi.string().required(),
    BillRefNumber: Joi.string().required(),
    InvoiceNumber: Joi.string().optional(),
    MSISDN: Joi.string().required(),
    FirstName: Joi.string().optional(),
    MiddleName: Joi.string().optional(),
    LastName: Joi.string().optional(),
    OrgAccountBalance: Joi.string().optional(),
  }),
};

module.exports = { validate, schemas };
