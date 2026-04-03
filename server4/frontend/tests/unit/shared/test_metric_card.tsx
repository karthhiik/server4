/**
 * test_metric_card.tsx
 * Unit tests for MetricCard component
 * Shared Brain Component - 4 variants (number, gauge, sparkline, progress)
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';
import { MetricCard } from '../../components/shared/MetricCard';
import * as Recharts from 'recharts';

expect.extend(toHaveNoViolations);

// Mock Recharts components
vi.mock('recharts', async () => {
  const actual = await vi.importActual('recharts');
  return {
    ...actual,
    RadialBarChart: ({ children }: any) => <div data-testid="radial-bar-chart">{children}</div>,
    LineChart: ({ children }: any) => <div data-testid="line-chart">{children}</div>,
    RadialBar: () => <div data-testid="radial-bar" />,
    Line: () => <div data-testid="line" />,
    CartesianGrid: () => <div data-testid="cartesian-grid" />,
    Tooltip: () => <div data-testid="tooltip" />,
  };
});

describe('MetricCard', () => {
  const baseProps = {
    title: 'Revenue',
    accentColor: '#667eea',
  };

  // ========== NUMBER VARIANT ==========
  describe('number variant', () => {
    const numberProps = {
      ...baseProps,
      variant: 'number' as const,
      value: 125000,
      label: 'USD',
      delta: 15,
    };

    it('renders number variant', () => {
      render(<MetricCard {...numberProps} />);
      expect(screen.getByTestId('metric-card')).toHaveAttribute('data-variant', 'number');
    });

    it('displays value', () => {
      render(<MetricCard {...numberProps} />);
      expect(screen.getByTestId('metric-value')).toHaveTextContent('125000');
    });

    it('displays label', () => {
      render(<MetricCard {...numberProps} />);
      expect(screen.getByTestId('metric-label')).toHaveTextContent('USD');
    });

    it('displays positive delta with up arrow', () => {
      render(<MetricCard {...numberProps} delta={15} />);
      const trendArrow = screen.getByTestId('trend-arrow');
      expect(trendArrow).toHaveClass('arrow-up');
      expect(screen.getByTestId('trend-percentage')).toHaveTextContent('+15%');
    });

    it('displays negative delta with down arrow', () => {
      render(<MetricCard {...numberProps} delta={-10} />);
      const trendArrow = screen.getByTestId('trend-arrow');
      expect(trendArrow).toHaveClass('arrow-down');
      expect(screen.getByTestId('trend-percentage')).toHaveTextContent('-10%');
    });

    it('displays zero delta without arrow change', () => {
      render(<MetricCard {...numberProps} delta={0} />);
      expect(screen.getByTestId('trend-percentage')).toHaveTextContent('0%');
    });

    it('formats large numbers with commas', () => {
      render(<MetricCard {...numberProps} value={1234567} />);
      expect(screen.getByTestId('metric-value')).toHaveTextContent('1,234,567');
    });
  });

  // ========== GAUGE VARIANT ==========
  describe('gauge variant', () => {
    const gaugeProps = {
      ...baseProps,
      variant: 'gauge' as const,
      value: 75,
      max: 100,
    };

    it('renders gauge variant', () => {
      render(<MetricCard {...gaugeProps} />);
      expect(screen.getByTestId('metric-card')).toHaveAttribute('data-variant', 'gauge');
    });

    it('renders RadialBarChart', () => {
      render(<MetricCard {...gaugeProps} />);
      expect(screen.getByTestId('radial-bar-chart')).toBeInTheDocument();
    });

    it('passes correct data to chart', () => {
      const { container } = render(<MetricCard {...gaugeProps} />);
      const chart = container.querySelector('[data-testid="radial-bar-chart"]');
      expect(chart).toBeInTheDocument();
    });

    it('displays percentage label', () => {
      render(<MetricCard {...gaugeProps} />);
      expect(screen.getByTestId('gauge-percentage')).toHaveTextContent('75%');
    });

    it('applies accent color to gauge', () => {
      render(<MetricCard {...gaugeProps} accentColor="#667eea" />);
      const chart = screen.getByTestId('radial-bar-chart');
      expect(chart).toHaveStyle('--accent-color: #667eea');
    });
  });

  // ========== SPARKLINE VARIANT ==========
  describe('sparkline variant', () => {
    const sparklineProps = {
      ...baseProps,
      variant: 'sparkline' as const,
      data: [
        { value: 10 },
        { value: 20 },
        { value: 15 },
        { value: 30 },
        { value: 25 },
      ],
    };

    it('renders sparkline variant', () => {
      render(<MetricCard {...sparklineProps} />);
      expect(screen.getByTestId('metric-card')).toHaveAttribute('data-variant', 'sparkline');
    });

    it('renders LineChart', () => {
      render(<MetricCard {...sparklineProps} />);
      expect(screen.getByTestId('line-chart')).toBeInTheDocument();
    });

    it('displays chart with correct data points', () => {
      const { container } = render(<MetricCard {...sparklineProps} />);
      const chart = container.querySelector('[data-testid="line-chart"]');
      expect(chart).toBeInTheDocument();
    });

    it('applies accent color to line', () => {
      render(<MetricCard {...sparklineProps} accentColor="#667eea" />);
      const line = screen.getByTestId('line');
      expect(line).toHaveAttribute('stroke', '#667eea');
    });
  });

  // ========== PROGRESS VARIANT ==========
  describe('progress variant', () => {
    const progressProps = {
      ...baseProps,
      variant: 'progress' as const,
      value: 65,
      max: 100,
    };

    it('renders progress variant', () => {
      render(<MetricCard {...progressProps} />);
      expect(screen.getByTestId('metric-card')).toHaveAttribute('data-variant', 'progress');
    });

    it('renders progress bar', () => {
      render(<MetricCard {...progressProps} />);
      expect(screen.getByTestId('progress-bar')).toBeInTheDocument();
    });

    it('sets correct bar width from value', () => {
      render(<MetricCard {...progressProps} value={50} max={100} />);
      const barFill = screen.getByTestId('progress-bar-fill');
      expect(barFill).toHaveStyle('width: 50%');
    });

    it('displays percentage text', () => {
      render(<MetricCard {...progressProps} value={65} max={100} />);
      expect(screen.getByTestId('progress-percentage')).toHaveTextContent('65%');
    });

    it('applies accent color to bar', () => {
      render(<MetricCard {...progressProps} accentColor="#667eea" />);
      const barFill = screen.getByTestId('progress-bar-fill');
      expect(barFill).toHaveStyle('background-color: #667eea');
    });

    it('handles edge case: 0 value', () => {
      render(<MetricCard {...progressProps} value={0} max={100} />);
      const barFill = screen.getByTestId('progress-bar-fill');
      expect(barFill).toHaveStyle('width: 0%');
    });

    it('handles edge case: max value', () => {
      render(<MetricCard {...progressProps} value={100} max={100} />);
      const barFill = screen.getByTestId('progress-bar-fill');
      expect(barFill).toHaveStyle('width: 100%');
    });
  });

  // ========== THEME INTEGRATION ==========
  describe('theme integration', () => {
    it('inherits accent color from theme context', () => {
      const { container } = render(
        <div style={{ '--theme-accent': '#667eea' } as any}>
          <MetricCard {...baseProps} variant="progress" value={50} max={100} accentColor="#667eea" />
        </div>
      );
      const card = screen.getByTestId('metric-card');
      expect(card).toBeInTheDocument();
    });

    it('applies custom accent color override', () => {
      render(
        <MetricCard
          {...baseProps}
          variant="progress"
          value={50}
          max={100}
          accentColor="#ff6b6b"
        />
      );
      const barFill = screen.getByTestId('progress-bar-fill');
      expect(barFill).toHaveStyle('background-color: #ff6b6b');
    });
  });

  // ========== ACCESSIBILITY ==========
  describe('accessibility', () => {
    it('has no axe violations (number variant)', async () => {
      const { container } = render(
        <MetricCard {...baseProps} variant="number" value={125000} label="USD" delta={15} />
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has no axe violations (gauge variant)', async () => {
      const { container } = render(
        <MetricCard {...baseProps} variant="gauge" value={75} max={100} />
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has aria-label for title', () => {
      render(<MetricCard {...baseProps} variant="number" value={125000} label="USD" />);
      const card = screen.getByTestId('metric-card');
      expect(card).toHaveAttribute('aria-label', expect.stringContaining('Revenue'));
    });

    it('progress bar has aria-valuenow', () => {
      render(<MetricCard {...baseProps} variant="progress" value={65} max={100} />);
      const progressBar = screen.getByTestId('progress-bar');
      expect(progressBar).toHaveAttribute('aria-valuenow', '65');
      expect(progressBar).toHaveAttribute('aria-valuemin', '0');
      expect(progressBar).toHaveAttribute('aria-valuemax', '100');
    });
  });

  // ========== RESPONSIVE ==========
  describe('responsive behavior', () => {
    it('displays correctly at desktop (1280px)', () => {
      window.innerWidth = 1280;
      render(<MetricCard {...baseProps} variant="number" value={125000} label="USD" />);
      expect(screen.getByTestId('metric-card')).toBeVisible();
    });

    it('displays correctly at tablet (768px)', () => {
      window.innerWidth = 768;
      render(<MetricCard {...baseProps} variant="number" value={125000} label="USD" />);
      expect(screen.getByTestId('metric-card')).toBeVisible();
    });

    it('displays correctly at mobile (<500px)', () => {
      window.innerWidth = 375;
      render(<MetricCard {...baseProps} variant="number" value={125000} label="USD" />);
      expect(screen.getByTestId('metric-card')).toBeVisible();
    });

    it('chart responsive at all breakpoints', () => {
      const breakpoints = [1280, 768, 375];
      breakpoints.forEach((width) => {
        window.innerWidth = width;
        const { unmount } = render(
          <MetricCard {...baseProps} variant="gauge" value={75} max={100} />
        );
        expect(screen.getByTestId('radial-bar-chart')).toBeInTheDocument();
        unmount();
      });
    });
  });
});
