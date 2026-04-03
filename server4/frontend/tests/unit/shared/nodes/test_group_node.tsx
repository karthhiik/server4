/**
 * test_group_node.tsx
 * Unit tests for GroupNode component
 * React Flow node - container node with label header
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';
import { GroupNode } from '../../components/shared/nodes/GroupNode';

expect.extend(toHaveNoViolations);

describe('GroupNode', () => {
  const mockData = {
    label: 'Market Analysis',
    type: 'group',
    color: '#667eea',
  };

  const baseProps = {
    data: mockData,
    selected: false,
  };

  // ========== RENDERING ==========
  describe('rendering', () => {
    it('renders container node', () => {
      render(<GroupNode {...baseProps} />);
      expect(screen.getByTestId('group-node')).toBeInTheDocument();
    });

    it('displays label header', () => {
      render(<GroupNode {...baseProps} />);
      expect(screen.getByTestId('group-header')).toHaveTextContent('Market Analysis');
    });

    it('renders as container with padding', () => {
      render(<GroupNode {...baseProps} />);

      const node = screen.getByTestId('group-node');
      expect(node).toHaveClass('group-container');
    });

    it('applies custom color to header', () => {
      render(<GroupNode {...baseProps} />);

      const header = screen.getByTestId('group-header');
      expect(header).toHaveStyle('background-color: #667eea');
    });
  });

  // ========== CHILDREN ==========
  describe('children rendering', () => {
    it('renders children nodes inside container', () => {
      render(
        <GroupNode {...baseProps}>
          <div data-testid="child-node">Child Node</div>
        </GroupNode>
      );

      expect(screen.getByTestId('child-node')).toBeInTheDocument();
      expect(screen.getByTestId('group-node')).toContainElement(
        screen.getByTestId('child-node')
      );
    });

    it('positions children within container bounds', () => {
      render(
        <GroupNode {...baseProps}>
          <div data-testid="child-1">Child 1</div>
          <div data-testid="child-2">Child 2</div>
        </GroupNode>
      );

      const container = screen.getByTestId('group-node');
      expect(container).toContainElement(screen.getByTestId('child-1'));
      expect(container).toContainElement(screen.getByTestId('child-2'));
    });
  });

  // ========== SELECTION ==========
  describe('selection state', () => {
    it('applies selected class', () => {
      render(<GroupNode {...baseProps} selected={true} />);

      const node = screen.getByTestId('group-node');
      expect(node).toHaveClass('selected');
    });

    it('highlights border when selected', () => {
      render(<GroupNode {...baseProps} selected={true} />);

      const node = screen.getByTestId('group-node');
      expect(node).toHaveStyle('border-color: var(--accent-color)');
    });
  });

  // ========== ACCESSIBILITY ==========
  describe('accessibility', () => {
    it('has no axe violations', async () => {
      const { container } = render(<GroupNode {...baseProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has role="group"', () => {
      render(<GroupNode {...baseProps} />);

      const node = screen.getByTestId('group-node');
      expect(node).toHaveAttribute('role', 'group');
    });

    it('header has aria-label', () => {
      render(<GroupNode {...baseProps} />);

      const header = screen.getByTestId('group-header');
      expect(header).toHaveAttribute('aria-label', expect.stringContaining('Market Analysis'));
    });
  });

  // ========== RESPONSIVE ==========
  describe('responsive behavior', () => {
    it('displays at all breakpoints', () => {
      const breakpoints = [1280, 768, 375];

      breakpoints.forEach((width) => {
        window.innerWidth = width;
        const { unmount } = render(<GroupNode {...baseProps} />);
        expect(screen.getByTestId('group-node')).toBeVisible();
        unmount();
      });
    });
  });
});
