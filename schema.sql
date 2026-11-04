-- Smart Agriculture Management System - PostgreSQL Database Schema
-- Compatible with PostgreSQL 13+, Neon, Supabase, Vercel Postgres, AWS RDS

-- 1. Farmers
CREATE TABLE IF NOT EXISTS farmer (
    farmer_id INTEGER PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    phone VARCHAR(15),
    address VARCHAR(200)
);

-- 2. Fields
CREATE TABLE IF NOT EXISTS field (
    field_id INTEGER PRIMARY KEY,
    farmer_id INTEGER NOT NULL REFERENCES farmer(farmer_id) ON DELETE CASCADE,
    field_name VARCHAR(100) NOT NULL,
    area NUMERIC(10,2),
    location VARCHAR(150)
);

-- 3. Crops
CREATE TABLE IF NOT EXISTS crop (
    crop_id INTEGER PRIMARY KEY,
    crop_name VARCHAR(100) NOT NULL,
    crop_type VARCHAR(50),
    min_ph NUMERIC(4,2),
    max_ph NUMERIC(4,2),
    water_requirement VARCHAR(50),
    min_nitrogen NUMERIC(10,2),
    min_phosphorus NUMERIC(10,2),
    min_potassium NUMERIC(10,2)
);

-- 4. Crop Seasons
CREATE TABLE IF NOT EXISTS crop_season (
    crop_season_id INTEGER PRIMARY KEY,
    crop_id INTEGER NOT NULL REFERENCES crop(crop_id) ON DELETE CASCADE,
    season VARCHAR(50) NOT NULL
);

-- 5. Field Crops (Harvests & Plantings)
CREATE TABLE IF NOT EXISTS field_crop (
    field_crop_id INTEGER PRIMARY KEY,
    field_id INTEGER NOT NULL REFERENCES field(field_id) ON DELETE CASCADE,
    crop_id INTEGER NOT NULL REFERENCES crop(crop_id) ON DELETE CASCADE,
    season VARCHAR(50),
    sowing_date DATE,
    harvest_date DATE,
    yield NUMERIC(10,2)
);

-- 6. Soil Tests
CREATE TABLE IF NOT EXISTS soil (
    soil_id INTEGER PRIMARY KEY,
    field_id INTEGER NOT NULL REFERENCES field(field_id) ON DELETE CASCADE,
    test_date DATE NOT NULL,
    soil_type VARCHAR(50),
    ph NUMERIC(4,2),
    nitrogen NUMERIC(10,2),
    phosphorus NUMERIC(10,2),
    potassium NUMERIC(10,2),
    moisture NUMERIC(5,2)
);

-- 7. Weather Records
CREATE TABLE IF NOT EXISTS weather (
    weather_id INTEGER PRIMARY KEY,
    field_id INTEGER NOT NULL REFERENCES field(field_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    temperature NUMERIC(5,2),
    rainfall NUMERIC(6,2),
    humidity NUMERIC(5,2)
);

-- 8. Irrigation Logs
CREATE TABLE IF NOT EXISTS irrigation (
    irrigation_id INTEGER PRIMARY KEY,
    field_id INTEGER NOT NULL REFERENCES field(field_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    water_amount NUMERIC(10,2),
    method VARCHAR(50)
);

-- 9. Fertilizers
CREATE TABLE IF NOT EXISTS fertilizer (
    fertilizer_id INTEGER PRIMARY KEY,
    fertilizer_name VARCHAR(100) NOT NULL,
    type VARCHAR(50),
    nitrogen_content NUMERIC(5,2),
    phosphorus_content NUMERIC(5,2),
    potassium_content NUMERIC(5,2)
);

-- 10. Field Fertilizer Usage
CREATE TABLE IF NOT EXISTS field_fertilizer (
    field_fertilizer_id INTEGER PRIMARY KEY,
    field_id INTEGER NOT NULL REFERENCES field(field_id) ON DELETE CASCADE,
    fertilizer_id INTEGER NOT NULL REFERENCES fertilizer(fertilizer_id) ON DELETE CASCADE,
    date DATE NOT NULL,
    quantity NUMERIC(10,2)
);

-- 11. Recommendations
CREATE TABLE IF NOT EXISTS recommendation (
    recommendation_id INTEGER PRIMARY KEY,
    field_id INTEGER NOT NULL REFERENCES field(field_id) ON DELETE CASCADE,
    crop_id INTEGER REFERENCES crop(crop_id) ON DELETE SET NULL,
    fertilizer_id INTEGER REFERENCES fertilizer(fertilizer_id) ON DELETE SET NULL,
    recommendation_date DATE NOT NULL,
    irrigation_advice VARCHAR(255),
    reason VARCHAR(500)
);
