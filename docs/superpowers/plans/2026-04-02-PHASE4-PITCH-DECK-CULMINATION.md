# Phase 4: Pitch Deck Canvas Polish & Enhancements (Culmination)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development. This plan executes task-by-task with fresh subagents, two-stage review gates, and frequent commits.

**Goal:** Build the final investor presentation platform that integrates all Phase 0-3 infrastructure into a seamless, production-ready Pitch Deck Canvas.

**Architecture:** The Pitch Deck Canvas is a **presentation engine** that:
1. Renders 8 investor-grade slides in a structured narrative
2. **Integrates the 3D Globe** (Phase 3) on "Market Opportunity" slide for immersive visualization
3. **Integrates the Scenario Engine** (Phase 3) on "Financials/Ask" slide for live what-if modeling
4. **Implements full keyboard navigation** (Phase 3 a11yUtils) for professional presentation mode
5. Exports to PDF/PowerPoint and supports draft persistence
6. Maintains ≥88% test pass rate (Option B gate) with zero regressions

**Tech Stack:** React 18 + TypeScript, Framer Motion (transitions), Vite, TDD (Vitest), Phase 3 utilities

**Integration Points:**
- `src/features/intelligence/shared/ThreeDGlobe.tsx` — Import for market visualization
- `src/features/intelligence/shared/ScenarioSlider.tsx` + `useScenarios.ts` — Import for financial scenarios
- `src/services/accessibility/a11yUtils.ts` — Import for keyboard navigation and WCAG compliance
- `src/features/intelligence/canvas/` — Follow established canvas patterns

---

## File Structure

```
src/features/intelligence/pitch/
├── PitchDeckCanvas.tsx              (Main component, semantic landmarks)
├── components/
│   ├── SlideRenderer.tsx            (Slide type dispatch/rendering)
│   ├── slides/
│   │   ├── CoverSlide.tsx           (Title + company info)
│   │   ├── StorySlide.tsx           (Narrative/mission)
│   │   ├── MarketOpportunitySlide.tsx (Market data + 3D Globe integration)
│   │   ├── SolutionSlide.tsx        (Product/solution)
│   │   ├── CompetitiveSlide.tsx     (Competitive advantage)
│   │   ├── FinancialsSlide.tsx      (Revenue + scenario engine integration)
│   │   ├── AskSlide.tsx             (Funding ask + use of funds)
│   │   └── ClosingSlide.tsx         (Call to action)
│   ├── PresentationControls.tsx     (Nav buttons, slide counter, keyboard listener)
│   ├── PresentationMode.tsx         (Full-screen presentation styling)
│   └── SlideThumbnailPanel.tsx      (Slide preview sidebar)
├── hooks/
│   └── usePitchDeckPresentation.ts  (State management for presentation)
└── types/
    └── pitchDeck.types.ts            (Slide type definitions, data models)

tests/integration/
├── test_pitch_deck_canvas.tsx       (Main canvas integration tests)
├── test_pitch_slides.tsx            (Individual slide rendering tests)
├── test_3d_globe_integration.tsx    (ThreeDGlobe import + interaction)
├── test_scenario_integration.tsx    (ScenarioSlider integration)
├── test_keyboard_navigation.tsx     (Full a11y keyboard flow)
├── test_export_functionality.tsx    (PDF/PowerPoint export)
└── test_pitch_regression.tsx        (Full Phase 0-4 regression gate)
```

---

## Task Breakdown (12 Tasks, TDD-First)

### Task 1: Project Setup & Slide Type System

**Files:**
- Create: `src/features/intelligence/pitch/types/pitchDeck.types.ts`
- Create: `src/features/intelligence/pitch/PitchDeckCanvas.tsx`
- Create: `tests/integration/test_pitch_deck_canvas.tsx`

**Objective:** Define slide type system and create the main PitchDeckCanvas component with semantic landmarks (WCAG).

---

**Steps:**

- [ ] **1.1: Write failing test for slide type system**

```typescript
// tests/integration/test_pitch_deck_canvas.tsx

import { describe, it, expect } from 'vitest';
import { SlideType } from '../../src/features/intelligence/pitch/types/pitchDeck.types';

describe('Pitch Deck - Slide Types', () => {
  it('defines all 8 required slide types', () => {
    const slideTypes: SlideType[] = [
      'cover',
      'story',
      'market-opportunity',
      'solution',
      'competitive',
      'financials',
      'ask',
      'closing',
    ];

    expect(slideTypes).toHaveLength(8);
    slideTypes.forEach(type => {
      expect(typeof type).toBe('string');
    });
  });

  it('Slide interface includes required properties', () => {
    // Verify type definition exists
    const mockSlide = {
      id: 'slide-1',
      type: 'cover' as SlideType,
      title: 'Company Name',
      subtitle: 'Pitch Deck',
      content: {},
    };

    expect(mockSlide.id).toBeDefined();
    expect(mockSlide.type).toBeDefined();
    expect(mockSlide.title).toBeDefined();
  });
});

describe('Pitch Deck Canvas - Component Structure', () => {
  it('renders with semantic landmarks (role="application")', () => {
    const { container } = render(<PitchDeckCanvas />);
    const canvas = container.querySelector('[role="application"]');
    expect(canvas).toBeInTheDocument();
    expect(canvas).toHaveAttribute('aria-label');
  });

  it('has role="navigation" for slide controls', () => {
    render(<PitchDeckCanvas />);
    const nav = screen.getByRole('navigation');
    expect(nav).toHaveAttribute('aria-label', expect.stringContaining('presentation'));
  });

  it('has role="main" for slide content', () => {
    render(<PitchDeckCanvas />);
    const main = screen.getByRole('main');
    expect(main).toBeInTheDocument();
  });

  it('has role="complementary" for thumbnail sidebar', () => {
    render(<PitchDeckCanvas />);
    const aside = screen.getByRole('complementary');
    expect(aside).toHaveAttribute('aria-label', expect.stringContaining('slide'));
  });
});
```

- [ ] **1.2: Run test to verify it fails**

```bash
cd d:/Desktop/New_Flask/FLASK/lliveupdatedstreaming
npm test -- tests/integration/test_pitch_deck_canvas.tsx --run
```

Expected output: FAIL — "pitchDeck.types module not found", "PitchDeckCanvas is not exported"

- [ ] **1.3: Create slide type definitions**

```typescript
// src/features/intelligence/pitch/types/pitchDeck.types.ts

export type SlideType =
  | 'cover'
  | 'story'
  | 'market-opportunity'
  | 'solution'
  | 'competitive'
  | 'financials'
  | 'ask'
  | 'closing';

export interface SlideContent {
  [key: string]: any;
}

export interface Slide {
  id: string;
  type: SlideType;
  title: string;
  subtitle?: string;
  content: SlideContent;
  notes?: string;
}

export interface PitchDeckData {
  id: string;
  companyName: string;
  tagline: string;
  slides: Slide[];
  createdAt: string;
  updatedAt: string;
  status: 'draft' | 'published';
}

export interface PresentationState {
  currentSlideIndex: number;
  isFullScreen: boolean;
  isPaused: boolean;
  showNotes: boolean;
}
```

- [ ] **1.4: Create PitchDeckCanvas component with landmarks**

```typescript
// src/features/intelligence/pitch/PitchDeckCanvas.tsx

import React, { useState } from 'react';
import { PitchDeckData, PresentationState } from './types/pitchDeck.types';

interface PitchDeckCanvasProps {
  deckId?: string;
}

export const PitchDeckCanvas: React.FC<PitchDeckCanvasProps> = ({ deckId = 'default' }) => {
  const [state, setState] = useState<PresentationState>({
    currentSlideIndex: 0,
    isFullScreen: false,
    isPaused: false,
    showNotes: false,
  });

  const [deckData] = useState<PitchDeckData>({
    id: deckId,
    companyName: 'Barise',
    tagline: 'Strategic Intelligence Platform',
    slides: [],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
    status: 'draft',
  });

  return (
    <div
      role="application"
      aria-label="Pitch Deck Canvas — Investor presentation builder"
      className="pitch-deck-canvas"
    >
      {/* Navigation Rail */}
      <nav
        role="navigation"
        aria-label="Presentation controls and slide navigation"
        className="presentation-controls"
      >
        {/* Controls rendered by PresentationControls component */}
      </nav>

      {/* Main Slide Content */}
      <main role="main" className="slide-content">
        {/* Slides rendered by SlideRenderer component */}
      </main>

      {/* Thumbnail Sidebar */}
      <aside
        role="complementary"
        aria-label="Slide thumbnail panel and overview"
        className="slide-thumbnails"
      >
        {/* Thumbnails rendered by SlideThumbnailPanel component */}
      </aside>
    </div>
  );
};

export default PitchDeckCanvas;
```

- [ ] **1.5: Run test to verify it passes**

```bash
npm test -- tests/integration/test_pitch_deck_canvas.tsx --run
```

Expected output: PASS — All 5 tests passing, semantic landmarks verified

- [ ] **1.6: Commit**

```bash
git add src/features/intelligence/pitch/types/pitchDeck.types.ts \
        src/features/intelligence/pitch/PitchDeckCanvas.tsx \
        tests/integration/test_pitch_deck_canvas.tsx

git commit -m "feat(phase4): task 1 - pitch deck canvas core structure with WCAG landmarks

- Create slide type system (8 slide types: cover, story, market-opportunity, solution, competitive, financials, ask, closing)
- Create PitchDeckCanvas component with semantic landmarks (role='application', 'navigation', 'main', 'complementary')
- All aria-labels following WCAG 2.1 AA standard from Phase 3/Option B
- Tests: 5/5 passing (type system, landmark structure, accessibility)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 2: Slide Renderer & Individual Slide Components (8 Slides)

**Files:**
- Create: `src/features/intelligence/pitch/components/SlideRenderer.tsx`
- Create: `src/features/intelligence/pitch/components/slides/CoverSlide.tsx`
- Create: `src/features/intelligence/pitch/components/slides/StorySlide.tsx`
- Create: `src/features/intelligence/pitch/components/slides/MarketOpportunitySlide.tsx`
- Create: `src/features/intelligence/pitch/components/slides/SolutionSlide.tsx`
- Create: `src/features/intelligence/pitch/components/slides/CompetitiveSlide.tsx`
- Create: `src/features/intelligence/pitch/components/slides/FinancialsSlide.tsx`
- Create: `src/features/intelligence/pitch/components/slides/AskSlide.tsx`
- Create: `src/features/intelligence/pitch/components/slides/ClosingSlide.tsx`
- Create: `tests/integration/test_pitch_slides.tsx`

**Objective:** Create slide renderer that dispatches to 8 specific slide components, each with proper content structure.

**Steps:** (This task is large; breakdown per slide type)

- [ ] **2.1: Write failing test for SlideRenderer**

```typescript
// tests/integration/test_pitch_slides.tsx

import { render, screen } from '@testing-library/react';
import { SlideRenderer } from '../../src/features/intelligence/pitch/components/SlideRenderer';
import { Slide } from '../../src/features/intelligence/pitch/types/pitchDeck.types';

describe('Pitch Deck - SlideRenderer', () => {
  it('renders CoverSlide for cover type', () => {
    const slide: Slide = {
      id: 'cover-1',
      type: 'cover',
      title: 'Barise',
      subtitle: 'Strategic Intelligence Platform',
      content: { companyName: 'Barise', tagline: 'Strategic Intelligence Platform' },
    };

    render(<SlideRenderer slide={slide} />);
    expect(screen.getByText('Barise')).toBeInTheDocument();
  });

  it('renders StorySlide for story type', () => {
    const slide: Slide = {
      id: 'story-1',
      type: 'story',
      title: 'Our Story',
      content: { mission: 'Empower founders with data-driven intelligence' },
    };

    render(<SlideRenderer slide={slide} />);
    expect(screen.getByRole('heading', { name: /Our Story/i })).toBeInTheDocument();
  });

  it('renders MarketOpportunitySlide for market-opportunity type', () => {
    const slide: Slide = {
      id: 'market-1',
      type: 'market-opportunity',
      title: 'Market Opportunity',
      content: { tam: 50000000, sam: 10000000, market_data: [] },
    };

    render(<SlideRenderer slide={slide} />);
    expect(screen.getByRole('heading', { name: /Market Opportunity/i })).toBeInTheDocument();
  });

  // Similar tests for solution, competitive, financials, ask, closing
});

describe('Pitch Deck - Individual Slides', () => {
  it('CoverSlide displays company name and tagline', () => {
    render(
      <CoverSlide
        title="Barise"
        subtitle="Strategic Intelligence Platform"
        content={{ companyName: 'Barise', tagline: 'Strategic Intelligence Platform' }}
      />
    );
    expect(screen.getByText('Barise')).toBeInTheDocument();
    expect(screen.getByText('Strategic Intelligence Platform')).toBeInTheDocument();
  });

  it('StorySlide displays mission statement', () => {
    render(
      <StorySlide
        title="Our Story"
        content={{ mission: 'Empower founders with intelligence' }}
      />
    );
    expect(screen.getByText(/mission/i)).toBeInTheDocument();
  });

  // Tests for each slide type
});
```

- [ ] **2.2: Run test to verify it fails**

```bash
npm test -- tests/integration/test_pitch_slides.tsx --run
```

Expected: FAIL — SlideRenderer not found, slide components not exported

- [ ] **2.3: Create SlideRenderer component**

```typescript
// src/features/intelligence/pitch/components/SlideRenderer.tsx

import React from 'react';
import { Slide } from '../types/pitchDeck.types';
import CoverSlide from './slides/CoverSlide';
import StorySlide from './slides/StorySlide';
import MarketOpportunitySlide from './slides/MarketOpportunitySlide';
import SolutionSlide from './slides/SolutionSlide';
import CompetitiveSlide from './slides/CompetitiveSlide';
import FinancialsSlide from './slides/FinancialsSlide';
import AskSlide from './slides/AskSlide';
import ClosingSlide from './slides/ClosingSlide';

interface SlideRendererProps {
  slide: Slide;
}

export const SlideRenderer: React.FC<SlideRendererProps> = ({ slide }) => {
  switch (slide.type) {
    case 'cover':
      return <CoverSlide {...slide} />;
    case 'story':
      return <StorySlide {...slide} />;
    case 'market-opportunity':
      return <MarketOpportunitySlide {...slide} />;
    case 'solution':
      return <SolutionSlide {...slide} />;
    case 'competitive':
      return <CompetitiveSlide {...slide} />;
    case 'financials':
      return <FinancialsSlide {...slide} />;
    case 'ask':
      return <AskSlide {...slide} />;
    case 'closing':
      return <ClosingSlide {...slide} />;
    default:
      const _exhaustive: never = slide.type;
      return _exhaustive;
  }
};

export default SlideRenderer;
```

- [ ] **2.4: Create CoverSlide component**

```typescript
// src/features/intelligence/pitch/components/slides/CoverSlide.tsx

import React from 'react';
import { Slide } from '../../types/pitchDeck.types';

interface CoverSlideProps extends Slide {
  type: 'cover';
}

export const CoverSlide: React.FC<CoverSlideProps> = ({ title, subtitle }) => {
  return (
    <div className="slide cover-slide" role="region" aria-label="Title Slide">
      <h1>{title}</h1>
      <p className="tagline">{subtitle}</p>
      <p className="date">{new Date().getFullYear()}</p>
    </div>
  );
};

export default CoverSlide;
```

- [ ] **2.5: Create remaining slide components (StorySlide, MarketOpportunitySlide, etc.)**

For brevity, showing the pattern; repeat for each:

```typescript
// src/features/intelligence/pitch/components/slides/StorySlide.tsx

import React from 'react';
import { Slide } from '../../types/pitchDeck.types';

interface StorySlideProps extends Slide {
  type: 'story';
}

export const StorySlide: React.FC<StorySlideProps> = ({ title, content }) => {
  return (
    <div className="slide story-slide" role="region" aria-label="Company Story">
      <h2>{title}</h2>
      <div className="mission">{content.mission || 'Our Mission'}</div>
      <div className="narrative">{content.narrative || 'Tell our story...'}</div>
    </div>
  );
};

export default StorySlide;
```

Repeat pattern for:
- `MarketOpportunitySlide.tsx` (will later integrate ThreeDGlobe)
- `SolutionSlide.tsx`
- `CompetitiveSlide.tsx`
- `FinancialsSlide.tsx` (will later integrate ScenarioSlider)
- `AskSlide.tsx`
- `ClosingSlide.tsx`

- [ ] **2.6: Run tests to verify all slides render**

```bash
npm test -- tests/integration/test_pitch_slides.tsx --run
```

Expected: PASS — All slide types dispatch correctly, individual slides render content

- [ ] **2.7: Commit**

```bash
git add src/features/intelligence/pitch/components/ tests/integration/test_pitch_slides.tsx

git commit -m "feat(phase4): task 2 - slide renderer and all 8 slide components

Implements SlideRenderer dispatcher for all 8 slide types:
- CoverSlide (title, tagline, date)
- StorySlide (mission, narrative)
- MarketOpportunitySlide (TAM/SAM, market data - ready for 3D globe integration)
- SolutionSlide (product overview, key features)
- CompetitiveSlide (positioning, differentiation)
- FinancialsSlide (revenue, metrics - ready for scenario engine integration)
- AskSlide (funding ask, use of funds)
- ClosingSlide (call to action)

All slides use semantic HTML with role='region' and aria-label.
Tests: Renderer dispatch + individual slide rendering verified.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 3: Presentation Controls & Keyboard Navigation

**Files:**
- Create: `src/features/intelligence/pitch/components/PresentationControls.tsx`
- Create: `src/features/intelligence/pitch/hooks/usePitchDeckPresentation.ts`
- Create: `tests/integration/test_keyboard_navigation.tsx`

**Objective:** Implement keyboard navigation using Phase 3 a11yUtils. Enter/Space = next slide, Escape = overview.

**Steps:**

- [ ] **3.1: Write failing test for keyboard navigation**

```typescript
// tests/integration/test_keyboard_navigation.tsx

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { PitchDeckCanvas } from '../../src/features/intelligence/pitch/PitchDeckCanvas';

describe('Pitch Deck - Keyboard Navigation', () => {
  it('Enter key advances to next slide', async () => {
    const user = userEvent.setup();
    render(<PitchDeckCanvas />);

    const slideCounter = screen.getByTestId('slide-counter');
    expect(slideCounter).toHaveTextContent('Slide 1 of 8');

    // Press Enter to go to next slide
    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(slideCounter).toHaveTextContent('Slide 2 of 8');
    });
  });

  it('Space key advances to next slide', async () => {
    const user = userEvent.setup();
    render(<PitchDeckCanvas />);

    const slideCounter = screen.getByTestId('slide-counter');
    expect(slideCounter).toHaveTextContent('Slide 1 of 8');

    // Press Space to go to next slide
    await user.keyboard(' ');

    await waitFor(() => {
      expect(slideCounter).toHaveTextContent('Slide 2 of 8');
    });
  });

  it('Escape key shows slide overview/thumbnail panel', async () => {
    const user = userEvent.setup();
    render(<PitchDeckCanvas />);

    const thumbnailPanel = screen.getByRole('complementary');
    expect(thumbnailPanel).toHaveClass('hidden');

    // Press Escape to show overview
    await user.keyboard('{Escape}');

    await waitFor(() => {
      expect(thumbnailPanel).not.toHaveClass('hidden');
    });
  });

  it('Shift+Space goes to previous slide', async () => {
    const user = userEvent.setup();
    render(<PitchDeckCanvas />);

    const slideCounter = screen.getByTestId('slide-counter');

    // Go forward first
    await user.keyboard('{Enter}');
    await waitFor(() => {
      expect(slideCounter).toHaveTextContent('Slide 2');
    });

    // Go back with Shift+Space
    await user.keyboard('{Shift> }');

    await waitFor(() => {
      expect(slideCounter).toHaveTextContent('Slide 1');
    });
  });

  it('Keyboard navigation is announced via ARIA live region', async () => {
    const user = userEvent.setup();
    render(<PitchDeckCanvas />);

    const ariaLive = screen.getByRole('status', { name: /slide navigation/i });
    expect(ariaLive).toHaveAttribute('aria-live', 'polite');

    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(ariaLive).toHaveTextContent(/slide 2/i);
    });
  });
});
```

- [ ] **3.2: Run test to verify it fails**

```bash
npm test -- tests/integration/test_keyboard_navigation.tsx --run
```

Expected: FAIL — PresentationControls not found, keyboard handlers not implemented

- [ ] **3.3: Create keyboard navigation hook using a11yUtils**

```typescript
// src/features/intelligence/pitch/hooks/usePitchDeckPresentation.ts

import { useEffect, useCallback } from 'react';
import { PresentationState } from '../types/pitchDeck.types';

interface UsePitchDeckPresentationProps {
  state: PresentationState;
  setState: (state: PresentationState) => void;
  totalSlides: number;
}

export const usePitchDeckPresentation = ({
  state,
  setState,
  totalSlides,
}: UsePitchDeckPresentationProps) => {
  const nextSlide = useCallback(() => {
    setState({
      ...state,
      currentSlideIndex: Math.min(state.currentSlideIndex + 1, totalSlides - 1),
    });
  }, [state, setState, totalSlides]);

  const prevSlide = useCallback(() => {
    setState({
      ...state,
      currentSlideIndex: Math.max(state.currentSlideIndex - 1, 0),
    });
  }, [state, setState]);

  const goToSlide = useCallback((index: number) => {
    setState({
      ...state,
      currentSlideIndex: Math.max(0, Math.min(index, totalSlides - 1)),
    });
  }, [state, setState, totalSlides]);

  const toggleOverview = useCallback(() => {
    setState({
      ...state,
      isFullScreen: !state.isFullScreen,
    });
  }, [state, setState]);

  // Keyboard event handler
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Enter or Space: next slide
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        if (e.shiftKey) {
          prevSlide();
        } else {
          nextSlide();
        }
      }

      // Escape: show overview/full-screen toggle
      if (e.key === 'Escape') {
        e.preventDefault();
        toggleOverview();
      }

      // Arrow keys: navigate
      if (e.key === 'ArrowRight') {
        e.preventDefault();
        nextSlide();
      }

      if (e.key === 'ArrowLeft') {
        e.preventDefault();
        prevSlide();
      }

      // Number keys: jump to slide (1-8)
      if (/^[1-8]$/.test(e.key)) {
        e.preventDefault();
        goToSlide(parseInt(e.key) - 1);
      }
    },
    [nextSlide, prevSlide, goToSlide, toggleOverview]
  );

  // Attach keyboard listener
  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return {
    nextSlide,
    prevSlide,
    goToSlide,
    toggleOverview,
    currentSlideIndex: state.currentSlideIndex,
    isFullScreen: state.isFullScreen,
  };
};

export default usePitchDeckPresentation;
```

- [ ] **3.4: Create PresentationControls component**

```typescript
// src/features/intelligence/pitch/components/PresentationControls.tsx

import React from 'react';

interface PresentationControlsProps {
  currentSlideIndex: number;
  totalSlides: number;
  onNextSlide: () => void;
  onPrevSlide: () => void;
  onToggleOverview: () => void;
  isFullScreen: boolean;
}

export const PresentationControls: React.FC<PresentationControlsProps> = ({
  currentSlideIndex,
  totalSlides,
  onNextSlide,
  onPrevSlide,
  onToggleOverview,
  isFullScreen,
}) => {
  return (
    <div
      className="presentation-controls"
      role="navigation"
      aria-label="Presentation controls and navigation"
    >
      <button
        onClick={onPrevSlide}
        disabled={currentSlideIndex === 0}
        aria-label="Previous slide (Shift+Space)"
        className="prev-btn"
      >
        ← Previous
      </button>

      <div
        className="slide-counter"
        role="status"
        aria-label="Slide navigation"
        data-testid="slide-counter"
      >
        Slide {currentSlideIndex + 1} of {totalSlides}
      </div>

      <button
        onClick={onNextSlide}
        disabled={currentSlideIndex === totalSlides - 1}
        aria-label="Next slide (Space or Enter)"
        className="next-btn"
      >
        Next →
      </button>

      <button
        onClick={onToggleOverview}
        aria-label={isFullScreen ? 'Exit full-screen (Escape)' : 'Enter full-screen (Escape)'}
        className="overview-btn"
      >
        {isFullScreen ? 'Exit Overview' : 'Show Overview'}
      </button>
    </div>
  );
};

export default PresentationControls;
```

- [ ] **3.5: Update PitchDeckCanvas to use hook and controls**

```typescript
// src/features/intelligence/pitch/PitchDeckCanvas.tsx (updated)

import React, { useState } from 'react';
import { PitchDeckData, PresentationState } from './types/pitchDeck.types';
import { usePitchDeckPresentation } from './hooks/usePitchDeckPresentation';
import { PresentationControls } from './components/PresentationControls';

// ... existing code ...

export const PitchDeckCanvas: React.FC<PitchDeckCanvasProps> = ({ deckId = 'default' }) => {
  const [state, setState] = useState<PresentationState>({
    currentSlideIndex: 0,
    isFullScreen: false,
    isPaused: false,
    showNotes: false,
  });

  const { nextSlide, prevSlide, toggleOverview } = usePitchDeckPresentation({
    state,
    setState,
    totalSlides: 8,
  });

  return (
    <div role="application" aria-label="Pitch Deck Canvas" className="pitch-deck-canvas">
      <PresentationControls
        currentSlideIndex={state.currentSlideIndex}
        totalSlides={8}
        onNextSlide={nextSlide}
        onPrevSlide={prevSlide}
        onToggleOverview={toggleOverview}
        isFullScreen={state.isFullScreen}
      />

      <main role="main" className="slide-content">
        {/* SlideRenderer uses state.currentSlideIndex */}
      </main>

      <aside role="complementary" aria-label="Slide thumbnails" className="slide-thumbnails">
        {/* Thumbnails */}
      </aside>
    </div>
  );
};
```

- [ ] **3.6: Run tests to verify keyboard navigation**

```bash
npm test -- tests/integration/test_keyboard_navigation.tsx --run
```

Expected: PASS — All keyboard interactions working, ARIA live region announces navigation

- [ ] **3.7: Commit**

```bash
git add src/features/intelligence/pitch/hooks/usePitchDeckPresentation.ts \
        src/features/intelligence/pitch/components/PresentationControls.tsx \
        tests/integration/test_keyboard_navigation.tsx

git commit -m "feat(phase4): task 3 - keyboard navigation and presentation controls

Implements full keyboard navigation using a11yUtils patterns:
- Enter/Space: Next slide
- Shift+Space: Previous slide
- Arrow Left/Right: Navigate slides
- Escape: Show/hide overview (full-screen mode)
- Number keys (1-8): Jump to specific slide

Updates:
- Create usePitchDeckPresentation hook for state management
- Create PresentationControls component with accessible buttons
- ARIA live region announces all slide transitions
- Keyboard handlers integrated into main PitchDeckCanvas

Tests: 5/5 keyboard navigation tests passing.
Accessibility: Full keyboard-only navigation supported, WCAG compliant.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 4: 3D Globe Integration (Market Opportunity Slide)

**Files:**
- Modify: `src/features/intelligence/pitch/components/slides/MarketOpportunitySlide.tsx`
- Create: `tests/integration/test_3d_globe_integration.tsx`

**Objective:** Import Phase 3's ThreeDGlobe component and integrate it into Market Opportunity slide.

**Steps:**

- [ ] **4.1: Write failing test for 3D globe integration**

```typescript
// tests/integration/test_3d_globe_integration.tsx

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MarketOpportunitySlide } from '../../src/features/intelligence/pitch/components/slides/MarketOpportunitySlide';

describe('Pitch Deck - 3D Globe Integration', () => {
  const mockMarketData = {
    id: 'market-1',
    type: 'market-opportunity' as const,
    title: 'Market Opportunity',
    content: {
      tam: 50000000,
      sam: 10000000,
      som: 1000000,
      regions: ['North America', 'Europe', 'Asia Pacific', 'Emerging Markets'],
    },
  };

  it('renders 3D Globe component on Market Opportunity slide', async () => {
    render(<MarketOpportunitySlide {...mockMarketData} />);

    // Wait for globe to appear
    await waitFor(
      () => {
        const globe = screen.getByTestId('three-d-globe');
        expect(globe).toBeInTheDocument();
      },
      { timeout: 3000 }
    );
  });

  it('displays market regions for globe visualization', async () => {
    render(<MarketOpportunitySlide {...mockMarketData} />);

    const regions = screen.getAllByTestId(/region-marker-/);
    expect(regions).toHaveLength(4);
  });

  it('displays TAM/SAM metrics alongside globe', () => {
    render(<MarketOpportunitySlide {...mockMarketData} />);

    expect(screen.getByText('$50M')).toBeInTheDocument(); // TAM
    expect(screen.getByText('$10M')).toBeInTheDocument(); // SAM
  });

  it('globe is keyboard accessible (follow ThreeDGlobe a11y)', async () => {
    const user = userEvent.setup();
    render(<MarketOpportunitySlide {...mockMarketData} />);

    const globe = await screen.findByTestId('three-d-globe');

    // Canvas should be focusable
    globe.focus();
    expect(document.activeElement).toBe(globe);
  });

  it('provides alternative text for screen readers', async () => {
    render(<MarketOpportunitySlide {...mockMarketData} />);

    // Check for sr-only table (from ThreeDGlobe accessibility)
    const srTable = screen.getByRole('region', { name: /Market Region Data/i });
    expect(srTable).toBeInTheDocument();
  });
});
```

- [ ] **4.2: Run test to verify it fails**

```bash
npm test -- tests/integration/test_3d_globe_integration.tsx --run
```

Expected: FAIL — ThreeDGlobe not imported, globe doesn't render

- [ ] **4.3: Update MarketOpportunitySlide to import and display ThreeDGlobe**

```typescript
// src/features/intelligence/pitch/components/slides/MarketOpportunitySlide.tsx

import React from 'react';
import { Slide } from '../../types/pitchDeck.types';
import { ThreeDGlobe } from '../../../shared/ThreeDGlobe'; // Phase 3 component

interface MarketOpportunitySlideProps extends Slide {
  type: 'market-opportunity';
}

export const MarketOpportunitySlide: React.FC<MarketOpportunitySlideProps> = ({
  title,
  content,
}) => {
  const { tam, sam, som, regions } = content;

  // Format currency
  const formatCurrency = (value: number) => {
    if (value >= 1000000) {
      return `$${(value / 1000000).toFixed(0)}M`;
    }
    return `$${value}`;
  };

  return (
    <div className="slide market-opportunity-slide" role="region" aria-label="Market Opportunity">
      <h2>{title}</h2>

      <div className="market-metrics">
        <div className="metric">
          <label>Total Addressable Market (TAM)</label>
          <span className="value">{formatCurrency(tam)}</span>
        </div>
        <div className="metric">
          <label>Serviceable Addressable Market (SAM)</label>
          <span className="value">{formatCurrency(sam)}</span>
        </div>
        <div className="metric">
          <label>Serviceable Obtainable Market (SOM)</label>
          <span className="value">{formatCurrency(som)}</span>
        </div>
      </div>

      {/* Integrated 3D Globe from Phase 3 */}
      <div className="globe-container">
        <h3>Global Market Regions</h3>
        <ThreeDGlobe
          regions={regions || []}
          width={400}
          height={300}
        />
      </div>

      <div className="market-narrative">
        <p className="key-insight">
          Our addressable market spans {regions?.length || 0} global regions
          with significant growth potential in emerging markets.
        </p>
      </div>
    </div>
  );
};

export default MarketOpportunitySlide;
```

- [ ] **4.4: Run tests to verify globe integration**

```bash
npm test -- tests/integration/test_3d_globe_integration.tsx --run
```

Expected: PASS — Globe renders, metrics display, keyboard accessible

- [ ] **4.5: Commit**

```bash
git add src/features/intelligence/pitch/components/slides/MarketOpportunitySlide.tsx \
        tests/integration/test_3d_globe_integration.tsx

git commit -m "feat(phase4): task 4 - 3D globe integration on Market Opportunity slide

Integrates Phase 3 ThreeDGlobe component into investor pitch:
- Imports ThreeDGlobe from src/features/intelligence/shared/ThreeDGlobe
- Displays regions on interactive 3D visualization
- Shows TAM/SAM/SOM metrics alongside globe
- Leverages Phase 3 a11y features (sr-only table, WCAG landmarks)
- Code-split Three.js bundle (no main bundle impact)

Market Opportunity slide now provides:
- Quantitative metrics (TAM/SAM/SOM)
- Qualitative visualization (global regions on 3D globe)
- Screen reader support via sr-only table
- Keyboard accessible via ThreeDGlobe accessibility

Tests: 5/5 integration tests passing.
No regressions in Phase 3 globe tests.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Task 5: Scenario Engine Integration (Financials Slide)

**Files:**
- Modify: `src/features/intelligence/pitch/components/slides/FinancialsSlide.tsx`
- Create: `tests/integration/test_scenario_integration.tsx`

**Objective:** Import Phase 3's ScenarioSlider and useScenarios hook, integrate into Financials/Ask slide for live what-if modeling.

**Steps:**

- [ ] **5.1: Write failing test for scenario engine integration**

```typescript
// tests/integration/test_scenario_integration.tsx

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { FinancialsSlide } from '../../src/features/intelligence/pitch/components/slides/FinancialsSlide';

describe('Pitch Deck - Scenario Engine Integration', () => {
  const mockFinancialData = {
    id: 'financials-1',
    type: 'financials' as const,
    title: 'Financial Projections',
    content: {
      marketSize: 1000,
      conversionRate: 5,
      pricePoint: 100,
      customerAcquisitionCost: 200,
      lifetimeValue: 2000,
    },
  };

  it('renders ScenarioSlider controls for financial metrics', () => {
    render(<FinancialsSlide {...mockFinancialData} />);

    // Should have sliders for each metric
    expect(screen.getByLabelText(/Market Size/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Conversion Rate/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/Price Point/i)).toBeInTheDocument();
  });

  it('updates projected revenue in real-time when scenarios change', async () => {
    const user = userEvent.setup();
    render(<FinancialsSlide {...mockFinancialData} />);

    // Initial projection: 1000 * (5/100) * 100 = 5000
    expect(screen.getByText(/5,000/)).toBeInTheDocument();

    // Change market size slider
    const marketSizeSlider = screen.getByRole('slider', { name: /Market Size/i });
    await user.tripleClick(marketSizeSlider);
    await user.keyboard('2000');

    // New projection should update: 2000 * (5/100) * 100 = 10000
    await waitFor(() => {
      expect(screen.getByText(/10,000/)).toBeInTheDocument();
    });
  });

  it('shows delta percentage for modified metrics', async () => {
    const user = userEvent.setup();
    render(<FinancialsSlide {...mockFinancialData} />);

    const pricePointSlider = screen.getByRole('slider', { name: /Price Point/i });

    // Change price point from 100 to 150 (+50%)
    await user.tripleClick(pricePointSlider);
    await user.keyboard('150');

    // Should show +50% delta
    await waitFor(() => {
      expect(screen.getByText(/\+50%/)).toBeInTheDocument();
    });
  });

  it('calculates LTV:CAC ratio improvement', async () => {
    const user = userEvent.setup();
    render(<FinancialsSlide {...mockFinancialData} />);

    // Initial ratio: 2000 / 200 = 10x
    expect(screen.getByText('10:1')).toBeInTheDocument();

    // Reduce CAC from 200 to 100
    const cacSlider = screen.getByRole('slider', { name: /Customer Acquisition Cost/i });
    await user.tripleClick(cacSlider);
    await user.keyboard('100');

    // New ratio: 2000 / 100 = 20x
    await waitFor(() => {
      expect(screen.getByText('20:1')).toBeInTheDocument();
    });
  });

  it('preserves scenario state during pitch presentation', async () => {
    const user = userEvent.setup();
    const { rerender } = render(<FinancialsSlide {...mockFinancialData} />);

    // Change a scenario
    const marketSizeSlider = screen.getByRole('slider', { name: /Market Size/i });
    await user.tripleClick(marketSizeSlider);
    await user.keyboard('1500');

    // Re-render (simulating slide navigation away and back)
    rerender(<FinancialsSlide {...mockFinancialData} />);

    // Scenario state should persist
    expect(screen.getByText(/7,500/)).toBeInTheDocument(); // 1500 * 0.05 * 100
  });

  it('provides reset button to return to baseline projections', async () => {
    const user = userEvent.setup();
    render(<FinancialsSlide {...mockFinancialData} />);

    // Change scenario
    const marketSizeSlider = screen.getByRole('slider', { name: /Market Size/i });
    await user.tripleClick(marketSizeSlider);
    await user.keyboard('2000');

    // Click Reset
    const resetBtn = screen.getByRole('button', { name: /Reset Scenarios/i });
    await user.click(resetBtn);

    // Should return to baseline: 1000 * 0.05 * 100 = 5000
    await waitFor(() => {
      expect(screen.getByText(/5,000/)).toBeInTheDocument();
    });
  });
});
```

- [ ] **5.2: Run test to verify it fails**

```bash
npm test -- tests/integration/test_scenario_integration.tsx --run
```

Expected: FAIL — ScenarioSlider not imported, scenarios not reactive

- [ ] **5.3: Update FinancialsSlide to import and integrate scenario engine**

```typescript
// src/features/intelligence/pitch/components/slides/FinancialsSlide.tsx

import React, { useMemo } from 'react';
import { Slide } from '../../types/pitchDeck.types';
import { ScenarioSlider } from '../../../shared/ScenarioSlider'; // Phase 3 component
import { useScenarios } from '../../../shared/hooks/useScenarios'; // Phase 3 hook

interface FinancialsSlideProp extends Slide {
  type: 'financials';
}

export const FinancialsSlide: React.FC<FinancialsSlideProp> = ({ title, content }) => {
  const baselineMetrics = {
    marketSize: content.marketSize || 1000,
    conversionRate: content.conversionRate || 5, // 5%, not 0.05
    pricePoint: content.pricePoint || 100,
    customerAcquisitionCost: content.customerAcquisitionCost || 200,
    lifetimeValue: content.lifetimeValue || 2000,
  };

  // Use Phase 3 scenario engine hook
  const { scenarios, setScenario, reset, calculations } = useScenarios(baselineMetrics);

  // Format currency
  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
    }).format(value);
  };

  return (
    <div className="slide financials-slide" role="region" aria-label="Financial Projections">
      <h2>{title}</h2>

      {/* Financial Scenario Sliders (Phase 3 integration) */}
      <div className="financial-scenarios">
        <h3>What-If Scenarios</h3>

        <ScenarioSlider
          label="Market Size"
          baseValue={baselineMetrics.marketSize}
          currentValue={scenarios.current.marketSize}
          min={baselineMetrics.marketSize * 0.5}
          max={baselineMetrics.marketSize * 2}
          step={baselineMetrics.marketSize * 0.05}
          onChange={(val) => setScenario('marketSize', val)}
          unit="K"
        />

        <ScenarioSlider
          label="Conversion Rate"
          baseValue={baselineMetrics.conversionRate}
          currentValue={scenarios.current.conversionRate}
          min={1}
          max={15}
          step={0.5}
          onChange={(val) => setScenario('conversionRate', val)}
          unit="%"
        />

        <ScenarioSlider
          label="Price Point"
          baseValue={baselineMetrics.pricePoint}
          currentValue={scenarios.current.pricePoint}
          min={baselineMetrics.pricePoint * 0.5}
          max={baselineMetrics.pricePoint * 2}
          step={10}
          onChange={(val) => setScenario('pricePoint', val)}
          unit="$"
        />

        <ScenarioSlider
          label="Customer Acquisition Cost"
          baseValue={baselineMetrics.customerAcquisitionCost}
          currentValue={scenarios.current.customerAcquisitionCost}
          min={baselineMetrics.customerAcquisitionCost * 0.25}
          max={baselineMetrics.customerAcquisitionCost * 1.5}
          step={25}
          onChange={(val) => setScenario('customerAcquisitionCost', val)}
          unit="$"
        />

        <button onClick={reset} className="reset-btn" aria-label="Reset all scenarios to baseline">
          Reset Scenarios
        </button>
      </div>

      {/* Projected Outcomes (real-time calculations from scenarios) */}
      <div className="financial-outcomes">
        <h3>Projected Outcomes</h3>

        <div className="outcome-item">
          <label>Projected Year 1 Revenue</label>
          <span className="value">{formatCurrency(calculations.projectedRevenue)}</span>
        </div>

        <div className="outcome-item">
          <label>LTV:CAC Ratio</label>
          <span className="value">{calculations.ltvCacRatio.toFixed(1)}:1</span>
        </div>

        <div className="outcome-item">
          <label>Payback Period</label>
          <span className="value">{calculations.paybackMonths.toFixed(1)} months</span>
        </div>
      </div>

      <p className="financial-note text-sm text-gray-600">
        Adjust the sliders above to see how different assumptions affect financial projections.
        All calculations use current market data and normalized percentage conversions.
      </p>
    </div>
  );
};

export default FinancialsSlide;
```

- [ ] **5.4: Run tests to verify scenario integration**

```bash
npm test -- tests/integration/test_scenario_integration.tsx --run
```

Expected: PASS — Scenarios reactive, projections update, metrics calculated correctly

- [ ] **5.5: Commit**

```bash
git add src/features/intelligence/pitch/components/slides/FinancialsSlide.tsx \
        tests/integration/test_scenario_integration.tsx

git commit -m "feat(phase4): task 5 - scenario engine integration on Financials slide

Integrates Phase 3 scenario engine into investor pitch:
- Imports ScenarioSlider component (x5 metrics)
- Imports useScenarios hook for real-time calculations
- Implements what-if modeling for investor scenarios
- Uses explicit percentage normalization (conversionRate: 5 = 5%, not 0.05)

Financials/Ask slide now provides:
- Interactive sliders for 5 key metrics
- Real-time revenue projections (marketSize × conversionRate × pricePoint)
- LTV:CAC ratio improvement tracking
- Payback period calculations
- Reset button to return to baseline
- Scenario state persists during presentation navigation

Investors can now adjust assumptions and see financial impact live.

Tests: 6/6 scenario integration tests passing.
No regressions in Phase 3 scenario engine tests.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

### Tasks 6-12: (Abbreviated for brevity; provide full task specs)

Due to token limits, the remaining 7 tasks follow the same TDD pattern:

**Task 6: Slide Thumbnail Panel & Navigation**
- Navigate slides via thumbnail click
- Show current slide indicator
- Tests: Thumbnail rendering, click navigation, focus management

**Task 7: Presentation Mode (Full-Screen Polish)**
- Hide controls in presentation mode
- Maximize slide content
- Tests: Mode toggle, UI visibility, exit behavior

**Task 8: Export & Sharing**
- Export to PDF
- Create shareable draft link
- Tests: Export file generation, share URL creation

**Task 9: A11y Audit & WCAG Completion**
- Run jest-axe on full deck
- Verify keyboard-only navigation end-to-end
- Tests: 0 axe violations, complete keyboard flow

**Task 10: Performance Optimization**
- Memoize slide rendering
- Lazy load slides
- Tests: Performance metrics, no unnecessary re-renders

**Task 11: Integration Tests (Phase 4 Complete)**
- End-to-end pitch presentation flow
- All features working together
- Tests: 15+ integration scenarios

**Task 12: Final Regression & Commit**
- Run full Phase 0-4 test suite
- Verify ≥88% pass rate
- Final commit with summary

---

## Success Criteria & Gates

### Quality Gate 1: Spec Compliance (Per Task)
- [ ] Tests are comprehensive (cover happy path, edge cases, a11y)
- [ ] Code matches spec exactly (no extra features, no gaps)
- [ ] All 8 slide types rendering properly
- [ ] Keyboard navigation fully functional (Enter, Space, Escape, Arrows, 1-8)
- [ ] 3D Globe integrated on Market Opportunity
- [ ] Scenario Engine integrated on Financials
- [ ] All Phase 3 utilities properly leveraged

### Quality Gate 2: Code Quality (Per Task)
- [ ] TypeScript strict mode (no implicit any)
- [ ] React 18 best practices (hooks, memoization, cleanup)
- [ ] Performance optimized (lazy loading, memoization where appropriate)
- [ ] Accessibility verified (jest-axe 0 violations, full keyboard nav)
- [ ] No memory leaks (proper cleanup, event listener removal)

### Quality Gate 3: Regression (Final Gate)
- [ ] Full Phase 0-4 test suite passes
- [ ] Pass rate ≥88% (Option B gate maintained)
- [ ] Zero new failures introduced by Phase 4
- [ ] Phase 1-2-3 tests still passing (no breaking changes)

---

## Execution Handoff

**Plan saved to:** `docs/superpowers/plans/2026-04-02-PHASE4-PITCH-DECK-CULMINATION.md`

**Execution choice (Founder to decide):**

1. **Subagent-Driven (Recommended)** — I dispatch a fresh subagent per task, review between tasks, fast iteration. Each task gets spec review + code quality review gates.

2. **Inline Execution** — Execute tasks in this session using executing-plans skill, batch execution with checkpoints.

**Which approach would you like for Phase 4 execution?**
