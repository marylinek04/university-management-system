-- =============================================
-- TRIGGERS
-- =============================================
USE University_database3;
GO

--triggers

-- Trigger: automatically create StudentAccount when a new Student is added
CREATE OR ALTER TRIGGER trg_CreateStudentAccount
ON Student
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    -- Insert a StudentAccount for each newly added student
    INSERT INTO StudentAccount (studentID, balance)
    SELECT studentID, 0
    FROM inserted;
END;
GO


CREATE OR ALTER TRIGGER dbo.trg_CheckSectionCapacity
ON dbo.Enrollment
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;
    IF EXISTS (
        SELECT 1
        FROM inserted i
        JOIN dbo.Section s ON i.sectionID = s.sectionID
        WHERE (SELECT COUNT(*) FROM dbo.Enrollment WHERE sectionID = i.sectionID AND enrollment_status = 'ENROLLED') > s.capacity
    )
    BEGIN
        ROLLBACK TRANSACTION;
        THROW 51000, 'Section capacity exceeded.', 1;
        
    END
END;

GO

CREATE OR ALTER TRIGGER dbo.trg_UpdateGPA
ON dbo.Grade
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;
    
    DECLARE @AffectedStudents TABLE (StudentID INT);
    
    INSERT INTO @AffectedStudents (StudentID)
    SELECT e.studentID
    FROM inserted i
    JOIN dbo.Enrollment e ON i.enrollmentID = e.enrollmentID
    UNION
    SELECT e.studentID
    FROM deleted d
    JOIN dbo.Enrollment e ON d.enrollmentID = e.enrollmentID;

    UPDATE s
    SET s.GPA = dbo.fn_CalculateGPA(s.studentID)
    FROM dbo.Student s
    WHERE s.studentID IN (SELECT StudentID FROM @AffectedStudents);
END;

GO

CREATE OR ALTER TRIGGER trg_UpdateStudentAccountBalance
ON StudentPayment
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    -- Update the balance for each student who made a payment
    UPDATE sa
    SET sa.balance = sa.balance + i.amount
    FROM StudentAccount sa
    JOIN inserted i ON sa.studentID = i.studentID;
END;
GO

CREATE OR ALTER TRIGGER trg_CreateAcademicRecord
ON [User]
AFTER INSERT
AS
BEGIN
    SET NOCOUNT ON;

    ---------------------------------------------------------
    -- 1) Create Student records safely
    ---------------------------------------------------------
    INSERT INTO Student
        (userID, firstName, lastName, email, dateOfBirth, admissionDate, status, programID)
    SELECT
        i.userID,

        -- Safe first name
        CASE 
            WHEN CHARINDEX(' ', i.username) > 0 
                THEN LEFT(i.username, CHARINDEX(' ', i.username) - 1)
            ELSE i.username
        END,

        -- Safe last name
        CASE 
            WHEN CHARINDEX(' ', i.username) > 0 
                THEN SUBSTRING(i.username, CHARINDEX(' ', i.username) + 1, LEN(i.username))
            ELSE ''
        END,

        i.email,
        '2000-01-01',
        GETDATE(),
        'Active',
        1
    FROM inserted i
    JOIN Role r ON r.roleID = i.roleID
    WHERE r.roleName = 'Student'
      AND NOT EXISTS (
            SELECT 1 FROM Student s WHERE s.userID = i.userID
      );


    ---------------------------------------------------------
    -- 2) Create StudentAccount ONLY if missing
    ---------------------------------------------------------
    INSERT INTO StudentAccount (studentID, balance)
    SELECT s.studentID, 0
    FROM Student s
    JOIN inserted i ON s.userID = i.userID
    JOIN Role r ON r.roleID = i.roleID
    WHERE r.roleName = 'Student'
      AND NOT EXISTS (
            SELECT 1
            FROM StudentAccount sa
            WHERE sa.studentID = s.studentID
      );


    ---------------------------------------------------------
    -- 3) Create Instructor records safely
    ---------------------------------------------------------
    INSERT INTO Instructor
        (userID, fullName, email, departmentID)
    SELECT
        i.userID,
        i.username,
        i.email,
        1
    FROM inserted i
    JOIN Role r ON r.roleID = i.roleID
    WHERE r.roleName = 'Instructor'
      AND NOT EXISTS (
            SELECT 1 FROM Instructor ins WHERE ins.userID = i.userID
      );


    ---------------------------------------------------------
    -- 4) Create InstructorPolicy ONLY if missing
    ---------------------------------------------------------
    INSERT INTO InstructorPolicy (instructorID, maxCredits)
    SELECT ins.instructorID, 10
    FROM Instructor ins
    JOIN inserted i ON ins.userID = i.userID
    JOIN Role r ON r.roleID = i.roleID
    WHERE r.roleName = 'Instructor'
      AND NOT EXISTS (
            SELECT 1
            FROM InstructorPolicy p
            WHERE p.instructorID = ins.instructorID
      );

END;
GO
