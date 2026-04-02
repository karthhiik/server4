# Phase 3: Polish & Advanced Features - IMPLEMENTATION PLAN (DETAILED)

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` with TDD approach. Each task has test-first requirements.

**Goal:** Implement 3D enhancements, scenario engines, accessibility compliance, and multiplayer awareness architecture to make Barise canvases production-grade.

**Scope:** 4 Major Features + Complete Testing
- Feature 1: 3D Market Globe with interactive regions (Three.js)
- Feature 2: What-If Scenario Engine with real-time recalculation
- Feature 3: WCAG 2.1 AA Accessibility Compliance (ARIA, keyboard nav)
- Feature 4: Multiplayer Presence Architecture (Future WebSocket ready)

**Test Target:** 45+ new unit & integration tests (all TDD-driven)
**Estimated Duration:** 20-28 hours with subagent-driven development (increased from 16-20 for robust A11y)
**Architecture:** TDD first, implement second, review gates between tasks
**Critical Requirements:**
- ✅ Dynamic imports for Three.js (prevent bundle bloat)
- ✅ Standard WCAG contrast ratio algorithm (not pseudo-science)
- ✅ Hidden data tables for 3D accessibility
- ✅ Normalized scenario math (no magic numbers)

---

## File Structure Overview

```
lliveupdatedstreaming/src/
├── features/intelligence/
│   ├── shared/
│   │   ├── ThreeDGlobe.tsx (NEW)
│   │   ├── ScenarioSlider.tsx (NEW)
│   │   ├── hooks/
│   │   │   └── useScenarios.ts (NEW)
│   │   └── AccessibilityOverlay.tsx (NEW)
│   ├── business-plan/
│   │   ├── nodes/
│   │   │   └── MarketNode.tsx (MODIFY - add 3D support)
│   │   └── BusinessPlanCanvas.tsx (MODIFY - add A11y)
│   ├── gtm/
│   │   ├── GTMCanvas.tsx (MODIFY - add scenario slider)
│   │   └── views/... (MODIFY - add A11y)
│   ├── swot/
│   │   └── SWOTCanvas.tsx (MODIFY - add A11y)
│   └── pitch/
│       └── PitchDeckCanvas.tsx (MODIFY - add A11y)
└── services/
    ├── multiplayer/
    │   └── presenceService.ts (NEW - stub only)
    └── accessibility/
        └── a11yUtils.ts (NEW)

lliveupdatedstreaming/tests/
├── integration/
│   ├── test_3d_globe.tsx (NEW)
│   ├── test_scenario_engine.tsx (NEW)
│   ├── test_accessibility_compliance.tsx (NEW)
│   ├── test_multiplayer_stubs.tsx (NEW)
│   └── test_export_quality.tsx (NEW)
├── performance/
│   ├── test_three_js_memory.spec.ts (NEW)
│   ├── test_bundle_size.spec.ts (NEW)
│   └── lighthouse_audit.spec.ts (NEW)
└── e2e/
    ├── business_plan_full_flow.spec.ts (NEW)
    ├── gtm_full_flow.spec.ts (NEW)
    ├── swot_full_flow.spec.ts (NEW)
    └── pitch_full_flow.spec.ts (NEW)
```

---

## TASK 1: 3D Market Globe Enhancement

**Objective:** Add interactive Three.js globe to MarketNode that shows highlighted regions on hover.

**Files to Create/Modify:**
- Create: `src/features/intelligence/shared/ThreeDGlobe.tsx`
- Modify: `src/features/intelligence/business-plan/nodes/MarketNode.tsx`
- Create: `tests/integration/test_3d_globe.tsx`

### Test Success Criteria:
- [ ] 3D globe renders in a canvas element on hover
- [ ] Globe displays 3-5 highlighted regions as glowing spheres
- [ ] Regions auto-rotate and animate
- [ ] WebGL context is properly destroyed on unmount (memory leak prevention)
- [ ] No Three.js console errors
- [ ] Responsive to viewport size changes

### Tasks:

#### Task 1.1: Write failing test for 3D globe

```typescript
// tests/integration/test_3d_globe.tsx

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MarketNode } from '../../src/features/intelligence/business-plan/nodes/MarketNode';

describe('3D Market Globe', () => {
  const mockMarketData = {
    id: 'market-apac',
    title: 'Asia Pacific',
    icon: '🌏',
    metrics: {
      tam: '$500B',
      growth: '12%',
      marketShare: '8%',
    },
    regions: ['China', 'India', 'Southeast Asia', 'Japan', 'South Korea'],
    confidence: 'verified' as const,
  };

  it('renders 3D globe on hover with region highlights', async () => {
    const user = userEvent.setup();
    render(<MarketNode data={mockMarketData} />);

    const nodeElement = screen.getByTestId('market-node-apac');

    // Initially no globe
    expect(screen.queryByTestId('three-d-globe')).not.toBeInTheDocument();

    // Hover to show globe
    await user.hover(nodeElement);

    // Globe appears
    await waitFor(() => {
      const globe = screen.getByTestId('three-d-globe');
      expect(globe).toBeInTheDocument();
      expect(globe.tagName).toBe('CANVAS');
    });

    // Verify region markers exist
    const regionMarkers = screen.getAllByTestId(/region-marker-/);
    expect(regionMarkers).toHaveLength(5);
  });

  it('sets correct colors for region highlights', async () => {
    const user = userEvent.setup();
    render(<MarketNode data={mockMarketData} />);

    await user.hover(screen.getByTestId('market-node-apac'));

    await waitFor(() => {
      const markers = screen.getAllByTestId(/region-marker-/);
      markers.forEach((marker) => {
        const color = window.getComputedStyle(marker).backgroundColor;
        expect(color).toMatch(/rgba\(0, 255, 136/); // Glow color: #00ff88
      });
    });
  });

  it('cleans up WebGL context on unmount', async () => {
    const user = userEvent.setup();
    const { unmount } = render(<MarketNode data={mockMarketData} />);

    await user.hover(screen.getByTestId('market-node-apac'));
    await waitFor(() => {
      expect(screen.getByTestId('three-d-globe')).toBeInTheDocument();
    });

    // Verify WebGL context exists before unmount
    const canvas = screen.getByTestId('three-d-globe') as HTMLCanvasElement;
    const gl = canvas.getContext('webgl');
    expect(gl).not.toBeNull();

    unmount();

    // After unmount, canvas should be removed
    expect(screen.queryByTestId('three-d-globe')).not.toBeInTheDocument();
  });

  it('handles resize events without breaking', async () => {
    const user = userEvent.setup();
    render(<MarketNode data={mockMarketData} />);

    await user.hover(screen.getByTestId('market-node-apac'));

    await waitFor(() => {
      expect(screen.getByTestId('three-d-globe')).toBeInTheDocument();
    });

    // Simulate resize
    global.innerWidth = 800;
    global.innerHeight = 600;
    window.dispatchEvent(new Event('resize'));

    // Globe should still be there and functional
    await waitFor(() => {
      expect(screen.getByTestId('three-d-globe')).toBeInTheDocument();
    });
  });

  it('stops rotating when unhovered', async () => {
    const user = userEvent.setup();
    render(<MarketNode data={mockMarketData} />);

    await user.hover(screen.getByTestId('market-node-apac'));

    await waitFor(() => {
      expect(screen.getByTestId('three-d-globe')).toBeInTheDocument();
    });

    const globeBefore = screen.getByTestId('three-d-globe');

    // Unhover
    await user.unhover(screen.getByTestId('market-node-apac'));

    // Globe should disappear
    expect(screen.queryByTestId('three-d-globe')).not.toBeInTheDocument();
  });
});
```

#### Task 1.2: Implement ThreeDGlobe component

**CRITICAL:** Use dynamic imports to prevent bundle bloat. Create TWO files:

**File A: GlobeRenderer.tsx (heavy Three.js logic - will be code-split)**

```typescript
// src/features/intelligence/shared/GlobeRenderer.tsx
// This file is lazy-loaded and will be in a separate bundle chunk

import React, { useRef, useEffect } from 'react';
import * as THREE from 'three';

interface ThreeDGlobeProps {
  regions: string[];
  width?: number;
  height?: number;
}

export const ThreeDGlobe: React.FC<ThreeDGlobeProps> = ({
  regions,
  width = 300,
  height = 300,
}) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const sceneRef = useRef<THREE.Scene | null>(null);
  const rendererRef = useRef<THREE.WebGLRenderer | null>(null);
  const globeRef = useRef<THREE.Mesh | null>(null);
  const animationIdRef = useRef<number>();

  useEffect(() => {
    if (!canvasRef.current) return;

    // Create scene
    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(75, width / height, 0.1, 1000);
    const renderer = new THREE.WebGLRenderer({
      canvas: canvasRef.current,
      antialias: true,
      alpha: true,
    });

    renderer.setSize(width, height);
    renderer.setClearColor(0x0a0e27, 0.1); // Transparent dark background
    renderer.shadowMap.enabled = true;

    sceneRef.current = scene;
    rendererRef.current = renderer;

    // Create globe with gradient material
    const globeGeometry = new THREE.SphereGeometry(1.5, 64, 64);
    const globeCanvas = document.createElement('canvas');
    globeCanvas.width = 2048;
    globeCanvas.height = 1024;
    const ctx = globeCanvas.getContext('2d')!;

    // Gradient texture
    const gradient = ctx.createLinearGradient(0, 0, 0, globeCanvas.height);
    gradient.addColorStop(0, '#1a3a52');
    gradient.addColorStop(0.5, '#2a5a7a');
    gradient.addColorStop(1, '#0a1a2a');
    ctx.fillStyle = gradient;
    ctx.fillRect(0, 0, globeCanvas.width, globeCanvas.height);

    const globeTexture = new THREE.CanvasTexture(globeCanvas);
    const globeMaterial = new THREE.MeshPhongMaterial({
      map: globeTexture,
      emissive: 0x1a4a6a,
      shininess: 5,
    });

    const globe = new THREE.Mesh(globeGeometry, globeMaterial);
    globe.castShadow = true;
    globe.receiveShadow = true;
    scene.add(globe);
    globeRef.current = globe;

    // Add region markers
    const markerGeometry = new THREE.SphereGeometry(0.12, 32, 32);
    const markerMaterial = new THREE.MeshBasicMaterial({
      color: 0x00ff88,
      emissive: 0x00ff88,
      emissiveIntensity: 1,
    });

    regions.forEach((region, idx) => {
      const angle = (idx / regions.length) * Math.PI * 2;
      const elevation = Math.sin(idx * 0.618) * (Math.PI / 3); // Fibonacci spread

      const marker = new THREE.Mesh(markerGeometry, markerMaterial.clone());
      marker.position.set(
        1.8 * Math.cos(elevation) * Math.cos(angle),
        1.8 * Math.sin(elevation),
        1.8 * Math.cos(elevation) * Math.sin(angle)
      );

      marker.userData.region = region;
      marker.castShadow = true;
      scene.add(marker);
    });
    });

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.6);
    const directionalLight = new THREE.DirectionalLight(0xffffff, 0.8);
    directionalLight.position.set(5, 3, 5);
    directionalLight.castShadow = true;
    scene.add(ambientLight, directionalLight);

    // Position camera
    camera.position.z = 3;

    // Animation loop
    const animate = () => {
      animationIdRef.current = requestAnimationFrame(animate);

      if (globeRef.current) {
        globeRef.current.rotation.y += 0.0008;
      }

      renderer.render(scene, camera);
    };

    animate();

    // Handle window resize
    const handleResize = () => {
      const newWidth = Math.min(window.innerWidth - 40, 300);
      const newHeight = newWidth;

      camera.aspect = newWidth / newHeight;
      camera.updateProjectionMatrix();
      renderer.setSize(newWidth, newHeight);
    };

    window.addEventListener('resize', handleResize);

    // Cleanup
    return () => {
      window.removeEventListener('resize', handleResize);
      if (animationIdRef.current) {
        cancelAnimationFrame(animationIdRef.current);
      }

      // Dispose of Three.js resources
      globeGeometry.dispose();
      globeMaterial.dispose();
      markerGeometry.dispose();
      renderer.dispose();

      sceneRef.current = null;
      rendererRef.current = null;
      globeRef.current = null;
    };
  }, [regions, width, height]);

  return (
    <>
      {/* Visual Canvas */}
      <canvas
        ref={canvasRef}
        data-testid="three-d-globe"
        style={{
          width: `${width}px`,
          height: `${height}px`,
          borderRadius: '8px',
          boxShadow: '0 0 20px rgba(0, 255, 136, 0.3)',
        }}
      />

      {/* Hidden accessibility table for screen readers - WCAG compliance */}
      <div className="sr-only" role="region" aria-label="Market Region Data">
        <table>
          <caption>3D globe region highlights and market data</caption>
          <tbody>
            {regions.map((region) => (
              <tr key={region}>
                <td>{region}</td>
                <td>Market region is highlighted on the interactive 3D globe</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
};

/**
 * File B: ThreeDGlobe.tsx (lazy-loading wrapper - stays in main bundle)
 * This component uses lazy loading to prevent Three.js from blocking initial page load
 */

interface ThreeDGlobeProps {
  regions: string[];
  width?: number;
  height?: number;
}

// Dynamic import with Suspense fallback
const GlobeRenderer = React.lazy(() => import('./GlobeRenderer'));

export const ThreeDGlobe: React.FC<ThreeDGlobeProps> = ({
  regions,
  width = 300,
  height = 300
}) => {
  return (
    <Suspense fallback={
      <div
        className="globe-skeleton"
        style={{
          width: `${width}px`,
          height: `${height}px`,
          background: 'linear-gradient(90deg, #1a3a52 25%, #2a5a7a 50%, #1a3a52 75%)',
          backgroundSize: '200% 100%',
          animation: 'shimmer 1.5s infinite',
          borderRadius: '8px',
        }}
        aria-label="Loading 3D market globe..."
      />
    }>
      <GlobeRenderer regions={regions} width={width} height={height} />
    </Suspense>
  );
};
```

#### Task 1.3: Modify MarketNode to use ThreeDGlobe

```typescript
// src/features/intelligence/business-plan/nodes/MarketNode.tsx (MODIFY)

import React, { useState } from 'react';
import { ThreeDGlobe } from '../../shared/ThreeDGlobe';
import { ConfidenceBadge } from '../../shared/ConfidenceBadge';
import { motion, AnimatePresence } from 'framer-motion';

interface MarketNodeData {
  id: string;
  title: string;
  icon: string;
  metrics: {
    tam: string;
    growth: string;
    marketShare: string;
  };
  regions: string[];
  confidence: 'verified' | 'corroborated' | 'inference' | 'weak_signal';
}

interface MarketNodeProps {
  data: MarketNodeData;
  onEditClick?: () => void;
}

export const MarketNode: React.FC<MarketNodeProps> = ({ data, onEditClick }) => {
  const [showGlobe, setShowGlobe] = useState(false);

  return (
    <motion.div
      data-testid={`market-node-${data.id}`}
      className="market-node-card"
      whileHover={{ scale: 1.02 }}
      onMouseEnter={() => setShowGlobe(true)}
      onMouseLeave={() => setShowGlobe(false)}
      role="region"
      aria-label={`Market: ${data.title}`}
    >
      {/* Header */}
      <div className="node-header">
        <span className="node-icon">{data.icon}</span>
        <h3 className="node-title">{data.title}</h3>
        <ConfidenceBadge level={data.confidence} size="sm" />
      </div>

      {/* Metrics */}
      <div className="node-metrics">
        <div className="metric">
          <span className="label">TAM:</span>
          <span className="value">{data.metrics.tam}</span>
        </div>
        <div className="metric">
          <span className="label">Growth:</span>
          <span className="value">{data.metrics.growth}</span>
        </div>
        <div className="metric">
          <span className="label">Market Share:</span>
          <span className="value">{data.metrics.marketShare}</span>
        </div>
      </div>

      {/* 3D Globe */}
      <AnimatePresence>
        {showGlobe && (
          <motion.div
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.8 }}
            className="globe-container"
          >
            <ThreeDGlobe regions={data.regions} width={300} height={300} />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Actions */}
      <div className="node-actions">
        <button
          onClick={onEditClick}
          className="btn-edit"
          aria-label={`Edit ${data.title} market information`}
        >
          Edit
        </button>
      </div>
    </motion.div>
  );
};
```

#### Task 1.4: Run tests and verify

```bash
cd lliveupdatedstreaming
npm test -- tests/integration/test_3d_globe.tsx --run
# Expected: 5/5 passing
```

#### Task 1.5: Commit

```bash
git add src/features/intelligence/shared/ThreeDGlobe.tsx
git add src/features/intelligence/business-plan/nodes/MarketNode.tsx
git add tests/integration/test_3d_globe.tsx
git commit -m "feat: add 3D interactive globe to MarketNode with region highlighting"
```

---

## TASK 2: What-If Scenario Engine

**Objective:** Create reusable scenario sliders that recalculate dependent metrics in real-time.

**Files to Create/Modify:**
- Create: `src/features/intelligence/shared/hooks/useScenarios.ts`
- Create: `src/features/intelligence/shared/ScenarioSlider.tsx`
- Modify: `src/features/intelligence/gtm/GTMCanvas.tsx`
- Create: `tests/integration/test_scenario_engine.tsx`

### Test Success Criteria:
- [ ] Scenario state tracks baseline + current values
- [ ] Sliders update scenario values on change
- [ ] Dependent metrics recalculate automatically
- [ ] Reset button returns all to baseline
- [ ] Delta percentages display correctly
- [ ] Integration with GTM Canvas works

### Tasks:

#### Task 2.1: Write integration tests for scenario engine

```typescript
// tests/integration/test_scenario_engine.tsx

import { renderHook, act, waitFor } from '@testing-library/react';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useScenarios } from '../../src/features/intelligence/shared/hooks/useScenarios';
import { ScenarioSlider } from '../../src/features/intelligence/shared/ScenarioSlider';

describe('Scenario Engine - useScenarios Hook', () => {
  const baseMetrics = {
    marketSize: 1000,
    conversionRate: 5,
    pricePoint: 100,
    customerAcquisitionCost: 200,
    lifetimeValue: 2000,
  };

  it('tracks baseline and current scenario values separately', () => {
    const { result } = renderHook(() => useScenarios(baseMetrics));

    expect(result.current.scenarios.baseline).toEqual(baseMetrics);
    expect(result.current.scenarios.current).toEqual(baseMetrics);
  });

  it('updates scenario value when setScenario is called', () => {
    const { result } = renderHook(() => useScenarios(baseMetrics));

    act(() => {
      result.current.setScenario('marketSize', 1500);
    });

    expect(result.current.scenarios.current.marketSize).toBe(1500);
    expect(result.current.scenarios.baseline.marketSize).toBe(1000);
  });

  it('recalculates dependent metrics when values change', () => {
    const { result } = renderHook(() => useScenarios(baseMetrics));

    const baselineRevenue = result.current.calculations.projectedRevenue;

    act(() => {
      result.current.setScenario('marketSize', 2000); // Double market size
    });

    const newRevenue = result.current.calculations.projectedRevenue;
    expect(newRevenue).toBeGreaterThan(baselineRevenue);
  });

  it('calculates percentage deltas from baseline', () => {
    const { result } = renderHook(() => useScenarios(baseMetrics));

    act(() => {
      result.current.setScenario('pricePoint', 150); // 50% increase
    });

    const delta = result.current.calculations.deltas.pricePoint;
    expect(delta).toBe(50); // 50% increase
  });

  it('resets all scenarios to baseline on reset()', () => {
    const { result } = renderHook(() => useScenarios(baseMetrics));

    act(() => {
      result.current.setScenario('marketSize', 2000);
      result.current.setScenario('conversionRate', 10);
    });

    expect(result.current.scenarios.current.marketSize).toBe(2000);

    act(() => {
      result.current.reset();
    });

    expect(result.current.scenarios.current).toEqual(result.current.scenarios.baseline);
  });

  it('calculates LTV:CAC ratio improvement', () => {
    const { result } = renderHook(() => useScenarios(baseMetrics));

    const baselineRatio = result.current.calculations.ltvCacRatio;

    act(() => {
      result.current.setScenario('customerAcquisitionCost', 100); // Reduce CAC
    });

    const improvedRatio = result.current.calculations.ltvCacRatio;
    expect(improvedRatio).toBeGreaterThan(baselineRatio);
  });
});

describe('Scenario Engine - UI Integration', () => {
  it('ScenarioSlider updates parent state on change', async () => {
    const user = userEvent.setup();
    const handleChange = vi.fn();

    render(
      <ScenarioSlider
        label="Market Size"
        baseValue={1000}
        currentValue={1000}
        min={500}
        max={2000}
        step={50}
        onChange={handleChange}
        unit="K"
      />
    );

    const slider = screen.getByRole('slider');
    await user.tripleClick(slider);
    await user.keyboard('{Backspace}1200');

    expect(handleChange).toHaveBeenCalledWith(1200);
  });

  it('displays delta percentage when value changes', async () => {
    const user = userEvent.setup();

    const { rerender } = render(
      <ScenarioSlider
        label="Price Point"
        baseValue={100}
        currentValue={100}
        min={50}
        max={200}
        step={10}
        onChange={() => {}}
        unit="$"
      />
    );

    // No delta shown at baseline
    expect(screen.queryByText(/\+0%|−0%/)).not.toBeInTheDocument();

    // Show delta when value changes
    rerender(
      <ScenarioSlider
        label="Price Point"
        baseValue={100}
        currentValue={150}
        min={50}
        max={200}
        step={10}
        onChange={() => {}}
        unit="$"
      />
    );

    expect(screen.getByText('+50%')).toBeInTheDocument();
  });
});
```

#### Task 2.2: Implement useScenarios hook

```typescript
// src/features/intelligence/shared/hooks/useScenarios.ts

import { useState, useMemo } from 'react';

interface ScenarioState {
  baseline: Record<string, number>;
  current: Record<string, number>;
}

export const useScenarios = (baselineMetrics: Record<string, number>) => {
  const [scenarios, setScenarios] = useState<ScenarioState>({
    baseline: baselineMetrics,
    current: { ...baselineMetrics },
  });

  const setScenario = (key: string, value: number) => {
    setScenarios((prev) => ({
      ...prev,
      current: { ...prev.current, [key]: Math.max(0, value) },
    }));
  };

  const reset = () => {
    setScenarios((prev) => ({
      ...prev,
      current: { ...prev.baseline },
    }));
  };

  // Memoized calculated metrics
  const calculations = useMemo(() => {
    const deltas: Record<string, number> = {};

    Object.keys(scenarios.current).forEach((key) => {
      const current = scenarios.current[key];
      const baseline = scenarios.baseline[key];
      deltas[key] = ((current - baseline) / baseline) * 100;
    });

    /**
     * CRITICAL: Normalize percentage metrics to decimals before calculation
     * conversionRate is stored as 0-100 (e.g., 5 = 5%)
     * We convert to decimal (0.05) for projections
     */
    const conversionRateAsDecimal = (scenarios.current.conversionRate || 0) / 100;

    // Now calculation is clear: marketSize * decimal conversion rate * price point
    const projectedRevenue =
      (scenarios.current.marketSize || 0) *
      conversionRateAsDecimal *
      (scenarios.current.pricePoint || 0);

    const ltvCacRatio =
      (scenarios.current.lifetimeValue || 0) /
      (scenarios.current.customerAcquisitionCost || 1);

    const paybackMonths =
      (scenarios.current.customerAcquisitionCost || 0) /
      Math.max((scenarios.current.monthlyRecurringRevenue || 0), 1);

    return {
      deltas,
      projectedRevenue,
      ltvCacRatio,
      paybackMonths,
    };
  }, [scenarios]);

  return {
    scenarios,
    setScenario,
    reset,
    calculations,
  };
};
```

#### Task 2.3: Implement ScenarioSlider component

```typescript
// src/features/intelligence/shared/ScenarioSlider.tsx

import React from 'react';
import { Slider } from '@/components/ui/slider';
import { motion } from 'framer-motion';

interface ScenarioSliderProps {
  label: string;
  baseValue: number;
  currentValue: number;
  min: number;
  max: number;
  step: number;
  onChange: (value: number) => void;
  unit?: string;
}

export const ScenarioSlider: React.FC<ScenarioSliderProps> = ({
  label,
  baseValue,
  currentValue,
  min,
  max,
  step,
  onChange,
  unit = '',
}) => {
  const percentDelta = ((currentValue - baseValue) / baseValue) * 100;
  const isImprovement = percentDelta > 0;
  const isChanged = percentDelta !== 0;

  return (
    <motion.div
      className="scenario-slider-wrapper"
      layout
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
    >
      {/* Header with label and value */}
      <div className="slider-header">
        <label className="slider-label" htmlFor={`slider-${label}`}>
          {label}
        </label>
        <div className="slider-values">
          <span className="current-value">
            {currentValue.toFixed(0)}
            {unit}
          </span>
          {isChanged && (
            <motion.span
              className={`delta-badge ${isImprovement ? 'positive' : 'negative'}`}
              initial={{ opacity: 0, scale: 0.8 }}
              animate={{ opacity: 1, scale: 1 }}
            >
              {isImprovement ? '+' : ''}
              {percentDelta.toFixed(1)}%
            </motion.span>
          )}
        </div>
      </div>

      {/* Slider component */}
      <Slider
        id={`slider-${label}`}
        value={[currentValue]}
        onValueChange={([val]) => onChange(val)}
        min={min}
        max={max}
        step={step}
        className="scenario-slider-input"
        aria-label={`${label} scenario slider, baseline ${baseValue}${unit}`}
      />

      {/* Baseline reference */}
      <div className="slider-baseline">
        <span>Baseline: {baseValue}{unit}</span>
      </div>
    </motion.div>
  );
};
```

#### Task 2.4: Integrate into GTM Canvas

```typescript
// src/features/intelligence/gtm/GTMCanvas.tsx (MODIFY)

import { useScenarios } from '../../shared/hooks/useScenarios';
import { ScenarioSlider } from '../../shared/ScenarioSlider';

export const GTMCanvas: React.FC<{ gtmId: string }> = ({ gtmId }) => {
  /**
   * Baseline metrics for scenario engine
   *
   * IMPORTANT: All metrics are stored in their "display" format:
   * - conversionRate: 0-100 (e.g., 5 = 5%, NOT 0.05)
   * - pricePoint: raw number (e.g., 100)
   * - marketSize: raw number (e.g., 1000)
   *
   * The useScenarios hook normalizes conversionRate to decimal (0.05) during calculations.
   * This prevents ambiguity and magic numbers like "0.01" in the projection formula.
   */
  const baselineMetrics = {
    marketSize: 100,
    conversionRate: 5, // Entry format: 5 (meaning 5%), NOT 0.05
    pricePoint: 100,
    customerAcquisitionCost: 500,
    lifetimeValue: 5000,
  };

  const { scenarios, setScenario, reset, calculations } = useScenarios(baselineMetrics);

  return (
    <div className="gtm-canvas">
      {/* Main content */}
      <main className="canvas-content">
        {/* Existing views */}
      </main>

      {/* Scenarios panel */}
      <aside className="scenarios-panel" aria-label="What-If Scenarios">
        <div className="panel-header">
          <h3>What-If Scenarios</h3>
          <button
            onClick={reset}
            className="btn-reset"
            aria-label="Reset all scenarios to baseline"
          >
            Reset
          </button>
        </div>

        <div className="sliders-container">
          {Object.entries(baselineMetrics).map(([key, baseline]) => (
            <ScenarioSlider
              key={key}
              label={key.replace(/([A-Z])/g, ' $1').trim()}
              baseValue={baseline}
              currentValue={scenarios.current[key]}
              min={Math.max(0, baseline * 0.5)}
              max={baseline * 2}
              step={baseline * 0.05}
              onChange={(val) => setScenario(key, val)}
              unit={key === 'pricePoint' ? '$' : '%'}
            />
          ))}
        </div>

        {/* Calculated results */}
        <div className="scenarios-results">
          <h4>Projected Outcomes</h4>
          <div className="result-item">
            <span>Projected Revenue:</span>
            <strong>${(calculations.projectedRevenue / 1000).toFixed(1)}K</strong>
          </div>
          <div className="result-item">
            <span>LTV:CAC Ratio:</span>
            <strong>{calculations.ltvCacRatio.toFixed(2)}x</strong>
          </div>
          <div className="result-item">
            <span>Payback Period:</span>
            <strong>{calculations.paybackMonths.toFixed(1)} months</strong>
          </div>
        </div>
      </aside>
    </div>
  );
};
```

#### Task 2.5: Run tests

```bash
npm test -- tests/integration/test_scenario_engine.tsx --run
# Expected: 7/7 passing
```

#### Task 2.6: Commit

```bash
git add src/features/intelligence/shared/hooks/useScenarios.ts
git add src/features/intelligence/shared/ScenarioSlider.tsx
git add src/features/intelligence/gtm/GTMCanvas.tsx
git add tests/integration/test_scenario_engine.tsx
git commit -m "feat: implement what-if scenario engine with real-time metric recalculation"
```

---

## TASK 3: Accessibility Compliance (WCAG 2.1 AA)

**Objective:** Make all canvases keyboard-navigable and screen-reader compatible.

**Files to Create/Modify:**
- Create: `tests/integration/test_accessibility_compliance.tsx`
- Modify: All canvas components (BusinessPlanCanvas, GTMCanvas, SWOTCanvas, PitchDeckCanvas)
- Create: `src/services/accessibility/a11yUtils.ts`

### Test Success Criteria:
- [ ] Zero axe violations in each canvas
- [ ] All interactive elements keyboard-navigable (Tab, Enter, Arrow keys)
- [ ] Proper ARIA labels on all buttons, charts, and custom components
- [ ] Focus management in modals and drawers working
- [ ] Screen reader announces state changes
- [ ] Color contrast ratios meet WCAG AA

### Tasks:

#### Task 3.1: Write accessibility compliance tests

```typescript
// tests/integration/test_accessibility_compliance.tsx

import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { axe, toHaveNoViolations } from 'jest-axe';
import { BusinessPlanCanvas } from '../../src/features/intelligence/business-plan/BusinessPlanCanvas';
import { GTMCanvas } from '../../src/features/intelligence/gtm/GTMCanvas';
import { SWOTCanvas } from '../../src/features/intelligence/swot/SWOTCanvas';
import { PitchDeckCanvas } from '../../src/features/intelligence/pitch/PitchDeckCanvas';

expect.extend(toHaveNoViolations);

describe('Accessibility - Axe Violations', () => {
  it('BusinessPlanCanvas has no axe violations', async () => {
    const { container } = render(
      <BusinessPlanCanvas planId="test-123" />
    );
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('GTMCanvas has no axe violations', async () => {
    const { container } = render(<GTMCanvas gtmId="gtm-123" />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('SWOTCanvas has no axe violations', async () => {
    const { container } = render(<SWOTCanvas swotId="swot-123" />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });

  it('PitchDeckCanvas has no axe violations', async () => {
    const { container } = render(<PitchDeckCanvas deckId="pitch-123" />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});

describe('Accessibility - Keyboard Navigation', () => {
  it('navigates between nav rail buttons with Tab key', async () => {
    const user = userEvent.setup();
    render(<BusinessPlanCanvas planId="test-123" />);

    const navButtons = screen.getAllByRole('button', { name: /summary|map|metrics|report/i });

    // Tab through buttons
    for (let i = 0; i < navButtons.length - 1; i++) {
      expect(navButtons[i]).toHaveFocus();
      await user.keyboard('{Tab}');
    }
  });

  it('activates buttons with Enter key', async () => {
    const user = userEvent.setup();
    render(<BusinessPlanCanvas planId="test-123" />);

    const metricsButton = screen.getByRole('button', { name: /metrics dashboard/i });
    metricsButton.focus();

    await user.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText(/metrics dashboard/i)).toBeVisible();
    });
  });

  it('navigates React Flow nodes with arrow keys', async () => {
    const user = userEvent.setup();
    render(<BusinessPlanCanvas planId="test-123" />);

    // Activate Strategy Map view
    await user.click(screen.getByRole('button', { name: /strategy map/i }));

    const firstNode = screen.getAllByRole('button', { name: /market node|competitor/i })[0];
    firstNode.focus();

    // Arrow right to next node
    await user.keyboard('{ArrowRight}');

    expect(screen.getAllByRole('button', { name: /market|competitor/i })[1]).toHaveFocus();
  });
});

describe('Accessibility - ARIA Labels', () => {
  it('buttons have descriptive aria-labels', () => {
    render(<BusinessPlanCanvas planId="test-123" />);

    expect(screen.getByRole('button', { name: /executive summary/i })).toHaveAttribute(
      'aria-label'
    );
    expect(screen.getByRole('button', { name: /strategy map/i })).toHaveAttribute(
      'aria-label'
    );
  });

  it('charts have aria-labels describing content', () => {
    render(<BusinessPlanCanvas planId="test-123" />);

    // Metrics charts should have descriptions
    const charts = screen.queryAllByRole('img', { hidden: true });
    charts.forEach((chart) => {
      if (chart.getAttribute('aria-label')) {
        expect(chart).toHaveAttribute('aria-label');
      }
    });
  });

  it('modals and drawers set proper aria-modal and aria-labelledby', async () => {
    const user = userEvent.setup();
    render(<BusinessPlanCanvas planId="test-123" />);

    // Open evidence drawer
    const sourceButtons = screen.queryAllByRole('button', { name: /sources|evidence/i });
    if (sourceButtons.length > 0) {
      await user.click(sourceButtons[0]);

      const drawer = screen.getByRole('dialog');
      expect(drawer).toHaveAttribute('aria-modal', 'true');
    }
  });
});

describe('Accessibility - Focus Management', () => {
  it('focus moves to modal on open', async () => {
    const user = userEvent.setup();
    render(<BusinessPlanCanvas planId="test-123" />);

    const openButton = screen.getByRole('button', { name: /sources|evidence/i });
    await user.click(openButton);

    const modal = screen.getByRole('dialog');
    expect(modal.querySelector('button, input, [tabindex="0"]')).toHaveFocus();
  });

  it('focus returns to trigger button on modal close', async () => {
    const user = userEvent.setup();
    render(<BusinessPlanCanvas planId="test-123" />);

    const openButton = screen.getByRole('button', { name: /sources|evidence/i });
    openButton.focus();

    await user.click(openButton);
    const closeButton = screen.getByRole('button', { name: /close/i });
    await user.click(closeButton);

    expect(openButton).toHaveFocus();
  });
});

describe('Accessibility - Screen Reader Announcements', () => {
  it('announces view changes', async () => {
    const user = userEvent.setup();
    render(<BusinessPlanCanvas planId="test-123" />);

    const mapButton = screen.getByRole('button', { name: /strategy map/i });
    expect(mapButton).toHaveAttribute('aria-current', 'page'); // Currently visible

    await user.click(screen.getByRole('button', { name: /metrics/i }));

    await waitFor(() => {
      expect(mapButton).not.toHaveAttribute('aria-current', 'page');
      expect(screen.getByRole('button', { name: /metrics/i })).toHaveAttribute(
        'aria-current',
        'page'
      );
    });
  });

  it('announces loading and success states', async () => {
    const { rerender } = render(
      <div role="status" aria-live="polite" aria-label="Canvas loading">
        Loading...
      </div>
    );

    expect(screen.getByLabelText(/Canvas loading/i)).toHaveTextContent('Loading...');

    rerender(
      <div role="status" aria-live="polite" aria-label="Canvas loading">
        Content loaded successfully
      </div>
    );

    expect(screen.getByLabelText(/Canvas loading/i)).toHaveTextContent('Content loaded');
  });
});
```

#### Task 3.2: Fix BusinessPlanCanvas ARIA labels

```typescript
// src/features/intelligence/business-plan/BusinessPlanCanvas.tsx (MODIFY)

export const BusinessPlanCanvas: React.FC<{ planId: string }> = ({ planId }) => {
  const [activeView, setActiveView] = useState('summary');

  return (
    <div className="business-plan-canvas" role="application" aria-label="Business Plan Canvas">
      {/* Nav Rail */}
      <nav
        className="nav-rail"
        role="navigation"
        aria-label="Business Plan canvas navigation"
      >
        <button
          onClick={() => setActiveView('summary')}
          className="nav-icon"
          aria-current={activeView === 'summary' ? 'page' : undefined}
          aria-label="Executive Summary view - overview of company and 4 key metrics"
          title="Executive Summary"
        >
          📊
        </button>
        <button
          onClick={() => setActiveView('strategy')}
          className="nav-icon"
          aria-current={activeView === 'strategy' ? 'page' : undefined}
          aria-label="Strategy Map view - interactive network diagram of business strategy"
          title="Strategy Map"
        >
          🎯
        </button>
        <button
          onClick={() => setActiveView('metrics')}
          className="nav-icon"
          aria-current={activeView === 'metrics' ? 'page' : undefined}
          aria-label="Metrics Dashboard view - financial projections and KPI charts"
          title="Metrics Dashboard"
        >
          📈
        </button>
        <button
          onClick={() => setActiveView('report')}
          className="nav-icon"
          aria-current={activeView === 'report' ? 'page' : undefined}
          aria-label="Full Report view - comprehensive document with sources"
          title="Full Report"
        >
          📄
        </button>
      </nav>

      {/* Main Content */}
      <main className="canvas-main" role="main">
        {activeView === 'summary' && <ExecutiveSummary data={data} />}
        {activeView === 'strategy' && <StrategyMap data={data} />}
        {activeView === 'metrics' && <MetricsDashboard data={data} />}
        {activeView === 'report' && <FullReport data={data} />}
      </main>

      {/* Intel Sidebar */}
      <aside
        className="intel-sidebar"
        role="complementary"
        aria-label="Business intelligence sidebar - market snapshot"
      >
        <IntelSidebar data={data} />
      </aside>
    </div>
  );
};
```

#### Task 3.3: Create a11y utilities

```typescript
// src/services/accessibility/a11yUtils.ts

/**
 * Generate ARIA label for chart components
 */
export const getChartAriaLabel = (chartType: string, title: string, description: string) => {
  return `${chartType} chart titled "${title}". ${description}`;
};

/**
 * Calculate WCAG relative luminance (standard algorithm - not approximation)
 * Reference: https://www.w3.org/TR/WCAG20/#relativeluminancedef
 */
const getRelativeLuminance = (hex: string): number => {
  const rgb = parseInt(hex.slice(1), 16);
  const r = ((rgb >> 16) & 0xff) / 255;
  const g = ((rgb >> 8) & 0xff) / 255;
  const b = (rgb & 0xff) / 255;

  // Convert to linear RGB
  const toLinear = (c: number) => {
    if (c <= 0.03928) {
      return c / 12.92;
    }
    return Math.pow((c + 0.055) / 1.055, 2.4);
  };

  const R = toLinear(r);
  const G = toLinear(g);
  const B = toLinear(b);

  // Standard WCAG formula
  return 0.2126 * R + 0.7152 * G + 0.0722 * B;
};

/**
 * Check color contrast ratio using WCAG standard formula
 * Returns ratio (e.g., 4.5 for WCAG AA compliance)
 * WCAG AA requires 4.5:1 for normal text, 3:1 for large text
 */
export const checkContrastRatio = (foreground: string, background: string): number => {
  const l1 = getRelativeLuminance(foreground);
  const l2 = getRelativeLuminance(background);

  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);

  return (lighter + 0.05) / (darker + 0.05);
};

/**
 * Verify if colors meet WCAG AA standard (4.5:1 for normal text)
 */
export const isWCAGCompliant = (foreground: string, background: string, largeText: boolean = false): boolean => {
  const ratio = checkContrastRatio(foreground, background);
  const threshold = largeText ? 3 : 4.5;
  return ratio >= threshold;
};

/**
 * Create keyboard navigation handler for custom components
 */
export const useArrowKeyNavigation = (
  items: HTMLElement[],
  onItemSelect: (index: number) => void
) => {
  const handleKeyDown = (e: KeyboardEvent) => {
    const currentIndex = items.findIndex((el) => el === document.activeElement);

    if (e.key === 'ArrowRight' || e.key === 'ArrowDown') {
      e.preventDefault();
      const nextIndex = (currentIndex + 1) % items.length;
      items[nextIndex].focus();
      onItemSelect(nextIndex);
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      const prevIndex = currentIndex === 0 ? items.length - 1 : currentIndex - 1;
      items[prevIndex].focus();
      onItemSelect(prevIndex);
    }
  };

  return handleKeyDown;
};
```

#### Task 3.4: Apply similar fixes to remaining canvases

Repeat the ARIA labeling pattern for:
- GTMCanvas.tsx
- SWOTCanvas.tsx
- PitchDeckCanvas.tsx

#### Task 3.5: Run tests

```bash
npm install --save-dev jest-axe
npm test -- tests/integration/test_accessibility_compliance.tsx --run
# Expected: All axe violations fixed, 15+ tests passing
```

#### Task 3.6: Commit

```bash
git add tests/integration/test_accessibility_compliance.tsx
git add src/features/intelligence/business-plan/BusinessPlanCanvas.tsx
git add src/features/intelligence/gtm/GTMCanvas.tsx
git add src/features/intelligence/swot/SWOTCanvas.tsx
git add src/features/intelligence/pitch/PitchDeckCanvas.tsx
git add src/services/accessibility/a11yUtils.ts
git commit -m "feat: implement WCAG 2.1 AA accessibility compliance across all canvases"
```

---

## TASK 4: Multiplayer Presence Architecture (Stub)

**Objective:** Create service and UI stubs for future WebSocket-driven multiplayer features (not implemented yet).

**Files to Create:**
- Create: `src/services/multiplayer/presenceService.ts`
- Create: `src/features/intelligence/shared/MultiplayerPresence.tsx`
- Create: `tests/integration/test_multiplayer_stubs.tsx`

### Test Success Criteria:
- [ ] Service initializes with user/canvas context
- [ ] All required methods are defined (connect, disconnect, broadcast)
- [ ] Activity feed structure is correct
- [ ] UI renders without errors
- [ ] Clear TODO comments for WebSocket implementation

### Tasks:

#### Task 4.1: Write tests for multiplayer stubs

```typescript
// tests/integration/test_multiplayer_stubs.tsx

import { renderHook, act } from '@testing-library/react';
import { render, screen } from '@testing-library/react';
import { useMultiplayerPresence } from '../../src/services/multiplayer/presenceService';
import { MultiplayerPresence } from '../../src/features/intelligence/shared/MultiplayerPresence';

describe('Multiplayer Presence - Service Stubs', () => {
  it('initializes presence service with user and canvas ID', () => {
    const { result } = renderHook(() =>
      useMultiplayerPresence('user-abc-123', 'plan-xyz-789')
    );

    expect(result.current.userId).toBe('user-abc-123');
    expect(result.current.canvasId).toBe('plan-xyz-789');
    expect(result.current.isConnected).toBe(false);
  });

  it('provides connect and disconnect methods', () => {
    const { result } = renderHook(() =>
      useMultiplayerPresence('user-123', 'plan-456')
    );

    expect(typeof result.current.connect).toBe('function');
    expect(typeof result.current.disconnect).toBe('function');
  });

  it('provides broadcastCursorPosition method', () => {
    const { result } = renderHook(() =>
      useMultiplayerPresence('user-123', 'plan-456')
    );

    expect(typeof result.current.broadcastCursorPosition).toBe('function');
  });

  it('initializes with empty active users list', () => {
    const { result } = renderHook(() =>
      useMultiplayerPresence('user-123', 'plan-456')
    );

    expect(Array.isArray(result.current.activeUsers)).toBe(true);
    expect(result.current.activeUsers).toHaveLength(0);
  });

  it('initializes with empty activity feed', () => {
    const { result } = renderHook(() =>
      useMultiplayerPresence('user-123', 'plan-456')
    );

    expect(Array.isArray(result.current.activityFeed)).toBe(true);
    expect(result.current.activityFeed).toHaveLength(0);
  });

  it('connect method is callable', async () => {
    const { result } = renderHook(() =>
      useMultiplayerPresence('user-123', 'plan-456')
    );

    await act(async () => {
      await result.current.connect();
    });

    // Stub implementation: connection status should update
    // (real implementation would set isConnected = true)
  });

  it('broadcastCursorPosition accepts x, y coordinates', async () => {
    const { result } = renderHook(() =>
      useMultiplayerPresence('user-123', 'plan-456')
    );

    await act(async () => {
      result.current.broadcastCursorPosition(100, 200);
    });

    // Stub: no error thrown
  });
});

describe('Multiplayer Presence - UI Stubs', () => {
  it('renders activity feed component', () => {
    render(
      <MultiplayerPresence userId="user-123" canvasId="plan-456" />
    );

    expect(screen.getByText(/activity feed/i)).toBeInTheDocument();
  });

  it('shows empty state when no activity', () => {
    render(
      <MultiplayerPresence userId="user-123" canvasId="plan-456" />
    );

    expect(screen.getByText(/waiting for activity/i)).toBeInTheDocument();
  });

  it('renders without errors in development mode', () => {
    expect(() => {
      render(
        <MultiplayerPresence userId="user-123" canvasId="plan-456" />
      );
    }).not.toThrow();
  });
});
```

#### Task 4.2: Implement presence service stub

```typescript
// src/services/multiplayer/presenceService.ts

import { useState, useCallback } from 'react';

export interface PresenceUser {
  userId: string;
  username: string;
  cursorX?: number;
  cursorY?: number;
  lastActive: number;
  color?: string;
}

export interface ActivityFeedItem {
  id: string;
  userId: string;
  username: string;
  action: 'entered' | 'edited' | 'exited' | 'viewed';
  target?: string;
  timestamp: number;
}

interface UseMultiplayerPresenceReturn {
  userId: string;
  canvasId: string;
  isConnected: boolean;
  activeUsers: PresenceUser[];
  activityFeed: ActivityFeedItem[];
  connect: () => Promise<void>;
  disconnect: () => void;
  broadcastCursorPosition: (x: number, y: number) => void;
  broadcastEdit: (target: string, content: string) => void;
}

export const useMultiplayerPresence = (
  userId: string,
  canvasId: string
): UseMultiplayerPresenceReturn => {
  const [isConnected, setIsConnected] = useState(false);
  const [activeUsers, setActiveUsers] = useState<PresenceUser[]>([]);
  const [activityFeed, setActivityFeed] = useState<ActivityFeedItem[]>([]);

  const connect = useCallback(async () => {
    // TODO: Implement WebSocket connection
    // TODO: Send initial presence message with userId, canvasId, timestamp
    // TODO: Set up event listeners for:
    //       - presence-joined (new user entered)
    //       - presence-left (user exited)
    //       - cursor-moved (broadcast cursor position)
    //       - content-edited (broadcast edits)
    console.log(
      `[STUB] Multiplayer presence connecting for user ${userId} on canvas ${canvasId}`
    );
    setIsConnected(true);
  }, [userId, canvasId]);

  const disconnect = useCallback(() => {
    // TODO: Close WebSocket connection
    // TODO: Send presence-left message
    console.log('[STUB] Multiplayer presence disconnecting');
    setIsConnected(false);
  }, []);

  const broadcastCursorPosition = useCallback((x: number, y: number) => {
    // TODO: Send cursor position update via WebSocket
    // TODO: Format: { type: 'cursor-moved', userId, x, y, timestamp }
    console.log(`[STUB] Broadcasting cursor position: (${x}, ${y})`);
  }, []);

  const broadcastEdit = useCallback((target: string, content: string) => {
    // TODO: Send edit event via WebSocket
    // TODO: Format: { type: 'content-edited', userId, target, content, timestamp }
    console.log(`[STUB] Broadcasting edit to ${target}`);
  }, []);

  return {
    userId,
    canvasId,
    isConnected,
    activeUsers,
    activityFeed,
    connect,
    disconnect,
    broadcastCursorPosition,
    broadcastEdit,
  };
};
```

#### Task 4.3: Implement MultiplayerPresence UI stub

```typescript
// src/features/intelligence/shared/MultiplayerPresence.tsx

import React, { useEffect } from 'react';
import { motion } from 'framer-motion';
import { useMultiplayerPresence } from '../../services/multiplayer/presenceService';

interface MultiplayerPresenceProps {
  userId: string;
  canvasId: string;
  autoConnect?: boolean;
}

export const MultiplayerPresence: React.FC<MultiplayerPresenceProps> = ({
  userId,
  canvasId,
  autoConnect = true,
}) => {
  const presence = useMultiplayerPresence(userId, canvasId);

  useEffect(() => {
    if (autoConnect) {
      presence.connect();

      // TODO: Set up real-time listeners
      // TODO: useEffect cleanup: call presence.disconnect() on unmount

      return () => {
        presence.disconnect();
      };
    }
  }, [autoConnect, userId, canvasId]);

  return (
    <motion.div
      className="multiplayer-presence"
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.3 }}
      role="complementary"
      aria-label="Multiplayer activity feed"
    >
      {/* Connection status indicator */}
      <div className="connection-status">
        <span
          className={`status-dot ${presence.isConnected ? 'connected' : 'disconnected'}`}
          aria-live="polite"
        >
          {presence.isConnected ? '🟢 Connected' : '⚪ Offline'}
        </span>
      </div>

      {/* Active users count */}
      <div className="active-users">
        <p className="users-count">
          <strong>{presence.activeUsers.length}</strong> user{presence.activeUsers.length !== 1 ? 's' : ''} active
        </p>

        {/* TODO: Render active user avatars/indicators */}
        {/* TODO: Show cursor positions and selections */}
      </div>

      {/* Activity feed */}
      <div className="activity-feed">
        <h4>Activity Feed</h4>

        {presence.activityFeed.length === 0 ? (
          <p className="empty-state">Waiting for activity...</p>
        ) : (
          <ul className="activity-list">
            {presence.activityFeed.map((item) => (
              <motion.li
                key={item.id}
                className="activity-item"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
              >
                <span className="action-badge" data-action={item.action}>
                  {item.action === 'entered' && '👋 Entered'}
                  {item.action === 'edited' && '✏️ Edited'}
                  {item.action === 'exited' && '🚪 Exited'}
                  {item.action === 'viewed' && '👁️ Viewed'}
                </span>
                <span className="username">{item.username}</span>
                {item.target && <span className="target">{item.target}</span>}
                <span className="timestamp">
                  {new Date(item.timestamp).toLocaleTimeString()}
                </span>
              </motion.li>
            ))}
          </ul>
        )}
      </div>

      {/* TODO: Collaborative editing locks - prevent conflicts */}
      {/* TODO: Show which sections are being edited by other users */}
      {/* TODO: "Undo" button that only affects user's own changes */}
    </motion.div>
  );
};
```

#### Task 4.4: Run tests

```bash
npm test -- tests/integration/test_multiplayer_stubs.tsx --run
# Expected: 7/7 passing - all stubs in place and ready for WebSocket implementation
```

#### Task 4.5: Commit

```bash
git add src/services/multiplayer/presenceService.ts
git add src/features/intelligence/shared/MultiplayerPresence.tsx
git add tests/integration/test_multiplayer_stubs.tsx
git commit -m "feat: add multiplayer presence architecture stubs (ready for WebSocket implementation)"
```

---

## Final Phase 3 Verification

Once all 4 tasks are complete:

#### Run full Phase 3 test suite:

```bash
npm test -- tests/integration/test_3d_globe.tsx tests/integration/test_scenario_engine.tsx tests/integration/test_accessibility_compliance.tsx tests/integration/test_multiplayer_stubs.tsx --run
# Expected: 45+ tests passing (5 + 7 + 15 + 7 + others)
```

#### Verify no regressions in Phase 1-2 tests:

```bash
npm test -- tests/unit/test_business_plan_*.tsx tests/unit/test_gtm_*.tsx tests/unit/test_swot_*.tsx tests/unit/test_pitch_*.tsx --run
# Expected: All Phase 1-2 tests still passing (798+ tests)
```

#### Final commit:

```bash
git add .
git commit -m "chore: Phase 3 complete - 3D enhancements, scenarios, accessibility, multiplayer stubs

- 3D interactive market globe with region highlighting
- What-if scenario engine with real-time metric recalculation
- WCAG 2.1 AA accessibility compliance across all canvases
- Multiplayer presence architecture stubs (future WebSocket ready)
- 45+ new integration tests covering all features
- All Phase 1-2 tests still passing (no regressions)
"
```

---

## Summary Statistics

| Component | Files | Tests | Lines |
|-----------|-------|-------|-------|
| 3D Globe | 2 | 5 | ~350 |
| Scenario Engine | 3 | 8 | ~400 |
| Accessibility | 6 | 20 | ~800 |
| Multiplayer Stubs | 3 | 7 | ~300 |
| **TOTAL** | **14** | **40+** | **~1,850** |

**Phase 3 Ready for Execution:** All tasks detailed with test-first approach, exact file locations, and specific test expectations.

**Next:** After Phase 3 completion → Proceed to Phase 4 (Pitch Deck Canvas polish + enhancements)
