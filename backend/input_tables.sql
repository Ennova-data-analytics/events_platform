-- Enable UUID generation functions if the extension is not already enabled.
CREATE EXTENSION IF NOT EXISTS "pgcrypto";


-- =============================================================================
-- Pillar 1: Identity & Access Management
-- Manages users, roles, and their permissions.
-- =============================================================================

CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(255),
    phone_number VARCHAR(50),
    
    cv_url TEXT,
    cover_letter_url TEXT,
    
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE roles (
    role_id SERIAL PRIMARY KEY,
    role_name VARCHAR(50) UNIQUE NOT NULL 
);

CREATE TABLE user_roles (
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role_id INT NOT NULL REFERENCES roles(role_id) ON DELETE CASCADE,
    
    PRIMARY KEY (user_id, role_id)
);


-- =============================================================================
-- Pillar 2: Event & Logistics Core (CRM)
-- Manages the events themselves and the network of external contacts.
-- Note: 'form_templates' table must exist before 'events' due to foreign key.
-- It is defined in Pillar 3 and created first.
-- =============================================================================

CREATE TABLE contacts (
    contact_id SERIAL PRIMARY KEY,
    contact_name VARCHAR(255) NOT NULL,
    company VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    contact_type VARCHAR(50),
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- =============================================================================
-- Pillar 3: Flexible Forms & Registrations
-- The system for creating custom registration forms and storing submissions.
-- =============================================================================

CREATE TABLE form_templates (
    template_id SERIAL PRIMARY KEY,
    template_name VARCHAR(255) NOT NULL, 
    
    fields JSONB NOT NULL,
    
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


CREATE TABLE events (
    event_id SERIAL PRIMARY KEY,
    event_name VARCHAR(255) NOT NULL,
    description TEXT,
    event_date_start TIMESTAMP WITH TIME ZONE NOT NULL,
    event_date_end TIMESTAMP WITH TIME ZONE,
    location TEXT,
    status VARCHAR(50) NOT NULL DEFAULT 'Draft', 
    capacity INT,
    price_euros DECIMAL(10, 2) DEFAULT 0.00,
    
    form_template_id INT REFERENCES form_templates(template_id) ON DELETE SET NULL,
    
    created_by_user_id UUID REFERENCES users(user_id), 
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE event_contacts (
    event_id INT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    contact_id INT NOT NULL REFERENCES contacts(contact_id) ON DELETE CASCADE,
    
    PRIMARY KEY (event_id, contact_id)
);

CREATE TABLE registrations (
    registration_id SERIAL PRIMARY KEY,
    event_id INT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    
    status VARCHAR(50) NOT NULL DEFAULT 'Pending Payment', 
    
    stripe_payment_intent_id VARCHAR(255) UNIQUE,
    
  
    form_responses JSONB,
    
    registration_date TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    
    UNIQUE(event_id, user_id)
);


-- =============================================================================
-- Pillar 4: Performance & Feedback
-- Tables for tracking post-event success.
-- =============================================================================

CREATE TABLE feedback (
    feedback_id SERIAL PRIMARY KEY,
    event_id INT NOT NULL REFERENCES events(event_id) ON DELETE CASCADE,
    
    user_id UUID REFERENCES users(user_id) ON DELETE SET NULL,
    
    respondent_type VARCHAR(50) NOT NULL, 
    satisfaction_score INT,
    comments TEXT,
    submitted_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);


-- =============================================================================
-- Initial Data Population
-- Inserts the essential, non-changing data needed for the application to run.
-- =============================================================================

INSERT INTO roles (role_name) VALUES
    ('attendee'),
    ('organiser'),
    ('super_admin');
