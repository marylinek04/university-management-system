-- =============================================
-- VIEWS
-- =============================================
USE University_database3;
GO

GO

CREATE OR ALTER VIEW dbo.vw_StudentTranscript
WITH SCHEMABINDING
AS
SELECT
    s.userID,
    s.studentID,
    s.firstName,
    s.lastName,
    c.courseCode,
    c.courseTitle,
    sec.instructorID,
    sem.semesterName,
    g.gradeValue,
    c.credits,
    g.gradeStatus
    
    
FROM dbo.Student s
JOIN dbo.Enrollment e ON e.studentID = s.studentID
JOIN dbo.Section sec ON sec.sectionID = e.sectionID
JOIN dbo.Course c ON c.courseID = sec.courseID
JOIN dbo.Semester sem ON sem.semesterID = sec.semesterID
LEFT JOIN dbo.Grade g ON g.enrollmentID = e.enrollmentID
GO



GO
CREATE OR ALTER VIEW dbo.vw_SectionCapacityStatus
WITH SCHEMABINDING
AS
SELECT
    sec.sectionID,
    c.courseCode,
    sem.semesterName,
    sec.capacity,
    COUNT(e.enrollmentID) AS enrolled_count,
    sec.capacity - COUNT(e.enrollmentID) AS remaining_seats
FROM dbo.Section sec
JOIN dbo.Course c ON c.courseID = sec.courseID
JOIN dbo.Semester sem ON sem.semesterID = sec.semesterID
LEFT JOIN dbo.Enrollment e ON e.sectionID = sec.sectionID
GROUP BY sec.sectionID, c.courseCode, sem.semesterName, sec.capacity;

GO


CREATE OR ALTER VIEW dbo.vw_InstructorTeachingLoad
WITH SCHEMABINDING
AS
SELECT
    i.instructorID,
    i.fullName,
    sem.semesterName,
    COUNT(sec.sectionID) AS sections_assigned,
    SUM(c.credits) AS total_credits
FROM dbo.Instructor i
JOIN dbo.Section sec ON sec.instructorID = i.instructorID
JOIN dbo.Course c ON c.courseID = sec.courseID
JOIN dbo.Semester sem ON sem.semesterID = sec.semesterID
GROUP BY i.instructorID, i.fullName, sem.semesterName;
GO
