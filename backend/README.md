# SVOps Backend

FastAPI + Clean Architecture 기반의 자동화된 DAG 실행 시스템

## 시스템 개요

SVOps Backend는 **Clean Architecture** 패턴을 기반으로 구성된 자동화된 워크플로 관리 시스템입니다. Apache Airflow와 Celery를 통합하여 순차적 DAG 실행 체인을 자동으로 관리하며, 실시간 상태 모니터링을 제공합니다.

## 핵심 기능

### 자동 DAG 체인 실행
- **Task 실행 → data_processing_pipeline → ml_training_pipeline → simple_workflow_example**
- 각 DAG 완료 시 자동으로 다음 DAG 트리거
- 실패 시 자동 Task 상태 업데이트
- Celery 기반 비동기 모니터링

### 실시간 상태 모니터링
- WebSocket을 통한 실시간 상태 업데이트
- REST API를 통한 상세 실행 상태 조회
- 각 DAG별 개별 상태 추적

### Frontend 통합 지원
- Task 실행을 위한 단일 API 엔드포인트
- 전체 DAG 체인 상태 추적 API
- 실시간 진행상황 모니터링

### 계층 구조

```
app/
├── domain/              # 도메인 계층 (비즈니스 로직의 핵심)
│   ├── entities.py      # 도메인 엔티티
│   ├── value_objects.py # 값 객체
│   └── repositories.py  # 리포지토리 인터페이스
├── application/         # 애플리케이션 계층 (유스케이스)
│   └── use_cases/       # 비즈니스 유스케이스
├── infrastructure/      # 인프라스트럭처 계층 (기술적 구현)
│   ├── database/        # 데이터베이스 모델
│   └── repositories/    # 리포지토리 구현
├── presentation/        # 프레젠테이션 계층 (API)
│   ├── api/            # API 라우터
│   └── schemas/        # Pydantic 스키마
├── shared/             # 공통 컴포넌트
│   ├── exceptions.py   # 도메인 예외
│   └── types.py       # 공통 타입
└── core/              # 핵심 설정
    ├── config.py      # 애플리케이션 설정
    └── database.py    # 데이터베이스 설정
```

## 설계 원칙

### 1. 의존성 역전 원칙 (Dependency Inversion)
- 고수준 모듈(도메인)이 저수준 모듈(인프라)에 의존하지 않음
- 추상화(인터페이스)에 의존하여 구현체 교체 용이

### 2. 단일 책임 원칙 (Single Responsibility)
- 각 계층과 모듈이 하나의 명확한 책임을 가짐
- 변경 이유가 하나씩만 존재

### 3. 개방-폐쇄 원칙 (Open-Closed)
- 확장에는 열려있고 수정에는 닫혀있음
- 새로운 기능 추가 시 기존 코드 수정 최소화

## 주요 도메인 엔티티

### User (사용자)
- 시스템 사용자 관리
- JWT 기반 인증 및 권한 관리

### Dataset (데이터셋)
- AI/ML 작업을 위한 데이터셋 관리
- 타입별 분류 (Vector, Surf, Jetson)
- Ground Truth 경로 관리

### Task (태스크)
- 데이터 처리 작업 관리 
- **자동 DAG 체인 실행의 시작점**
- 빌드 설정 및 실행 결과 관리
- 상태: PENDING → RUNNING → COMPLETED/FAILED

### Workflow & WorkflowRun
- Apache Airflow DAG와 매핑되는 워크플로
- 각 DAG 실행의 개별 상태 관리
- Task와 연결되어 자동 체인 실행

## 자동화된 워크플로 시스템

### DAG 실행 체인
```
Task 실행 요청
    ↓
data_processing_pipeline (DAG 1)
    ↓ (자동)
ml_training_pipeline (DAG 2)
    ↓ (자동)
simple_workflow_example (DAG 3)
    ↓
Task 상태 COMPLETED 업데이트
```

### 핵심 구현 요소

#### 1. DAG 체인 설정
```python
# app/application/tasks/dag_chain_tasks.py
DAG_EXECUTION_CHAIN = [
    "data_processing_pipeline",
    "ml_training_pipeline", 
    "simple_workflow_example"
]
```

#### 2. Celery 기반 모니터링
- `trigger_next_dag_after_completion.delay()`: 다음 DAG 자동 실행
- Airflow API를 통한 DAG 상태 모니터링
- 완료/실패 시 자동 상태 업데이트

#### 3. 에러 처리
- DAG 실행 실패 시 Task 상태 FAILED로 업데이트
- 체인 중단 및 알림 시스템 연동

## Frontend 통합 API

### Task 실행
```http
POST /api/v1/tasks/{task_id}/execute
Content-Type: application/json

{
    "parameters": {},
    "note": "Task execution from frontend"
}
```

**Response:**
```json
{
    "task_id": 1,
    "total_dags": 3,
    "workflow_runs": [...],
    "message": "Task 1 execution started with 3 DAG chain"
}
```

### Task 상태 조회
```http
GET /api/v1/tasks/{task_id}/status
```

**Response:**
```json
{
    "task_id": 1,
    "task_status": "running",
    "task_name": "ML Training Task",
    "dag_chain": ["data_processing_pipeline", "ml_training_pipeline", "simple_workflow_example"],
    "workflow_runs": [
        {
            "id": "run_1",
            "workflow_id": "wf_1", 
            "status": "success",
            "start_date": "2025-01-01T10:00:00",
            "end_date": "2025-01-01T10:30:00"
        }
    ],
    "total_workflow_runs": 3,
    "overall_status": "running"
}
```

### WebSocket 실시간 모니터링
```javascript
// 전역 상태 구독
const ws = new WebSocket('ws://localhost:8000/ws');

// 특정 워크플로 구독
const wsWorkflow = new WebSocket('ws://localhost:8000/ws/workflow/{workflow_id}');

// 사용자별 알림 구독
const wsUser = new WebSocket('ws://localhost:8000/ws/user/{user_id}');
```

## 프로덕션 준비 API 엔드포인트

### 인증 (Authentication)
- `POST /api/v1/auth/login` - 사용자 로그인
- `POST /api/v1/auth/refresh` - JWT 토큰 갱신

### 사용자 관리 (Users)
- `POST /api/v1/users/` - 사용자 생성
- `GET /api/v1/users/{user_id}` - 사용자 조회
- `PUT /api/v1/users/{user_id}` - 사용자 수정
- `DELETE /api/v1/users/{user_id}` - 사용자 삭제
- `GET /api/v1/users/` - 사용자 목록

### 데이터셋 관리 (Datasets)
- `POST /api/v1/datasets/` - 데이터셋 생성
- `GET /api/v1/datasets/{dataset_id}` - 데이터셋 조회
- `PUT /api/v1/datasets/{dataset_id}` - 데이터셋 수정
- `DELETE /api/v1/datasets/{dataset_id}` - 데이터셋 삭제
- `GET /api/v1/datasets/` - 데이터셋 목록

### 태스크 관리 (Tasks)
- `POST /api/v1/tasks/` - 태스크 생성
- `GET /api/v1/tasks/{task_id}` - 태스크 조회
- `PUT /api/v1/tasks/{task_id}` - 태스크 수정
- `DELETE /api/v1/tasks/{task_id}` - 태스크 삭제
- `GET /api/v1/tasks/` - 태스크 목록
- **`POST /api/v1/tasks/{task_id}/execute`** - **자동 DAG 체인 실행**
- **`GET /api/v1/tasks/{task_id}/status`** - **실행 상태 조회**

### 워크플로 관리 (Workflows)
- `POST /api/v1/workflows/` - 워크플로 생성
- `POST /api/v1/workflows/{workflow_id}/runs` - 워크플로 실행
- `GET /api/v1/workflows/{workflow_id}/runs` - 실행 목록 조회
- `GET /api/v1/workflows/{workflow_id}/runs/{run_id}` - 실행 상태 조회
- `POST /api/v1/workflows/{workflow_id}/runs/{run_id}/control` - 실행 제어 (stop/retry)

### 알림 관리 (Notifications)
- `POST /api/v1/notifications/configs` - 알림 설정 생성 (관리자)
- `GET /api/v1/notifications/configs` - 알림 설정 목록 (관리자)
- `DELETE /api/v1/notifications/configs/{config_name}` - 알림 설정 삭제
- `POST /api/v1/notifications/configs/{config_name}/enable` - 알림 활성화
- `POST /api/v1/notifications/configs/{config_name}/disable` - 알림 비활성화
- `GET /api/v1/notifications/types` - 알림 타입 목록
- `POST /api/v1/notifications/webhook/{config_name}` - 외부 웹훅 수신

### WebSocket 엔드포인트
- `WS /ws` - 전역 이벤트 구독
- `WS /ws/user/{user_id}` - 사용자별 이벤트 구독
- `WS /ws/workflow/{workflow_id}` - 워크플로별 이벤트 구독
- `WS /ws/user/{user_id}/workflow/{workflow_id}` - 사용자+워크플로 이벤트 구독
- `GET /ws/stats` - WebSocket 연결 통계

## 개발 가이드

### 새로운 기능 추가 시 개발 순서

#### 1. 도메인 계층부터 시작 (`app/domain/`)

**새로운 엔티티 추가:**
```python
# app/domain/entities.py
@dataclass
class NewEntity(Entity):
    id: Optional[NewEntityId]
    name: str
    # 비즈니스 로직 메서드들
    def business_method(self):
        pass
```

**값 객체 정의:**
```python
# app/domain/value_objects.py
@dataclass(frozen=True)
class NewEntityId:
    value: int
```

**리포지토리 인터페이스 정의:**
```python
# app/domain/repositories.py
class NewEntityRepository(ABC):
    @abstractmethod
    async def create(self, entity: NewEntity) -> NewEntity:
        pass
```

#### 2. 인프라스트럭처 계층 구현 (`app/infrastructure/`)

**데이터베이스 모델:**
```python
# app/infrastructure/database/models.py
class NewEntityModel(Base):
    __tablename__ = "new_entities"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
```

**리포지토리 구현:**
```python
# app/infrastructure/repositories/new_entity_repository.py
class SQLAlchemyNewEntityRepository(NewEntityRepository):
    def __init__(self, session: AsyncSession):
        self.session = session
    
    async def create(self, entity: NewEntity) -> NewEntity:
        # 구현 코드
```

#### 3. 애플리케이션 계층 구현 (`app/application/`)

**유스케이스 정의:**
```python
# app/application/use_cases/new_entity_use_cases.py
@dataclass
class CreateNewEntityCommand:
    name: str

class NewEntityUseCases:
    def __init__(self, uow: UnitOfWork):
        self.uow = uow
    
    async def create_entity(self, command: CreateNewEntityCommand) -> NewEntity:
        # 비즈니스 로직 구현
```

#### 4. 프레젠테이션 계층 구현 (`app/presentation/`)

**API 스키마:**
```python
# app/presentation/schemas/new_entity_schemas.py
class NewEntityCreate(BaseModel):
    name: str

class NewEntityResponse(BaseModel):
    id: int
    name: str
```

**API 라우터:**
```python
# app/presentation/api/new_entities.py
router = APIRouter(prefix="/new-entities", tags=["new-entities"])

@router.post("/", response_model=NewEntityResponse)
async def create_entity(data: NewEntityCreate):
    # API 엔드포인트 구현
```

**라우터 등록:**
```python
# app/presentation/api/api.py
from app.presentation.api import new_entities
api_router.include_router(new_entities.router)
```

## 파일별 역할 가이드

### 도메인 계층
- **`entities.py`**: 비즈니스 규칙과 도메인 로직을 포함한 핵심 엔티티
- **`value_objects.py`**: 불변 값 객체 (ID, 설정 객체 등)
- **`repositories.py`**: 데이터 접근을 위한 추상 인터페이스

### 애플리케이션 계층
- **`use_cases/`**: 특정 비즈니스 시나리오를 처리하는 유스케이스
- **Command 객체**: 입력 데이터를 캡슐화

### 인프라스트럭처 계층
- **`database/models.py`**: SQLAlchemy ORM 모델
- **`repositories/`**: 리포지토리 인터페이스의 구체적 구현
- **`unit_of_work.py`**: 트랜잭션 관리

### 프레젠테이션 계층
- **`api/`**: FastAPI 라우터와 엔드포인트
- **`schemas/`**: 요청/응답 데이터 검증을 위한 Pydantic 모델

## 환경 설정 및 실행

### 필수 요구사항
- Python 3.11+
- PostgreSQL 14+
- Redis 6.2+
- Apache Airflow 2.5+
- Docker & Docker Compose

### Docker Compose 실행 (권장)
```bash
# 전체 시스템 실행 (Backend + PostgreSQL + Redis + Airflow + Celery)
docker-compose up --build

# 백그라운드 실행
docker-compose up -d --build
```

### 로컬 개발 환경
```bash
# 1. 의존성 설치
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. 환경 변수 설정
cp .env.example .env  # 필요시 수정

# 3. 데이터베이스 초기화
./scripts/init-db.sh

# 4. Celery Worker 실행 (별도 터미널)
celery -A app.core.celery_app worker --loglevel=info -Q default,workflow_monitoring,dag_chain,notifications

# 5. 백엔드 서버 실행
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### API 문서 및 모니터링
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Airflow UI**: http://localhost:8080 (admin/admin)
- **WebSocket Stats**: http://localhost:8000/ws/stats

## 테스트

### 단위 테스트
```bash
pytest tests/unit/
```

### 통합 테스트
```bash
pytest tests/integration/
```

## 데이터베이스 마이그레이션

### Alembic 설정
```bash
# 마이그레이션 파일 생성
alembic revision --autogenerate -m "Add new table"

# 마이그레이션 적용
alembic upgrade head
```

## 시스템 아키텍처

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Frontend      │────│   Backend API    │────│   PostgreSQL    │
│   (React/Vue)   │    │   (FastAPI)      │    │   Database      │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ├────────────────────┬─────────────────┐
                              │                    │                 │
                       ┌──────────────┐    ┌──────────────┐  ┌──────────────┐
                       │   Celery     │    │   Apache     │  │   Redis      │
                       │   Worker     │    │   Airflow    │  │   Cache      │
                       └──────────────┘    └──────────────┘  └──────────────┘
```

### 주요 구성 요소
- **FastAPI Backend**: REST API 및 WebSocket 서버
- **Celery Worker**: 비동기 작업 처리 및 DAG 모니터링  
- **Apache Airflow**: DAG 정의 및 스케줄링
- **PostgreSQL**: 메인 데이터베이스
- **Redis**: Celery 브로커 및 캐싱

## 배포

### Docker Compose (권장)
```bash
# 전체 스택 배포
docker-compose up -d --build

# 로그 확인
docker-compose logs -f backend celery-worker airflow-webserver
```

### 프로덕션 환경
```bash
# 환경별 설정 파일 사용
docker-compose -f docker-compose.prod.yml up -d --build
```

## 개발 완료 상태

### 구현 완료 기능
- 자동 DAG 체인 실행 (data_processing → ml_training → simple_workflow)
- Task 상태 자동 업데이트 (RUNNING → COMPLETED/FAILED)
- Celery 기반 비동기 모니터링 시스템
- WebSocket 실시간 상태 알림
- JWT 인증 시스템
- Clean Architecture 기반 확장 가능한 구조

### 제거된 개발 아티팩트
- 테스트용 알림 엔드포인트 (`/notifications/test`)
- 테스트용 WebSocket 엔드포인트 (`/ws/test`)
- 미구현 로그 조회 엔드포인트
- 개발용 디버그 로그 코드

## 보안 고려사항

1. **환경 변수 관리**: 민감한 정보는 반드시 환경 변수로 관리
2. **입력 검증**: Pydantic을 통한 강력한 입력 데이터 검증
3. **SQL 인젝션 방지**: SQLAlchemy ORM 사용으로 자동 방지
4. **CORS 설정**: 프로덕션 환경에서는 특정 도메인만 허용

## 성능 최적화 팁

1. **비동기 처리**: 모든 DB 작업은 async/await 사용
2. **연결 풀링**: SQLAlchemy 연결 풀 설정 최적화
3. **쿼리 최적화**: N+1 문제 방지를 위한 적절한 로딩 전략
4. **캐싱**: Redis 등을 활용한 캐싱 전략 고려

## 기여 가이드

1. 새로운 기능은 반드시 도메인 계층부터 시작
2. 테스트 코드 작성 필수
3. Clean Architecture 원칙 준수
4. 코드 리뷰를 통한 품질 관리

## 참고 자료

- [Clean Architecture (Robert C. Martin)](https://blog.cleancoder.com/uncle-bob/2012/08/13/the-clean-architecture.html)
- [Domain Driven Design](https://martinfowler.com/bliki/DomainDrivenDesign.html)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy Documentation](https://docs.sqlalchemy.org/)