-- =============================================
-- TEST SCRIPTS
-- =============================================
USE University_database3;
GO

SELECT* FROM Section;
SELECT* FROM Course;
SELECT* FROM Semester;
SELECT* FROM Program;
SELECT* FROM Student;
SELECT* FROM [User];
SELECT* FROM Instructor;
SELECT* FROM InstructorPolicy;


-- Active enrollments
SELECT * FROM dbo.fn_ActiveEnrollments(1);   -- SemesterID = 1


-- Section capacity
SELECT * FROM dbo.vw_SectionCapacityStatus;
   


SELECT * FROM dbo.Instructor_assigned_sections(2, 'Fall 2024');



EXEC dbo.usp_CreateUser
    @Username = 'finance',
    @PasswordHash = '123',
    @Email = 'finance@uni.edu',
    @RoleName = 'finance';




--std pays
SELECT DB_NAME() AS CurrentDatabase;

EXEC usp_RegisterStudentPayment 'Aseel Menhem', 4000, 12;
EXEC usp_RegisterStudentPayment 'Maryline Karam', 2000, 12;
EXEC usp_RegisterStudentPayment 'Maryam Daaibes', 2000, 12;

--test
EXEC usp_RegisterStudentPayment 'Nour Hamad', 2000, 12;
EXEC usp_RegisterStudentPayment 'Karim Saleh', 2000, 12;

--check balance
SELECT dbo.fn_GetStudentBalance('Aseel Menhem') AS AseelBalance;
SELECT dbo.fn_GetStudentBalance('Maryline Karam') AS MarylineBalance;
SELECT dbo.fn_GetStudentBalance('Maryam Daaibes') AS MaryamBalance;

--enroll

EXEC usp_EnrollStudent 'Aseel Menhem', 'CE301', 'Fall 2024';
EXEC usp_EnrollStudent 'Aseel Menhem', 'CE410', 'Spring 2025';

EXEC usp_EnrollStudent 'Maryline Karam', 'CE301', 'Fall 2024';
EXEC usp_EnrollStudent 'Maryline Karam', 'EE320', 'Spring 2025';
EXEC usp_EnrollStudent 'Maryline Karam', 'CE410', 'Spring 2025';

EXEC usp_EnrollStudent 'Maryam Daaibes', 'ME210', 'Fall 2024';
EXEC usp_EnrollStudent 'Maryam Daaibes', 'CV220', 'Fall 2025';

EXEC usp_EnrollStudent 'Nour Hamad', 'CE301', 'Fall 2024';
EXEC usp_EnrollStudent 'Karim Saleh', 'EE410', 'Fall 2024';


---STD TRANSCRIPT

EXEC dbo.usp_GetMyTranscript
    @username = 'Aseel Menhem',
    @password = 'pass';

EXEC dbo.usp_GetMyTranscript
    @username = 'Maryline Karam',
    @password = 'pass';

EXEC dbo.usp_GetMyTranscript
    @username = 'Maryam Daaibes',
    @password = 'pass';



SELECT * FROM dbo.vw_StudentTranscript;


--RESET BALANCES IF NEEDED
UPDATE StudentAccount SET balance = 0;
DELETE FROM StudentPayment;


--ASSIGN INSTRUCTOR TO SECTIONS

EXEC AssignInstructorToSection 'Dr. Maya Saad', 'CE301', 'Fall 2024';
EXEC AssignInstructorToSection 'Dr. Hassan Nasser', 'EE410', 'Fall 2024';
EXEC AssignInstructorToSection 'Dr. Rami Fakhoury', 'ME210', 'Fall 2024';


SELECT * FROM dbo.vw_InstructorTeachingLoad;

--TIME ENTRIES AND APPROVAL

EXEC dbo.usp_LogInstructorHours
    @InstructorID = 3,
    @SectionID = 1,
    @WorkDate = '2024-09-28',
    @HoursWorked = 2;

SELECT * FROM InstructorTimeEntry;
EXEC dbo.usp_ApproveInstructorHours 8,15;


-- TEST LOCK AND SET STD GRADE
EXEC dbo.usp_LockGrades 1;


EXEC dbo.usp_SetStudentGrade
    @InstructorID = 3,          -- Dr. Maya Saad (check from Instructor table)
    @StudentID = 7,             -- Aseel Menhem (check from Student table)
    @SemesterName = 'Fall 2024',
    @CourseCode = 'CE301',
    @GradeValue = 'A';


    --DROP

EXEC dbo.DropStudentFromCourse 'Aseel Menhem', 'CE301', 'Fall 2024';
EXEC dbo.usp_UnLockGrades 1;
EXEC dbo.DropStudentFromCourse 'Aseel Menhem', 'CE301', 'Fall 2024';

--prove grade was deleted
SELECT *
FROM Grade g
JOIN Enrollment e ON g.enrollmentID = e.enrollmentID
WHERE e.studentID = 1;

--prove enrollment was deleted
SELECT *
FROM Enrollment
WHERE studentID = 1;


EXEC dbo.usp_SetStudentGrade 3, 7, 'Fall 2024', 'CE301', 'A'; -- Aseel
EXEC dbo.usp_SetStudentGrade 3, 10, 'Fall 2024', 'CE301', 'B'; -- Nour
EXEC dbo.usp_SetStudentGrade 2, 9, 'Fall 2025', 'CV220', 'A'; -- Maryam
EXEC dbo.usp_SetStudentGrade 1, 8, 'Spring 2025', 'EE320', 'B'; -- Maryline
EXEC dbo.usp_SetStudentGrade 3, 7, 'Spring 2025', 'CE410', 'A'; -- Aseel
EXEC dbo.usp_SetStudentGrade 1, 8, 'Fall 2024', 'EE410', 'A'; -- Maryline
EXEC dbo.usp_SetStudentGrade 1, 11, 'Fall 2024', 'EE410', 'C'; -- Karim
EXEC dbo.usp_SetStudentGrade 2, 10, 'Fall 2024', 'ME210', 'B'; -- Maryam


--SECTION COURSE SEM INSTRUCTOR VIEW
SELECT 
    sec.sectionID,
    c.courseCode,
    sem.semesterName,
    i.fullName,
    i.instructorID
FROM Section sec
JOIN Course c ON c.courseID = sec.courseID
JOIN Semester sem ON sem.semesterID = sec.semesterID
LEFT JOIN Instructor i ON i.instructorID = sec.instructorID;


--std and enrolled courses
SELECT 
    s.firstName,
    s.lastName,
    e.sectionID,
    c.courseCode,
    sem.semesterName
FROM Enrollment e
JOIN Student s ON s.studentID = e.studentID
JOIN Section sec ON sec.sectionID = e.sectionID
JOIN Course c ON c.courseID = sec.courseID
JOIN Semester sem ON sem.semesterID = sec.semesterID
WHERE s.firstName = 'Aseel';

EXEC dbo.GenerateInstructorPayroll 
    @StartDate = '2024-09-01',
    @EndDate   = '2024-09-30';

SELECT 
    sp.paymentID,
    i.fullName,
    sp.totalHours,
    sp.amountPaid,
    sp.periodStart,
    sp.periodEnd
FROM SalaryPayment sp
JOIN Instructor i ON i.instructorID = sp.instructorID;
