-- =============================================
-- FUNCTIONS
-- =============================================
USE University_database3;
GO

GO
CREATE OR ALTER FUNCTION dbo.Instructor_assigned_sections
(
    @instructorID INT,
    @semesterName VARCHAR(50)
)
RETURNS TABLE
AS
RETURN (
    SELECT  
        s.sectionID,
        c.courseID,
        c.courseCode,
        c.courseTitle,
        sem.semesterName
    FROM dbo.Section s
    JOIN dbo.Course c ON s.courseID = c.courseID
    JOIN dbo.Semester sem ON s.semesterID = sem.semesterID
    WHERE s.instructorID = @instructorID  
      AND sem.semesterName = @semesterName
);
GO







CREATE OR ALTER FUNCTION dbo.fn_CalculateGPA (@StudentID INT)
RETURNS DECIMAL(4,2)
AS
BEGIN
    DECLARE @GPA DECIMAL(4,2);

    SELECT @GPA =
        CAST(
            SUM(
                CASE g.gradeValue
                    WHEN 'A' THEN 4.0
                    WHEN 'B' THEN 3.0
                    WHEN 'C' THEN 2.0
                    WHEN 'D' THEN 1.0
                    WHEN 'F' THEN 0.0
                END * c.credits
            ) / NULLIF(SUM(c.credits),0) AS DECIMAL(4,2)
        )
    FROM dbo.Enrollment e
    JOIN dbo.Section sec ON sec.sectionID = e.sectionID
    JOIN dbo.Course c ON c.courseID = sec.courseID
    JOIN dbo.Grade g ON g.enrollmentID = e.enrollmentID   
    WHERE e.studentID = @StudentID;

    RETURN ISNULL(@GPA,0);
END;




GO

CREATE OR ALTER FUNCTION dbo.fn_ActiveEnrollments (
    @SemesterID INT
)
RETURNS TABLE
AS
RETURN (
    SELECT
        s.studentID,
        s.firstName,
        s.lastName,
        c.courseCode,
        sec.sectionID
    FROM dbo.Enrollment e
    JOIN dbo.Student s ON s.studentID = e.studentID
    JOIN dbo.Section sec ON sec.sectionID = e.sectionID
    JOIN dbo.Course c ON c.courseID = sec.courseID
    WHERE sec.semesterID = @SemesterID
);

GO


GO
CREATE OR ALTER FUNCTION dbo.fn_TotalEarnedCredits (
    @StudentID INT
)
RETURNS INT
AS
BEGIN
    DECLARE @Credits INT;
    SELECT @Credits = ISNULL(SUM(c.credits), 0)         
    FROM dbo.Enrollment e
    JOIN dbo.Section sec ON sec.sectionID = e.sectionID
    JOIN dbo.Course c ON c.courseID = sec.courseID
    JOIN dbo.Grade g ON g.enrollmentID = e.enrollmentID
    WHERE e.studentID = @StudentID
        AND g.gradeValue IN ('A','B','C','D');
    RETURN @Credits;
END;
GO

CREATE OR ALTER FUNCTION dbo.fn_GetStudentBalance(@StudentName VARCHAR(120))
RETURNS DECIMAL(12,2)
AS
BEGIN
    DECLARE @StudentID INT, @Balance DECIMAL(12,2);

    SELECT @StudentID = studentID
    FROM Student
    WHERE CONCAT(firstName, ' ', lastName) = @StudentName;

    IF @StudentID IS NULL
        RETURN NULL;

    SELECT @Balance = balance
    FROM StudentAccount
    WHERE studentID = @StudentID;

    RETURN @Balance;
END;
GO

CREATE OR ALTER FUNCTION dbo.fn_CanEnroll(@StudentName VARCHAR(120), @RequiredAmount DECIMAL(10,2))
RETURNS BIT
AS
BEGIN
    DECLARE @Balance DECIMAL(12,2);

    SET @Balance = dbo.fn_GetStudentBalance(@StudentName);

    IF @Balance IS NULL OR @Balance < @RequiredAmount
        RETURN 0; -- Cannot enroll

    RETURN 1; -- Can enroll
END;
GO
