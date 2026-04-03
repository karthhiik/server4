/**
 * test_enrichment_card.tsx
 * Unit tests for EnrichmentCard component
 * Shared Brain Component - company enrichment data card
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';
import { EnrichmentCard } from '../../components/shared/EnrichmentCard';

expect.extend(toHaveNoViolations);

describe('EnrichmentCard', () => {
  const mockCompanyData = {
    name: 'TechCorp Inc',
    industry: 'SaaS',
    size: '500-1000',
    founded: 2018,
    website: 'techcorp.io',
    funding: '$50M Series B',
    raised: '$50M',
    valuation: '$500M',
    competitors: ['CompetitorA', 'CompetitorB', 'CompetitorC'],
  };

  const baseProps = {
    data: mockCompanyData,
    onSelect: vi.fn(),
  };

  // ========== RENDERING ==========
  describe('rendering', () => {
    it('renders card container', () => {
      render(<EnrichmentCard {...baseProps} />);

      expect(screen.getByTestId('enrichment-card')).toBeInTheDocument();
    });

    it('displays company name', () => {
      render(<EnrichmentCard {...baseProps} />);

      expect(screen.getByTestId('company-name')).toHaveTextContent('TechCorp Inc');
    });

    it('displays industry badge', () => {
      render(<EnrichmentCard {...baseProps} />);

      expect(screen.getByTestId('industry-badge')).toHaveTextContent('SaaS');
    });

    it('displays company size', () => {
      render(<EnrichmentCard {...baseProps} />);

      expect(screen.getByText('500-1000')).toBeInTheDocument();
    });

    it('displays founded year', () => {
      render(<EnrichmentCard {...baseProps} />);

      expect(screen.getByText('2018')).toBeInTheDocument();
    });
  });

  // ========== FUNDING INFORMATION ==========
  describe('funding information', () => {
    it('displays funding raised', () => {
      render(<EnrichmentCard {...baseProps} />);

      expect(screen.getByTestId('funding-raised')).toHaveTextContent('$50M');
    });

    it('displays valuation', () => {
      render(<EnrichmentCard {...baseProps} />);

      expect(screen.getByTestId('company-valuation')).toHaveTextContent('$500M');
    });

    it('shows funding stage', () => {
      render(<EnrichmentCard {...baseProps} />);

      expect(screen.getByText(/Series B/)).toBeInTheDocument();
    });
  });

  // ========== COMPETITORS ==========
  describe('competitors list', () => {
    it('displays competitors section', () => {
      render(<EnrichmentCard {...baseProps} />);

      expect(screen.getByTestId('competitors-section')).toBeInTheDocument();
    });

    it('displays each competitor', () => {
      render(<EnrichmentCard {...baseProps} />);

      expect(screen.getByText('CompetitorA')).toBeInTheDocument();
      expect(screen.getByText('CompetitorB')).toBeInTheDocument();
      expect(screen.getByText('CompetitorC')).toBeInTheDocument();
    });

    it('shows competitor count', () => {
      render(<EnrichmentCard {...baseProps} />);

      expect(screen.getByText(/3 competitors/i)).toBeInTheDocument();
    });
  });

  // ========== WEBSITE LINK ==========
  describe('website link', () => {
    it('displays website link', () => {
      render(<EnrichmentCard {...baseProps} />);

      const link = screen.getByRole('link', { name: /techcorp\.io/i });
      expect(link).toHaveAttribute('href', 'https://techcorp.io');
      expect(link).toHaveAttribute('target', '_blank');
    });
  });

  // ========== USE TOGGLE ==========
  describe('use toggle', () => {
    it('displays use toggle switch', () => {
      render(<EnrichmentCard {...baseProps} />);

      expect(screen.getByTestId('use-toggle')).toBeInTheDocument();
    });

    it('triggers onSelect when toggled on', async () => {
      const onSelect = vi.fn();
      render(<EnrichmentCard {...baseProps} onSelect={onSelect} />);

      const toggle = screen.getByTestId('use-toggle');
      fireEvent.click(toggle);

      await waitFor(() => {
        expect(onSelect).toHaveBeenCalledWith(mockCompanyData, true);
      });
    });

    it('triggers onSelect when toggled off', async () => {
      const onSelect = vi.fn();
      render(<EnrichmentCard {...baseProps} isSelected={true} onSelect={onSelect} />);

      const toggle = screen.getByTestId('use-toggle');
      fireEvent.click(toggle);

      await waitFor(() => {
        expect(onSelect).toHaveBeenCalledWith(mockCompanyData, false);
      });
    });

    it('shows selected state', () => {
      render(<EnrichmentCard {...baseProps} isSelected={true} />);

      const toggle = screen.getByTestId('use-toggle');
      expect(toggle).toHaveAttribute('aria-checked', 'true');
    });
  });

  // ========== EXPAND/COLLAPSE ==========
  describe('expand/collapse', () => {
    it('expands on click', async () => {
      render(<EnrichmentCard {...baseProps} />);

      const card = screen.getByTestId('enrichment-card');
      fireEvent.click(card);

      await waitFor(() => {
        expect(card).toHaveClass('expanded');
      });
    });

    it('shows all details when expanded', async () => {
      const { rerender } = render(<EnrichmentCard {...baseProps} />);

      const card = screen.getByTestId('enrichment-card');
      expect(card).not.toHaveClass('expanded');

      rerender(
        <EnrichmentCard {...baseProps} isExpanded={true} />
      );

      await waitFor(() => {
        expect(screen.getByTestId('competitors-section')).toBeVisible();
      });
    });

    it('applies animation class', async () => {
      const { rerender } = render(
        <EnrichmentCard {...baseProps} isExpanded={false} />
      );

      rerender(
        <EnrichmentCard {...baseProps} isExpanded={true} />
      );

      const card = screen.getByTestId('enrichment-card');
      expect(card).toHaveClass('expand-animation');
    });
  });

  // ========== ACCESSIBILITY ==========
  describe('accessibility', () => {
    it('has no axe violations', async () => {
      const { container } = render(<EnrichmentCard {...baseProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has aria-label with company name', () => {
      render(<EnrichmentCard {...baseProps} />);

      const card = screen.getByTestId('enrichment-card');
      expect(card).toHaveAttribute('aria-label', expect.stringContaining('TechCorp Inc'));
    });

    it('toggle has aria-label', () => {
      render(<EnrichmentCard {...baseProps} />);

      const toggle = screen.getByTestId('use-toggle');
      expect(toggle).toHaveAttribute('aria-label');
    });

    it('website link has aria-label', () => {
      render(<EnrichmentCard {...baseProps} />);

      const link = screen.getByRole('link', { name: /techcorp\.io/i });
      expect(link).toHaveAttribute('aria-label');
    });
  });

  // ========== RESPONSIVE ==========
  describe('responsive behavior', () => {
    it('displays at desktop', () => {
      window.innerWidth = 1280;
      render(<EnrichmentCard {...baseProps} />);
      expect(screen.getByTestId('enrichment-card')).toBeVisible();
    });

    it('displays at tablet', () => {
      window.innerWidth = 768;
      render(<EnrichmentCard {...baseProps} />);
      expect(screen.getByTestId('enrichment-card')).toBeVisible();
    });

    it('displays at mobile', () => {
      window.innerWidth = 375;
      render(<EnrichmentCard {...baseProps} />);
      expect(screen.getByTestId('enrichment-card')).toBeVisible();
    });

    it('adjusts card width on mobile', () => {
      window.innerWidth = 375;
      render(<EnrichmentCard {...baseProps} />);

      const card = screen.getByTestId('enrichment-card');
      expect(card).toHaveClass('card-mobile');
    });
  });
});
