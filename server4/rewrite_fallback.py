#!/usr/bin/env python
"""Fix skeleton_planner.py by rewriting the problematic function cleanly"""

filepath = 'app/services/v4/skeleton_planner.py'

# Read the file
with open(filepath, 'rb') as f:
    data = f.read()

print(f"Read {len(data)} bytes")

# Find the start of _fallback_skeleton function
start_marker = b'    def _fallback_skeleton('
start_idx = data.find(start_marker)
print(f"Found function start at: {start_idx}")

if start_idx >= 0:
    # Find where this function ends (next def or class at indent 0)
    rest = data[start_idx+len(start_marker):]
    # Find next top-level def or class
    import re
    matches = [m.start() for m in re.finditer(rb'\n(def |class )', rest)]
    if matches:
        end_idx = start_idx + len(start_marker) + matches[0]
    else:
        end_idx = len(data)
    
    print(f"Function ends at: {end_idx}")
    print(f"Function text (first 200 bytes): {repr(data[start_idx:start_idx+200])}")
    
    # Create a clean replacement
    new_func = b'''    def _fallback_skeleton(
        self,
        project_id: str,
        user_query: str,
        intents: list[str],
        research: ResearchPacket,
        target_slide_count: Optional[int] = None,
        narrative_arc: str = "investor_pitch",
    ) -> DeckSkeleton:
        """Fallback skeleton."""
        cap = (
            target_slide_count
            if target_slide_count and target_slide_count > 0
            else self.FALLBACK_MAX_SLIDES
        )
        cap = min(cap, self.FALLBACK_MAX_SLIDES)
        intents = intents[:cap]
        
        # Intent-appropriate layout map
        _intent_layout: dict[str, str] = {
            "title":          "title-only",
            "problem":        "two-column",
            "solution":       "two-column",
            "how_it_works":   "diagram",
            "market":         "stat-hero",
            "traction":       "stat-hero",
            "business_model": "two-column",
            "competition":    "comparison",
            "team":           "team-grid",
            "technology":     "two-column",
            "finances":      "chart-focus",
            "go_to_market":   "two-column",
            "ask":            "stat-hero",
            "vision":         "image-full",
        }
        
        slides: list[SlideSkeleton] = []
        for i, intent in enumerate(intents):
            fallback_headline = self._default_headline_for_intent(
                intent, research.company_name if research else None
            )
            slides.append(SlideSkeleton(
                index=i,
                intent=intent,
                purpose=f"Cover {intent.replace('_', ' ')} for this pitch",
                headline_target=fallback_headline,
                key_points=self._seed_key_points(intent, user_query, research),
                density_target="medium",
                layout_hint=_intent_layout.get(intent, "two-column"),
                evidence_refs=[c.url for c in research.top_citations(2)],
                generic_risk="high",
            ))
        
        company = (research.company_name or "").strip() if research else ""
        title = self._clean_title_from_query(user_query, company or None)
        return DeckSkeleton(
            project_id=project_id,
            title=title[:120],
            narrative_arc=narrative_arc or "custom",
            slides=slides,
        )
'''
    
    # Replace
    data = data[:start_idx] + new_func + data[end_idx:]
    
    # Write back
    with open(filepath, 'wb') as f:
        f.write(data)
    
    print(f"Wrote {len(data)} bytes")
    print("Function rewritten cleanly!")
else:
    print("Could not find function")
