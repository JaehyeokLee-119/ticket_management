# 랩 잡일 티켓 관리 시스템 (Lab Chore Ticket Management System)

## 프로젝트 소개
랩 내 잡일(청소, 회의 주최 등) 분배의 공정성과 효율성을 높이기 위한 티켓 기반 관리 시스템입니다. 교수/관리자와 일반 사용자를 구분하여, 티켓(잡일 면제권) 부여, 태스크(잡일) 랜덤 분배, 이력 관리, 알림 기능 등을 제공합니다.

---

## 주요 기능
- **회원가입/로그인**: 이메일 기반 인증, 역할(교수/관리자/일반 사용자) 구분
- **티켓 관리**: 교수/관리자가 티켓 부여/회수, 사유 기록, 이력 확인
- **태스크 관리**: 교수/관리자가 태스크 생성, 후보자 지정, 랜덤 선정 및 알림
- **티켓 사용/면제**: 선정된 인원이 티켓 사용 시 면제, 이력 기록
- **알림**: 이메일 및 웹 알림(추후)
- **이력/통계**: 티켓 및 태스크 이력, 통계(추후)

---

## 기술 스택
- **백엔드**: Python Flask, Flask-SQLAlchemy, Flask-Login
- **DB**: SQLite (개발용, 추후 PostgreSQL 확장 가능)
- **프론트엔드**: Flask Jinja2 템플릿 (추후 React 등 확장 가능)
- **인증**: 세션 기반 (Flask-Login)
- **알림**: 이메일 (추후 웹/모바일 푸시)

---

## 설치 및 실행 방법

1. **의존성 설치**
    ```bash
    pip install -r requirements.txt
    ```

2. **DB 초기화**
    ```bash
    python app.py db init
    python app.py db migrate
    python app.py db upgrade
    ```

3. **서버 실행**
    ```bash
    python app.py
    ```

4. **웹사이트 접속**
    - [http://localhost:5000](http://localhost:5000)

---

## 폴더 구조 예시
```
lab_ticket_system/
├── app.py
├── models.py
├── routes/
│   ├── auth.py
│   └── ...
├── templates/
│   ├── login.html
│   ├── register.html
│   └── ...
├── static/
│   └── ...
├── requirements.txt
└── README.md
```

---

## 향후 계획 및 TODO
- 통계/로그 대시보드
- 모바일 푸시/앱
- Slack/Discord 등 외부 서비스 연동
- 프론트엔드 React 등으로 확장

---

## 문의
- 담당자: (이름/이메일 입력) 