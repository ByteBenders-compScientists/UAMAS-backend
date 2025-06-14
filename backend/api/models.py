import uuid
from datetime import datetime, timezone

from api import db

class Assessment(db.Model):

    __tablename__ = 'assessments'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    creator_id = db.Column(db.String(36), db.ForeignKey('users.id'))  # Assuming user table exists # change back when using uamas_db psql
    # creator_id = db.Column(db.String(36), nullable=False)  # user ID of the creator # using uamas.db sqlite for testing
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    questions_type = db.Column(db.String(50))  # e.g., open-ended, close-ended
    type = db.Column(db.String(100))  # CAT, Assignment, etc.
    unit_id = db.Column(db.String(36), db.ForeignKey('units.id'), nullable=False)  # Assuming a unit ID is associated with the assessment
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)  # Assuming a course ID is associated with the assessment
    topic = db.Column(db.String(100))
    total_marks = db.Column(db.Integer)
    number_of_questions = db.Column(db.Integer, default=0)  # Number of questions in the assessment
    difficulty = db.Column(db.String(50)) # e.g., Easy, Medium, Hard
    verified = db.Column(db.Boolean, default=False)  # Whether the assessment is verified
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    questions = db.relationship('Question', backref='assessments')

    def to_dict(self):
        return {
            'id': self.id,
            'creator_id': self.creator_id,
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
            # 'status': None
        }
    
    def __repr__(self):
        return f'<Assessment {self.id} by {self.creator_id}>'

class Question(db.Model):

    __tablename__ = 'questions'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = db.Column(db.String(36), db.ForeignKey('assessments.id'), nullable=False)
    text = db.Column(db.Text)
    marks = db.Column(db.Float)
    type = db.Column(db.String(50))  # e.g., text, MCQ, image-based, (returned by frontend)
    rubric = db.Column(db.Text)  # JSON or text rubric for marking
    correct_answer = db.Column(db.Text)  # For MCQs or similar
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # assessment = db.relationship('Assessment', back_populates='questions')

    def to_dict(self):
        return {
            'id': self.id,
            'assessment_id': self.assessment_id,
            'text': self.text,
            'marks': self.marks,
            'type': self.type,
            'rubric': self.rubric,
            'correct_answer': self.correct_answer,
            'created_at': self.created_at.isoformat()
        }
    
    def __repr__(self):
        return f'<Question {self.id} for Assessment {self.assessment_id}>'


class Submission(db.Model):

    __tablename__ = 'submissions'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    assessment_id = db.Column(db.String(36), db.ForeignKey('assessments.id'), nullable=False)
    student_id = db.Column(db.String(36), db.ForeignKey('users.id'), nullable=False)  # Assuming user table exists
    # student_id = db.Column(db.String(36), nullable=False) # user ID of the student
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
    score = db.Column(db.JSON)         # [{q_id, marks_awarded},…]
    feedback = db.Column(db.JSON)         # [{q_id, text},…]
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
        return f'<Result {self.id} for Submission {self.submission_id}>'


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

'''
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

class Course(db.Model):
    __tablename__ = 'courses'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    school = db.Column(db.String(100), nullable=False)

class Unit(db.Model):
    __tablename__ = 'units'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    unit_code = db.Column(db.String(20), unique=True, nullable=False)
    unit_name = db.Column(db.String(100), nullable=False)
    level = db.Column(db.SmallInteger, nullable=False)
    semester = db.Column(db.SmallInteger, nullable=False)
    course_id = db.Column(
        db.String(36),
        db.ForeignKey('courses.id', ondelete='SET NULL')
    )

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