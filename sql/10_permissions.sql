-- =============================================
-- SECURITY PERMISSIONS
-- =============================================
USE University_database3;
GO

-- Remove table access from PUBLIC (default)
DENY SELECT, INSERT, UPDATE, DELETE ON SCHEMA::dbo TO PUBLIC;
GO

-- Grant specific permissions to roles
-- ADMIN ROLE
GRANT EXECUTE ON dbo.usp_CreateUser TO role_admin;
GRANT EXECUTE ON dbo.usp_EnrollStudent TO role_admin;
GRANT EXECUTE ON dbo.DropStudentFromCourse TO role_admin;
GRANT EXECUTE ON dbo.AssignInstructorToSection TO role_admin;
GRANT EXECUTE ON dbo.usp_LockGrades TO role_admin;
GRANT EXECUTE ON dbo.usp_UnLockGrades TO role_admin;
GRANT EXECUTE ON dbo.usp_ApproveInstructorHours TO role_admin;
GRANT EXECUTE ON dbo.usp_RegisterStudentPayment TO role_admin;
GRANT EXECUTE ON dbo.GenerateInstructorPayroll TO role_admin;

-- FINANCE ROLE
GRANT EXECUTE ON dbo.usp_RegisterStudentPayment TO role_finance;
GRANT EXECUTE ON dbo.GenerateInstructorPayroll TO role_finance;

-- REGISTRAR ROLE
GRANT EXECUTE ON dbo.usp_EnrollStudent TO role_registrar;
GRANT EXECUTE ON dbo.DropStudentFromCourse TO role_registrar;

-- HOD ROLE
GRANT EXECUTE ON dbo.AssignInstructorToSection TO role_hod;
GRANT EXECUTE ON dbo.usp_LockGrades TO role_hod;
GRANT EXECUTE ON dbo.usp_UnLockGrades TO role_hod;
GRANT EXECUTE ON dbo.usp_ApproveInstructorHours TO role_hod;

-- INSTRUCTOR ROLE
GRANT EXECUTE ON dbo.usp_SetStudentGrade TO role_instructor;
GRANT EXECUTE ON dbo.usp_LogInstructorHours TO role_instructor;

-- STUDENT ROLE
GRANT EXECUTE ON dbo.usp_GetMyTranscript TO role_student;

-- VIEW PERMISSIONS
GRANT SELECT ON dbo.vw_StudentTranscript TO role_student, role_admin, role_registrar, role_hod;
GRANT SELECT ON dbo.vw_SectionCapacityStatus TO role_admin, role_registrar;
GRANT SELECT ON dbo.vw_InstructorTeachingLoad TO role_admin, role_hod, role_instructor;

-- FUNCTION PERMISSIONS
GRANT EXECUTE ON dbo.fn_GetStudentBalance TO role_finance;
GRANT SELECT ON dbo.fn_ActiveEnrollments TO role_registrar;
GRANT SELECT ON dbo.Instructor_assigned_sections TO role_instructor;
GRANT EXECUTE ON dbo.fn_CalculateGPA TO PUBLIC; -- GPA calculation is public
GRANT EXECUTE ON dbo.fn_TotalEarnedCredits TO PUBLIC; -- Credits calculation is public

PRINT 'Permissions assigned successfully.';
GO