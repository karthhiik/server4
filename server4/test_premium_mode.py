#!/usr/bin/env python
"""
Premium Mode Test - Run V4 pipeline in premium mode.
Uses real LLM API (LLM/GLM models from .env, no Gemini).
Output: premiummodeupdated.json
"""
import json
import sys

def run_premium_mode():
    """Run Premium mode test."""
    print("[START] Starting Premium Mode Test...")
    print("[INFO] Note: Using LLM/GLM models (no Gemini)")
    
    try:
        from app.services.v4.content_pipeline import V4ContentPipeline
        from app.services.v4.skeleton_planner import SkeletonPlanner
        
        # Initialize planner
        planner = SkeletonPlanner(model_tier="premium")
        
        print("[OK] Imports successful")
        print(f"[OK] Planner mode: {planner.model_tier}")
        
        # Test with user's input
        user_query = "Create an investor pitch deck for a revolutionary AI-powered cyber-insurance platform that also explores space technology applications"
        project_id = "test_premium_001"
        
        # Generate skeleton
        print(f"\n[GEN] Generating skeleton for: {user_query}")
        
        from app.services.v4.research_collector import ResearchPacket, Citation
        mock_research = ResearchPacket(
            query=user_query,
            industry="AI Technology",
            company_name="CyberSpace AI",
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
            slide_count=10,
            narrative_arc="investor_pitch"
        )
        
        print(f"[OK] Generated skeleton: {skeleton.title}")
        print(f"[OK] Slides: {len(skeleton.slides)}")
        
        # Output results
        result = {
            "mode": "premium",
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
                        "thesis_sentence": s.thesis_sentence,
                    }
                    for s in skeleton.slides
                ]
            }
        }
        
        with open('premiummodeupdated.json', 'w') as f:
            json.dump(result, f, indent=2)
        
        print(f"\n[OK] Results saved to premiummodeupdated.json")
        return True
        
    except Exception as e:
        print(f"[ERROR] Error: {e}")
        import traceback
        traceback.print_exc()
        
        result = {
            "mode": "premium",
            "status": "error",
            "error": str(e)
        }
        with open('premiummodeupdated.json', 'w') as f:
            json.dump(result, f, indent=2)
        return False

if __name__ == "__main__":
    success = run_premium_mode()
    sys.exit(0 if success else 1)
