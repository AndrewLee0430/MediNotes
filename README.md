# MediNotes 🏥

AI-powered medical knowledge assistant for healthcare professionals.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![Next.js 14](https://img.shields.io/badge/Next.js-14-black)](https://nextjs.org/)

## 🎯 Overview

MediNotes helps healthcare professionals quickly access accurate medical information...

（继续保留完整内容，删除所有 <<<<<<<、=======、>>>>>>> 标记）

## 🏗️ Architecture
```mermaid
graph TB
    subgraph "User Interface"
        A[Next.js Frontend]
    end
    
    subgraph "API Layer"
        B[FastAPI Server]
        C[Cache Layer]
    end
    
    subgraph "Data Sources"
        D[Local Vector DB<br/>191 drugs, 690 docs]
        E[PubMed API]
        F[FDA OpenFDA]
    end
    
    subgraph "AI Engine"
        G[OpenAI GPT-4o-mini]
        H[LangChain RAG]
    end
    
    A --> B
    B --> C
    C --> D
    C --> E
    C --> F
    B --> H
    H --> G
    H --> D
    
    style D fill:#d4edda
    style C fill:#ffe1e1
```

（继续保留剩余内容）