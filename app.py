from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
from werkzeug.security import generate_password_hash, check_password_hash
import random

from models import db, User, Ticket, Task, TaskCandidate, TaskAssignment

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devkey')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lab_ticket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# 라우트 임포트 (추후 분리)
# from routes import auth

# 회원가입
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form['email']
        name = request.form['name']
        password = request.form['password']
        role = request.form['role']
        if User.query.filter_by(email=email).first():
            flash('이미 등록된 이메일입니다.')
            return render_template('register.html')
        hashed_pw = generate_password_hash(password)
        user = User(email=email, name=name, password=hashed_pw, role=role)
        db.session.add(user)
        db.session.commit()
        flash('회원가입이 완료되었습니다. 로그인 해주세요.')
        return redirect(url_for('login'))
    return render_template('register.html')

# 로그인
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('로그인 성공!')
            return redirect(url_for('dashboard'))
        else:
            flash('이메일 또는 비밀번호가 올바르지 않습니다.')
    return render_template('login.html')

# 로그아웃
@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('로그아웃 되었습니다.')
    return redirect(url_for('login'))

# 대시보드(역할별 분기)
@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

# 관리자: 티켓 관리 페이지
@app.route('/ticket/manage', methods=['GET', 'POST'])
@login_required
def ticket_manage():
    if current_user.role != 'admin':
        flash('접근 권한이 없습니다.')
        return redirect(url_for('dashboard'))
    users = User.query.all()
    if request.method == 'POST':
        user_id = request.form['user_id']
        action = request.form['action']  # grant/revoke
        reason = request.form['reason']
        target_user = User.query.get(user_id)
        if not target_user:
            flash('사용자를 찾을 수 없습니다.')
            return redirect(url_for('ticket_manage'))
        ticket = Ticket(user_id=user_id, type=action, reason=reason, created_by=current_user.email)
        db.session.add(ticket)
        db.session.commit()
        flash(f'{target_user.name}님에게 티켓 {"부여" if action=="grant" else "회수"} 완료!')
        return redirect(url_for('ticket_manage'))
    tickets = Ticket.query.order_by(Ticket.created_at.desc()).all()
    return render_template('ticket_manage.html', users=users, tickets=tickets)

# 사용자: 내 티켓 현황/이력
@app.route('/ticket/my')
@login_required
def my_ticket():
    # 티켓 잔여 수 계산: grant - revoke - use
    tickets = Ticket.query.filter_by(user_id=current_user.id).order_by(Ticket.created_at.desc()).all()
    grant = sum(1 for t in tickets if t.type == 'grant')
    revoke = sum(1 for t in tickets if t.type == 'revoke')
    use = sum(1 for t in tickets if t.type == 'use')
    remain = grant - revoke - use
    return render_template('ticket_my.html', tickets=tickets, remain=remain)

# 관리자: 태스크 관리 페이지
@app.route('/task/manage', methods=['GET', 'POST'])
@login_required
def task_manage():
    if current_user.role != 'admin':
        flash('접근 권한이 없습니다.')
        return redirect(url_for('dashboard'))
    users = User.query.all()
    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        required_count = int(request.form['required_count'])
        candidate_ids = request.form.getlist('candidates')
        task = Task(title=title, description=description, created_by=current_user.email, required_count=required_count)
        db.session.add(task)
        db.session.commit()
        for uid in candidate_ids:
            candidate = TaskCandidate(task_id=task.id, user_id=uid)
            db.session.add(candidate)
        db.session.commit()
        flash('태스크가 생성되었습니다.')
        return redirect(url_for('task_manage'))
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    return render_template('task_manage.html', users=users, tasks=tasks)

# 태스크 실행(랜덤 선정)
@app.route('/task/execute/<int:task_id>')
@login_required
def task_execute(task_id):
    if current_user.role != 'admin':
        flash('접근 권한이 없습니다.')
        return redirect(url_for('dashboard'))
    task = Task.query.get_or_404(task_id)
    if task.status == 'completed':
        flash('이미 실행된 태스크입니다.')
        return redirect(url_for('task_manage'))
    candidates = [c.user for c in task.candidates]
    if len(candidates) < task.required_count:
        flash('후보자 수가 필요 인원수보다 적습니다.')
        return redirect(url_for('task_manage'))
    selected = random.sample(candidates, task.required_count)
    for user in selected:
        assignment = TaskAssignment(task_id=task.id, user_id=user.id, status='selected')
        db.session.add(assignment)
    task.status = 'completed'
    db.session.commit()
    flash('태스크가 실행되어 인원이 선정되었습니다.')
    return redirect(url_for('task_manage'))

# 사용자: 태스크 참여/면제
@app.route('/task/my', methods=['GET', 'POST'])
@login_required
def my_tasks():
    # 선정된 태스크 목록
    assignments = TaskAssignment.query.filter_by(user_id=current_user.id, status='selected').order_by(TaskAssignment.assigned_at.desc()).all()
    # 티켓 잔여 수 계산
    tickets = Ticket.query.filter_by(user_id=current_user.id).all()
    grant = sum(1 for t in tickets if t.type == 'grant')
    revoke = sum(1 for t in tickets if t.type == 'revoke')
    use = sum(1 for t in tickets if t.type == 'use')
    remain = grant - revoke - use
    if request.method == 'POST':
        assignment_id = request.form['assignment_id']
        assignment = TaskAssignment.query.get(assignment_id)
        if assignment and assignment.user_id == current_user.id and not assignment.ticket_used:
            if remain > 0:
                # 티켓 사용 처리
                assignment.status = 'exempted'
                assignment.ticket_used = True
                assignment.reason = '티켓 사용으로 면제'
                # 티켓 사용 이력 기록
                ticket = Ticket(user_id=current_user.id, type='use', reason=f'Task {assignment.task.title} 면제', created_by=current_user.email)
                db.session.add(ticket)
                db.session.commit()
                flash(f'태스크 "{assignment.task.title}"에 대해 티켓을 사용하여 면제되었습니다.')
            else:
                flash('잔여 티켓이 없습니다.')
        return redirect(url_for('my_tasks'))
    return render_template('task_my.html', assignments=assignments, remain=remain)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 