/**
 * test_slide_renderer.tsx
 * Unit tests for SlideRenderer component
 * Pitch Deck Canvas - dispatcher for all 8 slide types
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';
import { SlideRenderer } from '../../components/canvases/pitch/SlideRenderer';

expect.extend(toHaveNoViolations);

describe('SlideRenderer', () => {
  const mockSlides = [
    {
      id: 'slide-1',
      type: 'executive_summary',
      title: 'Executive Summary',
      content: { summary: 'Our company overview' },
    },
    {
      id: 'slide-2',
      type: 'product_demo',
      title: 'Product Demo',
      content: { description: 'Demo content' },
    },
    {
      id: 'slide-3',
      type: 'market',
      title: 'Market',
      content: { market_size: '$10B' },
    },
    {
      id: 'slide-4',
      type: 'business_model',
      title: 'Business Model',
      content: { revenue_streams: ['Subscriptions'] },
    },
    {
      id: 'slide-5',
      type: 'financials',
      title: 'Financials',
      content: { revenue: '$1M' },
    },
    {
      id: 'slide-6',
      type: 'team',
      title: 'Team',
      content: { members: ['CEO', 'CTO'] },
    },
    {
      id: 'slide-7',
      type: 'traction',
      title: 'Traction',
      content: { users: '10K' },
    },
    {
      id: 'slide-8',
      type: 'ask',
      title: 'Ask',
      content: { amount: '$5M' },
    },
  ];

  const baseProps = {
    slides: mockSlides,
    currentSlideIndex: 0,
    onNavigate: vi.fn(),
  };

  // ========== RENDERING ==========
  describe('rendering', () => {
    it('renders slide container', () => {
      render(<SlideRenderer {...baseProps} />);

      expect(screen.getByTestId('slide-renderer')).toBeInTheDocument();
    });

    it('displays current slide', () => {
      render(<SlideRenderer {...baseProps} />);

      expect(screen.getByTestId('slide-executive-summary')).toBeInTheDocument();
    });

    it('renders correct slide based on index', () => {
      const { rerender } = render(<SlideRenderer {...baseProps} currentSlideIndex={0} />);

      expect(screen.getByTestId('slide-executive-summary')).toBeInTheDocument();

      rerender(<SlideRenderer {...baseProps} currentSlideIndex={1} />);

      expect(screen.getByTestId('slide-product-demo')).toBeInTheDocument();
    });
  });

  // ========== SLIDE TYPES DISPATCH ==========
  describe('slide type dispatch', () => {
    const slideTypes = [
      { type: 'executive_summary', testId: 'slide-executive-summary' },
      { type: 'product_demo', testId: 'slide-product-demo' },
      { type: 'market', testId: 'slide-market' },
      { type: 'business_model', testId: 'slide-business-model' },
      { type: 'financials', testId: 'slide-financials' },
      { type: 'team', testId: 'slide-team' },
      { type: 'traction', testId: 'slide-traction' },
      { type: 'ask', testId: 'slide-ask' },
    ];

    slideTypes.forEach(({ type, testId }, index) => {
      it(`renders ${type} slide correctly`, () => {
        render(<SlideRenderer {...baseProps} currentSlideIndex={index} />);

        expect(screen.getByTestId(testId)).toBeInTheDocument();
      });
    });
  });

  // ========== NAVIGATION ==========
  describe('keyboard navigation', () => {
    it('navigates to next slide on Enter key', async () => {
      const onNavigate = vi.fn();
      render(<SlideRenderer {...baseProps} onNavigate={onNavigate} />);

      const renderer = screen.getByTestId('slide-renderer');
      fireEvent.keyDown(renderer, { key: 'Enter', code: 'Enter' });

      expect(onNavigate).toHaveBeenCalledWith('next');
    });

    it('navigates to next slide on Space key', async () => {
      const onNavigate = vi.fn();
      render(<SlideRenderer {...baseProps} onNavigate={onNavigate} />);

      const renderer = screen.getByTestId('slide-renderer');
      fireEvent.keyDown(renderer, { key: ' ', code: 'Space' });

      expect(onNavigate).toHaveBeenCalledWith('next');
    });

    it('navigates to previous slide on ArrowLeft', async () => {
      const onNavigate = vi.fn();
      render(<SlideRenderer {...baseProps} currentSlideIndex={2} onNavigate={onNavigate} />);

      const renderer = screen.getByTestId('slide-renderer');
      fireEvent.keyDown(renderer, { key: 'ArrowLeft', code: 'ArrowLeft' });

      expect(onNavigate).toHaveBeenCalledWith('previous');
    });

    it('navigates to next slide on ArrowRight', async () => {
      const onNavigate = vi.fn();
      render(<SlideRenderer {...baseProps} onNavigate={onNavigate} />);

      const renderer = screen.getByTestId('slide-renderer');
      fireEvent.keyDown(renderer, { key: 'ArrowRight', code: 'ArrowRight' });

      expect(onNavigate).toHaveBeenCalledWith('next');
    });

    it('exits presentation on Escape', async () => {
      const onNavigate = vi.fn();
      render(<SlideRenderer {...baseProps} onNavigate={onNavigate} isPresenting={true} />);

      const renderer = screen.getByTestId('slide-renderer');
      fireEvent.keyDown(renderer, { key: 'Escape', code: 'Escape' });

      expect(onNavigate).toHaveBeenCalledWith('exit-presentation');
    });
  });

  // ========== NAVIGATION BUTTONS ==========
  describe('navigation buttons', () => {
    it('displays previous button', () => {
      render(<SlideRenderer {...baseProps} />);

      expect(screen.getByTestId('nav-previous-button')).toBeInTheDocument();
    });

    it('displays next button', () => {
      render(<SlideRenderer {...baseProps} />);

      expect(screen.getByTestId('nav-next-button')).toBeInTheDocument();
    });

    it('previous button triggers onNavigate', () => {
      const onNavigate = vi.fn();
      render(<SlideRenderer {...baseProps} currentSlideIndex={2} onNavigate={onNavigate} />);

      const prevBtn = screen.getByTestId('nav-previous-button');
      fireEvent.click(prevBtn);

      expect(onNavigate).toHaveBeenCalledWith('previous');
    });

    it('next button triggers onNavigate', () => {
      const onNavigate = vi.fn();
      render(<SlideRenderer {...baseProps} onNavigate={onNavigate} />);

      const nextBtn = screen.getByTestId('nav-next-button');
      fireEvent.click(nextBtn);

      expect(onNavigate).toHaveBeenCalledWith('next');
    });

    it('disables previous button on first slide', () => {
      render(<SlideRenderer {...baseProps} currentSlideIndex={0} />);

      const prevBtn = screen.getByTestId('nav-previous-button');
      expect(prevBtn).toHaveAttribute('disabled');
    });

    it('disables next button on last slide', () => {
      render(
        <SlideRenderer {...baseProps} currentSlideIndex={mockSlides.length - 1} />
      );

      const nextBtn = screen.getByTestId('nav-next-button');
      expect(nextBtn).toHaveAttribute('disabled');
    });
  });

  // ========== PRESENTATION MODE ==========
  describe('presentation mode', () => {
    it('applies presentation style when isPresenting=true', () => {
      render(<SlideRenderer {...baseProps} isPresenting={true} />);

      const renderer = screen.getByTestId('slide-renderer');
      expect(renderer).toHaveClass('presentation-mode');
    });

    it('hides UI controls in presentation mode', () => {
      render(<SlideRenderer {...baseProps} isPresenting={true} />);

      expect(screen.queryByTestId('slide-thumbnail')).not.toBeVisible();
    });

    it('shows UI controls in normal mode', () => {
      render(<SlideRenderer {...baseProps} isPresenting={false} />);

      expect(screen.getByTestId('nav-previous-button')).toBeVisible();
    });
  });

  // ========== SLIDE COUNTER ==========
  describe('slide counter', () => {
    it('displays current slide number and total', () => {
      render(<SlideRenderer {...baseProps} currentSlideIndex={0} />);

      const counter = screen.getByTestId('slide-counter');
      expect(counter).toHaveTextContent('1 / 8');
    });

    it('updates counter on navigation', () => {
      const { rerender } = render(<SlideRenderer {...baseProps} currentSlideIndex={0} />);

      expect(screen.getByTestId('slide-counter')).toHaveTextContent('1 / 8');

      rerender(<SlideRenderer {...baseProps} currentSlideIndex={4} />);

      expect(screen.getByTestId('slide-counter')).toHaveTextContent('5 / 8');
    });
  });

  // ========== ACCESSIBILITY ==========
  describe('accessibility', () => {
    it('has no axe violations', async () => {
      const { container } = render(<SlideRenderer {...baseProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('renderer has role="region"', () => {
      render(<SlideRenderer {...baseProps} />);

      const renderer = screen.getByTestId('slide-renderer');
      expect(renderer).toHaveAttribute('role', 'region');
    });

    it('slide counter has aria-live', () => {
      render(<SlideRenderer {...baseProps} />);

      const counter = screen.getByTestId('slide-counter');
      expect(counter).toHaveAttribute('aria-live', 'polite');
    });

    it('navigation buttons have aria-labels', () => {
      render(<SlideRenderer {...baseProps} />);

      const prevBtn = screen.getByTestId('nav-previous-button');
      const nextBtn = screen.getByTestId('nav-next-button');

      expect(prevBtn).toHaveAttribute('aria-label');
      expect(nextBtn).toHaveAttribute('aria-label');
    });

    it('current slide has proper semantics', () => {
      render(<SlideRenderer {...baseProps} />);

      const slide = screen.getByTestId('slide-executive-summary');
      expect(slide).toHaveAttribute('role', 'article');
    });
  });

  // ========== RESPONSIVE ==========
  describe('responsive behavior', () => {
    it('displays correctly at desktop (1280px)', () => {
      window.innerWidth = 1280;
      render(<SlideRenderer {...baseProps} />);
      expect(screen.getByTestId('slide-renderer')).toBeVisible();
    });

    it('displays correctly at tablet (768px)', () => {
      window.innerWidth = 768;
      render(<SlideRenderer {...baseProps} />);
      expect(screen.getByTestId('slide-renderer')).toBeVisible();
    });

    it('displays correctly at mobile (<500px)', () => {
      window.innerWidth = 375;
      render(<SlideRenderer {...baseProps} />);
      expect(screen.getByTestId('slide-renderer')).toBeVisible();
    });

    it('adjusts navigation on mobile', () => {
      window.innerWidth = 375;
      render(<SlideRenderer {...baseProps} />);

      const navButtons = screen.getByTestId('nav-previous-button').parentElement;
      expect(navButtons).toHaveClass('nav-mobile');
    });
  });
});
