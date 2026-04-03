/**
 * test_export_toolbar.tsx
 * Unit tests for ExportToolbar component
 * Shared Brain Component - floating export pill with radial menu
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';
import { ExportToolbar } from '../../components/shared/ExportToolbar';

expect.extend(toHaveNoViolations);

describe('ExportToolbar', () => {
  const baseProps = {
    onExport: vi.fn(),
  };

  // ========== RENDERING ==========
  describe('rendering', () => {
    it('renders floating pill bottom-right', () => {
      render(<ExportToolbar {...baseProps} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      expect(pill).toBeInTheDocument();
      expect(pill).toHaveClass('floating-pill');
    });

    it('displays export icon in pill', () => {
      render(<ExportToolbar {...baseProps} />);

      const icon = screen.getByTestId('export-icon');
      expect(icon).toBeInTheDocument();
    });

    it('positions in bottom-right corner', () => {
      render(<ExportToolbar {...baseProps} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      expect(pill).toHaveStyle({
        position: 'fixed',
        bottom: expect.any(String),
        right: expect.any(String),
      });
    });
  });

  // ========== HOVER EXPANSION ==========
  describe('hover expansion', () => {
    it('shows only pill on initial state', () => {
      render(<ExportToolbar {...baseProps} />);

      expect(screen.getByTestId('export-toolbar-pill')).toBeInTheDocument();
      expect(screen.queryByTestId('export-buttons-radial')).not.toBeInTheDocument();
    });

    it('expands radial menu on hover', async () => {
      render(<ExportToolbar {...baseProps} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      fireEvent.mouseEnter(pill);

      await waitFor(() => {
        expect(screen.getByTestId('export-buttons-radial')).toBeInTheDocument();
      });
    });

    it('displays all 5 format buttons when expanded', async () => {
      render(<ExportToolbar {...baseProps} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      fireEvent.mouseEnter(pill);

      await waitFor(() => {
        expect(screen.getByTestId('export-btn-pdf')).toBeInTheDocument();
        expect(screen.getByTestId('export-btn-docx')).toBeInTheDocument();
        expect(screen.getByTestId('export-btn-markdown')).toBeInTheDocument();
        expect(screen.getByTestId('export-btn-png')).toBeInTheDocument();
        expect(screen.getByTestId('export-btn-toon')).toBeInTheDocument();
      });
    });

    it('collapses radial menu on mouse leave', async () => {
      render(<ExportToolbar {...baseProps} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      fireEvent.mouseEnter(pill);

      await waitFor(() => {
        expect(screen.getByTestId('export-buttons-radial')).toBeInTheDocument();
      });

      fireEvent.mouseLeave(pill);

      await waitFor(() => {
        expect(screen.queryByTestId('export-buttons-radial')).not.toBeInTheDocument();
      });
    });

    it('applies animation class on expand', async () => {
      render(<ExportToolbar {...baseProps} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      fireEvent.mouseEnter(pill);

      await waitFor(() => {
        const radial = screen.getByTestId('export-buttons-radial');
        expect(radial).toHaveClass('radial-expand-animation');
      });
    });
  });

  // ========== FORMAT BUTTONS ==========
  describe('format buttons', () => {
    beforeEach(async () => {
      render(<ExportToolbar {...baseProps} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      fireEvent.mouseEnter(pill);

      await waitFor(() => {
        expect(screen.getByTestId('export-buttons-radial')).toBeInTheDocument();
      });
    });

    it('PDF button triggers pdf export', async () => {
      const onExport = vi.fn();
      render(<ExportToolbar {...baseProps} onExport={onExport} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      fireEvent.mouseEnter(pill);

      await waitFor(() => {
        const pdfBtn = screen.getByTestId('export-btn-pdf');
        fireEvent.click(pdfBtn);
      });

      expect(onExport).toHaveBeenCalledWith('pdf');
    });

    it('DOCX button triggers docx export', async () => {
      const onExport = vi.fn();
      render(<ExportToolbar {...baseProps} onExport={onExport} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      fireEvent.mouseEnter(pill);

      await waitFor(() => {
        const docxBtn = screen.getByTestId('export-btn-docx');
        fireEvent.click(docxBtn);
      });

      expect(onExport).toHaveBeenCalledWith('docx');
    });

    it('Markdown button triggers markdown export', async () => {
      const onExport = vi.fn();
      render(<ExportToolbar {...baseProps} onExport={onExport} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      fireEvent.mouseEnter(pill);

      await waitFor(() => {
        const mdBtn = screen.getByTestId('export-btn-markdown');
        fireEvent.click(mdBtn);
      });

      expect(onExport).toHaveBeenCalledWith('markdown');
    });

    it('PNG button triggers png export', async () => {
      const onExport = vi.fn();
      render(<ExportToolbar {...baseProps} onExport={onExport} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      fireEvent.mouseEnter(pill);

      await waitFor(() => {
        const pngBtn = screen.getByTestId('export-btn-png');
        fireEvent.click(pngBtn);
      });

      expect(onExport).toHaveBeenCalledWith('png');
    });

    it('TOON button triggers toon export', async () => {
      const onExport = vi.fn();
      render(<ExportToolbar {...baseProps} onExport={onExport} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      fireEvent.mouseEnter(pill);

      await waitFor(() => {
        const toonBtn = screen.getByTestId('export-btn-toon');
        fireEvent.click(toonBtn);
      });

      expect(onExport).toHaveBeenCalledWith('toon');
    });

    it('buttons have correct labels', async () => {
      render(<ExportToolbar {...baseProps} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      fireEvent.mouseEnter(pill);

      await waitFor(() => {
        expect(screen.getByText(/pdf/i)).toBeInTheDocument();
        expect(screen.getByText(/docx/i)).toBeInTheDocument();
        expect(screen.getByText(/markdown/i)).toBeInTheDocument();
        expect(screen.getByText(/png/i)).toBeInTheDocument();
      });
    });

    it('buttons are positioned in radial layout', async () => {
      render(<ExportToolbar {...baseProps} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      fireEvent.mouseEnter(pill);

      await waitFor(() => {
        const buttons = screen.getAllByTestId(/export-btn-/);
        buttons.forEach((btn) => {
          expect(btn).toHaveClass('radial-position');
        });
      });
    });
  });

  // ========== LOADING STATE ==========
  describe('loading state', () => {
    it('shows loading spinner during export', async () => {
      const { rerender } = render(
        <ExportToolbar {...baseProps} isExporting={false} />
      );

      expect(screen.queryByTestId('export-spinner')).not.toBeInTheDocument();

      rerender(<ExportToolbar {...baseProps} isExporting={true} />);

      expect(screen.getByTestId('export-spinner')).toBeInTheDocument();
    });

    it('disables buttons during export', async () => {
      const { rerender } = render(
        <ExportToolbar {...baseProps} isExporting={false} />
      );

      const pill = screen.getByTestId('export-toolbar-pill');
      fireEvent.mouseEnter(pill);

      await waitFor(() => {
        expect(screen.getByTestId('export-btn-pdf')).not.toHaveAttribute('disabled');
      });

      rerender(<ExportToolbar {...baseProps} isExporting={true} />);

      const pdfBtn = screen.getByTestId('export-btn-pdf');
      expect(pdfBtn).toHaveAttribute('disabled');
    });

    it('shows loading text on pill during export', async () => {
      const { rerender } = render(
        <ExportToolbar {...baseProps} isExporting={false} />
      );

      rerender(<ExportToolbar {...baseProps} isExporting={true} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      expect(pill).toHaveTextContent(/exporting/i);
    });
  });

  // ========== SUCCESS TOAST ==========
  describe('success feedback', () => {
    it('shows success toast after export completes', async () => {
      const { rerender } = render(
        <ExportToolbar {...baseProps} isExporting={true} />
      );

      rerender(<ExportToolbar {...baseProps} isExporting={false} />);

      await waitFor(() => {
        const toast = screen.getByTestId('export-success-toast');
        expect(toast).toBeInTheDocument();
        expect(toast).toHaveTextContent(/export completed/i);
      });
    });

    it('auto-dismisses success toast after 3 seconds', async () => {
      vi.useFakeTimers();

      const { rerender } = render(
        <ExportToolbar {...baseProps} isExporting={true} />
      );

      rerender(<ExportToolbar {...baseProps} isExporting={false} />);

      await waitFor(() => {
        expect(screen.getByTestId('export-success-toast')).toBeInTheDocument();
      });

      vi.advanceTimersByTime(3000);

      await waitFor(() => {
        expect(screen.queryByTestId('export-success-toast')).not.toBeInTheDocument();
      });

      vi.useRealTimers();
    });

    it('shows error toast on export failure', async () => {
      const { rerender } = render(
        <ExportToolbar {...baseProps} isExporting={true} error={undefined} />
      );

      rerender(
        <ExportToolbar {...baseProps} isExporting={false} error="Export failed: File too large" />
      );

      await waitFor(() => {
        const errorToast = screen.getByTestId('export-error-toast');
        expect(errorToast).toBeInTheDocument();
        expect(errorToast).toHaveTextContent('Export failed');
      });
    });
  });

  // ========== INTERACTIONS ==========
  describe('interactions', () => {
    it('calls onExport with correct format', async () => {
      const onExport = vi.fn();
      render(<ExportToolbar {...baseProps} onExport={onExport} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      fireEvent.mouseEnter(pill);

      await waitFor(() => {
        const pdfBtn = screen.getByTestId('export-btn-pdf');
        fireEvent.click(pdfBtn);
      });

      expect(onExport).toHaveBeenCalledTimes(1);
      expect(onExport).toHaveBeenCalledWith('pdf');
    });

    it('collapses menu after export click', async () => {
      const onExport = vi.fn();
      render(<ExportToolbar {...baseProps} onExport={onExport} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      fireEvent.mouseEnter(pill);

      await waitFor(() => {
        expect(screen.getByTestId('export-buttons-radial')).toBeInTheDocument();
      });

      const pdfBtn = screen.getByTestId('export-btn-pdf');
      fireEvent.click(pdfBtn);

      await waitFor(() => {
        expect(screen.queryByTestId('export-buttons-radial')).not.toBeInTheDocument();
      });
    });
  });

  // ========== ACCESSIBILITY ==========
  describe('accessibility', () => {
    it('has no axe violations', async () => {
      const { container } = render(<ExportToolbar {...baseProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('pill button has aria-label', () => {
      render(<ExportToolbar {...baseProps} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      expect(pill).toHaveAttribute('aria-label', expect.stringContaining('export'));
    });

    it('export buttons have descriptive aria-labels', async () => {
      render(<ExportToolbar {...baseProps} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      fireEvent.mouseEnter(pill);

      await waitFor(() => {
        const pdfBtn = screen.getByTestId('export-btn-pdf');
        expect(pdfBtn).toHaveAttribute('aria-label', expect.stringContaining('PDF'));
      });
    });

    it('spinner has aria-live region', async () => {
      const { rerender } = render(
        <ExportToolbar {...baseProps} isExporting={false} />
      );

      rerender(<ExportToolbar {...baseProps} isExporting={true} />);

      const spinner = screen.getByTestId('export-spinner');
      expect(spinner).toHaveAttribute('aria-live', 'polite');
    });
  });

  // ========== RESPONSIVE ==========
  describe('responsive behavior', () => {
    it('displays at desktop (1280px)', () => {
      window.innerWidth = 1280;
      render(<ExportToolbar {...baseProps} />);
      expect(screen.getByTestId('export-toolbar-pill')).toBeVisible();
    });

    it('displays at tablet (768px)', () => {
      window.innerWidth = 768;
      render(<ExportToolbar {...baseProps} />);
      expect(screen.getByTestId('export-toolbar-pill')).toBeVisible();
    });

    it('displays at mobile (<500px)', () => {
      window.innerWidth = 375;
      render(<ExportToolbar {...baseProps} />);
      expect(screen.getByTestId('export-toolbar-pill')).toBeVisible();
    });

    it('adjusts position on mobile', () => {
      window.innerWidth = 375;
      render(<ExportToolbar {...baseProps} />);

      const pill = screen.getByTestId('export-toolbar-pill');
      expect(pill).toHaveClass('pill-mobile');
    });
  });
});
