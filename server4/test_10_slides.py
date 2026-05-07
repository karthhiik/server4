"""
Real-World Standard Mode Test — 10 Slides (No Model Loading).
Tests actual generation speed after models are cached.
"""
import asyncio
import time

async def test_10_slides():
    print("=" * 60)
    print("REAL-WORLD TEST: 10 Slides (Cached Models)")
    print("=" * 60)
    print(f"Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    from app.services.v4.content_pipeline import V4ContentPipeline
    from app.services.input_analyzer import InputAnalyzer
    from app.models.generation_input_v4 import GenerationInputV4, StandardGenerationInput
    
    # Rich prompt (should skip questions)
    prompt = (
        "Acme AI is a hiring platform for SaaS companies. "
        "We have $2M ARR, 500 customers, 25% YoY growth. "
        "Raising $5M Series A led by a16z. "
        "Founders: Jane Doe (CEO, ex-Google PM), John Smith (CTO, MIT CS). "
        "Competitors: Lever, Greenhouse. Our AI cuts time-to-hire by 60%."
    )
    
    print("Input Prompt:")
    print(f"  {prompt[:80]}...")
    print(f"  Length: {len(prompt)} chars")
    print()
    
    # Analyze
    print("Step 1: Analyzing prompt...")
    analyzer = InputAnalyzer()
    input_v4 = GenerationInputV4(
        mode='standard',
        standard_input=StandardGenerationInput(
            prompt=prompt,
            slide_count=10
        )
    )
    analysis = await analyzer.analyze(input_v4)
    
    print(f"  Purpose: {analysis.detected_purpose}")
    print(f"  Richness score: {analysis.input_richness_score:.2f}")
    print(f"  Questions to ask: {len(analysis.missing_context)} (should be 0)")
    print()
    
    # Generate (this is the real test)
    print("Step 2: Running V4 Content Pipeline...")
    print("=" * 60)
    start = time.perf_counter()
    
    pipeline = V4ContentPipeline()
    result = await pipeline.generate(
        project_id='test-10-slides',
        user_id='dev-test-user',
        user_query=prompt,
        analysis=analysis.model_dump(),
        mode='standard',
        purpose=analysis.detected_purpose.value,
        industry=analysis.detected_industry,
        company_name=analysis.detected_company_name,
        target_slide_count=10,
        structured_context={},
    )
    
    end = time.perf_counter()
    elapsed = end - start
    print("=" * 60)
    print("RESULTS:")
    print(f"  Total time: {elapsed:.2f}s")
    print(f"  Target: <10s for 10 slides")
    print(f"  Status: {'PASS' if elapsed < 10 else 'FAIL'} (target <10s)")
    print()
    print(f"  Project ID: {result.project_id}")
    print(f"  Deck title: {result.deck_title}")
    print(f"  Slides generated: {len(result.slides)}")
    print(f"  Target: 10 slides")
    print(f"  Status: {'PASS' if len(result.slides) == 10 else 'FAIL'} (slide count)")
    print(f"  Narrative arc: {result.narrative_arc}")
    print(f"  Research citations: {len(result.research.citations)}")
    print(f"  Duration (pipeline): {result.duration_ms}ms")
    print()
    
    # Content quality
    print("CONTENT QUALITY:")
    slides_with_headlines = sum(1 for s in result.slides if hasattr(s, 'headline') and s.headline and len(s.headline) > 10)
    print(f"  Slides with headlines: {slides_with_headlines}/{len(result.slides)}")
    print(f"  Status: {'PASS' if slides_with_headlines >= 8 else 'FAIL'} (>=8)")
    
    slides_with_content = sum(1 for s in result.slides if hasattr(s, 'body') and s.body and len(s.body) > 100)
    print(f"  Slides with content: {slides_with_content}/{len(result.slides)}")
    print(f"  Status: {'PASS' if slides_with_content >= 8 else 'FAIL'} (>=8)")
    print()
    
    # Show sample headlines
    print("SAMPLE SLIDE HEADLINES:")
    for i, slide in enumerate(result.slides[:5]):
        if hasattr(slide, 'headline'):
            headline = slide.headline[:60] if slide.headline else "(no headline)"
            print(f"  Slide {i+1}: {headline}...")
    if len(result.slides) > 5:
        print(f"  ... and {len(result.slides) - 5} more slides")
    print()
    
    # Summary
    print("=" * 60)
    print("SUMMARY:")
    time_pass = elapsed < 10
    count_pass = len(result.slides) == 10
    quality_pass = slides_with_headlines >= 8 and slides_with_content >= 8
    
    print(f"  Timing: {'PASS' if time_pass else 'FAIL'} ({elapsed:.2f}s < 10s)")
    print(f"  Slide Count: {'PASS' if count_pass else 'FAIL'} ({len(result.slides)} == 10)")
    print(f"  Content Quality: {'PASS' if quality_pass else 'FAIL'} (headlines + content)")
    print()
    
    overall = "PASS" if (time_pass and count_pass and quality_pass) else "FAIL"
    print(f"  OVERALL: {overall}")
    print("=" * 60)
    
    return overall == "PASS"


if __name__ == "__main__":
    success = asyncio.run(test_10_slides())
    exit(0 if success else 1)
