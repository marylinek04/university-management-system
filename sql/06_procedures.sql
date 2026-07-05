-- =============================================
-- STORED PROCEDURES
-- =============================================
USE University_database3;
GO

--procedures 
CREATE OR ALTER PROCEDURE usp_CreateUser
@Username VARCHAR(50),
@Email VARCHAR(120),
@PasswordHash VARCHAR(255),
@RoleName VARCHAR(50)
AS
BEGIN
SET NOCOUNT ON;


-- Check for existing user/email
IF EXISTS (SELECT 1 FROM [User] WHERE username = @Username OR email = @Email)
BEGIN
    ;THROW 50001, 'User with this username or email already exists.', 1;
END

-- Insert ONLY into User table
INSERT INTO [User] (roleID, username, email, passwordHash)
SELECT roleID, @Username, @Email, @PasswordHash
FROM [Role]
WHERE roleName = @RoleName;
END;

GO


CREATE OR ALTER PROCEDURE usp_RegisterStudentPayment
    @StudentFullName VARCHAR(150),
    @Amount DECIMAL(10,2),
    @ProcessedByUserID INT
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @StudentID INT;

    SELECT @StudentID = s.studentID
    FROM Student s
    WHERE CONCAT(s.firstName, ' ', s.lastName) = @StudentFullName;

    IF @StudentID IS NULL
        THROW 50010, 'Student not found.', 1;

    -- ONLY insert payment
    INSERT INTO StudentPayment (studentID, amount, processed_by)
    VALUES (@StudentID, @Amount, @ProcessedByUserID);


END;
GO



CREATE OR ALTER PROCEDURE dbo.usp_EnrollStudent
    @StudentName   VARCHAR(120),   -- "First Last"
    @CourseCode    VARCHAR(20),
    @SemesterName  VARCHAR(50)
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        BEGIN TRAN;

        DECLARE 
            @StudentID INT,
            @CourseID INT,
            @SemesterID INT,
            @SectionID INT,
            @CourseFee DECIMAL(10,2);

        /* -------------------------
           Resolve Student
        ------------------------- */
        SELECT @StudentID = studentID
        FROM Student
        WHERE LTRIM(RTRIM(firstName)) + ' ' + LTRIM(RTRIM(lastName))
      = LTRIM(RTRIM(@StudentName));

        IF @StudentID IS NULL
            THROW 50001, 'Student not found.', 1;

        /* -------------------------
           Resolve Course + Fee
        ------------------------- */
        SELECT 
            @CourseID = courseID,
            @CourseFee = courseFee
        FROM Course
        WHERE courseCode = @CourseCode;

        IF @CourseID IS NULL
            THROW 50002, 'Course not found.', 1;

        /* -------------------------
           Resolve Semester
        ------------------------- */
        SELECT @SemesterID = semesterID
        FROM Semester
        WHERE semesterName = @SemesterName;

        IF @SemesterID IS NULL
            THROW 50003, 'Semester not found.', 1;

        /* -------------------------
           Resolve Section
        ------------------------- */
        SELECT @SectionID = sectionID
        FROM Section
        WHERE courseID = @CourseID
          AND semesterID = @SemesterID;

        IF @SectionID IS NULL
            THROW 50004, 'Section not found for this course and semester.', 1;

        /* -------------------------
           Financial eligibility check
           (USING YOUR FUNCTION)
        ------------------------- */
        IF dbo.fn_CanEnroll(@StudentName, @CourseFee) = 0
            THROW 50005, 'Insufficient balance to enroll in this course.', 1;

        /* -------------------------
           Enroll student
           (capacity trigger will fire)
        ------------------------- */
        INSERT INTO Enrollment (studentID, sectionID)
        VALUES (@StudentID, @SectionID);
        /* -------------------------
   Deduct course fee from student balance
------------------------- */
UPDATE StudentAccount
SET balance = balance - @CourseFee
WHERE studentID = @StudentID;


        COMMIT;

        PRINT 'Student enrolled successfully.';
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.usp_SetStudentGrade
    @InstructorID INT,
    @StudentID INT,
    @SemesterName VARCHAR(50),
    @CourseCode VARCHAR(20),
    @GradeValue CHAR(2)
WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        BEGIN TRAN;

        DECLARE @SectionID INT;
        DECLARE @EnrollmentID INT;
        DECLARE @CurrentStatus VARCHAR(20);

        -- 1) Validate grade
        IF @GradeValue NOT IN ('A','B','C','D','F')
            THROW 50020, 'Invalid grade value.', 1;

      
           /* -----------------------------------------------------------
    1) Find enrollment FIRST (most important rule)
------------------------------------------------------------*/
    SELECT 
    @EnrollmentID = e.enrollmentID,
    @SectionID = e.sectionID
FROM Enrollment e
JOIN Section sec   ON sec.sectionID = e.sectionID
JOIN Course c      ON c.courseID = sec.courseID
JOIN Semester sem  ON sem.semesterID = sec.semesterID
WHERE e.studentID = @StudentID
  AND c.courseCode = @CourseCode
  AND sem.semesterName = @SemesterName;

IF @EnrollmentID IS NULL
    THROW 50021, 'Student is not enrolled in this course in this semester.', 1;

/* -----------------------------------------------------------
   2) NOW verify instructor teaches this section
------------------------------------------------------------*/
IF NOT EXISTS (
    SELECT 1
    FROM Section
    WHERE sectionID = @SectionID
      AND instructorID = @InstructorID
)
    THROW 50024, 'Instructor not assigned to this student section.', 1;

        /* -----------------------------------------------------------
           4) Get enrollmentID
        ------------------------------------------------------------*/
        SELECT @EnrollmentID = enrollmentID
        FROM Enrollment
        WHERE studentID = @StudentID
          AND sectionID = @SectionID;

        /* -----------------------------------------------------------
           5) Check if grade is locked
        ------------------------------------------------------------*/
        SELECT @CurrentStatus = gradeStatus
        FROM Grade
        WHERE enrollmentID = @EnrollmentID;

        IF @CurrentStatus = 'Locked'
            THROW 50022, 'Cannot modify grade. Grade is locked.', 1;

        /* -----------------------------------------------------------
           6) Insert or Update grade
        ------------------------------------------------------------*/
        IF EXISTS (SELECT 1 FROM Grade WHERE enrollmentID = @EnrollmentID)
        BEGIN
            UPDATE Grade
            SET gradeValue = @GradeValue,
                gradeStatus = 'Draft',
                created_at = SYSUTCDATETIME()
            WHERE enrollmentID = @EnrollmentID;
        END
        ELSE
        BEGIN
            INSERT INTO Grade (enrollmentID, gradeValue, gradeStatus, created_at)
            VALUES (@EnrollmentID, @GradeValue, 'Draft', SYSUTCDATETIME());
        END

        COMMIT;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        THROW;
    END CATCH
END;
GO






CREATE OR ALTER PROCEDURE dbo.usp_LockGrades
    @SectionID INT
WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        BEGIN TRAN;

        UPDATE dbo.Grade
        SET gradeStatus = 'Locked'
        WHERE enrollmentID IN (
            SELECT enrollmentID
            FROM dbo.Enrollment
            WHERE sectionID = @SectionID
        );

        COMMIT;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        THROW;
    END CATCH
END;
GO


CREATE OR ALTER PROCEDURE dbo.usp_UnLockGrades
    @SectionID INT
WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;

    BEGIN TRY
        BEGIN TRAN;

        UPDATE dbo.Grade
        SET gradeStatus = 'Draft'
        WHERE enrollmentID IN (
            SELECT enrollmentID
            FROM dbo.Enrollment
            WHERE sectionID = @SectionID
        );

        COMMIT;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        THROW;
    END CATCH
END;
GO




CREATE OR ALTER PROCEDURE dbo.usp_GetMyTranscript
    @username VARCHAR(50),
    @password VARCHAR(255)  -- hashed or plain for demo
    WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;

    -- Validate credentials
    DECLARE @UserID INT;

    SELECT @UserID = userID
    FROM [User]
    WHERE username = @username
      AND passwordHash = @password  -- NOTE: in real life, use HASHBYTES / salted hash

    IF @UserID IS NULL
        THROW 50050, 'Invalid username or password', 1;

    DECLARE @StudentID INT;

    SELECT @StudentID = studentID
    FROM dbo.Student
    WHERE userID = @UserID;

    -- Result set 1: student info + GPA
    SELECT 
        studentID,
        firstName,
        lastName,
        GPA,
        dbo.fn_TotalEarnedCredits(studentID) AS TotalEarnedCredits
    FROM dbo.Student
    WHERE studentID = @StudentID;

    -- Result set 2: course transcript
    SELECT courseCode, courseTitle, semesterName, gradeValue, instructorID
    FROM dbo.vw_StudentTranscript
    WHERE studentID = @StudentID;
END;
GO


GO
CREATE OR ALTER PROCEDURE dbo.AssignInstructorToSection
    @InstructorName VARCHAR(120),
    @CourseCode VARCHAR(20),
    @SemesterName VARCHAR(50)
WITH EXECUTE AS CALLER
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @InstructorID INT, 
            @CourseID INT, 
            @SemesterID INT, 
            @SectionID INT,
            @Credits INT, 
            @CurrentLoad INT = 0, 
            @MaxLoad INT;

    -- Instructor
    SELECT @InstructorID = instructorID
    FROM Instructor
    WHERE fullName = @InstructorName;

    IF @InstructorID IS NULL
        THROW 50001, 'Instructor not found.', 1;

    -- Course
    SELECT @CourseID = courseID
    FROM Course
    WHERE courseCode = @CourseCode;

    IF @CourseID IS NULL
        THROW 50002, 'Course not found.', 1;

    -- Semester
    SELECT @SemesterID = semesterID
    FROM Semester
    WHERE semesterName = @SemesterName;

    IF @SemesterID IS NULL
        THROW 50003, 'Semester not found.', 1;

    -- Section + Credits (deterministic)
    SELECT TOP 1 
        @SectionID = s.sectionID,
        @Credits = c.credits
    FROM Section s
    JOIN Course c ON c.courseID = s.courseID
    WHERE s.courseID = @CourseID
      AND s.semesterID = @SemesterID;

    IF @SectionID IS NULL
        THROW 50004, 'Section for this course and semester not found.', 1;

    -- If already assigned, stop
    IF EXISTS (
        SELECT 1 FROM Section
        WHERE sectionID = @SectionID
          AND instructorID = @InstructorID
    )
    BEGIN
        PRINT 'Instructor already assigned to this section.';
        RETURN;
    END

    -- Current load in this semester
    SELECT @CurrentLoad = ISNULL(SUM(c.credits),0)
    FROM Section s
    JOIN Course c ON c.courseID = s.courseID
    WHERE s.instructorID = @InstructorID
      AND s.semesterID = @SemesterID;

    -- Max load from policy
    SELECT @MaxLoad = maxCredits
    FROM InstructorPolicy
    WHERE instructorID = @InstructorID;

    IF @MaxLoad IS NULL
        SET @MaxLoad = 12;

    IF (@CurrentLoad + @Credits) > @MaxLoad
        THROW 60001, 'Instructor teaching load exceeded.', 1;

    -- Assign
    UPDATE Section
    SET instructorID = @InstructorID
    WHERE sectionID = @SectionID;

    PRINT 'Instructor assigned successfully.';
END;
GO


CREATE OR ALTER PROCEDURE dbo.DropStudentFromCourse 
    @StudentName VARCHAR(120),   -- "First Last"
    @CourseCode VARCHAR(20),
    @SemesterName VARCHAR(50)
 AS
 BEGIN
    SET NOCOUNT ON;

    DECLARE @StudentID INT, @CourseID INT, @SemesterID INT, @SectionID INT, @EnrollmentID INT;

    -- Get Student ID
    SELECT @StudentID = studentID
    FROM Student
    WHERE CONCAT(firstName, ' ', lastName) = @StudentName;

    IF @StudentID IS NULL
        THROW 50001, 'Student not found.', 1;

    -- Get Course ID
    SELECT @CourseID = courseID
    FROM Course
    WHERE courseCode = @CourseCode;

    IF @CourseID IS NULL
        THROW 50002, 'Course not found.', 1;

    -- Get Semester ID
    SELECT @SemesterID = semesterID
    FROM Semester
    WHERE semesterName = @SemesterName;

    IF @SemesterID IS NULL
        THROW 50003, 'Semester not found.', 1;

    -- Get Section ID
    SELECT @SectionID = sectionID
    FROM Section
    WHERE courseID = @CourseID
      AND semesterID = @SemesterID;

    IF @SectionID IS NULL
        THROW 50004, 'Section not found for this course and semester.', 1;

    -- Check if grades are locked
    IF EXISTS (
        SELECT 1
        FROM Grade g
        JOIN Enrollment e ON g.enrollmentID = e.enrollmentID
        WHERE e.studentID = @StudentID
          AND e.sectionID = @SectionID
          AND g.gradeStatus = 'Locked'
    )
        THROW 60010, 'Cannot drop a course after grades are locked.', 1;

    -- Get Enrollment ID
    SELECT @EnrollmentID = enrollmentID
    FROM Enrollment
    WHERE studentID = @StudentID
      AND sectionID = @SectionID;

    -- Delete Grade if exists
    DELETE FROM Grade
    WHERE enrollmentID = @EnrollmentID;

    -- Delete Enrollment
    DELETE FROM Enrollment
    WHERE enrollmentID = @EnrollmentID;

    PRINT 'Student successfully dropped from course.';
END;
GO

GO
CREATE OR ALTER PROCEDURE dbo.usp_LogInstructorHours
    @InstructorID INT,
    @SectionID INT,
    @WorkDate DATE,
    @HoursWorked DECIMAL(5,2)
AS
BEGIN
    SET NOCOUNT ON;

    -- Validate section belongs to instructor
    IF NOT EXISTS (
        SELECT 1
        FROM Section
        WHERE sectionID = @SectionID
          AND instructorID = @InstructorID
    )
        THROW 70001, 'Instructor is not assigned to this section.', 1;

    -- Insert time entry (not approved yet)
    INSERT INTO InstructorTimeEntry
        (instructorID, sectionID, entryDate, hoursWorked, approved)
    VALUES
        (@InstructorID, @SectionID, @WorkDate, @HoursWorked, 0);

    PRINT 'Hours logged successfully. Waiting for approval.';
END;
GO


CREATE OR ALTER PROCEDURE dbo.GenerateInstructorPayroll
    @StartDate DATE,
    @EndDate DATE
 AS
 BEGIN
    INSERT INTO SalaryPayment (instructorID, periodStart, periodEnd, totalHours, amountPaid)
    SELECT
        t.instructorID,
        @StartDate,
        @EndDate,
        SUM(t.hoursWorked),
        SUM(t.hoursWorked) * s.hourlyRate
    FROM InstructorTimeEntry t
    JOIN InstructorSalary s ON t.instructorID = s.instructorID
    WHERE t.entryDate BETWEEN @StartDate AND @EndDate
      AND t.approved = 1
    GROUP BY t.instructorID, s.hourlyRate;
 END;
GO

CREATE OR ALTER PROCEDURE dbo.usp_ApproveInstructorHours
    @EntryID INT,
    @ApprovedBy NVARCHAR   -- HOD/Admin ID
AS
BEGIN
    SET NOCOUNT ON;

    IF NOT EXISTS (
        SELECT 1
        FROM InstructorTimeEntry
        WHERE entryID = @EntryID
    )
        THROW 70002, 'Time entry not found.', 1;

    UPDATE InstructorTimeEntry
    SET approved = 1,
        approved_by= @ApprovedBy,
        approvedOn = SYSDATETIME()
    WHERE entryID = @EntryID;

    PRINT 'Hours approved and recorded.';
END;
GO
