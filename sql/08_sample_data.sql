-- =============================================
-- SAMPLE DATA
-- =============================================
USE University_database3;
GO

-- =============================================
--  INSERT SAMPLE DATA
-- =============================================
INSERT INTO [Role] (roleName) VALUES
('Student'), ('Instructor'), ('Admin'),('HOD'), ('Registrar'), ('Finance Officer');
GO
-- Users


-- Departments (all Faculty of Engineering)
INSERT INTO Department (departmentName, facultyName) VALUES
('Electrical Engineering', 'Faculty of Engineering'),
('Mechanical Engineering', 'Faculty of Engineering'),
('Computer Engineering', 'Faculty of Engineering'),
('Civil Engineering', 'Faculty of Engineering');
GO

-- Programs
INSERT INTO Program (programName, degreeLevel, departmentID) VALUES
('Computer Engineering Program', 'Bachelor', 3),
('Electrical Power Systems', 'Master', 1),
('Mechanical Design', 'Bachelor', 2),
('Civil Infrastructure', 'Bachelor', 4),
('Embedded Systems', 'Master', 3);
GO



-- =============================================
-- 7) Courses (including courseFee)
-- =============================================
INSERT INTO Course (courseCode, courseTitle, credits, courseFee, departmentID) VALUES
('CE301', 'Data Structures', 3, 1500, 3),
('CE410', 'Operating Systems', 4, 1800, 3),
('EE320', 'Electrical Machines', 3, 1600, 1),
('CV220', 'Structural Analysis', 3, 1400, 4);
GO

-- =============================================
-- 8) Semesters
-- =============================================
INSERT INTO Semester (semesterName, startDate, endDate) VALUES
('Fall 2024', '2024-09-01', '2024-12-20'),
('Spring 2025', '2025-02-01', '2025-06-01'),
('Fall 2025', '2025-07-01', '2025-08-31');
GO

-- Students (username = full name)
EXEC usp_CreateUser 'Aseel Menhem', 'aseel.student@uni.edu', 'pass', 'Student';
EXEC usp_CreateUser 'Maryline Karam', 'maryline.student@uni.edu', 'pass', 'Student';
EXEC usp_CreateUser 'Maryam Daaibes', 'maryam.student@uni.edu', 'pass', 'Student';
EXEC usp_CreateUser 'Nour Hamad', 'nour.student@uni.edu', 'pass', 'Student';
EXEC usp_CreateUser 'Karim Saleh', 'karim.student@uni.edu', 'pass', 'Student';

-- Instructors
EXEC usp_CreateUser 'Dr. Hassan Nasser', 'hassan.nasser@uni.edu', 'pass', 'Instructor';
EXEC usp_CreateUser 'Dr. Rami Fakhoury', 'rami.fakhoury@uni.edu', 'pass', 'Instructor';
EXEC usp_CreateUser 'Dr. Maya Saad', 'maya.saad@uni.edu', 'pass', 'Instructor';

-- =============================================
-- 9) Sections
-- =============================================
INSERT INTO Section (courseID, semesterID, instructorID, capacity)
SELECT
    c.courseID,
    s.semesterID,
    i.instructorID,
    v.capacity
FROM (VALUES
    ('CE301', 'Fall 2024',  'Dr. Maya Saad',        2),
    ('EE410', 'Fall 2024',  'Dr. Hassan Nasser',   20),
    ('ME210', 'Fall 2024',  'Dr. Rami Fakhoury',   30),
    ('CE410', 'Spring 2025','Dr. Maya Saad',       35),
    ('EE320', 'Spring 2025','Dr. Hassan Nasser',   30),
    ('CV220', 'Fall 2025',  'Dr. Rami Fakhoury',   40)
) AS v(courseCode, semesterName, instructorName, capacity)
JOIN Course c     ON c.courseCode = v.courseCode
JOIN Semester s   ON s.semesterName = v.semesterName
JOIN Instructor i ON i.fullName = v.instructorName;

INSERT INTO InstructorSalary (instructorID, hourlyRate, bankAccount) VALUES
(1, 50, 'ACC001'),   -- Dr. Hassan
(2, 60, 'ACC002'),   -- Dr. Rami
(3, 55, 'ACC003');   -- Dr. Maya

INSERT INTO InstructorTimeEntry (instructorID, SectionID, entryDate, hoursWorked, approved)
VALUES
-- Maya (CE301 SectionID = 1)
(3, 1, '2024-09-10', 3, 1),
(3, 1, '2024-09-12', 2, 1),

-- Hassan (EE410 SectionID = 2)
(1, 2, '2024-09-11', 4, 1),
(1, 2, '2024-09-13', 3, 1),

-- Rami (ME210 SectionID = 3)
(2, 3, '2024-09-15', 5, 1);
GO