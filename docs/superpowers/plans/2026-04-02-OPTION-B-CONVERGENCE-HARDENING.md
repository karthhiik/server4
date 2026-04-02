# Option B: Convergence & Hardening Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` (recommended) or `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Unify Phase 1-2 accessibility and test stability before Phase 4, eliminating the "Swiss Cheese" product risk and ensuring solid data input pipelines.

**Strategy:**
1. **B1 (Test Hardening):** Fix SWOT/GTM test discovery and ensure all 60+ Phase 1-2 frontend tests run and pass
2. **B2 (A11y Convergence):** Apply Phase 3 WCAG 2.1 AA patterns to existing canvases (BusinessPlan, SWOT, GTM)
3. **B3 (Regression Verification):** Run full test suite (Phase 0-3) and confirm 100% stability

**Timeline:** 4-6 hours (parallel tasks possible for B1 and B2)

**Tech Stack:** Vitest, jest-axe, React 18, TypeScript 5, Framer Motion, shadcn/ui

---

## File Structure

### B1: Test Configuration & Imports
```
lliveupdatedstreaming/
├── vite.config.ts (modify: Vitest config)
├── vitest.setup.ts (modify or create: global test setup)
├── tests/
│   ├── integration/
│   │   ├── test_business_plan.tsx (modify: fix imports)
│   │   ├── test_swot_canvas.tsx (modify: fix imports)
│   │   ├── test_gtm_canvas.tsx (modify: fix imports)
│   │   └── ... (other tests)
│   └── unit/
│       └── ... (existing unit tests)
└── src/ (no changes, imports only)
```

### B2: Accessibility Retrofit
```
lliveupdatedstreaming/
├── src/features/intelligence/
│   ├── business-plan/BusinessPlanCanvas.tsx (modify: add role/aria-label)
│   ├── swot/SWOTCanvas.tsx (modify: add role/aria-label)
│   ├── gtm/GTMCanvas.tsx (modify: add role/aria-label)
│   └── pitch/PitchDeckCanvas.tsx (modify: add role/aria-label)
├── src/services/accessibility/a11yUtils.ts (existing - no changes)
└── tests/integration/
    └── test_accessibility_convergence.tsx (create: verify all canvases pass axe)
```

### B3: Regression Testing
```
tests/
├── Phase 0 (131 tests) ✅ existing
├── Phase 1 (60+ tests) - to be verified
├── Phase 2 (60+ tests) - to be verified (SWOT/GTM)
├── Phase 3 (44+ tests) ✅ existing
└── Combined: 300+ tests total
```

---

## Sub-Task B1: Test Discovery & SWOT/GTM Stability

### Context
The SWOT and GTM canvas test suites are not being discovered by Vitest. This is typically due to:
1. Wrong test file naming convention
2. Vitest glob pattern not matching test location
3. Missing `vitest.setup.ts` for global test environment config
4. Import path resolution issues (TypeScript `@/` aliases)

### Task B1.1: Audit Current Vitest Configuration

**Files:**
- Read: `vite.config.ts`
- Read: `package.json` (test script)
- Locate: `vitest.setup.ts` or `test.setup.ts`

**Steps:**

- [ ] **Step 1: Read vite.config.ts to check Vitest test pattern**

Run:
```bash
cd d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming && cat vite.config.ts | grep -A 10 "test:"
```

Expected: See Vitest config with `include` glob pattern. e.g., `include: ['tests/**/*.test.{ts,tsx}']`

If not found, this is the problem: Vitest test discovery may be too restrictive.

- [ ] **Step 2: Check test file naming convention in tests/integration/**

Run:
```bash
ls -la tests/integration/ | grep test_
```

Expected: See files like `test_3d_globe.tsx`, `test_scenario_engine.tsx`, etc.

**Note:** These use `test_` prefix, not `.test.` suffix. Check if vite.config.ts glob pattern matches this.

- [ ] **Step 3: Check for vitest.setup.ts**

Run:
```bash
find . -name "vitest.setup.ts" -o -name "test.setup.ts" -o -name "setupTests.ts"
```

If not found: We need to create one to set up global test environment (MSW, mocks, etc.)

- [ ] **Step 4: Verify TypeScript path alias resolution**

Run:
```bash
grep -r "alias" vite.config.ts
```

Expected: Should see `@/` or similar alias pointing to `src/`. Example:
```typescript
alias: {
  '@': fileURLToPath(new URL('./src', import.meta.url)),
}
```

If missing or wrong, tests cannot import from `@/components/`, etc.

---

### Task B1.2: Fix Vitest Configuration for Test Discovery

**Files:**
- Modify: `vite.config.ts`
- Create or Modify: `vitest.setup.ts`

**Steps:**

- [ ] **Step 1: Read current vite.config.ts**

Read entire file to understand current Vitest config structure.

- [ ] **Step 2: Ensure test glob pattern matches test file names**

Update `vite.config.ts` test config to include `test_*` naming:

```typescript
export default defineConfig({
  plugins: [react(), viteTsconfigPaths()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: ['./vitest.setup.ts'],
    include: ['tests/**/*.{test,spec}.{ts,tsx}', 'tests/**/test_*.{ts,tsx}'],
    exclude: ['node_modules', 'dist', '.idea', '.git', '.cache'],
    coverage: {
      provider: 'v8',
      reporter: ['text', 'json', 'html'],
    },
  },
});
```

Key changes:
- `setupFiles: ['./vitest.setup.ts']` - adds global setup
- `include` now matches both `.test.tsx` AND `test_*.tsx` patterns
- `globals: true` - use global test/describe/expect (Vitest 1.0+)
- `environment: 'jsdom'` - for React component testing

- [ ] **Step 3: Create vitest.setup.ts for global test environment**

Create `vitest.setup.ts` in project root:

```typescript
import { expect, afterEach, vi } from 'vitest';
import { cleanup } from '@testing-library/react';
import * as matchers from '@testing-library/jest-dom';

// Extend Vitest matchers with jest-dom matchers
expect.extend(matchers);

// Cleanup React component renders after each test
afterEach(() => {
  cleanup();
});

// Mock window.matchMedia for responsive design tests
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});

// Mock IntersectionObserver for lazy-load tests
global.IntersectionObserver = class IntersectionObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  takeRecords() {
    return [];
  }
  unobserve() {}
} as any;

// Mock ResizeObserver for Three.js canvas tests
global.ResizeObserver = class ResizeObserver {
  constructor() {}
  disconnect() {}
  observe() {}
  unobserve() {}
} as any;
```

- [ ] **Step 4: Verify alias in vite.config.ts**

Ensure TypeScript path alias is configured. Add if missing:

```typescript
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';
import viteTsconfigPaths from 'vite-tsconfig-paths';
import path from 'path';

export default defineConfig({
  plugins: [react(), viteTsconfigPaths()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  // ... rest of config
});
```

- [ ] **Step 5: Update package.json test script**

Ensure `package.json` has proper test command:

```json
{
  "scripts": {
    "test": "vitest",
    "test:ui": "vitest --ui",
    "test:coverage": "vitest --coverage"
  }
}
```

- [ ] **Step 6: Run Vitest in discovery mode to verify pattern matching**

Run:
```bash
cd d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming && npx vitest --listTests
```

Expected: Should list ALL test files, including:
```
tests/integration/test_3d_globe.tsx
tests/integration/test_scenario_engine.tsx
tests/integration/test_accessibility_compliance.tsx
tests/integration/test_swot_canvas.tsx
tests/integration/test_gtm_canvas.tsx
... (all test files)
```

If SWOT/GTM tests are missing, check their file paths and names.

- [ ] **Step 7: Commit test configuration fixes**

```bash
cd d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming && git add vite.config.ts vitest.setup.ts package.json && git commit -m "fix: update Vitest configuration for proper test discovery

- Add test_*.{ts,tsx} glob pattern to include
- Create vitest.setup.ts with global test environment
- Add jsdom environment, jest-dom matchers, window mocks
- Configure path aliases for @/ imports
- Ensure all Phase 1-2 tests discoverable and runnable

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task B1.3: Fix Imports in SWOT/GTM Test Files

**Files:**
- Modify: `tests/integration/test_swot_canvas.tsx`
- Modify: `tests/integration/test_gtm_canvas.tsx`
- Modify: `tests/integration/test_business_plan.tsx` (if exists)

**Steps:**

- [ ] **Step 1: Audit import paths in test files**

Check each test file for import statements. Look for:
- Relative paths like `../../src/features/...` (brittl, can break with file moves)
- Alias imports like `@/features/...` (better, uses vite alias)
- Wrong paths like `src/features/` without `@/`

Run:
```bash
grep -r "^import" tests/integration/test_swot_canvas.tsx | head -20
```

- [ ] **Step 2: Update test_swot_canvas.tsx imports**

Replace relative imports with alias imports. Example:

**Before:**
```typescript
import { SWOTCanvas } from '../../../src/features/intelligence/swot/SWOTCanvas';
import { render } from '@testing-library/react';
```

**After:**
```typescript
import { SWOTCanvas } from '@/features/intelligence/swot/SWOTCanvas';
import { render, screen } from '@testing-library/react';
```

Do the same for all relative `src/` imports → use `@/` alias.

- [ ] **Step 3: Update test_gtm_canvas.tsx imports**

Same as Step 2, replace relative imports with `@/` aliases:

```typescript
// ❌ WRONG (before)
import { GTMCanvas } from '../../../src/features/intelligence/gtm/GTMCanvas';

// ✅ RIGHT (after)
import { GTMCanvas } from '@/features/intelligence/gtm/GTMCanvas';
```

- [ ] **Step 4: Check for mock/MSW imports**

Ensure test setup includes Mock Service Worker for API calls:

```typescript
import { server } from '@/mocks/handlers';
import { beforeAll, afterEach, afterAll } from 'vitest';

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

If this is missing, add it to both test files.

- [ ] **Step 5: Run SWOT tests to verify discovery**

```bash
cd d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming && npx vitest tests/integration/test_swot_canvas.tsx --run --reporter=verbose
```

Expected: Tests run (pass or fail is OK at this point; discovery is the goal).

If "test file not found" or import errors, fix paths and retry.

- [ ] **Step 6: Run GTM tests to verify discovery**

```bash
cd d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming && npx vitest tests/integration/test_gtm_canvas.tsx --run --reporter=verbose
```

Expected: Tests run without "cannot find module" errors.

- [ ] **Step 7: Commit test import fixes**

```bash
cd d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming && git add tests/integration/test_*.tsx && git commit -m "fix: update test imports to use path aliases

- Replace relative paths with @/ alias imports
- Ensure SWOT and GTM test files discoverable
- Fix MSW/mock setup in test files
- Verify all 60+ Phase 1-2 tests run

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task B1.4: Run Phase 1-2 Test Suite & Fix Failures

**Files:**
- No files modified (diagnosis & fixes only)

**Steps:**

- [ ] **Step 1: Run full Phase 1-2 test suite**

```bash
cd d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming && npx vitest tests/integration/test_business_plan.tsx tests/integration/test_swot_canvas.tsx tests/integration/test_gtm_canvas.tsx --run
```

Expected: Some tests may fail (that's OK; we're discovering brittleness).

Capture output showing:
- Number of tests run
- Number passed/failed
- Specific error messages for any failures

- [ ] **Step 2: Diagnose test failures**

For each failing test, check:
1. **Render errors:** Are components not mounting? Check props.
2. **Assertion errors:** Are screen queries finding elements? Check selectors.
3. **Async issues:** Are tests awaiting async operations? Check waitFor usage.
4. **Mock errors:** Are API mocks set up correctly? Check MSW handlers.

- [ ] **Step 3: Fix each failing test**

For each test that fails:
1. Read the test code
2. Identify the root cause (missing mock, wrong selector, missing await, etc.)
3. Fix in the smallest way possible (TDD approach)
4. Run just that test to verify fix

Example failure fix:
```typescript
// ❌ WRONG (test failing because selector is wrong)
it('displays market data', () => {
  render(<BusinessPlanCanvas />);
  const marketData = screen.getByText('Market Size'); // Element doesn't exist
  expect(marketData).toBeInTheDocument();
});

// ✅ RIGHT (use actual element text or role query)
it('displays market data', () => {
  render(<BusinessPlanCanvas />);
  const marketData = screen.getByRole('heading', { name: /market size/i });
  expect(marketData).toBeInTheDocument();
});
```

- [ ] **Step 4: Commit test fixes (per fix, not batched)**

After each test fix:
```bash
git add tests/integration/test_<filename>.tsx && git commit -m "fix: resolve test assertion for <specific test name>"
```

This creates multiple small commits (one per fix) which is cleaner than one giant "fix all tests" commit.

- [ ] **Step 5: Verify all Phase 1-2 tests now pass**

```bash
cd d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming && npx vitest tests/integration/test_business_plan.tsx tests/integration/test_swot_canvas.tsx tests/integration/test_gtm_canvas.tsx --run
```

Expected: All tests PASS (60+ tests, 100% success rate)

- [ ] **Step 6: Final B1 commit**

Once all tests pass:
```bash
git add tests/ && git commit -m "test(b1): phase 1-2 test suite complete - 60+ tests passing

All SWOT, GTM, and BusinessPlan canvas tests now discoverable and passing.
Vitest configuration updated for proper test-_ pattern matching.
Path aliases (@/) resolve correctly across all test files.

Test coverage:
- BusinessPlanCanvas: X tests ✅
- SWOTCanvas: Y tests ✅
- GTMCanvas: Z tests ✅

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Sub-Task B2: Accessibility Retrofit (Apply Phase 3 Patterns)

### Context
Phase 3 created a WCAG 2.1 AA framework (`a11yUtils.ts`) and established patterns (role attributes, aria-label). Now apply these same patterns to existing Phase 1-2 canvases to eliminate the "Swiss Cheese" accessibility gap.

### Task B2.1: Add ARIA Labels & Role Attributes to BusinessPlanCanvas

**Files:**
- Modify: `src/features/intelligence/business-plan/BusinessPlanCanvas.tsx`

**Steps:**

- [ ] **Step 1: Read BusinessPlanCanvas to understand structure**

File should have:
- Main canvas container
- Navigation rail with view buttons (Summary, Strategy, Metrics, Report)
- Main content area
- Sidebar for intelligence

- [ ] **Step 2: Add role="application" and aria-label to root container**

Wrap the entire canvas in semantic landmarks:

```typescript
export const BusinessPlanCanvas = () => {
  return (
    <div
      className="business-plan-canvas"
      role="application"
      aria-label="Business Plan Canvas - Strategic business planning and strategy development tool"
    >
      {/* Existing content */}
    </div>
  );
};
```

- [ ] **Step 3: Add role="navigation" and aria-label to nav rail**

Find nav rail element and add semantic markup:

```typescript
<nav
  className="nav-rail"
  role="navigation"
  aria-label="Business Plan Canvas navigation - view selector"
>
  <button
    onClick={() => setActiveView('summary')}
    aria-current={activeView === 'summary' ? 'page' : undefined}
    aria-label="Executive Summary - Overview of company vision, mission, and key metrics"
    title="Executive Summary"
  >
    📊
  </button>
  <button
    onClick={() => setActiveView('strategy')}
    aria-current={activeView === 'strategy' ? 'page' : undefined}
    aria-label="Strategy Map - Visual representation of strategic initiatives and dependencies"
    title="Strategy Map"
  >
    🗺️
  </button>
  <button
    onClick={() => setActiveView('metrics')}
    aria-current={activeView === 'metrics' ? 'page' : undefined}
    aria-label="Metrics Dashboard - Key performance indicators and business metrics"
    title="Metrics Dashboard"
  >
    📈
  </button>
  <button
    onClick={() => setActiveView('report')}
    aria-current={activeView === 'report' ? 'page' : undefined}
    aria-label="Full Report - Comprehensive business plan document"
    title="Full Report"
  >
    📄
  </button>
</nav>
```

Key: Each button has `aria-current="page"` when active, and descriptive `aria-label` explaining what the view shows.

- [ ] **Step 4: Add role="main" to main content area**

```typescript
<main
  className="canvas-main"
  role="main"
  aria-label="Business Plan content"
>
  {/* Views render here */}
</main>
```

- [ ] **Step 5: Add role="complementary" to sidebar**

```typescript
<aside
  className="intelligence-sidebar"
  role="complementary"
  aria-label="Business intelligence sidebar - supporting data and analysis"
>
  {/* Sidebar content */}
</aside>
```

- [ ] **Step 6: Verify no axe violations**

Create quick test to verify:

```typescript
import { axe, toHaveNoViolations } from 'jest-axe';
expect.extend(toHaveNoViolations);

it('BusinessPlanCanvas has no accessibility violations', async () => {
  const { container } = render(<BusinessPlanCanvas planId="test" />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

Run:
```bash
npx vitest tests/integration/test_business_plan.tsx --run
```

Expected: axe test passes (0 violations)

- [ ] **Step 7: Commit B2.1**

```bash
git add src/features/intelligence/business-plan/BusinessPlanCanvas.tsx && git commit -m "a11y: add WCAG landmarks to BusinessPlanCanvas

- Add role='application' to root container
- Add role='navigation' with aria-label to nav rail
- Add aria-current='page' to active nav button
- Add role='main' to content area
- Add role='complementary' to sidebar
- All nav buttons have descriptive aria-label

Accessibility verified: jest-axe reports 0 violations.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task B2.2: Add ARIA Labels & Role Attributes to SWOTCanvas

**Files:**
- Modify: `src/features/intelligence/swot/SWOTCanvas.tsx`

**Steps:**

- [ ] **Step 1: Read SWOTCanvas to understand structure**

Similar structure to BusinessPlanCanvas:
- Main container
- Nav (Matrix, Analysis, Recommendations views)
- Main content
- Sidebar

- [ ] **Step 2: Apply same semantic landmarks**

```typescript
export const SWOTCanvas = () => {
  return (
    <div
      className="swot-canvas"
      role="application"
      aria-label="SWOT Analysis Canvas - Strategic strengths, weaknesses, opportunities, and threats analysis"
    >
      <nav
        className="nav-rail"
        role="navigation"
        aria-label="SWOT Analysis navigation"
      >
        <button
          onClick={() => setActiveView('matrix')}
          aria-current={activeView === 'matrix' ? 'page' : undefined}
          aria-label="SWOT Matrix - 2x2 grid showing strengths, weaknesses, opportunities, threats"
        >
          4️⃣
        </button>
        <button
          onClick={() => setActiveView('analysis')}
          aria-current={activeView === 'analysis' ? 'page' : undefined}
          aria-label="Detailed Analysis - In-depth assessment of each SWOT dimension"
        >
          🔍
        </button>
        <button
          onClick={() => setActiveView('recommendations')}
          aria-current={activeView === 'recommendations' ? 'page' : undefined}
          aria-label="Recommendations - Strategic insights and action items"
        >
          💡
        </button>
      </nav>

      <main className="canvas-main" role="main">
        {/* Views */}
      </main>

      <aside role="complementary" aria-label="SWOT analysis intelligence sidebar">
        {/* Sidebar */}
      </aside>
    </div>
  );
};
```

- [ ] **Step 3: Verify with jest-axe**

```bash
npx vitest tests/integration/test_swot_canvas.tsx --run
```

Expected: 0 violations

- [ ] **Step 4: Commit B2.2**

```bash
git add src/features/intelligence/swot/SWOTCanvas.tsx && git commit -m "a11y: add WCAG landmarks to SWOTCanvas

- Add semantic role and aria-label to container and nav
- Add aria-current='page' to active button
- Add role='main' and role='complementary' landmarks
- All buttons have descriptive aria-label

Accessibility verified: jest-axe reports 0 violations.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task B2.3: Add ARIA Labels & Role Attributes to GTMCanvas

**Files:**
- Modify: `src/features/intelligence/gtm/GTMCanvas.tsx`

**Steps:**

- [ ] **Step 1: Apply semantic landmarks to GTMCanvas**

```typescript
export const GTMCanvas = () => {
  return (
    <div
      className="gtm-canvas"
      role="application"
      aria-label="Go-to-Market Strategy Canvas - Market analysis and launch planning"
    >
      <nav
        className="nav-rail"
        role="navigation"
        aria-label="GTM Canvas navigation"
      >
        <button
          onClick={() => setActiveView('overview')}
          aria-current={activeView === 'overview' ? 'page' : undefined}
          aria-label="Market Overview - Market size, segments, and opportunity assessment"
        >
          🌍
        </button>
        <button
          onClick={() => setActiveView('channels')}
          aria-current={activeView === 'channels' ? 'page' : undefined}
          aria-label="Distribution Channels - Go-to-market channels and partnership strategy"
        >
          📡
        </button>
        <button
          onClick={() => setActiveView('metrics')}
          aria-current={activeView === 'metrics' ? 'page' : undefined}
          aria-label="Metrics & Scenarios - Key metrics and what-if scenario planning"
        >
          📊
        </button>
        <button
          onClick={() => setActiveView('timeline')}
          aria-current={activeView === 'timeline' ? 'page' : undefined}
          aria-label="Launch Timeline - Phased rollout and milestone schedule"
        >
          📅
        </button>
      </nav>

      <main className="canvas-main" role="main">
        {/* Views */}
      </main>

      <aside role="complementary" aria-label="GTM metrics and planning sidebar">
        {/* Sidebar with scenario sliders */}
      </aside>
    </div>
  );
};
```

- [ ] **Step 2: Verify with jest-axe**

```bash
npx vitest tests/integration/test_gtm_canvas.tsx --run
```

Expected: 0 violations

- [ ] **Step 3: Commit B2.3**

```bash
git add src/features/intelligence/gtm/GTMCanvas.tsx && git commit -m "a11y: add WCAG landmarks to GTMCanvas

- Add semantic role and aria-label to container and nav
- Add aria-current='page' to active button
- Add role='main' and role='complementary' landmarks
- All buttons have descriptive aria-label

Accessibility verified: jest-axe reports 0 violations.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task B2.4: Add ARIA Labels & Role Attributes to PitchDeckCanvas

**Files:**
- Modify: `src/features/intelligence/pitch/PitchDeckCanvas.tsx`

**Steps:**

- [ ] **Step 1: Apply semantic landmarks to PitchDeckCanvas**

```typescript
export const PitchDeckCanvas = () => {
  return (
    <div
      className="pitch-deck-canvas"
      role="application"
      aria-label="Pitch Deck Canvas - Investor presentation and storytelling"
    >
      <nav
        className="nav-rail"
        role="navigation"
        aria-label="Pitch Deck navigation"
      >
        <button
          onClick={() => setActiveSlide(0)}
          aria-current={activeSlide === 0 ? 'page' : undefined}
          aria-label="Cover Slide - Company name, logo, and tagline"
        >
          🎬
        </button>
        <button
          onClick={() => setActiveSlide(1)}
          aria-current={activeSlide === 1 ? 'page' : undefined}
          aria-label="Company Story - Mission, vision, and founding story"
        >
          📖
        </button>
        <button
          onClick={() => setActiveSlide(2)}
          aria-current={activeSlide === 2 ? 'page' : undefined}
          aria-label="Market Opportunity - TAM, SAM, market trends"
        >
          🎯
        </button>
        <button
          onClick={() => setActiveSlide(3)}
          aria-current={activeSlide === 3 ? 'page' : undefined}
          aria-label="Solution & Product - How we solve the problem"
        >
          💡
        </button>
        <button
          onClick={() => setActiveSlide(4)}
          aria-current={activeSlide === 4 ? 'page' : undefined}
          aria-label="The Ask - Funding request and use of funds"
        >
          💰
        </button>
      </nav>

      <main className="canvas-main" role="main">
        {/* Slides render here */}
      </main>

      <aside role="complementary" aria-label="Pitch deck presentation sidebar">
        {/* Notes, animations, timing sidebar */}
      </aside>
    </div>
  );
};
```

- [ ] **Step 2: Verify with jest-axe**

```bash
npx vitest tests/integration/test_pitch_deck.tsx --run
```

Expected: 0 violations

- [ ] **Step 3: Commit B2.4**

```bash
git add src/features/intelligence/pitch/PitchDeckCanvas.tsx && git commit -m "a11y: add WCAG landmarks to PitchDeckCanvas

- Add semantic role and aria-label to container and nav
- Add aria-current='page' to active button
- Add role='main' and role='complementary' landmarks
- All buttons have descriptive aria-label (cover, story, market, solution, ask)

Accessibility verified: jest-axe reports 0 violations.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task B2.5: Create Comprehensive Accessibility Convergence Test

**Files:**
- Create: `tests/integration/test_accessibility_convergence.tsx`

**Steps:**

- [ ] **Step 1: Write comprehensive accessibility test**

```typescript
/**
 * Accessibility Convergence Test
 * Verifies all canvases (Phase 1-4) meet WCAG 2.1 AA standards
 */

import { render } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import { BusinessPlanCanvas } from '@/features/intelligence/business-plan/BusinessPlanCanvas';
import { SWOTCanvas } from '@/features/intelligence/swot/SWOTCanvas';
import { GTMCanvas } from '@/features/intelligence/gtm/GTMCanvas';
import { PitchDeckCanvas } from '@/features/intelligence/pitch/PitchDeckCanvas';

expect.extend(toHaveNoViolations);

describe('Accessibility Convergence - All Canvases WCAG 2.1 AA Compliant', () => {
  it('BusinessPlanCanvas has zero axe violations', async () => {
    const { container } = render(<BusinessPlanCanvas planId="test-123" />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('SWOTCanvas has zero axe violations', async () => {
    const { container } = render(<SWOTCanvas swotId="swot-123" />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('GTMCanvas has zero axe violations', async () => {
    const { container } = render(<GTMCanvas gtmId="gtm-123" />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('PitchDeckCanvas has zero axe violations', async () => {
    const { container } = render(<PitchDeckCanvas deckId="pitch-123" />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  describe('Semantic Landmarks Present', () => {
    const canvases = [
      { Component: BusinessPlanCanvas, props: { planId: 'test' }, name: 'BusinessPlan' },
      { Component: SWOTCanvas, props: { swotId: 'test' }, name: 'SWOT' },
      { Component: GTMCanvas, props: { gtmId: 'test' }, name: 'GTM' },
      { Component: PitchDeckCanvas, props: { deckId: 'test' }, name: 'PitchDeck' },
    ];

    canvases.forEach(({ Component, props, name }) => {
      it(`${name}Canvas has role='application'`, () => {
        const { container } = render(<Component {...props} />);
        const appElement = container.querySelector('[role="application"]');
        expect(appElement).toBeInTheDocument();
        expect(appElement).toHaveAttribute('aria-label');
      });

      it(`${name}Canvas has role='navigation'`, () => {
        const { container } = render(<Component {...props} />);
        const nav = container.querySelector('[role="navigation"]');
        expect(nav).toBeInTheDocument();
        expect(nav).toHaveAttribute('aria-label');
      });

      it(`${name}Canvas has role='main'`, () => {
        const { container } = render(<Component {...props} />);
        const main = container.querySelector('[role="main"]');
        expect(main).toBeInTheDocument();
      });

      it(`${name}Canvas has role='complementary'`, () => {
        const { container } = render(<Component {...props} />);
        const aside = container.querySelector('[role="complementary"]');
        expect(aside).toBeInTheDocument();
        expect(aside).toHaveAttribute('aria-label');
      });
    });
  });

  describe('Navigation Button Accessibility', () => {
    it('active nav button has aria-current="page"', () => {
      const { container } = render(<BusinessPlanCanvas planId="test" />);
      const activeButton = container.querySelector('[aria-current="page"]');
      expect(activeButton).toBeInTheDocument();
      expect(activeButton).toHaveAttribute('aria-label');
    });

    it('all nav buttons have aria-label', () => {
      const { container } = render(<BusinessPlanCanvas planId="test" />);
      const navButtons = container.querySelectorAll('nav [role="button"], nav button');
      expect(navButtons.length).toBeGreaterThan(0);
      navButtons.forEach(button => {
        expect(button).toHaveAttribute('aria-label');
      });
    });
  });
});
```

- [ ] **Step 2: Run convergence test**

```bash
cd d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming && npx vitest tests/integration/test_accessibility_convergence.tsx --run
```

Expected: All tests pass (4 axe tests + semantic landmark tests)

If any test fails:
1. Check the specific canvas for missing role/aria-label
2. Refer back to Tasks B2.1-B2.4 to add missing attributes
3. Re-run until all tests pass

- [ ] **Step 3: Commit convergence test**

```bash
git add tests/integration/test_accessibility_convergence.tsx && git commit -m "test(b2): accessibility convergence verification

Create comprehensive test suite verifying all canvases meet WCAG 2.1 AA standards:
- BusinessPlanCanvas ✅
- SWOTCanvas ✅
- GTMCanvas ✅
- PitchDeckCanvas ✅

Tests verify:
- Zero axe violations per canvas
- All semantic landmarks present (application, navigation, main, complementary)
- All nav buttons have aria-label and aria-current tracking
- Proper accessibility attributes throughout

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Sub-Task B3: Full Regression Test Suite (Phase 0-3)

### Context
Verify that all 300+ tests from Phase 0, 1, 2, and 3 pass together. This ensures no cross-task breakage and confirms the unified, stable foundation for Phase 4.

### Task B3.1: Run Full Phase 0-3 Test Suite

**Files:**
- No files modified (verification only)

**Steps:**

- [ ] **Step 1: Run ALL tests (Phase 0-3)**

```bash
cd d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming && npx vitest --run 2>&1 | tee test-results.log
```

This runs the entire test suite. Capture output.

Expected output (approximate):
```
✓ Tests:  300+ passed
✓ Duration: X seconds
✓ Coverage: Y%
```

- [ ] **Step 2: Verify specific test counts**

After running, check specific tag/pattern counts:

```bash
# Count Phase 0 tests
npx vitest --listTests | grep -c "phase0\|Phase 0" || echo "Phase 0: embedded in monorepo"

# Count Phase 1 tests
npx vitest --listTests | grep -c "test_business_plan"

# Count Phase 2 tests
npx vitest --listTests | grep -c "test_swot\|test_gtm"

# Count Phase 3 tests
npx vitest --listTests | grep -c "test_3d_globe\|test_scenario\|test_accessibility\|test_multiplayer"
```

- [ ] **Step 3: Check for any failures or warnings**

```bash
grep -i "fail\|error\|warn" test-results.log | head -20
```

Expected: Minimal warnings (if any), zero failures.

If failures found:
1. Identify which test is failing
2. Run just that test for details: `npx vitest tests/integration/test_<name>.tsx --run`
3. Fix the issue (usually due to missing setup or mock)
4. Re-run full suite

- [ ] **Step 4: Generate test coverage report**

```bash
cd d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming && npx vitest --coverage --run
```

Expected: Coverage report shows lines/functions/branches coverage for:
- src/features/intelligence/
- src/services/
- src/hooks/

Note: Phase 0 tests likely in separate monorepo; this covers lliveupdatedstreaming frontend.

- [ ] **Step 5: Verify specific Phase 3 components have good coverage**

Run coverage-specific filter:

```bash
npx vitest --coverage --run --include="tests/integration/test_3d_globe.tsx,tests/integration/test_scenario_engine.tsx,tests/integration/test_accessibility_compliance.tsx,tests/integration/test_multiplayer_stubs.tsx"
```

Expected:
- GlobeRenderer: >80% coverage
- useScenarios hook: >85% coverage
- a11yUtils: >90% coverage
- presenceService: >80% coverage

- [ ] **Step 6: Document test results**

Create `TEST_RESULTS_B3.md` in project root:

```markdown
# Phase 0-3 Regression Test Results
**Date:** 2026-04-02
**Scope:** Full test suite (Phase 0-3)

## Summary
- ✅ Total Tests: 300+
- ✅ Passed: 300+
- ❌ Failed: 0
- ⚠️ Warnings: X (minor)

## By Phase
- Phase 0: 131 tests ✅
- Phase 1: 60+ tests ✅
- Phase 2: 60+ tests ✅ (SWOT/GTM fixed)
- Phase 3: 44+ tests ✅

## Key Metrics
- Execution Time: X seconds
- Coverage: Y%
- No broken imports
- No memory leaks detected
- All mocks properly cleaned up

## Regression Status
✅ **PASSED** - No regressions detected. All phases stable.
```

- [ ] **Step 7: Generate final B3 commit**

Once all tests pass and coverage is acceptable:

```bash
cd d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming && git add . && git commit -m "test(b3): phase 0-3 regression verification complete

Full test suite (300+ tests) executed successfully:
✅ Phase 0: 131 tests passing (monorepo)
✅ Phase 1: 60+ tests passing (BusinessPlan canvas)
✅ Phase 2: 60+ tests passing (SWOT/GTM canvases - fixed)
✅ Phase 3: 44+ tests passing (3D Globe, Scenarios, A11y, Multiplayer)

Regression analysis:
✅ No import failures
✅ No breaking changes between phases
✅ All accessibility tests passing (jest-axe 0 violations)
✅ All mocks properly isolated
✅ No memory leaks detected
✅ Code coverage acceptable (>80% on new Phase 3 components)

Foundation Status: STABLE ✅
Ready for Phase 4: YES ✅

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Option B Completion Criteria

All sub-tasks complete when:

✅ **B1 Complete:**
- Vitest configuration updated (test glob, setupFiles)
- All SWOT/GTM test imports use `@/` aliases
- 60+ Phase 1-2 tests discoverable and passing
- Commit: `fix: update Vitest configuration for proper test discovery`
- Commit: `fix: update test imports to use path aliases`

✅ **B2 Complete:**
- All 4 canvases have semantic landmarks (role, aria-label, aria-current)
- jest-axe reports 0 violations per canvas
- Convergence test verifies all canvases pass
- Commits: One per canvas + convergence test

✅ **B3 Complete:**
- Full regression test suite runs (300+ tests)
- All Phase 0-3 tests passing (100%)
- Coverage report acceptable (>80% Phase 3 components)
- No regressions detected
- Final commit: `test(b3): phase 0-3 regression verification complete`

---

## Files Summary

### Created
- `vitest.setup.ts` - Global test setup with mocks
- `tests/integration/test_accessibility_convergence.tsx` - Unified A11y verification

### Modified
- `vite.config.ts` - Test glob pattern + path aliases
- `package.json` - Test scripts (if needed)
- `tests/integration/test_*.tsx` - Import path fixes
- `src/features/intelligence/business-plan/BusinessPlanCanvas.tsx` - A11y landmarks
- `src/features/intelligence/swot/SWOTCanvas.tsx` - A11y landmarks
- `src/features/intelligence/gtm/GTMCanvas.tsx` - A11y landmarks
- `src/features/intelligence/pitch/PitchDeckCanvas.tsx` - A11y landmarks

### Not Modified (Existing)
- `src/services/accessibility/a11yUtils.ts` - Already complete from Phase 3
- `src/services/multiplayer/presenceService.ts` - Already complete from Phase 3

---

## Risk Mitigation

**Risk:** Test fixes introduce new failures
**Mitigation:** Run tests after each fix; commit frequently; use `--run` flag

**Risk:** Accessibility retrofit breaks existing functionality
**Mitigation:** Test layout/rendering hasn't changed; only added attributes; verify with jest-axe

**Risk:** Full regression takes too long
**Mitigation:** Run in parallel if possible; can skip Phase 0 if in separate monorepo

---

## Timeline Estimate

| Task | Time | Notes |
|------|------|-------|
| B1.1 - Audit Vitest | 15 min | Read configs |
| B1.2 - Fix Vite config | 20 min | Update vitest.setup.ts |
| B1.3 - Fix test imports | 30 min | Update 3+ test files |
| B1.4 - Fix test failures | 45 min | Depends on current state |
| **B1 Total** | **1.75 hrs** | |
| B2.1-B2.4 - A11y retrofit | 90 min | 4 canvases × ~15 min each + test |
| B2.5 - Convergence test | 20 min | Write + run |
| **B2 Total** | **1.75 hrs** | |
| B3.1 - Full regression | 60 min | Run suite + debug + results |
| **B3 Total** | **1 hr** | |
| **Grand Total** | **4.5 hrs** | Within 4-6 hour target |

---

## Success Definition

Option B is **complete and successful** when:

✅ All SWOT/GTM tests discoverable and passing (B1)
✅ All 4 canvases meet WCAG 2.1 AA (jest-axe 0 violations) (B2)
✅ Full regression test suite passes (300+ tests) (B3)
✅ No regressions between phases
✅ Unified, accessible, stable foundation established
✅ Phase 4 can proceed with confidence

**Final Status:** Option B transforms Phase 3's "Polish & Advanced Features" from isolated improvements into a **cohesive, accessible, production-hardened system** that's ready for the Pitch Deck (Phase 4) without the "Swiss Cheese" accessibility gap.

---

## Next Steps After Completion

Once Option B is complete:

1. **Proceed to Phase 4** - Pitch Deck Canvas Polish & Enhancements
   - Enhanced slide generation
   - Data visualization improvements
   - Export to PDF/PowerPoint
   - Presentation mode

2. **Phase 4 Benefits from Option B:**
   - Can reuse exact A11y patterns from Phase 1-2 (no reinvention)
   - All data input pipelines (SWOT, GTM) are stable and tested
   - No regressions risk (full test suite passing)
   - Cohesive, professional-grade system

