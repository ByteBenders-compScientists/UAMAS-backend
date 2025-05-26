import uuid
from datetime import datetime

from api import db

class Assessment(db.Model):

    __tablename__ = 'assessments'

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # creator_id = db.Column(db.String(36), db.ForeignKey('user.id'))  # Assuming user table exists # change back when using uamas_db psql
    creator_id = db.Column(db.String(36), nullable=False)  # user ID of the creator # using uamas.db sqlite for testing
    title = db.Column(db.String(255))
    description = db.Column(db.Text)
    questions_type = db.Column(db.String(50))  # e.g., open-ended, close-ended
    type = db.Column(db.String(100))  # CAT, Assignment, etc.
    unit_id = db.Column(db.String(36))
    course_id = db.Column(db.String(36))  # Assuming a course ID is associated with the assessment
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
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id'))
    # student_id = db.Column(db.String(36), db.ForeignKey('user.id'))  # Assuming user table exists
    student_id = db.Column(db.String(36), nullable=False) # user ID of the student
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
    question_id = db.Column(db.Integer, db.ForeignKey('questions.id'))
    assessment_id = db.Column(db.Integer, db.ForeignKey('assessments.id'))  # For reference
    student_id = db.Column(db.String(36), nullable=False)
    text_answer = db.Column(db.Text, nullable=True)
    image_path = db.Column(db.String(36), nullable=True)  # For image answers, if applicable
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
    student_id = db.Column(db.String(36), nullable=False)  # user ID of the student
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
    student_id = db.Column(db.String(36), nullable=False)  # user ID of the student
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
