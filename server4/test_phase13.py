#!/usr/bin/env python3
"""
Phase 13 Tests -- Repository Integration Modules (Style Transfer, Icon Registry, Resource KB).

100 tests covering all Phase 13 modules + integration with DesignerAgent:
    Tests   1-30:  Style Transfer Intelligence (infer_style, score_specificity, build_design_prompt)
    Tests  31-60:  Icon Registry (icon lookups, slide types, content elements, industry)
    Tests  61-85:  Resource Knowledge Base (categories, tags, APIs, toolkit summary)
    Tests  86-100: Integration (DesignerAgent wiring, __init__ exports, cross-module)

Run:
    cd server4
    python test_phase13.py
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


class TestResult:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.errors = []

    def ok(self, name: str):
        self.passed += 1
        print(f"  [PASS] {name}")

    def fail(self, name: str, reason: str):
        self.failed += 1
        self.errors.append((name, reason))
        print(f"  [FAIL] {name}: {reason}")

    def summary(self):
        total = self.passed + self.failed
        print(f"\n{'='*60}")
        print(f"Phase 13 Tests: {self.passed}/{total} passed")
        if self.errors:
            print("\nFailures:")
            for name, reason in self.errors:
                print(f"  - {name}: {reason}")
        print(f"{'='*60}")
        return self.failed == 0


results = TestResult()


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1: Style Transfer Intelligence (Tests 1-30)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 1: Style Transfer Intelligence ===")

# Test 1: Import style_transfer module
try:
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
    results.ok("T1: Import style_transfer module")
except Exception as e:
    results.fail("T1: Import style_transfer module", str(e))

# Test 2: Tone enum values
try:
    expected_tones = {"professional", "casual", "authoritative", "inspirational",
                      "technical", "playful", "urgent", "empathetic"}
    actual = {t.value for t in Tone}
    assert expected_tones == actual, f"Got {actual}"
    results.ok("T2: Tone enum has 8 values")
except Exception as e:
    results.fail("T2: Tone enum has 8 values", str(e))

# Test 3: SentenceStructure enum values
try:
    expected = {"short_punchy", "balanced", "narrative", "data_driven", "bullet_heavy"}
    actual = {s.value for s in SentenceStructure}
    assert expected == actual, f"Got {actual}"
    results.ok("T3: SentenceStructure enum has 5 values")
except Exception as e:
    results.fail("T3: SentenceStructure enum has 5 values", str(e))

# Test 4: VocabularyLevel enum values
try:
    expected = {"simple", "moderate", "technical", "executive"}
    actual = {v.value for v in VocabularyLevel}
    assert expected == actual, f"Got {actual}"
    results.ok("T4: VocabularyLevel enum has 4 values")
except Exception as e:
    results.fail("T4: VocabularyLevel enum has 4 values", str(e))

# Test 5: InferredStyle dataclass fields
try:
    style = InferredStyle(
        tone=Tone.PROFESSIONAL,
        formality_level=0.8,
        sentence_structure=SentenceStructure.BALANCED,
        vocabulary_level=VocabularyLevel.TECHNICAL,
        personality_traits=["precise", "authoritative"],
        writing_patterns={"uses_data": True},
        visual_energy=0.6,
        color_warmth=0.4,
        whitespace_ratio=0.5,
    )
    assert style.tone == Tone.PROFESSIONAL
    assert style.formality_level == 0.8
    assert style.visual_energy == 0.6
    results.ok("T5: InferredStyle dataclass creation")
except Exception as e:
    results.fail("T5: InferredStyle dataclass creation", str(e))

# Test 6: InferredStyle default values
try:
    style = InferredStyle()
    assert style.tone == Tone.PROFESSIONAL
    assert style.formality_level == 0.7
    assert style.vocabulary_level == VocabularyLevel.MODERATE
    assert style.personality_traits == ["confident", "clear"]
    assert style.writing_patterns == {}
    results.ok("T6: InferredStyle defaults")
except Exception as e:
    results.fail("T6: InferredStyle defaults", str(e))

# Test 7: infer_style from professional text
try:
    style = infer_style("Our enterprise SaaS platform leverages cutting-edge AI for institutional investors")
    assert isinstance(style, InferredStyle)
    assert style.tone in (Tone.PROFESSIONAL, Tone.TECHNICAL, Tone.AUTHORITATIVE)
    assert style.formality_level >= 0.5
    results.ok("T7: infer_style professional text")
except Exception as e:
    results.fail("T7: infer_style professional text", str(e))

# Test 8: infer_style from casual text
try:
    style = infer_style("Hey, check out this cool app we built for the community! Fun social platform")
    assert isinstance(style, InferredStyle)
    assert style.tone in (Tone.CASUAL, Tone.PLAYFUL, Tone.EMPATHETIC)
    results.ok("T8: infer_style casual text")
except Exception as e:
    results.fail("T8: infer_style casual text", str(e))

# Test 9: infer_style from technical text
try:
    style = infer_style("The microservice architecture implements gRPC with protobuf serialization and Kubernetes orchestration",
                        audience="developers")
    assert isinstance(style, InferredStyle)
    assert style.vocabulary_level in (VocabularyLevel.TECHNICAL, VocabularyLevel.EXECUTIVE)
    results.ok("T9: infer_style technical text")
except Exception as e:
    results.fail("T9: infer_style technical text", str(e))

# Test 10: infer_style from empty text
try:
    style = infer_style("")
    assert isinstance(style, InferredStyle)
    assert style.tone == Tone.PROFESSIONAL  # default fallback
    results.ok("T10: infer_style empty text returns defaults")
except Exception as e:
    results.fail("T10: infer_style empty text returns defaults", str(e))

# Test 11: SpecificityScore dataclass
try:
    spec = SpecificityScore(
        total=0.75,
        has_colors=True,
        has_layout=False,
        has_typography=False,
        has_audience=True,
        has_purpose=True,
        has_industry=True,
        has_style_ref=False,
        has_brand=False,
    )
    assert spec.total == 0.75
    assert spec.has_colors is True
    assert spec.has_audience is True
    results.ok("T11: SpecificityScore dataclass creation")
except Exception as e:
    results.fail("T11: SpecificityScore dataclass creation", str(e))

# Test 12: SpecificityScore needs_ideation (low specificity)
try:
    spec = SpecificityScore(total=0.3)
    assert spec.needs_ideation is True, f"total=0.3 should need ideation"
    results.ok("T12: SpecificityScore needs_ideation=True when low")
except Exception as e:
    results.fail("T12: SpecificityScore needs_ideation=True when low", str(e))

# Test 13: SpecificityScore needs_ideation (high specificity)
try:
    spec = SpecificityScore(total=0.8)
    assert spec.needs_ideation is False, f"total=0.8 should not need ideation"
    results.ok("T13: SpecificityScore needs_ideation=False when high")
except Exception as e:
    results.fail("T13: SpecificityScore needs_ideation=False when high", str(e))

# Test 14: SpecificityScore ideation_depth levels
try:
    deep = SpecificityScore(total=0.2)
    assert deep.ideation_depth == "deep", f"Got {deep.ideation_depth}"
    standard = SpecificityScore(total=0.4)
    assert standard.ideation_depth == "standard", f"Got {standard.ideation_depth}"
    minimal = SpecificityScore(total=0.7)
    assert minimal.ideation_depth == "minimal", f"Got {minimal.ideation_depth}"
    results.ok("T14: SpecificityScore ideation_depth levels")
except Exception as e:
    results.fail("T14: SpecificityScore ideation_depth levels", str(e))

# Test 15: score_specificity with detailed input
try:
    score = score_specificity(
        topic="AI-powered fintech analytics platform",
        purpose="Series A pitch to VCs",
        audience="Venture capitalists at Sequoia",
        company_name="FinTech Co",
    )
    assert isinstance(score, SpecificityScore)
    assert score.total > 0.0, "Should have some specificity"
    assert score.has_audience is True
    assert score.has_purpose is True
    assert score.has_industry is True
    results.ok("T15: score_specificity with detailed input")
except Exception as e:
    results.fail("T15: score_specificity with detailed input", str(e))

# Test 16: score_specificity with minimal input
try:
    score = score_specificity(topic="presentation")
    assert isinstance(score, SpecificityScore)
    assert score.total < 0.5, f"Minimal input should have low specificity, got {score.total}"
    results.ok("T16: score_specificity with minimal input")
except Exception as e:
    results.fail("T16: score_specificity with minimal input", str(e))

# Test 17: score_specificity returns SpecificityScore
try:
    score = score_specificity(
        topic="Healthcare AI",
        purpose="Team update",
        audience="Engineering team",
    )
    assert hasattr(score, "total")
    assert hasattr(score, "needs_ideation")
    assert hasattr(score, "ideation_depth")
    assert 0.0 <= score.total <= 1.0
    results.ok("T17: score_specificity return type correctness")
except Exception as e:
    results.fail("T17: score_specificity return type correctness", str(e))

# Test 18: StyleEvaluationDimension dataclass
try:
    dim = StyleEvaluationDimension(
        name="style_fidelity",
        score=85.0,
        weight=1.2,
        feedback="Excellent style consistency",
    )
    assert dim.name == "style_fidelity"
    assert dim.score == 85.0
    assert dim.weight == 1.2
    results.ok("T18: StyleEvaluationDimension creation")
except Exception as e:
    results.fail("T18: StyleEvaluationDimension creation", str(e))

# Test 19: StyleEvaluation with dimensions (field-based)
try:
    evaluation = StyleEvaluation()
    evaluation.style_fidelity = StyleEvaluationDimension(name="style_fidelity", score=0.8, weight=1.2, feedback="Good")
    evaluation.content_preservation = StyleEvaluationDimension(name="content_preservation", score=0.9, weight=1.0, feedback="Excellent")
    evaluation.output_quality = StyleEvaluationDimension(name="output_quality", score=0.75, weight=1.0, feedback="Decent")
    assert len(evaluation.dimensions) == 7  # All 7 dims exist by default
    assert evaluation.weighted_score > 0
    results.ok("T19: StyleEvaluation with dimensions")
except Exception as e:
    results.fail("T19: StyleEvaluation with dimensions", str(e))

# Test 20: StyleEvaluation weighted_score calculation
try:
    evaluation = StyleEvaluation()
    # Set specific scores on two dims, rest stay at 0
    evaluation.style_fidelity = StyleEvaluationDimension(name="a", score=1.0, weight=2.0, feedback="")
    evaluation.content_preservation = StyleEvaluationDimension(name="b", score=0.5, weight=1.0, feedback="")
    ws = evaluation.weighted_score
    # weighted across all 7 dims (5 at score=0 with default weights)
    assert ws > 0, f"Weighted score should be > 0, got {ws}"
    results.ok("T20: StyleEvaluation weighted_score calculation")
except Exception as e:
    results.fail("T20: StyleEvaluation weighted_score calculation", str(e))

# Test 21: StyleEvaluation grade property
try:
    eval_low = StyleEvaluation()  # All dims at score=0
    assert eval_low.grade == "F", f"All zeros should be F, got {eval_low.grade}"

    eval_high = StyleEvaluation()
    for dim_name in ["style_fidelity", "content_preservation", "output_quality",
                     "audience_fit", "style_inference_accuracy", "visual_cohesion", "narrative_support"]:
        setattr(eval_high, dim_name, StyleEvaluationDimension(name=dim_name, score=0.95, weight=1.0, feedback=""))
    assert eval_high.grade == "A", f"All 0.95 should be A, got {eval_high.grade}"
    results.ok("T21: StyleEvaluation grade property")
except Exception as e:
    results.fail("T21: StyleEvaluation grade property", str(e))

# Test 22: StyleEvaluation default state
try:
    evaluation = StyleEvaluation()
    # Default: all 7 dims at score=0
    assert evaluation.weighted_score == 0.0
    assert len(evaluation.dimensions) == 7
    results.ok("T22: StyleEvaluation default state returns 0")
except Exception as e:
    results.fail("T22: StyleEvaluation default state returns 0", str(e))

# Test 23: build_design_prompt basic
try:
    prompt = build_design_prompt(
        topic="AI startup pitch",
        purpose="Fundraising",
        audience="VCs",
    )
    assert isinstance(prompt, StructuredDesignPrompt)
    assert prompt.topic == "AI startup pitch"
    assert prompt.purpose == "Fundraising"
    results.ok("T23: build_design_prompt basic")
except Exception as e:
    results.fail("T23: build_design_prompt basic", str(e))

# Test 24: build_design_prompt to_prompt_string
try:
    prompt = build_design_prompt(
        topic="Healthcare analytics",
        purpose="Board meeting",
        audience="Board of directors",
    )
    text = prompt.to_prompt_string()
    assert isinstance(text, str)
    assert len(text) > 50, f"Prompt too short: {len(text)}"
    assert "[Context]" in text
    results.ok("T24: build_design_prompt to_prompt_string")
except Exception as e:
    results.fail("T24: build_design_prompt to_prompt_string", str(e))

# Test 25: StructuredDesignPrompt fields
try:
    prompt = StructuredDesignPrompt(
        topic="SaaS pitch for investors",
        layout_preference="hero-title with glass cards",
        components=["gradient background", "glassmorphism cards", "metric displays"],
    )
    assert prompt.topic == "SaaS pitch for investors"
    assert len(prompt.components) == 3
    text = prompt.to_prompt_string()
    assert "SaaS pitch" in text
    results.ok("T25: StructuredDesignPrompt manual creation")
except Exception as e:
    results.fail("T25: StructuredDesignPrompt manual creation", str(e))

# Test 26: infer_style personality_traits populated
try:
    style = infer_style("Our innovative disruptive platform transforms the industry with groundbreaking technology")
    assert isinstance(style.personality_traits, list)
    results.ok("T26: infer_style personality_traits is list")
except Exception as e:
    results.fail("T26: infer_style personality_traits is list", str(e))

# Test 27: infer_style visual_energy range
try:
    style = infer_style("Exciting revolutionary amazing breakthrough stunning visual impact")
    assert 0.0 <= style.visual_energy <= 1.0, f"visual_energy out of range: {style.visual_energy}"
    results.ok("T27: infer_style visual_energy in [0,1]")
except Exception as e:
    results.fail("T27: infer_style visual_energy in [0,1]", str(e))

# Test 28: infer_style color_warmth range
try:
    style = infer_style("A warm, friendly product for families and children")
    assert 0.0 <= style.color_warmth <= 1.0, f"color_warmth out of range: {style.color_warmth}"
    results.ok("T28: infer_style color_warmth in [0,1]")
except Exception as e:
    results.fail("T28: infer_style color_warmth in [0,1]", str(e))

# Test 29: infer_style whitespace_ratio range
try:
    style = infer_style("Minimal clean elegant premium luxury design")
    assert 0.0 <= style.whitespace_ratio <= 1.0
    results.ok("T29: infer_style whitespace_ratio in [0,1]")
except Exception as e:
    results.fail("T29: infer_style whitespace_ratio in [0,1]", str(e))

# Test 30: score_specificity with style reference
try:
    score = score_specificity(
        topic="Minimal modern keynote for our product launch",
        purpose="Product launch",
        audience="Developers",
    )
    assert isinstance(score, SpecificityScore)
    # "minimal" and "modern" are style reference keywords
    assert score.has_style_ref is True, "minimal/modern should be detected as style_ref"
    results.ok("T30: score_specificity detects style reference")
except Exception as e:
    results.fail("T30: score_specificity detects style reference", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2: Icon Registry (Tests 31-60)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 2: Icon Registry ===")

# Test 31: Import icon_registry module
try:
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
    results.ok("T31: Import icon_registry module")
except Exception as e:
    results.fail("T31: Import icon_registry module", str(e))

# Test 32: IconVariant enum
try:
    expected = {"regular", "filled", "light", "color"}
    actual = {v.value for v in IconVariant}
    assert expected == actual, f"Got {actual}"
    results.ok("T32: IconVariant enum has 4 values")
except Exception as e:
    results.fail("T32: IconVariant enum has 4 values", str(e))

# Test 33: IconSize enum
try:
    sizes = {s.value for s in IconSize}
    assert 16 in sizes and 24 in sizes and 48 in sizes
    results.ok("T33: IconSize enum has expected sizes")
except Exception as e:
    results.fail("T33: IconSize enum has expected sizes", str(e))

# Test 34: IconRef dataclass
try:
    icon = IconRef(
        name="arrow-trending",
        variant=IconVariant.REGULAR,
        size=IconSize.SIZE_24,
        category="growth",
        description="Upward trend indicator",
    )
    assert icon.name == "arrow-trending"
    assert icon.variant == IconVariant.REGULAR
    assert icon.size == IconSize.SIZE_24
    results.ok("T34: IconRef dataclass creation")
except Exception as e:
    results.fail("T34: IconRef dataclass creation", str(e))

# Test 35: IconRef fluent_name property
try:
    icon = IconRef(
        name="arrow-trending",
        variant=IconVariant.REGULAR,
        size=IconSize.SIZE_24,
    )
    fluent = icon.fluent_name
    assert isinstance(fluent, str)
    assert "arrow" in fluent.lower() or "trend" in fluent.lower() or "24" in fluent
    results.ok("T35: IconRef fluent_name property")
except Exception as e:
    results.fail("T35: IconRef fluent_name property", str(e))

# Test 36: IconRef svg_path property
try:
    icon = IconRef(
        name="arrow-trending",
        variant=IconVariant.REGULAR,
        size=IconSize.SIZE_24,
    )
    path = icon.svg_path
    assert isinstance(path, str)
    assert len(path) > 0
    results.ok("T36: IconRef svg_path property")
except Exception as e:
    results.fail("T36: IconRef svg_path property", str(e))

# Test 37: IconRef cdn_url property
try:
    icon = IconRef(
        name="arrow-trending",
        variant=IconVariant.REGULAR,
        size=IconSize.SIZE_24,
    )
    url = icon.cdn_url
    assert isinstance(url, str)
    assert url.startswith("https://")
    results.ok("T37: IconRef cdn_url property returns URL")
except Exception as e:
    results.fail("T37: IconRef cdn_url property returns URL", str(e))

# Test 38: SLIDE_TYPE_ICONS has expected slide types
try:
    expected_types = {"title-hero", "problem", "solution", "market", "traction",
                      "team", "competition", "business-model", "financials", "ask", "closing"}
    actual_types = set(SLIDE_TYPE_ICONS.keys())
    missing = expected_types - actual_types
    assert not missing, f"Missing slide types: {missing}"
    results.ok("T38: SLIDE_TYPE_ICONS has 11 slide types")
except Exception as e:
    results.fail("T38: SLIDE_TYPE_ICONS has 11 slide types", str(e))

# Test 39: Each slide type has icon list
try:
    for slide_type, icons in SLIDE_TYPE_ICONS.items():
        assert isinstance(icons, list), f"{slide_type} not a list"
        assert len(icons) >= 2, f"{slide_type} has < 2 icons"
    results.ok("T39: Each slide type has >= 2 icons")
except Exception as e:
    results.fail("T39: Each slide type has >= 2 icons", str(e))

# Test 40: CONTENT_ELEMENT_ICONS has expected elements
try:
    expected_elements = {"feature", "benefit", "step", "quote", "stat", "timeline",
                         "comparison", "list", "technology", "security", "growth", "communication"}
    actual = set(CONTENT_ELEMENT_ICONS.keys())
    missing = expected_elements - actual
    assert not missing, f"Missing elements: {missing}"
    results.ok("T40: CONTENT_ELEMENT_ICONS has 12 element types")
except Exception as e:
    results.fail("T40: CONTENT_ELEMENT_ICONS has 12 element types", str(e))

# Test 41: INDUSTRY_ICONS has expected industries
try:
    expected_industries = {"fintech", "healthtech", "edtech", "saas", "ecommerce", "ai_ml"}
    actual = set(INDUSTRY_ICONS.keys())
    missing = expected_industries - actual
    assert not missing, f"Missing industries: {missing}"
    results.ok("T41: INDUSTRY_ICONS has 6 industries")
except Exception as e:
    results.fail("T41: INDUSTRY_ICONS has 6 industries", str(e))

# Test 42: get_icons_for_slide returns IconRef list
try:
    icons = get_icons_for_slide("title-hero")
    assert isinstance(icons, list)
    assert len(icons) > 0
    assert all(isinstance(i, IconRef) for i in icons)
    results.ok("T42: get_icons_for_slide returns IconRef list")
except Exception as e:
    results.fail("T42: get_icons_for_slide returns IconRef list", str(e))

# Test 43: get_icons_for_slide with unknown type
try:
    icons = get_icons_for_slide("unknown-type")
    assert isinstance(icons, list)
    # Should return empty or default
    results.ok("T43: get_icons_for_slide unknown type returns list")
except Exception as e:
    results.fail("T43: get_icons_for_slide unknown type returns list", str(e))

# Test 44: get_icons_for_slide all known types
try:
    all_ok = True
    for slide_type in SLIDE_TYPE_ICONS.keys():
        icons = get_icons_for_slide(slide_type)
        if not icons:
            all_ok = False
    assert all_ok, "Some slide types returned no icons"
    results.ok("T44: get_icons_for_slide works for all types")
except Exception as e:
    results.fail("T44: get_icons_for_slide works for all types", str(e))

# Test 45: get_icons_for_content returns list
try:
    icons = get_icons_for_content("feature")
    assert isinstance(icons, list)
    assert len(icons) > 0
    assert all(isinstance(i, IconRef) for i in icons)
    results.ok("T45: get_icons_for_content returns IconRef list")
except Exception as e:
    results.fail("T45: get_icons_for_content returns IconRef list", str(e))

# Test 46: get_icons_for_content unknown element
try:
    icons = get_icons_for_content("nonexistent")
    assert isinstance(icons, list)
    results.ok("T46: get_icons_for_content unknown element returns list")
except Exception as e:
    results.fail("T46: get_icons_for_content unknown element returns list", str(e))

# Test 47: get_icons_for_industry returns list
try:
    icons = get_icons_for_industry("fintech")
    assert isinstance(icons, list)
    assert len(icons) > 0
    assert all(isinstance(i, IconRef) for i in icons)
    results.ok("T47: get_icons_for_industry returns IconRef list")
except Exception as e:
    results.fail("T47: get_icons_for_industry returns IconRef list", str(e))

# Test 48: get_icons_for_industry unknown industry
try:
    icons = get_icons_for_industry("aerospace")
    assert isinstance(icons, list)
    results.ok("T48: get_icons_for_industry unknown returns list")
except Exception as e:
    results.fail("T48: get_icons_for_industry unknown returns list", str(e))

# Test 49: suggest_icon_variant for high formality
try:
    variant = suggest_icon_variant(0.9)
    assert isinstance(variant, IconVariant)
    assert variant == IconVariant.LIGHT, f"High formality should suggest LIGHT, got {variant}"
    results.ok("T49: suggest_icon_variant returns IconVariant")
except Exception as e:
    results.fail("T49: suggest_icon_variant returns IconVariant", str(e))

# Test 50: suggest_icon_variant for different formality levels
try:
    v1 = suggest_icon_variant(0.9)   # formal → LIGHT
    v2 = suggest_icon_variant(0.6)   # medium → REGULAR
    v3 = suggest_icon_variant(0.3)   # casual → FILLED
    assert v1 == IconVariant.LIGHT
    assert v2 == IconVariant.REGULAR
    assert v3 == IconVariant.FILLED
    results.ok("T50: suggest_icon_variant handles different levels")
except Exception as e:
    results.fail("T50: suggest_icon_variant handles different levels", str(e))

# Test 51: get_all_icon_names returns set of strings
try:
    names = get_all_icon_names()
    assert isinstance(names, (set, list))
    assert len(names) > 10, f"Expected > 10 icons, got {len(names)}"
    assert all(isinstance(n, str) for n in names)
    results.ok("T51: get_all_icon_names returns non-empty set")
except Exception as e:
    results.fail("T51: get_all_icon_names returns non-empty set", str(e))

# Test 52: IconRef default values
try:
    icon = IconRef(name="test-icon")
    assert icon.variant == IconVariant.REGULAR
    assert icon.size == IconSize.SIZE_24
    results.ok("T52: IconRef default variant=REGULAR, size=24")
except Exception as e:
    results.fail("T52: IconRef default variant=REGULAR, size=24", str(e))

# Test 53: Icon names are strings not empty
try:
    names = get_all_icon_names()
    for name in names:
        assert len(name) > 0, f"Empty icon name found"
        assert isinstance(name, str)
    results.ok("T53: All icon names are non-empty strings")
except Exception as e:
    results.fail("T53: All icon names are non-empty strings", str(e))

# Test 54: SLIDE_TYPE_ICONS values are IconRef lists
try:
    for slide_type, icons in SLIDE_TYPE_ICONS.items():
        for icon in icons:
            assert isinstance(icon, IconRef), f"{slide_type}: {icon} not IconRef"
    results.ok("T54: SLIDE_TYPE_ICONS values are IconRef lists")
except Exception as e:
    results.fail("T54: SLIDE_TYPE_ICONS values are IconRef lists", str(e))

# Test 55: CONTENT_ELEMENT_ICONS values are IconRef lists
try:
    for element, icons in CONTENT_ELEMENT_ICONS.items():
        assert isinstance(icons, list)
        for icon in icons:
            assert isinstance(icon, IconRef)
    results.ok("T55: CONTENT_ELEMENT_ICONS values are IconRef lists")
except Exception as e:
    results.fail("T55: CONTENT_ELEMENT_ICONS values are IconRef lists", str(e))

# Test 56: INDUSTRY_ICONS values are IconRef lists
try:
    for industry, icons in INDUSTRY_ICONS.items():
        assert isinstance(icons, list)
        for icon in icons:
            assert isinstance(icon, IconRef)
    results.ok("T56: INDUSTRY_ICONS values are IconRef lists")
except Exception as e:
    results.fail("T56: INDUSTRY_ICONS values are IconRef lists", str(e))

# Test 57: get_icons_for_slide with variant override
try:
    icons = get_icons_for_slide("market")
    # All returned icons should be IconRef
    for icon in icons:
        assert hasattr(icon, "name")
        assert hasattr(icon, "variant")
        assert hasattr(icon, "size")
    results.ok("T57: get_icons_for_slide returns proper IconRef objects")
except Exception as e:
    results.fail("T57: get_icons_for_slide returns proper IconRef objects", str(e))

# Test 58: get_icons_for_content for stat element
try:
    icons = get_icons_for_content("stat")
    assert len(icons) >= 1, "stat should have icons"
    results.ok("T58: get_icons_for_content stat has icons")
except Exception as e:
    results.fail("T58: get_icons_for_content stat has icons", str(e))

# Test 59: get_icons_for_industry saas
try:
    icons = get_icons_for_industry("saas")
    assert len(icons) >= 2, f"saas should have >= 2 icons, got {len(icons)}"
    results.ok("T59: get_icons_for_industry saas has multiple icons")
except Exception as e:
    results.fail("T59: get_icons_for_industry saas has multiple icons", str(e))

# Test 60: Icon count across all maps is reasonable
try:
    total_slide = sum(len(v) for v in SLIDE_TYPE_ICONS.values())
    total_content = sum(len(v) for v in CONTENT_ELEMENT_ICONS.values())
    total_industry = sum(len(v) for v in INDUSTRY_ICONS.values())
    total = total_slide + total_content + total_industry
    assert total >= 50, f"Expected >= 50 total icon mappings, got {total}"
    results.ok(f"T60: Total icon mappings = {total} (>= 50)")
except Exception as e:
    results.fail("T60: Total icon mappings count", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3: Resource Knowledge Base (Tests 61-85)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 3: Resource Knowledge Base ===")

# Test 61: Import resource_kb module
try:
    from app.services.slides_new.design.resource_kb import (
        DesignResource,
        get_resources_by_category,
        get_resources_with_api,
        get_resources_by_tag,
        get_resource_categories,
        get_design_toolkit_summary,
        ALL_RESOURCES,
    )
    results.ok("T61: Import resource_kb module")
except Exception as e:
    results.fail("T61: Import resource_kb module", str(e))

# Test 62: DesignResource dataclass
try:
    resource = DesignResource(
        name="Coolors",
        url="https://coolors.co",
        category="color",
        description="Color palette generator",
        free=True,
        api_available=True,
        tags=["color", "palette", "generator"],
    )
    assert resource.name == "Coolors"
    assert resource.free is True
    assert resource.api_available is True
    results.ok("T62: DesignResource dataclass creation")
except Exception as e:
    results.fail("T62: DesignResource dataclass creation", str(e))

# Test 63: ALL_RESOURCES is non-empty
try:
    assert isinstance(ALL_RESOURCES, list)
    assert len(ALL_RESOURCES) > 20, f"Expected > 20 resources, got {len(ALL_RESOURCES)}"
    results.ok(f"T63: ALL_RESOURCES has {len(ALL_RESOURCES)} resources")
except Exception as e:
    results.fail("T63: ALL_RESOURCES is non-empty", str(e))

# Test 64: All resources have required fields
try:
    for r in ALL_RESOURCES:
        assert isinstance(r, DesignResource)
        assert r.name, f"Resource missing name"
        assert r.url, f"Resource {r.name} missing url"
        assert r.category, f"Resource {r.name} missing category"
    results.ok("T64: All resources have name/url/category")
except Exception as e:
    results.fail("T64: All resources have required fields", str(e))

# Test 65: get_resource_categories returns categories
try:
    categories = get_resource_categories()
    assert isinstance(categories, (list, set))
    assert len(categories) >= 5, f"Expected >= 5 categories, got {len(categories)}"
    results.ok(f"T65: get_resource_categories returns {len(categories)} categories")
except Exception as e:
    results.fail("T65: get_resource_categories returns categories", str(e))

# Test 66: get_resources_by_category color
try:
    resources = get_resources_by_category("color")
    assert isinstance(resources, list)
    assert len(resources) >= 1, "Should have color resources"
    assert all(isinstance(r, DesignResource) for r in resources)
    results.ok(f"T66: get_resources_by_category color = {len(resources)}")
except Exception as e:
    results.fail("T66: get_resources_by_category color", str(e))

# Test 67: get_resources_by_category gradient
try:
    resources = get_resources_by_category("gradient")
    assert isinstance(resources, list)
    assert len(resources) >= 1
    results.ok(f"T67: get_resources_by_category gradient = {len(resources)}")
except Exception as e:
    results.fail("T67: get_resources_by_category gradient", str(e))

# Test 68: get_resources_by_category font
try:
    resources = get_resources_by_category("font")
    assert isinstance(resources, list)
    assert len(resources) >= 1
    results.ok(f"T68: get_resources_by_category font = {len(resources)}")
except Exception as e:
    results.fail("T68: get_resources_by_category font", str(e))

# Test 69: get_resources_by_category icon
try:
    resources = get_resources_by_category("icon")
    assert isinstance(resources, list)
    assert len(resources) >= 1
    results.ok(f"T69: get_resources_by_category icon = {len(resources)}")
except Exception as e:
    results.fail("T69: get_resources_by_category icon", str(e))

# Test 70: get_resources_by_category illustration
try:
    resources = get_resources_by_category("illustration")
    assert isinstance(resources, list)
    assert len(resources) >= 1
    results.ok(f"T70: get_resources_by_category illustration = {len(resources)}")
except Exception as e:
    results.fail("T70: get_resources_by_category illustration", str(e))

# Test 71: get_resources_by_category animation
try:
    resources = get_resources_by_category("animation")
    assert isinstance(resources, list)
    assert len(resources) >= 1
    results.ok(f"T71: get_resources_by_category animation = {len(resources)}")
except Exception as e:
    results.fail("T71: get_resources_by_category animation", str(e))

# Test 72: get_resources_by_category background
try:
    resources = get_resources_by_category("background")
    assert isinstance(resources, list)
    assert len(resources) >= 1
    results.ok(f"T72: get_resources_by_category background = {len(resources)}")
except Exception as e:
    results.fail("T72: get_resources_by_category background", str(e))

# Test 73: get_resources_by_category design_system
try:
    resources = get_resources_by_category("design_system")
    assert isinstance(resources, list)
    assert len(resources) >= 1
    results.ok(f"T73: get_resources_by_category design_system = {len(resources)}")
except Exception as e:
    results.fail("T73: get_resources_by_category design_system", str(e))

# Test 74: get_resources_by_category unknown returns empty
try:
    resources = get_resources_by_category("nonexistent_category")
    assert isinstance(resources, list)
    assert len(resources) == 0
    results.ok("T74: get_resources_by_category unknown returns empty")
except Exception as e:
    results.fail("T74: get_resources_by_category unknown returns empty", str(e))

# Test 75: get_resources_with_api returns only API resources
try:
    api_resources = get_resources_with_api()
    assert isinstance(api_resources, list)
    assert len(api_resources) >= 1, "Should have API-available resources"
    for r in api_resources:
        assert r.api_available is True, f"{r.name} api_available should be True"
    results.ok(f"T75: get_resources_with_api returns {len(api_resources)} API resources")
except Exception as e:
    results.fail("T75: get_resources_with_api returns API resources", str(e))

# Test 76: get_resources_by_tag returns matching resources
try:
    resources = get_resources_by_tag("palette")
    assert isinstance(resources, list)
    assert len(resources) >= 1, "Should find resources tagged 'palette'"
    results.ok(f"T76: get_resources_by_tag palette = {len(resources)}")
except Exception as e:
    results.fail("T76: get_resources_by_tag palette", str(e))

# Test 77: get_resources_by_tag unknown returns empty
try:
    resources = get_resources_by_tag("zzzznonexistent")
    assert isinstance(resources, list)
    assert len(resources) == 0
    results.ok("T77: get_resources_by_tag unknown returns empty")
except Exception as e:
    results.fail("T77: get_resources_by_tag unknown returns empty", str(e))

# Test 78: get_design_toolkit_summary returns dict
try:
    summary = get_design_toolkit_summary()
    assert isinstance(summary, dict)
    assert len(summary) > 0, "Summary should not be empty"
    results.ok("T78: get_design_toolkit_summary returns dict")
except Exception as e:
    results.fail("T78: get_design_toolkit_summary returns dict", str(e))

# Test 79: get_design_toolkit_summary has category counts
try:
    summary = get_design_toolkit_summary()
    categories = get_resource_categories()
    for cat in categories:
        assert cat in summary, f"Missing {cat} in summary"
    results.ok("T79: Toolkit summary has all categories")
except Exception as e:
    results.fail("T79: Toolkit summary has all categories", str(e))

# Test 80: Resources have valid URLs
try:
    for r in ALL_RESOURCES:
        assert r.url.startswith("https://") or r.url.startswith("http://"), \
            f"{r.name} has invalid URL: {r.url}"
    results.ok("T80: All resources have valid URL format")
except Exception as e:
    results.fail("T80: All resources have valid URLs", str(e))

# Test 81: Free resources exist
try:
    free = [r for r in ALL_RESOURCES if r.free]
    assert len(free) >= 10, f"Expected >= 10 free resources, got {len(free)}"
    results.ok(f"T81: {len(free)} free resources available")
except Exception as e:
    results.fail("T81: Free resources exist", str(e))

# Test 82: Resources have tags
try:
    tagged = [r for r in ALL_RESOURCES if r.tags]
    assert len(tagged) >= len(ALL_RESOURCES) * 0.5, "At least 50% resources should have tags"
    results.ok(f"T82: {len(tagged)} resources have tags")
except Exception as e:
    results.fail("T82: Resources have tags", str(e))

# Test 83: No duplicate resource names
try:
    names = [r.name for r in ALL_RESOURCES]
    duplicates = [n for n in names if names.count(n) > 1]
    assert not duplicates, f"Duplicate resources: {set(duplicates)}"
    results.ok("T83: No duplicate resource names")
except Exception as e:
    results.fail("T83: No duplicate resource names", str(e))

# Test 84: DesignResource default values
try:
    r = DesignResource(name="Test", url="https://test.com", category="test", description="A test resource")
    assert isinstance(r.description, str)
    assert isinstance(r.free, bool)
    assert r.free is True  # default
    assert isinstance(r.api_available, bool)
    assert r.api_available is False  # default
    results.ok("T84: DesignResource default values work")
except Exception as e:
    results.fail("T84: DesignResource default values work", str(e))

# Test 85: get_resources_by_tag case handling
try:
    r1 = get_resources_by_tag("Color")
    r2 = get_resources_by_tag("color")
    # Should handle case (either both work or lowercase works)
    assert isinstance(r1, list) and isinstance(r2, list)
    results.ok("T85: get_resources_by_tag handles case")
except Exception as e:
    results.fail("T85: get_resources_by_tag handles case", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4: Integration Tests (Tests 86-100)
# ══════════════════════════════════════════════════════════════════════════════

print("\n=== Section 4: Integration Tests ===")

# Test 86: Design __init__.py exports Phase 13 style_transfer
try:
    from app.services.slides_new.design import (
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
    results.ok("T86: design __init__ exports style_transfer")
except Exception as e:
    results.fail("T86: design __init__ exports style_transfer", str(e))

# Test 87: Design __init__.py exports Phase 13 icon_registry
try:
    from app.services.slides_new.design import (
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
    results.ok("T87: design __init__ exports icon_registry")
except Exception as e:
    results.fail("T87: design __init__ exports icon_registry", str(e))

# Test 88: Design __init__.py exports Phase 13 resource_kb
try:
    from app.services.slides_new.design import (
        DesignResource,
        get_resources_by_category,
        get_resources_with_api,
        get_resources_by_tag,
        get_resource_categories,
        get_design_toolkit_summary,
        ALL_RESOURCES,
    )
    results.ok("T88: design __init__ exports resource_kb")
except Exception as e:
    results.fail("T88: design __init__ exports resource_kb", str(e))

# Test 89: Design __init__.py still exports Phase 2 + 5
try:
    from app.services.slides_new.design import (
        DesignSystem,
        generate_design_system,
        BrandDNA,
        AntiAISlopProcessor,
        StyleDiscoveryResult,
        PreTeXtEngine,
        DesignIntelligenceEngine,
    )
    results.ok("T89: design __init__ still exports Phase 2+5")
except Exception as e:
    results.fail("T89: design __init__ still exports Phase 2+5", str(e))

# Test 90: DesignerAgent imports new modules
try:
    from app.services.slides_new.agents.designer_agent import DesignerAgent
    # Verify the class exists and has designer type
    assert DesignerAgent is not None
    results.ok("T90: DesignerAgent imports successfully")
except Exception as e:
    results.fail("T90: DesignerAgent imports successfully", str(e))

# Test 91: DesignerAgent has _build_style_intelligence method
try:
    from app.services.slides_new.agents.designer_agent import DesignerAgent
    assert hasattr(DesignerAgent, "_build_style_intelligence")
    results.ok("T91: DesignerAgent has _build_style_intelligence")
except Exception as e:
    results.fail("T91: DesignerAgent has _build_style_intelligence", str(e))

# Test 92: _build_style_intelligence returns dict
try:
    from app.services.slides_new.agents.designer_agent import DesignerAgent
    # Call static-like (it doesn't need self for this)
    agent = DesignerAgent.__new__(DesignerAgent)
    result = agent._build_style_intelligence(
        topic="AI SaaS Platform for fintech",
        purpose="Series A pitch",
        audience="VC investors",
        industry="fintech",
    )
    assert isinstance(result, dict)
    assert "inferred_style" in result
    assert "specificity" in result
    results.ok("T92: _build_style_intelligence returns correct dict")
except Exception as e:
    results.fail("T92: _build_style_intelligence returns correct dict", str(e))

# Test 93: Style intelligence inferred_style has expected keys
try:
    result = agent._build_style_intelligence(
        topic="Enterprise analytics dashboard",
        purpose="Quarterly review",
        audience="Board of directors",
    )
    style = result["inferred_style"]
    expected_keys = {"tone", "formality_level", "vocabulary_level", "visual_energy",
                     "color_warmth", "whitespace_ratio", "personality_traits"}
    assert expected_keys.issubset(set(style.keys())), f"Missing keys: {expected_keys - set(style.keys())}"
    results.ok("T93: Style intelligence has expected keys")
except Exception as e:
    results.fail("T93: Style intelligence has expected keys", str(e))

# Test 94: Style intelligence specificity has expected keys
try:
    spec = result["specificity"]
    expected_keys = {"total", "needs_ideation", "ideation_depth", "has_audience",
                     "has_purpose", "has_industry"}
    assert expected_keys.issubset(set(spec.keys())), f"Missing: {expected_keys - set(spec.keys())}"
    results.ok("T94: Style intelligence specificity has keys")
except Exception as e:
    results.fail("T94: Style intelligence specificity has keys", str(e))

# Test 95: Style intelligence with minimal input
try:
    result = agent._build_style_intelligence(
        topic="presentation",
        purpose="",
        audience="",
    )
    assert isinstance(result, dict)
    assert result["specificity"]["needs_ideation"] is True
    results.ok("T95: Minimal input triggers needs_ideation")
except Exception as e:
    results.fail("T95: Minimal input triggers needs_ideation", str(e))

# Test 96: Cross-module: style inference + icon lookup
try:
    style = infer_style("Fintech startup disrupting payment processing")
    icons = get_icons_for_industry("fintech")
    assert isinstance(style, InferredStyle)
    assert isinstance(icons, list)
    assert len(icons) > 0
    results.ok("T96: Cross-module style + icon lookup works")
except Exception as e:
    results.fail("T96: Cross-module style + icon lookup works", str(e))

# Test 97: Cross-module: specificity + resources
try:
    score = score_specificity(topic="SaaS dashboard", purpose="pitch", audience="VCs")
    resources = get_resources_by_category("color")
    assert isinstance(score, SpecificityScore)
    assert isinstance(resources, list)
    results.ok("T97: Cross-module specificity + resources works")
except Exception as e:
    results.fail("T97: Cross-module specificity + resources works", str(e))

# Test 98: Cross-module: structured prompt + icons
try:
    prompt = build_design_prompt(
        topic="Healthcare AI platform",
        purpose="Board presentation",
        audience="Hospital executives",
    )
    icons = get_icons_for_industry("healthtech")
    text = prompt.to_prompt_string()
    assert len(text) > 0
    assert len(icons) > 0
    results.ok("T98: Cross-module prompt + industry icons")
except Exception as e:
    results.fail("T98: Cross-module prompt + industry icons", str(e))

# Test 99: All Phase 13 modules importable from design package
try:
    import app.services.slides_new.design as design_pkg

    # Count Phase 13 symbols
    p13_symbols = [
        "InferredStyle", "SpecificityScore", "StructuredDesignPrompt",
        "StyleEvaluation", "StyleEvaluationDimension", "Tone",
        "SentenceStructure", "VocabularyLevel", "build_design_prompt",
        "infer_style", "score_specificity",
        "IconRef", "IconVariant", "IconSize",
        "get_icons_for_slide", "get_icons_for_content",
        "get_icons_for_industry", "suggest_icon_variant", "get_all_icon_names",
        "SLIDE_TYPE_ICONS", "CONTENT_ELEMENT_ICONS", "INDUSTRY_ICONS",
        "DesignResource", "get_resources_by_category", "get_resources_with_api",
        "get_resources_by_tag", "get_resource_categories",
        "get_design_toolkit_summary", "ALL_RESOURCES",
    ]
    for sym in p13_symbols:
        assert hasattr(design_pkg, sym), f"Missing: {sym}"
    results.ok(f"T99: All {len(p13_symbols)} Phase 13 symbols exported")
except Exception as e:
    results.fail("T99: All Phase 13 symbols exported", str(e))

# Test 100: DesignerAgent ICON_MAP still works alongside icon_registry
try:
    from app.services.slides_new.agents.designer_agent import DesignerAgent
    # Old ICON_MAP for Lucide
    assert hasattr(DesignerAgent, "ICON_MAP")
    assert isinstance(DesignerAgent.ICON_MAP, dict)
    assert "growth" in DesignerAgent.ICON_MAP
    # New icon_registry for Fluent UI (separate concern)
    icons = get_icons_for_slide("traction")
    assert len(icons) > 0
    results.ok("T100: Lucide ICON_MAP + Fluent icon_registry coexist")
except Exception as e:
    results.fail("T100: Lucide ICON_MAP + Fluent icon_registry coexist", str(e))


# ══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════════════

success = results.summary()
sys.exit(0 if success else 1)
