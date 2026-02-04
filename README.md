# 🎓 University Management System

A complete database system for managing university operations - students, courses, grades, and finances.

> **Built with**: SQL Server, T-SQL, MongoDB  
> **Made by**: Aseel Menhem & Maryline Karam

---

## 📖 What is This?

This is a full university database that handles:
- 👨‍🎓 Student enrollment and grades
- 👨‍🏫 Instructor assignments and payroll
- 📚 Course management and scheduling
- 💰 Tuition payments and financial tracking
- 🔐 Role-based security (6 different user types)

Think of it as the backend system that powers a university's operations!

---

## ✨ What Makes It Special?

### Smart Enrollment System
When a student tries to enroll:
1. ✅ Checks if they have enough money
2. ✅ Checks if the class isn't full
3. ✅ Automatically deducts the course fee
4. ❌ Rejects if anything fails

### Automatic Grade Processing
When an instructor submits a grade:
1. 📝 Validates the grade (A, B, C, D, or F)
2. 🔒 Checks if grades are locked
3. 🧮 Automatically recalculates student's GPA
4. 📊 Updates transcript in real-time

### Payroll System
For instructor payments:
1. ⏰ Instructors log their work hours
2. ✅ Department head approves hours
3. 💵 System calculates payment (hours × rate)
4. 💰 Generates payroll automatically

---

## 🏗️ Database Structure

### Core Tables (15 Total)

**Security** 🔐
- `Role` - Defines 6 user roles
- `User` - All system users

**Academic** 📚
- `Department` - University departments
- `Program` - Degree programs (Bachelor, Master, PhD)
- `Student` - Student records with GPA
- `Instructor` - Instructor profiles
- `Course` - Course catalog
- `Semester` - Academic periods
- `Section` - Course sections per semester
- `Enrollment` - Student enrollments
- `Grade` - Grades and transcripts

**Financial** 💰
- `StudentAccount` - Student balances
- `StudentPayment` - Payment records
- `InstructorSalary` - Instructor pay rates
- `SalaryPayment` - Payroll history

### How They Connect

```
User → Student → Enrollment → Grade
              ↓
          Program
              ↓
         Department → Course → Section → Enrollment
                          ↓
                    Instructor → SalaryPayment
```

---

## 📊 Data Visualizations (MongoDB Charts)

We created interactive dashboards to visualize the data:

To support data-driven decision-making, several analytical dashboards were created using MongoDB Charts. These visualizations provide clear insights into the university's financial status, faculty workload, and course utilization, transforming raw operational data into meaningful management information.

Static snapshots of the charts are included below for documentation purposes, while the live dashboards allow real-time interaction during demonstrations.

### Student Tuition Collection Status

This visualization presents the financial status of student accounts by comparing paid balances against outstanding tuition fees, offering a quick overview of the university's cash flow.

**Key Insight:**  
The chart allows the finance office to immediately identify unpaid balances, assess financial exposure, and prioritize collection efforts, reducing institutional financial risk.

### Instructor Workload Analysis

This chart summarizes the total teaching hours logged by each instructor, based on approved time entries.

**Key Insight:**  
By visualizing workload distribution, department heads can ensure fairness, detect overload situations, and validate teaching hours before salary processing.

### Course Utilization (Capacity vs. Enrollment)

This visualization compares section capacity against actual student enrollment to evaluate how efficiently academic resources are being used.

**Key Insight:**  
The chart highlights underutilized sections and fully booked classes, supporting better planning of future course offerings and classroom allocation.

📎 All visualization images and supporting diagrams are available in the project documentation attachments.

---

## 🚀 Getting Started

### Prerequisites
- SQL Server 2019 or later
- SQL Server Management Studio (SSMS)
- (Optional) MongoDB for visualizations

### Quick Setup

**Step 1: Run the SQL scripts in order**
```sql
-- Open SSMS and run these files:
1. sql/01_initialization.sql  -- Creates database
2. sql/02_tables.sql          -- Creates tables
3. sql/03_security.sql        -- Sets up users and roles
4. sql/04_views.sql           -- Creates views
5. sql/05_functions.sql       -- Creates functions
6. sql/06_procedures.sql      -- Creates stored procedures
7. sql/07_triggers.sql        -- Creates triggers
8. sql/08_sample_data.sql     -- Loads test data
```

**Step 2: Verify it works**
```sql
-- Run test scripts
:r sql/09_test_scripts.sql

-- Check if data loaded
SELECT * FROM Student;
SELECT * FROM Course;
SELECT * FROM Enrollment;
```

**Done!** ✅ Your database is ready.

---

## 🎮 How to Use It

### Example 1: Enroll a Student

```sql
-- First, make sure student has money
EXEC usp_RegisterStudentPayment 
    @StudentFullName = 'John Doe',
    @Amount = 2000,
    @ProcessedByUserID = 1;

-- Check balance
SELECT dbo.fn_GetStudentBalance('John Doe');

-- Enroll in course
EXEC usp_EnrollStudent 
    @StudentName = 'John Doe',
    @CourseCode = 'CE301',
    @SemesterName = 'Fall 2024';
```

**What happens behind the scenes:**
1. System checks balance ≥ course fee ($1,500)
2. System checks section has space
3. Enrollment is created
4. $1,500 is deducted from balance

---

### Example 2: Submit a Grade

```sql
-- Instructor submits grade
EXEC usp_SetStudentGrade
    @InstructorID = 3,           -- Dr. Maya Saad
    @StudentID = 1,              -- John Doe
    @SemesterName = 'Fall 2024',
    @CourseCode = 'CE301',
    @GradeValue = 'A';
```

**What happens behind the scenes:**
1. Verifies instructor teaches this course
2. Checks grade isn't locked
3. Saves grade
4. **Automatically recalculates student's GPA!**

---

### Example 3: View Transcript

```sql
-- Student logs in to see grades
EXEC usp_GetMyTranscript
    @username = 'john.doe',
    @password = 'hashed_password';
```

**Returns:**
- Student info and current GPA
- All courses taken
- Grades received
- Total credits earned

---

## 🔒 Security System

We have **6 different user roles**, each with specific permissions:

| Role | What They Can Do |
|------|------------------|
| 👨‍🎓 **Student** | View own transcript, request enrollment |
| 👨‍🏫 **Instructor** | Submit grades, view assigned classes, log work hours |
| 📝 **Registrar** | Enroll/drop students, view section capacity |
| 👔 **Admin** | Create users, lock/unlock grades, manage everything |
| 🏛️ **Head of Department** | Assign instructors, approve teaching loads |
| 💰 **Finance Officer** | Process payments, generate payroll |

### How Security Works

```sql
-- Students can ONLY see their own data
GRANT EXECUTE ON usp_GetMyTranscript TO role_student;

-- Instructors can ONLY grade their own classes
GRANT EXECUTE ON usp_SetStudentGrade TO role_instructor;

-- Finance handles money
GRANT EXECUTE ON usp_RegisterStudentPayment TO role_finance;
GRANT EXECUTE ON GenerateInstructorPayroll TO role_finance;
```

No one can access tables directly - everything goes through controlled procedures!

---

## 🤖 Automated Features

### 1. Automatic GPA Calculation
When any grade changes:
- Trigger fires automatically
- Recalculates weighted average
- Updates student's GPA
- No manual calculation needed!

### 2. Capacity Enforcement
When enrolling a student:
- Trigger checks current enrollment count
- Compares to section capacity
- **Rejects** if class is full
- Prevents overbooking!

### 3. Account Creation
When creating a new student user:
- Trigger automatically creates Student record
- Trigger automatically creates StudentAccount
- Starts with $0 balance
- Ready to go!

### 4. Balance Updates
When processing a payment:
- Trigger automatically updates balance
- No manual balance tracking
- Always accurate!

---

## 📊 The Numbers

What's inside:

- **15 Tables** with proper relationships
- **10 Stored Procedures** for business logic
- **6 Functions** for calculations
- **5 Triggers** for automation
- **3 Views** for reporting
- **6 User Roles** with security
- **2,500+ lines** of SQL code
- **100% compatibility** between design and code

---

## 🗂️ Project Files

```
university-management-system/
├── sql/                          ← All SQL code
│   ├── 01_initialization.sql     ← Start here
│   ├── 02_tables.sql
│   ├── 03_security.sql
│   ├── 04_views.sql
│   ├── 05_functions.sql
│   ├── 06_procedures.sql
│   ├── 07_triggers.sql
│   ├── 08_sample_data.sql
│   └── 09_test_scripts.sql       ← Test everything
│
├── mongodb/                      ← NoSQL version
│   └── university_management_playground.mongodb.js
│
└── docs/
    ├── charts/
    │   ├── student_tuition_collection.png
    │   ├── instructor_workload_analysis.png
    │   ├── course_utilization.png
    ├── ERD_diag_UMS.png          ← Database ERD
    ├── USE_CASE_UMS.png          ← Use Case Diagram
    └── Presentation_Slides.pdf   ← Project Presentation
```

---

## 🎯 Key Features Explained

### Smart Enrollment

**Problem**: Students enrolling without enough money, or in full classes.

**Our Solution**:
```sql
-- Check 1: Financial validation
IF dbo.fn_CanEnroll(@StudentName, @CourseFee) = 0
    THROW 50005, 'Insufficient balance';

-- Check 2: Capacity validation (via trigger)
IF enrollment_count > capacity
    ROLLBACK;
    
-- If both pass: Enroll and deduct fee
INSERT INTO Enrollment...
UPDATE StudentAccount SET balance = balance - @CourseFee;
```

Result: Only qualified students get enrolled ✅

---

### Grade Protection

**Problem**: Accidentally changing final grades after semester ends.

**Our Solution**:
```sql
-- Grades start as 'Draft'
INSERT INTO Grade (gradeStatus) VALUES ('Draft');

-- Admin locks grades when semester ends
EXEC usp_LockGrades @SectionID = 1;

-- Now instructors CAN'T modify them
IF gradeStatus = 'Locked'
    THROW 50022, 'Cannot modify locked grade';
```

Result: Final grades are protected 🔒

---

### Teaching Load Management

**Problem**: Instructors getting assigned too many courses.

**Our Solution**:
```sql
-- Each instructor has a limit (default: 12 credits)
INSERT INTO InstructorPolicy (maxCredits) VALUES (12);

-- When assigning, check current load
IF (@CurrentLoad + @NewCourseCredits) > @MaxLoad
    THROW 60001, 'Teaching load exceeded';
```

Result: Balanced workload for all instructors ⚖️

---

## 🍃 MongoDB Integration

We also built this system in **MongoDB** (NoSQL) to compare approaches!

### SQL vs MongoDB

**SQL (What we use):**
- Structured tables with relationships
- Strong data integrity
- Perfect for transactional data
- ACID guarantees

**MongoDB (For analytics):**
- Flexible documents
- Embedded data
- Fast analytics queries
- Great for reporting

### MongoDB Charts Dashboard

We created 3 interactive visualizations:

1. **Financial Status** - Who paid, who owes money
2. **Instructor Workload** - Hours worked by instructor
3. **Course Utilization** - Full vs. empty classes

You can explore the MongoDB playground at: `mongodb/university_management_playground.mongodb.js`

---

## 🎓 What We Learned

### Database Design
- How to normalize data properly
- When to denormalize for performance
- Importance of foreign keys and constraints

### Business Logic
- Implementing real-world rules in code
- Transaction management (ACID)
- Error handling and validation

### Security
- Role-based access control
- Principle of least privilege
- Why direct table access is dangerous

### Automation
- Triggers for automatic updates
- Stored procedures for complex logic
- Functions for reusable calculations

---

## 🛠️ Technical Details

### Technologies Used
- **Database**: SQL Server 2019
- **Language**: T-SQL
- **Analytics**: MongoDB
- **Version Control**: Git/GitHub
- **Documentation**: Markdown

### Design Patterns
- Three-tier architecture
- Repository pattern (via stored procedures)
- Trigger-based automation
- Role-based security

### Best Practices Followed
- ✅ Normalized database design
- ✅ Comprehensive constraints
- ✅ Transaction management
- ✅ Error handling
- ✅ Code documentation
- ✅ Security by default

---

## 🧪 Testing

We included test data for:
- **5 Students** (Aseel, Maryline, Maryam, Nour, Karim)
- **3 Instructors** (Dr. Hassan, Dr. Rami, Dr. Maya)
- **4 Courses** (CE301, CE410, EE320, CV220)
- **3 Semesters** (Fall 2024, Spring 2025, Fall 2025)

Run `sql/09_test_scripts.sql` to test:
- ✅ Student enrollment
- ✅ Payment processing
- ✅ Grade submission
- ✅ Payroll generation
- ✅ Transcript generation
- ✅ Capacity enforcement
- ✅ Teaching load validation

---

## 🚧 Future Enhancements

Ideas for v2.0:
- [ ] Course prerequisites system
- [ ] Waitlist functionality
- [ ] Email notifications
- [ ] Degree audit (graduation checker)
- [ ] Mobile app
- [ ] REST API
- [ ] Web dashboard
- [ ] Advanced analytics

---

## 📝 Documentation

Full documentation available:
- **Presentation** - slides explaining everything
- **ERD Diagram** - Visual database structure
- **Use Case Diagram** - 6 user roles and their actions
- **Compatibility Report** - Verification that design matches code

---

## 🤝 Contributing

Want to improve this project?

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/awesome`)
3. Commit your changes (`git commit -m 'Add awesome feature'`)
4. Push to the branch (`git push origin feature/awesome`)
5. Open a Pull Request

---

## 👥 Authors

**Aseel Menhem** - SQL Implementation & Database Development
**Maryline Karam** - Database Design, Documentation, MongoDB Integration, Publications
---

## 🙏 Acknowledgments

- SQL Server documentation
- MongoDB documentation  
- Database design best practices
- Our instructor Eng Mohammad Aoude

---
