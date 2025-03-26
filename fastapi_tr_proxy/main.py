"""
FastAPI 메인 애플리케이션 모듈
Spring Boot의 TrApplication.java에 해당
"""

import logging
import os
from fastapi import FastAPI, HTTPException, Depends, Body, Path, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional
import json

from agent.share.orchestrator.tr_manager import TrManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# FastAPI 애플리케이션 초기화
app = FastAPI(
    title="TR Proxy API",
    description="트랜잭션 프록시 서비스 API",
    version="1.0.0",
)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 실제 환경에서는 특정 도메인만 허용하도록 수정
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TR 관리자 초기화
tr_manager = TrManager()

# 애플리케이션 시작 시 실행되는 이벤트 핸들러
@app.on_event("startup")
async def startup_event():
    """
    애플리케이션 시작 시 실행되는 초기화 로직
    Spring Boot의 @PostConstruct와 유사
    """
    logger.info("TR Proxy FastAPI 애플리케이션 시작")
    tr_manager.start()

# 애플리케이션 종료 시 실행되는 이벤트 핸들러
@app.on_event("shutdown")
async def shutdown_event():
    """
    애플리케이션 종료 시 실행되는 정리 로직
    Spring Boot의 @PreDestroy와 유사
    """
    logger.info("TR Proxy FastAPI 애플리케이션 종료")
    tr_manager.stop()

# API 키 인증 미들웨어
@app.middleware("http")
async def api_key_middleware(request: Request, call_next):
    """
    API 키 인증 미들웨어
    Spring Security의 필터 체인 역할
    
    Args:
        request: HTTP 요청
        call_next: 다음 미들웨어 또는 엔드포인트 핸들러
        
    Returns:
        응답 객체
    """
    # API 키 설정
    api_key_name = os.getenv("AUTH_TOKEN_HEADER", "X-API-KEY")
    api_key = os.getenv("AUTH_TOKEN", "default-api-key")

    # 캐시 설정 경로를 share/config 디렉토리로 변경
    os.environ.setdefault("CACHE_CONFIG_PATH", 
                          os.path.join(os.path.dirname(__file__), 
                                 "share", "config", "cache-config.json"))
    
    # 공개 경로 설정
    public_paths = ["/", "/docs", "/redoc", "/openapi.json", "/proxy/health"]
    
    # 공개 경로는 인증 없이 접근 가능
    if any(request.url.path.startswith(path) for path in public_paths):
        return await call_next(request)
    
    # API 키 검증
    request_api_key = request.headers.get(api_key_name)
    if request_api_key != api_key:
        return JSONResponse(
            status_code=403,
            content={"detail": "Invalid API Key"},
        )
    
    return await call_next(request)

# 예외 처리 핸들러
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """
    HTTP 예외 처리 핸들러
    Spring의 @ExceptionHandler에 해당
    
    Args:
        request: 요청 객체
        exc: HTTP 예외
        
    Returns:
        JSONResponse: 에러 정보를 담은 JSON 응답
    """
    logger.error(f"HTTP 예외 발생: {exc.detail}", exc_info=True)
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": exc.detail},
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """
    일반 예외 처리 핸들러
    Spring의 GlobalExceptionHandler에 해당
    
    Args:
        request: 요청 객체
        exc: 일반 예외
        
    Returns:
        JSONResponse: 에러 정보를 담은 JSON 응답
    """
    logger.error(f"일반 예외 발생: {str(exc)}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"message": "Internal Server Error"},
    )

# 헬스 체크 엔드포인트
@app.get("/")
async def health_check():
    """
    루트 경로 헬스 체크 엔드포인트
    Spring의 HealthCheckController.healthCheck() 메서드에 해당
    
    Returns:
        str: OK 메시지
    """
    return "ok"

# 프록시 헬스 체크 엔드포인트
@app.get("/proxy/health")
async def proxy_health_check():
    """
    프록시 서비스 헬스 체크 엔드포인트
    Spring의 ProxyController.healthCheck() 메서드에 해당
    
    Returns:
        str: OK 메시지
    """
    return "ok"

# TR 코드로 데이터 요청 엔드포인트
@app.post("/proxy/api/kb/{tr_code}")
async def get_tr_data_by_code(
    tr_code: str = Path(..., description="TR 코드"),
    tr_body: Dict[str, Any] = Body(..., description="TR 요청 본문"),
):
    """
    TR 코드로 데이터를 요청하는 엔드포인트
    Spring의 ProxyController.getTrDataByCode() 메서드에 해당
    
    Args:
        tr_code: TR 코드
        tr_body: TR 요청 본문
        
    Returns:
        Dict[str, Any]: TR 응답 데이터
    """
    logger.debug(f"TR 코드: {tr_code}")
    
    # 데이터 본문 및 헤더 추출
    data_body = {}
    continue_key = None
    
    if "dataHeader" in tr_body:
        data_header = tr_body["dataHeader"]
        if "contKey" in data_header:
            continue_key = data_header["contKey"]
    
    if "dataBody" in tr_body:
        data_body = tr_body["dataBody"]
    else:
        logger.debug("dataBody가 없어 tr_body를 사용")
        data_body = tr_body
    
    # TR 데이터 요청
    try:
        result = await tr_manager.get_tr_data_by_code(tr_code, data_body, continue_key)
        return result
    except Exception as e:
        logger.error(f"TR 데이터 요청 중 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# TR 별칭으로 데이터 요청 엔드포인트 (v1.0)
@app.post("/v1.0/ksv/spec/{alias}")
async def get_tr_data_by_alias(
    alias: str = Path(..., description="TR 별칭"),
    tr_body: Dict[str, Any] = Body(..., description="TR 요청 본문"),
):
    """
    TR 별칭으로 데이터를 요청하는 엔드포인트
    Spring의 ProxyController.getTrDataByAlias() 메서드에 해당
    
    Args:
        alias: TR 별칭
        tr_body: TR 요청 본문
        
    Returns:
        Dict[str, Any]: TR 응답 데이터
    """
    logger.debug(f"별칭: {alias}")
    
    # 데이터 본문 및 헤더 추출
    data_body = {}
    continue_key = None
    
    if "dataHeader" in tr_body:
        data_header = tr_body["dataHeader"]
        if "contKey" in data_header:
            continue_key = data_header["contKey"]
    
    if "dataBody" in tr_body:
        data_body = tr_body["dataBody"]
    else:
        logger.debug("dataBody가 없어 tr_body를 사용")
        data_body = tr_body
    
    # TR 데이터 요청
    try:
        result = await tr_manager.get_tr_data_by_alias(alias, data_body, continue_key)
        return result
    except Exception as e:
        logger.error(f"TR 데이터 요청 중 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

# TR 별칭으로 데이터 요청 엔드포인트 (v2.0)
@app.post("/v2.0/NISV01/{alias}")
async def get_tr_data_by_alias_v2(
    alias: str = Path(..., description="TR 별칭"),
    tr_body: Dict[str, Any] = Body(..., description="TR 요청 본문"),
):
    """
    TR 별칭으로 데이터를 요청하는 엔드포인트 V2
    Spring의 ProxyController.getTrDataByAliasV2() 메서드에 해당
    
    Args:
        alias: TR 별칭
        tr_body: TR 요청 본문
        
    Returns:
        Dict[str, Any]: TR 응답 데이터
    """
    # 데이터 본문 및 헤더 추출
    data_body = {}
    continue_key = None
    
    if "dataHeader" in tr_body:
        data_header = tr_body["dataHeader"]
        if "contKey" in data_header:
            continue_key = data_header["contKey"]
    
    if "dataBody" in tr_body:
        data_body = tr_body["dataBody"]
    else:
        logger.debug("dataBody가 없어 tr_body를 사용")
        data_body = tr_body
    
    # TR 데이터 요청
    try:
        result = await tr_manager.get_tr_data_by_alias(alias, data_body, continue_key)
        return result
    except Exception as e:
        logger.error(f"TR 데이터 요청 중 오류 발생: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))