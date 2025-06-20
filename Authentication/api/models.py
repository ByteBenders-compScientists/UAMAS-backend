from . import db
import uuid
from datetime import datetime, timezone

# association table for lecturer-unit many-to-many relationship
lecturer_units = db.Table(
    'lecturer_units',
    db.Column('lecturer_id', db.String(36), db.ForeignKey('lecturers.id', ondelete='CASCADE'), primary_key=True),
    db.Column('unit_id', db.String(36), db.ForeignKey('units.id', ondelete='CASCADE'), primary_key=True)
)

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

class Student(db.Model):
    __tablename__ = 'students'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = db.Column(
        db.String(36),
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
        unique=True
    )
    reg_number = db.Column(db.String(30), unique=True, nullable=False)
    year_of_study = db.Column(db.SmallInteger, nullable=False)
    semester = db.Column(db.SmallInteger, nullable=False) # Added for semester tracking, if needed
    firstname = db.Column(db.String(50), nullable=False)
    surname = db.Column(db.String(50), nullable=False)
    othernames = db.Column(db.String(50))

    course_id = db.Column(
        db.String(36),
        db.ForeignKey('courses.id', ondelete='CASCADE'),
        nullable=False
    )

    # relationships
    user = db.relationship('User', back_populates='student')
    course = db.relationship('Course', back_populates='students')

    @property
    def units(self):
        """
        Returns the list of Unit objects associated with the student's course and filtered by the units by level/year of study.
        """
        units = []
        if self.course:
            for unit in self.course.units:
                if unit.level == self.year_of_study and unit.semester == self.semester:
                    units.append(unit)
            return units
        return []

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'reg_number': self.reg_number,
            'year_of_study': self.year_of_study,
            'firstname': self.firstname,
            'surname': self.surname,
            'othernames': self.othernames,
            # 'course': self.course.to_dict(),
            'semester': self.semester,
            'course': {
                'id': self.course.id if self.course else None,
                'name': self.course.name if self.course else None
            },
            'units': [u.to_dict() for u in self.units]
        }

    def __repr__(self):
        return f"<Student {self.reg_number}>"

# hobbies/interests for students

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
    units = db.relationship(
        'Unit',
        secondary=lecturer_units,
        back_populates='lecturers'
    )

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'firstname': self.firstname,
            'surname': self.surname,
            'othernames': self.othernames,
            'units': [u.to_dict() for u in self.units]
        }

    def __repr__(self):
        return f"<Lecturer {self.firstname} {self.surname}>"

class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    school = db.Column(db.String(100), nullable=False)

    # relationships
    units = db.relationship('Unit', back_populates='course', cascade='all, delete')
    students = db.relationship('Student', back_populates='course', cascade='all, delete')

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
    unit_code = db.Column(db.String(20), unique=True, nullable=False)
    unit_name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.SmallInteger, nullable=False)  # e.g., rep: year 1, 2, 3, 4
    semester = db.Column(db.SmallInteger, nullable=False) # rep: semester: 1 for first sem etc
    course_id = db.Column(
        db.String(36),
        db.ForeignKey('courses.id', ondelete='SET NULL')
    )

    # relationships
    course = db.relationship('Course', back_populates='units')
    lecturers = db.relationship(
        'Lecturer',
        secondary=lecturer_units,
        back_populates='units'
    )

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
