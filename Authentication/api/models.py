from . import db
import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import foreign

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin', 'student', 'lecturer', name='user_roles'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    # one-to-one relations
    student = db.relationship('Student', uselist=False, back_populates='user', cascade='all, delete')
    lecturer = db.relationship('Lecturer', uselist=False, back_populates='user', cascade='all, delete')

    def to_dict(self):
        return {
            'id': self.id,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }

    def __repr__(self):
        return f"<User {self.email}>"
    
# association table
student_courses = db.Table(
    'student_courses',
    db.Column('student_id', db.String(36),
              db.ForeignKey('students.id', ondelete='CASCADE'),
              primary_key=True),
    db.Column('course_id', db.String(36),
              db.ForeignKey('courses.id', ondelete='CASCADE'),
              primary_key=True),
)

class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.String(36), primary_key=True,
                   default=lambda: str(uuid.uuid4()))
    user_id = db.Column(
        db.String(36),
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        unique=True
    )
    reg_number   = db.Column(db.String(30), unique=True, nullable=False)
    year_of_study = db.Column(db.SmallInteger, nullable=False)
    semester      = db.Column(db.SmallInteger, nullable=False)
    firstname     = db.Column(db.String(50), nullable=False)
    surname       = db.Column(db.String(50), nullable=False)
    othernames    = db.Column(db.String(50))

    courses = db.relationship(
        'Course',
        secondary=student_courses,
        back_populates='students',
        lazy='joined'
    )

    user = db.relationship('User', back_populates='student')

    @property
    def units(self):
        """
        Flatten out all units for all enrolled courses,
        then filter by year_of_study & semester.
        """
        units = []
        for course in self.courses:
            units.extend(
                u for u in course.units
                if u.level == self.year_of_study and u.semester == self.semester
            )
        return units

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'reg_number': self.reg_number,
            'year_of_study': self.year_of_study,
            'semester': self.semester,
            'firstname': self.firstname,
            'surname': self.surname,
            'othernames': self.othernames,
            'courses': [
                {'id': c.id, 'name': c.name}
                for c in self.courses
            ],
            'units': [u.to_dict() for u in self.units]
        }

    def __repr__(self):
        return f"<Student {self.reg_number}>"

class Lecturer(db.Model):
    __tablename__ = 'lecturers'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(
        db.String(36),
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        unique=True
    )
    firstname = db.Column(db.String(50), nullable=False)
    surname = db.Column(db.String(50), nullable=False)
    othernames = db.Column(db.String(50))

    # relationship
    user = db.relationship('User', back_populates='lecturer')
    courses = db.relationship('Course', primaryjoin='Lecturer.user_id == foreign(Course.created_by)', cascade='all, delete')

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'firstname': self.firstname,
            'surname': self.surname,
            'othernames': self.othernames,
            'courses': [course.to_dict() for course in self.courses]
        }

    def __repr__(self):
        return f"<Lecturer {self.firstname} {self.surname}>"

class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    school = db.Column(db.String(100), nullable=False)
    # course created by which lecturer
    created_by = db.Column(
        db.String(36),
        db.ForeignKey('users.id', ondelete='SET NULL'),
        nullable=False
    )

    # relationships
    units = db.relationship('Unit', back_populates='course', cascade='all, delete')
    students = db.relationship(
        'Student',
        secondary=student_courses,
        back_populates='courses'
    )

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'department': self.department,
            'school': self.school,
            'units': [u.to_dict() for u in self.units]
        }

    def __repr__(self):
        return f"<Course {self.code}>"

class Unit(db.Model):
    __tablename__ = 'units'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    unit_code = db.Column(db.String(20), nullable=False)
    unit_name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.SmallInteger, nullable=False)
    semester = db.Column(db.SmallInteger, nullable=False)
    course_id = db.Column(
        db.String(36),
        db.ForeignKey('courses.id', ondelete='SET NULL')
    )

    # relationships
    course = db.relationship('Course', back_populates='units')

    def to_dict(self):
        return {
            'id': self.id,
            'unit_code': self.unit_code,
            'unit_name': self.unit_name,
            'level': self.level,
            'semester': self.semester,
            'course_id': self.course_id
        }

    def __repr__(self):
        return f"<Unit {self.unit_code}>"
