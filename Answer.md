# Technical Questions & Answers

## 1. Telegram Bot
The Telegram bot provides an alternative interface to the web application, allowing users to interact with the ERA tax support system directly through Telegram messaging. This increases accessibility, especially for users who prefer messaging apps over web browsers. The bot will have feature parity with the web interface, handling the same queries and providing the same quality responses.

## 2. Naive RAG Limitations
Naive RAG systems have several limitations:
- **Keyword Mismatch**: Pure semantic search may miss exact legal terms or Proclamation numbers
- **Context Loss**: Single retrieval step may not capture nuanced relationships
- **No Confidence Scoring**: Cannot determine when to escalate to human agents
- **Poor Multilingual Handling**: Struggles with code-switched queries (mixed Amharic-English)
- **Citation Issues**: May generate responses without proper source attribution

Our hybrid approach addresses these by combining BM25 keyword matching with dense retrieval, adding confidence scoring, and implementing proper citation validation.

## 3. BM25 Knowledge Base Storage
For BM25 (sparse retrieval), we'll use **PostgreSQL with full-text search** instead of Elasticsearch to maintain a consistent stack. PostgreSQL's built-in full-text search supports:
- Inverted indexes for fast keyword lookup
- Ranking algorithms similar to BM25
- Multi-language support including custom dictionaries
- Integration with our existing PostgreSQL database

The equivalent of vector store for BM25 is the **inverted index** stored in PostgreSQL's `tsvector` columns.

## 4. NLU Pipeline Component Values

### Language Detection
- **Value**: Routes queries to appropriate language-specific processing pipelines
- **Importance**: Ensures proper tokenization (Amharic uses different morphology than English)
- **Impact**: Improves downstream NLU accuracy by 15-20%

### Tokenization
- **Value**: Correctly segments text into meaningful units
- **Amharic Specific**: Handles Ethiopic script's complex morphology and compound words
- **Impact**: Foundation for all subsequent NLP tasks

### Intent Classification
- **Value**: Determines what the user wants (Information, Procedure, Definition, Clarification)
- **Impact**: Routes to appropriate response templates and retrieval strategies
- **Business Value**: Enables personalized responses based on user intent

### Entity Extraction
- **Value**: Identifies key entities (TIN numbers, Proclamation references, amounts, dates)
- **Impact**: Enables targeted retrieval and validation of specific legal references
- **Example**: Extracting "285/2002" enables direct lookup of VAT Proclamation

## 5. Zero-Shot in XLM-RoBERTa
**Zero-shot** means the model can classify intents without being specifically trained on Ethiopian tax domain data. We provide the model with:
- Intent categories: ["Informational", "Procedural", "Definitional", "Clarification"]
- The user query
- A prompt template

The model uses its pre-trained multilingual knowledge to classify the query into one of these categories without needing labeled Ethiopian tax examples.

## 6. Entity Extraction Enhancement

### Current RegEx Approach Limitations:
- **TIN Numbers**: `\b\d{10}\b` (works well)
- **Proclamation Numbers**: `\b\d{3}/\d{4}\b` (works well)
- **Amounts**: `\b\d+(\.\d+)?\s*(ETB|Birr)\b` (moderate success)
- **Dates**: Complex patterns, moderate success

### Better Approach: Small LLM for Entity Extraction
Use **Gemini 2.5 Flash** with structured prompts:
```
Extract entities from: "{user_query}"
Return JSON: {
  "tin_numbers": [],
  "proclamations": [],
  "amounts": [],
  "dates": [],
  "tax_types": []
}
```
This approach is more robust and can handle variations, typos, and context-dependent entities.

## 7. Sparse Retrieval (BM25) Value

### Why BM25?
- **Exact Matches**: Critical for legal terms like "Proclamation 285/2002"
- **Keyword Precision**: Finds documents containing specific tax terminology
- **Complementary**: Covers cases where semantic search fails

### Amharic Support:
BM25 works with Amharic text but requires:
- Proper tokenization (SentencePiece handles this)
- Amharic stopword lists
- Stemming rules for Amharic morphology

### Beyond Exact Match:
- **Fuzzy Matching**: Handle typos in Proclamation numbers
- **Synonym Expansion**: Map "VAT" ↔ "ተጨማሪ እሴት ታክስ"
- **Abbreviation Handling**: "MoR" ↔ "Ministry of Revenue"

## 8. Fusion vs Reranking

### Reciprocal Rank Fusion (RRF):
- **Purpose**: Combines rankings from BM25 and dense retrieval
- **Method**: Uses rank positions, not raw scores
- **Formula**: `RRF_score = Σ 1/(k + rank_i)` where k=60
- **Advantage**: Robust to score scale differences between systems

### Cross-Encoder Reranking:
- **Purpose**: Final relevance scoring of top candidates
- **Method**: Uses a transformer model (ms-marco-MiniLM) to score query-document pairs
- **Input**: Takes query + document text as single input
- **Output**: Relevance score between 0-1

### How They Determine Relevance:
1. **RRF**: Documents appearing high in both BM25 and dense results get highest scores
2. **Cross-Encoder**: Uses deep attention mechanisms to understand query-document relationships
3. **Training**: Cross-encoder is trained on query-document relevance pairs

## 9. Evaluation Metrics Detailed Explanation

### Accuracy Metrics

#### Exact Match (EM)
- **How it works**: Compares generated answer with ground truth character-by-character
- **Measurement**: `EM = (Exact matches / Total questions) × 100%`
- **Category fit**: Measures precise factual accuracy
- **Use case**: Best for short, factual answers like "VAT rate is 15%"

#### F1 Score
- **How it works**: Harmonic mean of precision and recall at token level
- **Calculation**: `F1 = 2 × (Precision × Recall) / (Precision + Recall)`
- **Category fit**: Balances completeness vs accuracy
- **Use case**: Good for longer explanatory answers

#### Top-K Retrieval Accuracy
- **How it works**: Checks if correct source document appears in top-K retrieved results
- **Measurement**: `Top-K = (Queries with correct doc in top-K / Total queries) × 100%`
- **Category fit**: Measures retrieval system effectiveness
- **Impact**: If retrieval fails, generation will definitely fail

### Response Quality Metrics

#### ROUGE-L
- **How it works**: Measures longest common subsequence between generated and reference text
- **Calculation**: Based on recall and precision of longest common subsequences
- **Category fit**: Captures content overlap and ordering
- **Advantage**: Less sensitive to exact wording than EM

#### BERTScore
- **How it works**: Uses BERT embeddings to compute semantic similarity
- **Measurement**: Cosine similarity between contextualized embeddings
- **Category fit**: Captures semantic meaning beyond surface text
- **Advantage**: Rewards paraphrases that preserve meaning

#### Citation Accuracy
- **How it works**: Verifies that cited sources actually support the generated claims
- **Measurement**: `Citation Accuracy = (Correct citations / Total citations) × 100%`
- **Category fit**: Critical for legal/regulatory domain
- **Method**: Extract claims from answer, check against cited document chunks

### User Experience Metrics

#### Response Latency
- **How it works**: Measures time from query submission to response display
- **Measurement**: End-to-end response time in seconds
- **Category fit**: Directly impacts user satisfaction
- **Target**: <5 seconds for 95% of queries

#### Session Success Rate
- **How it works**: Percentage of sessions where user query is resolved without escalation
- **Measurement**: `Success Rate = (Resolved sessions / Total sessions) × 100%`
- **Category fit**: Measures overall system effectiveness
- **Indicators**: User doesn't ask for human agent, doesn't repeat similar questions

#### Escalation Rate
- **How it works**: Percentage of queries that require human intervention
- **Measurement**: `Escalation Rate = (Human escalations / Total queries) × 100%`
- **Category fit**: Measures system limitations and cost impact
- **Triggers**: Low confidence scores, explicit user requests for human help

### Robustness Metrics

#### Hallucination Rate
- **How it works**: Manual review of random sample to identify unsupported claims
- **Measurement**: `Hallucination Rate = (Responses with false claims / Sample size) × 100%`
- **Category fit**: Critical safety metric for legal domain
- **Method**: Expert reviewers check if generated claims are supported by retrieved documents

#### Multilingual Parity
- **How it works**: Compares accuracy metrics between Amharic and English queries
- **Measurement**: `Parity = |Accuracy_Amharic - Accuracy_English|`
- **Category fit**: Ensures fair service across languages
- **Target**: ≤5% difference in key metrics between languages