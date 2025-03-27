"""
KB증권 TR 구현 모듈
KB증권 TR 요청을 처리하기 위한 TrInterface 구현
"""

import os
import json
import logging
import xml.etree.ElementTree as ET
from typing import Dict, Any, Optional, List
import asyncio
from py4j.java_gateway import JavaGateway, GatewayParameters, launch_gateway, CallbackServerParameters

from agent.share.core.interface.tr_interface import TrInterface

logger = logging.getLogger(__name__)

class KbsecTr(TrInterface):
    """
    KB증권 TR 구현 클래스
    TrInterface를 구현하여 KB증권 TR 요청 처리
    """
    
    def __init__(self):
        """
        KB증권 TR 클래스 초기화
        설정 로드 및 KASS 브리지 초기화
        """
        # 환경 설정 (.env 파일에서 로드)
        self.environment = os.getenv("APP_ENV", "local")
        
        # 캐시 설정 로드
        self.tr_rules = self._load_cache_config()
        
        # 별칭 매핑 구성
        self.alias_mapping = {}
        for key, value in self.tr_rules.items():
            alias = value.get("alias")
            if alias:
                self.alias_mapping[alias] = key
        
        # Java 게이트웨이 (실제 모드에서만 초기화)
        self.gateway = None
        if self.environment != "local":
            self._init_gateway()
        
        # 채널 ID (.env 파일에서 로드)
        self.channel_id = os.getenv("CHANNEL_ID", "3Aw")
        
        # 스키마 캐시 초기화
        self.schema_cache = {}
        
        # 스키마 디렉토리
        self.schema_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema")
        
        logger.info(f"KB증권 TR 클래스 초기화 완료: 환경={self.environment}, 채널ID={self.channel_id}")
    
    def _load_cache_config(self) -> Dict[str, Any]:
        """
        캐시 설정 파일을 로드
        
        Returns:
            Dict[str, Any]: 캐시 설정 정보
        """
        config_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "schema", "cache-config.json"
        )
        
        try:
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            else:
                logger.warning(f"캐시 설정 파일을 찾을 수 없음: {config_path}")
                return {}
        except Exception as e:
            logger.error(f"캐시 설정 로드 중 오류 발생: {str(e)}", exc_info=True)
            return {}
    
    def _init_gateway(self):
        """
        Java 게이트웨이 초기화
        KASS 라이브러리와 통신하기 위한 Py4J 게이트웨이 설정
        """
        try:
            # 개발 환경에서만 실행
            if self.environment == "local":
                return
            
            # JAR 파일 디렉토리 (.env 파일에서 로드)
            jar_dir = os.getenv("JAR_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "driver"))
            
            # JAR 파일 목록 구성
            jar_files = []
            if os.path.exists(jar_dir):
                for file in os.listdir(jar_dir):
                    if file.lower().endswith(".jar"):
                        jar_files.append(os.path.join(jar_dir, file))
            
            if jar_files:
                # 클래스패스 구성
                classpath = os.pathsep.join(jar_files)
                
                # 게이트웨이 시작
                port = launch_gateway(classpath=classpath, die_on_exit=True)
                self.gateway = JavaGateway(gateway_parameters=GatewayParameters(port=port))
                logger.info(f"Java 게이트웨이 초기화 완료: {len(jar_files)}개 JAR 파일 로드")
            else:
                logger.warning(f"JAR 파일을 찾을 수 없음: {jar_dir}")
                
        except Exception as e:
            logger.error(f"Java 게이트웨이 초기화 중 오류 발생: {str(e)}", exc_info=True)
    
    async def request_tr(
        self, tr_code: str, params: Dict[str, Any], continue_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        TR 요청을 수행하는 메서드
        
        Args:
            tr_code: TR 코드
            params: TR 요청 매개변수
            continue_key: 연속 조회 키 (옵션)
            
        Returns:
            Dict[str, Any]: TR 응답 데이터
        """
        logger.info(f"[TR-{tr_code}] 요청 시작")
        
        if self.environment == "local":
            # 로컬 환경(목 데이터)
            return await self._mock_tr_request(tr_code, params, continue_key)
        else:
            # 개발/운영 환경(실제 통신)
            return await self._real_tr_request(tr_code, params, continue_key)
    
    async def _mock_tr_request(
        self, tr_code: str, params: Dict[str, Any], continue_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        목 TR 요청 처리 (로컬 환경)
        
        Args:
            tr_code: TR 코드
            params: TR 요청 매개변수
            continue_key: 연속 조회 키 (옵션)
            
        Returns:
            Dict[str, Any]: 목 TR 응답 데이터
        """
        # 응답 시간 시뮬레이션
        await asyncio.sleep(0.1)
        
        # 기본 응답 헤더
        result = {
            "dataHeader": {
                "resultCode": "200",
                "resultMessage": "정상",
                "processFlag": "A",
                "category": "API"
            },
            "dataBody": {}
        }
        
        # 특수 TR 코드 처리
        if tr_code == "IVCA0060":
            # 지수 정보 TR
            ind_typ_cd = params.get("indTypCd", "")
            indx_id = "KG001P" if ind_typ_cd == "001" else "OG001P"
            
            result["dataBody"] = {
                "indxInfo": {
                    "indxId": indx_id,
                    "indxNm": "코스피 지수" if indx_id == "KG001P" else "해외 지수",
                    "indxVal": "2456.78",
                    "indxChg": "+12.34",
                    "indxChgRt": "+0.5%"
                }
            }
        elif tr_code.startswith("K"):
            # 일반 정보 TR
            result["dataBody"] = {
                "items": [
                    {"item_id": "1", "item_name": "항목1", "value": "100"},
                    {"item_id": "2", "item_name": "항목2", "value": "200"},
                    {"item_id": "3", "item_name": "항목3", "value": "300"}
                ]
            }
        else:
            # 기본 목업 데이터
            result["dataBody"] = {
                "result": "success",
                "timestamp": "2025-03-26T10:30:00",
                "requestParam": params
            }
        
        # 연속 조회 키가 있으면 반환
        if continue_key:
            result["dataHeader"]["contKey"] = continue_key + "_next"
        
        logger.info(f"[TR-{tr_code}] 목 응답 생성 완료")
        return result
    
    async def _real_tr_request(
        self, tr_code: str, params: Dict[str, Any], continue_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        실제 TR 요청 처리 (개발/운영 환경)
        
        Args:
            tr_code: TR 코드
            params: TR 요청 매개변수
            continue_key: 연속 조회 키 (옵션)
            
        Returns:
            Dict[str, Any]: 실제 TR 응답 데이터
        """
        if not self.gateway:
            logger.error("Java 게이트웨이가 초기화되지 않음")
            raise Exception("Java 게이트웨이 초기화 필요")
        
        try:
            # 비동기 실행 (별도 스레드에서 실행)
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None, self._execute_java_tr_request, tr_code, params, continue_key
            )
            
            logger.info(f"[TR-{tr_code}] 실제 응답 수신 완료")
            return result
        except Exception as e:
            logger.error(f"TR 요청 처리 중 오류 발생: {str(e)}", exc_info=True)
            return {
                "dataHeader": {
                    "resultCode": "500",
                    "resultMessage": f"오류: {str(e)}",
                    "processFlag": "E",
                    "category": "API"
                },
                "dataBody": {}
            }
    
    def _execute_java_tr_request(
        self, tr_code: str, params: Dict[str, Any], continue_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Java 라이브러리를 통한 TR 요청 실행 (블로킹)
        
        Args:
            tr_code: TR 코드
            params: TR 요청 매개변수
            continue_key: 연속 조회 키 (옵션)
            
        Returns:
            Dict[str, Any]: TR 응답 데이터
        """
        try:
            # HeaderWrap 생성
            header_wrap = self.gateway.jvm.com.kbsec.kass.dib.protocol.HeaderWrap()
            header_wrap.setChannelID(self.channel_id)
            
            # 연속 조회 설정
            if continue_key:
                header_wrap.setCont_flag("Y")
                header_wrap.setContkey_new(continue_key)
            
            # TrxRuleObject 생성
            trx_rule = self.gateway.jvm.com.kbsec.kass.transaction.TrxRuleObject(f"Tkb_{tr_code}")
            
            # 요청 데이터를 Java Map으로 변환
            java_map = self._dict_to_java_map(params)
            
            # IVCA0060 특수 처리
            if tr_code == "IVCA0060" and "indTypCd" in params:
                ind_typ_cd = params.get("indTypCd")
                
                if ind_typ_cd == "001":
                    java_map.put("indxId", "KG001P")
                elif ind_typ_cd == "301":
                    java_map.put("indxId", "OG001P")
            
            # TR 요청 실행
            result_code = trx_rule.rq(java_map, None, header_wrap)
            
            if result_code != 0:
                raise Exception(f"TR 요청 실패: {result_code}")
            
            # 응답 처리
            response = trx_rule.getResult().getOutput()
            
            # 응답 객체를 Python 딕셔너리로 변환
            result = self._java_to_python(response)
            
            # 기본 응답 형식 구성
            python_result = {
                "dataHeader": {
                    "resultCode": "200",
                    "resultMessage": "정상",
                    "processFlag": "A",
                    "category": "API"
                },
                "dataBody": {}
            }
            
            # 응답 데이터 필터링 및 구성
            for key, value in result.items():
                if not key.startswith("_") and not key.startswith("TRX_HEADER") and not key.startswith("filler"):
                    python_result["dataBody"][key] = value
            
            # 연속 키 처리
            if "TRX_HEADER" in result and "contKey" in result["TRX_HEADER"]:
                python_result["dataHeader"]["contKey"] = result["TRX_HEADER"]["contKey"]
            
            return python_result
            
        except Exception as e:
            logger.error(f"Java TR 요청 실행 중 오류 발생: {str(e)}", exc_info=True)
            raise
    
    def _dict_to_java_map(self, data: Dict[str, Any]) -> Any:
        """
        Python 딕셔너리를 Java HashMap으로 변환
        
        Args:
            data: Python 딕셔너리
            
        Returns:
            Any: Java HashMap 객체
        """
        java_map = self.gateway.jvm.java.util.HashMap()
        
        for key, value in data.items():
            if isinstance(value, dict):
                # 중첩 딕셔너리는 재귀적으로 변환
                java_map.put(key, self._dict_to_java_map(value))
            elif isinstance(value, list):
                # 리스트는 ArrayList로 변환
                java_list = self._list_to_java_list(value)
                java_map.put(key, java_list)
            else:
                # 기본 타입은 그대로 추가
                java_map.put(key, value)
        
        return java_map
    
    def _list_to_java_list(self, data: List[Any]) -> Any:
        """
        Python 리스트를 Java ArrayList로 변환
        
        Args:
            data: Python 리스트
            
        Returns:
            Any: Java ArrayList 객체
        """
        java_list = self.gateway.jvm.java.util.ArrayList()
        
        for item in data:
            if isinstance(item, dict):
                # 딕셔너리는 HashMap으로 변환
                java_list.add(self._dict_to_java_map(item))
            elif isinstance(item, list):
                # 중첩 리스트는 재귀적으로 변환
                java_list.add(self._list_to_java_list(item))
            else:
                # 기본 타입은 그대로 추가
                java_list.add(item)
        
        return java_list
    
    def _java_to_python(self, java_obj: Any) -> Dict[str, Any]:
        """
        Java 객체를 Python 딕셔너리로 변환
        
        Args:
            java_obj: Java 객체
            
        Returns:
            Dict[str, Any]: Python 딕셔너리
        """
        if not java_obj:
            return {}
        
        try:
            result = {}
            if hasattr(java_obj, "keySet"):
                key_set = java_obj.keySet()
                key_iter = key_set.iterator()
                
                while key_iter.hasNext():
                    key = key_iter.next()
                    value = java_obj.get(key)
                    
                    # 재귀적으로 변환
                    if hasattr(value, "keySet"):
                        result[key] = self._java_to_python(value)
                    elif hasattr(value, "size") and hasattr(value, "get"):
                        # 배열인 경우
                        result[key] = [
                            self._java_to_python(value.get(i)) if hasattr(value.get(i), "keySet")
                            else value.get(i)
                            for i in range(value.size())
                        ]
                    else:
                        result[key] = value
                
                return result
            else:
                # 기본 toString 사용
                return {"value": str(java_obj)}
            
        except Exception as e:
            logger.error(f"Java 객체 변환 중 오류 발생: {str(e)}", exc_info=True)
            return {"error": str(e)}
    
    def get_tr_code_by_alias(self, alias: str) -> Optional[str]:
        """
        별칭에 해당하는 TR 코드를 반환
        
        Args:
            alias: TR 별칭
            
        Returns:
            Optional[str]: TR 코드 또는 None
        """
        return self.alias_mapping.get(alias)
    
    def get_cache_ttl(self, tr_code: str) -> int:
        """
        TR 코드에 대한 캐시 TTL(Time-To-Live) 값을 반환
        
        Args:
            tr_code: TR 코드
            
        Returns:
            int: 캐시 TTL (초 단위)
        """
        tr = self.tr_rules.get(tr_code, {})
        if not tr:
            return 30  # 기본 TTL
        
        return tr.get("ttl", 30)
    
    def get_not_evict_tr_codes(self) -> List[str]:
        """
        캐시 삭제 대상에서 제외할 TR 코드 목록을 반환
        
        Returns:
            List[str]: 캐시 삭제 제외 TR 코드 목록
        """
        # 하드코딩된 예외 목록 (실제 구현에서는 설정에서 로드 가능)
        return ["KBI50130"]