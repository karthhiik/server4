/**
 * test_pitch_slides.tsx
 * Unit tests for all 8 Pitch Deck slides
 * Pitch Deck Canvas - individual slide components
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';
import {
  ExecutiveSummarySlide,
  ProductDemoSlide,
  MarketSlide,
  BusinessModelSlide,
  FinancialsSlide,
  TeamSlide,
  TractionSlide,
  AskSlide,
} from '../../components/canvases/pitch/slides';

expect.extend(toHaveNoViolations);

describe('Pitch Slides', () => {
  const commonProps = { onUpdate: vi.fn() };

  // ========== EXECUTIVE SUMMARY SLIDE ==========
  describe('ExecutiveSummarySlide', () => {
    const data = {
      tagline: 'The Airbnb for workspaces',
      companyName: 'WorkSpace Inc',
      problem: 'Real estate utilization is inefficient',
      solution: 'Platform connecting flexible workspaces',
    };

    it('renders executive summary', () => {
      render(<ExecutiveSummarySlide data={data} {...commonProps} />);
      expect(screen.getByTestId('slide-executive-summary')).toBeInTheDocument();
    });

    it('displays company name', () => {
      render(<ExecutiveSummarySlide data={data} {...commonProps} />);
      expect(screen.getByText('WorkSpace Inc')).toBeInTheDocument();
    });

    it('displays tagline', () => {
      render(<ExecutiveSummarySlide data={data} {...commonProps} />);
      expect(screen.getByText('The Airbnb for workspaces')).toBeInTheDocument();
    });

    it('displays problem statement', () => {
      render(<ExecutiveSummarySlide data={data} {...commonProps} />);
      expect(screen.getByText('Real estate utilization is inefficient')).toBeInTheDocument();
    });

    it('displays solution', () => {
      render(<ExecutiveSummarySlide data={data} {...commonProps} />);
      expect(screen.getByText(/flexible workspaces/)).toBeInTheDocument();
    });

    it('has no axe violations', async () => {
      const { container } = render(<ExecutiveSummarySlide data={data} {...commonProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  // ========== PRODUCT DEMO SLIDE ==========
  describe('ProductDemoSlide', () => {
    const data = {
      title: 'Product Demo',
      features: ['Easy booking', 'Real-time availability', 'Secure payments'],
      demoUrl: 'https://demo.workspace.io',
      videoUrl: 'https://video.workspace.io/demo.mp4',
    };

    it('renders product demo slide', () => {
      render(<ProductDemoSlide data={data} {...commonProps} />);
      expect(screen.getByTestId('slide-product-demo')).toBeInTheDocument();
    });

    it('displays demo title', () => {
      render(<ProductDemoSlide data={data} {...commonProps} />);
      expect(screen.getByText('Product Demo')).toBeInTheDocument();
    });

    it('lists all features', () => {
      render(<ProductDemoSlide data={data} {...commonProps} />);
      expect(screen.getByText('Easy booking')).toBeInTheDocument();
      expect(screen.getByText('Real-time availability')).toBeInTheDocument();
    });

    it('has no axe violations', async () => {
      const { container } = render(<ProductDemoSlide data={data} {...commonProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  // ========== MARKET SLIDE ==========
  describe('MarketSlide', () => {
    const data = {
      totalAddressableMarket: '$50B',
      serviceableMarket: '$10B',
      targetMarket: '$1B',
      marketGrowthRate: '25%',
    };

    it('renders market slide', () => {
      render(<MarketSlide data={data} {...commonProps} />);
      expect(screen.getByTestId('slide-market')).toBeInTheDocument();
    });

    it('displays TAM', () => {
      render(<MarketSlide data={data} {...commonProps} />);
      expect(screen.getByText('$50B')).toBeInTheDocument();
    });

    it('displays SAM', () => {
      render(<MarketSlide data={data} {...commonProps} />);
      expect(screen.getByText('$10B')).toBeInTheDocument();
    });

    it('displays growth rate', () => {
      render(<MarketSlide data={data} {...commonProps} />);
      expect(screen.getByText('25%')).toBeInTheDocument();
    });

    it('has no axe violations', async () => {
      const { container } = render(<MarketSlide data={data} {...commonProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  // ========== BUSINESS MODEL SLIDE ==========
  describe('BusinessModelSlide', () => {
    const data = {
      revenueModel: 'Subscription + Commission',
      unitEconomics: '3x LTV:CAC ratio',
      keyMetrics: ['$100/month subscription', '15% commission'],
      margins: '70% gross margin',
    };

    it('renders business model slide', () => {
      render(<BusinessModelSlide data={data} {...commonProps} />);
      expect(screen.getByTestId('slide-business-model')).toBeInTheDocument();
    });

    it('displays revenue model', () => {
      render(<BusinessModelSlide data={data} {...commonProps} />);
      expect(screen.getByText(/Subscription/)).toBeInTheDocument();
    });

    it('displays unit economics', () => {
      render(<BusinessModelSlide data={data} {...commonProps} />);
      expect(screen.getByText('3x LTV:CAC ratio')).toBeInTheDocument();
    });

    it('displays key metrics', () => {
      render(<BusinessModelSlide data={data} {...commonProps} />);
      expect(screen.getByText(/commission/i)).toBeInTheDocument();
    });

    it('has no axe violations', async () => {
      const { container } = render(<BusinessModelSlide data={data} {...commonProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  // ========== FINANCIALS SLIDE ==========
  describe('FinancialsSlide', () => {
    const data = {
      year1Revenue: '$500K',
      year2Revenue: '$2M',
      year3Revenue: '$10M',
      projectedProfitability: 'Year 3',
      burnRate: '$50K/month',
    };

    it('renders financials slide', () => {
      render(<FinancialsSlide data={data} {...commonProps} />);
      expect(screen.getByTestId('slide-financials')).toBeInTheDocument();
    });

    it('displays year 1 revenue', () => {
      render(<FinancialsSlide data={data} {...commonProps} />);
      expect(screen.getByText('$500K')).toBeInTheDocument();
    });

    it('displays profitability timeline', () => {
      render(<FinancialsSlide data={data} {...commonProps} />);
      expect(screen.getByText('Year 3')).toBeInTheDocument();
    });

    it('has no axe violations', async () => {
      const { container } = render(<FinancialsSlide data={data} {...commonProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  // ========== TEAM SLIDE ==========
  describe('TeamSlide', () => {
    const data = {
      team: [
        { name: 'Alice Johnson', title: 'CEO', background: '10 years SaaS' },
        { name: 'Bob Smith', title: 'CTO', background: '8 years Engineering' },
      ],
      advisors: ['Venture Capitalist A', 'Industry Expert B'],
    };

    it('renders team slide', () => {
      render(<TeamSlide data={data} {...commonProps} />);
      expect(screen.getByTestId('slide-team')).toBeInTheDocument();
    });

    it('displays team members', () => {
      render(<TeamSlide data={data} {...commonProps} />);
      expect(screen.getByText('Alice Johnson')).toBeInTheDocument();
      expect(screen.getByText('Bob Smith')).toBeInTheDocument();
    });

    it('displays titles', () => {
      render(<TeamSlide data={data} {...commonProps} />);
      expect(screen.getByText('CEO')).toBeInTheDocument();
      expect(screen.getByText('CTO')).toBeInTheDocument();
    });

    it('displays advisors', () => {
      render(<TeamSlide data={data} {...commonProps} />);
      expect(screen.getByText(/Venture Capitalist/)).toBeInTheDocument();
    });

    it('has no axe violations', async () => {
      const { container } = render(<TeamSlide data={data} {...commonProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  // ========== TRACTION SLIDE ==========
  describe('TractionSlide', () => {
    const data = {
      users: '50K active users',
      revenue: '$500K MRR',
      growth: '20% MoM',
      milestones: ['1st product launch', 'Series A ready'],
    };

    it('renders traction slide', () => {
      render(<TractionSlide data={data} {...commonProps} />);
      expect(screen.getByTestId('slide-traction')).toBeInTheDocument();
    });

    it('displays user count', () => {
      render(<TractionSlide data={data} {...commonProps} />);
      expect(screen.getByText('50K active users')).toBeInTheDocument();
    });

    it('displays revenue', () => {
      render(<TractionSlide data={data} {...commonProps} />);
      expect(screen.getByText('$500K MRR')).toBeInTheDocument();
    });

    it('displays growth rate', () => {
      render(<TractionSlide data={data} {...commonProps} />);
      expect(screen.getByText('20% MoM')).toBeInTheDocument();
    });

    it('lists milestones', () => {
      render(<TractionSlide data={data} {...commonProps} />);
      expect(screen.getByText(/launch/)).toBeInTheDocument();
    });

    it('has no axe violations', async () => {
      const { container } = render(<TractionSlide data={data} {...commonProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });

  // ========== ASK SLIDE ==========
  describe('AskSlide', () => {
    const data = {
      fundingAmount: '$5M',
      fundingStage: 'Series A',
      usesOfFunds: ['Product development', 'Sales & Marketing', 'Team expansion'],
      targetInvestors: 'VC firms with SaaS experience',
    };

    it('renders ask slide', () => {
      render(<AskSlide data={data} {...commonProps} />);
      expect(screen.getByTestId('slide-ask')).toBeInTheDocument();
    });

    it('displays funding amount', () => {
      render(<AskSlide data={data} {...commonProps} />);
      expect(screen.getByText('$5M')).toBeInTheDocument();
    });

    it('displays funding stage', () => {
      render(<AskSlide data={data} {...commonProps} />);
      expect(screen.getByText('Series A')).toBeInTheDocument();
    });

    it('displays uses of funds', () => {
      render(<AskSlide data={data} {...commonProps} />);
      expect(screen.getByText('Product development')).toBeInTheDocument();
      expect(screen.getByText('Sales & Marketing')).toBeInTheDocument();
    });

    it('displays target investors', () => {
      render(<AskSlide data={data} {...commonProps} />);
      expect(screen.getByText(/VC firms/)).toBeInTheDocument();
    });

    it('has no axe violations', async () => {
      const { container } = render(<AskSlide data={data} {...commonProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });
  });
});
