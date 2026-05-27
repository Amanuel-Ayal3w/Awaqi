#!/usr/bin/env python3
"""
Script to evaluate the Awaqi RAG system using RAGAS.

Usage:
    uv run python scripts/evaluate_rag.py
    
This loads a test dataset, runs your RAG pipeline, and computes
RAGAS metrics (faithfulness, answer_relevancy, context_recall, context_precision).
"""

import json
import logging
import sys
from pathlib import Path
import asyncio

# Add package src to path so imports work (when running from repo root)
repo_root = Path(__file__).parent.parent
ai_engine_src = repo_root / "packages" / "ai-engine" / "src"
database_src = repo_root / "packages" / "database" / "src"
sys.path.insert(0, str(ai_engine_src))
sys.path.insert(0, str(database_src))
# Keep repo root as fallback
sys.path.insert(0, str(repo_root))

from ai_engine.evaluation import evaluate_rag
from ai_engine.rag_answer import answer_from_chunks

try:
    from ai_engine.hybrid_retrieval import load_chunks_by_ids, retrieve_fused_chunk_ids
except Exception:  # pragma: no cover
    load_chunks_by_ids = None
    retrieve_fused_chunk_ids = None

try:
    from database import AsyncSessionLocal
except Exception:  # pragma: no cover
    AsyncSessionLocal = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_test_dataset(filepath: str = "eval_dataset.json") -> dict:
    """
    Load test dataset from JSON file.
    
    Expected format:
    {
        "test_cases": [
            {
                "question": "What is tax...",
                "expected_answer": "Tax is...",
                "relevant_documents": ["doc1", "doc2"]
            }
        ]
    }
    """
    if not Path(filepath).exists():
        logger.warning(f"Test dataset not found at {filepath}")
        logger.info("Creating sample test dataset...")
        return create_sample_dataset()
    
    with open(filepath) as f:
        return json.load(f)


def create_sample_dataset() -> dict:
    """Create a sample test dataset for demonstration."""
    return {
        "test_cases": [
            {
                "question": "What is personal income tax in Ethiopia?",
                "expected_answer": "Personal income tax is levied on income earned by individuals.",
                "relevant_documents": ["income_tax_policy"],
            },
            {
                "question": "What are tax deductions?",
                "expected_answer": "Tax deductions are expenses that reduce taxable income.",
                "relevant_documents": ["deductions_guide"],
            },
            {
                "question": "When is the tax filing deadline?",
                "expected_answer": "The tax filing deadline is typically at the end of the fiscal year.",
                "relevant_documents": ["tax_calendar"],
            },
        ]
    }


async def run_rag_pipeline(question: str, db_session) -> tuple[str, list[str]]:
    """
    Run the RAG pipeline for a question.
    
    Returns:
        (answer, retrieved_contexts)
    """
    try:
        if not retrieve_fused_chunk_ids or not load_chunks_by_ids or db_session is None:
            answer_text, _citations, _confidence, _follow_ups = await answer_from_chunks(
                question,
                [],
                language="en",
            )
            return answer_text, []

        # Retrieve relevant chunks
        chunk_ids = await retrieve_fused_chunk_ids(
            db_session,
            question,
            taxpayer_category=None,
            fused_top=8,
            vector_limit=20,
            bm25_limit=20,
        )
        chunks = await load_chunks_by_ids(db_session, chunk_ids)
        
        # Extract context text
        contexts = [chunk.content for chunk in chunks]
        
        # Generate answer
        answer_text, _citations, _confidence, _follow_ups = await answer_from_chunks(
            question,
            chunks,
            language="en",
        )
        
        return answer_text, contexts
    except Exception as e:
        logger.error(f"Error running RAG pipeline: {e}")
        return "I could not generate an answer.", []


async def _main_async():
    """Run the evaluation."""
    logger.info("Starting RAGAS evaluation...")
    
    # Load test dataset
    dataset = load_test_dataset()
    
    if not dataset.get("test_cases"):
        logger.error("No test cases found in dataset")
        return
    
    # Prepare evaluation data
    questions = []
    answers = []
    contexts = []
    ground_truths = []
    
    if AsyncSessionLocal is None:
        logger.warning(
            "Database dependencies are not available (e.g. asyncpg missing). "
            "Running evaluation in offline mode (no retrieval)."
        )
        for test_case in dataset["test_cases"]:
            question = test_case.get("question")
            expected_answer = test_case.get("expected_answer")
            if not question:
                continue
            logger.info(f"Processing (offline): {question}")
            answer, retrieved_contexts = await run_rag_pipeline(question, None)
            questions.append(question)
            answers.append(answer)
            contexts.append(retrieved_contexts)
            ground_truths.append(expected_answer)
    else:
        async with AsyncSessionLocal() as db:
            for test_case in dataset["test_cases"]:
                question = test_case.get("question")
                expected_answer = test_case.get("expected_answer")

                if not question:
                    continue

                logger.info(f"Processing: {question}")

                # Run RAG pipeline
                answer, retrieved_contexts = await run_rag_pipeline(question, db)

                questions.append(question)
                answers.append(answer)
                contexts.append(retrieved_contexts)
                ground_truths.append(expected_answer)
    
    # Run RAGAS evaluation
    logger.info("Running RAGAS metrics...")
    results = await evaluate_rag(
        questions=questions,
        answers=answers,
        contexts=contexts,
        ground_truths=ground_truths,
    )
    
    # Print results
    print("\n" + "=" * 60)
    print("RAGAS EVALUATION RESULTS")
    print("=" * 60)
    print(f"Faithfulness Score:      {results.faithfulness_score:.4f}")
    print(f"Answer Relevancy Score:  {results.answer_relevancy_score:.4f}")
    print(f"Context Recall Score:    {results.context_recall_score:.4f}")
    print(f"Context Precision Score: {results.context_precision_score:.4f}")
    print("-" * 60)
    print(f"Overall Average Score:   {results.average_score:.4f}")
    print("=" * 60)
    
    # Save results
    results_file = "evaluation_results.json"
    with open(results_file, "w") as f:
        json.dump(
            {
                "faithfulness": float(results.faithfulness_score),
                "answer_relevancy": float(results.answer_relevancy_score),
                "context_recall": float(results.context_recall_score),
                "context_precision": float(results.context_precision_score),
                "overall": float(results.average_score),
            },
            f,
            indent=2,
        )
    logger.info(f"Results saved to {results_file}")


if __name__ == "__main__":
    asyncio.run(_main_async())
