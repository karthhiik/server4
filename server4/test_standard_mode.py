#!/usr/bin/env python
"""
Standard Mode Test - Run V4 pipeline in standard mode.
User input: Cyber-Insurance / Space Exploration, 12 slides.
Output: standardmodeupdated.json
"""
import json
import sys

def run_standard_mode():
    """Run Standard mode test."""
    print("[START] Starting Standard Mode Test...")
    print("[QUERY] Create a presentation about Cyber-Insurance and Space Exploration (12 slides)")
    
    try:
        from app.services.v4.content_pipeline import V4ContentPipeline
        from app.services.v4.skeleton_planner import SkeletonPlanner, DeckSkeleton
        
        # Initialize planner
        planner = SkeletonPlanner(model_tier="standard")
        
        print("[OK] Imports successful")
        print(f"[OK] Planner mode: {planner.model_tier}")
        
        # Test with user's input
        user_query = "Create a presentation about Cyber-Insurance and Space Exploration with 12 slides"
        project_id = "test_standard_001"
        
        # Generate skeleton (planner.plan() handles async internally)
        print(f"\n[GEN] Generating skeleton for: {user_query}")
        
        from app.services.v4.research_collector import ResearchPacket, Citation
        mock_research = ResearchPacket(
            query=user_query,
            industry="Technology",
            company_name="CyberSpace Tech",
            citations=[],
            news_citations=[],
            financial_data={},
            social_signals={},
            duration_ms=0,
            cache_hit=False
        )
        
        skeleton = planner.plan(
            project_id=project_id,
            user_query=user_query,
            research=mock_research,
            slide_count=12,
            narrative_arc="investor_pitch"
        )
        
        print(f"[OK] Generated skeleton: {skeleton.title}")
        print(f"[OK] Slides: {len(skeleton.slides)}")
        
        # Output results
        result = {
            "mode": "standard",
            "status": "success",
            "project_id": project_id,
            "query": user_query,
            "skeleton": {
                "title": skeleton.title,
                "narrative_arc": skeleton.narrative_arc,
                "slide_count": len(skeleton.slides),
                "slides": [
                    {
                        "index": s.index,
                        "intent": s.intent,
                        "headline_target": s.headline_target,
                        "layout_hint": s.layout_hint,
                    }
                    for s in skeleton.slides
                ]
            }
        }
        
        with open('standardmodeupdated.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n[OK] Results saved to standardmodeupdated.json")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        
        result = {
            "mode": "standard",
            "status": "error",
            "error": str(e)
        }
        with open('standardmodeupdated.json', 'w') as f:
            json.dump(result, f, indent=2)
        return False

if __name__ == "__main__":
    success = run_standard_mode()
    sys.exit(0 if success else 1)
