/**
 * test_entity_chip.tsx
 * Unit tests for EntityChip component
 * Shared Brain Component - entity enrichment state machine
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';
import { EntityChip } from '../../components/shared/EntityChip';

expect.extend(toHaveNoViolations);

describe('EntityChip', () => {
  const mockEntity = {
    id: 'entity-1',
    name: 'TechCorp Inc',
    type: 'company',
  };

  const baseProps = {
    entity: mockEntity,
    onSearch: vi.fn(),
    onAnalyzeCompetitor: vi.fn(),
  };

  // ========== DETECTED STATE ==========
  describe('detected state', () => {
    it('shows detected badge initially', () => {
      render(<EntityChip {...baseProps} />);

      expect(screen.getByTestId('entity-badge')).toHaveTextContent('detected');
    });

    it('displays entity name', () => {
      render(<EntityChip {...baseProps} />);

      expect(screen.getByTestId('entity-name')).toHaveTextContent('TechCorp Inc');
    });

    it('shows search button', () => {
      render(<EntityChip {...baseProps} />);

      expect(screen.getByTestId('search-button')).toBeInTheDocument();
    });
  });

  // ========== SEARCHING STATE ==========
  describe('searching state', () => {
    it('shows spinner during search', async () => {
      const { rerender } = render(<EntityChip {...baseProps} state="detected" />);

      fireEvent.click(screen.getByTestId('search-button'));

      rerender(<EntityChip {...baseProps} state="searching" />);

      await waitFor(() => {
        expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
      });
    });

    it('disables buttons during search', async () => {
      const { rerender } = render(<EntityChip {...baseProps} state="detected" />);

      rerender(<EntityChip {...baseProps} state="searching" />);

      const searchBtn = screen.getByTestId('search-button');
      expect(searchBtn).toHaveAttribute('disabled');
    });

    it('shows "Searching..." text', () => {
      render(<EntityChip {...baseProps} state="searching" />);

      expect(screen.getByText(/searching/i)).toBeInTheDocument();
    });
  });

  // ========== ENRICHED STATE ==========
  describe('enriched state', () => {
    const enrichedData = {
      industry: 'SaaS',
      employees: '500-1000',
      founded: 2018,
      website: 'techcorp.io',
      funding: '$50M Series B',
    };

    it('expands to show enriched data', () => {
      render(
        <EntityChip {...baseProps} state="enriched" enrichedData={enrichedData} />
      );

      expect(screen.getByTestId('enriched-content')).toBeInTheDocument();
    });

    it('displays industry', () => {
      render(
        <EntityChip {...baseProps} state="enriched" enrichedData={enrichedData} />
      );

      expect(screen.getByText('SaaS')).toBeInTheDocument();
    });

    it('displays employee count', () => {
      render(
        <EntityChip {...baseProps} state="enriched" enrichedData={enrichedData} />
      );

      expect(screen.getByText('500-1000')).toBeInTheDocument();
    });

    it('displays founded year', () => {
      render(
        <EntityChip {...baseProps} state="enriched" enrichedData={enrichedData} />
      );

      expect(screen.getByText('2018')).toBeInTheDocument();
    });

    it('displays website link', () => {
      render(
        <EntityChip {...baseProps} state="enriched" enrichedData={enrichedData} />
      );

      const link = screen.getByRole('link', { name: /techcorp\.io/i });
      expect(link).toHaveAttribute('href', 'https://techcorp.io');
    });

    it('displays funding information', () => {
      render(
        <EntityChip {...baseProps} state="enriched" enrichedData={enrichedData} />
      );

      expect(screen.getByText('$50M Series B')).toBeInTheDocument();
    });

    it('shows "Analyze Competitor" button', () => {
      render(
        <EntityChip {...baseProps} state="enriched" enrichedData={enrichedData} />
      );

      expect(screen.getByTestId('analyze-competitor-button')).toBeInTheDocument();
    });
  });

  // ========== INTERACTIONS ==========
  describe('interactions', () => {
    it('triggers onSearch when search button clicked', async () => {
      const onSearch = vi.fn();
      render(<EntityChip {...baseProps} onSearch={onSearch} />);

      const searchBtn = screen.getByTestId('search-button');
      fireEvent.click(searchBtn);

      expect(onSearch).toHaveBeenCalledWith(mockEntity);
    });

    it('triggers onAnalyzeCompetitor when button clicked', () => {
      const onAnalyzeCompetitor = vi.fn();
      const enrichedData = {
        industry: 'SaaS',
        employees: '500-1000',
        founded: 2018,
        website: 'techcorp.io',
        funding: '$50M Series B',
      };

      render(
        <EntityChip
          {...baseProps}
          state="enriched"
          enrichedData={enrichedData}
          onAnalyzeCompetitor={onAnalyzeCompetitor}
        />
      );

      const analyzeBtn = screen.getByTestId('analyze-competitor-button');
      fireEvent.click(analyzeBtn);

      expect(onAnalyzeCompetitor).toHaveBeenCalledWith(mockEntity);
    });
  });

  // ========== EXPAND/COLLAPSE ==========
  describe('expand/collapse animation', () => {
    const enrichedData = {
      industry: 'SaaS',
      employees: '500-1000',
      founded: 2018,
      website: 'techcorp.io',
      funding: '$50M Series B',
    };

    it('animates expansion', async () => {
      const { rerender } = render(
        <EntityChip {...baseProps} state="detected" />
      );

      const chip = screen.getByTestId('entity-chip');
      expect(chip).toHaveClass('state-detected');

      rerender(
        <EntityChip
          {...baseProps}
          state="enriched"
          enrichedData={enrichedData}
        />
      );

      await waitFor(() => {
        expect(chip).toHaveClass('expand-animation');
      });
    });
  });

  // ========== ACCESSIBILITY ==========
  describe('accessibility', () => {
    it('has no axe violations', async () => {
      const { container } = render(<EntityChip {...baseProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has aria-label', () => {
      render(<EntityChip {...baseProps} />);

      const chip = screen.getByTestId('entity-chip');
      expect(chip).toHaveAttribute('aria-label', expect.stringContaining('TechCorp Inc'));
    });

    it('buttons have descriptive labels', () => {
      render(<EntityChip {...baseProps} />);

      const searchBtn = screen.getByTestId('search-button');
      expect(searchBtn).toHaveAttribute('aria-label', expect.stringContaining('search'));
    });
  });

  // ========== RESPONSIVE ==========
  describe('responsive behavior', () => {
    it('displays at desktop', () => {
      window.innerWidth = 1280;
      render(<EntityChip {...baseProps} />);
      expect(screen.getByTestId('entity-chip')).toBeVisible();
    });

    it('displays at tablet', () => {
      window.innerWidth = 768;
      render(<EntityChip {...baseProps} />);
      expect(screen.getByTestId('entity-chip')).toBeVisible();
    });

    it('displays at mobile', () => {
      window.innerWidth = 375;
      render(<EntityChip {...baseProps} />);
      expect(screen.getByTestId('entity-chip')).toBeVisible();
    });
  });
});
