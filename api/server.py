"""
MediNotes API Server
FastAPI 後端，整合諮詢筆記、RAG 檢索、FDA 驗證、合規防護與數據飛輪回饋
"""

from api.data_sources.fda import FDAClient
from api.data_sources.fda_cached import fda_client_cached

from dotenv import load_dotenv
import os

load_dotenv()  # 載入 .env 檔案

import os
import json
import time
from pathlib import Path
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from fastapi_clerk_auth import ClerkConfig, ClerkHTTPBearer, HTTPAuthorizationCredentials
from openai import OpenAI
from sqlalchemy.orm import Session
from sqlalchemy import desc

# --- 內部模組引用 ---
from api.models.schemas import (
    ResearchRequest,
    SuggestionsResponse,
    StreamEvent,
    StreamEventType,
    VerifyRequest, 
    VerifyResponse, 
    DrugInteraction
)
from api.rag.retriever import HybridRetriever
from api.rag.generator import AnswerGenerator
from api.data_sources.fda import FDAClient
from api.middleware.phi_handler import PHIDetector
from api.database.sql_db import get_db, engine, Base
from api.models.sql_models import AuditLog, UserFeedback, ChatHistory


# ============================================================
# 生命週期管理 (啟動時建立資料庫 Tables)
# ============================================================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 確保資料庫 Tables (含 user_feedback, chat_history) 存在
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title="MediNotes API",
    description="AI-powered medical assistant for healthcare professionals",
    version="2.1.0", 
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Clerk authentication
clerk_config = ClerkConfig(jwks_url=os.getenv("CLERK_JWKS_URL"))
clerk_guard = ClerkHTTPBearer(clerk_config)

# 初始化元件
retriever = HybridRetriever(
    local_threshold=0.6,
    enable_local=True,
    enable_pubmed=True,
    enable_fda=True
)
generator = AnswerGenerator(model="gpt-4o-mini")
fda_client = FDAClient()   # 使用缓存版本


# ============================================================
# Middleware: Audit Log & PHI 防護
# ============================================================
@app.middleware("http")
async def audit_middleware(request: Request, call_next):
    path = request.url.path
    
    # ✅ 串流端点直接跳过（不读取 body）
    if path in ["/api/research", "/api/consultation"]:
        return await call_next(request)
    
    # ✅ 非串流端点才进行 PHI 检查
    if path in ["/api/verify", "/api/feedback"] and request.method == "POST":
        try:
            body_bytes = await request.body()
            body_str = body_bytes.decode("utf-8")
            
            # PHI 檢查
            phi_type = PHIDetector.detect(body_str)
            if phi_type:
                return StreamingResponse(
                    iter([json.dumps({
                        "type": "error", 
                        "content": f"⚠️ 安全攔截：偵測到潛在的個人資訊 ({phi_type})。為符合隱私規範，請移除後再試。"
                    })]), 
                    media_type="application/json",
                    status_code=400
                )
                
            async def receive():
                return {"type": "http.request", "body": body_bytes}
            request._receive = receive
            
        except Exception as e:
            print(f"Middleware Error: {e}")

    response = await call_next(request)
    return response


# ============================================================
# 功能 1：諮詢筆記生成 (Consultation)
# ============================================================

class Visit(BaseModel):
    patient_name: str
    date_of_visit: str
    notes: str

consultation_system_prompt = """
You are provided with notes written by a doctor from a patient's visit.
Your job is to summarize the visit for the doctor and provide an email.
Reply with exactly three sections with the headings:
### Summary of visit for the doctor's records
### Next steps for the doctor
### Draft of email to patient in patient-friendly language
"""

def user_prompt_for(visit: Visit) -> str:
    return f"""Create the summary, next steps and draft email for:
Patient Name: {visit.patient_name}
Date of Visit: {visit.date_of_visit}
Notes:
{visit.notes}"""

@app.post("/api/consultation")
def consultation_summary(
    visit: Visit,
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard),
    db: Session = Depends(get_db)
):
    user_id = creds.decoded["sub"]
    client = OpenAI()
    
    try:
        audit = AuditLog(
            id=f"doc_{int(time.time()*1000)}",
            user_id=user_id,
            action="consultation_gen",
            query_content="Generated consultation note summary",
            ip_address="0.0.0.0"
        )
        db.add(audit)
        db.commit()
    except Exception as e:
        print(f"Audit Log Error: {e}")

    user_prompt = user_prompt_for(visit)
    prompt = [
        {"role": "system", "content": consultation_system_prompt},
        {"role": "user", "content": user_prompt},
    ]
    
    stream = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=prompt,
        stream=True,
    )
    
    def event_stream():
        for chunk in stream:
            text = chunk.choices[0].delta.content
            if text:
                lines = text.split("\n")
                for line in lines[:-1]:
                    yield f"data: {line}\n\n"
                    yield "data:  \n"
                yield f"data: {lines[-1]}\n\n"
    
    return StreamingResponse(event_stream(), media_type="text/event-stream")


# ============================================================
# 功能 2：醫學研究查詢 (Research / RAG)
# ============================================================

@app.post("/api/research")
async def research_query(
    request: ResearchRequest,
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard),
    db: Session = Depends(get_db)
):
    user_id = creds.decoded["sub"]
    start_time = time.time()
    
    async def event_stream():
        full_answer = ""
        
        try:
            documents = await retriever.retrieve(
                query=request.question,
                max_results=request.max_results or 5,
                source_filter=request.sources
            )
            
            async for event in generator.generate_stream(
                question=request.question,
                documents=documents
            ):
                if event.type == StreamEventType.ANSWER:
                    content = event.content or ""
                    full_answer += content
                    yield f"data: {json.dumps({'type': 'answer', 'content': content}, ensure_ascii=False)}\n\n"
                
                elif event.type == StreamEventType.CITATIONS:
                    citations_data = [c.model_dump() for c in event.content]
                    
                    # 記錄 Audit Log
                    try:
                        audit = AuditLog(
                            id=f"res_{int(time.time()*1000)}",
                            user_id=user_id,
                            action="research",
                            query_content=PHIDetector.sanitize_for_log(request.question),
                            resource_ids=[c.get('source_id') for c in citations_data],
                            ip_address="0.0.0.0"
                        )
                        db.add(audit)
                        db.commit()
                    except Exception as e:
                        print(f"Audit Log Error: {e}")

                    yield f"data: {json.dumps({'type': 'citations', 'content': citations_data}, ensure_ascii=False)}\n\n"
                
                elif event.type == StreamEventType.ERROR:
                    yield f"data: {json.dumps({'type': 'error', 'content': event.content}, ensure_ascii=False)}\n\n"
                
                elif event.type == StreamEventType.DONE:
                    elapsed_ms = int((time.time() - start_time) * 1000)
                    
                    # 儲存到 ChatHistory
                    try:
                        history = ChatHistory(
                            user_id=user_id,
                            session_type="research",
                            question=PHIDetector.sanitize_for_log(request.question),
                            answer=full_answer
                        )
                        db.add(history)
                        db.commit()
                    except Exception as e:
                        print(f"History Save Error: {e}")

                    yield f"data: {json.dumps({'type': 'done', 'query_time_ms': elapsed_ms}, ensure_ascii=False)}\n\n"
        
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)}, ensure_ascii=False)}\n\n"
            yield f"data: {json.dumps({'type': 'done'}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.get("/api/research/suggestions")
async def get_suggestions(creds: HTTPAuthorizationCredentials = Depends(clerk_guard)):
    return SuggestionsResponse.default_suggestions()


# ============================================================
# 功能 3：藥物交互作用驗證 (Verify)
# ============================================================

@app.post("/api/verify", response_model=VerifyResponse)
async def verify_drug_interaction(
    request: VerifyRequest,
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard),
    db: Session = Depends(get_db)
):
    start_time = time.time()
    user_id = creds.decoded["sub"]
    
    # 1. 搜尋 FDA 藥品標籤
    drug_labels = []
    for drug in request.drugs:
        # 保持异步调用
        labels = await fda_client.search_drug_labels(drug, limit=1)
        if labels:
            drug_labels.append(labels[0])
    
    # 2. 如果沒有找到任何藥品資料，提前返回
    if not drug_labels:
        try:
            db.add(AuditLog(
                id=f"ver_{int(time.time()*1000)}",
                user_id=user_id,
                action="verify_failed",
                query_content=f"No FDA data for: {request.drugs}",
                ip_address="0.0.0.0"
            ))
            db.commit()
        except: 
            pass

        return VerifyResponse(
            drugs_analyzed=request.drugs,
            interactions=[],
            summary="無法在 FDA 資料庫中找到這些藥物的標籤資訊，請確認拼字或使用英文藥名。",
            risk_level="Unknown",
            query_time_ms=int((time.time() - start_time) * 1000)
        )

    # 3. 準備 LLM 分析的 context
    fda_context = "\n".join([label.to_text() for label in drug_labels])
    
    system_prompt = """You are a clinical pharmacist. Analyze the provided FDA drug labels for interactions.
    Identify interactions between the listed drugs.
    Classify severity as: Critical, Major, Moderate, Minor.
    
    CRITICAL: You MUST return valid JSON with this EXACT structure:
    {
        "interactions": [
            {
                "drugs": ["Drug1", "Drug2"],
                "severity": "Major",
                "description": "Detailed description of the interaction",
                "recommendation": "Clinical recommendation"
            }
        ],
        "summary": "Brief summary of findings",
        "risk_level": "Major"
    }
    
    IMPORTANT RULES:
    1. The "drugs" field MUST be an array with exactly 2 drug names (strings)
    2. NEVER use empty arrays [] for the "drugs" field
    3. Drug names must match the input drugs exactly
    4. If no interactions found, return an empty "interactions" array: []
    5. Always include "summary" and "risk_level" fields
    
    Output JSON only, no additional text."""
    
    user_prompt = f"""
    Patient Context: {request.patient_context or 'None'}
    Drugs to Analyze: {', '.join(request.drugs)}
    
    Reference FDA Data:
    {fda_context}
    
    Please analyze interactions between these drugs based on the FDA data provided.
    """
    
    # 4. 呼叫 LLM 進行分析（带重试机制）
    client = OpenAI()
    summary = ""
    interactions = []
    risk_level = "Unknown"
    max_retries = 2  # ✅ 最多重试 2 次
    analysis_success = False
    
    for attempt in range(max_retries):
        try:
            completion = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                response_format={"type": "json_object"}
            )
            
            analysis = json.loads(completion.choices[0].message.content)
            
            # ✅ 添加严格的字段验证
            temp_interactions = []
            for item in analysis.get("interactions", []):
                try:
                    # 验证必要字段
                    drugs = item.get("drugs", [])
                    
                    # 跳过无效数据
                    if not drugs or len(drugs) < 2:
                        print(f"⚠️ Warning: Invalid interaction data - missing or incomplete drug_pair: {item}")
                        continue
                    
                    # 验证 drugs 是否为有效的药物名称
                    if not all(isinstance(d, str) and d.strip() for d in drugs):
                        print(f"⚠️ Warning: Invalid drug names: {drugs}")
                        continue
                    
                    # 创建交互作用对象
                    drug1, drug2 = drugs[0], drugs[1]
                    # ✅ 生成 FDA DailyMed 链接
                    source_url = f"https://dailymed.nlm.nih.gov/dailymed/search.cfm?labeltype=all&query={drug1.replace(' ', '+')}"
                    
                    temp_interactions.append(DrugInteraction(
                        drug_pair=tuple(drugs[:2]),  # 只取前两个
                        severity=item.get("severity", "Unknown"),
                        description=item.get("description", "No description provided"),
                        clinical_recommendation=item.get("recommendation", ""),
                        source="FDA Label Analysis",
                        source_url=source_url  # ✅ 添加链接
                    ))
                    
                except Exception as e:
                    print(f"⚠️ Error parsing interaction item: {e}, item: {item}")
                    continue  # 跳过这个交互作用，继续处理其他的
            
            # ✅ 如果成功解析到交互作用，或者没有交互作用（空数组也是成功），则退出重试
            interactions = temp_interactions
            
            # 检查是否成功（至少解析到一些数据，或者明确没有交互作用）
            if interactions or analysis.get("interactions") is not None:
                print(f"✅ Analysis successful on attempt {attempt + 1}")
                analysis_success = True
                break  # 成功，退出重试
            else:
                print(f"⚠️ Attempt {attempt + 1} failed - no valid interactions parsed")
                if attempt < max_retries - 1:
                    print(f"🔄 Retrying... ({attempt + 2}/{max_retries})")
                    continue
                    
        except Exception as e:
            print(f"❌ LLM call failed on attempt {attempt + 1}: {e}")
            if attempt < max_retries - 1:
                print(f"🔄 Retrying... ({attempt + 2}/{max_retries})")
                continue
            else:
                # 最后一次尝试也失败了
                summary = f"分析失敗，已重試 {max_retries} 次。錯誤: {str(e)}"
                risk_level = "Unknown"
    
    # ✅ 在重试循环外生成 summary
    if analysis_success:
        if interactions:
            # 有找到交互作用，生成準確的 summary
            severity_counts = {}
            for interaction in interactions:
                severity = interaction.severity
                severity_counts[severity] = severity_counts.get(severity, 0) + 1
            
            # 生成更準確的 summary
            summary_parts = []
            for severity, count in sorted(
                severity_counts.items(), 
                key=lambda x: {"Critical": 4, "Major": 3, "Moderate": 2, "Minor": 1}.get(x[0], 0), 
                reverse=True
            ):
                summary_parts.append(f"{count} 個{severity}")
            
            summary = f"發現 {len(interactions)} 個藥物交互作用：{', '.join(summary_parts)}。請參閱下方詳細說明並諮詢專業醫療人員。"
            
            # 根據最高嚴重度設定 risk_level
            if any(i.severity == "Critical" for i in interactions):
                risk_level = "Critical"
            elif any(i.severity == "Major" for i in interactions):
                risk_level = "Major"  
            elif any(i.severity == "Moderate" for i in interactions):
                risk_level = "Moderate"
            else:
                risk_level = "Minor"
        else:
            # 沒有找到交互作用
            summary = "在提供的 FDA 資料中未發現顯著的藥物交互作用。但這不代表完全沒有風險，請諮詢專業醫療人員。"
            risk_level = "Low"

    elapsed_ms = int((time.time() - start_time) * 1000)

    # 5. 寫入 Audit Log
    try:
        audit_log = AuditLog(
            id=f"ver_{int(time.time()*1000)}",
            user_id=user_id,
            action="verify",
            query_content=f"Checked: {request.drugs}",
            ip_address="0.0.0.0"
        )
        db.add(audit_log)
    except Exception as e:
        print(f"Audit Log Error: {e}")

    # 6. 寫入 ChatHistory
    try:
        history = ChatHistory(
            user_id=user_id,
            session_type="verify",
            question=f"Drugs: {', '.join(request.drugs)}",
            answer=summary
        )
        db.add(history)
        db.commit()
    except Exception as e:
        print(f"History Save Error: {e}")
        db.rollback()

    # 7. 返回結果
    return VerifyResponse(
        drugs_analyzed=request.drugs,
        interactions=interactions,
        summary=summary,
        risk_level=risk_level,
        query_time_ms=elapsed_ms
    )


# ============================================================
# 功能 4：數據飛輪 - 使用者回饋 (Feedback)
# ============================================================

class FeedbackCreate(BaseModel):
    query: str
    response: str
    rating: int
    feedback_text: Optional[str] = None
    category: str

@app.post("/api/feedback")
async def create_feedback(
    feedback: FeedbackCreate,
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard),
    db: Session = Depends(get_db)
):
    user_id = creds.decoded["sub"]
    try:
        sanitized_text = PHIDetector.sanitize_for_log(feedback.feedback_text) if feedback.feedback_text else None
        
        db_feedback = UserFeedback(
            id=f"fb_{int(time.time()*1000)}",
            user_id=user_id,
            query=feedback.query,
            response=feedback.response,
            rating=feedback.rating,
            feedback_text=sanitized_text,
            category=feedback.category
        )
        
        db.add(db_feedback)
        db.commit()
        return {"status": "success", "message": "Feedback recorded"}
        
    except Exception as e:
        print(f"Feedback Error: {e}")
        return {"status": "error", "message": str(e)}


# ============================================================
# 功能 5：查詢歷史紀錄 (History)
# ============================================================

@app.get("/api/history")
async def get_user_history(
    creds: HTTPAuthorizationCredentials = Depends(clerk_guard),
    db: Session = Depends(get_db)
):
    """
    取得使用者的查詢歷史 (Research & Verify)
    """
    user_id = creds.decoded["sub"]
    
    # 查詢 ChatHistory 表，最近 50 筆
    history = db.query(ChatHistory)\
        .filter(ChatHistory.user_id == user_id)\
        .order_by(desc(ChatHistory.created_at))\
        .limit(50)\
        .all()
        
    return history


# ============================================================
# 健康檢查與狀態
# ============================================================

@app.get("/health")
def health_check():
    return {"status": "healthy", "version": "2.1.0"}

@app.get("/api/status")
async def api_status(creds: HTTPAuthorizationCredentials = Depends(clerk_guard)):
    try:
        from api.database.vector_store import get_vector_store
        vs = get_vector_store()
        vector_store_status = vs.get_stats()
    except Exception as e:
        vector_store_status = {"error": str(e)}
    
    return {
        "status": "healthy",
        "version": "2.1.0",
        "features": {
            "consultation": True,
            "research": True,
            "pubmed": True,
            "fda": True,
            "verify": True,
            "feedback": True,
            "history": True
        },
        "vector_store": vector_store_status
    }

# 靜態檔案服務
static_path = Path("static")
if static_path.exists():
    @app.get("/")
    async def serve_root():
        return FileResponse(static_path / "index.html")
    app.mount("/", StaticFiles(directory="static", html=True), name="static")