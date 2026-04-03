/**
 * test_evidence_drawer.tsx
 * Unit tests for EvidenceDrawer component
 * Shared Brain Component - slide-in panel with tabs, search, and citations
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';
import { EvidenceDrawer } from '../../components/shared/EvidenceDrawer';

expect.extend(toHaveNoViolations);

// Mock Framer Motion for animations
vi.mock('framer-motion', () => ({
  motion: {
    div: ({ children, ...props }: any) => <div {...props}>{children}</div>,
  },
  AnimatePresence: ({ children }: any) => <>{children}</>,
}));

describe('EvidenceDrawer', () => {
  const mockEvidence = [
    {
      id: 'ev1',
      title: 'Market Size Report',
      domain: 'forbes.com',
      snippet: 'The market size is expected to grow...',
      date: '2024-01-15',
      confidenceLevel: 'verified',
      url: 'https://forbes.com/article',
    },
    {
      id: 'ev2',
      title: 'Competitor Analysis',
      domain: 'crunchbase.com',
      snippet: 'Recent funding rounds show...',
      date: '2024-01-10',
      confidenceLevel: 'corroborated',
      url: 'https://crunchbase.com/company',
    },
    {
      id: 'ev3',
      title: 'Industry Trends',
      domain: 'industry-report.com',
      snippet: 'Emerging technologies are changing...',
      date: '2024-01-05',
      confidenceLevel: 'inference',
      url: 'https://industry-report.com',
    },
  ];

  const baseProps = {
    isOpen: false,
    evidence: mockEvidence,
    onClose: vi.fn(),
  };

  // ========== VISIBILITY ==========
  describe('visibility', () => {
    it('hides panel when isOpen=false', () => {
      render(<EvidenceDrawer {...baseProps} isOpen={false} />);
      const drawer = screen.queryByTestId('evidence-drawer');
      expect(drawer).not.toBeVisible();
    });

    it('shows panel when isOpen=true', () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);
      const drawer = screen.getByTestId('evidence-drawer');
      expect(drawer).toBeVisible();
    });
  });

  // ========== ANIMATION ==========
  describe('animation', () => {
    it('applies slide-in animation class when opening', () => {
      const { rerender } = render(<EvidenceDrawer {...baseProps} isOpen={false} />);
      rerender(<EvidenceDrawer {...baseProps} isOpen={true} />);

      const drawer = screen.getByTestId('evidence-drawer');
      expect(drawer).toHaveClass('slide-in-animation');
    });

    it('applies slide-out animation class when closing', () => {
      const { rerender } = render(<EvidenceDrawer {...baseProps} isOpen={true} />);
      rerender(<EvidenceDrawer {...baseProps} isOpen={false} />);

      const drawer = screen.queryByTestId('evidence-drawer');
      expect(drawer).not.toHaveClass('slide-in-animation');
    });
  });

  // ========== TABS ==========
  describe('tabs', () => {
    it('renders two tabs: Sources and Visuals', () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      expect(screen.getByRole('tab', { name: /sources/i })).toBeInTheDocument();
      expect(screen.getByRole('tab', { name: /visuals/i })).toBeInTheDocument();
    });

    it('sources tab is active by default', () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      const sourcesTab = screen.getByRole('tab', { name: /sources/i });
      expect(sourcesTab).toHaveAttribute('aria-selected', 'true');
    });

    it('switches to visuals tab on click', async () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      const visualsTab = screen.getByRole('tab', { name: /visuals/i });
      fireEvent.click(visualsTab);

      await waitFor(() => {
        expect(visualsTab).toHaveAttribute('aria-selected', 'true');
      });
    });

    it('shows sources content when sources tab active', () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      const sourcesPanel = screen.getByTestId('sources-panel');
      expect(sourcesPanel).toBeVisible();
    });

    it('shows visuals content when visuals tab active', async () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      const visualsTab = screen.getByRole('tab', { name: /visuals/i });
      fireEvent.click(visualsTab);

      await waitFor(() => {
        const visualsPanel = screen.getByTestId('visuals-panel');
        expect(visualsPanel).toBeVisible();
      });
    });
  });

  // ========== SOURCES GROUPING ==========
  describe('sources grouping by confidence', () => {
    it('groups evidence by confidence level', () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      expect(screen.getByTestId('group-verified')).toBeInTheDocument();
      expect(screen.getByTestId('group-corroborated')).toBeInTheDocument();
      expect(screen.getByTestId('group-inference')).toBeInTheDocument();
    });

    it('groups verified evidence together', () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      const verifiedGroup = screen.getByTestId('group-verified');
      expect(verifiedGroup).toHaveTextContent('Market Size Report');
    });

    it('displays group headers', () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      expect(screen.getByText(/verified sources/i)).toBeInTheDocument();
      expect(screen.getByText(/corroborated sources/i)).toBeInTheDocument();
    });
  });

  // ========== EVIDENCE CARDS ==========
  describe('evidence card content', () => {
    it('displays evidence title', () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      expect(screen.getByText('Market Size Report')).toBeInTheDocument();
      expect(screen.getByText('Competitor Analysis')).toBeInTheDocument();
    });

    it('displays domain', () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      expect(screen.getByText('forbes.com')).toBeInTheDocument();
      expect(screen.getByText('crunchbase.com')).toBeInTheDocument();
    });

    it('displays snippet text', () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      expect(screen.getByText(/The market size is expected to grow/)).toBeInTheDocument();
    });

    it('displays date', () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      expect(screen.getByText('2024-01-15')).toBeInTheDocument();
    });

    it('displays ConfidenceBadge for each evidence', () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      const badges = screen.getAllByTestId('confidence-badge');
      expect(badges.length).toBeGreaterThan(0);
    });
  });

  // ========== SEARCH ==========
  describe('search functionality', () => {
    it('renders search bar', () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      expect(screen.getByTestId('evidence-search')).toBeInTheDocument();
    });

    it('filters evidence by title', async () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      const searchInput = screen.getByTestId('evidence-search') as HTMLInputElement;
      fireEvent.change(searchInput, { target: { value: 'Market' } });

      await waitFor(() => {
        expect(screen.getByText('Market Size Report')).toBeInTheDocument();
        expect(screen.queryByText('Competitor Analysis')).not.toBeInTheDocument();
      });
    });

    it('filters evidence by domain', async () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      const searchInput = screen.getByTestId('evidence-search') as HTMLInputElement;
      fireEvent.change(searchInput, { target: { value: 'crunchbase' } });

      await waitFor(() => {
        expect(screen.getByText('Competitor Analysis')).toBeInTheDocument();
        expect(screen.queryByText('Market Size Report')).not.toBeInTheDocument();
      });
    });

    it('clears filters when search is cleared', async () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      const searchInput = screen.getByTestId('evidence-search') as HTMLInputElement;
      fireEvent.change(searchInput, { target: { value: 'Market' } });

      await waitFor(() => {
        expect(screen.getByText('Market Size Report')).toBeInTheDocument();
      });

      fireEvent.change(searchInput, { target: { value: '' } });

      await waitFor(() => {
        expect(screen.getByText('Competitor Analysis')).toBeInTheDocument();
      });
    });

    it('shows no results message when no matches', async () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      const searchInput = screen.getByTestId('evidence-search') as HTMLInputElement;
      fireEvent.change(searchInput, { target: { value: 'xyz-nonexistent' } });

      await waitFor(() => {
        expect(screen.getByText(/no evidence found/i)).toBeInTheDocument();
      });
    });
  });

  // ========== CLOSE BUTTON ==========
  describe('close interactions', () => {
    it('shows close button (X)', () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      const closeBtn = screen.getByTestId('close-button');
      expect(closeBtn).toBeInTheDocument();
    });

    it('triggers onClose when X clicked', async () => {
      const onClose = vi.fn();
      render(<EvidenceDrawer {...baseProps} isOpen={true} onClose={onClose} />);

      const closeBtn = screen.getByTestId('close-button');
      fireEvent.click(closeBtn);

      await waitFor(() => {
        expect(onClose).toHaveBeenCalledTimes(1);
      });
    });

    it('triggers onClose when clicking outside', async () => {
      const onClose = vi.fn();
      render(<EvidenceDrawer {...baseProps} isOpen={true} onClose={onClose} />);

      const backdrop = screen.getByTestId('drawer-backdrop');
      fireEvent.click(backdrop);

      await waitFor(() => {
        expect(onClose).toHaveBeenCalledTimes(1);
      });
    });

    it('triggers onClose on Escape key', async () => {
      const onClose = vi.fn();
      render(<EvidenceDrawer {...baseProps} isOpen={true} onClose={onClose} />);

      fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });

      await waitFor(() => {
        expect(onClose).toHaveBeenCalledTimes(1);
      });
    });
  });

  // ========== CITATION HIGHLIGHTING ==========
  describe('citation highlighting', () => {
    it('auto-scrolls to highlighted citation', async () => {
      const { rerender } = render(
        <EvidenceDrawer {...baseProps} isOpen={true} highlightCitationId={undefined} />
      );

      rerender(
        <EvidenceDrawer {...baseProps} isOpen={true} highlightCitationId="ev1" />
      );

      const highlightedCard = screen.getByTestId('evidence-card-ev1');
      const scrollIntoViewSpy = vi.spyOn(highlightedCard, 'scrollIntoView');

      expect(highlightedCard).toHaveClass('highlighted');
    });

    it('applies highlight class to target citation', () => {
      render(
        <EvidenceDrawer {...baseProps} isOpen={true} highlightCitationId="ev2" />
      );

      const highlightedCard = screen.getByTestId('evidence-card-ev2');
      expect(highlightedCard).toHaveClass('highlighted');
    });

    it('removes highlight when citationId changes', () => {
      const { rerender } = render(
        <EvidenceDrawer {...baseProps} isOpen={true} highlightCitationId="ev1" />
      );

      expect(screen.getByTestId('evidence-card-ev1')).toHaveClass('highlighted');

      rerender(
        <EvidenceDrawer {...baseProps} isOpen={true} highlightCitationId="ev2" />
      );

      expect(screen.getByTestId('evidence-card-ev1')).not.toHaveClass('highlighted');
      expect(screen.getByTestId('evidence-card-ev2')).toHaveClass('highlighted');
    });
  });

  // ========== ACCESSIBILITY ==========
  describe('accessibility', () => {
    it('has no axe violations', async () => {
      const { container } = render(
        <EvidenceDrawer {...baseProps} isOpen={true} />
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('drawer has role="dialog"', () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      const drawer = screen.getByTestId('evidence-drawer');
      expect(drawer).toHaveAttribute('role', 'dialog');
    });

    it('tabs have proper ARIA attributes', () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      const sourcesTab = screen.getByRole('tab', { name: /sources/i });
      expect(sourcesTab).toHaveAttribute('aria-selected');
    });

    it('search has aria-label', () => {
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);

      const search = screen.getByTestId('evidence-search');
      expect(search).toHaveAttribute('aria-label');
    });
  });

  // ========== RESPONSIVE ==========
  describe('responsive behavior', () => {
    it('displays correctly at desktop (1280px)', () => {
      window.innerWidth = 1280;
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);
      expect(screen.getByTestId('evidence-drawer')).toBeVisible();
    });

    it('displays as slide-over at tablet (768px)', () => {
      window.innerWidth = 768;
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);
      const drawer = screen.getByTestId('evidence-drawer');
      expect(drawer).toHaveClass('drawer-tablet');
    });

    it('displays fullscreen at mobile (<500px)', () => {
      window.innerWidth = 375;
      render(<EvidenceDrawer {...baseProps} isOpen={true} />);
      const drawer = screen.getByTestId('evidence-drawer');
      expect(drawer).toHaveClass('drawer-mobile');
    });
  });
});
