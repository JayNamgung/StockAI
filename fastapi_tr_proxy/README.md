# TR Proxy FastAPI 서비스

Spring Boot으로 작성된 KB증권 TR 프록시 서비스를 FastAPI로 마이그레이션한 프로젝트입니다.

## 마이그레이션 개요

이 프로젝트는 Spring Boot 기반의 AWS Lambda 서버 애플리케이션을 FastAPI 프레임워크로 변환한 것입니다. 기존 애플리케이션의 모든 기능을 유지하면서 Python 환경에서 동작하도록 재구현하였습니다.

### 변환 접근 방식

1. **계층형 아키텍처 유지**:
   - Spring Boot의 Controller-Service-Repository 패턴을 유사하게 구현
   - Interface-Implementation 패턴 적용

2. **주요 기능별 변환**:
   - 컨트롤러 → FastAPI 라우터
   - 서비스 로직 → Python 클래스
   - 캐싱 → 사용자 정의 캐시 로직
   - 스케줄링 → APScheduler 사용

3. **코드 구조화**:
   - `agent/share/core/interface`: 인터페이스 정의
   - `agent/share/core/tr`: TR 구현체
   - `agent/share/repository`: 데이터 저장소
   - `agent/share/orchestrator`: 서비스 조율

### 주요 기능 구현

1. **TR 인터페이스 (TrInterface)**
   - 모든 TR 구현체가 따라야 하는 추상 인터페이스
   - TR 요청, 캐시 TTL 관리 기능 정의

2. **KB증권 TR 구현 (KbsecTr)**
   - KB증권 TR 요청 처리 구현
   - Py4J를 통한 Java 라이브러리 연동
   - 로컬/개발 환경 분기 처리

3. **TR 저장소 (TrRepository)**
   - TR 데이터 캐싱 및 관리
   - 다양한 TTL 정책 지원
   - 캐시 데코레이터 제공

4. **TR 관리자 (TrManager)**
   - TR 요청 실행 및 캐싱 조율
   - 스케줄링 기능 제공
   - 캐시 초기화 관리

## 프로젝트 구조
agent/
├── share/
│   ├── core/
│   │   ├── interface/
│   │   │   └── tr_interface.py     # TR 인터페이스 정의
│   │   └── tr/
│   │       ├── tr_kbsec.py         # KB증권 TR 구현
│   │       ├── driver/             # JAR 파일 디렉토리
│   │       │   ├── JKASS_v4.jar    # KB증권 KASS 라이브러리
│   │       │   └── ... (기타 JAR 파일들)
│   │       └── schema/             # TR 스키마 파일
│   ├── repository/
│   │   └── tr_repository.py        # TR 데이터 저장소
│   └── orchestrator/
│       └── tr_manager.py           # TR 관리 및 조율
├── main.py                        # FastAPI 애플리케이션
└── requirements.txt               # 패키지 의존성

## 변환 방식 요약

1. **계층 분리**:
   - 인터페이스와 구현체 분리로 확장성 확보
   - 관심사 분리를 통한 코드 유지보수성 향상

2. **비동기 처리**:
   - FastAPI의 비동기 기능을 활용한 효율적인 요청 처리
   - Java 라이브러리 호출은 별도 스레드 풀에서 실행

3. **캐싱 메커니즘**:
   - 인메모리 캐싱으로 반복 요청 최적화
   - TR 코드별 다양한 TTL 정책 지원

4. **스케줄링**:
   - APScheduler를 활용한 주기적 작업 관리
   - 매일 오전 8시 캐시 초기화 작업 수행

5. **로컬/개발 환경 분리**:
   - 로컬: 목 데이터 반환으로 개발 편의성 제공
   - 개발: Py4J를 통한 실제 KB증권 서버 통신

## 설치 및 실행

### 필수 요구사항
- Python 3.9 이상
- Java 8 이상 (개발 환경에서 필요)
- KB증권 KASS 라이브러리 JAR 파일 (개발 환경에서 필요)

### 환경 설정
```bash
# 가상 환경 생성
python -m venv venv

# 가상 환경 활성화
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate

# 의존성 설치
pip install -r requirements.txt

# 개발 모드로 실행
uvicorn agent.main:app --reload

# 프로덕션 모드로 실행
uvicorn agent.main:app --host 0.0.0.0 --port 8000

### API 테스트
# 헬스 체크
curl http://localhost:8000/

# TR 코드로 데이터 요청
curl -X POST http://localhost:8000/proxy/api/kb/IVCA0060 \
  -H "Content-Type: application/json" \
  -d '{"dataBody": {"indTypCd": "001"}}'

# 별칭으로 데이터 요청
curl -X POST http://localhost:8000/v1.0/ksv/spec/index_info \
  -H "Content-Type: application/json" \
  -d '{"dataBody": {"indTypCd": "001"}}'