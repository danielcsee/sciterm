"""OpenAI integration: intent routing, cited answers, and the entities they name."""

from api.llm.analysis import AnalysisPassage, stream_analysis
from api.llm.answer_entities import find_answer_entities
from api.llm.client import LlmClient, LlmError, get_llm_client
from api.llm.intent import classify_intent
from api.llm.models import AnswerEntity, IntentEntity, IntentResult
from api.llm.tools import INTENT_TOOLS, IntentToolName

__all__ = [
    "AnalysisPassage",
    "AnswerEntity",
    "INTENT_TOOLS",
    "IntentEntity",
    "IntentResult",
    "IntentToolName",
    "LlmClient",
    "LlmError",
    "classify_intent",
    "find_answer_entities",
    "get_llm_client",
    "stream_analysis",
]
