-- Valora Database Schema v2
-- Enhanced for multiple property types: Residential, Plot, Commercial, PG

-- ============================================================================
-- MAIN PROPERTIES TABLE (Enhanced)
-- ============================================================================

-- Add new columns to existing properties table
ALTER TABLE properties ADD COLUMN IF NOT EXISTS property_category TEXT;  -- residential, plot, commercial, pg
ALTER TABLE properties ADD COLUMN IF NOT EXISTS property_subtype TEXT;   -- flat, villa, office, warehouse, etc.

-- Residential specific
ALTER TABLE properties ADD COLUMN IF NOT EXISTS bhk TEXT;                -- 1BHK, 2BHK, etc.
ALTER TABLE properties ADD COLUMN IF NOT EXISTS configuration TEXT;      -- 2BHK+Study, Duplex, Penthouse

-- Plot/Land specific  
ALTER TABLE properties ADD COLUMN IF NOT EXISTS plot_area_sqft REAL;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS plot_dimensions TEXT;    -- 30x40, 60x40, etc.
ALTER TABLE properties ADD COLUMN IF NOT EXISTS plot_facing TEXT;        -- East, North, Corner
ALTER TABLE properties ADD COLUMN IF NOT EXISTS is_corner_plot BOOLEAN DEFAULT 0;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS approved_by TEXT;        -- BDA, BMRDA, BIAPPA, etc.

-- Commercial specific
ALTER TABLE properties ADD COLUMN IF NOT EXISTS commercial_type TEXT;    -- office, shop, showroom, warehouse, factory
ALTER TABLE properties ADD COLUMN IF NOT EXISTS seating_capacity INTEGER;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS cabins INTEGER;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS meeting_rooms INTEGER;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS pantry BOOLEAN DEFAULT 0;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS washrooms INTEGER;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS power_backup TEXT;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS suitable_for TEXT;       -- IT, Retail, Manufacturing, etc.

-- PG/Hostel specific
ALTER TABLE properties ADD COLUMN IF NOT EXISTS pg_type TEXT;            -- boys, girls, coed
ALTER TABLE properties ADD COLUMN IF NOT EXISTS room_type TEXT;          -- single, double, triple, dormitory
ALTER TABLE properties ADD COLUMN IF NOT EXISTS meals_included BOOLEAN DEFAULT 0;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS ac_available BOOLEAN DEFAULT 0;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS wifi_available BOOLEAN DEFAULT 0;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS security_deposit_months INTEGER;

-- Rent specific
ALTER TABLE properties ADD COLUMN IF NOT EXISTS rent_monthly REAL;
ALTER TABLE properties ADD COLUMN IF NOT EXISTS lease_duration TEXT;     -- 11 months, 2 years, etc.
ALTER TABLE properties ADD COLUMN IF NOT EXISTS lock_in_period TEXT;

-- Additional indexes
CREATE INDEX IF NOT EXISTS idx_properties_category ON properties(property_category);
CREATE INDEX IF NOT EXISTS idx_properties_subtype ON properties(property_subtype);
CREATE INDEX IF NOT EXISTS idx_properties_pincode ON properties(pincode);
CREATE INDEX IF NOT EXISTS idx_properties_bhk ON properties(bhk);
CREATE INDEX IF NOT EXISTS idx_properties_commercial_type ON properties(commercial_type);
CREATE INDEX IF NOT EXISTS idx_properties_pg_type ON properties(pg_type);

-- Composite indexes for common queries
CREATE INDEX IF NOT EXISTS idx_prop_cat_listing ON properties(property_category, listing_type);
CREATE INDEX IF NOT EXISTS idx_prop_cat_price ON properties(property_category, price);
CREATE INDEX IF NOT EXISTS idx_prop_locality_type ON properties(locality, property_category);
CREATE INDEX IF NOT EXISTS idx_prop_pincode_cat ON properties(pincode, property_category);
