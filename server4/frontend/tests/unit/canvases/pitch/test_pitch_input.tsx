/**
 * test_pitch_input.tsx
 * Unit tests for PitchInput component
 * Pitch Deck Canvas - input form with prompt submission
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import { PitchInput } from '../../components/canvases/pitch/PitchInput';

expect.extend(toHaveNoViolations);

describe('PitchInput', () => {
  const baseProps = {
    onPromptSubmit: vi.fn(),
    onToggleForm: vi.fn(),
  };

  // ========== RENDERING ==========
  describe('rendering', () => {
    it('renders input form', () => {
      render(<PitchInput {...baseProps} />);

      expect(screen.getByTestId('pitch-input-form')).toBeInTheDocument();
    });

    it('displays prompt input field', () => {
      render(<PitchInput {...baseProps} />);

      expect(screen.getByTestId('prompt-input')).toBeInTheDocument();
    });

    it('displays submit button', () => {
      render(<PitchInput {...baseProps} />);

      expect(screen.getByTestId('submit-prompt-button')).toBeInTheDocument();
    });

    it('displays form toggle button', () => {
      render(<PitchInput {...baseProps} />);

      expect(screen.getByTestId('toggle-form-button')).toBeInTheDocument();
    });
  });

  // ========== PROMPT SUBMISSION ==========
  describe('prompt submission', () => {
    it('enables submit button with valid input', async () => {
      const user = userEvent.setup();
      render(<PitchInput {...baseProps} />);

      const input = screen.getByTestId('prompt-input');
      await user.type(input, 'Create a pitch deck for my SaaS startup');

      const submitBtn = screen.getByTestId('submit-prompt-button');
      expect(submitBtn).not.toHaveAttribute('disabled');
    });

    it('disables submit button with empty input', () => {
      render(<PitchInput {...baseProps} />);

      const submitBtn = screen.getByTestId('submit-prompt-button');
      expect(submitBtn).toHaveAttribute('disabled');
    });

    it('triggers onPromptSubmit on button click', async () => {
      const user = userEvent.setup();
      const onPromptSubmit = vi.fn();
      render(<PitchInput {...baseProps} onPromptSubmit={onPromptSubmit} />);

      const input = screen.getByTestId('prompt-input');
      await user.type(input, 'Create a pitch deck');

      const submitBtn = screen.getByTestId('submit-prompt-button');
      fireEvent.click(submitBtn);

      expect(onPromptSubmit).toHaveBeenCalledWith('Create a pitch deck');
    });

    it('clears input after submission', async () => {
      const user = userEvent.setup();
      render(<PitchInput {...baseProps} />);

      const input = screen.getByTestId('prompt-input') as HTMLInputElement;
      await user.type(input, 'Create a pitch deck');

      const submitBtn = screen.getByTestId('submit-prompt-button');
      fireEvent.click(submitBtn);

      await waitFor(() => {
        expect(input.value).toBe('');
      });
    });

    it('submits on Enter key', async () => {
      const user = userEvent.setup();
      const onPromptSubmit = vi.fn();
      render(<PitchInput {...baseProps} onPromptSubmit={onPromptSubmit} />);

      const input = screen.getByTestId('prompt-input');
      await user.type(input, 'Create a pitch deck{Enter}');

      expect(onPromptSubmit).toHaveBeenCalled();
    });
  });

  // ========== FORM TOGGLE ==========
  describe('form toggle', () => {
    it('triggers onToggleForm on button click', () => {
      const onToggleForm = vi.fn();
      render(<PitchInput {...baseProps} onToggleForm={onToggleForm} />);

      const toggleBtn = screen.getByTestId('toggle-form-button');
      fireEvent.click(toggleBtn);

      expect(onToggleForm).toHaveBeenCalledTimes(1);
    });

    it('shows form sections when expanded', async () => {
      render(<PitchInput {...baseProps} isExpanded={true} />);

      expect(screen.getByTestId('form-section-summary')).toBeInTheDocument();
      expect(screen.getByTestId('form-section-market')).toBeInTheDocument();
    });

    it('collapses form sections when collapsed', async () => {
      const { rerender } = render(<PitchInput {...baseProps} isExpanded={true} />);

      expect(screen.getByTestId('form-section-summary')).toBeVisible();

      rerender(<PitchInput {...baseProps} isExpanded={false} />);

      expect(screen.queryByTestId('form-section-summary')).not.toBeVisible();
    });
  });

  // ========== ENTITY DETECTION ==========
  describe('entity detection', () => {
    it('displays detected entities as chips', () => {
      render(
        <PitchInput
          {...baseProps}
          detectedEntities={[
            { id: 'e1', name: 'TechCorp', type: 'company' },
            { id: 'e2', name: 'John Doe', type: 'person' },
          ]}
        />
      );

      expect(screen.getByTestId('entity-chip-e1')).toHaveTextContent('TechCorp');
      expect(screen.getByTestId('entity-chip-e2')).toHaveTextContent('John Doe');
    });

    it('removes entity chip on close', async () => {
      const { rerender } = render(
        <PitchInput
          {...baseProps}
          detectedEntities={[{ id: 'e1', name: 'TechCorp', type: 'company' }]}
        />
      );

      const closeBtn = screen.getByTestId('close-entity-e1');
      fireEvent.click(closeBtn);

      await waitFor(() => {
        expect(screen.queryByTestId('entity-chip-e1')).not.toBeInTheDocument();
      });
    });
  });

  // ========== LOADING STATE ==========
  describe('loading state', () => {
    it('shows spinner during submission', () => {
      render(<PitchInput {...baseProps} isGenerating={true} />);

      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    });

    it('disables submit button during generation', () => {
      render(<PitchInput {...baseProps} isGenerating={true} />);

      const submitBtn = screen.getByTestId('submit-prompt-button');
      expect(submitBtn).toHaveAttribute('disabled');
    });

    it('shows generating text', () => {
      render(<PitchInput {...baseProps} isGenerating={true} />);

      expect(screen.getByText(/generating/i)).toBeInTheDocument();
    });
  });

  // ========== ACCESSIBILITY ==========
  describe('accessibility', () => {
    it('has no axe violations', async () => {
      const { container } = render(<PitchInput {...baseProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('prompt input has aria-label', () => {
      render(<PitchInput {...baseProps} />);

      const input = screen.getByTestId('prompt-input');
      expect(input).toHaveAttribute('aria-label');
    });

    it('submit button has aria-label', () => {
      render(<PitchInput {...baseProps} />);

      const submitBtn = screen.getByTestId('submit-prompt-button');
      expect(submitBtn).toHaveAttribute('aria-label');
    });
  });

  // ========== RESPONSIVE ==========
  describe('responsive behavior', () => {
    it('displays correctly at desktop (1280px)', () => {
      window.innerWidth = 1280;
      render(<PitchInput {...baseProps} />);
      expect(screen.getByTestId('pitch-input-form')).toBeVisible();
    });

    it('displays correctly at tablet (768px)', () => {
      window.innerWidth = 768;
      render(<PitchInput {...baseProps} />);
      expect(screen.getByTestId('pitch-input-form')).toBeVisible();
    });

    it('displays correctly at mobile (<500px)', () => {
      window.innerWidth = 375;
      render(<PitchInput {...baseProps} />);
      expect(screen.getByTestId('pitch-input-form')).toBeVisible();
    });
  });
});
