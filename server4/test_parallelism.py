"""
Test True Parallelism in ParallelWriter.
"""
import asyncio
import time

async def test_parallel():
    print("=== Testing True Parallelism ===")
    
    from app.services.v4.parallel_writer import ParallelWriter, GeneratedSlide
    from app.services.v4.skeleton_planner import SlideSkeleton, DeckSkeleton
    from app.services.v4.research_collector import ResearchPacket
    
    writer = ParallelWriter()
    
    # Create a minimal skeleton with 5 slides
    slides = [
        SlideSkeleton(
            index=i,
            intent='title',
            purpose='pitch_deck',
            headline_target=f'Slide {i}',
            key_points=[],
            density_target='low',
            layout_hint='title-only'
        )
        for i in range(5)
    ]
    skeleton = DeckSkeleton(project_id='test-123', title='Test', narrative_arc='test', slides=slides)
    research = ResearchPacket(
        query='test', industry=None, company_name=None,
        citations=[], news_citations=[], financial_data={}, social_signals={}, duration_ms=0
    )
    
    print("Starting parallel write of 5 slides...")
    print("MAX_CONCURRENCY =", ParallelWriter.MAX_CONCURRENCY)
    print("Expected: ~1-2s if parallel, ~5-10s if sequential")
    print()
    
    start = time.perf_counter()
    
    result = await writer.write_all(
        skeleton=skeleton,
        research=research,
        mode='standard',
        purpose='pitch_deck',
    )
    
    end = time.perf_counter()
    elapsed = end - start
    
    print()
    print("=== Results ===")
    print(f"Total time: {elapsed:.2f}s")
    print(f"Slides generated: {len(result)}")
    print()
    
    # Check if parallel: if elapsed < 3.0s, it's likely parallel
    if elapsed < 3.0:
        print("STATUS: PASS (likely parallel)")
        print(f"  Time per slide: {elapsed/5:.2f}s")
        print(f"  Expected (parallel): ~1-2s total")
    elif elapsed < 5.0:
        print("STATUS: PARTIAL (maybe parallel)")
        print(f"  Time per slide: {elapsed/5:.2f}s")
    else:
        print("STATUS: FAIL (likely sequential)")
        print(f"  Time per slide: {elapsed/5:.2f}s")
        print(f"  Expected (parallel): ~1-2s total")
        print(f"  Actual too slow - NOT truly parallel!")
    
    return elapsed < 3.0


if __name__ == "__main__":
    success = asyncio.run(test_parallel())
    exit(0 if success else 1)
