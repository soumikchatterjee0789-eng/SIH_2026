"""
AI Financial Intelligence Engine Package.
Includes Context Synthesizer (RAG), Multi-Model LLM Gateway, and Deep Financial Reasoner.
"""
from app.services.ai_engine.context_builder import build_user_financial_context, FinancialContext
from app.services.ai_engine.llm_gateway import LLMGateway
from app.services.ai_engine.deep_reasoner import DeepFinancialReasoner

__all__ = ["build_user_financial_context", "FinancialContext", "LLMGateway", "DeepFinancialReasoner"]
