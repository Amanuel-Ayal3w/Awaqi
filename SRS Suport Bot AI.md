**College of Technology and Built Environment**

**School of Information Technology and Engineering**

**Department of IT/SE Eng.**

**LLM-Based Support Bot for Ethiopian Revenue Authority to enhance information desk service for tax payers and business** **owners**

**Software Requirements Specification**

**Team Members**

1\. Abdurahman Mohammed …ATE/8901/13

2\. Amanuel Ayalew…………….ATE/3871/13

3\. Basliel selamu .....................ATE/6761/13

4\. Bethel Wondowssen............ATE/8712/13

5\. Diborah Dereje.....................ATE/1712/13

**Advisor: Mr Daniel Date Dec 22 , 2025**

**Revision History**

| **Date** | **Description** | **Author** | **Comments** |
| --- | --- | --- | --- |
| 25/12/2026 | First draft | &lt;Your Name&gt; |     |
| --- | --- | --- | --- |
|     |     |     |     |
| --- | --- | --- | --- |
|     |     |     |     |
| --- | --- | --- | --- |
|     |     |     |     |
| --- | --- | --- | --- |

# Document Approval

The following Software Requirements Specification has been accepted and approved by the following:

| **Signature** | **Printed Name** | **Title** | **Date** |
| --- | --- | --- | --- |
|     | Mr Daniel Abebe | Advisor |     |
| --- | --- | --- | --- |
|     |     |     |     |
| --- | --- | --- | --- |
|     |     |     |     |
| --- | --- | --- | --- |

**Table of Contents**

[**Document Approval 2**](#_heading=h.e1jrkgvym6jj)

[List of Tables 4](#_heading=h.uw58a1hbr4ut)

[**Table 3.1: Use Case 1 - Taxpayer Enquires about VAT Registration 4**](#_heading=)

[**Table 3.2: Use Case 2 - Automated Knowledge Base Update 4**](#_heading=)

[**Table 3.3: Use Case 3 - Admin Upload Document 4**](#_heading=h.83ekkr6i0hbm)

[List of figures 5](#_heading=h.2qj00obdfp57)

[**Figure 1: High-Level System Architecture Diagram (Section 2.1) 5**](#_heading=h.j2xdmisf2300)

[**Definitions, Acronyms, and Abbreviations 6**](#_heading=h.2kri0c58yxq8)

[**DECLARATION 9**](#_heading=h.ichmdqwswihd)

[**1\. Introduction 1**](#_heading=h.pkp4r3pno41t)

[1.1 Purpose 1](#_heading=h.tgiv493kugaw)

[1.2 Scope 1](#_heading=h.dlz0i79dvg8q)

[1.3 Overview 2](#_heading=h.ryh03cusib38)

[1.4 Project Objectives 2](#_heading=h.taxck9u05vju)

[**2\. General Description 2**](#_heading=h.40r11v14rq1c)

[2.1 Literature Review 3](#_heading=h.qxu0k7qqkfb0)

[2.2 Product Perspective 3](#_heading=h.jvn41y3r3yni)

[2.3 Product Functions 4](#_heading=h.n4bm5cqlgh27)

[2.4 User Characteristics 4](#_heading=h.yt2eh5lu5jff)

[2.5 General Constraints 4](#_heading=h.w7svn2rdd08a)

[**3\. Specific Requirements 5**](#_heading=h.oc9afp29zs4e)

[3.1 External Interface Requirements 6](#_heading=h.l4owybmikq3g)

[3.2 Functional Requirements 13](#_heading=h.liixw9xov8lt)

[3.3 Use Cases 14](#_heading=h.9agn23u5wa8o)

[3.3.1 Use Case 1: Taxpayer Enquires about Tax Regulations 15](#_heading=h.u7u9asii991)

[3.3.2 Use Case 2: Automated Knowledge Base Update 19](#_heading=h.md7u7q6ckjh7)

[3.3.3 Use Case #3: Admin Upload Document (Manual Override) 22](#_heading=h.zd1i2nao92f4)

[3.4 Non-Functional Requirements 25](#_heading=h.pmznqsz6a9vy)

[3.5 Inverse Requirements 26](#_heading=h.dnv18vlh51cv)

[3.6 Design Constraints 26](#_heading=h.9id9nawg6y7b)

[3.7 Logical Database Requirements 26](#_heading=h.1nfn7526mruc)

[3.8 Other Requirements 26](#_heading=h.7wd0jlqhfylg)

[4\. Change Management Process 27](#_heading=h.5lrvuu8s6lj1)

[4.1 Change Request Lifecycle 27](#_heading=h.iu1z6lpyw3f6)

[4.2 Roles and Responsibilities 28](#_heading=h.hjdas3kwq4y0)

[4.3 Documentation of Changes 28](#_heading=h.9v4ww1c1yx9o)

[**5\. References 29**](#_heading=h.2nkn6p2g4t7s)

[6\. Appendices 30](#_heading=h.7tvgrgr3kih6)

# List of Tables Table 3.1: Use Case 1 - Taxpayer Enquires about VAT RegistrationTable 3.2: Use Case 2 - Automated Knowledge Base UpdateTable 3.3: Use Case 3 - Admin Upload DocumentList of figures Figure 1: High-Level System Architecture Diagram (Section 2.1)

# Definitions, Acronyms, and Abbreviations

| **Term / Acronym** | **Definition** |
| --- | --- |
| **API** | **Application Programming Interface.** A set of protocols and tools that allows different software applications to communicate with each other. |
| --- | --- |
| **Chunking** | The process of breaking down large text documents into smaller, semantically meaningful segments (e.g., 512 tokens) to be processed by the embedding model. |
| --- | --- |
| **Confidence Score** | A numerical value (usually between 0 and 1) indicating the probability that the AI-generated response is accurate based on the retrieved context. |
| --- | --- |
| **Cron Job** | A time-based job scheduler in Unix-like computer operating systems, used here to schedule the daily web scraper. |
| --- | --- |
| **Embedding** | A numerical representation (vector) of text where words with similar meanings have similar mathematical representations. |
| --- | --- |
| **Hallucination** | A phenomenon where a Large Language Model generates plausible-sounding but incorrect or nonsensical information not grounded in the provided source text. |
| --- | --- |
| **LLM** | **Large Language Model.** A type of artificial intelligence algorithm (e.g., GPT-4, Llama 3) that uses deep learning techniques and massively large data sets to understand, summarize, generate, and predict new content. |
| --- | --- |
| **MoR** | **Ministry of Revenue.** The Ethiopian government agency responsible for collecting taxes and customs duties. |
| --- | --- |
| **NLP** | **Natural Language Processing.** A branch of AI that gives computers the ability to understand text and spoken words in much the same way human beings can. |
| --- | --- |
| **OCR** | **Optical Character Recognition.** The electronic conversion of images of typed, handwritten, or printed text into machine-encoded text. |
| --- | --- |
| **PII** | **Personally Identifiable Information.** Information that can be used on its own or with other information to identify, contact, or locate a single person (e.g., TIN, Name, Phone Number). |
| --- | --- |
| **RAG** | **Retrieval-Augmented Generation.** A technique that optimizes the output of an LLM so it references an authoritative knowledge base (in this case, tax laws) outside its training data before generating a response. |
| --- | --- |
| **Scraper** | An automated software tool designed to extract data from websites. |
| --- | --- |
| **SIGTAS** | **Standard Integrated Government Tax Administration System.** The current internal legacy system used by the MoR for tax processing. |
| --- | --- |
| **SRS** | **Software Requirements Specification.** A document that describes what the software will do and how it will be expected to perform. |
| --- | --- |
| **TIN** | **Taxpayer Identification Number.** A unique registration number used by the tax authority to identify tax payers. |
| --- | --- |
| **UI/UX** | **User Interface / User Experience.** The visual elements a user interacts with and the overall experience of that interaction. |
| --- | --- |
| **VAT** | **Value Added Tax.** A consumption tax placed on a product whenever value is added at each stage of the supply chain. |
| --- | --- |
| **Vector Database** | A specialized database (e.g., Pinecone, Weaviate) optimized for storing and querying high-dimensional vector embeddings for fast similarity search. |
| --- | --- |

# DECLARATION

We declare that this written submission represents our ideas in our own words and where others’ ideas or words have been included. We have adequately cited and referenced the original sources. We also declare that we have adhered to all principles of academic honesty and integrity and have not misrepresented or fabricated or falsified any idea/data/fact/source in our submission. We understand that any violation of the above will be cause for disciplinary action by the Institute and can also evoke penal action from the sources which have thus not been properly cited or from whom proper permission has not been taken when needed.

**Group NO Team** **Date:**  Group 13

# 1\. Introduction

The introduction to the Software Requirement Specification (SRS) document should provide an overview of the complete SRS document. While writing this document please remember that this document should contain all of the information needed by a software engineer to adequately design and implement the software product described by the requirements listed in this document. (Note: the following subsection annotations are largely taken from the IEEE Guide to SRS).

## 1.1 Purpose

The purpose of this Software Requirements Specification (SRS) is to define the functional and non-functional requirements for the "LLM-Based Support Bot for the Ethiopian Revenue Authority." This document is intended for the software engineering team (developers, testers, and architects) to guide the design, implementation, and verification of the system. It also serves as a validation document for the stakeholders to ensure the proposed solution meets the identified business needs.

## 1.2 Problem Statement

The Ministry of Revenue (MoR) of Ethiopia serves over **4.5 million registered taxpayers**, with thousands of new registrations monthly. Each taxpayer faces unique circumstances requiring accurate, timely guidance on complex tax regulations. The Ethiopian tax code—like tax systems worldwide—is inherently complex and constantly evolving through new proclamations, directives, and amendments. This complexity leads to errors not only among first-time filers but also among veteran business owners.

**The Cost of Misinformation:** Incorrect tax information does not merely result in minor inconveniences. Taxpayers face:
- Substantial financial penalties (ranging from 10% to 100% of tax due)
- Prolonged compliance processes requiring multiple office visits
- Business operation disruptions due to frozen accounts or legal proceedings

**Current Information Channels and Their Limitations:**

1. **Physical Information Desk Officers:**
   - **Time & Cost Intensive:** Taxpayers must travel to MoR branch offices, often waiting hours in queues.
   - **Overwhelmed Staff:** With limited officers handling high volumes, responses are restricted to generic, basic information rather than personalized guidance.
   - **Information Gathering Bottleneck:** Studies indicate that over 50% of taxpayer time at revenue offices is spent merely gathering preliminary information before actual service delivery.
   - **Trial-and-Error Compliance:** Many taxpayers report needing 3-5 visits to correctly complete procedures like VAT registration or TIN correction.

2. **E-Services Portal (eservices.gov.et):**
   - **Outdated Content:** The platform is not actively maintained, containing regulations that may be superseded.
   - **Limited Scope:** Provides only basic, static information without context-aware or personalized responses.
   - **Trust Deficit:** Users are uncertain whether displayed information reflects current law, reducing adoption.

**Our Solution:**

This project delivers an **AI-Powered Information Desk Agent**—not merely another generic chatbot, but a localized, Ethiopia-specific solution that provides:
- **Accurate** answers grounded in official MoR proclamations and directives
- **Up-to-date** information through automated daily knowledge base synchronization
- **Personalized** responses tailored to the taxpayer's category (Individual, SME, Large Enterprise)
- **Instant** 24/7 availability eliminating queues and office-hour constraints
- **Context-aware** analysis capable of reviewing user-uploaded documents to provide specific guidance

**What Makes This System Different:**
Unlike generic RAG implementations, this system is built with a **customer-first, local-problem focus**. It employs Amharic-optimized language processing, Ethiopia-specific tax terminology mapping, and deterministic evaluation metrics to ensure measurable accuracy and explainability—addressing the critical trust gap in AI-generated legal guidance.

## 1.3 Scope

**Product Description:** The software is an intelligent, AI-powered chatbot system utilizing an advanced Retrieval Augmented Generation (RAG) architecture enhanced with hybrid search (BM25 + semantic retrieval). It is designed to transform tax information accessibility for Ethiopian taxpayers and business owners through localized, Amharic-first language support.

**Application Goals and Benefits:**

**Instant Access:** Reduce information retrieval time from days/weeks to seconds.

**Accessibility:** Provide 24/7 responses in Amharic and English via a web interface and Telegram bot.

**Accuracy:** Deliver regulation-grounded answers with mandatory source citations by querying a constantly updated knowledge base derived from the Ministry of Revenue (MoR) website.

**Cost Efficiency:** Reduce the burden on physical information desks and call centers by automating 70%+ of routine inquiries.

**The system will:**

1.  Automate the ingestion of tax regulations from mor.gov.et.
2.  Process natural language queries in Amharic and English.
3.  Provide citations for all answers generated.

**The system will not:**

1.  Perform direct tax filing or process payments.
2.  Store personal identifiable information (PII) of taxpayers.
3.  Provide binding legal advice beyond citing existing regulations.

## 1.3 Overview

The remainder of this document describes the system in detail. Section 2 provides a high-level overview of the product context and user demographics. Section 3 details the specific functional and interface requirements. Section 4 outlines the change management process.

## 1.4 Project Objectives

The goal of this project is to bridge the gap between complex tax legislation and taxpayer understanding through AI. The specific objectives include:

1.  **Localized Legal Accuracy:** Implement a Retrieval-Augmented Generation (RAG) architecture to ensure responses are grounded in official Ethiopian tax proclamations (e.g., VAT, Income Tax), providing sub-second responses with specific clause citations.
2.  **Linguistic Inclusivity:** Provide a robust multilingual interface in **Amharic and English**, specifically optimized to handle the morphological complexities of the Ethiopic script in legal contexts.
3.  **Operational Efficiency:** Reduce the burden on the Ethiopian Revenue Authority (MoR) physical information desks by automating answers to high-volume, routine tax queries.
4.  **Information Recency:** Establish an autonomous data pipeline that monitors and scrapes **mor.gov.et** for new directives, ensuring the bot’s knowledge base reflects the most current laws.

# 2\. General Description

This section of the SRS should describe the general factors that affect 'the product and its requirements. It should be made clear that this section does not state specific requirements; it only makes those requirements easier to understand.

## 2.1 Literature Review

The development of the LLM-based Support Bot is grounded in the evolving landscape of digital governance and AI research within Ethiopia and the wider African continent.

#### 2.1.1 Ethiopian Digital Tax & Legal Platforms

1.  **Ministry of Revenue (MoR) Portal:** The official repository for Ethiopian tax law (**mor.gov.et**). Literature identifies a "usability gap" where taxpayers struggle to find specific information within large, static PDF files. This project builds upon this infrastructure by making these documents semantically searchable.
2.  **Ethiopian Tax Law Assistant (2025):** A benchmark RAG-based project that demonstrated the feasibility of using **LangChain** and **ChromaDB** for local tax queries. Research on this assistant proved that providing clause-level citations significantly increases user trust in AI-generated legal advice.
3.  **Biritu Finance Bot:** A local platform serving as a case study for financial AI in Ethiopia. It demonstrated that Ethiopian users respond positively to conversational agents that simplify complex financial regulations into accessible Amharic and English dialogue.

#### 2.1.2 Amharic Natural Language Processing (NLP) Research

1.  **Linguistic Challenges:** Research from **Addis Ababa University** (e.g., _Machine Learning Models for Amharic_) underscores the difficulty of processing the Ethiopic script due to its rich morphology. This SRS adopts Unicode-aware tokenization as recommended by local NLP literature to ensure technical tax terms like "ተጨማሪ እሴት ታክስ" are correctly identified.
2.  **RAG vs. Fine-Tuning:** Current literature on "Low-Resource Language Processing" suggests that RAG is superior to fine-tuning for legal applications in Ethiopia, as it allows the model to access fresh data without the high cost of re-training for every new proclamation.

## 2.2 Product Perspective

This product is a new, standalone system designed to augment the existing service delivery channels of the Ethiopian Revenue Authority (In-person desks and Call centers).

1.  **System Interfaces:** The system interacts with the existing Ministry of Revenue website (mor.gov.et) as a data source via an automated scraper.
2.  **User Interfaces:** It provides a public-facing web interface accessible via standard web browsers on mobile and desktop devices.
3.  **Operations:** It operates independently of the MoR's internal transactional databases (SIGTAS), relying solely on public regulatory data.

## 2.3 Product Functions

The major functions of the software are:

1.  **Automated Content Acquisition:** Daily scraping of the MoR website for new regulations, proclamations, and announcements.
2.  **Vector Database Management:** Converting text documents into vector embeddings for semantic search.
3.  **Multilingual Query Processing:** Accepting and understanding queries in Amharic and English using fine-tuned transformer models.
4.  **Retrieval-Augmented Generation (RAG):** Retrieving relevant document chunks and generating context-aware answers using a Large Language Model (LLM).
5.  **Citation and Verification:** Providing references to specific legal articles or documents used to generate the answer.
6.  **Conversation Management:** Handling multi-turn conversations and maintaining

## 2.4 User Characteristics

1.  **Small Business Owners:** Low to moderate digital literacy; primarily seek compliance regarding VAT, withholding tax, and renewal deadlines. May prefer Amharic.
2.  **Corporate Tax Officers:** High digital literacy; seek specific regulatory details and complex procedural information. Comfortable with English or technical Amharic.
3.  **Individual Taxpayers:** General public needing basic TIN registration or income tax info.
4.  **System Administrators:** Technical staff responsible for monitoring the scraper health and system uptime.

**5 .Guest User (Public Taxpayer)**

1.  **Role:** An unregistered user seeking immediate answers regarding tax laws and directives.
2.  **Access:** No login credentials required.
3.  **Capabilities:** Can query the bot and receive citations based on a temporary session context.
4.  **Data Policy (Zero-Footprint):** The session exists strictly in the server's volatile memory (RAM) and is wiped immediately when the browser tab is closed.
5.  **Constraints:** Rate-limited to 15 queries per 10 minutes per IP address to prevent system abuse.

## 2.5 General Constraints

This subsection of the SRS should provide a general description of any other items that will limit the developer's options for designing the system.

1.  **Regulatory Policies:** The system must strictly adhere to published Ethiopian tax laws. It must not generate advice that contradicts Proclamations (e.g., 286/2002, 285/2002).
2.  **Hardware Limitations:** The system relies on cloud infrastructure (AWS/Azure) or local servers capable of running vector search and LLM inference.
3.  **Connectivity:** The system requires an active internet connection to function; offline mode is limited to viewing cached/previous chats.
4.  **Language Support:** Initially limited to Amharic and English; other Ethiopian languages are currently out of scope.
5.  **LLM Probabilistic Nature:** Large Language Models are inherently probabilistic, which limits explainability and creates "black-box" behavior. The system must implement deterministic evaluation metrics and confidence scoring to mitigate this constraint.
6.  **Amharic NLP Resource Scarcity:** Pre-trained models for Amharic are limited. The system must use existing multilingual models (e.g., XLM-RoBERTa, mBERT) rather than training custom models from scratch.

This section captures non-functional requirements in the customer's language. A more formal presentation of these will occur in section 3.

**2.6 Assumptions and Dependencies**

1.  **Source Availability:** It is assumed that mor.gov.et will remain accessible for scraping and that documents will continue to be published in PDF or HTML formats.
2.  **API Availability:** The project depends on the availability of LLM APIs (e.g., OpenAI or self-hosted Llama 3) and Vector Database services (Pinecone/Weaviate).
3.  **User Connectivity:** It is assumed users have access to smart devices and basic internet connectivity.

# 3\. Specific Requirements

This section contains all the software requirements at a level of detail sufficient to enable designers to design a system to satisfy those requirements, and testers to test that the system satisfies those requirements. Throughout this section, every stated requirement should be externally perceivable by users, operators, or other external systems. These requirements should include at a minimum a description of every input (stimulus) into the system, every output (response) from the system and all functions performed by the system in response to an input or in support of an output. The following principles apply:

1.  Specific requirements should be stated with all the characteristics of a good SRS

- correct
- unambiguous
- complete
- consistent
- ranked for importance and/or stability
- verifiable
- modifiable
- traceable

1.  Specific requirements should be cross-referenced to earlier documents that relate
2.  All requirements should be uniquely identifiable (usually via numbering like 3.1.2.3)
3.  Careful attention should be given to organizing the requirements to maximize readability (Several alternative organizations are given at end of document)

Before examining specific ways of organizing the requirements it is helpful to understand the various items that comprise requirements as described in the following subclasses. This section reiterates section 2, but is for developers not the customer. The customer buys in with section 2, the designers use section 3 to design and build the actual application.

### 3.1 External Interface Requirements

#### 3.1.1 User Interfaces

#### 3.1.2 Hardware Interfaces

- **Server Side:** The application shall run on virtualized cloud servers or physical servers capable of supporting Dockerized containers for the backend and vector database.
- **Client Side:** The system shall have no specific hardware requirements beyond a device capable of running a modern web browser (Chrome, Firefox, Safari, Edge).

#### 3.1.3 Software Interfaces

- **SI-01 Ministry Website:** The system shall interface with https://mor.gov.et via a Python-based web scraper (BeautifulSoup/Scrapy) to fetch public documents.
- **SI-02 Vector Database:** The system shall interface with a Vector Database (Pinecone or Weaviate) to store and retrieve document embeddings.
- **SI-03 LLM Service:** The system shall interact with an LLM provider (OpenAI API or local model interface) via REST API.
- **SI-04 Backend Framework:** The backend shall be built using Python FastAPI.
- **SI-05 Frontend Library:** The user interface shall be built using React with TypeScript.

#### 3.1.4 Communications Interfaces

- **CI-01:** The system shall use HTTPS for all communication between the client (browser) and the server.
- **CI-02:** The system shall use JSON formatting for API payloads (requests and responses).

### 3.2 Functional Requirements

#### 3.2.1 Knowledge Base Management

- **FR-01:** The system shall execute a scheduled job (cron) daily at 00:00 EAT to check for new content on the source website.
- **FR-02:** The system shall extract text from PDF and Word documents, correctly handling Amharic Unicode characters.
- **FR-03:** The system shall segment extracted text into semantic chunks (e.g., 512-1024 tokens) and generate vector embeddings.

#### 3.2.2 Query Processing

- **FR-04:** The system shall automatically detect the language of the user's input query.
- **FR-05:** The system shall classify the intent of the query (e.g., informational, procedural, definition).
- **FR-06:** The system shall perform semantic similarity searches against the vector database to retrieve the top 5-10 relevant document chunks.

#### 3.2.3 Response Generation

- **FR-07:** The system shall generate natural language responses using the retrieved chunks as the sole context (RAG pattern).
- **FR-08:** The system shall include a "Confidence Score"; if the score is below a defined threshold (e.g., 0.7), the system shall respond with a fallback message ("I don't have enough information on this topic").
- **FR-09:** The system shall cite the specific regulation or document title used to generate the response.

#### 3.2.4 Guest Users

- **FR-08.1:** Upon accessing the chat interface, the system shall prompt the Guest to select a profile (e.g., "Individual," "Small Business (Category C)," "Large Enterprise").
- **FR-08.2:** The system shall store this selection in **temporary RAM** for the duration of the active session to filter relevant tax laws (e.g., prioritizing Category C directives for Small Business users).
- **FR-08.3:** The interface shall display a persistent "Login to Save Chat" button during guest sessions.
- **FR-08.4:** If a Guest user chooses to log in mid-session, the system shall migrate the current RAM-based chat history to the persistent Database.

### 3.3 Use Cases

#### 3.3.1 Use Case #1: Taxpayer Enquires about VAT Registration

- **Pre-condition:** User navigates to the website or Telegram bot (Login not required).
- **Flow:**
    1.  User types query in Amharic/English (e.g., "How do I register for VAT?" / "እንዴት ለቫት መመዝገብ እችላለሁ?").
    2.  System detects language and classifies intent as "VAT Registration Procedure."
    3.  System retrieves VAT Proclamation No. 285/2002 sections regarding registration requirements.
    4.  System generates step-by-step registration guidance:
        - **Step 1:** Determine eligibility (annual turnover exceeds 1,000,000 ETB threshold).
        - **Step 2:** Gather required documents (TIN certificate, business license, ID, trade name registration).
        - **Step 3:** Visit nearest MoR branch or access online portal at eservices.gov.et.
        - **Step 4:** Complete VAT registration form (Form VAT-01).
        - **Step 5:** Submit documents and await VAT certificate (typically 3-5 business days).
    5.  System displays source citation: "VAT Proclamation No. 285/2002, Article 16."
    6.  System asks: "Would you like me to explain any of these steps in more detail?"
- **Post-condition (Guest):** Browser/Telegram closed → **Session Wiped (Data Lost).**
- **Post-condition (Registered):** Browser closed → Session Saved to DB for future reference.

#### 3.3.2 Use Case #3: System Updates Knowledge Base

- **Actor:** System (Automated Process)
- **Description:** Daily update of tax laws.
- **Flow:**
    1.  Scheduler triggers scraper.
    2.  Scraper detects a new directive PDF on mor.gov.et.
    3.  System downloads and processes text.
    4.  System updates vector index.
- **Postconditions:** New directive is searchable by users.

#### 3.3.3 Use Case #4: Admin Upload Document to Update Knowledge Base

- **Actor:** System Administrator / Ministry Staff
- **Description:** The admin manually uploads a new tax regulation document to update the system knowledge base immediately, bypassing the scheduled scraper.
- **Preconditions:** Admin is logged into the Admin Dashboard.
- **Flow:**
    1.  Admin navigates to the "Knowledge Base Manager" section.
    2.  Admin uploads a file via the drag-and-drop interface.
    3.  The system validates the file format and initiates processing (text extraction).
    4.  The system generates vector embeddings and indexes the content.
    5.  The system displays a "Success" status indicator to the admin.
- **Postconditions:** The new document is immediately available for user queries.

### 3.3.1 Use Case 1: Taxpayer Enquires about Tax Regulations

**Table 3.1 Use Case 1: Taxpayer Enquires about Tax Regulations**

| **Field** | **Description** |
| --- | --- |
| **Use Case ID** | UC-01 |
| --- | --- |
| **Actor** | Business Owner / Taxpayer (Primary) |
| --- | --- |
| **Goal** | To obtain accurate, cited answers regarding tax laws (e.g., VAT, Income Tax) by querying the system in natural language. |
| --- | --- |
| **Priority** | High (The core value proposition of the system) |
| --- | --- |
| **Frequency** | High (Continuous user interaction throughout the day) |
| --- | --- |
| **Preconditions** | • The user has accessed the web portal via a compatible browser.<br><br>• The Vector Database (SI-02) is online and populated with indexed documents.<br><br>• The LLM Service (SI-03) is operational. |
| --- | --- |
| **Postconditions** | **Success:** The user receives a natural language answer with specific citations to the Proclamation/Regulation.<br><br>**Failure:** The user receives a fallback message indicating the system cannot answer with high confidence. |
| --- | --- |
| **Main Success Scenario** | 1\. The user navigates to the "Ask an Expert" / Chat interface.<br><br>2\. The user types a query (e.g., "What is the threshold for VAT registration?") in either Amharic or English.<br><br>3\. The system detects the input language and classifies the intent (FR-04, FR-05).<br><br>4\. The system converts the user query into a vector embedding.<br><br>5\. The system performs a semantic similarity search against the Vector Database (Pinecone/Weaviate) to retrieve the top 5–10 relevant document chunks.<br><br>6\. The system constructs a prompt containing the user query and the retrieved chunks as context.<br><br>7\. The system sends the prompt to the LLM Service (OpenAI/Local Model).<br><br>8\. The system calculates a Confidence Score based on the relevance of the retrieved chunks.<br><br>9\. The system generates a natural language response (FR-07) citing the specific monetary threshold (e.g., "1,000,000 ETB") and the source Proclamation number.<br><br>10\. The system displays the answer and renders clickable citations for the source documents. |
| --- | --- |
| **Alternative Flows** | **A1: Low Confidence / No Relevant Information Found (at Step 8)**<br><br>• The system calculates a confidence score below the threshold (e.g., < 0.7).<br><br>• The system halts generation of a factual answer to prevent hallucination.<br><br>• The system displays: _"I don't have enough information in the current tax laws to answer this specific question accurately. Please consult a tax officer directly."_<br><br>**A2: Language Detection Failure / Mixed Language**<br><br>• The system detects mixed Amharic/English or an unsupported language.<br><br>• The system defaults to English processing but appends a note: _"Responding based on English interpretation."_<br><br>**A3: Service Timeout (Vector DB or LLM)**<br><br>• The backend fails to receive a response within 10 seconds.<br><br>• The system displays: _"The knowledge base is currently experiencing high traffic. Please try your query again in a moment."_ |
| --- | --- |
| **Exceptions** | • **Rate Limiting:** If a user makes >20 requests/minute, the system temporarily blocks the IP and shows a "Too Many Requests" error.<br><br>• **Profanity Detection:** If the input contains offensive language, the system refuses to process the query. |
| --- | --- |
| **Non-Functional Considerations** | • **Latency:** Total response time should be < 3 seconds.<br><br>• **Accuracy:** Citations must point to the correct Article/Proclamation 95% of the time.<br><br>• **Encoding:** Full support for Amharic Unicode (Ethiopic script) in both input and output. |
| --- | --- |

### 3.3.2 Use Case 2: Automated Knowledge Base Update

**Table 3.2 Use Case 2: Automated Knowledge Base Update**

| **Field** | **Description** |
| --- | --- |
| **Use Case ID** | UC-02 |
| --- | --- |
| **Actor** | System (Automated Cron Job) |
| --- | --- |
| **Goal** | To automatically detect, download, and index new tax directives from the Ministry of Revenues website without human intervention. |
| --- | --- |
| **Priority** | Medium (Background maintenance process) |
| --- | --- |
| **Frequency** | Daily (Scheduled at 00:00 EAT) |
| --- | --- |
| **Preconditions** | • The host server has internet access to https://mor.gov.et.<br><br>• The Python Scraper module is configured correctly.<br><br>• The Vector Database is writable. |
| --- | --- |
| **Postconditions** | **Success:** New documents are indexed, and the system is aware of the latest regulations.<br><br>**Failure:** Administrator is notified of scraper failure; no partial/corrupt data is indexed. |
| --- | --- |
| **Main Success Scenario** | 1\. The system scheduler triggers the scraping job at 00:00 EAT.<br><br>2\. The Scraper connects to the Ministry website and scans the "Directives/Proclamations" page.<br><br>3\. The system identifies a new document (PDF/Word) that does not exist in the local document hash registry.<br><br>4\. The system downloads the document to temporary storage.<br><br>5\. The system performs text extraction, specifically handling Amharic Unicode characters and multi-column PDF layouts (FR-02).<br><br>6\. The system segments the text into semantic chunks (512–1024 tokens).<br><br>7\. The system generates embeddings for the chunks and upserts them into the Vector Database.<br><br>8\. The system updates the local registry with the new file's hash to prevent re-downloading.<br><br>9\. The system logs a "Success" entry in the admin audit log. |
| --- | --- |
| **Alternative Flows** | **A1: No New Documents Found (at Step 3)**<br><br>• The scraper detects that all available files match the existing registry.<br><br>• The system logs "No updates found" and terminates the job gracefully.<br><br>**A2: Source Website Unavailable (at Step 2)**<br><br>• The system receives a 404 or 500 error from mor.gov.et.<br><br>• The system retries 3 times with exponential backoff.<br><br>• If still failing, the system logs a "Source Unreachable" error and sends an alert email to the System Admin.<br><br>**A3: Unreadable PDF / OCR Failure (at Step 5)**• The downloaded file is a scanned image without a text layer.<br><br>• The system attempts OCR. If confidence is low, it flags the file as "Requires Manual Review" in the Admin Dashboard and skips indexing to prevent garbage data. |
| --- | --- |
| **Exceptions** | • **Disk Space Full:** The job terminates and sends a critical alert.<br><br>• **API Limit Reached (Embedding Provider):** The system pauses the batch job and resumes when the rate limit resets. |
| --- | --- |
| **Non-Functional Considerations** | • **Processing Window:** The update process must complete between 00:00 and 06:00 EAT to minimize impact on daytime query performance.<br><br>• **Data Integrity:** The system must ensure no duplicate vectors are created for the same document. |
| --- | --- |

### 3.3.3 Use Case #3: Admin Upload Document (Manual Override)

**Table 3.3 Use Case #3: Admin Upload Document**

| **Field** | **Description** |
| --- | --- |
| **Use Case ID** | UC-03 |
| --- | --- |
| **Actor** | System Administrator / Ministry Staff |
| --- | --- |
| **Goal** | To manually introduce urgent regulations or internal documents into the knowledge base immediately, bypassing the daily schedule. |
| --- | --- |
| **Priority** | Medium (Critical for urgent policy changes) |
| --- | --- |
| **Frequency** | Low (On-demand/Ad-hoc) |
| --- | --- |
| **Preconditions** | • The Admin is logged into the Admin Dashboard with "Editor" privileges.<br><br>• The document is available in a supported format (PDF, DOCX, TXT). |
| --- | --- |
| **Postconditions** | **Success:** The uploaded document is immediately searchable by end-users via UC-01.<br><br>**Failure:** The user receives a descriptive error message; database remains unchanged. |
| --- | --- |
| **Main Success Scenario** | 1\. The Admin logs in and navigates to the "Knowledge Base Manager" section.<br><br>2\. The Admin clicks "Add New Document" and selects the file via the drag-and-drop interface.<br><br>3\. The system performs client-side validation (File type check, Size < 25MB).<br><br>4\. The Admin clicks "Upload & Process".<br><br>5\. The system uploads the file to the server and initiates the Text Extraction Pipeline.<br><br>6\. The system displays a progress bar (Parsing -> Chunking -> Embedding -> Indexing).<br><br>7\. The system successfully adds vectors to the database.<br><br>8\. The system displays a "Processing Complete" success message and shows a preview of the extracted text for verification.<br><br>9\. The new document status changes to "Active/Searchable". |
| --- | --- |
| **Alternative Flows** | **A1: Invalid File Format (at Step 3)**<br><br>• The user attempts to upload an unsupported file (e.g., .EXE, .ZIP).<br><br>• The system blocks the upload and displays: _"Invalid file type. Please upload PDF, DOCX, or TXT only."_<br><br>**A2: Text Extraction Failure (at Step 5)**<br><br>• The system cannot interpret the text encoding (e.g., corrupted Amharic font).<br><br>• The system halts processing and displays: _"Encoding Error: Could not extract text. Please check the document font or convert to standard UTF-8."_<br><br>**A3: Duplicate Document (at Step 5)**<br><br>• The system detects the content hash already exists in the vector store.<br><br>• The system asks: _"This document appears to be a duplicate. Do you want to overwrite it?"_<br><br>• The Admin selects Yes (Overwrite) or No (Cancel). |
| --- | --- |
| **Exceptions** | • **Network Interruption:** If the upload is interrupted, the system allows the user to retry without re-selecting the file.<br><br>• **Security Trigger:** If the file contains malware signatures, the server rejects it immediately and logs a security incident. |
| --- | --- |
| **Non-Functional Considerations** | • **Time to Live:** The document must be searchable within < 1 minute of upload completion.<br><br>• **Feedback:** The UI must provide real-time feedback during the embedding generation phase so the Admin knows the system hasn't frozen. |
| --- | --- |

### 3.4 Non-Functional Requirements

#### 3.4.1 Performance

1.  **NFR-01:** The system shall respond to user queries in less than 5 seconds on average, with a 95th percentile latency of <8 seconds.
2.  **NFR-02:** The scraper shall process new documents during off-peak hours (00:00-06:00 EAT) to minimize server load.
3.  **NFR-03:** The system shall support at least 100 concurrent users without performance degradation.

#### 3.4.2 Accuracy & Hallucination Prevention

1.  **NFR-04:** The system shall achieve a **Top-5 Retrieval Accuracy** of ≥85% (correct source document in top 5 results).
2.  **NFR-05:** The system shall maintain a **Hallucination Rate** of <5% as measured by manual sampling of 100 random responses monthly.
3.  **NFR-06:** The system shall achieve **Citation Accuracy** of ≥95% (cited Proclamation/Article matches the generated answer content).
4.  **NFR-07:** The system shall implement a **Confidence Threshold** of 0.7; responses below this threshold shall trigger a fallback message rather than potentially incorrect information.
5.  **NFR-08:** The system shall correctly classify user **Intent** with ≥90% accuracy across categories: Informational, Procedural, Definition, Clarification.

#### 3.4.3 Reliability

1.  **NFR-09:** The system shall implement exception handling to prevent crashes during PDF parsing errors or LLM timeouts.
2.  **NFR-10:** The system shall maintain an **Error Recovery Rate** of ≥95% (automatic recovery from transient failures).

#### 3.4.4 Availability

1.  **NFR-11:** The chatbot service shall be available 24/7, with a targeted uptime of 99.5%.
2.  **NFR-12:** Scheduled maintenance windows shall not exceed 4 hours per month.

#### 3.4.5 Security

1.  **NFR-13:** The system shall **not** request or store user Personal Identifiable Information (PII) such as TINs, names, or phone numbers.
2.  **NFR-14:** Conversation logs used for evaluation shall be anonymized before storage.
3.  **NFR-15:** To prevent abuse, the system shall enforce a rate limit of **15 requests per 10 minutes** per unique Client IP address using Redis cache.

#### 3.4.6 Multilingual Accuracy

1.  **NFR-16:** The system shall achieve equivalent accuracy (±5%) for queries in both Amharic and English.
2.  **NFR-17:** The system shall correctly handle code-switched queries (mixed Amharic-English) with ≥80% intent classification accuracy.

#### 3.4.7 Maintainability & Evaluation

1.  **NFR-18:** The code shall follow standard linting rules (ESLint/Prettier for frontend, Black/Ruff for Python backend).
2.  **NFR-19:** The system shall maintain version history of regulations to answer queries based on past effective dates.
3.  **NFR-20:** The system shall log all queries and responses (anonymized) for monthly evaluation using **Exact Match (EM)**, **F1 Score**, and **BERTScore** metrics.
4.  **NFR-21:** The system shall track **Session Success Rate** (user query resolved without escalation) targeting ≥80%.
5.  **NFR-22:** The system shall measure **Escalation Rate** (queries requiring human intervention) targeting <10%.

### 3.5 Inverse Requirements

1.  The system shall not perform tax calculations (e.g., calculating the exact tax amount for a specific salary).
2.  The system shall not allow users to file taxes directly through the chat interface.
3.  The system shall not support voice interaction in the initial release.
4.  The system shall not provide binding legal advice; all responses include a disclaimer.

### 3.6 Design Constraints

1.  **Language Models:** Must use pre-trained multilingual models capable of processing Amharic (e.g., XLM-RoBERTa for embeddings, GPT-4/Llama 3 for generation). Custom model training is out of scope due to Amharic data scarcity.
2.  **Data Residency:** Cloud hosting choices should consider Ethiopian data residency guidelines if applicable/available.
3.  **LLM Probabilistic Nature:** The inherent non-deterministic behavior of LLMs limits explainability. The system addresses this through:
    - Hybrid retrieval (BM25 + semantic search) for more deterministic document matching
    - Confidence scoring with explicit thresholds
    - Mandatory source citations for every factual claim
    - Structured evaluation metrics (EM, F1, ROUGE, BERTScore) for objective measurement
4.  **Prompt Engineering over Fine-Tuning:** Due to limited Amharic training data and computational constraints, the system prioritizes prompt engineering and RAG over model fine-tuning.

### 3.7 Project Contributions & Innovations

This project advances beyond naive RAG implementations through the following contributions:

1.  **Localized RAG for Ethiopian Tax Domain:**
    - Amharic-optimized text processing with proper Unicode handling for Ethiopic script
    - Ethiopia-specific tax terminology mapping and entity recognition
    - Bilingual (Amharic/English) knowledge base with cross-lingual retrieval

2.  **Hybrid Retrieval Architecture:**
    - **BM25 Keyword Matching:** Addresses semantic search limitations for exact legal terms and Proclamation numbers
    - **Dense Vector Retrieval:** Captures semantic similarity for conceptual queries
    - **Reciprocal Rank Fusion:** Combines both approaches for superior retrieval accuracy
    - **GraphRAG Integration (Future):** Knowledge graph for tax entity relationships (TIN → Business → VAT Status)

3.  **Deterministic Evaluation Framework:**
    - Objective metrics replacing subjective assessments
    - Automated hallucination detection through citation verification
    - A/B testing infrastructure for prompt optimization

4.  **Explainable Responses:**
    - Chain-of-retrieval transparency showing which documents informed the answer
    - Source document lineage for audit trails

### 3.8 Logical Database Requirements

1.  **Vector Database:** Stores high-dimensional embeddings of tax documents.
2.  **Relational Database (PostgreSQL):** Stores system metadata, anonymized conversation logs for analytics, and user feedback ratings.

### 3.9 Technology Stack

The system will use the following technology stack:

- **Frontend:** Next.js (React with TypeScript)
- **Backend:** Python FastAPI with LangChain orchestration
- **Database:** PostgreSQL with pgvector extension for vector storage
- **Full-text Search:** PostgreSQL built-in full-text search capabilities
- **LLM:** Gemini 2.5 Flash as primary model
- **Embeddings:** multilingual-e5-large for vector representations
- **Interfaces:** Web application and Telegram bot

The detailed algorithmic components and technical implementation specifications are documented in the Software Design Specification (SDS) document.

### 3.11 Other Requirements

1.  **Legal:** The system must include a disclaimer stating that the bot provides information for guidance only and does not replace official legal counsel.
2.  **Packaging:** The final deliverable shall be packaged as a Docker container set for easy deployment.
3.  **Telegram Integration:** The system shall provide a Telegram bot interface (@ERATaxBot) with feature parity to the web interface.

## 4\. Change Management Process

This section defines the formal protocol for modifying the project's scope, requirements, or architecture. It ensures that all changes are transparent, agreed upon by the team, and approved by the advisor before implementation.

### 4.1 Change Request Lifecycle

The process for updating the SRS or project scope follows these five steps:

1.  **Identification:** A potential change is identified by a team member, advisor, or stakeholder.
    - _Examples:_ Technical limitations discovered during development, new regulations from the Ministry, or feedback from the Advisor.
2.  **Documentation & Submission:** The change is formally documented.
    - **Tool:** GitHub Issues (labeled change-request).
    - **Required Info:** Description of change, justification ("Why is this needed?"), impact on timeline, and affected modules.
3.  **Team Review & Consensus:**
    - The change is discussed during the weekly **Project Meeting**.
    - **Voting Protocol:** A proposed change requires a **majority vote (3 out of 5 members)** to proceed to the Advisor Consultation phase.
    - **Conflict Resolution:** If the team is split, the Project Manager (Student Lead) makes the deciding recommendation.
4.  **Advisor Consultation & Approval:**
    - **Major Changes** (affecting scope, deadlines, or core technology) must be presented to the **Project Advisor (Mr. Daniel Abebe)**.
    - The team must present the _Technical Feasibility_ and _Revised Timeline_ to the Advisor.
    - **Formal Sign-off:** The Advisor gives verbal or written approval to proceed.
5.  **Implementation & Update:**
    - The SRS document is updated (version number incremented).
    - The change is added to the project backlog/sprint.
    - All team members are notified via the shared communication channel
    - (Telegram/Email)

### 4.2 Roles and Responsibilities

1.  **Project Team Members:**
    1.  Responsible for identifying technical risks and proposing viable alternatives.
    2.  Must participate in the voting process for changes.
    3.  Must adhere to the agreed-upon changes once approved.
2.  **Project Manager (Student Lead):**
    1.  Responsible for logging the Change Request in GitHub.
    2.  Facilitates the discussion during team meetings.
    3.  Acts as the primary liaison with the Advisor regarding scope changes.
3.  **Project Advisor (Mr. Daniel Abebe):**
    1.  Provides the final authority on changes that impact the project's academic validity or completion date.
    2.  Ensures the project remains within the scope of the university's requirements.

### 4.3 Documentation of Changes

1.  All approved changes must be recorded in the **Revision History** table of this SRS document.
2.  Meeting minutes where changes were discussed and voted upon must be saved in the shared project folder for transparency.

# 5\. References

1.  **Ethiopian Tax Law Assistant (2025).** _RAG implementation using LangChain and LLaMA3._ \[Online\]. Available: https://app.readytensor.ai/publications/ethiopian-tax-law-assistant-9zFCDKHMAuRd
2.  **PiSpace (2025).** _Biritu Finance Bot: Guide to Financial Wellness in Ethiopia._ \[Online\]. Available: https://pispace.co/ai/projects/biritu-finance-bot
3.  **Addis Ababa University.** _Machine Learning Models for Amharic Clinical Chatbot/NLP._ \[Online\]. Available: https://etd.aau.edu.et/bitstreams/b6b1e93e-7026-4d30-8824-2f776efbf401/download
4.  **Lewis, P., et al. (2020).** _Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks._ arXiv:2005.11401.
5.  **International Monetary Fund (IMF) (2024).** _Understanding AI in Tax and Customs Administrations._ \[Online\]. Available: https://www.elibrary.imf.org/view/journals/005/2024/006/article-A001-en.xml
6.  **South African Revenue Service (SARS).** _ChatBot Lwazi Enhancements._ \[Online\]. Available: https://www.sars.gov.za/latest-news/chatbot-lwazi-enhancements/
7.  **Business Daily Africa.** _KRA targets small traders with WhatsApp tax invoicing._ \[Online\]. Available: https://www.businessdailyafrica.com/bd/economy/kra-targets-small-traders-with-whatsapp-tax-invoicing-4800038

## 6\. Appendices

### A.1 Appendix 1: Tools and Technologies

## Backend: Python, FastAPIFrontend: React, TypeScriptAI/ML: OpenAI API / Llama 3, LangChainDatabase: Pinecone (Vector), PostgreSQL (Relational)Scraping: BeautifulSoup, Scrapy

### A.2 Appendix 2: Definitions

## RAG: Retrieval-Augmented Generation.LLM: Large Language Model.TIN: Taxpayer Identification Number.MoR: Ministry of Revenue.