// MongoDB Playground for University Management System
// This playground demonstrates how SQL Server data could be represented in MongoDB
// and provides visualization queries for analytics

// Select the database to use.
use('university_management_db');

// ============================================
// COLLECTION SCHEMAS (Document-Based)
// ============================================

// Drop existing collections for fresh start
db.departments.drop();
db.programs.drop();
db.students.drop();
db.instructors.drop();
db.courses.drop();
db.semesters.drop();
db.sections.drop();
db.enrollments.drop();
db.grades.drop();
db.student_payments.drop();
db.instructor_salaries.drop();

// ============================================
// 1. DEPARTMENTS COLLECTION
// ============================================
db.departments.insertMany([
  {
    _id: 1,
    departmentName: "Electrical Engineering",
    facultyName: "Faculty of Engineering",
    head: null,
    createdAt: new Date()
  },
  {
    _id: 2,
    departmentName: "Mechanical Engineering",
    facultyName: "Faculty of Engineering",
    head: null,
    createdAt: new Date()
  },
  {
    _id: 3,
    departmentName: "Computer Engineering",
    facultyName: "Faculty of Engineering",
    head: null,
    createdAt: new Date()
  },
  {
    _id: 4,
    departmentName: "Civil Engineering",
    facultyName: "Faculty of Engineering",
    head: null,
    createdAt: new Date()
  }
]);

// ============================================
// 2. PROGRAMS COLLECTION
// ============================================
db.programs.insertMany([
  {
    _id: 1,
    programName: "Computer Engineering Program",
    degreeLevel: "Bachelor",
    departmentId: 3,
    requiredCredits: 120,
    duration: "4 years"
  },
  {
    _id: 2,
    programName: "Electrical Power Systems",
    degreeLevel: "Master",
    departmentId: 1,
    requiredCredits: 60,
    duration: "2 years"
  },
  {
    _id: 3,
    programName: "Mechanical Design",
    degreeLevel: "Bachelor",
    departmentId: 2,
    requiredCredits: 120,
    duration: "4 years"
  },
  {
    _id: 4,
    programName: "Civil Infrastructure",
    degreeLevel: "Bachelor",
    departmentId: 4,
    requiredCredits: 120,
    duration: "4 years"
  },
  {
    _id: 5,
    programName: "Embedded Systems",
    degreeLevel: "Master",
    departmentId: 3,
    requiredCredits: 60,
    duration: "2 years"
  }
]);

// ============================================
// 3. STUDENTS COLLECTION (Embedded Document Pattern)
// ============================================
db.students.insertMany([
  {
    _id: 1,
    firstName: "Aseel",
    lastName: "Menhem",
    email: "aseel.student@uni.edu",
    dateOfBirth: new Date("2002-05-15"),
    admissionDate: new Date("2024-09-01"),
    status: "Active",
    programId: 1,
    GPA: 3.75,
    account: {
      balance: 500,
      totalPaid: 4000,
      payments: [
        {
          amount: 4000,
          date: new Date("2024-08-25"),
          description: "Initial payment",
          processedBy: "Finance Officer"
        }
      ]
    },
    enrollments: [
      {
        courseCode: "CE301",
        semesterName: "Fall 2024",
        enrollmentDate: new Date("2024-09-05"),
        status: "ENROLLED",
        grade: {
          value: "A",
          status: "Locked",
          submittedAt: new Date("2024-12-15")
        }
      },
      {
        courseCode: "CE410",
        semesterName: "Spring 2025",
        enrollmentDate: new Date("2024-09-05"),
        status: "ENROLLED",
        grade: {
          value: "A",
          status: "Draft",
          submittedAt: new Date("2025-05-20")
        }
      }
    ],
    createdAt: new Date("2024-08-20")
  },
  {
    _id: 2,
    firstName: "Maryline",
    lastName: "Karam",
    email: "maryline.student@uni.edu",
    dateOfBirth: new Date("2001-11-20"),
    admissionDate: new Date("2024-09-01"),
    status: "Active",
    programId: 1,
    GPA: 3.33,
    account: {
      balance: -1200,
      totalPaid: 2000,
      payments: [
        {
          amount: 2000,
          date: new Date("2024-08-25"),
          description: "Initial payment",
          processedBy: "Finance Officer"
        }
      ]
    },
    enrollments: [
      {
        courseCode: "CE301",
        semesterName: "Fall 2024",
        enrollmentDate: new Date("2024-09-05"),
        status: "ENROLLED",
        grade: null
      },
      {
        courseCode: "EE320",
        semesterName: "Spring 2025",
        enrollmentDate: new Date("2024-09-05"),
        status: "ENROLLED",
        grade: {
          value: "B",
          status: "Draft"
        }
      }
    ],
    createdAt: new Date("2024-08-20")
  },
  {
    _id: 3,
    firstName: "Maryam",
    lastName: "Daaibes",
    email: "maryam.student@uni.edu",
    dateOfBirth: new Date("2002-03-10"),
    admissionDate: new Date("2024-09-01"),
    status: "Active",
    programId: 2,
    GPA: 4.0,
    account: {
      balance: 600,
      totalPaid: 2000,
      payments: []
    },
    enrollments: [
      {
        courseCode: "CV220",
        semesterName: "Fall 2025",
        enrollmentDate: new Date("2024-09-05"),
        status: "ENROLLED",
        grade: {
          value: "A",
          status: "Draft"
        }
      }
    ],
    createdAt: new Date("2024-08-20")
  }
]);

// ============================================
// 4. INSTRUCTORS COLLECTION
// ============================================
db.instructors.insertMany([
  {
    _id: 1,
    fullName: "Dr. Hassan Nasser",
    email: "hassan.nasser@uni.edu",
    departmentId: 1,
    salary: {
      hourlyRate: 50,
      bankAccount: "ACC001"
    },
    policy: {
      maxCredits: 12
    },
    timeEntries: [
      {
        sectionId: 2,
        date: new Date("2024-09-11"),
        hoursWorked: 4,
        approved: true,
        approvedBy: "HOD"
      },
      {
        sectionId: 2,
        date: new Date("2024-09-13"),
        hoursWorked: 3,
        approved: true,
        approvedBy: "HOD"
      }
    ],
    teachingLoad: {
      "Fall 2024": {
        sections: 1,
        totalCredits: 4
      }
    },
    createdAt: new Date("2024-08-15")
  },
  {
    _id: 2,
    fullName: "Dr. Rami Fakhoury",
    email: "rami.fakhoury@uni.edu",
    departmentId: 2,
    salary: {
      hourlyRate: 60,
      bankAccount: "ACC002"
    },
    policy: {
      maxCredits: 12
    },
    timeEntries: [
      {
        sectionId: 3,
        date: new Date("2024-09-15"),
        hoursWorked: 5,
        approved: true,
        approvedBy: "HOD"
      }
    ],
    teachingLoad: {
      "Fall 2024": {
        sections: 1,
        totalCredits: 3
      }
    },
    createdAt: new Date("2024-08-15")
  },
  {
    _id: 3,
    fullName: "Dr. Maya Saad",
    email: "maya.saad@uni.edu",
    departmentId: 3,
    salary: {
      hourlyRate: 55,
      bankAccount: "ACC003"
    },
    policy: {
      maxCredits: 10
    },
    timeEntries: [
      {
        sectionId: 1,
        date: new Date("2024-09-10"),
        hoursWorked: 3,
        approved: true,
        approvedBy: "HOD"
      },
      {
        sectionId: 1,
        date: new Date("2024-09-12"),
        hoursWorked: 2,
        approved: true,
        approvedBy: "HOD"
      }
    ],
    teachingLoad: {
      "Fall 2024": {
        sections: 1,
        totalCredits: 3
      },
      "Spring 2025": {
        sections: 1,
        totalCredits: 4
      }
    },
    createdAt: new Date("2024-08-15")
  }
]);

// ============================================
// 5. COURSES COLLECTION
// ============================================
db.courses.insertMany([
  {
    _id: 1,
    courseCode: "CE301",
    courseTitle: "Data Structures",
    credits: 3,
    courseFee: 1500,
    departmentId: 3,
    description: "Introduction to data structures and algorithms",
    prerequisites: []
  },
  {
    _id: 2,
    courseCode: "CE410",
    courseTitle: "Operating Systems",
    credits: 4,
    courseFee: 1800,
    departmentId: 3,
    description: "Operating system concepts and implementation",
    prerequisites: ["CE301"]
  },
  {
    _id: 3,
    courseCode: "EE320",
    courseTitle: "Electrical Machines",
    credits: 3,
    courseFee: 1600,
    departmentId: 1,
    description: "Theory and operation of electrical machines",
    prerequisites: []
  },
  {
    _id: 4,
    courseCode: "CV220",
    courseTitle: "Structural Analysis",
    credits: 3,
    courseFee: 1400,
    departmentId: 4,
    description: "Analysis of structural systems",
    prerequisites: []
  }
]);

// ============================================
// 6. SEMESTERS COLLECTION
// ============================================
db.semesters.insertMany([
  {
    _id: 1,
    semesterName: "Fall 2024",
    startDate: new Date("2024-09-01"),
    endDate: new Date("2024-12-20"),
    status: "Active"
  },
  {
    _id: 2,
    semesterName: "Spring 2025",
    startDate: new Date("2025-02-01"),
    endDate: new Date("2025-06-01"),
    status: "Upcoming"
  },
  {
    _id: 3,
    semesterName: "Fall 2025",
    startDate: new Date("2025-07-01"),
    endDate: new Date("2025-08-31"),
    status: "Upcoming"
  }
]);

// ============================================
// 7. SECTIONS COLLECTION (Denormalized)
// ============================================
db.sections.insertMany([
  {
    _id: 1,
    courseId: 1,
    courseCode: "CE301",
    courseTitle: "Data Structures",
    semesterId: 1,
    semesterName: "Fall 2024",
    instructorId: 3,
    instructorName: "Dr. Maya Saad",
    capacity: 2,
    enrolled: 2,
    remainingSeats: 0,
    students: [
      { studentId: 1, name: "Aseel Menhem" },
      { studentId: 2, name: "Maryline Karam" }
    ]
  },
  {
    _id: 2,
    courseId: 3,
    courseCode: "EE320",
    courseTitle: "Electrical Machines",
    semesterId: 2,
    semesterName: "Spring 2025",
    instructorId: 1,
    instructorName: "Dr. Hassan Nasser",
    capacity: 30,
    enrolled: 1,
    remainingSeats: 29,
    students: [
      { studentId: 2, name: "Maryline Karam" }
    ]
  },
  {
    _id: 3,
    courseId: 4,
    courseCode: "CV220",
    courseTitle: "Structural Analysis",
    semesterId: 3,
    semesterName: "Fall 2025",
    instructorId: 2,
    instructorName: "Dr. Rami Fakhoury",
    capacity: 40,
    enrolled: 1,
    remainingSeats: 39,
    students: [
      { studentId: 3, name: "Maryam Daaibes" }
    ]
  }
]);

// ============================================
// ANALYTICS & VISUALIZATION QUERIES
// ============================================

print("\n========================================");
print("1. STUDENT ENROLLMENT STATISTICS");
print("========================================\n");

db.students.aggregate([
  {
    $project: {
      fullName: { $concat: ["$firstName", " ", "$lastName"] },
      status: 1,
      GPA: 1,
      enrollmentCount: { $size: "$enrollments" },
      accountBalance: "$account.balance"
    }
  },
  {
    $sort: { GPA: -1 }
  }
]).forEach(printjson);

print("\n========================================");
print("2. COURSE POPULARITY (BY ENROLLMENT)");
print("========================================\n");

db.sections.aggregate([
  {
    $group: {
      _id: "$courseCode",
      courseTitle: { $first: "$courseTitle" },
      totalSections: { $sum: 1 },
      totalEnrolled: { $sum: "$enrolled" },
      totalCapacity: { $sum: "$capacity" },
      utilizationRate: {
        $avg: {
          $multiply: [
            { $divide: ["$enrolled", "$capacity"] },
            100
          ]
        }
      }
    }
  },
  {
    $sort: { totalEnrolled: -1 }
  }
]).forEach(printjson);

print("\n========================================");
print("3. INSTRUCTOR WORKLOAD ANALYSIS");
print("========================================\n");

db.instructors.aggregate([
  {
    $project: {
      fullName: 1,
      "salary.hourlyRate": 1,
      totalTimeEntries: { $size: "$timeEntries" },
      totalHoursWorked: { $sum: "$timeEntries.hoursWorked" },
      approvedHours: {
        $sum: {
          $map: {
            input: {
              $filter: {
                input: "$timeEntries",
                cond: { $eq: ["$$this.approved", true] }
              }
            },
            in: "$$this.hoursWorked"
          }
        }
      },
      estimatedEarnings: {
        $multiply: [
          {
            $sum: {
              $map: {
                input: {
                  $filter: {
                    input: "$timeEntries",
                    cond: { $eq: ["$$this.approved", true] }
                  }
                },
                in: "$$this.hoursWorked"
              }
            }
          },
          "$salary.hourlyRate"
        ]
      }
    }
  },
  {
    $sort: { totalHoursWorked: -1 }
  }
]).forEach(printjson);

print("\n========================================");
print("4. DEPARTMENT STATISTICS");
print("========================================\n");

db.departments.aggregate([
  {
    $lookup: {
      from: "instructors",
      localField: "_id",
      foreignField: "departmentId",
      as: "instructors"
    }
  },
  {
    $lookup: {
      from: "courses",
      localField: "_id",
      foreignField: "departmentId",
      as: "courses"
    }
  },
  {
    $project: {
      departmentName: 1,
      facultyName: 1,
      totalInstructors: { $size: "$instructors" },
      totalCourses: { $size: "$courses" },
      avgInstructorRate: { $avg: "$instructors.salary.hourlyRate" }
    }
  }
]).forEach(printjson);

print("\n========================================");
print("5. FINANCIAL OVERVIEW");
print("========================================\n");

db.students.aggregate([
  {
    $group: {
      _id: null,
      totalStudents: { $sum: 1 },
      totalRevenue: { $sum: "$account.totalPaid" },
      totalOutstanding: {
        $sum: {
          $cond: [
            { $lt: ["$account.balance", 0] },
            { $abs: "$account.balance" },
            0
          ]
        }
      },
      avgBalance: { $avg: "$account.balance" }
    }
  }
]).forEach(printjson);

print("\n========================================");
print("6. GRADE DISTRIBUTION");
print("========================================\n");

db.students.aggregate([
  {
    $unwind: "$enrollments"
  },
  {
    $match: {
      "enrollments.grade.value": { $exists: true }
    }
  },
  {
    $group: {
      _id: "$enrollments.grade.value",
      count: { $sum: 1 }
    }
  },
  {
    $sort: { _id: 1 }
  }
]).forEach(printjson);

print("\n========================================");
print("7. SECTION CAPACITY REPORT");
print("========================================\n");

db.sections.aggregate([
  {
    $project: {
      courseCode: 1,
      semesterName: 1,
      instructorName: 1,
      capacity: 1,
      enrolled: 1,
      remainingSeats: 1,
      utilizationPercentage: {
        $multiply: [
          { $divide: ["$enrolled", "$capacity"] },
          100
        ]
      },
      status: {
        $cond: {
          if: { $gte: ["$enrolled", "$capacity"] },
          then: "FULL",
          else: {
            $cond: {
              if: { $gte: [{ $divide: ["$enrolled", "$capacity"] }, 0.8] },
              then: "NEARLY FULL",
              else: "AVAILABLE"
            }
          }
        }
      }
    }
  },
  {
    $sort: { utilizationPercentage: -1 }
  }
]).forEach(printjson);

print("\n========================================");
print("8. STUDENTS BY PROGRAM");
print("========================================\n");

db.students.aggregate([
  {
    $lookup: {
      from: "programs",
      localField: "programId",
      foreignField: "_id",
      as: "program"
    }
  },
  {
    $unwind: "$program"
  },
  {
    $group: {
      _id: "$program.programName",
      degreeLevel: { $first: "$program.degreeLevel" },
      studentCount: { $sum: 1 },
      avgGPA: { $avg: "$GPA" },
      students: {
        $push: {
          name: { $concat: ["$firstName", " ", "$lastName"] },
          GPA: "$GPA"
        }
      }
    }
  },
  {
    $sort: { studentCount: -1 }
  }
]).forEach(printjson);

print("\n========================================");
print("9. ENROLLMENT TRENDS BY SEMESTER");
print("========================================\n");

db.sections.aggregate([
  {
    $group: {
      _id: "$semesterName",
      totalSections: { $sum: 1 },
      totalEnrollments: { $sum: "$enrolled" },
      avgClassSize: { $avg: "$enrolled" },
      totalCapacity: { $sum: "$capacity" }
    }
  },
  {
    $sort: { _id: 1 }
  }
]).forEach(printjson);

print("\n========================================");
print("10. TOP PERFORMING STUDENTS");
print("========================================\n");

db.students.aggregate([
  {
    $match: {
      GPA: { $gt: 0 }
    }
  },
  {
    $project: {
      fullName: { $concat: ["$firstName", " ", "$lastName"] },
      GPA: 1,
      totalEnrollments: { $size: "$enrollments" },
      completedCourses: {
        $size: {
          $filter: {
            input: "$enrollments",
            cond: { $ne: ["$$this.grade", null] }
          }
        }
      }
    }
  },
  {
    $sort: { GPA: -1 }
  },
  {
    $limit: 5
  }
]).forEach(printjson);

print("\n========================================");
print("MONGODB VISUALIZATION COMPLETE!");
print("========================================\n");
print("This playground demonstrates:");
print("1. Document-based schema design");
print("2. Embedded documents (students.enrollments)");
print("3. Denormalization for performance");
print("4. Aggregation pipelines for analytics");
print("5. Real-time reporting queries");
print("\nYou can connect this to MongoDB Charts");
print("or use MongoDB Compass for visual exploration!");
print("========================================\n");
