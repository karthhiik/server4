"""
Design Module - Phase 2 + Phase 5 (Design Intelligence & Brand DNA) + Phase 13 (Repo Integrations).
"""

from app.services.slides_new.design.system import DesignSystem, generate_design_system

# Phase 5 — Brand DNA Extraction
from app.services.slides_new.design.brand_dna import (
    BrandDNA,
    BrandDNAExtractor,
    BrandMood,
    VisualStyle,
    VLMBrandAnalysisPrompt,
)

# Phase 5 — Anti-AI-Slop Processing
from app.services.slides_new.design.anti_slop import (
    AntiAISlopProcessor,
    SlopReport,
    SlopViolation,
    SlopSeverity,
)

# Phase 5 — Visual Style Discovery
from app.services.slides_new.design.style_discovery import (
    AITemplateSelector,
    LayoutDecision,
    StyleDiscoveryResult,
    StyleIntelligenceEngine,
    StylePreview,
)

# Phase 5 — PreTeXt Text Measurement
from app.services.slides_new.design.pretext_engine import (
    LayoutFitResult,
    PreTeXtEngine,
    TextMeasurement,
    check_slide_fit,
    measure_body,
    measure_heading,
)

# Phase 5 — Design Intelligence Orchestrator
from app.services.slides_new.design.design_intelligence import (
    DesignIntelligenceEngine,
    DesignQuality,
    PresentationDesignResult,
    SlideDesignSpec,
)

# Phase 13 — Style Transfer Intelligence (adapted from ArcadeAI/agent-style-transfer + stitch-kit)
from app.services.slides_new.design.style_transfer import (
    InferredStyle,
    SpecificityScore,
    StructuredDesignPrompt,
    StyleEvaluation,
    StyleEvaluationDimension,
    Tone,
    SentenceStructure,
    VocabularyLevel,
    build_design_prompt,
    infer_style,
    score_specificity,
)

# Phase 13 — Icon Reference Registry (adapted from microsoft/fluentui-system-icons)
from app.services.slides_new.design.icon_registry import (
    IconRef,
    IconVariant,
    IconSize,
    get_icons_for_slide,
    get_icons_for_content,
    get_icons_for_industry,
    suggest_icon_variant,
    get_all_icon_names,
    SLIDE_TYPE_ICONS,
    CONTENT_ELEMENT_ICONS,
    INDUSTRY_ICONS,
)

# Phase 13 — Design Resource Knowledge Base (from bradtraversy + Awesome-Design-Tools)
from app.services.slides_new.design.resource_kb import (
    DesignResource,
    get_resources_by_category,
    get_resources_with_api,
    get_resources_by_tag,
    get_resource_categories,
    get_design_toolkit_summary,
    ALL_RESOURCES,
)

__all__ = [
    # Phase 2
    "DesignSystem",
    "generate_design_system",
    # Phase 5 — Brand DNA
    "BrandDNA",
    "BrandDNAExtractor",
    "BrandMood",
    "VisualStyle",
    "VLMBrandAnalysisPrompt",
    # Phase 5 — Anti-Slop
    "AntiAISlopProcessor",
    "SlopReport",
    "SlopViolation",
    "SlopSeverity",
    # Phase 5 — Style Discovery
    "AITemplateSelector",
    "LayoutDecision",
    "StyleDiscoveryResult",
    "StyleIntelligenceEngine",
    "StylePreview",
    # Phase 5 — PreTeXt
    "LayoutFitResult",
    "PreTeXtEngine",
    "TextMeasurement",
    "check_slide_fit",
    "measure_body",
    "measure_heading",
    # Phase 5 — Design Intelligence
    "DesignIntelligenceEngine",
    "DesignQuality",
    "PresentationDesignResult",
    "SlideDesignSpec",
    # Phase 13 — Style Transfer Intelligence
    "InferredStyle",
    "SpecificityScore",
    "StructuredDesignPrompt",
    "StyleEvaluation",
    "StyleEvaluationDimension",
    "Tone",
    "SentenceStructure",
    "VocabularyLevel",
    "build_design_prompt",
    "infer_style",
    "score_specificity",
    # Phase 13 — Icon Registry
    "IconRef",
    "IconVariant",
    "IconSize",
    "get_icons_for_slide",
    "get_icons_for_content",
    "get_icons_for_industry",
    "suggest_icon_variant",
    "get_all_icon_names",
    "SLIDE_TYPE_ICONS",
    "CONTENT_ELEMENT_ICONS",
    "INDUSTRY_ICONS",
    # Phase 13 — Resource Knowledge Base
    "DesignResource",
    "get_resources_by_category",
    "get_resources_with_api",
    "get_resources_by_tag",
    "get_resource_categories",
    "get_design_toolkit_summary",
    "ALL_RESOURCES",
]
