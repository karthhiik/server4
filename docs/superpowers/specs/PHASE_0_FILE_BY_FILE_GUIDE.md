# Phase 0 - Detailed File-by-File Implementation Guide

**Quick Reference**: What to build, where to build it, and how it connects

---

## ✅ COMPLETED (62% - No changes needed)

### Frontend Shared Components

```typescript
// ✅ DONE: lliveupdatedstreaming/src/features/intelligence/shared/CanvasThemeProvider.tsx
// - React Context provider for theming
// - Export: CanvasThemeProvider, useCanvasTheme()
// - 4 presets: blue (business plan), emerald (GTM), violet (SWOT), amber (pitch)

// ✅ DONE: lliveupdatedstreaming/src/features/intelligence/shared/ConfidenceBadge.tsx
// - Component: <ConfidenceBadge level={6} size="md" count={42} onClick={() => showEvidence()} />
// - 6 levels: verified, corroborated, inference, weak_signal, unverifiable, speculative
// - 3 sizes: sm (icon+tooltip), md (icon+label), lg (icon+label+count)
// - Framer Motion pulse animation on render

// ✅ DONE: lliveupdatedstreaming/src/features/intelligence/shared/MetricCard.tsx
// - Component: <MetricCard variant="number" value={2.3} label="Market Growth" trend="up" delta="+0.5%" />
// - 4 variants: number (large), gauge (radial), sparkline (tiny chart), progress (bar)
// - Recharts integration
// - Inherits accent from CanvasThemeProvider

// ✅ DONE: lliveupdatedstreaming/src/features/intelligence/shared/EvidenceDrawer.tsx
// - Component: <EvidenceDrawer isOpen={true} onClose={() => {}} highlightCitationId="cite-123" />
// - Slide-in panel: 480px wide, right side, dark scrim
// - Tabs: Sources (grouped by confidence), Visuals (images with lightbox)
// - Search bar to filter within evidence
// - Citation-aware scrolling

// ✅ DONE: lliveupdatedstreaming/src/features/intelligence/shared/SectionEditor.tsx
// - Component: <SectionEditor mode="read|edit" content="..." onSave={save} />
// - Read mode: Renders markdown with inline citations
// - Edit mode: React Quill rich text editor
// - "/" Commands: /rewrite, /expand, /add-data, /make-punchier, /simplify, /add-chart, /cite-source
// - AI Sparkle button on paragraph hover
// - Auto-save debounced 5s
// - ConfidenceBadge in header
// - Version history dot link

// ✅ DONE: lliveupdatedstreaming/src/features/intelligence/shared/VersionHistoryDrawer.tsx
// - Component: <VersionHistoryDrawer taskId="..." onRestore={(version) => {}} />
// - Timeline list: timestamp, author icon, change type badge
// - Click version: preview content
// - "Compare" button: diff view (red/green highlighting)
// - "Restore" button: revert to version

// ✅ DONE: lliveupdatedstreaming/src/features/intelligence/shared/ExportToolbar.tsx
// - Component: <ExportToolbar contentRef={ref} canvasAccent="blue" />
// - Floating pill, bottom-right, hovers to expand radially
// - Format buttons: PDF (jsPDF + html2canvas), DOCX (docx), Markdown, PNG, TOON
// - WebGL capture before html2canvas
// - Loading spinner + success toast per format

// ✅ DONE: lliveupdatedstreaming/src/features/intelligence/types/canvas.ts
// - Export: CanvasThemeConfig, CanvasTheme, CitationReference, VisualizationSpec...

// ✅ DONE: lliveupdatedstreaming/src/features/intelligence/types/evidence.ts
// - Export: EvidenceItem, ConfidenceLevel, EvidenceSource...

// ✅ DONE: lliveupdatedstreaming/src/features/intelligence/types/metrics.ts
// - Export: MetricItem, MetricVariant, TrendDirection...

// ✅ DONE: lliveupdatedstreaming/src/features/intelligence/types/enrichment.ts
// - Export: WebEnrichment, DetectedEntity, CompetitorSnapshot...

// ✅ DONE: lliveupdatedstreaming/src/features/intelligence/types/index.ts
// - Re-export all from other type files
```

---

## ❌ TODO: STEP 0.8 - ReactFlowWrapper (~500 lines)

**Estimated time**: 2-3 hours (React + ReactFlow + Animations)
**Dependencies**: @xyflow/react, framer-motion, lucide-react
**Blocks**: None (foundation)
**Unblocks**: Strategy Map, Launch Map, TOWS Actions views

### File 1: `lliveupdatedstreaming/src/features/intelligence/shared/ReactFlowWrapper.tsx` (~120 lines)

```typescript
// Pre-configured ReactFlow component
export interface ReactFlowWrapperProps {
  nodes: Node[];
  edges: Edge[];
  nodeTypes?: Record<string, NodeTypes>;
  onNodeClick?: (event: React.MouseEvent, node: Node) => void;
  onConnect?: (connection: Connection) => void;
  onNodesChange?: (changes: NodeChange[]) => void;
  onEdgesChange?: (changes: EdgeChange[]) => void;
  autoLayout?: 'top-to-bottom' | 'left-to-right';
  minZoom?: number;
  maxZoom?: number;
}

export const ReactFlowWrapper: React.FC<ReactFlowWrapperProps> = ({
  nodes, edges, nodeTypes = {}, ...props
}) => {
  // Features to implement:
  // - Dark background with dot grid (20px spacing)
  // - MiniMap (bottom-left) with dark theme
  // - Controls (top-left) with dark theme
  // - Animated edges (animated: true, stroke: accent color)
  // - Snap-to-grid 15px
  // - Multi-select (Shift+click)
  // - Register 4 default node types: StrategyNode, MetricNode, EvidenceNode, GroupNode
  // - Optional ELK auto-layout
  // - IntersectionObserver guard for Three.js Canvas children
  return (
    <ReactFlow
      nodes={nodes}
      edges={edges}
      nodeTypes={{ ...DEFAULT_NODE_TYPES, ...nodeTypes }}
      // ... rest of implementation
    >
      <Background variant="dots" gap={20} />
      <Controls />
      <MiniMap />
    </ReactFlow>
  );
};

export const DEFAULT_NODE_TYPES = {
  strategy: StrategyNode,
  metric: MetricNode,
  evidence: EvidenceNode,
  group: GroupNode,
};
```

### File 2: `lliveupdatedstreaming/src/features/intelligence/shared/nodes/StrategyNode.tsx` (~80 lines)

```typescript
// Rounded card node with icon, title, subtitle, badge, status dot
export interface StrategyNodeData {
  icon: React.ReactNode; // lucide icon
  title: string;
  subtitle?: string;
  confidence?: ConfidenceLevel;
  status?: 'active' | 'stale' | 'draft';
  onClick?: (nodeId: string) => void;
  onDoubleClick?: (nodeId: string) => void;
  onContextMenu?: (nodeId: string) => void;
}

export const StrategyNode: React.FC<NodeProps<StrategyNodeData>> = ({ data, id, isSelected }) => {
  // Implement:
  // - Rounded card (border-radius: 12px)
  // - Icon + title + subtitle
  // - ConfidenceBadge in top-right corner
  // - Status dot (stale = pulsing amber border)
  // - Click/double-click/right-click handlers
  // - Highlight when selected
  return (
    <div className="rounded-lg bg-slate-900 border-2 border-slate-700 p-4">
      {/* content */}
    </div>
  );
};
```

### File 3: `lliveupdatedstreaming/src/features/intelligence/shared/nodes/MetricNode.tsx` (~60 lines)

```typescript
// Compact KPI pill
export interface MetricNodeData {
  label: string;
  value: number;
  unit?: string;
  trend?: 'up' | 'down' | 'flat';
}

export const MetricNode: React.FC<NodeProps<MetricNodeData>> = ({ data }) => {
  // Implement: Compact rounded pill with metric display
  return (
    <div className="rounded-full bg-slate-800 px-4 py-2 text-xs">
      {/* value + label */}
    </div>
  );
};
```

### File 4: `lliveupdatedstreaming/src/features/intelligence/shared/nodes/EvidenceNode.tsx` (~60 lines)

```typescript
// Citation chip with click to open EvidenceDrawer
export interface EvidenceNodeData {
  citationId: string;
  source: string;
  snippet?: string;
}

export const EvidenceNode: React.FC<NodeProps<EvidenceNodeData>> = ({ data }) => {
  const handleClick = () => {
    // Trigger EvidenceDrawer with this citationId
  };

  return (
    <div className="bg-blue-900 rounded-md px-3 py-1 text-xs text-blue-100 cursor-pointer hover:bg-blue-800">
      {/* citation chip */}
    </div>
  );
};
```

### File 5: `lliveupdatedstreaming/src/features/intelligence/shared/nodes/GroupNode.tsx` (~80 lines)

```typescript
// Container node with label header
export interface GroupNodeData {
  label: string;
}

export const GroupNode: React.FC<NodeProps<GroupNodeData>> = ({ children, data }) => {
  // Implement: Container with header, dashed border, child nodes inside
  return (
    <div className="border-2 border-dashed border-slate-600 rounded-lg p-4">
      <div className="text-sm font-semibold mb-3">{data.label}</div>
      {children}
    </div>
  );
};
```

---

## ❌ TODO: STEP 0.9 - WebSearchContext + Entity Chips (~350 lines)

**Estimated time**: 2 hours (after Step 0.11 endpoints are live)
**Dependencies**: Step 0.11 backend endpoints, framer-motion, lucide-react
**Blocks**: Step 0.10 (DualModeInput shell)
**Unblocks**: None directly

### File 1: `lliveupdatedstreaming/src/features/intelligence/shared/WebSearchContext.tsx` (~130 lines)

```typescript
// Manages entity detection and enrichment state
export interface WebSearchContextType {
  entities: DetectedEntity[];
  enrichments: Map<string, WebEnrichment>;
  loadingEntities: Set<string>;
  detectEntities: (text: string) => Promise<DetectedEntity[]>;
  enrichEntity: (entityName: string) => Promise<WebEnrichment>;
  analyzeCompetitor: (company: string) => Promise<CompetitorSnapshot>;
}

export const WebSearchContext = React.createContext<WebSearchContextType | null>(null);

export const WebSearchProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [entities, setEntities] = useState<DetectedEntity[]>([]);
  const [enrichments, setEnrichments] = useState<Map<string, WebEnrichment>>(new Map());
  const [loadingEntities, setLoadingEntities] = useState<Set<string>>(new Set());

  // Implement:
  // - detectEntities(text): debounced 500ms, calls POST /api/intelligence/detect-entities
  // - enrichEntity(name): calls POST /api/intelligence/web-enrich, caches result
  // - analyzeCompetitor(name): calls POST /api/intelligence/competitor-snapshot

  return (
    <WebSearchContext.Provider value={{ entities, enrichments, loadingEntities, detectEntities, enrichEntity, analyzeCompetitor }}>
      {children}
    </WebSearchContext.Provider>
  );
};

export const useWebSearch = () => {
  const ctx = useContext(WebSearchContext);
  if (!ctx) throw new Error('useWebSearch must be inside WebSearchProvider');
  return ctx;
};
```

### File 2: `lliveupdatedstreaming/src/features/intelligence/shared/EntityChip.tsx` (~100 lines)

```typescript
// Animated chip: detected → searching → enriched states
export interface EntityChipProps {
  entity: DetectedEntity;
  onSearch: () => void;
  onAnalyzeCompetitor: () => void;
}

export const EntityChip: React.FC<EntityChipProps> = ({ entity, onSearch, onAnalyzeCompetitor }) => {
  const { enrichments, loadingEntities } = useWebSearch();
  const isLoading = loadingEntities.has(entity.name);
  const isEnriched = !!enrichments.get(entity.name);

  // Implement:
  // - State: detected (gray) → searching (amber spinner) → enriched (blue)
  // - Framer Motion: scale/fade animation between states
  // - Action buttons: "Search" and "Analyze Competitor"
  // - Hover shows snippet/preview

  return (
    <motion.div
      initial={{ scale: 0.8, opacity: 0 }}
      animate={{ scale: 1, opacity: 1 }}
      className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-medium cursor-pointer
        ${isLoading ? 'bg-amber-900 text-amber-200' : isEnriched ? 'bg-blue-900 text-blue-200' : 'bg-slate-700 text-slate-200'}`}
    >
      {isLoading && <Spinner className="w-3 h-3" />}
      {entity.name}
      {/* Actions menu on click/hover */}
    </motion.div>
  );
};
```

### File 3: `lliveupdatedstreaming/src/features/intelligence/shared/EnrichmentCard.tsx` (~120 lines)

```typescript
// Expandable card: company data, funding, competitors, news
export interface EnrichmentCardProps {
  entity: string;
  enrichment: WebEnrichment;
  onUseToggle: (entity: string, use: boolean) => void;
}

export const EnrichmentCard: React.FC<EnrichmentCardProps> = ({ entity, enrichment, onUseToggle }) => {
  const [isExpanded, setIsExpanded] = useState(false);

  // Implement:
  // - Header: company name + logo (if available)
  // - Collapsed: funding, employee count, industry
  // - Expanded: full details (using Framer Motion layoutId for smooth expand)
  //   - Funding rounds
  //   - Top competitors
  //   - Recent news (last 3)
  //   - Market position
  // - "Use" toggle: adds to context

  return (
    <motion.div
      layout
      className="bg-slate-900 border border-slate-700 rounded-lg p-4 cursor-pointer"
      onClick={() => setIsExpanded(!isExpanded)}
    >
      <div className="flex items-center justify-between">
        <h4 className="font-semibold">{entity}</h4>
        <input
          type="checkbox"
          defaultChecked={enrichment.used}
          onChange={(e) => onUseToggle(entity, e.target.checked)}
          className="cursor-pointer"
        />
      </div>
      {isExpanded && (
        <motion.div layout className="mt-3 space-y-2">
          {/* Expanded content */}
        </motion.div>
      )}
    </motion.div>
  );
};
```

---

## ❌ TODO: STEP 0.11 - Backend Enrichment Endpoints (~600 lines)

**Estimated time**: 3-4 hours (FastAPI, SerpAPI, Redis)
**Dependencies**: Existing SerpAPI integration, Azure OpenAI, cache_service
**Blocks**: Step 0.9 (EntityChip UI)
**Unblocks**: None directly

### File 1: `Server1_FastApi/app/api/routes/intelligence_enrichment_routes.py` (~200 lines)

```python
from fastapi import APIRouter, Body, Depends, HTTPException
from app.api.deps import get_current_user, token_required
from app.services.intelligence.entity_detector import detect_entities
from app.services.intelligence.web_enricher import enrich_entity
from app.services.intelligence.competitor_analyzer import analyze_competitor
from app.core.ratelimit import rate_limit

router = APIRouter(prefix="/intelligence", tags=["intelligence"])

@router.post("/detect-entities")
@token_required
@rate_limit(max_calls=10, period=60)  # 10 per minute per user
async def detect_entities_endpoint(
    request: { "text": str },
    current_user = Depends(get_current_user)
) -> {"entities": list}:
    """
    Detect named entities in text using NER model.
    Cached 5 minutes by text hash.
    """
    entities = await detect_entities(request["text"], user_id=current_user.id)
    return {"entities": entities}

@router.post("/web-enrich")
@token_required
@rate_limit(max_calls=5, period=60)  # 5 per minute per user
async def enrich_entity_endpoint(
    request: { "entity_name": str },
    current_user = Depends(get_current_user)
) -> {"funding": dict, "competitors": list, "news": list, "market_position": dict}:
    """
    Enrich entity with web search data from SerpAPI.
    Cached 30 minutes.
    """
    enrichment = await enrich_entity(request["entity_name"], user_id=current_user.id)
    return enrichment

@router.post("/extract-form-fields")
@token_required
@rate_limit(max_calls=10, period=60)
async def extract_form_fields_endpoint(
    request: { "prompt": str, "schema": dict },
    current_user = Depends(get_current_user)
) -> {"fields": dict, "extraction_confidence": float}:
    """
    Extract structured fields from text matching JSON schema.
    Uses utility-tier model.
    """
    result = await extract_form_fields(request["prompt"], request["schema"], user_id=current_user.id)
    return result

@router.post("/competitor-snapshot")
@token_required
@rate_limit(max_calls=5, period=60)
async def competitor_snapshot_endpoint(
    request: { "company_name": str, "industry": str },
    current_user = Depends(get_current_user)
) -> CompetitorSnapshot:
    """
    Deep competitor analysis using research-tier model.
    Includes web enrichment and market research.
    """
    snapshot = await analyze_competitor(
        request["company_name"],
        request["industry"],
        user_id=current_user.id
    )
    return snapshot
```

### File 2: `Server1_FastApi/app/services/intelligence/entity_detector.py` (~120 lines)

```python
from app.core.ai import ai_factory
from app.core.cache import cache_service
import hashlib

async def detect_entities(text: str, user_id: str) -> list[dict]:
    """
    Detect named entities in text.
    Cache key: hash of text
    TTL: 5 minutes
    Model: utility-tier (fast, cheaper)
    """
    cache_key = f"entity_detect:{hashlib.md5(text.encode()).hexdigest()}"

    # Check cache
    cached = await cache_service.get(cache_key)
    if cached:
        return cached

    # Call LLM
    llm = ai_factory.get_model("utility-tier")
    response = await llm.create_message(
        system_prompt="You are an NER (Named Entity Recognition) expert. Extract all entities from the text.",
        user_message=f"Extract entities: {text}",
        json_mode=True,
    )

    entities = response.parsed.get("entities", [])

    # Cache for 5 minutes
    await cache_service.set(cache_key, entities, ttl=300)
    return entities
```

### File 3: `Server1_FastApi/app/services/intelligence/web_enricher.py` (~200 lines)

```python
from serpapi import google_search
from app.core.cache import cache_service
import hashlib

async def enrich_entity(entity_name: str, user_id: str) -> dict:
    """
    Enrich entity with web search data.
    Cache key: entity_name
    TTL: 30 minutes
    """
    cache_key = f"web_enrich:{entity_name.lower()}"

    # Check cache
    cached = await cache_service.get(cache_key)
    if cached:
        return cached

    # SerpAPI search
    params = {
        "q": f"{entity_name} company funding investors",
        "api_key": settings.SERPAPI_KEY,
    }
    results = google_search(params)

    enrichment = {
        "company_name": entity_name,
        "funding": extract_funding_data(results),
        "competitors": extract_competitors(results),
        "news": extract_news(results[:3]),
        "market_position": extract_market_position(results),
    }

    # Cache for 30 minutes
    await cache_service.set(cache_key, enrichment, ttl=1800)
    return enrichment

def extract_funding_data(results) -> dict:
    # Parse SerpAPI results for funding info
    pass

def extract_competitors(results) -> list:
    # Parse SerpAPI results for competitors
    pass

def extract_news(results) -> list:
    # Parse SerpAPI results for news
    pass

def extract_market_position(results) -> dict:
    # Parse SerpAPI results for market info
    pass
```

### File 4: `Server1_FastApi/app/services/intelligence/competitor_analyzer.py` (~80 lines)

```python
from app.core.ai import ai_factory

async def analyze_competitor(company_name: str, industry: str, user_id: str) -> dict:
    """
    Deep competitor analysis using research-tier model.
    Includes:
    - Company overview
    - Products/services
    - Market position
    - Strengths/weaknesses
    - Opportunities/threats

    No caching (always fresh research)
    """

    # Enrich with web data first
    web_enrich = await enrich_entity(company_name, user_id)

    # Prompt research-tier model
    llm = ai_factory.get_model("research-tier")

    prompt = f"""
    Analyze {company_name} in the {industry} industry.

    Web research available:
    {json.dumps(web_enrich, indent=2)}

    Provide:
    1. Company overview
    2. Product/service analysis
    3. Market position vs competitors
    4. Key strengths
    5. Key weaknesses
    6. Market opportunities
    7. Threats

    Return as JSON.
    """

    response = await llm.create_message(
        system_prompt="You are a competitive intelligence analyst.",
        user_message=prompt,
        json_mode=True,
    )

    return response.parsed
```

---

## ❌ TODO: STEP 0.12 - Prompt Enhancement Middleware (~500 lines)

**Estimated time**: 2-3 hours (Pydantic, validation logic)
**Dependencies**: None
**Blocks**: None directly
**Unblocks**: Phase 1-4 services (for quality gates)

### File 1: `Server1_FastApi/app/services/intelligence/prompt_enhancer.py` (~250 lines)

```python
from pydantic import BaseModel
import json

class PromptEnhancementContext(BaseModel):
    artifact_type: str  # business_plan, gtm, swot, pitch
    mode: str  # fast or deep
    user_input: str
    enrichment_context: dict = {}
    market_data: dict = {}

class EnhancedPrompt(BaseModel):
    system_prompt: str
    user_prompt: str
    output_schema: dict

class PromptEnhancer:
    """
    Enhances raw user prompts into structured, high-quality AI prompts.
    """

    NO_FLUFF_MANDATE = """
    You MUST be concise and fact-based. Avoid:
    - Flowery language ("innovative", "cutting-edge", "revolutionary")
    - Platitudes ("in today's digital world")
    - Obvious statements
    - Filler sentences

    If you can say it in 5 words, don't use 10.
    """

    DEPTH_INSTRUCTIONS = {
        "fast": "Provide essential information only. 2-3 key points per section.",
        "deep": "Provide comprehensive analysis. 5-7 detailed points per section with evidence.",
    }

    async def enhance(self, context: PromptEnhancementContext) -> EnhancedPrompt:
        """
        Transform raw prompt → enhanced system + user prompts with schema.
        """

        # Build system prompt
        system_prompt = self._build_system_prompt(context)

        # Build user prompt with enrichment context
        user_prompt = self._build_user_prompt(context)

        # Get output schema for artifact type
        output_schema = self._get_output_schema(context.artifact_type)

        return EnhancedPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            output_schema=output_schema,
        )

    def _build_system_prompt(self, context: PromptEnhancementContext) -> str:
        artifact_system = self._get_artifact_system_prompt(context.artifact_type)
        depth_instr = self.DEPTH_INSTRUCTIONS.get(context.mode, self.DEPTH_INSTRUCTIONS["fast"])

        return f"""
        {artifact_system}

        {self.NO_FLUFF_MANDATE}

        {depth_instr}

        Output MUST be valid JSON matching this schema:
        {json.dumps(self._get_output_schema(context.artifact_type), indent=2)}
        """

    def _build_user_prompt(self, context: PromptEnhancementContext) -> str:
        prompt = f"User request: {context.user_input}\n"

        if context.enrichment_context:
            prompt += f"\nEnrichment context:\n{json.dumps(context.enrichment_context, indent=2)}\n"

        if context.market_data:
            prompt += f"\nMarket data:\n{json.dumps(context.market_data, indent=2)}\n"

        return prompt

    def _get_artifact_system_prompt(self, artifact_type: str) -> str:
        prompts = {
            "business_plan": "You are a business plan analyst. Generate a comprehensive business plan...",
            "gtm": "You are a go-to-market strategist. Generate a detailed GTM strategy...",
            "swot": "You are a strategic analyst. Generate a SWOT analysis...",
            "pitch": "You are a pitch deck analyst. Analyze this pitch deck...",
        }
        return prompts.get(artifact_type, "")

    def _get_output_schema(self, artifact_type: str) -> dict:
        # Return to OutputValidator to see usage
        pass
```

### File 2: `Server1_FastApi/app/services/intelligence/output_validator.py` (~250 lines)

```python
from pydantic import BaseModel, ValidationError
from typing import Any

class ValidationResult(BaseModel):
    is_valid: bool
    errors: list[str] = []
    warnings: list[str] = []
    metrics: dict[str, Any] = {}

class OutputValidator:
    """
    Validates AI-generated outputs against quality gates.
    """

    SCHEMAS = {
        "business_plan_section": {
            "required": ["title", "content", "key_metrics", "confidence", "citations"],
            "min_content_length": 100,
            "required_citations": True,
        },
        "swot_item": {
            "required": ["quadrant", "statement", "impact", "evidence_count"],
            "min_content_length": 20,
        },
        "gtm_channel": {
            "required": ["channel_name", "cac", "ltv", "tactics", "timeline"],
            "min_content_length": 50,
        },
        "pitch_claim": {
            "required": ["claim", "evidence", "confidence", "counter_arguments"],
            "min_content_length": 30,
        },
    }

    async def validate(self,
                      output: dict,
                      schema_type: str,
                      artifact_type: str) -> ValidationResult:
        """
        Validate AI output against schema.
        Returns: ValidationResult with errors/warnings
        """

        errors = []
        warnings = []
        metrics = {}

        schema = self.SCHEMAS.get(schema_type, {})

        # 1. Check required fields
        for field in schema.get("required", []):
            if field not in output or output[field] is None:
                errors.append(f"Missing required field: {field}")

        # 2. Check content length
        if "content" in output:
            if len(output["content"]) < schema.get("min_content_length", 0):
                errors.append(f"Content too short (min {schema.get('min_content_length')})")

        # 3. Validate citation format
        if "citations" in output:
            citations = output.get("citations", [])
            if schema.get("required_citations") and len(citations) == 0:
                warnings.append("No citations found")

            for cite in citations:
                if not self._is_valid_citation_format(cite):
                    errors.append(f"Invalid citation format: {cite}")

        # 4. Extract and validate metrics
        if "key_metrics" in output:
            metrics = self._extract_metrics(output["key_metrics"])
            for metric_name, value in metrics.items():
                if not self._is_valid_metric(metric_name, value):
                    warnings.append(f"Unusual metric value: {metric_name}={value}")

        # 5. Confidence scoring
        if "confidence" in output:
            if not (0 <= output["confidence"] <= 1):
                errors.append("Confidence must be 0-1")

        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            metrics=metrics,
        )

    def _is_valid_citation_format(self, citation: dict) -> bool:
        required = ["source_id", "source_url", "snippet"]
        return all(k in citation for k in required)

    def _extract_metrics(self, metrics_data: dict) -> dict:
        # Parse metrics, extract numbers, units, trends
        pass

    def _is_valid_metric(self, name: str, value: Any) -> bool:
        # Sanity check metric values
        pass
```

---

## ❌ TODO: STEP 0.10 - DualModeInput Shell (~600 lines) [CRITICAL]

**Estimated time**: 3-4 hours (React forms, theming, integration)
**Dependencies**: Steps 0.8, 0.9 (all previous components)
**Blocks**: All Phase 1-4 input pages
**Unblocks**: Immediate Phase 1 implementation

### File 1: `lliveupdatedstreaming/src/features/intelligence/shared/DualModeInput.tsx` (~200 lines)

```typescript
// Page layout shell: hero + prompt + form
export interface DualModeInputProps {
  title: string;
  subtitle: string;
  accent: 'blue' | 'emerald' | 'violet' | 'amber';
  onGenerate: (prompt: string, formData: dict) => void;
  formConfig: FormSection[];
  children?: React.ReactNode;
}

export const DualModeInput: React.FC<DualModeInputProps> = ({
  title, subtitle, accent, onGenerate, formConfig, children
}) => {
  return (
    <CanvasThemeProvider accent={accent}>
      <motion.div className="min-h-screen bg-gradient-to-b from-slate-950 to-slate-900">
        {/* Hero Section */}
        <motion.section className="pt-20 pb-12 text-center">
          <h1 className="text-5xl font-bold text-white mb-4">{title}</h1>
          <p className="text-xl text-slate-400">{subtitle}</p>
        </motion.section>

        {/* Prompt Input + Form */}
        <motion.section className="max-w-2xl mx-auto px-4 space-y-8">
          <StrategyPromptInput
            onGenerate={onGenerate}
            formConfig={formConfig}
          />
        </motion.section>

        {children}
      </motion.div>
    </CanvasThemeProvider>
  );
};
```

### File 2: `lliveupdatedstreaming/src/features/intelligence/shared/StrategyPromptInput.tsx` (~250 lines)

```typescript
// Large textarea with entity chips, modes, suggestions, generate button
export interface StrategyPromptInputProps {
  onGenerate: (prompt: string, formData: dict) => void;
  formConfig: FormSection[];
  placeholder?: string;
}

export const StrategyPromptInput: React.FC<StrategyPromptInputProps> = ({
  onGenerate, formConfig, placeholder = "Describe your strategy..."
}) => {
  const [prompt, setPrompt] = useState("");
  const [mode, setMode] = useState<'fast' | 'deep'>('fast');
  const [showForm, setShowForm] = useState(false);
  const [formData, setFormData] = useState({});
  const [isGenerating, setIsGenerating] = useState(false);

  const { entities, detectEntities } = useWebSearch();

  // Debounced entity detection
  useEffect(() => {
    const timer = setTimeout(() => {
      if (prompt.length > 10) detectEntities(prompt);
    }, 500);
    return () => clearTimeout(timer);
  }, [prompt]);

  const handleGenerate = async () => {
    setIsGenerating(true);
    try {
      onGenerate(prompt, formData);
    } finally {
      setIsGenerating(false);
    }
  };

  return (
    <motion.div className="space-y-4">
      {/* Textarea */}
      <textarea
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        placeholder={placeholder}
        className="w-full h-32 bg-slate-900 border border-slate-700 rounded-lg p-4 text-white placeholder-slate-500"
      />

      {/* Entity chips */}
      {entities.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {entities.map(e => <EntityChip key={e.name} entity={e} />)}
        </div>
      )}

      {/* Mode toggle + suggestions + button */}
      <div className="flex gap-4 items-center">
        <div className="flex gap-2">
          <button
            onClick={() => setMode('fast')}
            className={`px-4 py-2 rounded-lg ${mode === 'fast' ? 'bg-blue-600' : 'bg-slate-700'}`}
          >
            ⚡ Fast
          </button>
          <button
            onClick={() => setMode('deep')}
            className={`px-4 py-2 rounded-lg ${mode === 'deep' ? 'bg-blue-600' : 'bg-slate-700'}`}
          >
            🔬 Deep
          </button>
        </div>

        <button
          onClick/{() => setShowForm(!showForm)}
          className="px-4 py-2 rounded-lg bg-slate-700 hover:bg-slate-600"
        >
          {showForm ? 'Hide Form' : 'Show Form'}
        </button>

        <button
          onClick={handleGenerate}
          disabled={!prompt.trim() || isGenerating}
          className="ml-auto px-6 py-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:bg-slate-600 text-white font-semibold"
        >
          {isGenerating ? 'Generating...' : 'Generate'}
        </button>
      </div>

      {/* Structured form (collapsible) */}
      {showForm && (
        <StructuredFormAccordion
          sections={formConfig}
          onChange={setFormData}
        />
      )}
    </motion.div>
  );
};
```

### File 3: `lliveupdatedstreaming/src/features/intelligence/shared/StructuredFormAccordion.tsx` (~150 lines)

```typescript
// Generic accordion: sections as glass cards with completion indicator
export interface FormSection {
  id: string;
  icon: React.ReactNode;
  title: string;
  fields: FormField[];
  showAIAssist?: boolean;
}

export interface FormField {
  name: string;
  type: 'text' | 'textarea' | 'number' | 'select' | 'checkbox';
  label: string;
  placeholder?: string;
  required?: boolean;
  options?: {label: string, value: any}[];
}

export interface StructuredFormAccordionProps {
  sections: FormSection[];
  onChange: (data: dict) => void;
}

export const StructuredFormAccordion: React.FC<StructuredFormAccordionProps> = ({
  sections, onChange
}) => {
  const [formData, setFormData] = useState({});
  const [expandedSection, setExpandedSection] = useState<string | null>(null);

  const handleFieldChange = (sectionId: string, fieldName: string, value: any) => {
    const newData = {
      ...formData,
      [sectionId]: {
        ...formData[sectionId],
        [fieldName]: value,
      },
    };
    setFormData(newData);
    onChange(newData);
  };

  return (
    <motion.div className="space-y-3">
      {sections.map(section => {
        const sectionData = formData[section.id] || {};
        const completionPercent = Object.values(sectionData).filter(Boolean).length / section.fields.length * 100;

        return (
          <motion.div
            key={section.id}
            layout
            className="bg-slate-800 bg-opacity-50 border border-slate-700 border-l-4 border-l-blue-500 rounded-lg overflow-hidden"
          >
            <button
              onClick={() => setExpandedSection(
                expandedSection === section.id ? null : section.id
              )}
              className="w-full p-4 flex items-center justify-between hover:bg-slate-800 hover:bg-opacity-50 transition"
            >
              <div className="flex items-center gap-3">
                <div className="text-xl">{section.icon}</div>
                <div className="text-left">
                  <div className="font-semibold text-white">{section.title}</div>
                  <div className="text-sm text-slate-400">{Math.round(completionPercent)}% complete</div>
                </div>
              </div>
              <ChevronDown className={`transition ${expandedSection === section.id ? 'rotate-180' : ''}`} />
            </button>

            {expandedSection === section.id && (
              <motion.div layout className="p-4 border-t border-slate-700 space-y-4 bg-slate-900 bg-opacity-50">
                {section.fields.map(field => (
                  <FormField
                    key={field.name}
                    field={field}
                    value={sectionData[field.name] || ''}
                    onChange={(value) => handleFieldChange(section.id, field.name, value)}
                  />
                ))}
                {section.showAIAssist && (
                  <button className="w-full mt-4 px-4 py-2 rounded-lg bg-purple-900 text-purple-100 hover:bg-purple-800">
                    ✨ AI Assist
                  </button>
                )}
              </motion.div>
            )}
          </motion.div>
        );
      })}
    </motion.div>
  );
};

const FormField: React.FC<{
  field: FormField,
  value: any,
  onChange: (value: any) => void
}> = ({ field, value, onChange }) => {
  switch (field.type) {
    case 'text':
      return (
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder}
          className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-white"
        />
      );
    case 'textarea':
      return (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={field.placeholder}
          className="w-full bg-slate-900 border border-slate-700 rounded px-3 py-2 text-white h-24"
        />
      );
    // ... other field types
  }
};
```

---

## 🔌 INTEGRATION POINTS

### Phase 0 components feed into Phase 1+:

```
BusinessPlanInput.tsx
  ├── extends DualModeInput (Step 0.10)
  ├── uses CanvasThemeProvider (Step 0.1, blue)
  └── form config → /api/generate-business-plan

BusinessPlanCanvas.tsx
  ├── displays 7 views
  ├── uses ExportToolbar (Step 0.7)
  └── each view uses relevant components:
      - Executive Summary: SectionEditor (0.5)
      - Strategy Map: ReactFlowWrapper (0.8)
      - Metrics: MetricCard (0.3)
      - Sources: EvidenceDrawer (0.4)
      - Edit: SectionEditor (0.5)
      - History: VersionHistoryDrawer (0.6)
```

Same pattern for GTM, SWOT, Pitch canvases.

---

## ✅ FINAL CHECKLIST

When all 5 remaining steps are complete:

- [ ] All imports resolve (no missing dependencies)
- [ ] No TypeScript compilation errors
- [ ] All 13 components render without errors in isolation
- [ ] All 4 theme colors apply correctly across all components
- [ ] ConfidenceBadge levels display correctly
- [ ] MetricCard all 4 variants render
- [ ] EvidenceDrawer opens, searches, filters by confidence
- [ ] SectionEditor "/" commands functional
- [ ] VersionHistoryDrawer shows versions, diffs, restore works
- [ ] ExportToolbar exports to PDF successfully
- [ ] ReactFlowWrapper renders graphs with 30+ nodes smoothly
- [ ] WebSearchContext detects entities in prompts
- [ ] Entity enrichment fetches real company data
- [ ] DualModeInput form generates from config
- [ ] All 4 backend endpoints callable with @token_required
- [ ] Rate limiting blocks excessive requests
- [ ] Prompt enhancer adds "No Fluff" mandate correctly
- [ ] Output validator catches schema violations
- [ ] No circular dependencies in imports
- [ ] All tests pass (unit + integration)
