-- Migration: Create users table
-- Version: 001
-- Description: Creates the users table for authentication

-- Create users table
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(256),
    name VARCHAR(255) NOT NULL,
    role VARCHAR(50) NOT NULL DEFAULT 'user',
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    auth_provider VARCHAR(50) NOT NULL DEFAULT 'local',
    google_id VARCHAR(255) UNIQUE,
    
    -- Profile fields
    phone VARCHAR(20),
    avatar_url TEXT,
    
    -- Language preferences
    text_language VARCHAR(10) NOT NULL DEFAULT 'en',
    voice_language VARCHAR(10) NOT NULL DEFAULT 'en',
    
    -- Timestamps
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP,
    
    -- Email verification
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    email_verification_token VARCHAR(256),
    
    -- Password reset
    password_reset_token VARCHAR(256),
    password_reset_expires TIMESTAMP
);

-- Create indexes for faster lookups
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);
CREATE INDEX IF NOT EXISTS idx_users_auth_provider ON users(auth_provider);
CREATE INDEX IF NOT EXISTS idx_users_google_id ON users(google_id) WHERE google_id IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_users_is_active ON users(is_active);

-- Create updated_at trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Create trigger for automatic updated_at
DROP TRIGGER IF EXISTS update_users_updated_at ON users;
CREATE TRIGGER update_users_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column();

-- Insert default admin user (password: admin123)
INSERT INTO users (email, password_hash, name, role, is_active, auth_provider, email_verified)
VALUES (
    'naveen.sandcube@gmail.com',
    '240be518fabd2724ddb6f04eeb9d5a38d18b46c5b083d36a5aaef2d3b24e0e9e', -- SHA256 of 'admin123'
    'Admin',
    'admin',
    TRUE,
    'local',
    TRUE
)
ON CONFLICT (email) DO NOTHING;

-- Insert demo user (password: demo123)
INSERT INTO users (email, password_hash, name, role, is_active, auth_provider, email_verified)
VALUES (
    'demo@valora.ai',
    'b7e94be513e96e8c45cd23d162275e5a12ebde9100a425c4ebcdd7fa4dcd897c', -- SHA256 of 'demo123'
    'Demo User',
    'user',
    TRUE,
    'local',
    TRUE
)
ON CONFLICT (email) DO NOTHING;

-- Comment on table
COMMENT ON TABLE users IS 'User accounts for authentication and authorization';
