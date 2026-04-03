/**
 * test_evidence_node.tsx
 * Unit tests for EvidenceNode component
 * React Flow node - citation chip with evidence drawer integration
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';
import { EvidenceNode } from '../../components/shared/nodes/EvidenceNode';

expect.extend(toHaveNoViolations);

describe('EvidenceNode', () => {
  const mockData = {
    citationId: 'cite-001',
    source: 'Forbes',
    title: 'Market Analysis Report',
    type: 'citation',
  };

  const baseProps = {
    data: mockData,
    selected: false,
  };

  // ========== RENDERING ==========
  describe('rendering', () => {
    it('renders citation chip', () => {
      render(<EvidenceNode {...baseProps} />);
      expect(screen.getByTestId('evidence-node')).toBeInTheDocument();
    });

    it('displays citation ID', () => {
      render(<EvidenceNode {...baseProps} />);
      expect(screen.getByTestId('citation-id')).toHaveTextContent('cite-001');
    });

    it('displays source', () => {
      render(<EvidenceNode {...baseProps} />);
      expect(screen.getByTestId('source-name')).toHaveTextContent('Forbes');
    });
  });

  // ========== INTERACTIONS ==========
  describe('interactions', () => {
    it('opens evidence drawer on click', async () => {
      render(<EvidenceNode {...baseProps} />);

      const node = screen.getByTestId('evidence-node');
      fireEvent.click(node);

      await waitFor(() => {
        expect(screen.getByTestId('evidence-drawer')).toBeVisible();
      });
    });

    it('passes citation ID to drawer', async () => {
      render(<EvidenceNode {...baseProps} />);

      const node = screen.getByTestId('evidence-node');
      fireEvent.click(node);

      await waitFor(() => {
        const drawer = screen.getByTestId('evidence-drawer');
        expect(drawer).toHaveAttribute('data-highlight-id', 'cite-001');
      });
    });
  });

  // ========== ACCESSIBILITY ==========
  describe('accessibility', () => {
    it('has no axe violations', async () => {
      const { container } = render(<EvidenceNode {...baseProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has aria-label', () => {
      render(<EvidenceNode {...baseProps} />);

      const node = screen.getByTestId('evidence-node');
      expect(node).toHaveAttribute('aria-label', expect.stringContaining('Forbes'));
    });
  });

  // ========== RESPONSIVE ==========
  describe('responsive behavior', () => {
    it('displays at all breakpoints', () => {
      const breakpoints = [1280, 768, 375];

      breakpoints.forEach((width) => {
        window.innerWidth = width;
        const { unmount } = render(<EvidenceNode {...baseProps} />);
        expect(screen.getByTestId('evidence-node')).toBeVisible();
        unmount();
      });
    });
  });
});
