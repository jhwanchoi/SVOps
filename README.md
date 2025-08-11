# SVOps - Service Operations Platform

FastAPI + PostgreSQL + Airflow + Next.js 기반의 서비스 운영 플랫폼

## 프로젝트 구조

```
├── backend/          # FastAPI 백엔드
├── frontend/         # Next.js 프론트엔드  
├── airflow/          # Airflow DAGs 및 설정
├── data/             # 데이터 저장소
│   └── postgres/     # PostgreSQL 데이터
├── logs/             # 로그 파일
└── docker-compose.yml
```

## 기술 스택

- **Backend**: FastAPI (Python 3.9+)
- **Database**: PostgreSQL  
- **Workflow**: Apache Airflow 2.10.5
- **Frontend**: Next.js
- **Containerization**: Docker & Docker Compose

## 시작하기

```bash
# 전체 서비스 실행
docker-compose up -d

# 개발 모드로 백엔드만 실행
cd backend && uvicorn main:app --reload

# 프론트엔드 개발 서버
cd frontend && npm run dev
```