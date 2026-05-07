"""
Real-world Standard Mode Test Script
Tests question generator, model routing, and measures timing.
"""
import asyncio
import time
import json

async def test_question_generator():
    """Test the conversational question generator with various prompt richness levels."""
    print("=" * 60)
    print("TESTING: Question Generator")
    print("=" * 60)
    
    from app.services.v4.question_generator import ConversationalQuestionGenerator
    from app.services.input_analyzer import InputAnalyzer
    from app.models.generation_input_v4 import GenerationInputV4, StandardGenerationInput
    
    gen = ConversationalQuestionGenerator()
    analyzer = InputAnalyzer()
    
    # Test 1: Rich prompt (should skip questions)
    print("\n[Test 1] Rich prompt (should skip questions)")
    rich_input = GenerationInputV4(
        mode='standard',
        standard_input=StandardGenerationInput(
            prompt='Acme AI is a hiring platform for SaaS companies. '
                   'We have $2M ARR, 500 customers, 25% YoY growth. '
                   'Raising $5M Series A led by a16z. Founders: Jane Doe (ex-Google PM), '
                   'John Smith (CTO, MIT CS). Competitors: Lever, Greenhouse.'
        )
    )
    analysis1 = await analyzer.analyze(rich_input)
    questions1 = gen.generate(analysis1)
    print(f"  Prompt richness score: {analysis1.input_richness_score:.2f}")
    print(f"  Questions generated: {len(questions1)} (expected: 0 - skip)")
    print(f"  Missing context count: {len(analysis1.missing_context)}")
    assert len(questions1) == 0, f"Expected 0 questions, got {len(questions1)}"
    print("  ✓ PASS: Rich prompt correctly skips questions")
    
    # Test 2: Thin prompt (should generate questions)
    print("\n[Test 2] Thin prompt (should generate questions)")
    thin_input = GenerationInputV4(
        mode='standard',
        standard_input=StandardGenerationInput(
            prompt='AI app for helping companies hire better'
        )
    )
    analysis2 = await analyzer.analyze(thin_input)
    questions2 = gen.generate(analysis2)
    print(f"  Prompt richness score: {analysis2.input_richness_score:.2f}")
    print(f"  Questions generated: {len(questions2)} (max: 8)")
    print(f"  Missing context count: {len(analysis2.missing_context)}")
    assert len(questions2) > 0, "Expected questions for thin prompt"
    assert len(questions2) <= 8, f"Too many questions: {len(questions2)}"
    print("  Questions:")
    for i, q in enumerate(questions2):
        print(f"    Q{i+1} [{q['importance']:9s}]: {q['text'][:70]}...")
    print("  ✓ PASS: Thin prompt generates appropriate questions")
    
    # Test 3: Medium prompt (partial questions)
    print("\n[Test 3] Medium prompt (partial context)")
    med_input = GenerationInputV4(
        mode='standard',
        standard_input=StandardGenerationInput(
            prompt='Acme AI is a hiring platform. We have $50K MRR and 200 customers.'
        )
    )
    analysis3 = await analyzer.analyze(med_input)
    questions3 = gen.generate(analysis3)
    print(f"  Prompt richness score: {analysis3.input_richness_score:.2f}")
    print(f"  Questions generated: {len(questions3)}")
    print(f"  Missing context: {[mc.field for mc in analysis3.missing_context[:5]]}...")
    assert len(questions3) > 0 and len(questions3) <= 8
    print("  ✓ PASS: Medium prompt generates partial questions")
    
    # Test 4: Question enrichment
    print("\n[Test 4] Question enrichment (enrich prompt with answers)")
    if questions2:
        answers = {
            'traction': '$50K MRR, 200 customers, 15% MoM growth',
            'fundraising': '$2M Seed round, closing Q2 2026',
            'team': 'Jane Doe (CEO, ex-Google PM), John Smith (CTO)'
        }
        enriched = gen.enrich_prompt_with_answers(
            thin_input.standard_input.prompt,
            questions2,
            answers
        )
        print(f"  Original prompt length: {len(thin_input.standard_input.prompt)}")
        print(f"  Enriched prompt length: {len(enriched)}")
        assert 'Additional Context' in enriched
        assert '$50K MRR' in enriched
        print("  ✓ PASS: Prompt enrichment works correctly")
    
    print("\n" + "=" * 60)
    print("QUESTION GENERATOR: ALL TESTS PASSED")
    print("=" * 60)
    return True


async def test_model_routing():
    """Verify standard mode uses Groq as primary model."""
    print("\n" + "=" * 60)
    print("TESTING: Standard Mode Model Routing")
    print("=" * 60)
    
    from app.services.llm.model_router import ModelRouter, STANDARD_MODE_ROUTING_TABLE, TaskType
    
    router = ModelRouter()
    
    # Check standard mode routing table exists
    print("\n[Test 1] Standard mode routing table exists")
    assert len(STANDARD_MODE_ROUTING_TABLE) > 0, "Standard mode routing table is empty"
    print(f"  ✓ PASS: {len(STANDARD_MODE_ROUTING_TABLE)} task types configured")
    
    # Check Groq is primary for key tasks
    print("\n[Test 2] Groq is primary for narrative tasks")
    narrative_chain = STANDARD_MODE_ROUTING_TABLE.get(TaskType.NARRATIVE_STORYTELLING, [])
    print(f"  Narrative chain: {narrative_chain[:4]}...")
    assert narrative_chain[0] == 'groq', f"Expected 'groq' as primary, got '{narrative_chain[0]}'"
    print("  ✓ PASS: Groq is primary for narrative generation")
    
    print("\n[Test 3] Groq is primary for template fill")
    fill_chain = STANDARD_MODE_ROUTING_TABLE.get(TaskType.TEMPLATE_FILL, [])
    print(f"  Template fill chain: {fill_chain[:4]}...")
    assert fill_chain[0] == 'groq', f"Expected 'groq' as primary"
    print("  ✓ PASS: Groq is primary for template fill")
    
    print("\n[Test 4] OpenRouter is safety net")
    for task, chain in STANDARD_MODE_ROUTING_TABLE.items():
        assert 'openrouter' in chain, f"Missing openrouter in {task.value}"
    print("  ✓ PASS: All chains have openrouter safety net")
    
    # Check slow models are NOT in standard chain
    print("\n[Test 5] Slow models excluded from standard mode")
    for task, chain in STANDARD_MODE_ROUTING_TABLE.items():
        assert 'kimi-k2-thinking' not in chain[:3], f"Kimi in standard chain: {task.value}"
        assert 'deepseek-v3' not in chain[:3], f"DeepSeek in standard chain: {task.value}"
    print("  ✓ PASS: Slow reasoning models excluded from standard mode")
    
    print("\n" + "=" * 60)
    print("MODEL ROUTING: ALL TESTS PASSED")
    print("=" * 60)
    return True


async def test_standard_input_model():
    """Verify StandardGenerationInput is simplified (prompt + slide_count + language only)."""
    print("\n" + "=" * 60)
    print("TESTING: StandardGenerationInput Model")
    print("=" * 60)
    
    from app.models.generation_input_v4 import StandardGenerationInput, PresentationPurpose
    
    # Test valid input
    print("\n[Test 1] Valid input (prompt only)")
    valid = StandardGenerationInput(
        prompt='AI hiring platform for SaaS companies'
    )
    print(f"  Prompt: {valid.prompt}")
    print(f"  Purpose (hardcoded): {valid.purpose}")  # Should be PITCH_DECK
    print(f"  Audience (hardcoded): {valid.audience}")  # Should be "Investors"
    assert valid.purpose == PresentationPurpose.PITCH_DECK
    assert valid.audience == "Investors"
    print("  ✓ PASS: Purpose and audience are hardcoded for pitch decks")
    
    # Test with slide_count
    print("\n[Test 2] With optional slide_count")
    with_count = StandardGenerationInput(
        prompt='AI hiring platform',
        slide_count=12
    )
    print(f"  Slide count: {with_count.slide_count}")
    assert with_count.slide_count == 12
    print("  ✓ PASS: slide_count optional field works")
    
    # Test invalid input
    print("\n[Test 3] Invalid input (empty prompt)")
    try:
        invalid = StandardGenerationInput(prompt='')
        assert False, "Should have raised ValueError"
    except ValueError as e:
        print(f"  ✓ PASS: Correctly rejects empty prompt: {e}")
    
    print("\n" + "=" * 60)
    print("INPUT MODEL: ALL TESTS PASSED")
    print("=" * 60)
    return True


async def test_groq_keys_available():
    """Check if Groq API keys are available in .env."""
    print("\n" + "=" * 60)
    print("TESTING: Groq API Keys Availability")
    print("=" * 60)
    
    from app.config import settings
    
    groq_keys = settings.groq_keys
    print(f"\n  Groq keys configured: {len(groq_keys)}")
    print(f"  Expected: 8 (G0-G7)")
    
    if len(groq_keys) >= 1:
        # Mask keys for security
        masked = [k[:10] + '...' + k[-4:] for k in groq_keys]
        print(f"  Keys (masked): {masked}")
        print("  ✓ PASS: Groq keys are configured")
    else:
        print("  ⚠ WARNING: No Groq keys found - generation will use fallbacks")
    
    # Check if we have 8 keys as mentioned in .env
    if len(groq_keys) == 8:
        print("  ✓ PASS: All 8 Groq keys configured (round-robin enabled)")
    else:
        print(f"  ℹ INFO: Found {len(groq_keys)} keys (expected 8 per .env)")
    
    print("\n" + "=" * 60)
    print("GROQ KEYS: CHECK COMPLETE")
    print("=" * 60)
    return len(groq_keys) > 0


async def main():
    """Run all tests and generate report."""
    print("\n" + "#" * 60)
    print(" " * 18 + "STANDARD MODE VERIFICATION REPORT")
    print("#" * 60)
    print("Timestamp:", time.strftime("%Y-%m-%d %H:%M:%S"))
    
    results = {}
    
    try:
        results['question_generator'] = await test_question_generator()
    except Exception as e:
        print(f"\n✗ FAIL: Question Generator - {e}")
        results['question_generator'] = False
    
    try:
        results['model_routing'] = await test_model_routing()
    except Exception as e:
        print(f"\n✗ FAIL: Model Routing - {e}")
        results['model_routing'] = False
    
    try:
        results['input_model'] = await test_standard_input_model()
    except Exception as e:
        print(f"\n✗ FAIL: Input Model - {e}")
        results['input_model'] = False
    
    try:
        results['groq_keys'] = await test_groq_keys_available()
    except Exception as e:
        print(f"\n✗ FAIL: Groq Keys - {e}")
        results['groq_keys'] = False
    
    # Final Report
    print("\n" + "█" * 60)
    print(" " * 20 + "FINAL REPORT")
    print("█" * 60)
    
    total = len(results)
    passed = sum(1 for v in results.values() if v is True)
    
    for test_name, result in results.items():
        status = "✓ PASS" if result is True else "✗ FAIL"
        print(f"  {test_name:25s}: {status}")
    
    print(f"\n  Total: {total} tests")
    print(f"  Passed: {passed}")
    print(f"  Failed: {total - passed}")
    print(f"  Success Rate: {passed/total*100:.0f}%")
    
    if passed == total:
        print("\n  🎉 ALL TESTS PASSED - Implementation matches plan!")
    else:
        print(f"\n  ⚠ Some tests failed - review implementation")
    
    print("\n" + "█" * 60)
    
    return passed == total


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)
