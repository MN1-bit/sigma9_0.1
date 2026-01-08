# ═══════════════════════════════════════════════════════════════════════════
# Oracle (LLM) Endpoints
# ═══════════════════════════════════════════════════════════════════════════
#
# 📌 역할:
#     LLM 모델 목록 조회 및 종목 분석 요청 API
#
# 📌 엔드포인트:
#     GET  /oracle/models   - LLM 모델 목록 조회
#     POST /oracle/analyze  - 종목 분석 요청
#
# ═══════════════════════════════════════════════════════════════════════════

from fastapi import APIRouter, HTTPException
from loguru import logger

from .models import AnalysisRequest
from .common import get_timestamp


router = APIRouter()


@router.get("/oracle/models", summary="LLM 모델 목록")
async def get_oracle_models():
    """
    사용 가능한 LLM 모델 목록을 조회합니다.
    """
    try:
        from backend.llm.oracle import oracle_service
        return await oracle_service.get_available_models()
    except Exception as e:
        logger.error(f"Failed to get oracle models: {e}")
        return {"providers": [], "error": str(e)}


@router.post("/oracle/analyze", summary="종목 분석 요청")
async def analyze_ticker(request: AnalysisRequest):
    """
    종목에 대한 LLM 분석을 요청합니다.
    """
    try:
        from backend.llm.oracle import oracle_service
        
        prompt = f"Analyze ticker {request.ticker}."
        if request.question:
            prompt += f" Question: {request.question}"
        
        result = await oracle_service.analyze(prompt, request.provider, request.model)
        return {
            "ticker": request.ticker,
            "analysis": result,
            "timestamp": get_timestamp()
        }
    except Exception as e:
        logger.error(f"Oracle analysis failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
