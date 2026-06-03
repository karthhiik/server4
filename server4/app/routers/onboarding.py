"""
Onboarding Router - Progressive profiling API
Handles step-by-step user input collection for pitch deck generation
"""

from __future__ import annotations

import tempfile
import os
from typing import Optional, Dict, Any
from fastapi import APIRouter, UploadFile, File, HTTPException
from pydantic import BaseModel

from app.models.user_input import (
    UserInputContext,
    Purpose,
    Stage,
    DocumentSource,
    ParsedDocument
)
# from app.services.v4.document_parser import DocumentParser  # Module not found - commented out for server startup
import structlog

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/onboarding", tags=["onboarding"])


# Pydantic models for request/response
class Step1Request(BaseModel):
    company_name: str
    one_liner: str
    website_url: Optional[str] = None


class Step2Request(BaseModel):
    purpose: str  # "fundraising", "partnership", "sales", "hiring"
    target_audience: list[str]  # ["VC / Angel Investors", "Corporate / Strategic Partners"]


class Step3Request(BaseModel):
    funding_amount: Optional[str] = None
    funding_round: Optional[str] = None
    traction_metrics: Optional[str] = None
    stage: Optional[str] = None


class Step4Request(BaseModel):
    style: str  # "minimal", "bold", "corporate"
    mode: str  # "standard", "premium"


class GenerateRequest(BaseModel):
    user_context: Dict[str, Any]


@router.post("/step1-company")
async def submit_company_info(data: Step1Request):
    """Step 1: Company name + one-liner"""
    logger.info(
        "onboarding_step1",
        company_name=data.company_name,
        has_website=bool(data.website_url),
    )
    
    # Validate
    if not data.company_name or len(data.company_name) < 2:
        raise HTTPException(status_code=400, detail="Company name is required")
    
    if not data.one_liner or len(data.one_liner) < 10:
        raise HTTPException(status_code=400, detail="One-liner must be at least 10 characters")
    
    # Store in session (for now, return data)
    # TODO: Implement session storage
    return {
        "step": 1,
        "status": "success",
        "data": data.model_dump(),
        "next": "step2-purpose"
    }


@router.post("/step2-purpose")
async def submit_purpose(data: Step2Request):
    """Step 2: Audience + purpose with smart defaults"""
    logger.info(
        "onboarding_step2",
        purpose=data.purpose,
        audience_count=len(data.target_audience),
    )
    
    # Validate purpose
    valid_purposes = ["fundraising", "partnership", "sales", "hiring"]
    if data.purpose not in valid_purposes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid purpose. Must be one of: {valid_purposes}"
        )
    
    # Apply smart defaults
    if data.purpose == "fundraising" and not data.target_audience:
        data.target_audience = ["VC / Angel Investors"]
    elif data.purpose == "partnership" and not data.target_audience:
        data.target_audience = ["Corporate / Strategic Partners"]
    
    return {
        "step": 2,
        "status": "success",
        "data": data.model_dump(),
        "next": "step3-facts"
    }


@router.post("/upload-document")
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = "pdf"
):
    """Upload and parse document (alternative to manual input)"""
    logger.info(
        "document_upload_start",
        filename=file.filename,
        doc_type=doc_type,
    )
    
    # Validate doc_type
    valid_types = ["pdf", "ppt", "pptx", "url"]
    if doc_type not in valid_types:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid doc_type. Must be one of: {valid_types}"
        )
    
    # Save temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=f".{doc_type}") as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name
    
    try:
        # Parse document - DocumentParser module not found, returning stub response
        # TODO: Re-enable when DocumentParser is available
        # For now, return a stub response to allow server startup
        return {
            "success": True,
            "auto_fill": {},
            "message": "Document parsing temporarily disabled"
        }
        
        # Original parsing logic (unreachable until DocumentParser is available):
        # if doc_type == "url":
        #     url = content.decode('utf-8').strip()
        #     parsed = await parser.parse_url(url)
        # else:
        #     doc_source_map = {
        #         "pdf": DocumentSource.UPLOADED_PDF,
        #         "ppt": DocumentSource.UPLOADED_PPT,
        #         "pptx": DocumentSource.UPLOADED_PPTX,
        #     }
        #     parsed = await parser.parse_file(tmp_path, doc_source_map[doc_type])
        # 
        # logger.info(
        #     "document_parse_success",
        #     confidence=parsed.confidence,
        #     has_company=bool(parsed.company_name),
        #     has_funding=bool(parsed.funding_amount),
        # )
        # 
        # # Auto-fill data
        # auto_fill = {}
        # if parsed.company_name:
        #     auto_fill["company_name"] = parsed.company_name
        # if parsed.one_liner:
        #     auto_fill["one_liner"] = parsed.one_liner
        # if parsed.funding_amount:
        #     auto_fill["funding_amount"] = parsed.funding_amount
        # if parsed.funding_round:
        #     auto_fill["funding_round"] = parsed.funding_round
        # if parsed.traction_metrics:
        #     auto_fill["traction_metrics"] = parsed.traction_metrics
        # if parsed.stage:
        #     auto_fill["stage"] = parsed.stage
        # if parsed.industry:
        #     auto_fill["industry"] = parsed.industry
        # 
        # return {
        #     "status": "success",
        #     "parsed_data": {
        #         "company_name": parsed.company_name,
        #         "one_liner": parsed.one_liner,
        #         "funding_amount": parsed.funding_amount,
        #         "funding_round": parsed.funding_round,
        #         "traction_metrics": parsed.traction_metrics,
        #         "stage": parsed.stage,
        #         "industry": parsed.industry,
        #         "confidence": parsed.confidence,
        #     },
        #     "auto_fill": auto_fill,
        # }
        
    except Exception as e:
        logger.error(
            "document_upload_failed",
            error=str(e)[:200],
        )
        raise HTTPException(status_code=500, detail=f"Document parsing failed: {str(e)}")
    finally:
        # Clean up temp file
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


@router.post("/step3-facts")
async def submit_quick_facts(data: Step3Request):
    """Step 3: Quick facts (optional - progressive profiling)"""
    logger.info(
        "onboarding_step3",
        has_funding=bool(data.funding_amount),
        has_traction=bool(data.traction_metrics),
    )
    
    return {
        "step": 3,
        "status": "success",
        "data": data.model_dump(),
        "next": "step4-style"
    }


@router.post("/step4-style")
async def submit_style(data: Step4Request):
    """Step 4: Deck style + mode"""
    logger.info(
        "onboarding_step4",
        style=data.style,
        mode=data.mode,
    )
    
    # Validate
    valid_styles = ["minimal", "bold", "corporate"]
    if data.style not in valid_styles:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid style. Must be one of: {valid_styles}"
        )
    
    valid_modes = ["standard", "premium"]
    if data.mode not in valid_modes:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode. Must be one of: {valid_modes}"
        )
    
    return {
        "step": 4,
        "status": "success",
        "data": data.model_dump(),
        "next": "generate"
    }


@router.post("/generate")
async def generate_deck(data: GenerateRequest):
    """Final step: Generate deck with authoritative input"""
    logger.info(
        "onboarding_generate",
        company_name=data.user_context.get("company_name"),
        purpose=data.user_context.get("purpose"),
    )
    
    try:
        # Convert dict to UserInputContext
        purpose_map = {
            "fundraising": Purpose.FUNDRAISING,
            "partnership": Purpose.PARTNERSHIP,
            "sales": Purpose.SALES,
            "hiring": Purpose.HIRING,
        }
        
        stage_map = {
            "idea": Stage.IDEA,
            "pre-revenue": Stage.PRE_REVENUE,
            "seed": Stage.SEED,
            "series-a": Stage.SERIES_A,
            "growth": Stage.GROWTH,
        }
        
        user_context = UserInputContext(
            company_name=data.user_context.get("company_name"),
            one_liner=data.user_context.get("one_liner"),
            purpose=purpose_map.get(data.user_context.get("purpose"), Purpose.FUNDRAISING),
            target_audience=data.user_context.get("target_audience", []),
            funding_amount=data.user_context.get("funding_amount"),
            funding_round=data.user_context.get("funding_round"),
            traction_metrics=data.user_context.get("traction_metrics"),
            stage=stage_map.get(data.user_context.get("stage")),
            industry=data.user_context.get("industry"),
            website_url=data.user_context.get("website_url"),
        )
        
        # Convert to structured context for pipeline
        structured = user_context.to_structured_context()
        
        # Add raw UserInputContext for authoritative override in parallel_writer
        structured["_user_input_context"] = {
            "company_name": user_context.company_name,
            "one_liner": user_context.one_liner,
            "purpose": user_context.purpose.value,
            "target_audience": user_context.target_audience,
            "funding_amount": user_context.funding_amount,
            "funding_round": user_context.funding_round,
            "traction_metrics": user_context.traction_metrics,
            "stage": user_context.stage.value if user_context.stage else None,
            "industry": user_context.industry,
        }
        
        # Call existing V4 pipeline
        from app.services.v4.content_pipeline import V4ContentPipeline
        pipeline = V4ContentPipeline()
        
        result = await pipeline.generate(
            project_id=f"onboarding_{user_context.company_name.replace(' ', '_')}",
            user_id="onboarding_user",
            user_query=user_context.one_liner,
            analysis={
                "industry": user_context.industry or "unknown",
                "purpose": user_context.purpose.value,
                "company_name": user_context.company_name,
                "target_audience": user_context.target_audience,
            },
            mode=data.user_context.get("mode", "standard"),
            purpose=user_context.purpose.value,
            structured_context=structured,  # AUTHORITATIVE override with UserInputContext embedded
        )
        
        logger.info(
            "onboarding_generate_success",
            project_id=result.generation_id,
            n_slides=len(result.slides),
            critic_score=result.critic.overall if result.critic else 0,
        )
        
        return {
            "status": "success",
            "generation_id": result.generation_id,
            "slides": len(result.slides),
            "critic_score": result.critic.overall if result.critic else 0,
            "duration_ms": result.duration_ms,
        }
        
    except Exception as e:
        logger.error(
            "onboarding_generate_failed",
            error=str(e)[:200],
        )
        raise HTTPException(status_code=500, detail=f"Generation failed: {str(e)}")
