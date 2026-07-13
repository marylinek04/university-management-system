-- =====================================================================
-- University Operations AI Agent - Sample Data
-- Adapted from sql/08_sample_data.sql (same students, instructors,
-- courses, departments, programs, semesters where possible), extended
-- with a prerequisite chain and current-semester sections/enrollments
-- so the agent's tools have realistic scenarios to reason about:
--   - a full section (capacity 1, already occupied)            -> Maryline
--   - a student with insufficient balance for a course fee     -> Maryam / Karim
--   - a duplicate enrollment attempt                            -> Nour
--   - a missing-prerequisite attempt                            -> Yousef
--   - a clean, fully-eligible enrollment                        -> Aseel / Hana
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------
-- Roles & Users
-- ---------------------------------------------------------------
INSERT INTO roles (role_id, role_name) VALUES
 (1, 'Student'),
 (2, 'Instructor'),
 (3, 'Admin'),
 (4, 'HOD'),
 (5, 'Registrar'),
 (6, 'Finance Officer');

INSERT INTO users (user_id, role_id, username, email, password_hash, full_name) VALUES
 (1, 1, 'aseel.menhem',   'aseel.student@uni.edu',   'demo_hash', 'Aseel Menhem'),
 (2, 1, 'maryline.karam', 'maryline.student@uni.edu','demo_hash', 'Maryline Karam'),
 (3, 1, 'maryam.daaibes', 'maryam.student@uni.edu',  'demo_hash', 'Maryam Daaibes'),
 (4, 1, 'nour.hamad',     'nour.student@uni.edu',    'demo_hash', 'Nour Hamad'),
 (5, 1, 'karim.saleh',    'karim.student@uni.edu',   'demo_hash', 'Karim Saleh'),
 (6, 1, 'yousef.khalil',  'yousef.student@uni.edu',  'demo_hash', 'Yousef Khalil'),
 (13, 1, 'hana.tfaily',   'hana.student@uni.edu',    'demo_hash', 'Hana Tfaily'),
 (7, 2, 'hassan.nasser',  'hassan.nasser@uni.edu',   'demo_hash', 'Dr. Hassan Nasser'),
 (8, 2, 'rami.fakhoury',  'rami.fakhoury@uni.edu',   'demo_hash', 'Dr. Rami Fakhoury'),
 (9, 2, 'maya.saad',      'maya.saad@uni.edu',       'demo_hash', 'Dr. Maya Saad'),
 (10, 5, 'registrar1',    'registrar@uni.edu',       'demo_hash', 'Registrar Office'),
 (11, 6, 'finance1',      'finance@uni.edu',         'demo_hash', 'Finance Office'),
 (12, 3, 'admin1',        'admin@uni.edu',           'demo_hash', 'System Admin');

-- ---------------------------------------------------------------
-- Departments & Programs
-- ---------------------------------------------------------------
INSERT INTO departments (department_id, department_name, faculty_name) VALUES
 (1, 'Electrical Engineering', 'Faculty of Engineering'),
 (2, 'Mechanical Engineering', 'Faculty of Engineering'),
 (3, 'Computer Engineering',   'Faculty of Engineering'),
 (4, 'Civil Engineering',      'Faculty of Engineering');

INSERT INTO programs (program_id, program_name, degree_level, department_id) VALUES
 (1, 'Computer Engineering Program', 'Bachelor', 3),
 (2, 'Electrical Power Systems',     'Master',   1),
 (3, 'Mechanical Design',            'Bachelor', 2),
 (4, 'Civil Infrastructure',         'Bachelor', 4),
 (5, 'Embedded Systems',             'Master',   3);

-- ---------------------------------------------------------------
-- Courses & Prerequisites
-- ---------------------------------------------------------------
INSERT INTO courses (course_id, course_code, course_title, credits, course_fee, department_id, description) VALUES
 (1, 'CE205', 'Programming Fundamentals', 3, 1200, 3, 'Introductory programming course covering control flow, functions, and basic data structures.'),
 (2, 'CE301', 'Data Structures',          3, 1500, 3, 'Linked lists, trees, hash tables, graphs and algorithm analysis.'),
 (3, 'CE410', 'Operating Systems',        4, 1800, 3, 'Processes, scheduling, memory management, file systems and concurrency.'),
 (4, 'EE320', 'Electrical Machines',      3, 1600, 1, 'Transformers, DC and AC machines, and electromechanical energy conversion.'),
 (5, 'CV220', 'Structural Analysis',      3, 1400, 4, 'Analysis of statically determinate and indeterminate structures.');

-- CE301 requires CE205, CE410 requires CE301
INSERT INTO course_prerequisites (course_id, prerequisite_course_id) VALUES
 (2, 1),
 (3, 2);

-- ---------------------------------------------------------------
-- Semesters (Spring 2026 is the current/active registration term)
-- ---------------------------------------------------------------
INSERT INTO semesters (semester_id, semester_name, start_date, end_date, is_current) VALUES
 (1, 'Fall 2024',   '2024-09-01', '2024-12-20', 0),
 (2, 'Spring 2025', '2025-02-01', '2025-06-01', 0),
 (3, 'Fall 2025',   '2025-09-01', '2025-12-20', 0),
 (4, 'Spring 2026', '2026-02-01', '2026-06-30', 1);

-- ---------------------------------------------------------------
-- Students
-- ---------------------------------------------------------------
INSERT INTO students (student_id, user_id, first_name, last_name, email, status, gpa, program_id) VALUES
 (1, 1, 'Aseel',    'Menhem',   'aseel.student@uni.edu',   'Active', 3.5,  1),
 (2, 2, 'Maryline', 'Karam',    'maryline.student@uni.edu','Active', 4.0,  1),
 (3, 3, 'Maryam',   'Daaibes',  'maryam.student@uni.edu',  'Active', 2.5,  1),
 (4, 4, 'Nour',     'Hamad',    'nour.student@uni.edu',    'Active', 4.0,  1),
 (5, 5, 'Karim',    'Saleh',    'karim.student@uni.edu',   'Active', 3.67, 1),
 (6, 6, 'Yousef',   'Khalil',   'yousef.student@uni.edu',  'Active', NULL, 1),
 (7, 13, 'Hana',    'Tfaily',   'hana.student@uni.edu',    'Active', 3.5,  1);

-- ---------------------------------------------------------------
-- Instructors & Salaries
-- ---------------------------------------------------------------
INSERT INTO instructors (instructor_id, user_id, full_name, email, department_id, max_credits) VALUES
 (1, 7, 'Dr. Hassan Nasser', 'hassan.nasser@uni.edu', 1, 12),
 (2, 8, 'Dr. Rami Fakhoury', 'rami.fakhoury@uni.edu', 2, 12),
 (3, 9, 'Dr. Maya Saad',     'maya.saad@uni.edu',     3, 9);

INSERT INTO instructor_salaries (instructor_id, hourly_rate, bank_account) VALUES
 (1, 50, 'ACC001'),
 (2, 60, 'ACC002'),
 (3, 55, 'ACC003');

-- ---------------------------------------------------------------
-- Sections
--   1: CE205 / Fall 2024   / Hassan  (history)
--   2: EE320 / Fall 2024   / Hassan  (history)
--   3: CE301 / Spring 2025 / Maya    (history)
--   4: CV220 / Spring 2025 / Rami    (history)
--   5: CE301 / Spring 2026 / Maya    (capacity 1 -> currently FULL)
--   6: CE410 / Spring 2026 / Maya    (open, Nour already enrolled)
--   7: EE320 / Spring 2026 / Hassan  (open)
--   8: CV220 / Spring 2026 / Rami    (open)
--   9: CE205 / Spring 2026 / Hassan  (open)
-- ---------------------------------------------------------------
INSERT INTO sections (section_id, course_id, semester_id, instructor_id, capacity) VALUES
 (1, 1, 1, 1, 30),
 (2, 4, 1, 1, 30),
 (3, 2, 2, 3, 30),
 (4, 5, 2, 2, 30),
 (5, 2, 4, 3, 1),
 (6, 3, 4, 3, 35),
 (7, 4, 4, 1, 30),
 (8, 5, 4, 2, 40),
 (9, 1, 4, 1, 30);

-- ---------------------------------------------------------------
-- Historical enrollments + locked grades
-- ---------------------------------------------------------------
INSERT INTO enrollments (enrollment_id, student_id, section_id, enrollment_date, enrollment_status) VALUES
 (1,  1, 1, '2024-09-05', 'COMPLETED'),  -- Aseel    CE205 Fall24 -> A
 (2,  1, 3, '2025-02-05', 'COMPLETED'),  -- Aseel    CE301 Spring25 -> B
 (3,  2, 1, '2024-09-05', 'COMPLETED'),  -- Maryline CE205 Fall24 -> A
 (4,  3, 1, '2024-09-05', 'COMPLETED'),  -- Maryam   CE205 Fall24 -> B
 (5,  3, 2, '2024-09-05', 'COMPLETED'),  -- Maryam   EE320 Fall24 -> C
 (6,  4, 1, '2024-09-05', 'COMPLETED'),  -- Nour     CE205 Fall24 -> A
 (7,  4, 3, '2025-02-05', 'COMPLETED'),  -- Nour     CE301 Spring25 -> A
 (8,  5, 1, '2024-09-05', 'COMPLETED'),  -- Karim    CE205 Fall24 -> A
 (9,  5, 3, '2025-02-05', 'COMPLETED'),  -- Karim    CE301 Spring25 -> A
 (10, 5, 4, '2025-02-05', 'COMPLETED'),  -- Karim    CV220 Spring25 -> B
 -- Current-semester (Spring 2026) enrollments
 (11, 4, 5, '2026-02-10', 'ENROLLED'),   -- Nour enrolled in CE301 (fills the 1-seat section -> FULL)
 (12, 4, 6, '2026-02-10', 'ENROLLED'),   -- Nour already enrolled in CE410 (duplicate-enrollment test)
 (13, 7, 1, '2024-09-05', 'COMPLETED'),  -- Hana     CE205 Fall24 -> A
 (14, 7, 3, '2025-02-05', 'COMPLETED');  -- Hana     CE301 Spring25 -> B (prereqs done: eligible for CE410)

INSERT INTO grades (enrollment_id, grade_value, grade_status) VALUES
 (1, 'A', 'Locked'),
 (2, 'B', 'Locked'),
 (3, 'A', 'Locked'),
 (4, 'B', 'Locked'),
 (5, 'C', 'Locked'),
 (6, 'A', 'Locked'),
 (7, 'A', 'Locked'),
 (8, 'A', 'Locked'),
 (9, 'A', 'Locked'),
 (10, 'B', 'Locked'),
 (13, 'A', 'Locked'),
 (14, 'B', 'Locked');

-- ---------------------------------------------------------------
-- Student Accounts & Payments
--   Aseel:    3000 (enough for CE410 fee 1800)
--   Maryline: 2000 (enough for CE301 fee 1500, but section 5 is full)
--   Maryam:    500 (insufficient for CE410 fee 1800)
--   Nour:     5000
--   Karim:    1000 (insufficient for CE410 fee 1800)
--   Yousef:   5000 (sufficient balance, but missing CE301 prereq for CE410/CE301)
--   Hana:     4000 (prereqs complete -> fully eligible for CE410, fee 1800)
-- ---------------------------------------------------------------
INSERT INTO student_accounts (student_id, balance) VALUES
 (1, 3000),
 (2, 2000),
 (3, 500),
 (4, 5000),
 (5, 1000),
 (6, 5000),
 (7, 4000);

INSERT INTO student_payments (student_id, amount, payment_date, description) VALUES
 (1, 4500, '2024-09-01 10:00:00', 'Tuition payment - Fall 2024 & Spring 2025'),
 (2, 3500, '2024-09-01 10:05:00', 'Tuition payment - Fall 2024 & Spring 2025'),
 (3, 2000, '2024-09-01 10:10:00', 'Tuition payment - Fall 2024'),
 (4, 7000, '2024-09-01 10:15:00', 'Tuition payment - Fall 2024 & Spring 2025'),
 (5, 4000, '2024-09-01 10:20:00', 'Tuition payment - Fall 2024 & Spring 2025'),
 (6, 5000, '2026-01-15 09:00:00', 'Tuition deposit - Spring 2026'),
 (7, 4000, '2026-01-20 09:00:00', 'Tuition deposit - Spring 2026');

-- ---------------------------------------------------------------
-- Instructor time entries (for payroll / workload tools)
-- ---------------------------------------------------------------
INSERT INTO instructor_time_entries (instructor_id, section_id, entry_date, hours_worked, approved) VALUES
 (1, 1, '2024-09-10', 10, 1),
 (1, 2, '2024-09-11', 8,  1),
 (1, 7, '2026-02-15', 5,  1),
 (1, 7, '2026-03-01', 4,  0),
 (2, 4, '2025-02-15', 12, 1),
 (2, 8, '2026-02-20', 6,  1),
 (3, 3, '2025-02-15', 15, 1),
 (3, 5, '2026-02-12', 4,  1),
 (3, 6, '2026-03-05', 3,  0);

-- ---------------------------------------------------------------
-- Historical salary payments
-- ---------------------------------------------------------------
INSERT INTO salary_payments (instructor_id, period_start, period_end, total_hours, amount_paid, paid_on) VALUES
 (1, '2024-09-01', '2024-12-20', 18, 900,  '2025-01-05 09:00:00'),
 (2, '2025-02-01', '2025-06-01', 12, 720,  '2025-06-05 09:00:00'),
 (3, '2025-02-01', '2025-06-01', 15, 825,  '2025-06-05 09:00:00');
