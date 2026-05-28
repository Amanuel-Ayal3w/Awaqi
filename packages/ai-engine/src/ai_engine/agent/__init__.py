"""
Awaqi Max — ReAct agent that wraps the existing RAG pipeline.

The agent can:
  - call the internal KB hybrid retriever (rag_search) with refined queries,
    iterating until it has enough grounded evidence;
  - call an Ethiopian-grounded web search (ethiopian_web_search) that biases
    Google Search toward .et / mor.gov.et / official Ethiopian sources via
    Gemini's built-in google_search grounding tool;
  - synthesise a final, cited answer.

See ``docs/awaqi-max.md`` for the architecture write-up.
"""

from ai_engine.agent.react_agent import AgentResult, AgentTrace, run_awaqi_max

__all__ = ["AgentResult", "AgentTrace", "run_awaqi_max"]
