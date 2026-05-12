**College of Technology and Built Environment**

**School of Information Technology and Engineering**

**Department of IT/SE Eng.**

**LLM-Based Support Bot for Ethiopian Revenue Authority to enhance information desk service for tax payers and business** **owners**

**Software Design Specification**

**Team Members**

1\. Abdurahman Mohammed …ATE/8901/13

2\. Amanuel Ayalew…………….ATE/3871/13

3\. Basliel selamu .....................ATE/6761/13

4\. Bethel Wondowssen............ATE/8712/13

5\. Diborah Dereje.....................ATE/1712/13

**Advisor: Mr Daniel Date: Dec 27, 2025**

**Table of Contents**

[List of Tables 2](#_heading=h.9lhuqvsf828n)

[List of figures 3](#_heading=h.c3joa1dcimz8)

[Definitions, Acronyms, Abbreviations 4](#_heading=h.eytx5wtl80ie)

[**1**. **Introduction** 1](#_heading=h.i8lf0dpstvxx)

[1.1 Purpose 1](#_heading=h.yy1j58a4l381)

[1.2 General Overview 1](#_heading=h.y7qf939is8r9)

[1.3Development Methods & Contingencies 1](#_heading=h.k25h67dwn15k)

[**2\. System Architecture** 2](#_heading=h.9uzao4r9xhku)

[2.1 Subsystem decomposition 2](#_heading=h.nxn4e1aivd2q)

[**3\. Object Model 5**](#_heading=h.bwj8xy7v0ior)

[**3.1 Class Diagram 5**](#_heading=h.8n5mbxkpxudt)

[3.2 Sequence Diagram 7](#_heading=h.ssrwi91j0g64)

[3.3 State chartDiagram 10](#_heading=h.p5yvy6v5xpuy)

[**4\. Detailed Design 11**](#_heading=)

[4.2 Class: Admin (Inherits from User) 13](#_heading=h.smmrjgjmtzdg)

[4.3 Class ChatSession 15](#_heading=h.ymncpdo5ee9)

[4.4 Class KnowledgeEngine (RAG Controller) 17](#_heading=h.v6nblka28kyi)

[4.5 Class WebScraper 20](#_heading=h.19wgnx3j7lov)

[4.6 Algorithm Design 22](#_heading=h.i35isom9h6v9)

[4.6.1 Retrieval Augmented Generation (RAG) Flow 22](#_heading=h.bc8n8nui622)

[4.6.2 Vector Similarity Search (Cosine Similarity) 22](#_heading=h.m1smxfk69ir)

[4.6.3 Text Chunking Algorithm (Sliding Window) 23](#_heading=h.d98h5ypuzu0o)

[**5\. References 24**](#_heading=h.dw3urs9wkvz8)

# List of Tables

1.  Table 4.1: Attributes description for Document class
2.  Table 4.2: Operation description for Document class
3.  Table 4.3: Attributes description for Admin class
4.  Table 4.4: Operation description for Admin class
5.  Table 4.5: Attributes description for ChatSession class
6.  Table 4.6: Operation description for ChatSession class
7.  Table 4.7: Attributes description for KnowledgeEngine class
8.  Table 4.8: Operation description for KnowledgeEngine class
9.  Table 4.9: Attributes description for WebScraper class
10. Table 4.10: Operation description for WebScraper class

# List of figures

1.  Architecture Diagram
2.  Class Diagram Part 1: Domain Layer (Data Model)
3.  Class Diagram Part 2: Application Layer (Controllers & Services)
4.  Class Diagram Part 3: Infrastructure Layer (External Interfaces)
5.  Figure 1: Standard RAG Conversation Flow (Success Scenario)
6.  Figure 2: Session Validation & Security Flow
7.  Figure 3: Error Handling & Fallback Strategy
8.  State Chart Diagram: System Logic Tree (Decision Flow)

# Definitions, Acronyms, Abbreviations

| **Acronym/Term** | **Definition** | **Context/Source** |
| --- | --- | --- |
| **RAG** | Retrieval Augmented Generation | Defined as the system's core method for answering questions based on facts<sup>1111</sup>. |
| --- | --- | --- |
| **LLM** | Large Language Model | Described as the AI component used to generate responses. |
| --- | --- | --- |
| **MoR** | Ministry of Revenue | The source of the regulatory documents ingested by the system<sup>3</sup>. |
| --- | --- | --- |
| **OOD** | Object-Oriented Design | The methodology used to model interactions between Users, Documents, and the Chat Engine. |
| --- | --- | --- |
| **RBAC** | Role-Based Access Control | The architecture used to enforce boundary controls and privileges. |
| --- | --- | --- |
| **JWT** | JSON Web Token | The token format used to validate and authorize Administrator sessions. |
| --- | --- | --- |
| **CRUD** | Create, Read, Update, Delete | The set of capabilities granted to Administrators regarding the Knowledge Base. |
| --- | --- | --- |
| **OCR** | Optical Character Recognition | Listed as a component of the DocumentProcessor within the Ingestion Subsystem. |
| --- | --- | --- |
| **UUID** | Universally Unique Identifier | The data type used for unique identification of documents and sessions. |
| --- | --- | --- |

# 1\. Introduction

## 1.1 Purpose

The purpose of this System Design document is to translate the business requirements and business processes defined in the SRS into a technical design that will be used to develop the LLM-Based Support Bot for the Ethiopian Revenue Authority. This document describes the system architecture, subsystem decomposition, and detailed object models required to implement the advanced Retrieval Augmented Generation (RAG) system with hybrid search capabilities.

## 1.2 General Overview

The system is designed as an AI-powered information desk agent accessible via web interface and Telegram bot, capable of answering tax-related queries in Amharic and English. Unlike generic RAG implementations, this system employs a **hybrid retrieval architecture** combining BM25 keyword matching with dense vector search, specifically optimized for Ethiopian tax terminology and Amharic language processing.

The system operates by:
1. Ingesting regulatory documents from the Ministry of Revenue (MoR) website
2. Converting documents into vector embeddings using multilingual models (multilingual-e5-large)
3. Implementing dual retrieval paths (BM25 + semantic) with Reciprocal Rank Fusion
4. Using a Large Language Model (LLM) to generate regulation-grounded responses with mandatory citations
5. Applying confidence scoring to prevent hallucinations and trigger appropriate fallbacks

## 1.3 Development Methods & Contingencies

**Methodology:** The system design utilizes **Object-Oriented Design (OOD)** principles to model the interaction between Users, Documents, and the Chat Engine. The development follows an **Agile** approach with iterative sprints, allowing for rapid adjustment of the LLM prompts and retrieval parameters.

**Technologies:**

1.  **Backend:** Python (FastAPI) for high-performance API handling.
2.  **Frontend:** Next.js (React with TypeScript) for responsive web interface and Telegram bot integration.
3.  **AI/ML:** LangChain for orchestration, Gemini 2.5 Flash for inference, multilingual-e5-large for embeddings.
4.  **Database:** PostgreSQL with pgvector extension for vector storage and built-in full-text search for BM25-style keyword matching.
5.  **NLU:** XLM-RoBERTa for intent classification, fastText for language detection.

**Contingencies:**

1.  **LLM Latency:** If external APIs (e.g., OpenAI) experience high latency (>5s), the design supports swapping the LLMService interface for a local, quantized Llama 3 8B model running on the host server.
2.  **Scraper Blocking:** If the MoR website changes its DOM structure, the Scraper module is isolated as a microservice. This allows the team to update the scraping logic without redeploying the core chat.
3.  **Low Confidence Responses:** If retrieval confidence falls below 0.6 threshold, the system returns a standardized fallback message rather than potentially hallucinated content.

# 2.System Architecture

## 2.1 Subsystem decomposition

The system is decomposed into four major subsystems to ensure separation of concerns.

1.  **Client Subsystem (Frontend):**
    1.  Responsible for rendering the chat interface, handling user input, and displaying markdown responses.
    2.  **Components:** ChatUI, HistoryManager, APIConnector.
2.  **API Subsystem (Backend Controller):**
    1.  Acts as the central controller, managing session state and routing requests.
    2.  **Components:** Nestn js, SessionManager, RateLimiter.
3.  **Intelligence Subsystem (RAG Engine):**
    1.  Responsible for semantic search and answer generation.
    2.  **Components:** EmbeddingEngine, VectorStoreClient (Pinecone), LLMClient.
4.  **Ingestion Subsystem (Data Pipeline):**
    1.  Background workers that keep the knowledge base current.
    2.  **Components:** WebScraper, DocumentProcessor (OCR), ChunkingService.

**Hybrid Storage Architecture** The system employs a dual-storage strategy to handle different user types efficiently:

- **Persistent Storage (PostgreSQL):** Used exclusively for Registered Users to store profiles and long-term chat history.
- **Volatile Storage (Redis + RAM):** Used for Guest Users. Redis tracks IP addresses for rate limiting (with a 10-minute Time-To-Live), while the application RAM holds the active conversation context. This ensures guest data is naturally purged when the session ends.


Architecture Diagram 

@startuml
skinparam style strictuml
skinparam componentStyle uml2
top to bottom direction

title Figure 1: High-Level System Architecture (Hybrid RAG)

package "Client Layer" {
    [React Frontend] as UI
    [Telegram Bot] as TG
    note right of UI
      Handles User Input
      & Guest Context (RAM)
    end note
}

package "API Gateway Layer" {
    [FastAPI Controller] as API
    [Auth Middleware] as Auth
    [Rate Limiter] as RL
}

package "NLU Pipeline" {
    [Language Detector] as LangDet
    [Intent Classifier] as Intent
    [Entity Extractor] as Entity
    note bottom of Intent
      XLM-RoBERTa
      (Pre-trained)
    end note
}

package "Hybrid Retrieval (RAG)" {
    [BM25 Sparse Search] as BM25
    [Dense Vector Search] as Dense
    [Reciprocal Rank Fusion] as RRF
    [Cross-Encoder Reranker] as Rerank
}

package "Generation & Confidence" {
    [Prompt Constructor] as Prompt
    [LLM Service] as LLM
    [Confidence Scorer] as Conf
    [Citation Validator] as Cite
}

package "Data Persistence Layer" {
    database "Redis Cache" as Redis
    database "PostgreSQL" as DB
    database "Elasticsearch" as ES
}

package "External Infrastructure" {
    cloud "pgvector (PostgreSQL)" as Vectors
    cloud "Gemini 2.5 Flash" as LLMAPI
}

' Connections
UI --> API : HTTPS / JSON
TG --> API : Telegram API
API --> Auth : Validate Request
API --> RL : Check Rate Limit
RL --> Redis : IP Counter

API --> LangDet : Detect Language
LangDet --> Intent : Classify Intent
Intent --> Entity : Extract Entities

Entity --> BM25 : Query Terms
Entity --> Dense : Query Vector
BM25 --> DB : Full-text Search
Dense --> Vectors : Semantic Search
BM25 --> RRF : Sparse Results
Dense --> RRF : Dense Results
RRF --> Rerank : Fused Candidates
Rerank --> Prompt : Top-5 Chunks

Prompt --> LLM : Constructed Prompt
LLM --> LLMAPI : Inference
LLMAPI --> Conf : Response + Logits
Conf --> Cite : Validate Sources
Cite --> API : Final Response

API --> DB : Save History (Registered Only)

@enduml




### **2.2 Hardware/Software Mapping**

The system architecture abstracts the software layer from the underlying hardware through a containerized deployment strategy. While the application is inherently platform-independent, it is explicitly optimized for a Docker environment. This approach ensures operational consistency across development, testing, and production stages by encapsulating all necessary dependencies within the container. Consequently, the system can be deployed seamlessly on any host operating system that supports containerization, eliminating hardware-specific compatibility issues.

### **2.3 Access Control**

To ensure data integrity and system security, the platform enforces strict boundary controls using a Role-Based Access Control (RBAC) architecture. This model clearly delineates privileges between transient public interactions and privileged administrative operations.

**Public User Access** The Public User role is designed to prioritize accessibility and ease of use for taxpayers. To lower the barrier to entry, the system utilizes anonymous authentication, assigning a unique Session ID managed via browser cookies rather than requiring formal login credentials. The permissions for this role are strictly scoped to "read-only" interactions within the Chat Interface. This allows users to submit queries and review their specific session history, while ensuring they cannot modify the system's underlying configuration or data.

**Administrator Access** In contrast, the Administrator role is granted comprehensive control over the system's operational and data layers. Access to this role is secured through a robust authentication process requiring valid credentials (username and password), which are subsequently validated via a JSON Web Token (JWT). Administrators possess full CRUD (Create, Read, Update, Delete) capabilities regarding the Knowledge Base. Their operational scope extends to critical maintenance tasks, including the manual ingestion of documents, auditing of error logs, execution of manual scraping triggers, and the mitigation of security threats through IP blacklisting.

# 3\. Object Model3.1 Class Diagram

domain class Diagram 

@startuml
skinparam style strictuml
skinparam classAttributeIconSize 0
skinparam linetype ortho
skinparam nodesep 50
skinparam ranksep 50
top to bottom direction
hide empty members

title Class Diagram Part 1: Domain Layer (Data Model)

package "User Entities" {
    
    abstract class "BaseUser" {
        + userType: UserRole
        + {abstract} validateAccess(): Boolean
        + initiateChat(): ChatSession
    }

    class "Guest" {
        - clientIP: String
        - tempCategory: TaxPayerType
        + setCategory(type: TaxPayerType)
        + validateAccess(): CheckRedisLimit
    }

    class "RegisteredUser" {
        - userID: UUID
        - email: String
        - passwordHash: String
        - profileCreated: Date
        + login(password): Boolean
        + validateAccess(): VerifyToken
    }
}

package "Chat Entities" {

    class "ChatSession" {
        + sessionID: UUID
        + isEphemeral: Boolean
        + createdAt: DateTime
        + endSession()
    }

    class "Message" {
        + content: String
        + timestamp: DateTime
        + sender: SenderRole
        + citations: List<String>
    }
}

' Relations
BaseUser <|-- Guest
BaseUser <|-- RegisteredUser
BaseUser "1" -- "0..*" ChatSession : owns >
ChatSession "1" *-- "0..*" Message : contains >
Guest -[hidden]down-> ChatSession

note bottom of Guest: ID = clientIP (RAM)
note bottom of RegisteredUser: ID = UUID (DB)
@enduml



part 2 


@startuml
skinparam style strictuml
skinparam classAttributeIconSize 0
hide empty members
title Class Diagram Part 2: Application Layer (Controllers & Services)

package "Controllers (API)" {
    class "ChatController" {
        + sendMessage(req: ChatRequest): ChatResponse
        + getHistory(userID: UUID): List<Message>
        + handleTelegram(update: TelegramUpdate): void
    }
}

package "NLU Services" {
    class "LanguageDetector" {
        + detect(text: String): LanguageCode
    }
    
    class "IntentClassifier" {
        + classify(text: String): IntentResult
        - model: XLMRoberta
    }
    
    class "EntityExtractor" {
        + extract(text: String): List<Entity>
        - patterns: RegexPatterns
    }
}

package "Retrieval Services" {
    class "HybridRAGService" {
        + retrieve(query: String): List<Chunk>
        + generateResponse(context: String, query: String): String
        - bm25Client: ElasticsearchClient
        - vectorClient: PineconeClient
    }
    
    class "BM25Retriever" {
        + search(terms: List<String>): List<Result>
    }
    
    class "DenseRetriever" {
        + search(vector: Float[]): List<Result>
    }
    
    class "RankFusion" {
        + fuse(sparse: List, dense: List): List<Chunk>
        - k: Int = 60
    }
}

package "Confidence & Validation" {
    class "ConfidenceScorer" {
        + score(retrieval: Float, citation: Float): Float
        + shouldFallback(score: Float): Boolean
        - threshold: Float = 0.7
    }
    
    class "CitationValidator" {
        + validate(answer: String, sources: List<Chunk>): Float
    }
}

package "Auth Services" {
    class "AuthService" {
        + validateToken(token: String): UserProfile
        + checkGuestLimit(ip: String): Boolean
    }
    
    class "AdminService" {
        + uploadDocument(file: PDF): Boolean
    }
}

' Relationships
ChatController --> AuthService : validates access
ChatController --> LanguageDetector : detect language
LanguageDetector --> IntentClassifier : process
IntentClassifier --> EntityExtractor : extract
EntityExtractor --> HybridRAGService : query

HybridRAGService --> BM25Retriever : sparse search
HybridRAGService --> DenseRetriever : dense search
BM25Retriever --> RankFusion : results
DenseRetriever --> RankFusion : results
RankFusion --> ConfidenceScorer : check

HybridRAGService --> CitationValidator : validate

note right of IntentClassifier
  Pre-trained XLM-RoBERTa
  Zero-shot classification
end note

note bottom of RankFusion
  Reciprocal Rank Fusion
  Combines BM25 + Dense
end note
@enduml



part3 

@startuml
skinparam style strictuml
skinparam classAttributeIconSize 0
hide empty members
title Class Diagram Part 3: Infrastructure Layer (External Interfaces)

package "Interfaces (Ports)" {
    interface "IDataRepository" {
        + saveUser(user)
        + saveChat(session)
        + logEvaluation(metrics)
    }
    
    interface "ICacheManager" {
        + incrementKey(key, ttl)
        + getValue(key)
    }
    
    interface "IVectorStore" {
        + similaritySearch(vector): List<Result>
        + upsert(chunks: List<Chunk>)
    }
    
    interface "ISparseSearch" {
        + bm25Search(terms: List<String>): List<Result>
        + indexDocument(doc: Document)
    }
    
    interface "ILLMProvider" {
        + generate(prompt: String): LLMResponse
        + getTokenProbabilities(): Float[]
    }
    
    interface "IEmbedder" {
        + embed(text: String): Float[]
        + embedBatch(texts: List<String>): List<Float[]>
    }
}

package "Implementations (Adapters)" {
    class "PostgresAdapter" implements IDataRepository {
        - connectionString: String
    }
    
    class "RedisAdapter" implements ICacheManager {
        - redisHost: String
    }
    
    class "PgVectorAdapter" implements IVectorStore {
        - connectionString: String
        - tableName: String = "document_embeddings"
    }
    
    class "PostgreSQLFullTextAdapter" implements ISparseSearch {
        - connectionString: String
        - searchConfig: String = "english, simple"
    }
    
    class "GeminiClient" implements ILLMProvider {
        - apiKey: String
        - model: String = "gemini-2.5-flash"
    }
    
    class "E5Embedder" implements IEmbedder {
        - modelName: String = "multilingual-e5-large"
    }
    
    class "TelegramBotAdapter" {
        - botToken: String
        + sendMessage(chatId, text)
        + receiveUpdate(): Update
    }
}

package "Evaluation Infrastructure" {
    class "MetricsCollector" {
        + logQuery(query, response, latency)
        + computeEMScore(answer, groundTruth): Float
        + computeROUGE(answer, reference): Float
    }
    
    class "HallucinationDetector" {
        + sample(responses: List, n: Int): List
        + flagForReview(response): void
    }
}

@enduml


## 3.2 Sequence Diagram

@startuml
skinparam style strictuml
skinparam sequenceMessageAlign center
autoactivate on
title Figure 1: Hybrid RAG Conversation Flow (Success Scenario)

actor "User" as U
participant "ChatController" as API
participant "NLU Pipeline" as NLU
participant "BM25 Search" as BM25
participant "Vector DB" as VDB
participant "Fusion Engine" as Fusion
participant "LLM Service" as LLM
participant "Confidence Scorer" as Conf

U -> API: Send Question ("How to register for VAT?")

API -> NLU: Process(query)
    NLU -> NLU: Detect Language (Amharic/English)
    NLU -> NLU: Classify Intent (Procedural)
    NLU -> NLU: Extract Entities (VAT, Registration)
return NLU Results

API -> BM25: Keyword Search(query terms)
return Sparse Results (Top 10)

API -> VDB: Semantic Search(query vector)
return Dense Results (Top 10)

API -> Fusion: Reciprocal Rank Fusion
    Fusion -> Fusion: Merge & Rerank
return Top 5 Chunks

API -> Conf: Check Retrieval Confidence
    Conf -> Conf: Max Score >= 0.6?
return Confidence OK

API -> LLM: Generate(context + query)
    LLM -> LLM: Construct Prompt\n(System + Context + Citations Required)
return Answer with Citations

API -> Conf: Validate Citations
    Conf -> Conf: Match claims to sources
return Citation Accuracy OK

API --> U: Display Answer + Source References

@enduml



@startuml
skinparam style strictuml
skinparam sequenceMessageAlign center
autoactivate on
title Figure 3: Error Handling & Fallback Strategy

actor "User" as U
participant "API Gateway" as API
participant "Redis" as Cache
participant "Hybrid RAG" as RAG
participant "Confidence Scorer" as Conf

U -> API: Send Request

alt #Pink Case 1: Rate Limit Exceeded (Guest)
    API -> Cache: Check IP Limit
    Cache --> API: Limit > 15
    API --> U: **Error 429:** "Too Many Requests.\nPlease wait 10 mins."

else #LightYellow Case 2: Retrieval Service Timeout
    API -> RAG: Retrieve Context
    RAG -> RAG: BM25 + Vector Search
    note right: Connection Timeout (5s)
    RAG --> API: Error (Service Unavailable)
    API --> U: **Fallback:** "I am unable to search the tax laws right now.\nPlease try again later."

else #LightBlue Case 3: Low Retrieval Confidence
    API -> RAG: Retrieve Context
    RAG -> Conf: Check Scores
    Conf --> RAG: Max Score < 0.6
    RAG --> API: Low Confidence Flag
    API --> U: **Fallback:** "I couldn't find relevant information for this query.\nPlease consult an ERA officer directly."

else #LightGreen Case 4: Low Generation Confidence
    API -> RAG: Generate Answer
    RAG -> Conf: Validate Citations
    Conf --> RAG: Citation Overlap < 0.5
    RAG --> API: Confidence Score < 0.7
    API --> U: **Disclaimer Reply:** "[Answer]\n\n⚠️ Note: This information may be incomplete.\nPlease verify with official ERA sources."

else #Orange Case 5: Intent Classification Unclear
    API -> RAG: Process Query
    RAG --> API: Intent Confidence < 0.5
    API --> U: **Clarification:** "I'm not sure what you're asking.\nAre you asking about:\n1. VAT Registration\n2. TIN Application\n3. Tax Filing Deadlines?"
end
@enduml

## 3.3 State chartDiagram
@startuml
skinparam style strictuml
skinparam linetype ortho
skinparam state {
  BackgroundColor White
  BorderColor Black
  ArrowColor Black
}
hide empty description

title State Chart Diagram: Hybrid RAG System Logic Tree

[*] --> UserInput : User sends question

state "1. NLU Processing" as NLULayer {
    state "Initialize Context (RAM)" as RAMInit
    UserInput --> RAMInit
    note right: No Login Required
    
    state "Language Detection" as LangDet
    RAMInit --> LangDet
    
    state "Intent Classification" as IntentClass
    LangDet --> IntentClass
    
    state "Entity Extraction" as EntityExt
    IntentClass --> EntityExt
}

state "2. Hybrid Retrieval Layer" as RagLayer {
    EntityExt --> ParallelSearch
    
    state ParallelSearch <<fork>>
    
    state "BM25 Keyword Search" as BM25
    state "Dense Vector Search" as Dense
    
    ParallelSearch --> BM25
    ParallelSearch --> Dense
    
    state ParallelJoin <<join>>
    BM25 --> ParallelJoin
    Dense --> ParallelJoin
    
    state "Reciprocal Rank Fusion" as RRF
    ParallelJoin --> RRF
    
    state "Confidence Check" as ConfCheck <<choice>>
    RRF --> ConfCheck
    
    state "Proceed to Generation" as Proceed
    state "Return Fallback" as Fallback #LightYellow
    
    ConfCheck --> Proceed : Score >= 0.6
    ConfCheck --> Fallback : Score < 0.6
}

state "3. Generation Layer" as GenLayer {
    state "Construct Prompt" as Prompt
    Proceed --> Prompt
    
    state "LLM Inference" as LLMInfer
    Prompt --> LLMInfer
    
    state "Citation Validation" as CiteValid
    LLMInfer --> CiteValid
    
    state "Final Confidence" as FinalConf <<choice>>
    CiteValid --> FinalConf
    
    state "Return with Citations" as Success #LightGreen
    state "Return with Disclaimer" as Disclaimer #LightBlue
    
    FinalConf --> Success : Score >= 0.7
    FinalConf --> Disclaimer : Score < 0.7
}

state "4. Response Layer" as RespLayer {
    state "Render Markdown" as Render
    Success --> Render
    Disclaimer --> Render
    Fallback --> Render
    
    note bottom of Render
        Guest: Data wiped on close
        Registered: Saved to DB
    end note
}

Render --> [*]
@enduml

# 4\. Detailed Design

This section provides the detailed design for the classes identified in the Class Diagram (Section 3.1). It defines the specific attributes, types, visibility, and contractual obligations (pre/post-conditions) for the core system components.

Table 4.1: Attributes description for Document class

| Attribute | Type | Visibility | Invariant |
| --- | --- | --- | --- |
| docID | String (UUID) | Private | docID can not be NULL and must be unique across the database. |
| --- | --- | --- | --- |
| title | String | Public | title NULL and length > 5 chars. Must match the official legal title. |
| --- | --- | --- | --- |
| rawContent | Blob | Private | rawContent NULL. File size must be < 25MB. |
| --- | --- | --- | --- |
| fileType | Enum | Public | Must be one of {PDF, DOCX, TXT}. |
| --- | --- | --- | --- |
| uploadDate | DateTime | Protected | Defaults to current server timestamp. |
| --- | --- | --- | --- |
| processStatus | Enum | Public | Must be {PENDING, PROCESSING, INDEXED, FAILED}. |
| --- | --- | --- | --- |

Table 4.2: Operation description for Document class

| Operation | Visibility | Return Type | Argument | Pre-Condition | Post-Condition |
| --- | --- | --- | --- | --- | --- |
| extractText | Private | String | fileBlob | File must be a valid PDF/DOCX format; File size < 25MB. | Returns raw text string including Amharic Unicode characters. |
| --- | --- | --- | --- | --- | --- |
| cleanText | Private | String | rawText | rawText is not null. | Removes headers, footers, and page numbers. |
| --- | --- | --- | --- | --- | --- |
| chunkContent | Public | List&lt;String&gt; | cleanedText | cleanedText length > 100 chars. | Returns list of strings where each string length <= 1024 tokens. |
| --- | --- | --- | --- | --- | --- |
| updateStatus | Public | Void | newStatus | newStatus is a valid Enum value. | processStatus is updated to the new value. |
| --- | --- | --- | --- | --- | --- |

### 4.2 Class: Admin (Inherits from User)

Represents an authenticated system administrator with privileges to manage the knowledge base manually.

Table 4.3: Attributes description for Admin class

| Attribute | Type | Visibility | Invariant |
| --- | --- | --- | --- |
| adminID | String | Private | adminID <> NULL. |
| --- | --- | --- | --- |
| username | String | Public | username must be unique and alphanumeric. |
| --- | --- | --- | --- |
| passwordHash | String | Private | Must be SHA-256 encrypted string; never plain text. |
| --- | --- | --- | --- |
| role | Enum | Protected | Defaults to SUPER_ADMIN. |
| --- | --- | --- | --- |
| sessionToken | String | Private | Valid JWT token with 1-hour expiration. |
| --- | --- | --- | --- |

**Table 4.4 Operation description for Admin class**

| Operation | Visibility | Return Type | Argument | Pre-Condition | Post-Condition |
| --- | --- | --- | --- | --- | --- |
| login | Public | Bool | user, pass | The account must exist in PostgreSQL. | If valid, sessionToken is generated; else return False. |
| --- | --- | --- | --- | --- | --- |
| uploadDocument | Public | Void | fileObj | User must be logged in; File must be valid. | New Document object is created with status PENDING. |
| --- | --- | --- | --- | --- | --- |
| viewSystemLogs | Public | JSON | dateRange | User must have a SUPER_ADMIN role. | Returns error/access logs for the specified period. |
| --- | --- | --- | --- | --- | --- |
| forceScrape | Public | Void | \-  | Scraper service must be idle (not currently running). | Scraper job is triggered immediately. |
| --- | --- | --- | --- | --- | --- |

### 

### **4.3 Class ChatSession**

Represents a continuous conversation thread between a public user (Taxpayer) and the AI Bot.

**Table 4.5 Attributes description for ChatSession class**

| Attribute | Type | Visibility | Invariant |
| --- | --- | --- | --- |
| sessionID | String | Public | Unique UUID generated upon first page load. |
| --- | --- | --- | --- |
| messageHistory | List&lt;Message&gt; | Private | Ordered list by timestamp; Max size 20 messages (context window). |
| --- | --- | --- | --- |
| startTime | DateTime | Private | System time at session creation. |
| --- | --- | --- | --- |
| lastActivity | DateTime | Public | lastActivity <= CurrentTime. |
| --- | --- | --- | --- |
| clientIP | String | Private | Valid IP address format. |
| --- | --- | --- | --- |

**Table 4.6 Operation description for ChatSession class**

| Operation | Visibility | Return Type | Argument | Pre-Condition | Post-Condition |
| --- | --- | --- | --- | --- | --- |
| addMessage | Public | Void | msgContent, senderRole | msgContent is not empty; senderRole is {USER, AI}. | Message is appended to messageHistory; lastActivity updated. |
| --- | --- | --- | --- | --- | --- |
| getContext | Public | String | \-  | messageHistory is not empty. | Returns concatenated string of last 5 interactions for LLM context. |
| --- | --- | --- | --- | --- | --- |
| checkTimeout | Private | Boolean | \-  | \-  | Returns True if CurrentTime - lastActivity > 30 mins. |
| --- | --- | --- | --- | --- | --- |
| detectLanguage | Public | String | inputText | inputText is not null. | Returns 'am' (Amharic) or 'en' (English). |
| --- | --- | --- | --- | --- | --- |

### 

### **4.4 Class KnowledgeEngine (RAG Controller)**

This is the core logic class responsible for bridging the user query with the Vector Database and the LLM.

**Table 4.7 Attributes description for KnowledgeEngine class**

| Attribute | Type | Visibility | Invariant |
| --- | --- | --- | --- |
| embeddingModel | String | Private | Constant: "text-embedding-3-small" or similar. |
| --- | --- | --- | --- |
| vectorDBClient | Object | Private | Active connection object to Pinecone. |
| --- | --- | --- | --- |
| confidenceThreshold | Float | Public | Value must be between 0.0 and 1.0 (e.g., 0.75). |
| --- | --- | --- | --- |

**Table 4.8: Operation description for KnowledgeEngine class**

| Operation | Visibility | Return Type | Argument | Pre-Condition | Post-Condition |
| --- | --- | --- | --- | --- | --- |
| vectorizeQuery | Private | Vector\[\] | queryText | queryText is not empty. | Returns float array representation of text. |
| --- | --- | --- | --- | --- | --- |
| retrieveContext | Public | List&lt;String&gt; | queryVector | Vector DB is online. | Returns top 5 document chunks sorted by similarity score. |
| --- | --- | --- | --- | --- | --- |
| generateAnswer | Public | String | context, query | LLM API is reachable. | Returns natural language response citing sources. |
| --- | --- | --- | --- | --- | --- |
| validateConfidence | Private | Boolean | score | \-  | Returns True if score >= confidenceThreshold. |
| --- | --- | --- | --- | --- | --- |

### **4.5 Class WebScraper**

The automated agent responsible for keeping the knowledge base up to date.

**Table 4.9: Attributes description for WebScraper class**

| Attribute | Type | Visibility | Invariant |
| --- | --- | --- | --- |
| targetURL | String | Private | Constant: "https://mor.gov.et". |
| --- | --- | --- | --- |
| scheduleTime | Time | Private | Constant: 00:00 EAT. |
| --- | --- | --- | --- |
| downloadPath | String | Private | Path must be writeable by the system. |
| --- | --- | --- | --- |

**Table 4.10: Operation description for WebScraper class**

| Operation | Visibility | Return Type | Argument | Pre-Condition | Post-Condition |
| --- | --- | --- | --- | --- | --- |
| scanForUpdates | Public | List&lt;URL&gt; | \-  | Internet connection is active. | Returns list of PDF links not present in known_hashes DB. |
| --- | --- | --- | --- | --- | --- |
| downloadFile | Protected | File | url | URL is valid. | The file is saved to downloadPath. |
| --- | --- | --- | --- | --- | --- |
| logError | Private | Void | errorMsg | \-  | Error details written to system log. |
| --- | --- | --- | --- | --- | --- |

## 4.6 Algorithm Design

### **4.6.1 Hybrid Retrieval Augmented Generation (RAG) Flow**

The system uses an advanced hybrid RAG pattern that combines keyword matching with semantic search to answer questions based on facts rather than the AI's training memory. This addresses limitations of naive RAG implementations.

1.  **Input:** The system receives a query from the user (e.g., "What is the VAT rate?" / "የቫት ምጣኔ ስንት ነው?").
2.  **NLU Processing:** Language detection, intent classification (XLM-RoBERTa), and entity extraction (Proclamation numbers, TIN patterns, amounts).
3.  **Dual Retrieval Path:**
    - **BM25 Sparse Search:** Keyword matching for exact legal terms, Proclamation numbers (e.g., "285/2002")
    - **Dense Vector Search:** Semantic similarity using multilingual-e5-large embeddings
4.  **Fusion & Reranking:** Reciprocal Rank Fusion combines both result sets; Cross-Encoder reranks top candidates.
5.  **Confidence Check:** If max retrieval score < 0.6, return fallback message instead of proceeding.
6.  **Augmentation:** The system combines the user's question with top-5 retrieved chunks into a structured prompt with citation requirements.
7.  **Generation:** The LLM generates a response with mandatory source citations.
8.  **Post-Processing:** Citation validation ensures generated claims match source documents.

### **4.6.2 Vector Similarity Search (Cosine Similarity)**

To find the right documents, the system needs to measure how similar a user's question is to the stored documents.

1.  **The Concept:** The system converts both the User's Question and the Tax Documents into lists of numbers called "vectors" using multilingual-e5-large (1024 dimensions). These vectors represent the meaning of the text in a multi-dimensional space.
2.  **The Calculation:** The system calculates the angle between the Question Vector and the Document Vector.
    1.  If the angle is small (close to 0 degrees), the vectors point in the same direction, meaning the texts are very similar in meaning.
    2.  If the angle is wide (close to 90 degrees), the texts are unrelated.
3.  **Threshold:** The system only accepts documents where the similarity score is high (above 0.6 for retrieval, 0.7 for high-confidence answers).

### **4.6.3 BM25 Keyword Matching (Sparse Retrieval)**

Dense vector search alone may miss exact legal terminology. BM25 provides complementary keyword-based retrieval.

1.  **Term Frequency (TF):** Measures how often query terms appear in a document.
2.  **Inverse Document Frequency (IDF):** Weighs rare terms higher than common terms.
3.  **Length Normalization:** Adjusts for document length to avoid bias toward longer documents.
4.  **Use Case:** Critical for exact matches like "Proclamation 285/2002" or "ደንብ ቁጥር 410/2017".

### **4.6.4 Reciprocal Rank Fusion (RRF)**

Combines BM25 and dense retrieval results into a unified ranking.

**Formula:** `RRF_score(d) = Σ 1 / (k + rank_i(d))`

Where `k=60` (constant), and `rank_i(d)` is the rank of document `d` in retrieval system `i`.

**Benefit:** Documents appearing in top ranks of both systems receive highest combined scores, leveraging strengths of both approaches.

### **4.6.5 Text Chunking Algorithm (Sliding Window)**

Tax documents are often very long, but the AI can only read a certain amount of text at once. To solve this, the system breaks documents into smaller pieces.

1.  **Chunking:** The document is split into blocks of approximately 750 words (1024 tokens).
2.  **Overlap:** To prevent cutting a sentence in half at the end of a block, the system creates an "overlap." The last 100 words of Block A are repeated as the first 100 words of Block B. This ensures the context flows smoothly from one chunk to the next.
3.  **Metadata Preservation:** Each chunk retains source document ID, page number, and section header for citation purposes.

### **4.6.6 Confidence Estimation Algorithm**

The system implements multi-signal confidence scoring to prevent hallucinations.

| Signal | Weight | Measurement |
| --- | --- | --- |
| Retrieval Score | 0.4 | Max cosine similarity from dense search |
| BM25 Score | 0.2 | Normalized BM25 score |
| Citation Overlap | 0.3 | Ratio of generated claims with source support |
| LLM Uncertainty | 0.1 | Token probability variance (if available) |

**Decision Logic:**
- Combined Score ≥ 0.7 → Return answer with citations
- Combined Score 0.5-0.7 → Return answer with disclaimer
- Combined Score < 0.5 → Return fallback: "Please consult an ERA officer"

### **4.6.7 Guest Rate Limiting Algorithm (Token Bucket)**

To secure the free tier, the system implements a volatile rate limiter using Redis:

- **Identifier:** Client_IP_Address
- **Storage:** Redis Cache (In-Memory)
- **Logic:**
  - Check: `GET rate_limit:{IP}`
  - If Null: `SET rate_limit:{IP} = 1, EXPIRE 600` (10 minutes)
  - If < 15: `INCR rate_limit:{IP}`. Allow request.
  - If >= 15: Return HTTP 429 (Too Many Requests)
- **Privacy:** The Redis key automatically expires after 10 minutes, ensuring no permanent log of the IP address is retained.

### **4.6.8 Intent Classification Algorithm**

Using XLM-RoBERTa in zero-shot classification mode:

**Intent Categories:**
1. **Informational** - "What is VAT?" → Retrieve definition documents
2. **Procedural** - "How do I register for TIN?" → Retrieve step-by-step guides
3. **Definitional** - "Define withholding tax" → Retrieve glossary entries
4. **Clarification** - "Can you explain step 3?" → Use session context

**Prompt Template for Zero-Shot:**
```
Classify the following query into one of: Informational, Procedural, Definitional, Clarification
Query: {user_query}
Classification:
```

## 4.7 Evaluation Framework Design

### **4.7.1 Automated Metrics Pipeline**

@startuml
skinparam style strictuml
title Figure: Evaluation Metrics Pipeline

start
:Collect Query-Response Pairs (Anonymized);

partition "Retrieval Evaluation" {
    :Compute Top-K Accuracy;
    :Measure Mean Reciprocal Rank (MRR);
    :Calculate Recall@5;
}

partition "Generation Evaluation" {
    :Compute Exact Match (EM) for FAQs;
    :Calculate F1 Score;
    :Measure ROUGE-L;
    :Compute BERTScore;
}

partition "Citation Verification" {
    :Extract Generated Claims;
    :Match Against Source Chunks;
    :Calculate Citation Accuracy;
}

partition "Hallucination Detection" {
    :Sample 50-100 Responses;
    :Manual Expert Review;
    :Compute Hallucination Rate;
}

:Aggregate Metrics Dashboard;
:Alert if Below Thresholds;
stop

@enduml

### **4.7.2 Evaluation Metrics Definitions**

| Metric | Formula/Description | Target |
| --- | --- | --- |
| **Top-K Retrieval Accuracy** | % of queries where correct doc is in top-K | ≥ 85% (K=5) |
| **Exact Match (EM)** | % of answers exactly matching ground truth | ≥ 70% (FAQs) |
| **F1 Score** | Harmonic mean of precision and recall | ≥ 0.8 |
| **ROUGE-L** | Longest common subsequence overlap | ≥ 0.5 |
| **BERTScore** | Semantic similarity of generated vs reference | ≥ 0.85 |
| **Citation Accuracy** | % of citations correctly pointing to source | ≥ 95% |
| **Hallucination Rate** | % of responses with unsupported claims | < 5% |
| **Multilingual Parity** | Accuracy difference (Amharic vs English) | ≤ 5% |

## 4.8 Key Algorithms & AI/ML Architecture

This section defines the core algorithmic components that power the system's intelligence.

### 4.8.1 Natural Language Understanding (NLU) Pipeline

**Purpose:** Understand user queries in Amharic, English, or mixed code-switched input.

| Component | Algorithm/Model | Justification |
| --- | --- | --- |
| Language Detection | fastText langdetect | Lightweight, supports Amharic, no training required |
| Tokenization | SentencePiece (Amharic), SpaCy (English) | Handles Ethiopic script morphology |
| Intent Classification | XLM-RoBERTa (zero-shot) | Pre-trained multilingual model with Amharic support |
| Entity Extraction | Gemini 2.5 Flash (structured prompts) | More robust than RegEx for tax-specific entities |

### 4.8.2 Information Retrieval (Hybrid RAG)

**Purpose:** Retrieve relevant ERA documents to ground responses and prevent hallucinations.

| Component | Algorithm | Description |
| --- | --- | --- |
| Sparse Retrieval | PostgreSQL Full-text Search | Keyword matching for exact legal terms, Proclamation numbers |
| Dense Retrieval | Cosine Similarity on Embeddings | Semantic search using multilingual-e5-large embeddings |
| Fusion | Reciprocal Rank Fusion (RRF) | Combines sparse and dense retrieval scores |
| Reranking | Cross-Encoder (ms-marco-MiniLM) | Final relevance scoring of top candidates |

### 4.8.3 LLM Response Generation

**Purpose:** Generate accurate, readable, and properly cited answers.

The system uses **Gemini 2.5 Flash** as the primary language model for generating responses. All responses must include proper source citations with specific Proclamation numbers and article references to ensure legal accuracy and traceability.

### 4.8.4 Confidence Estimation & Fallback

**Purpose:** Determine response reliability and trigger human escalation when needed.

The system uses retrieval confidence scoring based on the maximum cosine similarity score from the document search. When the retrieval confidence falls below 0.6, the system will inform the user that it cannot find sufficient information and offer the option to contact a human ERA officer for assistance.

### 4.8.5 Dialogue Management

**Purpose:** Maintain conversation flow and multi-turn context.

- **Context Window:** Last 5 exchanges (user + assistant) maintained in session
- **Slot Filling:** Track taxpayer category, query topic, and pending clarifications
- **Handoff Management:** When conversation is escalated to human agents, provide a summarization of the chat history and tracked user slots

### 4.8.6 Algorithm Flow Diagram

@startuml
skinparam style strictuml
skinparam activityBackgroundColor White
skinparam activityBorderColor Black

title Figure: End-to-End Algorithm Pipeline

start
:User Query (Amharic/English/Mixed);

partition "1. NLU Pipeline" {
    :Language Detection (fastText);
    :Tokenization (SentencePiece/SpaCy);
    :Intent Classification (XLM-RoBERTa);
    :Entity Extraction (Gemini 2.5 Flash);
}

partition "2. Hybrid Retrieval (RAG)" {
    fork
        :PostgreSQL Full-text Search;
    fork again
        :Dense Vector Search (pgvector);
    end fork
    :Reciprocal Rank Fusion;
    :Cross-Encoder Reranking;
    :Top-5 Document Chunks;
}

partition "3. Confidence Check" {
    if (Retrieval Score >= 0.6?) then (yes)
        :Proceed to Generation;
    else (no)
        :Offer Human Agent Option;
        stop
    endif
}

partition "4. LLM Generation" {
    :Construct Prompt (Context + Query + Citations Required);
    :Gemini 2.5 Flash Inference;
    :Parse Response + Extract Citations;
}

partition "5. Post-Processing" {
    :Validate Citations Against Sources;
    :Log Query-Response Pair (Anonymized);
    :Update Session Context;
}

:Display Response to User;
stop

@enduml

## 4.9 Model Selection Rationale

### **4.9.1 LLM Selection**

**Decision: Gemini 2.5 Flash**

| Criterion | Gemini 2.5 Flash | Justification |
| --- | --- | --- |
| Amharic Support | Excellent | Strong multilingual capabilities |
| Cost | Moderate | Cost-effective for production scale |
| Latency | ~1-2s | Fast inference suitable for real-time chat |
| API Reliability | High | Google Cloud infrastructure |
| **Recommendation** | **Primary Choice** | Best balance of performance, cost, and reliability |

### **4.9.2 Database Stack Selection**

**Decision: PostgreSQL + pgvector**

| Component | Technology | Justification |
| --- | --- | --- |
| Vector Storage | pgvector extension | Native PostgreSQL integration, no separate vector DB needed |
| Full-text Search | Elasticsearch | simpler stack |
| Relational Data | PostgreSQL | Unified database for all data types |
| **Advantage** | **Simplified Stack** | Single database technology reduces complexity and maintenance |

### **4.9.3 Fine-Tuning vs Prompt Engineering**

**Decision: Prompt Engineering + RAG (No Fine-Tuning)**

| Factor | Fine-Tuning | Prompt Engineering | Our Choice |
| --- | --- | --- | --- |
| Amharic Data Availability | Insufficient | Not required | Prompt Engineering |
| Update Frequency | Requires retraining | Update prompts only | Prompt Engineering |
| Computational Cost | High | Low | Prompt Engineering |
| Iteration Speed | Slow | Fast | Prompt Engineering |
| Factual Grounding | Model memory | RAG retrieval | RAG |

## 5\. References

1.  **IEEE Standards**
    - _IEEE Std 1016-2009_: IEEE Recommended Practice for Software Design Descriptions.

2.  **Academic & Conceptual Foundations**
    - Lewis, P., et al. (2020). _Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks_. arXiv preprint arXiv:2005.11401. (Foundational paper for the RAG architecture used in Section 4.6.1).
    - Robertson, S., & Zaragoza, H. (2009). _The Probabilistic Relevance Framework: BM25 and Beyond_. Foundations and Trends in Information Retrieval.
    - Conneau, A., et al. (2020). _Unsupervised Cross-lingual Representation Learning at Scale (XLM-RoBERTa)_. arXiv:1911.02116.

3.  **Technical Documentation (Backend & Infrastructure)**
    - FastAPI: _FastAPI Web Framework Documentation_. Retrieved from https://fastapi.tiangolo.com/
    - Docker: _Docker Engine User Guide & Container Best Practices_. Retrieved from https://docs.docker.com/
    - PostgreSQL: _pgvector Extension Documentation_. Retrieved from https://github.com/pgvector/pgvector
    - LangChain: _Building RAG Pipelines with LLMs_. Retrieved from https://python.langchain.com/
    - PostgreSQL: _Full-Text Search Documentation_. Retrieved from https://www.postgresql.org/docs/current/textsearch.html

4.  **Technical Documentation (Frontend)**
    - Next.js: _Next.js Documentation_. Retrieved from https://nextjs.org/docs
    - React: _React.js Documentation_. Retrieved from https://react.dev/
    - TypeScript: _TypeScript Language Specification_. Retrieved from https://www.typescriptlang.org/docs/

5.  **AI/ML Resources**
    - Google AI: _Gemini API Documentation_. Retrieved from https://ai.google.dev/gemini-api
    - Hugging Face: _XLM-RoBERTa Model Card_. Retrieved from https://huggingface.co/xlm-roberta-base
    - _multilingual-e5-large Model Card_. Retrieved from https://huggingface.co/intfloat/multilingual-e5-large
    - Telegram: _Bot API Documentation_. Retrieved from https://core.telegram.org/bots/api