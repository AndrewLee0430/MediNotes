graph TD
    %% 節點樣式定義
    classDef research fill:#ff8e6e22,stroke:#ff8e6e,stroke-width:2px,color:#ff8e6e
    classDef verify fill:#63b3ed22,stroke:#63b3ed,stroke-width:2px,color:#63b3ed
    classDef explain fill:#68d39122,stroke:#68d391,stroke-width:2px,color:#68d391
    classDef guard fill:#fc818122,stroke:#fc8181,stroke-width:2px,color:#fc8181
    classDef infra fill:#b794f422,stroke:#b794f4,stroke-width:2px,color:#b794f4
    classDef db fill:#f6e05e22,stroke:#f6e05e,stroke-width:2px,color:#f6e05e
    classDef ext fill:#76e4f722,stroke:#76e4f7,stroke-width:2px,color:#76e4f7

    %% 頂部層級
    User([User - Any Language]) -- HTTPS --> FE[Next.js 14 Frontend]
    FE -- REST / SSE --> Auth[Clerk JWT Auth]
    Auth --> API[FastAPI Backend]

    %% Input Guards 子圖
    subgraph Guards [🛡️ INPUT GUARDS - Cheapest to Expensive]
        G0[0. Length Check] --> G1[1. PHI Regex]
        G1 --> G2[2. Injection Check]
        G2 --> G3[3. Intent GPT-4-mini]
        G3 --> G4[4. Rate Limit]
    end
    
    API --> G0
    G4 -- Passed --> Router{Pipeline Router}

    %% Research Pipeline
    subgraph RP [🔍 RESEARCH PIPELINE]
        R1[Query Rewriting] --> R_Data{Data Retrieval}
        R_Data --> R_DB[(Chroma DB)]
        R_Data --> R_Pub[PubMed API]
        R_Data --> R_FDA[FDA API]
        R_DB & R_Pub & R_FDA --> R2[Dedup + Year Boost]
        R2 --> R3[LLM-as-Judge]
        R3 --> R4[Reranker top_k=8]
        R4 --> R5[GPT-4.1 Generator]
    end

    %% Verify Pipeline
    subgraph VP [✅ VERIFY PIPELINE]
        V1[Drug Name Parser] --> V2[Levenshtein Correction]
        V2 --> V3[FDA Cache Check]
        V3 -- miss --> V4[OpenFDA Live API]
        V4 & V3 --> V5[GPT-4 Interaction Analysis]
        V5 --> V6[Structured Response]
    end

    %% Explain Pipeline
    subgraph EP [📖 EXPLAIN PIPELINE]
        E1[Language Detection] --> E2[Entity Extractor]
        E2 --> E_Data{External Knowledge}
        E_Data --> E_LOINC[LOINC]
        E_Data --> E_Rx[RxNorm]
        E_Data --> E_Med[MedlinePlus]
        E_LOINC & E_Rx & E_Med --> E3[Cache Layer]
        E3 --> E4[GPT-4 Explanation]
    end

    %% 連接 Router 到各個 Pipeline
    Router -->|Research Query| RP
    Router -->|Drug Interaction| VP
    Router -->|Lab/Med Terms| EP

    %% 基礎設施
    subgraph Infra [⚙️ INFRASTRUCTURE]
        PG[(PostgreSQL - History/Audit)]
        VDB[(ChromaDB - Vector Store)]
        SC[SimpleCache - In-memory]
        SSE[SSE Stream]
    end

    %% 樣式套用
    class G0,G1,G2,G3,G4 guard
    class R1,R2,R3,R4,R5 research
    class V1,V2,V5,V6 verify
    class E1,E2,E4 explain
    class PG,SC,SSE,Auth infra
    class R_DB,V3,E3,VDB db
    class R_Pub,R_FDA,V4,E_LOINC,E_Rx,E_Med ext
