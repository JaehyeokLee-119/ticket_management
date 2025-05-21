from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import os
from werkzeug.security import generate_password_hash, check_password_hash
import random
import logging

from models import db, User, Ticket, Task, TaskCandidate, TaskAssignment

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'devkey')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///lab_ticket.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

logging.basicConfig(level=logging.DEBUG)

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
        name = request.form['name']
        password = request.form['password']
        user = User.query.filter_by(name=name).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('로그인 성공!')
            return redirect(url_for('dashboard'))
        else:
            flash('이름 또는 비밀번호가 올바르지 않습니다.')
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
        ticket = Ticket(user_id=user_id, type=action, reason=reason, created_by=current_user.name)
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
    
    # 부여된 티켓 정보 수집
    grant_tickets = [t for t in tickets if t.type == 'grant']
    
    return render_template('ticket_my.html', tickets=tickets, remain=remain, grant_tickets=grant_tickets)

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
        task = Task(title=title, description=description, created_by=current_user.name, required_count=required_count)
        db.session.add(task)
        db.session.commit()
        for uid in candidate_ids:
            candidate = TaskCandidate(task_id=task.id, user_id=uid)
            db.session.add(candidate)
        db.session.commit()
        flash('태스크가 생성되었습니다.')
        return redirect(url_for('task_manage'))
    
    # 태스크 목록과 각 태스크에 대한 선정 결과 조회
    tasks = Task.query.order_by(Task.created_at.desc()).all()
    
    # 각 태스크에 대한 선정된 사용자 정보 수집
    task_results = {}
    task_statuses = {}  # 실제 진행 상태 정보
    needs_reselection = {}  # 추가 선정 필요 여부

    for task in tasks:
        if task.status == 'completed':
            # 선정된 사용자 조회
            assignments = TaskAssignment.query.filter_by(task_id=task.id).all()
            selected_users = []
            pending_responses = 0  # 응답 대기 중인 사용자 수

            for assignment in assignments:
                user = User.query.get(assignment.user_id)
                if user:
                    # 상태에 따라 구분
                    if assignment.status == 'selected':
                        status = '응답 대기 중'
                        pending_responses += 1
                    elif assignment.status == 'accepted':
                        status = '수락됨'
                    else:  # exempted
                        status = '면제됨'
                    
                    selected_users.append({
                        'name': user.name,
                        'status': status,
                        'ticket_used': assignment.ticket_used,
                        'reason': assignment.reason
                    })
            
            task_results[task.id] = selected_users
            
            # 현재 활성 인원 계산 (면제되지 않은 인원, 수락한 인원 포함)
            active_assignments = TaskAssignment.query.filter(
                TaskAssignment.task_id == task.id,
                TaskAssignment.status.in_(['selected', 'accepted'])
            ).count()
            
            if pending_responses > 0:
                # 응답 대기 중인 사용자가 있으면 "진행 중"
                task_statuses[task.id] = "진행 중 (응답 대기)"
            
            # 추가 선정 필요 여부 확인
            additional_needed = task.required_count - active_assignments
            if additional_needed > 0:
                needs_reselection[task.id] = True
                task_statuses[task.id] = f"추가 선정 필요 ({additional_needed}명)"
            elif not pending_responses:
                # 모든 인원이 응답 완료하고 필요 인원을 충족하면 "완료"
                task_statuses[task.id] = "완료"
    
    return render_template('task_manage.html', users=users, tasks=tasks, 
                           task_results=task_results, task_statuses=task_statuses,
                           needs_reselection=needs_reselection)

# 태스크 실행(랜덤 선정)
@app.route('/task/execute/<int:task_id>')
@login_required
def task_execute(task_id):
    if current_user.role != 'admin':
        flash('접근 권한이 없습니다.')
        return redirect(url_for('dashboard'))
    
    task = Task.query.get_or_404(task_id)
    if task.status == 'completed':
        # 이미 완료된 태스크인 경우, 면제된 인원을 확인하고 추가 선정 진행
        # 현재 활성 인원 수 확인 (면제되지 않은 인원, 수락한 인원 포함)
        active_assignments = TaskAssignment.query.filter(
            TaskAssignment.task_id == task.id,
            TaskAssignment.status.in_(['selected', 'accepted'])
        ).count()
        
        # 필요한 추가 인원 수 계산
        additional_needed = task.required_count - active_assignments
        
        if additional_needed <= 0:
            flash('이미 필요한 인원이 모두 선정되었습니다.')
            return redirect(url_for('task_manage'))
            
        # 이미 선정된 사용자 ID 목록 (현재 active한 사용자만, 면제된 사용자는 제외)
        already_selected_ids = [
            assignment.user_id for assignment in 
            TaskAssignment.query.filter(
                TaskAssignment.task_id == task.id,
                TaskAssignment.status.in_(['selected', 'accepted'])
            ).all()
        ]
        
        # 후보자 목록 (면제된 사용자도 다시 선정될 수 있음)
        available_candidates = [
            c.user for c in task.candidates 
            if c.user.id not in already_selected_ids
        ]
        
        if len(available_candidates) < additional_needed:
            flash(f'추가로 필요한 {additional_needed}명을 선정할 수 없습니다. 후보자가 부족합니다.')
            return redirect(url_for('task_manage'))
        
        # 추가 인원 랜덤 선정
        additional_selected = random.sample(available_candidates, additional_needed)
        auto_accepted = 0  # 자동으로 수락된 사용자 수
        
        for user in additional_selected:
            # 이미 이 태스크에 대해 면제된 기록이 있는지 확인
            existing_exempt = TaskAssignment.query.filter_by(
                task_id=task.id, 
                user_id=user.id,
                status='exempted'
            ).first()
            
            # 사용자의 잔여 티켓 수 계산
            tickets = Ticket.query.filter_by(user_id=user.id).all()
            grant = sum(1 for t in tickets if t.type == 'grant')
            revoke = sum(1 for t in tickets if t.type == 'revoke')
            use = sum(1 for t in tickets if t.type == 'use')
            remain = grant - revoke - use
            
            # 상태 설정 (티켓이 없으면 자동으로 accepted)
            status = 'selected' if remain > 0 else 'accepted'
            
            if existing_exempt:
                # 이미 면제된 적이 있던 사용자는 기존 레코드를 업데이트
                existing_exempt.status = status
                if status == 'accepted':
                    auto_accepted += 1
                flash(f'{user.name}님이 다시 선정되었습니다. (이전에 면제됨)')
            else:
                # 새로운 선정
                assignment = TaskAssignment(task_id=task.id, user_id=user.id, status=status)
                if status == 'accepted':
                    auto_accepted += 1
                db.session.add(assignment)
        
        db.session.commit()
        
        if auto_accepted > 0:
            flash(f'추가 인원 {additional_needed}명이 선정되었습니다. (이 중 {auto_accepted}명은 티켓이 없어 자동 수락됨)')
        else:
            flash(f'추가 인원 {additional_needed}명이 선정되었습니다.')
        return redirect(url_for('task_manage'))
    
    # 처음 실행하는 경우 (status == 'pending')
    candidates = [c.user for c in task.candidates]
    if len(candidates) < task.required_count:
        flash('후보자 수가 필요 인원수보다 적습니다.')
        return redirect(url_for('task_manage'))
    
    selected = random.sample(candidates, task.required_count)
    auto_accepted = 0  # 자동으로 수락된 사용자 수
    
    for user in selected:
        # 사용자의 잔여 티켓 수 계산
        tickets = Ticket.query.filter_by(user_id=user.id).all()
        grant = sum(1 for t in tickets if t.type == 'grant')
        revoke = sum(1 for t in tickets if t.type == 'revoke')
        use = sum(1 for t in tickets if t.type == 'use')
        remain = grant - revoke - use
        
        # 상태 설정 (티켓이 없으면 자동으로 accepted)
        status = 'selected' if remain > 0 else 'accepted'
        if status == 'accepted':
            auto_accepted += 1
            
        assignment = TaskAssignment(task_id=task.id, user_id=user.id, status=status)
        db.session.add(assignment)
    
    task.status = 'completed'
    db.session.commit()
    
    if auto_accepted > 0:
        flash(f'태스크가 실행되어 {task.required_count}명이 선정되었습니다. (이 중 {auto_accepted}명은 티켓이 없어 자동 수락됨)')
    else:
        flash('태스크가 실행되어 인원이 선정되었습니다.')
    return redirect(url_for('task_manage'))

# 사용자: 태스크 참여/면제
@app.route('/task/my', methods=['GET', 'POST'])
@login_required
def my_tasks():
    # 선정된 태스크 목록 (응답 대기 중인 것만)
    assignments = TaskAssignment.query.filter_by(
        user_id=current_user.id, 
        status='selected'
    ).order_by(TaskAssignment.assigned_at.desc()).all()
    
    # 이미 응답한 태스크 목록 (수락 또는 면제)
    completed_assignments = TaskAssignment.query.filter(
        TaskAssignment.user_id == current_user.id,
        TaskAssignment.status.in_(['accepted', 'exempted'])
    ).order_by(TaskAssignment.assigned_at.desc()).all()
    
    # 티켓 잔여 수 계산
    tickets = Ticket.query.filter_by(user_id=current_user.id).all()
    grant = sum(1 for t in tickets if t.type == 'grant')
    revoke = sum(1 for t in tickets if t.type == 'revoke')
    use = sum(1 for t in tickets if t.type == 'use')
    remain = grant - revoke - use
    
    # 부여된 티켓 정보 수집
    grant_tickets = [t for t in tickets if t.type == 'grant']
    
    if request.method == 'POST':
        assignment_id = request.form['assignment_id']
        action = request.form['action']  # 'accept' 또는 'exempt'
        
        assignment = TaskAssignment.query.get(assignment_id)
        if assignment and assignment.user_id == current_user.id and assignment.status == 'selected':
            if action == 'accept':
                # 태스크 수락 처리
                assignment.status = 'accepted'
                db.session.commit()
                flash(f'태스크 "{assignment.task.title}"를 수락했습니다.')
            elif action == 'exempt' and remain > 0:
                # 티켓 사용 처리
                assignment.status = 'exempted'
                assignment.ticket_used = True
                assignment.reason = '티켓 사용으로 면제'
                # 티켓 사용 이력 기록
                ticket = Ticket(user_id=current_user.id, type='use', reason=f'Task {assignment.task.title} 면제', created_by=current_user.name)
                db.session.add(ticket)
                db.session.commit()
                flash(f'태스크 "{assignment.task.title}"에 대해 티켓을 사용하여 면제되었습니다.')
            elif action == 'exempt' and remain <= 0:
                flash('잔여 티켓이 없습니다.')
        
        return redirect(url_for('my_tasks'))
    
    return render_template('task_my.html', 
                           assignments=assignments, 
                           completed_assignments=completed_assignments,
                           remain=remain,
                           grant_tickets=grant_tickets)

@app.route('/test')
def test():
    return "테스트 페이지 작동 중"

@app.route('/')
def index():
    return redirect(url_for('login'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 