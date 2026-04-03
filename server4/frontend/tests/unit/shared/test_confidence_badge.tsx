/**
 * test_confidence_badge.tsx
 * Unit tests for ConfidenceBadge component
 * Shared Brain Component - 6 confidence levels, 3 sizes, hover tooltips
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';
import { ConfidenceBadge } from '../../components/shared/ConfidenceBadge';

expect.extend(toHaveNoViolations);

describe('ConfidenceBadge', () => {
  // ========== CONFIDENCE LEVELS ==========
  describe('confidence levels', () => {
    it('renders verified badge', () => {
      render(<ConfidenceBadge level="verified" />);
      expect(screen.getByTestId('confidence-badge')).toHaveAttribute('data-level', 'verified');
      expect(screen.getByText(/verified/i)).toBeInTheDocument();
    });

    it('renders corroborated badge', () => {
      render(<ConfidenceBadge level="corroborated" />);
      expect(screen.getByTestId('confidence-badge')).toHaveAttribute('data-level', 'corroborated');
      expect(screen.getByText(/corroborated/i)).toBeInTheDocument();
    });

    it('renders inference badge', () => {
      render(<ConfidenceBadge level="inference" />);
      expect(screen.getByTestId('confidence-badge')).toHaveAttribute('data-level', 'inference');
    });

    it('renders scenario badge', () => {
      render(<ConfidenceBadge level="scenario" />);
      expect(screen.getByTestId('confidence-badge')).toHaveAttribute('data-level', 'scenario');
    });

    it('renders weak_signal badge', () => {
      render(<ConfidenceBadge level="weak_signal" />);
      expect(screen.getByTestId('confidence-badge')).toHaveAttribute('data-level', 'weak_signal');
    });

    it('renders blocked badge', () => {
      render(<ConfidenceBadge level="blocked" />);
      expect(screen.getByTestId('confidence-badge')).toHaveAttribute('data-level', 'blocked');
    });
  });

  // ========== SIZES ==========
  describe('sizes', () => {
    it('renders small size (sm)', () => {
      render(<ConfidenceBadge level="verified" size="sm" />);
      const badge = screen.getByTestId('confidence-badge');
      expect(badge).toHaveAttribute('data-size', 'sm');
      expect(badge).toHaveClass('size-sm');
    });

    it('renders medium size (md)', () => {
      render(<ConfidenceBadge level="verified" size="md" />);
      const badge = screen.getByTestId('confidence-badge');
      expect(badge).toHaveAttribute('data-size', 'md');
      expect(badge).toHaveClass('size-md');
    });

    it('renders large size (lg)', () => {
      render(<ConfidenceBadge level="verified" size="lg" />);
      const badge = screen.getByTestId('confidence-badge');
      expect(badge).toHaveAttribute('data-size', 'lg');
      expect(badge).toHaveClass('size-lg');
    });
  });

  // ========== ICONS AND LABELS ==========
  describe('icons and labels', () => {
    it('shows icon and label on md size', () => {
      render(<ConfidenceBadge level="verified" size="md" />);
      const icon = screen.getByTestId('confidence-icon');
      expect(icon).toBeInTheDocument();
      expect(screen.getByText(/verified/i)).toBeInTheDocument();
    });

    it('shows icon and label on lg size', () => {
      render(<ConfidenceBadge level="verified" size="lg" />);
      const icon = screen.getByTestId('confidence-icon');
      expect(icon).toBeInTheDocument();
      expect(screen.getByText(/verified/i)).toBeInTheDocument();
    });

    it('hides label on sm size', () => {
      render(<ConfidenceBadge level="verified" size="sm" />);
      const badge = screen.getByTestId('confidence-badge');
      // sm should only show icon, no visible label
      expect(badge.querySelector('[class*="label"]')?.textContent).toBe('');
    });

    it('renders correct icon for each level', () => {
      const levels = ['verified', 'corroborated', 'inference', 'scenario', 'weak_signal', 'blocked'];
      levels.forEach((level) => {
        const { unmount } = render(<ConfidenceBadge level={level as any} size="md" />);
        const icon = screen.getByTestId('confidence-icon');
        expect(icon).toBeInTheDocument();
        unmount();
      });
    });
  });

  // ========== INTERACTIONS ==========
  describe('interactions', () => {
    it('triggers onClick callback', () => {
      const handleClick = vi.fn();
      render(<ConfidenceBadge level="verified" onClick={handleClick} />);

      const badge = screen.getByTestId('confidence-badge');
      fireEvent.click(badge);

      expect(handleClick).toHaveBeenCalledTimes(1);
    });

    it('shows tooltip on hover (sm size)', async () => {
      render(<ConfidenceBadge level="verified" size="sm" />);

      const badge = screen.getByTestId('confidence-badge');
      fireEvent.mouseEnter(badge);

      await waitFor(() => {
        const tooltip = screen.getByRole('tooltip');
        expect(tooltip).toBeVisible();
      });
    });

    it('hides tooltip on mouse leave', async () => {
      render(<ConfidenceBadge level="verified" size="sm" />);

      const badge = screen.getByTestId('confidence-badge');
      fireEvent.mouseEnter(badge);

      await waitFor(() => {
        expect(screen.getByRole('tooltip')).toBeVisible();
      });

      fireEvent.mouseLeave(badge);

      await waitFor(() => {
        expect(screen.getByRole('tooltip')).not.toBeVisible();
      });
    });

    it('tooltip contains level description', async () => {
      render(<ConfidenceBadge level="verified" size="sm" />);

      const badge = screen.getByTestId('confidence-badge');
      fireEvent.mouseEnter(badge);

      await waitFor(() => {
        const tooltip = screen.getByRole('tooltip');
        expect(tooltip.textContent).toContain('verified');
      });
    });
  });

  // ========== ACCESSIBILITY ==========
  describe('accessibility', () => {
    it('has no axe violations', async () => {
      const { container } = render(<ConfidenceBadge level="verified" size="md" />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('has proper aria-label', () => {
      render(<ConfidenceBadge level="verified" />);
      const badge = screen.getByTestId('confidence-badge');
      expect(badge).toHaveAttribute('aria-label', expect.stringContaining('verified'));
    });

    it('tooltip has role="tooltip"', async () => {
      render(<ConfidenceBadge level="verified" size="sm" />);

      const badge = screen.getByTestId('confidence-badge');
      fireEvent.mouseEnter(badge);

      await waitFor(() => {
        expect(screen.getByRole('tooltip')).toBeInTheDocument();
      });
    });
  });

  // ========== STYLING ==========
  describe('styling', () => {
    it('applies verified color class', () => {
      render(<ConfidenceBadge level="verified" size="md" />);
      const badge = screen.getByTestId('confidence-badge');
      expect(badge).toHaveClass('bg-green-100', 'text-green-800');
    });

    it('applies corroborated color class', () => {
      render(<ConfidenceBadge level="corroborated" size="md" />);
      const badge = screen.getByTestId('confidence-badge');
      expect(badge).toHaveClass('bg-blue-100', 'text-blue-800');
    });

    it('applies blocked color class', () => {
      render(<ConfidenceBadge level="blocked" size="md" />);
      const badge = screen.getByTestId('confidence-badge');
      expect(badge).toHaveClass('bg-red-100', 'text-red-800');
    });
  });

  // ========== RESPONSIVE ==========
  describe('responsive behavior', () => {
    it('displays correctly at desktop (1280px)', () => {
      window.innerWidth = 1280;
      render(<ConfidenceBadge level="verified" size="md" />);
      expect(screen.getByTestId('confidence-badge')).toBeVisible();
    });

    it('displays correctly at tablet (768px)', () => {
      window.innerWidth = 768;
      render(<ConfidenceBadge level="verified" size="md" />);
      expect(screen.getByTestId('confidence-badge')).toBeVisible();
    });

    it('displays correctly at mobile (<500px)', () => {
      window.innerWidth = 375;
      render(<ConfidenceBadge level="verified" size="sm" />);
      expect(screen.getByTestId('confidence-badge')).toBeVisible();
    });
  });
});
