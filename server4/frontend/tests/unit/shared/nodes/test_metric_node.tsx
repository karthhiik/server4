/**
 * test_metric_node.tsx
 * Unit tests for MetricNode component
 * React Flow node - compact KPI pill display
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';
import { MetricNode } from '../../components/shared/nodes/MetricNode';

expect.extend(toHaveNoViolations);

describe('MetricNode', () => {
  const mockData = {
    label: 'Revenue',
    value: '$125M',
    unit: 'USD',
    trend: '+15%',
  };

  const baseProps = {
    data: mockData,
    selected: false,
  };

  // ========== RENDERING ==========
  describe('rendering', () => {
    it('renders metric node', () => {
      render(<MetricNode {...baseProps} />);
      expect(screen.getByTestId('metric-node')).toBeInTheDocument();
    });

    it('displays value', () => {
      render(<MetricNode {...baseProps} />);
      expect(screen.getByTestId('metric-value')).toHaveTextContent('$125M');
    });

    it('displays unit', () => {
      render(<MetricNode {...baseProps} />);
      expect(screen.getByTestId('metric-unit')).toHaveTextContent('USD');
    });

    it('renders as compact pill shape', () => {
      render(<MetricNode {...baseProps} />);

      const node = screen.getByTestId('metric-node');
      expect(node).toHaveClass('pill-shape');
    });
  });

  // ========== CLICK HANDLERS ==========
  describe('click handlers', () => {
    it('triggers onClick handler', () => {
      const onClick = vi.fn();
      render(<MetricNode {...baseProps} onClick={onClick} />);

      const node = screen.getByTestId('metric-node');
      fireEvent.click(node);

      expect(onClick).toHaveBeenCalledTimes(1);
    });
  });

  // ========== SELECTION ==========
  describe('selection state', () => {
    it('applies selected class', () => {
      render(<MetricNode {...baseProps} selected={true} />);

      const node = screen.getByTestId('metric-node');
      expect(node).toHaveClass('selected');
    });

    it('removes selected class when not selected', () => {
      render(<MetricNode {...baseProps} selected={false} />);

      const node = screen.getByTestId('metric-node');
      expect(node).not.toHaveClass('selected');
    });
  });

  // ========== ACCESSIBILITY ==========
  describe('accessibility', () => {
    it('has no axe violations', async () => {
      const { container } = render(<MetricNode {...baseProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has aria-label', () => {
      render(<MetricNode {...baseProps} />);

      const node = screen.getByTestId('metric-node');
      expect(node).toHaveAttribute('aria-label', expect.stringContaining('Revenue'));
    });
  });

  // ========== RESPONSIVE ==========
  describe('responsive behavior', () => {
    it('displays at all breakpoints', () => {
      const breakpoints = [1280, 768, 375];

      breakpoints.forEach((width) => {
        window.innerWidth = width;
        const { unmount } = render(<MetricNode {...baseProps} />);
        expect(screen.getByTestId('metric-node')).toBeVisible();
        unmount();
      });
    });
  });
});
