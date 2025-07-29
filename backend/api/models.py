import uuid
from datetime import datetime, timezone

from api import db
from sqlalchemy.orm import foreign

class Assessment(db.Model):

    __tablename__ = 'assessments'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    creator_id = db.Column(db.String(36), db.ForeignKey('users.id'))
    week = db.Column(db.SmallInteger, nullable=False, default = 0)
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    questions_type = db.Column(db.String(50))  # open-ended, close-ended
    close_ended_type = db.Column(db.String(50), nullable=True)  # multiple choices with one answer, multiple choices with multiple answers, matching
    type = db.Column(db.String(100))  # CAT, Assignment, Case study
    unit_id = db.Column(db.String(36), db.ForeignKey('units.id'), nullable=False)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    topic = db.Column(db.String(100))
    total_marks = db.Column(db.Integer)
    number_of_questions = db.Column(db.Integer, default=0)  # Number of questions in the assessment
    difficulty = db.Column(db.String(50)) # Easy, Medium, Hard
    verified = db.Column(db.Boolean, default=False)  # Whether the assessment is verified
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    deadline = db.Column(db.DateTime, nullable=True)
    duration = db.Column(db.Integer, nullable=True)  # minutes
    blooms_level = db.Column(db.String(50), nullable=True)  # Remember, Understand, Apply, Analyze, Evaluate, Create
    questions = db.relationship('Question', back_populates='assessment', cascade='all, delete-orphan')

    @property
    def level(self):
        unit = db.session.query(Unit).filter_by(id=self.unit_id).first()
        return unit.level if unit else None
    @property
    def semester(self):
        unit = db.session.query(Unit).filter_by(id=self.unit_id).first()
        return unit.semester if unit else None

    def to_dict(self):
        return {
            'id': self.id,
            'creator_id': self.creator_id,
            'week': self.week,
            'title': self.title,
            'description': self.description,
            'questions_type': self.questions_type,
            'type': self.type,
            'unit_id': self.unit_id,
            'course_id': self.course_id,
            'topic': self.topic,
            'total_marks': self.total_marks,
            'number_of_questions': self.number_of_questions,
            'difficulty': self.difficulty,
            'verified': self.verified,
            'created_at': self.created_at.isoformat(),
            'level': self.level,
            'semester': self.semester,
            'deadline': self.deadline.isoformat() if self.deadline else None,
            'duration': self.duration,
            'blooms_level': self.blooms_level,
            'close_ended_type': self.close_ended_type,
            'questions': [q.to_dict() for q in self.questions] if self.questions else []
        }
    
    def __repr__(self):
        return f'<Assessment {self.id} by {self.creator_id}>'

class Question(db.Model):

    __tablename__ = 'questions'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = db.Column(db.String(36), db.ForeignKey('assessments.id'), nullable=False)
    text = db.Column(db.Text)
    marks = db.Column(db.Float)
    type = db.Column(db.String(50))
    rubric = db.Column(db.Text)  # text rubric for marking
    correct_answer = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    choices = db.Column(db.JSON, nullable=True)

    assessment = db.relationship('Assessment', back_populates='questions')

    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'text': self.text,
            'marks': self.marks,
            'type': self.type,
            'rubric': self.rubric,
            'correct_answer': self.correct_answer,
            'created_at': self.created_at.isoformat(),
            'choices': self.choices if self.choices else None
        }
    
    def __repr__(self):
        return f'<Question {self.id} for Assessment {self.assessment_id}>'


class Submission(db.Model):

    __tablename__ = 'submissions'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = db.Column(db.String(36), db.ForeignKey('assessments.id'), nullable=False)
    student_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)  # Assuming user table exists
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    graded = db.Column(db.Boolean, default=False)

    # assessment = db.relationship('Assessment', backref='submissions')

    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'student_id': self.student_id,
            'submitted_at': self.submitted_at.isoformat(),
            'graded': self.graded
        }
    
    def __repr__(self):
        return f'<Submission {self.id} for Assessment {self.assessment_id} by Student {self.student_id}>'

class Answer(db.Model):

    __tablename__ = 'answers'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    question_id = db.Column(db.String(36), db.ForeignKey('questions.id'), nullable=False)
    assessment_id = db.Column(db.String(36), db.ForeignKey('assessments.id'), nullable=False)  # For reference
    student_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)  # Assuming user table exists
    text_answer = db.Column(db.Text, nullable=True)
    image_path = db.Column(db.String(100), nullable=True)  # For image answers, if applicable
    saved_at = db.Column(db.DateTime, default=datetime.utcnow)

    # question = db.relationship('Question', backref='answers')

    def to_dict(self):
        return {
            'id': self.id,
            'question_id': self.question_id,
            'assessment_id': self.assessment_id,
            'student_id': self.student_id,
            'text_answer': self.text_answer,
            'image_path': self.image_path,
            'saved_at': self.saved_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Answer {self.id} for Question {self.question_id} by Student {self.student_id}>'



class Result(db.Model):

    __tablename__ = 'results'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)  # Assuming user table exists
    assessment_id = db.Column(db.String(36), db.ForeignKey('assessments.id'), nullable=False)
    question_id = db.Column(db.String(36), db.ForeignKey('questions.id'), nullable=False)
    score = db.Column(db.Float)
    feedback = db.Column(db.Text)
    graded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'assessment_id': self.assessment_id,
            'question_id': self.question_id,
            'score': self.score,
            'feedback': self.feedback,
            'graded_at': self.graded_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Result {self.id} Assessment {self.assessment_id}>'


class TotalMarks(db.Model):

    __tablename__ = 'total_marks'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    student_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)  # Assuming user table exists
    assessment_id = db.Column(db.String(36), db.ForeignKey('assessments.id'), nullable=False)
    submission_id = db.Column(db.String(36), db.ForeignKey('submissions.id'), nullable=False)
    total_marks = db.Column(db.Float)
    calculated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'assessment_id': self.assessment_id,
            'submission_id': self.submission_id,
            'total_marks': self.total_marks,
            'calculated_at': self.calculated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<TotalMarks {self.id} for Assessment {self.assessment_id} by Student {self.student_id}>'


class Notes(db.Model):
    __tablename__ = 'notes'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    lecturer_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    unit_id = db.Column(db.String(36), db.ForeignKey('units.id'), nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False)
    file_path = db.Column(db.String(500), nullable=False)
    file_size = db.Column(db.Integer, nullable=False)
    file_type = db.Column(db.String(10), nullable=False)
    mime_type = db.Column(db.String(100), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    lecturer = db.relationship('User', backref='uploaded_notes')
    course = db.relationship('Course', backref='notes')
    unit = db.relationship('Unit', backref='notes')
    
    def to_dict(self):
        return {
            'id': self.id,
            'lecturer_id': self.lecturer_id,
            'course_id': self.course_id,
            'unit_id': self.unit_id,
            'title': self.title,
            'description': self.description,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'file_type': self.file_type,
            'mime_type': self.mime_type,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
    
    def __repr__(self):
        return f'<Notes {self.id}: {self.title} by {self.lecturer_id}>'

'''
DOES NOT FOLLOW THE FAMOUS `DRY (Don't Repeat Yourself)` PRINCIPLE: fix this later

Authentication service Models
The models below has relationships with the models above
'''

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
        lazy='joined'   # or selectin, etc.
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
