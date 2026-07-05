--SELECT IS_SRVROLEMEMBER('sysadmin');
--SELECT IS_ROLEMEMBER('db_owner');

-- Disconnect all users from the database

-- Switch to master so University is not in use



IF DB_ID('University_database3') IS NULL
    CREATE DATABASE University_database3;
GO

USE University_database3;
GO



/* =========================
   DROP CHILD TABLES FIRST
   ========================= */

DROP TABLE IF EXISTS Grade;
DROP TABLE IF EXISTS Enrollment;
DROP TABLE IF EXISTS InstructorTimeEntry;
DROP TABLE IF EXISTS SalaryPayment;
DROP TABLE IF EXISTS StudentPayment;
DROP TABLE IF EXISTS InstructorAssignmentHistory;

DROP TABLE IF EXISTS Section;
DROP TABLE IF EXISTS StudentAccount;
DROP TABLE IF EXISTS InstructorSalary;
DROP TABLE IF EXISTS InstructorPolicy;

DROP TABLE IF EXISTS Student;
DROP TABLE IF EXISTS Instructor;

DROP TABLE IF EXISTS Course;
DROP TABLE IF EXISTS Program;
DROP TABLE IF EXISTS Semester;

DROP TABLE IF EXISTS Department;

DROP TABLE IF EXISTS [User];
DROP TABLE IF EXISTS [Role];

GO
