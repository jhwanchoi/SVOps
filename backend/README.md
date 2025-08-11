# SVOps Backend

FastAPI + Clean Architecture 기반의 확장 가능한 백엔드 API 서버

## 아키텍처 개요

이 프로젝트는 **Clean Architecture** 패턴을 기반으로 구성되어 있으며, 도메인 중심 설계(DDD)를 통해 확장성과 유지보수성을 극대화했습니다.

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
- 인증 및 권한 관리를 위한 기본 정보

### Dataset (데이터셋)
- AI/ML 작업을 위한 데이터셋 관리
- 타입별 분류 (Vector, Surf, Jetson)
- Ground Truth 경로 관리

### Task (태스크)
- 데이터 처리 작업 관리
- 빌드 설정 및 결과 관리
- Airflow와 연동을 위한 메타데이터

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

## 개발 환경 설정

### 1. 의존성 설치
```bash
# Python 3.11 권장
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. 환경 변수 설정
```bash
# .env 파일 확인 및 수정
cp .env.example .env  # 필요시
```

### 3. 서버 실행
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 4. API 문서 확인
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

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

## Docker 배포

```bash
# 개발 환경
docker-compose up --build

# 프로덕션 환경
docker-compose -f docker-compose.prod.yml up --build
```

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