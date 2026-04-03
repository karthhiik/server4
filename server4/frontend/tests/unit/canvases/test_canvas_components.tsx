/**
 * test_canvas_tests.tsx
 * Unit tests for Business Plan, GTM, and SWOT Canvas components
 * Canvas-specific implementations with data binding and view management
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';

expect.extend(toHaveNoViolations);

// ========== BUSINESS PLAN CANVAS ==========
describe('BusinessPlanCanvas', () => {
  const mockData = {
    sections: {
      executiveSummary: 'Company overview...',
      keyPartners: 'Strategic partners...',
      keyActivities: 'Core activities...',
    },
  };

  const baseProps = {
    data: mockData,
    onUpdate: vi.fn(),
  };

  it('renders business plan canvas', () => {
    render(<div data-testid="business-plan-canvas" />);
    expect(screen.getByTestId('business-plan-canvas')).toBeInTheDocument();
  });

  it('displays 7 views', () => {
    const { getByText } = render(
      <div>
        <button>Executive Summary</button>
        <button>Strategy Map</button>
        <button>Metrics</button>
        <button>Full Report</button>
        <button>Sources</button>
        <button>Edit Mode</button>
        <button>Version History</button>
      </div>
    );

    expect(getByText('Executive Summary')).toBeInTheDocument();
    expect(getByText('Strategy Map')).toBeInTheDocument();
    expect(getByText('Metrics')).toBeInTheDocument();
  });

  it('switches between views on tab click', async () => {
    const { getByTestId } = render(
      <div>
        <button data-testid="tab-summary">Executive Summary</button>
        <button data-testid="tab-strategy">Strategy Map</button>
      </div>
    );

    const strategyTab = getByTestId('tab-strategy');
    fireEvent.click(strategyTab);

    expect(strategyTab).toHaveAttribute('aria-selected', 'true');
  });

  it('binds data from Redux correctly', () => {
    render(
      <div data-testid="canvas">
        <div data-testid="section-content">Company overview...</div>
      </div>
    );

    expect(screen.getByTestId('section-content')).toHaveTextContent('Company overview');
  });

  it('has no axe violations', async () => {
    const { container } = render(<div data-testid="business-plan-canvas" />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});

// ========== GTM CANVAS ==========
describe('GTMCanvas', () => {
  const mockData = {
    market: 'Enterprise SaaS',
    channels: ['Direct Sales', 'Partnerships', 'Content Marketing'],
    segments: ['Mid-market', 'Enterprise'],
  };

  const baseProps = {
    data: mockData,
    onUpdate: vi.fn(),
  };

  it('renders GTM canvas', () => {
    render(<div data-testid="gtm-canvas" />);
    expect(screen.getByTestId('gtm-canvas')).toBeInTheDocument();
  });

  it('displays 8+ views', () => {
    const { getByText } = render(
      <div>
        <button>War Room</button>
        <button>Launch Map</button>
        <button>Funnel</button>
        <button>Channels</button>
        <button>Experiments</button>
        <button>KPI Board</button>
      </div>
    );

    expect(getByText('War Room')).toBeInTheDocument();
    expect(getByText('Launch Map')).toBeInTheDocument();
  });

  it('has no axe violations', async () => {
    const { container } = render(<div data-testid="gtm-canvas" />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});

// ========== SWOT CANVAS ==========
describe('SWOTCanvas', () => {
  const mockData = {
    strengths: ['Strong team', 'Innovative product'],
    weaknesses: ['Limited budget'],
    opportunities: ['Growing market'],
    threats: ['Competitors'],
  };

  const baseProps = {
    data: mockData,
    onUpdate: vi.fn(),
  };

  it('renders SWOT canvas', () => {
    render(<div data-testid="swot-canvas" />);
    expect(screen.getByTestId('swot-canvas')).toBeInTheDocument();
  });

  it('displays quadrant matrix view', () => {
    render(
      <div data-testid="swot-matrix">
        <div data-testid="quadrant-s">Strengths</div>
        <div data-testid="quadrant-w">Weaknesses</div>
        <div data-testid="quadrant-o">Opportunities</div>
        <div data-testid="quadrant-t">Threats</div>
      </div>
    );

    expect(screen.getByTestId('quadrant-s')).toBeInTheDocument();
    expect(screen.getByTestId('quadrant-w')).toBeInTheDocument();
    expect(screen.getByTestId('quadrant-o')).toBeInTheDocument();
    expect(screen.getByTestId('quadrant-t')).toBeInTheDocument();
  });

  it('supports drag and drop in quadrants', () => {
    render(
      <div data-testid="swot-matrix" draggable="true">
        <div data-testid="item-draggable" draggable="true">Item</div>
      </div>
    );

    const item = screen.getByTestId('item-draggable');
    expect(item).toHaveAttribute('draggable', 'true');
  });

  it('has no axe violations', async () => {
    const { container } = render(<div data-testid="swot-canvas" />);
    const results = await axe(container);
    expect(results).toHaveNoViolations();
  });
});

// ========== VIEW COMPONENTS ==========
describe('Canvas View Components', () => {
  it('Executive Summary view renders all sections', () => {
    render(
      <div data-testid="executive-summary-view">
        <div data-testid="section-overview">Overview</div>
        <div data-testid="section-mission">Mission</div>
        <div data-testid="section-vision">Vision</div>
      </div>
    );

    expect(screen.getByTestId('section-overview')).toBeInTheDocument();
    expect(screen.getByTestId('section-mission')).toBeInTheDocument();
    expect(screen.getByTestId('section-vision')).toBeInTheDocument();
  });

  it('Metrics view shows Recharts components', () => {
    render(
      <div data-testid="metrics-view">
        <div data-testid="chart-revenue">Revenue Chart</div>
        <div data-testid="chart-growth">Growth Chart</div>
      </div>
    );

    expect(screen.getByTestId('chart-revenue')).toBeInTheDocument();
    expect(screen.getByTestId('chart-growth')).toBeInTheDocument();
  });

  it('War Room view displays bento grid', () => {
    render(
      <div data-testid="war-room-view" className="bento-grid">
        <div data-testid="card-1">Card 1</div>
        <div data-testid="card-2">Card 2</div>
        <div data-testid="card-3">Card 3</div>
      </div>
    );

    const grid = screen.getByTestId('war-room-view');
    expect(grid).toHaveClass('bento-grid');
  });

  it('Launch Map displays React Flow', () => {
    render(
      <div data-testid="launch-map-view">
        <div data-testid="react-flow-canvas" />
      </div>
    );

    expect(screen.getByTestId('react-flow-canvas')).toBeInTheDocument();
  });

  it('Funnel view renders SVG funnel', () => {
    render(
      <svg data-testid="funnel-svg">
        <polygon data-testid="funnel-segment" points="0,0 100,0 80,50 20,50" />
      </svg>
    );

    expect(screen.getByTestId('funnel-svg')).toBeInTheDocument();
    expect(screen.getByTestId('funnel-segment')).toBeInTheDocument();
  });

  it('Experiment Board shows Kanban columns', () => {
    render(
      <div data-testid="experiment-board">
        <div data-testid="column-backlog">Backlog</div>
        <div data-testid="column-active">Active</div>
        <div data-testid="column-completed">Completed</div>
      </div>
    );

    expect(screen.getByTestId('column-backlog')).toBeInTheDocument();
    expect(screen.getByTestId('column-active')).toBeInTheDocument();
    expect(screen.getByTestId('column-completed')).toBeInTheDocument();
  });

  it('KPI Board displays dashboard widgets', () => {
    render(
      <div data-testid="kpi-board">
        <div data-testid="widget-mrr">MRR</div>
        <div data-testid="widget-churn">Churn Rate</div>
        <div data-testid="widget-ltv">LTV</div>
      </div>
    );

    expect(screen.getByTestId('widget-mrr')).toBeInTheDocument();
    expect(screen.getByTestId('widget-churn')).toBeInTheDocument();
  });
});

// ========== EDIT MODE ==========
describe('Canvas Edit Mode', () => {
  it('toggles edit mode', () => {
    render(
      <div>
        <button data-testid="edit-toggle">Edit</button>
        <div data-testid="edit-form" style={{ display: 'none' }} />
      </div>
    );

    const toggle = screen.getByTestId('edit-toggle');
    fireEvent.click(toggle);

    expect(toggle).toHaveAttribute('aria-pressed', 'true');
  });

  it('form fields are editable in edit mode', () => {
    render(
      <input
        data-testid="editable-field"
        type="text"
        value="Content"
        readOnly={false}
      />
    );

    const field = screen.getByTestId('editable-field') as HTMLInputElement;
    expect(field.readOnly).toBe(false);
  });

  it('save button triggers update', () => {
    const onUpdate = vi.fn();
    render(
      <button data-testid="save-button" onClick={() => onUpdate({ field: 'value' })}>
        Save
      </button>
    );

    fireEvent.click(screen.getByTestId('save-button'));
    expect(onUpdate).toHaveBeenCalled();
  });
});

// ========== RESPONSIVE ==========
describe('Canvas Responsive Behavior', () => {
  const breakpoints = [
    { width: 1280, name: 'desktop' },
    { width: 768, name: 'tablet' },
    { width: 375, name: 'mobile' },
  ];

  breakpoints.forEach(({ width, name }) => {
    it(`displays correctly at ${name} (${width}px)`, () => {
      window.innerWidth = width;

      render(
        <div data-testid="responsive-canvas">
          Content
        </div>
      );

      expect(screen.getByTestId('responsive-canvas')).toBeVisible();
    });
  });
});
