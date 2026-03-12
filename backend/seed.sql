-- =============================================================================
-- seed.sql  —  Synthetic development data for the Events Platform
-- =============================================================================
-- Generated from seed.py (Python SQLAlchemy seed script).
--
-- Password for all accounts: password123
-- Bcrypt hash used: $2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW
--
-- Accounts created:
--   super_admin@dev.com  / password123  (super_admin + organiser)
--   organiser@dev.com    / password123  (organiser)
--   alice@dev.com        / password123  (attendee, ennova member, CS 3rd Year)
--   bob@dev.com          / password123  (attendee, Business 2nd Year)
--   carol@dev.com        / password123  (attendee, ennova member, Engineering 4th Year)
--   dave@dev.com         / password123  (attendee, Physics 1st Year)
--   eve@dev.com          / password123  (attendee, Mathematics MSc)
--
-- To run:
--   psql -U <user> -d <database> -f seed.sql
--
-- Idempotency:
--   Users and roles use ON CONFLICT DO NOTHING.
--   All other tables are inserted in dependency order.
--   To fully reset before re-seeding, uncomment the TRUNCATE block below.
-- =============================================================================


-- =============================================================================
-- OPTIONAL RESET — uncomment this block to wipe all seeded data and restart
-- WARNING: This will DELETE all data in these tables.
-- =============================================================================
/*
TRUNCATE TABLE
    attendance_records,
    attendance_sessions,
    team_members,
    event_teams,
    guest_tickets,
    feedback_invitations,
    feedback,
    in_app_notifications,
    registrations,
    discount_codes,
    referral_links,
    ticket_types,
    event_feedback_templates,
    event_contacts,
    events,
    form_templates,
    feedback_templates,
    contacts,
    user_roles,
    users,
    roles
RESTART IDENTITY CASCADE;
*/


BEGIN;

-- =============================================================================
-- 1. ROLES
-- =============================================================================
INSERT INTO roles (role_id, role_name) VALUES
    (1, 'attendee'),
    (2, 'organiser'),
    (3, 'super_admin')
ON CONFLICT (role_name) DO NOTHING;

-- Reset sequence to avoid collisions if roles were already present
SELECT setval('roles_role_id_seq', GREATEST((SELECT MAX(role_id) FROM roles), 3));


-- =============================================================================
-- 2. USERS
-- =============================================================================
INSERT INTO users (
    user_id, email, hashed_password, full_name,
    phone_number, degree, study_year,
    is_active, is_ennova_member,
    created_at, updated_at
) VALUES
    -- super_admin@dev.com  (super_admin + organiser)
    (
        'a0000000-0000-0000-0000-000000000001'::uuid,
        'super_admin@dev.com',
        '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
        'Super Admin',
        '+44 7700 900000',
        NULL, NULL,
        TRUE, FALSE,
        NOW(), NOW()
    ),
    -- organiser@dev.com
    (
        'a0000000-0000-0000-0000-000000000002'::uuid,
        'organiser@dev.com',
        '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
        'Olivia Organiser',
        '+44 7700 900000',
        NULL, NULL,
        TRUE, FALSE,
        NOW(), NOW()
    ),
    -- alice@dev.com  (ennova member, CS 3rd Year)
    (
        'a0000000-0000-0000-0000-000000000003'::uuid,
        'alice@dev.com',
        '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
        'Alice Andersen',
        '+44 7700 900000',
        'Computer Science', '3rd Year',
        TRUE, TRUE,
        NOW(), NOW()
    ),
    -- bob@dev.com  (Business 2nd Year)
    (
        'a0000000-0000-0000-0000-000000000004'::uuid,
        'bob@dev.com',
        '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
        'Bob Benson',
        '+44 7700 900000',
        'Business', '2nd Year',
        TRUE, FALSE,
        NOW(), NOW()
    ),
    -- carol@dev.com  (ennova member, Engineering 4th Year)
    (
        'a0000000-0000-0000-0000-000000000005'::uuid,
        'carol@dev.com',
        '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
        'Carol Chen',
        '+44 7700 900000',
        'Engineering', '4th Year',
        TRUE, TRUE,
        NOW(), NOW()
    ),
    -- dave@dev.com  (Physics 1st Year)
    (
        'a0000000-0000-0000-0000-000000000006'::uuid,
        'dave@dev.com',
        '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
        'Dave Davies',
        '+44 7700 900000',
        'Physics', '1st Year',
        TRUE, FALSE,
        NOW(), NOW()
    ),
    -- eve@dev.com  (Mathematics MSc)
    (
        'a0000000-0000-0000-0000-000000000007'::uuid,
        'eve@dev.com',
        '$2b$12$EixZaYVK1fsbw1ZfbX3OXePaWxn96p36WQoeG6Lruj3vjPGga31lW',
        'Eve Evans',
        '+44 7700 900000',
        'Mathematics', 'MSc',
        TRUE, FALSE,
        NOW(), NOW()
    )
ON CONFLICT (email) DO NOTHING;


-- =============================================================================
-- 3. USER → ROLE ASSIGNMENTS
-- =============================================================================
INSERT INTO user_roles (user_id, role_id)
SELECT u.user_id, r.role_id
FROM (VALUES
    -- super_admin gets super_admin + organiser roles
    ('a0000000-0000-0000-0000-000000000001'::uuid, 'super_admin'),
    ('a0000000-0000-0000-0000-000000000001'::uuid, 'organiser'),
    -- organiser
    ('a0000000-0000-0000-0000-000000000002'::uuid, 'organiser'),
    -- attendees
    ('a0000000-0000-0000-0000-000000000003'::uuid, 'attendee'),
    ('a0000000-0000-0000-0000-000000000004'::uuid, 'attendee'),
    ('a0000000-0000-0000-0000-000000000005'::uuid, 'attendee'),
    ('a0000000-0000-0000-0000-000000000006'::uuid, 'attendee'),
    ('a0000000-0000-0000-0000-000000000007'::uuid, 'attendee')
) AS v(uid, rname)
JOIN users  u ON u.user_id   = v.uid
JOIN roles  r ON r.role_name = v.rname
ON CONFLICT DO NOTHING;


-- =============================================================================
-- 4. CONTACTS
-- =============================================================================
INSERT INTO contacts (
    contact_id, contact_name, company, email, phone, contact_type, notes, created_at
) VALUES
    (
        1,
        'Jane Smith',
        'TechCorp Ltd',
        'jane.smith@techcorp.example',
        '+44 20 7946 0001',
        'sponsor',
        'Primary contact for TechCorp sponsorship.',
        NOW()
    ),
    (
        2,
        'Mark Jones',
        'City Conference Centre',
        'mark.jones@citycc.example',
        '+44 20 7946 0002',
        'venue',
        NULL,
        NOW()
    )
ON CONFLICT DO NOTHING;

SELECT setval('contacts_contact_id_seq', GREATEST((SELECT MAX(contact_id) FROM contacts), 2));


-- =============================================================================
-- 5. FORM TEMPLATES
-- =============================================================================
INSERT INTO form_templates (template_id, template_name, fields, created_at) VALUES
    (
        1,
        'Basic Registration Form',
        '[
            {"id": "dietary",     "type": "select",   "label": "Dietary requirements", "options": ["None","Vegetarian","Vegan","Halal","Gluten-free"], "required": false},
            {"id": "tshirt_size", "type": "select",   "label": "T-shirt size",          "options": ["XS","S","M","L","XL","XXL"],                      "required": true},
            {"id": "linkedin",    "type": "text",     "label": "LinkedIn URL",           "required": false}
        ]'::jsonb,
        NOW()
    ),
    (
        2,
        'Hackathon Registration Form',
        '[
            {"id": "team_name", "type": "text",     "label": "Team name",              "required": true},
            {"id": "skills",    "type": "textarea", "label": "Key skills / tech stack", "required": true},
            {"id": "github",    "type": "text",     "label": "GitHub profile URL",     "required": false},
            {"id": "dietary",   "type": "select",   "label": "Dietary requirements",   "options": ["None","Vegetarian","Vegan","Halal","Gluten-free"], "required": false}
        ]'::jsonb,
        NOW()
    )
ON CONFLICT DO NOTHING;

SELECT setval('form_templates_template_id_seq', GREATEST((SELECT MAX(template_id) FROM form_templates), 2));


-- =============================================================================
-- 6. FEEDBACK TEMPLATES
-- =============================================================================
INSERT INTO feedback_templates (
    template_id, template_name, description, fields, created_at, updated_at
) VALUES
    (
        1,
        'Standard Event Feedback',
        'General post-event feedback form.',
        '[
            {"id": "overall",    "type": "rating",   "label": "Overall experience (1-5)", "required": true,  "min": 1, "max": 5},
            {"id": "content",    "type": "rating",   "label": "Content quality (1-5)",    "required": true,  "min": 1, "max": 5},
            {"id": "venue",      "type": "rating",   "label": "Venue & logistics (1-5)",  "required": true,  "min": 1, "max": 5},
            {"id": "highlights", "type": "textarea", "label": "What did you enjoy most?", "required": false},
            {"id": "improve",    "type": "textarea", "label": "What could we improve?",   "required": false},
            {"id": "recommend",  "type": "select",   "label": "Would you recommend this event?",
             "options": ["Definitely","Probably","Probably not","Definitely not"], "required": true}
        ]'::jsonb,
        NOW(),
        NOW()
    )
ON CONFLICT DO NOTHING;

SELECT setval('feedback_templates_template_id_seq', GREATEST((SELECT MAX(template_id) FROM feedback_templates), 1));


-- =============================================================================
-- 7. EVENTS
-- =============================================================================
-- Event IDs: 1=tech_conf, 2=hackathon, 3=past_event, 4=draft_event

INSERT INTO events (
    event_id,
    event_name, description,
    event_date_start, event_date_end,
    location, map_address, latitude, longitude,
    status, capacity, price_euros,
    signups_enabled, is_free_for_members,
    requires_approval, teams_enabled, team_max_members,
    image_url, sponsor_logos,
    form_template_id,
    created_by_user_id,
    created_at, updated_at
) VALUES

    -- 1. Ennova Tech Conference 2026 (Published, +30 days)
    (
        1,
        'Ennova Tech Conference 2026',
        'Our flagship annual tech conference featuring keynotes, workshops, and networking sessions with industry leaders. Don''t miss out!',
        NOW() + INTERVAL '30 days',
        NOW() + INTERVAL '30 days' + INTERVAL '8 hours',
        'City Conference Centre, London',
        '1 Tech Street, London EC1A 1BB',
        51.5194, -0.0862,
        'Published', 200, 0.00,
        TRUE, FALSE,
        FALSE, FALSE, NULL,
        'https://images.unsplash.com/photo-1540575467063-178a50c2df87?w=1200',
        ARRAY['https://placehold.co/200x80?text=TechCorp']::text[],
        1,
        'a0000000-0000-0000-0000-000000000002'::uuid,
        NOW(), NOW()
    ),

    -- 2. 48-Hour AI Hackathon (Published, +60 days, teams)
    (
        2,
        '48-Hour AI Hackathon',
        'Build something amazing in 48 hours. Form a team of up to 4, access cloud credits, mentors, and win prizes worth €5,000!',
        NOW() + INTERVAL '60 days',
        NOW() + INTERVAL '62 days',
        'Innovation Hub, Manchester',
        '2 Hack Lane, Manchester M1 1AE',
        53.4808, -2.2426,
        'Published', 120, 0.00,
        TRUE, FALSE,
        TRUE, TRUE, 4,
        'https://images.unsplash.com/photo-1504384308090-c894fdcc538d?w=1200',
        NULL,
        2,
        'a0000000-0000-0000-0000-000000000001'::uuid,
        NOW(), NOW()
    ),

    -- 3. Winter Networking Night (Completed, -30 days)
    (
        3,
        'Winter Networking Night',
        'An evening of networking, drinks, and lightning talks from alumni working in tech.',
        NOW() - INTERVAL '30 days',
        NOW() - INTERVAL '30 days' + INTERVAL '3 hours',
        'The Grand Hotel, Edinburgh',
        NULL,
        NULL, NULL,
        'Completed', 80, 5.00,
        FALSE, FALSE,
        FALSE, FALSE, NULL,
        'https://images.unsplash.com/photo-1511795409834-ef04bbd61622?w=1200',
        NULL,
        NULL,
        'a0000000-0000-0000-0000-000000000002'::uuid,
        NOW() - INTERVAL '60 days', NOW() - INTERVAL '30 days'
    ),

    -- 4. Spring Career Fair 2026 (Draft, +90 days)
    (
        4,
        'Spring Career Fair 2026',
        'Connect with 30+ top employers. Bring your CV!',
        NOW() + INTERVAL '90 days',
        NOW() + INTERVAL '90 days' + INTERVAL '6 hours',
        'University Main Hall',
        NULL,
        NULL, NULL,
        'Draft', 500, 0.00,
        FALSE, FALSE,
        FALSE, FALSE, NULL,
        NULL,
        NULL,
        NULL,
        'a0000000-0000-0000-0000-000000000002'::uuid,
        NOW(), NOW()
    )

ON CONFLICT DO NOTHING;

SELECT setval('events_event_id_seq', GREATEST((SELECT MAX(event_id) FROM events), 4));


-- =============================================================================
-- 8. EVENT ↔ CONTACT LINKS
-- =============================================================================
-- Tech conference has both sponsor and venue contacts
INSERT INTO event_contacts (event_id, contact_id) VALUES
    (1, 1),
    (1, 2)
ON CONFLICT DO NOTHING;


-- =============================================================================
-- 9. TICKET TYPES
-- =============================================================================
-- IDs: 1=tt_free, 2=tt_early, 3=tt_standard (tech_conf)
--      4=tt_hack (hackathon)
--      5=tt_past (past_event)

INSERT INTO ticket_types (
    ticket_type_id, event_id, name, description,
    price_euros, capacity, tickets_sold,
    is_free_for_members, show_availability,
    requires_team, team_max_members,
    display_order, is_active,
    created_at, updated_at
) VALUES

    -- Tech Conference ticket types
    (
        1, 1,
        'Standard (Free for Members)',
        'Free admission for Ennova members.',
        0.00, 50, 1,
        TRUE, TRUE,
        FALSE, NULL,
        0, TRUE,
        NOW(), NOW()
    ),
    (
        2, 1,
        'Early Bird',
        'Discounted ticket — limited availability.',
        15.00, 80, 2,
        FALSE, TRUE,
        FALSE, NULL,
        1, TRUE,
        NOW(), NOW()
    ),
    (
        3, 1,
        'Standard',
        'Full-price admission.',
        25.00, 70, 3,
        FALSE, TRUE,
        FALSE, NULL,
        2, TRUE,
        NOW(), NOW()
    ),

    -- Hackathon ticket type
    (
        4, 2,
        'Hacker Pass',
        'Full hackathon access including meals & swag.',
        0.00, 120, 3,
        FALSE, TRUE,
        TRUE, 4,
        0, TRUE,
        NOW(), NOW()
    ),

    -- Past event ticket type
    (
        5, 3,
        'General Admission',
        NULL,
        5.00, 80, 45,
        FALSE, TRUE,
        FALSE, NULL,
        0, TRUE,
        NOW() - INTERVAL '60 days', NOW() - INTERVAL '30 days'
    )

ON CONFLICT DO NOTHING;

SELECT setval('ticket_types_ticket_type_id_seq', GREATEST((SELECT MAX(ticket_type_id) FROM ticket_types), 5));


-- =============================================================================
-- 10. DISCOUNT CODES
-- =============================================================================
INSERT INTO discount_codes (
    code_id, event_id, code,
    discount_type, discount_value,
    max_uses, used_count,
    expires_at, is_active,
    created_at, updated_at
) VALUES
    (
        1, 1, 'SAVE10',
        'percentage', 10.00,
        30, 0,
        NOW() + INTERVAL '25 days', TRUE,
        NOW(), NOW()
    )
ON CONFLICT DO NOTHING;

SELECT setval('discount_codes_code_id_seq', GREATEST((SELECT MAX(code_id) FROM discount_codes), 1));


-- =============================================================================
-- 11. REFERRAL LINKS
-- =============================================================================
INSERT INTO referral_links (
    link_id, event_id, code,
    referrer_name, commission_percentage,
    is_active, created_at, updated_at
) VALUES
    (
        1, 1, 'REF-ALICE',
        'Alice Andersen', 5.00,
        TRUE, NOW(), NOW()
    )
ON CONFLICT DO NOTHING;

SELECT setval('referral_links_link_id_seq', GREATEST((SELECT MAX(link_id) FROM referral_links), 1));


-- =============================================================================
-- 12. EVENT FEEDBACK TEMPLATES
-- =============================================================================
INSERT INTO event_feedback_templates (
    id, event_id, template_id, is_primary, display_order, created_at
) VALUES
    (1, 1, 1, TRUE,  0, NOW()),  -- tech_conf   → Standard Feedback
    (2, 2, 1, TRUE,  0, NOW())   -- hackathon   → Standard Feedback
ON CONFLICT DO NOTHING;

SELECT setval('event_feedback_templates_id_seq', GREATEST((SELECT MAX(id) FROM event_feedback_templates), 2));


-- =============================================================================
-- 13. REGISTRATIONS
-- =============================================================================
-- IDs:
--  1  = alice  → tech_conf  tt_free     Approved
--  2  = bob    → tech_conf  tt_early    Approved         final=15
--  3  = carol  → tech_conf  tt_standard Approved         final=25
--  4  = dave   → tech_conf  tt_standard Pending Approval final=25
--  5  = eve    → tech_conf  tt_early    Approved         final=15
--  6  = alice  → hackathon  tt_hack     Approved
--  7  = bob    → hackathon  tt_hack     Approved
--  8  = carol  → hackathon  tt_hack     Pending Approval
--  9  = alice  → past_event tt_past     Approved  checked_in=true  final=5
--  10 = bob    → past_event tt_past     Approved  checked_in=true  final=5
--  11 = carol  → past_event tt_past     Approved  checked_in=false final=5

INSERT INTO registrations (
    registration_id,
    event_id, user_id, ticket_type_id,
    status,
    form_responses,
    final_amount_euros,
    ticket_token,
    checked_in, checked_in_at,
    member_discount_applied,
    registration_date
) VALUES

    -- Tech Conference registrations
    (
        1,
        1, 'a0000000-0000-0000-0000-000000000003'::uuid, 1,
        'Approved',
        '{"dietary": "Vegetarian", "tshirt_size": "M", "linkedin": "https://linkedin.com/in/alice-andersen"}'::jsonb,
        NULL,
        'tok_alice_conf_001',
        FALSE, NULL,
        FALSE,
        NOW()
    ),
    (
        2,
        1, 'a0000000-0000-0000-0000-000000000004'::uuid, 2,
        'Approved',
        '{"dietary": "None", "tshirt_size": "L"}'::jsonb,
        15.00,
        'tok_bob_conf_001',
        FALSE, NULL,
        FALSE,
        NOW()
    ),
    (
        3,
        1, 'a0000000-0000-0000-0000-000000000005'::uuid, 3,
        'Approved',
        '{"dietary": "Vegan", "tshirt_size": "S"}'::jsonb,
        25.00,
        'tok_carol_conf_001',
        FALSE, NULL,
        FALSE,
        NOW()
    ),
    (
        4,
        1, 'a0000000-0000-0000-0000-000000000006'::uuid, 3,
        'Pending Approval',
        '{"dietary": "None", "tshirt_size": "XL"}'::jsonb,
        25.00,
        'tok_dave_conf_001',
        FALSE, NULL,
        FALSE,
        NOW()
    ),
    (
        5,
        1, 'a0000000-0000-0000-0000-000000000007'::uuid, 2,
        'Approved',
        '{"dietary": "Halal", "tshirt_size": "M"}'::jsonb,
        15.00,
        'tok_eve_conf_001',
        FALSE, NULL,
        FALSE,
        NOW()
    ),

    -- Hackathon registrations
    (
        6,
        2, 'a0000000-0000-0000-0000-000000000003'::uuid, 4,
        'Approved',
        '{"team_name": "Team Alpha", "skills": "Python, ML, FastAPI", "github": "https://github.com/alice", "dietary": "Vegetarian"}'::jsonb,
        NULL,
        'tok_alice_hack_001',
        FALSE, NULL,
        FALSE,
        NOW()
    ),
    (
        7,
        2, 'a0000000-0000-0000-0000-000000000004'::uuid, 4,
        'Approved',
        '{"team_name": "Team Beta", "skills": "React, Node.js, AWS", "github": "https://github.com/bob", "dietary": "None"}'::jsonb,
        NULL,
        'tok_bob_hack_001',
        FALSE, NULL,
        FALSE,
        NOW()
    ),
    (
        8,
        2, 'a0000000-0000-0000-0000-000000000005'::uuid, 4,
        'Pending Approval',
        '{"team_name": "Team Alpha", "skills": "Data Science, Pandas", "github": "", "dietary": "Vegan"}'::jsonb,
        NULL,
        'tok_carol_hack_001',
        FALSE, NULL,
        FALSE,
        NOW()
    ),

    -- Past event registrations
    (
        9,
        3, 'a0000000-0000-0000-0000-000000000003'::uuid, 5,
        'Approved',
        '{}'::jsonb,
        5.00,
        'tok_alice_past_001',
        TRUE, NOW() - INTERVAL '30 days',
        FALSE,
        NOW() - INTERVAL '35 days'
    ),
    (
        10,
        3, 'a0000000-0000-0000-0000-000000000004'::uuid, 5,
        'Approved',
        '{}'::jsonb,
        5.00,
        'tok_bob_past_001',
        TRUE, NOW() - INTERVAL '30 days',
        FALSE,
        NOW() - INTERVAL '35 days'
    ),
    (
        11,
        3, 'a0000000-0000-0000-0000-000000000005'::uuid, 5,
        'Approved',
        '{}'::jsonb,
        5.00,
        'tok_carol_past_001',
        FALSE, NULL,
        FALSE,
        NOW() - INTERVAL '35 days'
    )

ON CONFLICT DO NOTHING;

SELECT setval('registrations_registration_id_seq', GREATEST((SELECT MAX(registration_id) FROM registrations), 11));


-- =============================================================================
-- 14. EVENT TEAMS
-- =============================================================================
-- IDs: 1=team_alpha (alice), 2=team_beta (bob)

INSERT INTO event_teams (
    team_id, event_id, team_name, max_members,
    created_by_user_id, created_at, updated_at
) VALUES
    (
        1, 2,
        'Team Alpha', 4,
        'a0000000-0000-0000-0000-000000000003'::uuid,
        NOW(), NOW()
    ),
    (
        2, 2,
        'Team Beta', 4,
        'a0000000-0000-0000-0000-000000000004'::uuid,
        NOW(), NOW()
    )
ON CONFLICT DO NOTHING;

SELECT setval('event_teams_team_id_seq', GREATEST((SELECT MAX(team_id) FROM event_teams), 2));


-- =============================================================================
-- 15. TEAM MEMBERS
-- =============================================================================
-- alice's hackathon reg (6) → team_alpha (1)
-- bob's hackathon reg (7)   → team_beta  (2)
-- carol is pending — not yet assigned to a team

INSERT INTO team_members (
    member_id, team_id, registration_id, joined_at
) VALUES
    (1, 1, 6, NOW()),   -- alice → team_alpha
    (2, 2, 7, NOW())    -- bob   → team_beta
ON CONFLICT DO NOTHING;

SELECT setval('team_members_member_id_seq', GREATEST((SELECT MAX(member_id) FROM team_members), 2));


-- =============================================================================
-- 16. GUEST TICKETS
-- =============================================================================
INSERT INTO guest_tickets (
    id, event_id,
    guest_name, guest_email,
    ticket_token,
    checked_in, checked_in_at,
    created_at, created_by_user_id
) VALUES
    (
        1, 1,
        'Guest Speaker', 'speaker@example.com',
        'tok_guest_speaker_001',
        FALSE, NULL,
        NOW(),
        'a0000000-0000-0000-0000-000000000002'::uuid
    )
ON CONFLICT DO NOTHING;

SELECT setval('guest_tickets_id_seq', GREATEST((SELECT MAX(id) FROM guest_tickets), 1));


-- =============================================================================
-- 17. FEEDBACK  (for past_event / Winter Networking Night)
-- =============================================================================
INSERT INTO feedback (
    feedback_id,
    event_id, user_id,
    feedback_template_id,
    form_responses,
    is_anonymous, submitted_at
) VALUES
    -- alice: overall=5 content=5 venue=4
    (
        1,
        3, 'a0000000-0000-0000-0000-000000000003'::uuid,
        1,
        '{"overall": 5, "content": 5, "venue": 4, "highlights": "Keynote was excellent!", "improve": "More networking time.", "recommend": "Definitely"}'::jsonb,
        FALSE,
        NOW() - INTERVAL '28 days'
    ),
    -- bob: overall=4 content=4 venue=3
    (
        2,
        3, 'a0000000-0000-0000-0000-000000000004'::uuid,
        1,
        '{"overall": 4, "content": 4, "venue": 3, "highlights": "Great speakers.", "improve": "Venue was a bit small.", "recommend": "Probably"}'::jsonb,
        FALSE,
        NOW() - INTERVAL '28 days'
    ),
    -- carol: anonymous, overall=3 content=4 venue=3
    (
        3,
        3, NULL,
        1,
        '{"overall": 3, "content": 4, "venue": 3, "highlights": "Good content.", "improve": "Start on time.", "recommend": "Probably"}'::jsonb,
        TRUE,
        NOW() - INTERVAL '28 days'
    )
ON CONFLICT DO NOTHING;

SELECT setval('feedback_feedback_id_seq', GREATEST((SELECT MAX(feedback_id) FROM feedback), 3));


-- =============================================================================
-- 18. IN-APP NOTIFICATIONS
-- =============================================================================
INSERT INTO in_app_notifications (
    notification_id,
    user_id,
    title, message,
    notification_type,
    related_entity_type, related_entity_id,
    is_read,
    created_at
) VALUES
    -- alice: Registration Approved for tech_conf
    (
        1,
        'a0000000-0000-0000-0000-000000000003'::uuid,
        'Registration Approved',
        'Your registration for ''Ennova Tech Conference 2026'' has been approved. See you there!',
        'registration_approved',
        'event', 1,
        FALSE,
        NOW()
    ),
    -- bob: Registration Approved for tech_conf
    (
        2,
        'a0000000-0000-0000-0000-000000000004'::uuid,
        'Registration Approved',
        'Your registration for ''Ennova Tech Conference 2026'' has been approved.',
        'registration_approved',
        'event', 1,
        FALSE,
        NOW()
    ),
    -- dave: Registration Received for tech_conf
    (
        3,
        'a0000000-0000-0000-0000-000000000006'::uuid,
        'Registration Received',
        'We received your registration for ''Ennova Tech Conference 2026''. Pending review.',
        'registration_received',
        'event', 1,
        FALSE,
        NOW()
    ),
    -- carol: Registration Approved for hackathon
    (
        4,
        'a0000000-0000-0000-0000-000000000005'::uuid,
        'Registration Approved',
        'Your registration for ''48-Hour AI Hackathon'' has been approved!',
        'registration_approved',
        'event', 2,
        FALSE,
        NOW()
    )
ON CONFLICT DO NOTHING;

SELECT setval('in_app_notifications_notification_id_seq', GREATEST((SELECT MAX(notification_id) FROM in_app_notifications), 4));


COMMIT;

-- =============================================================================
-- SUMMARY
-- =============================================================================
-- Inserted (with ON CONFLICT DO NOTHING idempotency):
--
--   Roles              : 3  (attendee, organiser, super_admin)
--   Users              : 7  (super_admin, organiser, alice, bob, carol, dave, eve)
--   User-Role links    : 8
--   Contacts           : 2  (Jane Smith / TechCorp, Mark Jones / City Conf Centre)
--   Form templates     : 2  (Basic Registration, Hackathon Registration)
--   Feedback templates : 1  (Standard Event Feedback)
--   Events             : 4  (Tech Conf, Hackathon, Winter Networking, Spring Career Fair)
--   Event-Contact links: 2  (tech_conf ↔ both contacts)
--   Ticket types       : 5  (3 for tech_conf, 1 for hackathon, 1 for past_event)
--   Discount codes     : 1  (SAVE10 — 10% off tech_conf)
--   Referral links     : 1  (REF-ALICE — 5% commission)
--   Event feedback tpl : 2  (tech_conf + hackathon → Standard Feedback)
--   Registrations      : 11 (5 tech_conf, 3 hackathon, 3 past_event)
--   Event teams        : 2  (Team Alpha, Team Beta — hackathon)
--   Team members       : 2  (alice → Alpha, bob → Beta)
--   Guest tickets      : 1  (Guest Speaker @ tech_conf)
--   Feedback           : 3  (alice, bob, carol-anon — past_event)
--   Notifications      : 4  (alice+bob approved, dave received, carol approved)
-- =============================================================================
