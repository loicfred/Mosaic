from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.config import get_settings
from app.core.errors import AppError
from app.llm.groq import LLMError, LLMRateLimited
from app.schemas.assistant import AnswerOut, AskIn
from app.security.deps import AuthContext, get_context
from app.security.rate_limit import limiter
from app.services import assistant_service, import_service, opportunity_service
from app.services.analysis_service import get_analysis

router = APIRouter(prefix="/insight", tags=["insight"])


@router.post("/ask", response_model=AnswerOut)
def ask(body: AskIn, ctx: AuthContext = Depends(get_context)) -> AnswerOut:
    s = get_settings()
    if not s.external_ai_enabled:
        raise AppError(503, "llm_unavailable", "The AI assistant is not configured (GROQ_API_KEY is not set).")
    allowed, retry = limiter.hit(f"llm:{ctx.user.id}", s.llm_rate_limit, s.llm_rate_window_seconds)
    if not allowed:
        raise AppError(429, "llm_rate_limited", "You have asked a lot of questions in a short time.",
                       {"retry_after": retry, "scope": "valora"})
    a = get_analysis(ctx.db, ctx.business)
    opps = opportunity_service.list_opportunities(ctx.db, ctx.business_id, None, False)
    pending = len(import_service.list_proposals(ctx.db, ctx.business_id, "pending", None))
    try:
        return assistant_service.ask(body, a, opps, ctx.business.name, pending)
    except LLMRateLimited as e:
        raise AppError(429, "llm_rate_limited", "The AI assistant has reached its free-tier limit for the moment.",
                       {"retry_after": e.retry_after, "scope": "groq"}) from None
    except LLMError as e:
        raise AppError(503, "llm_unavailable", "The AI assistant is unavailable right now.", {"reason": str(e)}) from None
