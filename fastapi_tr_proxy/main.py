"""
FastAPI 메인 애플리케이션 모듈
"""

import logging
import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Body, Path
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from typing import Dict, Any, Optional

# 환경 변수 로드
dotenv_path = os.path.join(
    os.path.dirname(__file__), 
    "share", "core", "tr", "driver", ".env"
)
load_dotenv(dotenv_path=dotenv_path)

from agent.share.core.tr.tr_kbsec import KbsecTr
from agent.share.repository.tr_repository import TrRepository
from agent.share.orchestrator.tr_manager import TrManager

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("tr-proxy")

# FastAPI 애플리케이션 초기화
app = FastAPI(
    title="TR Proxy API",
    description="KB증권 TR 프록시 서비스 API",
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

# 의존성 주입을 위한 객체 생성
tr_interface = KbsecTr()
tr_repository = TrRepository(tr_interface)
tr_manager = TrManager(tr_repository)

@app.on_event("startup")
async def startup_event():
    """
    애플리케이션 시작 시 실행되는 초기화 로직
    """
    env = os.getenv("APP_ENV", "local")
    logger.info(f"TR Proxy 서비스 시작: 환경={env}")
    tr_manager.start()

@app.on_event("shutdown")
async def shutdown_event():
    """
    애플리케이션 종료 시 실행되는 정리 로직
    """
    logger.info("TR Proxy 서비스 종료")
    tr_manager.stop()

@app.get("/")
async def health_check():
    """
    루트 경로 헬스 체크 엔드포인트
    """
    env = os.getenv("APP_ENV", "local")
    return {"status": "ok", "environment": env}

@app.get("/proxy/health")
async def proxy_health_check():
    """
    프록시 헬스 체크 엔드포인트
    """
    env = os.getenv("APP_ENV", "local")
    return {"status": "ok", "environment": env}

@app.post("/proxy/api/kb/{tr_code}")
async def get_tr_data_by_code(
    tr_code: str = Path(..., description="TR 코드"),
    tr_body: Dict[str, Any] = Body(..., description="TR 요청 본문"),
):
    """
    TR 코드로 데이터를 요청하는 엔드포인트
    
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

@app.post("/v1.0/ksv/spec/{alias}")
async def get_tr_data_by_alias(
    alias: str = Path(..., description="TR 별칭"),
    tr_body: Dict[str, Any] = Body(..., description="TR 요청 본문"),
):
    """
    TR 별칭으로 데이터를 요청하는 엔드포인트
    
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

@app.post("/v2.0/NISV01/{alias}")
async def get_tr_data_by_alias_v2(
    alias: str = Path(..., description="TR 별칭"),
    tr_body: Dict[str, Any] = Body(..., description="TR 요청 본문"),
):
    """
    TR 별칭으로 데이터를 요청하는 엔드포인트 V2
    
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