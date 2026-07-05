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


-- =============================================
--  CREATE SECURITY TABLES
-- =============================================
CREATE TABLE [Role] (
    roleID INT IDENTITY(1,1) PRIMARY KEY,
    roleName VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE [User] (
    userID INT IDENTITY(1,1) PRIMARY KEY,
    roleID INT NOT NULL,
    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(120) NOT NULL UNIQUE,
    passwordHash VARCHAR(255) NOT NULL,
    isActive BIT NOT NULL DEFAULT 1,
    createdAt DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME(),
    FOREIGN KEY (roleID) REFERENCES [Role](roleID)
);
GO

-- =============================================
--  ACADEMIC TABLES
-- =============================================
CREATE TABLE Department (
    departmentID INT IDENTITY(1,1) PRIMARY KEY,
    departmentName VARCHAR(100) NOT NULL UNIQUE,
    facultyName VARCHAR(100) NOT NULL
);

CREATE TABLE Program (
    programID INT IDENTITY(1,1) PRIMARY KEY,
    programName VARCHAR(100) NOT NULL,
    degreeLevel VARCHAR(50) NOT NULL CHECK (degreeLevel IN ('Bachelor','Master','PhD')),
    departmentID INT NOT NULL,
    CONSTRAINT fk_program_department FOREIGN KEY (departmentID) REFERENCES Department(departmentID)
);

CREATE TABLE Student (
    studentID INT IDENTITY(1,1) PRIMARY KEY,
    userID INT NOT NULL UNIQUE,
    firstName VARCHAR(60) NOT NULL,
    lastName VARCHAR(60) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    dateOfBirth DATE NOT NULL,
    admissionDate DATE NOT NULL,
    status VARCHAR(20) NOT NULL CHECK (status IN ('Active','Graduated','Suspended')),
    GPA DECIMAL(4,2) NULL,
    programID INT NOT NULL,
    CONSTRAINT fk_student_program FOREIGN KEY (programID) REFERENCES Program(programID),
    CONSTRAINT fk_student_user_id FOREIGN KEY (userID) REFERENCES [User](userID)
);

CREATE TABLE Instructor (
    instructorID INT IDENTITY(1,1) PRIMARY KEY,
    userID INT NOT NULL UNIQUE,
    fullName VARCHAR(120) NOT NULL,
    email VARCHAR(120) NOT NULL UNIQUE,
    departmentID INT NOT NULL,
    CONSTRAINT fk_instructor_department FOREIGN KEY (departmentID) REFERENCES Department(departmentID),
    CONSTRAINT fk_instructor_user_id FOREIGN KEY (userID) REFERENCES [User](userID)
);

CREATE TABLE Course (
    courseID INT IDENTITY(1,1) PRIMARY KEY,
    courseCode VARCHAR(20) NOT NULL UNIQUE,
    courseTitle VARCHAR(120) NOT NULL,
    credits INT NOT NULL CHECK (credits BETWEEN 1 AND 6),
    courseFee DECIMAL(12,2) NOT NULL DEFAULT 0,
    departmentID INT NOT NULL,
    CONSTRAINT fk_course_department FOREIGN KEY (departmentID) REFERENCES Department(departmentID)
);

CREATE TABLE Semester (
    semesterID INT IDENTITY(1,1) PRIMARY KEY,
    semesterName VARCHAR(50) NOT NULL UNIQUE,
    startDate DATE NOT NULL,
    endDate DATE NOT NULL,
    CONSTRAINT chk_semester_dates CHECK (endDate > startDate)
);

CREATE TABLE Section (
    sectionID INT IDENTITY(1,1) PRIMARY KEY,
    courseID INT NOT NULL,
    semesterID INT NOT NULL,
    instructorID INT NOT NULL,
    capacity INT NOT NULL CHECK (capacity > 0),
    created_by INT NULL,
    created_at DATETIME2 NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT fk_section_course FOREIGN KEY (courseID) REFERENCES Course(courseID),
    CONSTRAINT fk_section_semester FOREIGN KEY (semesterID) REFERENCES Semester(semesterID),
    CONSTRAINT fk_section_instructor FOREIGN KEY (instructorID) REFERENCES Instructor(instructorID)
);

CREATE TABLE Enrollment (
    enrollmentID INT IDENTITY(1,1) PRIMARY KEY,
    studentID INT NOT NULL,
    sectionID INT NOT NULL,
    enrollmentDate DATE NOT NULL DEFAULT GETDATE(),
    enrollment_status VARCHAR(20) NOT NULL DEFAULT 'ENROLLED',
    created_by INT NULL,
    created_at DATETIME2 NULL DEFAULT SYSUTCDATETIME(),
    updated_by INT NULL,
    updated_at DATETIME2 NULL,
    CONSTRAINT uq_student_section UNIQUE (studentID, sectionID),
    CONSTRAINT fk_enrollment_student FOREIGN KEY (studentID) REFERENCES Student(studentID),
    CONSTRAINT fk_enrollment_section FOREIGN KEY (sectionID) REFERENCES Section(sectionID)
);

CREATE TABLE Grade (
    gradeID INT IDENTITY(1,1) PRIMARY KEY,
    enrollmentID INT NOT NULL UNIQUE,
    gradeStatus VARCHAR(20) NOT NULL DEFAULT 'Draft',
    gradeValue CHAR(2) CHECK (gradeValue IN ('A','B','C','D','F')),
    created_by INT NULL,
    created_at DATETIME2 NULL DEFAULT SYSUTCDATETIME(),
    CONSTRAINT fk_grade_enrollment FOREIGN KEY (enrollmentID) REFERENCES Enrollment(enrollmentID)
);
GO

CREATE TABLE InstructorTimeEntry (
    entryID INT IDENTITY PRIMARY KEY,
    instructorID INT NOT NULL,
    sectionID INT NOT NULL,
    entryDate DATE NOT NULL,
    hoursWorked DECIMAL(4,2) NOT NULL CHECK (hoursWorked > 0),
    approved BIT DEFAULT 0,
    approved_by INT NULL,
    created_at DATETIME2 DEFAULT SYSUTCDATETIME(),

    FOREIGN KEY (instructorID) REFERENCES Instructor(instructorID),
    FOREIGN KEY (sectionID) REFERENCES Section(sectionID),
    FOREIGN KEY (approved_by) REFERENCES [User](userID)
);


CREATE TABLE InstructorSalary (
    salaryID INT IDENTITY PRIMARY KEY,
    instructorID INT NOT NULL UNIQUE,
    hourlyRate DECIMAL(10,2) NOT NULL,
    bankAccount VARCHAR(50),
    FOREIGN KEY (instructorID) REFERENCES Instructor(instructorID)
);

CREATE TABLE SalaryPayment (
    paymentID INT IDENTITY PRIMARY KEY,
    instructorID INT NOT NULL,
    periodStart DATE NOT NULL,
    periodEnd DATE NOT NULL,
    totalHours DECIMAL(6,2),
    amountPaid DECIMAL(12,2),
    paidOn DATETIME2,
    paidBy INT,
    FOREIGN KEY (instructorID) REFERENCES Instructor(instructorID),
    FOREIGN KEY (paidBy) REFERENCES [User](userID)
);


CREATE TABLE StudentAccount (
    studentID INT PRIMARY KEY,
    balance DECIMAL(12,2) NOT NULL DEFAULT 0,
    FOREIGN KEY (studentID) REFERENCES Student(studentID)
);

CREATE TABLE StudentPayment (
    paymentID INT IDENTITY PRIMARY KEY,
    studentID INT,
    amount DECIMAL(10,2),
    paymentDate DATETIME2 DEFAULT SYSUTCDATETIME(),
    description VARCHAR(200),
    processed_by INT,
    FOREIGN KEY (studentID) REFERENCES Student(studentID),
    FOREIGN KEY (processed_by) REFERENCES [User](userID)
);

CREATE TABLE InstructorPolicy (
    instructorID INT PRIMARY KEY,
    maxCredits INT NOT NULL DEFAULT 12,
    FOREIGN KEY (instructorID) REFERENCES Instructor(instructorID)
);
GO
