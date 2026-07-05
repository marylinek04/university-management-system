-- =============================================
-- ROLES, LOGINS, AND USERS
-- =============================================
-- Database roles
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'role_student')
    CREATE ROLE role_student;

IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'role_instructor')
    CREATE ROLE role_instructor;

IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'role_admin')
    CREATE ROLE role_admin;
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'role_finance')
    CREATE ROLE role_finance;

IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'role_registrar')
    CREATE ROLE role_registrar;

IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'role_hod')
    CREATE ROLE role_hod;



GO

-- Logins
IF EXISTS (SELECT * FROM sys.sql_logins WHERE name = 'studentLogin')
    DROP LOGIN studentLogin;
CREATE LOGIN studentLogin WITH PASSWORD = 'Pass1';

IF EXISTS (SELECT * FROM sys.sql_logins WHERE name = 'instructorLogin')
    DROP LOGIN instructorLogin;
CREATE LOGIN instructorLogin WITH PASSWORD = 'Pass2';

IF EXISTS (SELECT * FROM sys.sql_logins WHERE name = 'adminLogin')
    DROP LOGIN adminLogin;
CREATE LOGIN adminLogin WITH PASSWORD = 'Pass3!';

IF EXISTS (SELECT * FROM sys.sql_logins WHERE name = 'hodLogin')
    DROP LOGIN hodLogin;
CREATE LOGIN hodLogin WITH PASSWORD = 'Pass4';

IF EXISTS (SELECT * FROM sys.sql_logins WHERE name = 'registrarLogin')
    DROP LOGIN registrarLogin;
CREATE LOGIN registrarLogin WITH PASSWORD = 'Pass5';

IF EXISTS (SELECT * FROM sys.sql_logins WHERE name = 'financeLogin')
    DROP LOGIN financeLogin;
CREATE LOGIN financeLogin WITH PASSWORD = 'Pass6';
GO


-- Database users
IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'studentUser')
    CREATE USER studentUser FOR LOGIN studentLogin;

IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'instructorUser')
    CREATE USER instructorUser FOR LOGIN instructorLogin;

IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'adminUser')
    CREATE USER adminUser FOR LOGIN adminLogin;

IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'financeUser')
    CREATE USER financeUser FOR LOGIN financeLogin;

IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'registrarUser')
    CREATE USER registrarUser FOR LOGIN registrarLogin;

IF NOT EXISTS (SELECT * FROM sys.database_principals WHERE name = 'hodUser')
    CREATE USER hodUser FOR LOGIN hodLogin;



-- Assign roles
ALTER ROLE role_student ADD MEMBER studentUser;
ALTER ROLE role_instructor ADD MEMBER instructorUser;
ALTER ROLE role_admin ADD MEMBER adminUser;
ALTER ROLE role_hod ADD MEMBER hodUser;
ALTER ROLE role_finance ADD MEMBER financeUser;
ALTER ROLE role_registrar ADD MEMBER registrarUser;
GO

-- Give db_owner to your admin user for setup only (optional)
ALTER ROLE db_owner ADD MEMBER adminUser;
GO
