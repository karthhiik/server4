/**
 * test_strategy_node.tsx
 * Unit tests for StrategyNode component
 * React Flow node - displays strategy card with confidence badge
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';
import { StrategyNode } from '../../components/shared/nodes/StrategyNode';

expect.extend(toHaveNoViolations);

describe('StrategyNode', () => {
  const mockData = {
    label: 'Market Expansion',
    icon: '🚀',
    confidence: 'verified' as const,
    status: 'in-progress' as const,
    description: 'Expand to new geographic markets',
  };

  const baseProps = {
    data: mockData,
    isConnecting: false,
    selected: false,
  };

  // ========== RENDERING ==========
  describe('rendering', () => {
    it('renders card container', () => {
      render(<StrategyNode {...baseProps} />);
      expect(screen.getByTestId('strategy-node')).toBeInTheDocument();
    });

    it('displays icon', () => {
      render(<StrategyNode {...baseProps} />);
      expect(screen.getByText(mockData.icon)).toBeInTheDocument();
    });

    it('displays title', () => {
      render(<StrategyNode {...baseProps} />);
      expect(screen.getByText(mockData.label)).toBeInTheDocument();
    });

    it('displays subtitle/description', () => {
      render(<StrategyNode {...baseProps} />);
      expect(screen.getByText(mockData.description)).toBeInTheDocument();
    });

    it('renders ConfidenceBadge', () => {
      render(<StrategyNode {...baseProps} />);
      expect(screen.getByTestId('confidence-badge')).toBeInTheDocument();
    });

    it('displays status dot when present', () => {
      render(<StrategyNode {...baseProps} />);
      const statusDot = screen.getByTestId('status-dot');
      expect(statusDot).toHaveAttribute('data-status', 'in-progress');
    });
  });

  // ========== CLICK HANDLERS ==========
  describe('click handlers', () => {
    it('triggers onClick handler', () => {
      const onClick = vi.fn();
      render(<StrategyNode {...baseProps} onClick={onClick} />);

      const node = screen.getByTestId('strategy-node');
      fireEvent.click(node);

      expect(onClick).toHaveBeenCalledTimes(1);
    });

    it('triggers onDoubleClick handler', () => {
      const onDoubleClick = vi.fn();
      render(<StrategyNode {...baseProps} onDoubleClick={onDoubleClick} />);

      const node = screen.getByTestId('strategy-node');
      fireEvent.doubleClick(node);

      expect(onDoubleClick).toHaveBeenCalledTimes(1);
    });

    it('prevents default on context menu', () => {
      const onContextMenu = vi.fn();
      render(<StrategyNode {...baseProps} onContextMenu={onContextMenu} />);

      const node = screen.getByTestId('strategy-node');
      const event = new MouseEvent('contextmenu', { bubbles: true });
      const preventDefaultSpy = vi.spyOn(event, 'preventDefault');

      fireEvent(node, event);

      expect(preventDefaultSpy).toHaveBeenCalled();
    });

    it('shows context menu on right-click', async () => {
      render(<StrategyNode {...baseProps} />);

      const node = screen.getByTestId('strategy-node');
      fireEvent.contextMenu(node);

      await waitFor(() => {
        expect(screen.getByTestId('context-menu')).toBeInTheDocument();
      });
    });
  });

  // ========== HOVER EFFECTS ==========
  describe('hover effects', () => {
    it('applies hover class on mouse enter', async () => {
      render(<StrategyNode {...baseProps} />);

      const node = screen.getByTestId('strategy-node');
      fireEvent.mouseEnter(node);

      await waitFor(() => {
        expect(node).toHaveClass('hover');
      });
    });

    it('removes hover class on mouse leave', async () => {
      render(<StrategyNode {...baseProps} />);

      const node = screen.getByTestId('strategy-node');
      fireEvent.mouseEnter(node);

      await waitFor(() => {
        expect(node).toHaveClass('hover');
      });

      fireEvent.mouseLeave(node);

      await waitFor(() => {
        expect(node).not.toHaveClass('hover');
      });
    });

    it('shows description on hover', async () => {
      render(<StrategyNode {...baseProps} />);

      const node = screen.getByTestId('strategy-node');
      expect(screen.queryByTestId('node-description')).not.toBeVisible();

      fireEvent.mouseEnter(node);

      await waitFor(() => {
        expect(screen.getByTestId('node-description')).toBeVisible();
      });
    });
  });

  // ========== SELECTION STATE ==========
  describe('selection state', () => {
    it('applies selected class when selected', () => {
      render(<StrategyNode {...baseProps} selected={true} />);

      const node = screen.getByTestId('strategy-node');
      expect(node).toHaveClass('selected');
    });

    it('removes selected class when not selected', () => {
      render(<StrategyNode {...baseProps} selected={false} />);

      const node = screen.getByTestId('strategy-node');
      expect(node).not.toHaveClass('selected');
    });

    it('highlights border when selected', () => {
      render(<StrategyNode {...baseProps} selected={true} />);

      const node = screen.getByTestId('strategy-node');
      expect(node).toHaveStyle('border-color: var(--accent-color)');
    });
  });

  // ========== CONNECTION STATE ==========
  describe('connection state', () => {
    it('applies connecting class when isConnecting true', () => {
      render(<StrategyNode {...baseProps} isConnecting={true} />);

      const node = screen.getByTestId('strategy-node');
      expect(node).toHaveClass('connecting');
    });

    it('shows connection ports when connecting', () => {
      render(<StrategyNode {...baseProps} isConnecting={true} />);

      const inputPort = screen.getByTestId('handle-input');
      const outputPort = screen.getByTestId('handle-output');

      expect(inputPort).toBeVisible();
      expect(outputPort).toBeVisible();
    });
  });

  // ========== STATUS VARIANTS ==========
  describe('status variants', () => {
    const statuses = ['in-progress', 'completed', 'blocked', 'planned'] as const;

    statuses.forEach((status) => {
      it(`displays ${status} status correctly`, () => {
        render(
          <StrategyNode {...baseProps} data={{ ...mockData, status }} />
        );

        const statusDot = screen.getByTestId('status-dot');
        expect(statusDot).toHaveAttribute('data-status', status);
      });
    });
  });

  // ========== ACCESSIBILITY ==========
  describe('accessibility', () => {
    it('has no axe violations', async () => {
      const { container } = render(<StrategyNode {...baseProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('card has proper role', () => {
      render(<StrategyNode {...baseProps} />);

      const node = screen.getByTestId('strategy-node');
      expect(node).toHaveAttribute('role', 'article');
    });

    it('has aria-label with strategy name', () => {
      render(<StrategyNode {...baseProps} />);

      const node = screen.getByTestId('strategy-node');
      expect(node).toHaveAttribute('aria-label', expect.stringContaining('Market Expansion'));
    });

    it('status dot has aria-label', () => {
      render(<StrategyNode {...baseProps} />);

      const statusDot = screen.getByTestId('status-dot');
      expect(statusDot).toHaveAttribute('aria-label', expect.stringContaining('in-progress'));
    });
  });

  // ========== RESPONSIVE ==========
  describe('responsive behavior', () => {
    it('displays at desktop', () => {
      window.innerWidth = 1280;
      render(<StrategyNode {...baseProps} />);
      expect(screen.getByTestId('strategy-node')).toBeVisible();
    });

    it('displays at tablet', () => {
      window.innerWidth = 768;
      render(<StrategyNode {...baseProps} />);
      expect(screen.getByTestId('strategy-node')).toBeVisible();
    });

    it('displays at mobile', () => {
      window.innerWidth = 375;
      render(<StrategyNode {...baseProps} />);
      expect(screen.getByTestId('strategy-node')).toBeVisible();
    });
  });
});
