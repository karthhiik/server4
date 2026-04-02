#!/bin/bash
cd /d/Desktop/New_Flask/FLASK/lliveupdatedstreaming
git add src/features/intelligence/types/business-plan.ts
git add src/features/intelligence/components/BusinessPlanInput.tsx
git add src/features/intelligence/components/__tests__/test_business_plan_input.tsx
git add vitest.config.ts
git add package.json
git commit -m "feat: implement BusinessPlanInput page with 8-section form

- Add business-plan.ts types file with comprehensive interfaces
  - BusinessPlan: main artifact with id, user_id, company_name, sections, metrics
  - BusinessPlanSection: section data with citations and confidence levels
  - BusinessMetrics: revenue, CAC, LTV, burn rate, runway
  - StrategyNodeData: strategic elements with confidence scoring
  - CitationReference: source tracking with snippets
  - VisualizationSpec: chart/graph configuration
  - BusinessPlanFormData: complete form input structure

- Create BusinessPlanInput.tsx component
  - 8-section form: Company, Problem, Solution, Market, Business Model, GTM, Competitive, Financial
  - Each section includes required and optional fields with validation
  - Integrated with DualModeInput shell component
  - handleGenerate function calls /api/generate-business-plan
  - Navigation to canvas page on successful generation
  - Error handling and authentication checks
  - Toast notifications for user feedback

- Set up Vitest testing framework
  - Add vitest, @testing-library/react, happy-dom dev dependencies
  - Create vitest.config.ts with happy-dom environment
  - Add test script to package.json

- Create comprehensive test suite (38+ tests)
  - Tests for all 8 form sections
  - Validation of required fields
  - Form field types and options
  - Section descriptions and metadata
  - Integration with DualModeInput
  - API and navigation mocking

All tests are ready to run with: npm test"
