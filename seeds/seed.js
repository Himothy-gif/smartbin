const bcrypt = require('bcryptjs');
const { v4: uuidv4 } = require('uuid');
const db = require('../src/config/database');

async function seed() {
  console.log('Seeding database...');

  try {
    // 1. Create Company
    const companyId = uuidv4();
    await db.query(
      `INSERT INTO companies (id, name, paybill_number, contact_phone, contact_email, address)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [companyId, 'Smart Bin Ltd', '4060083', '0721482110', 'info@smartbin.co.ke', 'Nairobi, Kenya']
    );
    console.log('✅ Company created: Smart Bin Ltd');

    // 2. Create Admin User
    const adminId = uuidv4();
    const hashedPassword = await bcrypt.hash('admin123', 10);
    await db.query(
      `INSERT INTO users (id, company_id, full_name, email, password_hash, role)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [adminId, companyId, 'System Administrator', 'admin@smartbin.co.ke', hashedPassword, 'super_admin']
    );
    console.log('✅ Admin user created: admin@smartbin.co.ke / admin123');

    // 3. Create Estate: Gakindu Court
    const estateId = uuidv4();
    await db.query(
      `INSERT INTO estates (id, company_id, name, location, total_phases)
       VALUES ($1, $2, $3, $4, $5)`,
      [estateId, companyId, 'GAKINDU COURT', 'Nairobi, Kenya', 4]
    );
    console.log('✅ Estate created: GAKINDU COURT');

    // 4. Create Phases
    const phases = [];
    for (let i = 1; i <= 4; i++) {
      const phaseId = uuidv4();
      await db.query(
        `INSERT INTO phases (id, estate_id, phase_number, phase_name)
         VALUES ($1, $2, $3, $4)`,
        [phaseId, estateId, i, `Phase ${i}`]
      );
      phases.push({ id: phaseId, number: i });
    }
    console.log('✅ 4 phases created');

    // 5. Create Houses (sample: 10 houses per phase)
    const houses = [];
    for (const phase of phases) {
      for (let h = 340; h <= 360; h++) {
        const houseId = uuidv4();
        await db.query(
          `INSERT INTO houses (id, phase_id, house_number, gps_coordinates, bin_count)
           VALUES ($1, $2, $3, $4, $5)`,
          [houseId, phase.id, h.toString(), '-1.2921,36.8219', 1]
        );
        houses.push({ id: houseId, number: h, phase: phase.number, phaseId: phase.id });
      }
    }
    console.log(`✅ ${houses.length} houses created`);

    // 6. Create Residents (sample)
    const sampleResidents = [
      { house: 348, phase: 4, name: 'Faith E.', phone: '254712345678' },
      { house: 350, phase: 4, name: 'John Kamau', phone: '254723456789' },
      { house: 345, phase: 4, name: 'Mary Wanjiku', phone: '254734567890' },
      { house: 340, phase: 1, name: 'Peter Ochieng', phone: '254745678901' },
      { house: 355, phase: 2, name: 'Grace Atieno', phone: '254756789012' },
    ];

    for (const resident of sampleResidents) {
      const house = houses.find(h => h.number === resident.house && h.phase === resident.phase);
      if (house) {
        await db.query(
          `INSERT INTO residents (id, house_id, full_name, phone_number, is_primary)
           VALUES ($1, $2, $3, $4, $5)`,
          [uuidv4(), house.id, resident.name, resident.phone, true]
        );
      }
    }
    console.log(`✅ ${sampleResidents.length} residents created`);

    // 7. Create Sample Bills
    const faithHouse = houses.find(h => h.number === 348 && h.phase === 4);
    if (faithHouse) {
      const billId = uuidv4();
      await db.query(
        `INSERT INTO bills (id, house_id, amount, balance, bill_period, due_date, description, created_by)
         VALUES ($1, $2, $3, $3, $4, $5, $6, $7)`,
        [billId, faithHouse.id, 400.00, 'Dec 2024', '2024-12-15', 'Monthly garbage collection fee - Dec 2024', adminId]
      );
      console.log('✅ Sample bill created for Faith E. (348/4) - KES 400');
    }

    // 8. Create Sample Payment
    if (faithHouse) {
      await db.query(
        `INSERT INTO payments (id, house_id, amount, mpesa_code, mpesa_phone, payment_method, status)
         VALUES ($1, $2, $3, $4, $5, 'mpesa', 'completed')`,
        [uuidv4(), faithHouse.id, 400.00, 'ABC123XYZ', '254712345678']
      );
      console.log('✅ Sample payment created for Faith E. - KES 400');
    }

    // 9. Create Driver
    const driverId = uuidv4();
    await db.query(
      `INSERT INTO drivers (id, company_id, full_name, phone_number, license_number, vehicle_plate)
       VALUES ($1, $2, $3, $4, $5, $6)`,
      [driverId, companyId, 'James Mwangi', '254767890123', 'DL123456', 'KCA 123A']
    );
    console.log('✅ Sample driver created: James Mwangi');

    // 10. Create Settings
    await db.query(
      `INSERT INTO settings (id, company_id, setting_key, setting_value, description)
       VALUES ($1, $2, $3, $4, $5)`,
      [uuidv4(), companyId, 'default_bill_amount', '400', 'Default monthly garbage collection fee per household']
    );
    console.log('✅ Default settings created');

    console.log('\n🎉 Database seeded successfully!');
    console.log('\nLogin credentials:');
    console.log('  Email: admin@smartbin.co.ke');
    console.log('  Password: admin123');
    console.log('\nSample Account: 348/4 (Faith E.)');

  } catch (error) {
    console.error('Seed failed:', error);
  } finally {
    process.exit(0);
  }
}

seed();
