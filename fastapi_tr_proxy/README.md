# TR Proxy FastAPI 서비스

Spring Boot으로 작성된 TR Proxy 서비스를 FastAPI로 마이그레이션한 프로젝트입니다.

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

## 변환 방식 요약

1. **계층 분리**:
   - Spring Boot의 컨트롤러/서비스/저장소 계층을 명확히 분리하여 FastAPI 애플리케이션에 적용
   - 인터페이스와 구현체 분리로 확장성 확보

2. **비동기 처리**:
   - FastAPI의 비동기 기능을 활용하여 효율적인 요청 처리
   - `async/await` 패턴으로 블로킹 없는 처리 구현

3. **캐싱 메커니즘**:
   - Spring의 `@Cacheable` → 사용자 정의 캐시 데코레이터로 구현
   - 다양한 TTL 정책 지원

4. **스케줄링**:
   - Spring의 `@Scheduled` → APScheduler로 구현
   - 캐시 초기화 등의 주기적 작업 관리

5. **예외 처리**:
   - Spring의 `@ExceptionHandler` → FastAPI 예외 핸들러로 구현
   - 일관된 오류 응답 형식 제공

6. **설정 관리**:
   - Spring의 외부 설정 → JSON 파일 및 환경 변수로 관리
   - 구성 가능한 캐시 정책 지원

### 주요 기능 구현

#### 1. TR 인터페이스 (TrInterface)
- 모든 TR 구현체가 따라야 하는 추상 인터페이스
- TR 요청, 스키마 조회, 캐시 TTL 관리 기능 정의

#### 2. KB증권 TR 구현 (KbsecTr)
- KB증권 TR 요청 처리 구현
- 스키마 파싱 및 캐시 설정 관리
- 목업 데이터 제공 (실제 구현 시 KASS 라이브러리로 교체 필요)

#### 3. TR 저장소 (TrRepository)
- TR 데이터 캐싱 및 관리
- 다양한 TTL 정책 지원
- 캐시 데코레이터 제공

#### 4. TR 관리자 (TrManager)
- TR 요청 실행 및 캐싱 조율
- 스케줄링 기능 제공
- 캐시 초기화 관리

#### 5. FastAPI 애플리케이션
- API 엔드포인트 정의
- 예외 처리 및 미들웨어
- 애플리케이션 수명 주기 관리

## 설치 및 실행

### 필수 요구사항
- Python 3.9 이상
- FastAPI
- Uvicorn
- APScheduler

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