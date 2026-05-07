"""
Mode Transformers -- Rules for converting between presentation and reading modes.
Reading mode is generated FIRST (deeper reasoning with full evidence),
then compressed to presentation mode (slide-optimized).
"""

import json
import logging
from typing import Optional

from app.mcp.brain_mcp.research.models import (
    BodySection,
    PresentationContent,
    ReadingContent,
    StyleProfile,
)
from app.services.llm.model_router import ModelRouter, TaskType

logger = logging.getLogger(__name__)


READING_TO_PRESENTATION_PROMPT = """You are a presentation design expert converting detailed reading content
into punchy slide content. Follow the style rules EXACTLY.

=== STYLE RULES ===
Style: {style_id}
Max bullets: {max_bullets}
Max words per bullet: {max_words_per_bullet}
Max words in title: {max_words_title}
Headline mode: {headline_mode}
Bullet starts with: {bullet_starts_with}
Hero stat required: {hero_stat_required}
No adjectives: {no_adjectives}
Tone: {tone}

=== READING CONTENT TO COMPRESS ===
Title: {reading_title}
Summary: {reading_summary}
Sections:
{reading_sections}

=== KEY EVIDENCE ===
{evidence_summary}

RULES:
1. Title must be {max_words_title} words or fewer using {headline_mode} mode.
2. Extract exactly {max_bullets} bullets or fewer.
3. Each bullet must be {max_words_per_bullet} words or fewer.
4. Bullets must start with: {bullet_starts_with}.
5. If hero_stat_required is true, extract the single most impactful number.
6. If no_adjectives is true, strip all adjectives from bullets.
7. Preserve all numeric claims exactly -- do not round or change numbers.
8. Add subtitle only if meaningful and within 10 words.
9. Annotation should be source attribution if style requires it.

Return ONLY valid JSON:
{{
    "title": "Compressed headline",
    "subtitle": "Optional subtitle or null",
    "bullets": ["Bullet 1", "Bullet 2"],
    "hero_stat": "Key stat or null",
    "annotation": "Source note or null"
}}"""


PRESENTATION_TO_NOTES_PROMPT = """You are generating speaker notes for a presentation slide.
The speaker notes should help a presenter deliver this slide effectively.

=== PRESENTATION CONTENT ===
Title: {pres_title}
Subtitle: {pres_subtitle}
Bullets: {pres_bullets}
Hero stat: {pres_hero_stat}

=== FULL READING CONTENT (for depth) ===
Summary: {reading_summary}
Key sections: {reading_sections}

=== STYLE ===
Tone: {tone}
Audience: {audience}

RULES:
1. Speaker notes expand on each bullet with context from reading content.
2. Include transition phrases between points.
3. Note which data points to emphasize verbally.
4. Include backup data the speaker can use if questioned.
5. Keep each note to 1-3 sentences.
6. Match the {tone} tone.
7. Number notes to correspond with slide flow.

Return ONLY a JSON array of strings:
["Note 1 for opening/title", "Note 2 for first bullet", "Note 3 for second bullet", ...]"""


READING_GENERATION_PROMPT = """You are generating detailed reading-mode content for a presentation slide.
Reading mode is the full-depth document view, not the projection view.

=== SLIDE CONTEXT ===
Slide type: {slide_kind}
Topic: {topic}
Audience: {audience}

=== EVIDENCE ===
{evidence}

=== STYLE RULES ===
Style: {style_id}
Tone: {tone}
Include assumptions: {include_assumptions}
Include risks: {include_risks}
Citation required: {citation_required}
Data first: {data_first}
Max body sections: {max_body_sections}
Max sentences per paragraph: {paragraph_max_sentences}

RULES:
1. Title: Clear, descriptive heading for this section.
2. Summary: 2-3 sentence executive summary of the evidence for this slide topic.
3. Body sections: {max_body_sections} sections max, each with heading, paragraphs, and source_refs.
4. Each paragraph: {paragraph_max_sentences} sentences max.
5. Every numeric claim MUST cite its source in [brackets].
6. If include_assumptions is true, list key assumptions underlying the analysis.
7. If include_risks is true, list risks to the thesis.
8. If data_first is true, lead each section with the strongest data point.
9. Never invent data. Only use evidence provided.
10. If citation_required is true, every claim must have a source_ref.

Return ONLY valid JSON:
{{
    "title": "Section title",
    "summary": "2-3 sentence summary",
    "body_sections": [
        {{
            "heading": "Section heading",
            "paragraphs": ["Paragraph text with [Source] citations..."],
            "source_refs": ["Source Name"]
        }}
    ],
    "assumptions": ["Assumption 1", "Assumption 2"],
    "risks": ["Risk 1", "Risk 2"]
}}"""


class ModeTransformer:
    """Converts between reading and presentation modes using LLM."""

    def __init__(self, model_router: ModelRouter):
        self._router = model_router

    async def reading_to_presentation(
        self,
        reading: ReadingContent,
        style: StyleProfile,
        evidence_summary: str = "",
    ) -> PresentationContent:
        """Compress reading mode to presentation mode respecting style rules."""
        # Format reading sections for prompt
        sections_text = ""
        for section in reading.body_sections:
            sections_text += f"\n## {section.heading}\n"
            for p in section.paragraphs:
                sections_text += f"{p}\n"

        pres_rules = style.presentation_rules
        prompt = READING_TO_PRESENTATION_PROMPT.format(
            style_id=style.style_id,
            max_bullets=pres_rules.get("max_bullets", style.max_bullets_presentation),
            max_words_per_bullet=style.max_words_per_bullet,
            max_words_title=pres_rules.get("max_words_title", 8),
            headline_mode=style.headline_mode,
            bullet_starts_with=pres_rules.get("bullet_starts_with", "any"),
            hero_stat_required=pres_rules.get("hero_stat_required", False),
            no_adjectives=pres_rules.get("no_adjectives", False),
            tone=style.tone,
            reading_title=reading.title,
            reading_summary=reading.summary,
            reading_sections=sections_text,
            evidence_summary=evidence_summary,
        )

        messages = [
            {"role": "system", "content": "You are a presentation content compressor. Output only valid JSON."},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self._router.complete(
                task_type=TaskType.CONTENT_FIT_RESIZE,
                messages=messages,
                temperature=0.3,
                max_tokens=1024,
            )
            data = json.loads(self._strip_json_fences(response.content))

            # Enforce style constraints
            title = data.get("title", reading.title)
            max_title_words = pres_rules.get("max_words_title", 8)
            title_words = title.split()
            if len(title_words) > max_title_words:
                title = " ".join(title_words[:max_title_words])

            bullets = data.get("bullets", [])[:style.max_bullets_presentation]
            enforced_bullets = []
            for b in bullets:
                words = b.split()
                if len(words) > style.max_words_per_bullet:
                    b = " ".join(words[:style.max_words_per_bullet])
                enforced_bullets.append(b)

            return PresentationContent(
                title=title,
                subtitle=data.get("subtitle"),
                bullets=enforced_bullets,
                hero_stat=data.get("hero_stat"),
                annotation=data.get("annotation"),
            )
        except Exception as e:
            logger.error("reading_to_presentation failed: %s", e)
            # Fallback: extract from reading content directly
            return self._fallback_compress(reading, style)

    async def generate_speaker_notes(
        self,
        presentation: PresentationContent,
        reading: ReadingContent,
        style: StyleProfile,
        audience: str = "investors",
    ) -> list[str]:
        """Generate speaker notes from both modes."""
        sections_text = ""
        for section in reading.body_sections[:3]:
            sections_text += f"{section.heading}: "
            sections_text += " ".join(section.paragraphs[:2])
            sections_text += "\n"

        prompt = PRESENTATION_TO_NOTES_PROMPT.format(
            pres_title=presentation.title,
            pres_subtitle=presentation.subtitle or "None",
            pres_bullets="\n".join(f"- {b}" for b in presentation.bullets),
            pres_hero_stat=presentation.hero_stat or "None",
            reading_summary=reading.summary,
            reading_sections=sections_text,
            tone=style.tone,
            audience=audience,
        )

        messages = [
            {"role": "system", "content": "You generate speaker notes. Output only a JSON array of strings."},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self._router.complete(
                task_type=TaskType.TEMPLATE_FILL,
                messages=messages,
                temperature=0.4,
                max_tokens=1024,
            )
            notes = json.loads(self._strip_json_fences(response.content))
            if isinstance(notes, list):
                return [str(n) for n in notes]
            return []
        except Exception as e:
            logger.error("generate_speaker_notes failed: %s", e)
            return self._fallback_notes(presentation, reading)

    async def generate_reading_content(
        self,
        evidence_text: str,
        style: StyleProfile,
        slide_kind: str,
        topic: str,
        audience: str = "investors",
    ) -> ReadingContent:
        """Generate full reading-mode content from evidence."""
        rd_rules = style.reading_rules
        prompt = READING_GENERATION_PROMPT.format(
            slide_kind=slide_kind,
            topic=topic,
            audience=audience,
            evidence=evidence_text,
            style_id=style.style_id,
            tone=style.tone,
            include_assumptions=rd_rules.get("include_assumptions", True),
            include_risks=rd_rules.get("include_risks", True),
            citation_required=rd_rules.get("citation_required", True),
            data_first=rd_rules.get("data_first", True),
            max_body_sections=rd_rules.get("max_body_sections", 4),
            paragraph_max_sentences=rd_rules.get("paragraph_max_sentences", 5),
        )

        messages = [
            {"role": "system", "content": "You are a research content writer. Output only valid JSON."},
            {"role": "user", "content": prompt},
        ]

        try:
            response = await self._router.complete(
                task_type=TaskType.NARRATIVE_STORYTELLING,
                messages=messages,
                temperature=0.5,
                max_tokens=3000,
            )
            data = json.loads(self._strip_json_fences(response.content))

            body_sections = []
            for bs in data.get("body_sections", []):
                body_sections.append(BodySection(
                    heading=bs.get("heading", ""),
                    paragraphs=bs.get("paragraphs", []),
                    source_refs=bs.get("source_refs", []),
                ))

            return ReadingContent(
                title=data.get("title", topic),
                summary=data.get("summary", ""),
                body_sections=body_sections,
                assumptions=data.get("assumptions", []),
                risks=data.get("risks", []),
            )
        except Exception as e:
            logger.error("generate_reading_content failed: %s", e)
            return ReadingContent(
                title=topic,
                summary=f"Analysis of {topic} for {audience}.",
                body_sections=[BodySection(heading="Overview", paragraphs=["Evidence analysis pending."])],
            )

    def _fallback_compress(
        self,
        reading: ReadingContent,
        style: StyleProfile,
    ) -> PresentationContent:
        """Deterministic fallback: extract presentation from reading without LLM."""
        title_words = reading.title.split()
        max_w = style.presentation_rules.get("max_words_title", 8)
        title = " ".join(title_words[:max_w])

        bullets: list[str] = []
        for section in reading.body_sections:
            if section.paragraphs:
                first = section.paragraphs[0]
                words = first.split()[:style.max_words_per_bullet]
                bullets.append(" ".join(words))
            if len(bullets) >= style.max_bullets_presentation:
                break

        hero_stat: Optional[str] = None
        if style.presentation_rules.get("hero_stat_required"):
            import re
            for section in reading.body_sections:
                for p in section.paragraphs:
                    match = re.search(r'\$[\d,.]+\s*[BMKbmk]?|\d+\.?\d*\s*%', p)
                    if match:
                        hero_stat = match.group()
                        break
                if hero_stat:
                    break

        return PresentationContent(
            title=title,
            subtitle=None,
            bullets=bullets,
            hero_stat=hero_stat,
            annotation=None,
        )

    def _fallback_notes(
        self,
        presentation: PresentationContent,
        reading: ReadingContent,
    ) -> list[str]:
        """Deterministic fallback for speaker notes."""
        notes = [f"Open with: {presentation.title}"]
        if reading.summary:
            notes.append(f"Context: {reading.summary}")
        for bullet in presentation.bullets:
            notes.append(f"Expand on: {bullet}")
        return notes

    @staticmethod
    def _strip_json_fences(text: str) -> str:
        """Remove markdown code fences from LLM JSON responses."""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()
