/**
 * test_section_editor.tsx
 * Unit tests for SectionEditor component
 * Shared Brain Component - markdown editor with AI commands
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';
import userEvent from '@testing-library/user-event';
import { SectionEditor } from '../../components/shared/SectionEditor';

expect.extend(toHaveNoViolations);

// Mock React Quill
vi.mock('react-quill', () => ({
  default: ({ value, onChange, placeholder }: any) => (
    <textarea
      data-testid="quill-editor"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
    />
  ),
}));

describe('SectionEditor', () => {
  const baseProps = {
    title: 'Executive Overview',
    content: 'This is the current section content.',
    confidenceLevel: 'verified' as const,
    onRegenerate: vi.fn(),
    onSave: vi.fn(),
  };

  // ========== RENDER MODES ==========
  describe('render modes', () => {
    it('renders read mode by default', () => {
      render(<SectionEditor {...baseProps} />);

      const readView = screen.getByTestId('section-read-mode');
      expect(readView).toBeInTheDocument();
    });

    it('displays markdown content in read mode', () => {
      render(<SectionEditor {...baseProps} />);

      expect(screen.getByText(/This is the current section content/)).toBeInTheDocument();
    });

    it('toggles to edit mode on button click', async () => {
      render(<SectionEditor {...baseProps} />);

      const editToggle = screen.getByTestId('edit-toggle-button');
      fireEvent.click(editToggle);

      await waitFor(() => {
        expect(screen.getByTestId('quill-editor')).toBeInTheDocument();
      });
    });

    it('returns to read mode from edit mode', async () => {
      render(<SectionEditor {...baseProps} />);

      const editToggle = screen.getByTestId('edit-toggle-button');
      fireEvent.click(editToggle);

      await waitFor(() => {
        expect(screen.getByTestId('quill-editor')).toBeInTheDocument();
      });

      fireEvent.click(editToggle);

      await waitFor(() => {
        expect(screen.queryByTestId('quill-editor')).not.toBeInTheDocument();
      });
    });
  });

  // ========== HEADER ==========
  describe('header with confidence badge', () => {
    it('displays title in header', () => {
      render(<SectionEditor {...baseProps} />);

      expect(screen.getByTestId('section-title')).toHaveTextContent('Executive Overview');
    });

    it('displays ConfidenceBadge in header', () => {
      render(<SectionEditor {...baseProps} />);

      const badge = screen.getByTestId('confidence-badge');
      expect(badge).toHaveAttribute('data-level', 'verified');
    });

    it('renders different confidence levels', () => {
      const { unmount } = render(
        <SectionEditor {...baseProps} confidenceLevel="corroborated" />
      );

      expect(screen.getByTestId('confidence-badge')).toHaveAttribute('data-level', 'corroborated');
      unmount();

      render(
        <SectionEditor {...baseProps} confidenceLevel="inference" />
      );

      expect(screen.getByTestId('confidence-badge')).toHaveAttribute('data-level', 'inference');
    });
  });

  // ========== QUILL EDITOR ==========
  describe('React Quill editor', () => {
    it('shows React Quill in edit mode', async () => {
      render(<SectionEditor {...baseProps} />);

      const editToggle = screen.getByTestId('edit-toggle-button');
      fireEvent.click(editToggle);

      await waitFor(() => {
        expect(screen.getByTestId('quill-editor')).toBeInTheDocument();
      });
    });

    it('pre-fills editor with current content', async () => {
      render(<SectionEditor {...baseProps} />);

      const editToggle = screen.getByTestId('edit-toggle-button');
      fireEvent.click(editToggle);

      await waitFor(() => {
        const editor = screen.getByTestId('quill-editor') as HTMLTextAreaElement;
        expect(editor.value).toContain(baseProps.content);
      });
    });

    it('updates content on editor change', async () => {
      const user = userEvent.setup();
      render(<SectionEditor {...baseProps} />);

      const editToggle = screen.getByTestId('edit-toggle-button');
      fireEvent.click(editToggle);

      await waitFor(() => {
        expect(screen.getByTestId('quill-editor')).toBeInTheDocument();
      });

      const editor = screen.getByTestId('quill-editor') as HTMLTextAreaElement;
      await user.clear(editor);
      await user.type(editor, 'New content');

      expect(editor.value).toBe('New content');
    });
  });

  // ========== COMMAND MENU ==========
  describe('command menu (/)', () => {
    beforeEach(() => {
      render(<SectionEditor {...baseProps} />);

      const editToggle = screen.getByTestId('edit-toggle-button');
      fireEvent.click(editToggle);
    });

    it('shows command menu when "/" is typed', async () => {
      const editor = screen.getByTestId('quill-editor') as HTMLTextAreaElement;

      await waitFor(() => {
        fireEvent.change(editor, { target: { value: '/' } });
      });

      await waitFor(() => {
        expect(screen.getByTestId('command-menu')).toBeInTheDocument();
      });
    });

    it('displays rewrite command', async () => {
      const editor = screen.getByTestId('quill-editor') as HTMLTextAreaElement;

      fireEvent.change(editor, { target: { value: '/' } });

      await waitFor(() => {
        expect(screen.getByText('/rewrite')).toBeInTheDocument();
      });
    });

    it('displays expand command', async () => {
      const editor = screen.getByTestId('quill-editor') as HTMLTextAreaElement;

      fireEvent.change(editor, { target: { value: '/' } });

      await waitFor(() => {
        expect(screen.getByText('/expand')).toBeInTheDocument();
      });
    });

    it('displays add-data command', async () => {
      const editor = screen.getByTestId('quill-editor') as HTMLTextAreaElement;

      fireEvent.change(editor, { target: { value: '/' } });

      await waitFor(() => {
        expect(screen.getByText('/add-data')).toBeInTheDocument();
      });
    });

    it('displays make-punchier command', async () => {
      const editor = screen.getByTestId('quill-editor') as HTMLTextAreaElement;

      fireEvent.change(editor, { target: { value: '/' } });

      await waitFor(() => {
        expect(screen.getByText(/make-punchier/i)).toBeInTheDocument();
      });
    });

    it('displays simplify command', async () => {
      const editor = screen.getByTestId('quill-editor') as HTMLTextAreaElement;

      fireEvent.change(editor, { target: { value: '/' } });

      await waitFor(() => {
        expect(screen.getByText('/simplify')).toBeInTheDocument();
      });
    });

    it('hides menu when "/" is removed', async () => {
      const editor = screen.getByTestId('quill-editor') as HTMLTextAreaElement;

      fireEvent.change(editor, { target: { value: '/' } });

      await waitFor(() => {
        expect(screen.getByTestId('command-menu')).toBeInTheDocument();
      });

      fireEvent.change(editor, { target: { value: 'normal text' } });

      await waitFor(() => {
        expect(screen.queryByTestId('command-menu')).not.toBeInTheDocument();
      });
    });
  });

  // ========== AI SPARKLE BUTTON ==========
  describe('AI Sparkle button', () => {
    it('shows on hover in read mode', async () => {
      render(<SectionEditor {...baseProps} />);

      const readView = screen.getByTestId('section-read-mode');
      fireEvent.mouseEnter(readView);

      await waitFor(() => {
        expect(screen.getByTestId('ai-sparkle-button')).toBeInTheDocument();
      });
    });

    it('hides when not hovering', () => {
      render(<SectionEditor {...baseProps} />);

      const readView = screen.getByTestId('section-read-mode');
      fireEvent.mouseLeave(readView);

      expect(screen.queryByTestId('ai-sparkle-button')).not.toBeInTheDocument();
    });

    it('is hidden in edit mode', async () => {
      render(<SectionEditor {...baseProps} />);

      const editToggle = screen.getByTestId('edit-toggle-button');
      fireEvent.click(editToggle);

      await waitFor(() => {
        expect(screen.queryByTestId('ai-sparkle-button')).not.toBeInTheDocument();
      });
    });
  });

  // ========== REGENERATE BUTTON ==========
  describe('regenerate button', () => {
    it('shows regenerate button in edit mode', async () => {
      render(<SectionEditor {...baseProps} />);

      const editToggle = screen.getByTestId('edit-toggle-button');
      fireEvent.click(editToggle);

      await waitFor(() => {
        expect(screen.getByTestId('regenerate-button')).toBeInTheDocument();
      });
    });

    it('triggers onRegenerate callback', async () => {
      const onRegenerate = vi.fn();
      render(<SectionEditor {...baseProps} onRegenerate={onRegenerate} />);

      const editToggle = screen.getByTestId('edit-toggle-button');
      fireEvent.click(editToggle);

      await waitFor(() => {
        expect(screen.getByTestId('regenerate-button')).toBeInTheDocument();
      });

      const regenerateBtn = screen.getByTestId('regenerate-button');
      fireEvent.click(regenerateBtn);

      expect(onRegenerate).toHaveBeenCalledTimes(1);
    });

    it('shows loading state during regeneration', async () => {
      const onRegenerate = vi.fn();
      const { rerender } = render(
        <SectionEditor {...baseProps} onRegenerate={onRegenerate} isRegenerating={false} />
      );

      const editToggle = screen.getByTestId('edit-toggle-button');
      fireEvent.click(editToggle);

      await waitFor(() => {
        expect(screen.getByTestId('regenerate-button')).toBeInTheDocument();
      });

      rerender(
        <SectionEditor {...baseProps} onRegenerate={onRegenerate} isRegenerating={true} />
      );

      const regenerateBtn = screen.getByTestId('regenerate-button');
      expect(regenerateBtn).toHaveAttribute('disabled');
      expect(screen.getByTestId('loading-spinner')).toBeInTheDocument();
    });
  });

  // ========== SAVE DRAFT ==========
  describe('save draft', () => {
    it('saves to local storage on save', async () => {
      const onSave = vi.fn();
      render(<SectionEditor {...baseProps} onSave={onSave} />);

      const editToggle = screen.getByTestId('edit-toggle-button');
      fireEvent.click(editToggle);

      await waitFor(() => {
        expect(screen.getByTestId('quill-editor')).toBeInTheDocument();
      });

      const saveBtn = screen.getByTestId('save-draft-button');
      fireEvent.click(saveBtn);

      expect(onSave).toHaveBeenCalled();
    });

    it('loads draft from local storage on mount', () => {
      const savedDraft = 'Saved draft content';
      localStorage.setItem(`section-${baseProps.title}`, savedDraft);

      render(<SectionEditor {...baseProps} />);

      const editToggle = screen.getByTestId('edit-toggle-button');
      fireEvent.click(editToggle);

      const editor = screen.getByTestId('quill-editor') as HTMLTextAreaElement;
      expect(editor.value).toContain(savedDraft);

      localStorage.removeItem(`section-${baseProps.title}`);
    });
  });

  // ========== ACCESSIBILITY ==========
  describe('accessibility', () => {
    it('has no axe violations', async () => {
      const { container } = render(<SectionEditor {...baseProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('title has proper heading role', () => {
      render(<SectionEditor {...baseProps} />);

      const title = screen.getByTestId('section-title');
      expect(title).toHaveAttribute('role', 'heading');
    });

    it('edit toggle button has aria-label', () => {
      render(<SectionEditor {...baseProps} />);

      const toggle = screen.getByTestId('edit-toggle-button');
      expect(toggle).toHaveAttribute('aria-label');
    });

    it('read view has proper semantic markup', () => {
      render(<SectionEditor {...baseProps} />);

      const readView = screen.getByTestId('section-read-mode');
      expect(readView).toHaveAttribute('role', 'region');
    });
  });

  // ========== RESPONSIVE ==========
  describe('responsive behavior', () => {
    it('displays correctly at desktop (1280px)', () => {
      window.innerWidth = 1280;
      render(<SectionEditor {...baseProps} />);
      expect(screen.getByTestId('section-read-mode')).toBeVisible();
    });

    it('displays correctly at tablet (768px)', () => {
      window.innerWidth = 768;
      render(<SectionEditor {...baseProps} />);
      expect(screen.getByTestId('section-read-mode')).toBeVisible();
    });

    it('displays correctly at mobile (<500px)', () => {
      window.innerWidth = 375;
      render(<SectionEditor {...baseProps} />);
      expect(screen.getByTestId('section-read-mode')).toBeVisible();
    });

    it('adjusts editor width on mobile', async () => {
      window.innerWidth = 375;
      render(<SectionEditor {...baseProps} />);

      const editToggle = screen.getByTestId('edit-toggle-button');
      fireEvent.click(editToggle);

      await waitFor(() => {
        const editor = screen.getByTestId('quill-editor');
        expect(editor).toHaveClass('editor-mobile');
      });
    });
  });
});
