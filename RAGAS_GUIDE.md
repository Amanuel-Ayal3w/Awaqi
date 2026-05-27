# RAGAS Evaluation Guide for Awaqi

## Overview

RAGAS (Retrieval-Augmented Generation Assessment) is a framework for evaluating RAG systems without requiring human annotations. It uses LLM-based metrics to assess the quality of your QA system.

## Metrics Explained

### 1. **Faithfulness** (0-1 score)
- **What it measures**: Does the generated answer derive information from the retrieved context?
- **How it works**: Uses an LLM to check if all statements in the answer are supported by the context
- **Ideal range**: 0.8-1.0 (higher is better)
- **Interpretation**:
  - High (>0.8): Answer is well-grounded in retrieved documents
  - Low (<0.5): Answer makes claims not supported by context (hallucinations)

### 2. **Answer Relevancy** (0-1 score)
- **What it measures**: Is the generated answer actually relevant to the question?
- **How it works**: LLM evaluates if the answer directly addresses the question
- **Ideal range**: 0.8-1.0 (higher is better)
- **Interpretation**:
  - High (>0.8): Answer directly addresses the user's question
  - Low (<0.5): Answer is off-topic or misses the point

### 3. **Context Recall** (0-1 score)
- **What it measures**: Are all relevant documents included in the retrieved context?
- **How it works**: Compares retrieved context against ground truth (expected answer)
- **Ideal range**: 0.8-1.0 (higher is better)
- **Interpretation**:
  - High (>0.8): Retrieval system finds most relevant documents
  - Low (<0.5): Retrieval system misses important documents
  - **Note**: Requires `ground_truths` parameter to be meaningful

### 4. **Context Precision** (0-1 score)
- **What it measures**: Are the retrieved documents relevant to answering the question?
- **How it works**: Measures the ratio of relevant documents in the retrieved set
- **Ideal range**: 0.7-1.0 (higher is better)
- **Interpretation**:
  - High (>0.7): Retrieved documents are relevant and focused
  - Low (<0.3): Retrieved results contain much irrelevant content

## Getting Started

### Prerequisites

```bash
# Ensure RAGAS is installed
uv add ragas -p packages/ai-engine

# Ensure your .env has Google API credentials
export GOOGLE_API_KEY="your_api_key"
```

### Step 1: Prepare Your Test Dataset

Edit `eval_dataset.json` with your test cases:

```json
{
  "test_cases": [
    {
      "question": "What is personal income tax?",
      "expected_answer": "Personal income tax is a tax on earnings...",
      "relevant_documents": []
    }
  ]
}
```

### Step 2: Run Evaluation

```bash
cd /home/debbie/Desktop/Awaqi
uv run python scripts/evaluate_rag.py
```

### Step 3: Review Results

The script outputs metrics and saves results to `evaluation_results.json`:

```
============================================================
RAGAS EVALUATION RESULTS
============================================================
Faithfulness Score:      0.8234
Answer Relevancy Score:  0.7891
Context Recall Score:    0.6542
Context Precision Score: 0.8756
------------------------------------------------------------
Overall Average Score:   0.7856
============================================================
```

## Interpreting Your Results

### Overall Score > 0.8
✅ **Excellent**: Your RAG system is performing well

### Overall Score 0.6-0.8
⚠️ **Good but needs improvement**: 
- Investigate which metric is pulling down the score
- Review failing test cases for patterns
- Consider improving retrieval or generation

### Overall Score < 0.6
❌ **Poor performance**: 
- Check if RAG pipeline is working correctly
- Verify test dataset quality
- Consider re-indexing documents or adjusting retrieval parameters

## Improving Your Scores

### To improve Faithfulness:
1. Ensure retrieved documents are high quality
2. Use better chunking strategy
3. Add grounding instructions to your prompt
4. Filter out low-confidence chunks

### To improve Answer Relevancy:
1. Improve your retrieval system (context precision)
2. Refine prompt instructions to focus on the question
3. Add examples of good answers to your prompt
4. Use a more capable generation model

### To improve Context Recall:
1. Increase `top_k` in retrieval (retrieve more chunks)
2. Improve embedding quality
3. Better document chunking and metadata
4. Use hybrid search (BM25 + semantic)
5. Review ground truth - is it achievable?

### To improve Context Precision:
1. Reduce `top_k` if you're retrieving too much
2. Add better filtering/reranking
3. Use semantic similarity thresholds
4. Implement query expansion for better retrieval
5. Use multi-query retrieval

## Advanced Usage

### Custom Evaluation with Your Own Metrics

```python
from ragas.metrics import custom_metric
from ragas import evaluate

# Define a custom metric
custom_metric = custom_metric(
    name="custom_score",
    metric_type="retriever",  # or "generator"
    evaluation_fn=your_eval_function,
)

results = await evaluate(
    dataset=dataset,
    metrics=[faithfulness, custom_metric],
    llm=evaluator_llm,
)
```

### Continuous Evaluation

Create a CI/CD pipeline that runs RAGAS on each deployment:

```bash
# Add to your CI pipeline
uv run python scripts/evaluate_rag.py
# Fail if average score < 0.75
```

### A/B Testing RAG Changes

Run evaluation before and after changes:

```bash
# Before change
uv run python scripts/evaluate_rag.py > baseline.json

# Make changes to RAG pipeline

# After change  
uv run python scripts/evaluate_rag.py > new_version.json

# Compare results
```

## Troubleshooting

### "GOOGLE_API_KEY not set"
```bash
export GOOGLE_API_KEY="your_key_here"
```

### "No test cases found"
- Ensure `eval_dataset.json` exists in repo root
- Check JSON format is valid

### Low scores on all metrics
1. Check that documents are being indexed correctly
2. Verify RAG pipeline is connected properly
3. Test with a few manual examples
4. Check if embeddings are being computed

### Context Recall < 0.5
- Provide meaningful `ground_truths` in test cases
- Add more test cases
- Review if ground truth is actually in your knowledge base

## Next Steps

1. **Establish a baseline**: Run evaluation on current system
2. **Identify weaknesses**: See which metrics need improvement
3. **Iterate**: Make targeted changes and re-evaluate
4. **Monitor**: Track scores over time as you improve the system
5. **Automate**: Integrate into your CI/CD pipeline

## Resources

- [RAGAS Documentation](https://docs.ragas.io/)
- [RAG Evaluation Best Practices](https://docs.ragas.io/en/latest/evaluation/)
- [Awaqi RAG Architecture](./ARCHITECTURE.md)

