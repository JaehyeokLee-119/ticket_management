from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')  # 'admin' 또는 'user'
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    def __repr__(self):
        return f'<User {self.email}>'

class Ticket(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    type = db.Column(db.String(20), nullable=False)  # 'grant', 'revoke', 'use'
    reason = db.Column(db.String(200), nullable=False)
    created_by = db.Column(db.String(120), nullable=False)  # 이메일 또는 이름
    created_at = db.Column(db.DateTime, server_default=db.func.now())

    user = db.relationship('User', backref=db.backref('tickets', lazy=True))

class Task(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(200))
    created_by = db.Column(db.String(120), nullable=False)  # 이메일 또는 이름
    required_count = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    status = db.Column(db.String(20), default='pending')  # pending, completed

class TaskCandidate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    task = db.relationship('Task', backref=db.backref('candidates', lazy=True))
    user = db.relationship('User', backref=db.backref('task_candidates', lazy=True))

class TaskAssignment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(db.Integer, db.ForeignKey('task.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False)  # selected, exempted
    ticket_used = db.Column(db.Boolean, default=False)
    reason = db.Column(db.String(200))
    assigned_at = db.Column(db.DateTime, server_default=db.func.now())
    task = db.relationship('Task', backref=db.backref('assignments', lazy=True))
    user = db.relationship('User', backref=db.backref('task_assignments', lazy=True)) 