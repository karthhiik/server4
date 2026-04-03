# Phase 0.5 Implementation Status - Backend NER Layer

**Date**: 2026-04-03
**Status**: ✅ COMPLETE (Business Plan module only)

## What's Been Completed

### 1. NER Extraction Layer (100%)
- ✅ **prompt_parser.py** (320 lines)
  - Business plan prompt parsing (extract company, industry, stage, founded_year, etc.)
  - SWOT prompt parsing (business name, industry, description, competitors, etc.)
  - GTM prompt parsing (business info, target customer, demographics, budget, timeline, etc.)
  - Pitch prompt parsing (company, tagline, vision, problem, solution, ask amount, etc.)
  - Regex patterns for: funding stages, years, percentages, dollar amounts, industry keywords
  - spaCy NER integration (with fallback to regex-only mode)
  - Confidence scoring per extracted field (0-1 scale)

- ✅ **field_extractor.py** (180 lines)
  - Smart merging of prompt-extracted fields + user form data
  - Priority chain: form_data > extracted_values > defaults
  - Metadata tracking: source info, extraction quality, confidence scores
  - Methods for all 4 services: extract_business_plan_fields, extract_swot_fields, extract_gtm_fields, extract_pitch_fields

### 2. Business Plan Service Updated (100%)
- ✅ **server1_fastapi/app/services/business_plan_service.py**
  - Added FieldExtractor import
  - Updated generate_plan_fast() signature: accepts prompt (optional) + form_input (optional)
  - Updated generate_plan_deep() signature: accepts prompt (optional) + form_input (optional)
  - Both methods now call field_extractor.extract_business_plan_fields() first
  - Merged fields become single source of truth for generation

### 3. Business Plan Routes Updated (100%)
- ✅ **server1_fastapi/app/api/routes/business_plan_routes.py**
  - Updated GeneratePlanRequest: form_input (optional) + prompt (optional)
  - Updated GeneratePlanAsyncRequest: form_input (optional) + prompt (optional)
  - Updated /generate-business-plan endpoint: passes both parameters to service
  - Updated /generate-business-plan-async endpoint: stores request in cache for WebSocket

### 4. Dependencies Added (100%)
- ✅ **requirements.txt**: Added spacy==3.7.2
  - Install with: `pip install -r requirements.txt`
  - Download model: `python -m spacy download en_core_web_sm`

### 5. Test Scripts Created (100%)
- ✅ **test_phase1_business_plan.py**
  - Test Scenario 1: Prompt-only input (NER extraction)
  - Test Scenario 2: Form-only input (baseline)
  - Test Scenario 3: Dual input (form priority)
  - Usage: `python test_phase1_business_plan.py`

## What Still Needs to Do

### Phase 0.5 Extended: Update SWOT, GTM, Pitch Services
**Remaining**: 3 services (same pattern as Business Plan)

- [ ] **SWOT Service** (~30 minutes)
  - Update swot_service.py: add prompt parameter, call field_extractor
  - Update swot_routes.py: update request models, pass prompt to service
  - Build test script

- [ ] **GTM Service** (~30 minutes)
  - Update gtm_service.py: add prompt parameter, call field_extractor
  - Update gtm_routes.py: update request models, pass prompt to service
  - Build test script

- [ ] **Pitch Service** (~30 minutes)
  - Update pitch_deck_service.py: add prompt parameter + businessPlanId parameter
  - Update pitch_analysis_routes.py: update request models
  - Build test script for both source types (prompt + from-business-plan)

### Phase 1: Backend Testing (After Phase 0.5 Extended Complete)
**Estimated**: 2-3 hours for all 4 services × 3 scenarios

- [ ] Test all 4 services with prompt-only inputs
- [ ] Test all 4 services with form-only inputs
- [ ] Test all 4 services with dual inputs
- [ ] Verify confidence metadata included
- [ ] Check response time (target: <5s overhead for NER extraction)
- [ ] Generate testing report

### Phase 2: Frontend Integration
**Estimated**: 4-5 hours

- [ ] Fix StrategyPromptInput.tsx (replace fake setTimeout with real API calls)
- [ ] Fix StructuredFormAccordion.tsx (add form generation button)
- [ ] Fix auth token consistency (auth_token → jwt_token)
- [ ] Add error handling (401, 429, timeout)

### Phase 3: Pitch Restoration
**Estimated**: 2-3 hours

- [ ] Create PitchInput.tsx component (2-tab design: prompt + business_plan source)
- [ ] Add "Generate Pitch from This Plan" button to BusinessPlanInput
- [ ] Wire business plan → pitch auto-fill
- [ ] Update suggestion prompts

## Architecture Summary

```
USER INPUT
├─ Prompt-Based: "SaaS platform for real-time BI targeting mid-market..."
│  ├─ PromptParser.parse_*_prompt() → extracts fields via NER + regex
│  └─ FieldExtractor.extract_*_fields() → confidence-scored fields
│
├─ Form-Based: {company_name: "TechVenture", industry: "SaaS BI", ...}
│  └─ FieldExtractor.extract_*_fields() → passes through, confidence=1.0
│
└─ Dual Input: Both prompt + form
   └─ FieldExtractor.extract_*_fields() → merges (form takes priority)

MERGED FIELDS (Single Source of Truth)
└─ Service.generate_plan() → AI generation with consistent data

RESPONSE
└─ Plan + extraction metadata (_source, _confidence, extraction_quality)
```

## Installation Checklist

```bash
# 1. Install spacy in FastAPI environment
cd Server1_FastApi
pip install spacy==3.7.2

# 2. Download spacy English model
python -m spacy download en_core_web_sm

# 3. Restart FastAPI server
python run.py

# 4. Test Business Plan dual-input
python test_phase1_business_plan.py
```

## Key Design Decisions

1. **NER Integration**: spaCy with fallback to regex (handles offline scenarios)
2. **Field Extraction**: Separated from service layer (DRY, testable, reusable)
3. **Merge Priority**: form_data > extracted > defaults (respects user authority)
4. **Confidence Scoring**: Metadata helps frontend show extraction quality
5. **Backward Compatibility**: Services still accept form_input only (existing clients unaffected)

## Next Steps (Recommended)

1. **Immediately**:
   - Install spacy dependencies
   - Run test_phase1_business_plan.py to validate Business Plan implementation
   - Review TestResult output for any failures

2. **Then**:
   - Apply same pattern to SWOT, GTM, Pitch services (3 × 30 min = 1.5 hours)
   - Run test scripts for each service
   - Move to Phase 1 backend testing across all 4 services

3. **Finally**:
   - Phase 2: Frontend integration (fix generate buttons)
   - Phase 3: Pitch restoration

---

**Status**: Phase 0.5 ready for testing. Awaiting backend service expansion to SWOT/GTM/Pitch before Phase 1 testing can complete.
