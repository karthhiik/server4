/**
 * test_version_history_drawer.tsx
 * Unit tests for VersionHistoryDrawer component
 * Shared Brain Component - timeline of versions with diff view
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';
import { VersionHistoryDrawer } from '../../components/shared/VersionHistoryDrawer';

expect.extend(toHaveNoViolations);

describe('VersionHistoryDrawer', () => {
  const mockVersions = [
    {
      id: 'v1',
      timestamp: '2024-01-20 14:30:00',
      author: 'John Doe',
      authorIcon: '👤',
      changeType: 'created',
      changes: 'Initial version',
      content: 'Original executive summary content',
    },
    {
      id: 'v2',
      timestamp: '2024-01-20 15:45:00',
      author: 'Jane Smith',
      authorIcon: '👩',
      changeType: 'edited',
      changes: 'Updated market section',
      content: 'Original content + market updates',
    },
    {
      id: 'v3',
      timestamp: '2024-01-20 16:20:00',
      author: 'John Doe',
      authorIcon: '👤',
      changeType: 'regenerated',
      changes: 'AI regeneration',
      content: 'Completely new AI-generated version',
    },
  ];

  const baseProps = {
    isOpen: false,
    versions: mockVersions,
    currentVersion: mockVersions[2],
    onClose: vi.fn(),
    onRestore: vi.fn(),
  };

  // ========== VISIBILITY ==========
  describe('visibility', () => {
    it('hides drawer when isOpen=false', () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={false} />);

      const drawer = screen.queryByTestId('version-history-drawer');
      expect(drawer).not.toBeVisible();
    });

    it('shows drawer when isOpen=true', () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      const drawer = screen.getByTestId('version-history-drawer');
      expect(drawer).toBeVisible();
    });
  });

  // ========== ANIMATION ==========
  describe('slide-in animation', () => {
    it('applies slide-in animation on open', () => {
      const { rerender } = render(<VersionHistoryDrawer {...baseProps} isOpen={false} />);

      rerender(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      const drawer = screen.getByTestId('version-history-drawer');
      expect(drawer).toHaveClass('slide-in-animation');
    });
  });

  // ========== TIMELINE LIST ==========
  describe('timeline list rendering', () => {
    it('displays all versions in timeline', () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      expect(screen.getByTestId('timeline-item-v1')).toBeInTheDocument();
      expect(screen.getByTestId('timeline-item-v2')).toBeInTheDocument();
      expect(screen.getByTestId('timeline-item-v3')).toBeInTheDocument();
    });

    it('displays version timestamps', () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      expect(screen.getByText('2024-01-20 14:30:00')).toBeInTheDocument();
      expect(screen.getByText('2024-01-20 15:45:00')).toBeInTheDocument();
    });

    it('displays author icons', () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      const icons = screen.getAllByTestId('author-icon');
      expect(icons.length).toBeGreaterThan(0);
    });

    it('displays change type badges', () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      expect(screen.getByTestId('change-badge-created')).toBeInTheDocument();
      expect(screen.getByTestId('change-badge-edited')).toBeInTheDocument();
      expect(screen.getByTestId('change-badge-regenerated')).toBeInTheDocument();
    });

    it('highlights current version', () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      const currentItem = screen.getByTestId('timeline-item-v3');
      expect(currentItem).toHaveClass('current-version');
    });
  });

  // ========== VERSION SELECTION ==========
  describe('version selection', () => {
    it('selects version on click', async () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      const versionItem = screen.getByTestId('timeline-item-v1');
      fireEvent.click(versionItem);

      await waitFor(() => {
        expect(versionItem).toHaveClass('selected');
      });
    });

    it('shows preview of selected version', async () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      const versionItem = screen.getByTestId('timeline-item-v1');
      fireEvent.click(versionItem);

      await waitFor(() => {
        const preview = screen.getByTestId('version-preview');
        expect(preview).toHaveTextContent(mockVersions[0].content);
      });
    });

    it('updates preview when selection changes', async () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      let versionItem = screen.getByTestId('timeline-item-v1');
      fireEvent.click(versionItem);

      await waitFor(() => {
        const preview = screen.getByTestId('version-preview');
        expect(preview).toHaveTextContent(mockVersions[0].content);
      });

      versionItem = screen.getByTestId('timeline-item-v2');
      fireEvent.click(versionItem);

      await waitFor(() => {
        const preview = screen.getByTestId('version-preview');
        expect(preview).toHaveTextContent(mockVersions[1].content);
      });
    });
  });

  // ========== COMPARE VIEW ==========
  describe('compare button and diff view', () => {
    it('shows compare button on version selection', async () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      const versionItem = screen.getByTestId('timeline-item-v1');
      fireEvent.click(versionItem);

      await waitFor(() => {
        expect(screen.getByTestId('compare-button')).toBeInTheDocument();
      });
    });

    it('opens diff view on compare click', async () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      const versionItem = screen.getByTestId('timeline-item-v1');
      fireEvent.click(versionItem);

      await waitFor(() => {
        const compareBtn = screen.getByTestId('compare-button');
        fireEvent.click(compareBtn);
      });

      await waitFor(() => {
        expect(screen.getByTestId('diff-view')).toBeInTheDocument();
      });
    });

    it('shows additions in green in diff view', async () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      const versionItem = screen.getByTestId('timeline-item-v2');
      fireEvent.click(versionItem);

      await waitFor(() => {
        const compareBtn = screen.getByTestId('compare-button');
        fireEvent.click(compareBtn);
      });

      await waitFor(() => {
        const additions = screen.getByTestId('diff-additions');
        expect(additions).toHaveClass('diff-add');
        expect(additions).toHaveStyle('background-color: #90EE90');
      });
    });

    it('shows removals in red in diff view', async () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      const versionItem = screen.getByTestId('timeline-item-v2');
      fireEvent.click(versionItem);

      await waitFor(() => {
        const compareBtn = screen.getByTestId('compare-button');
        fireEvent.click(compareBtn);
      });

      await waitFor(() => {
        const removals = screen.getByTestId('diff-removals');
        expect(removals).toHaveClass('diff-remove');
        expect(removals).toHaveStyle('background-color: #FFB6C6');
      });
    });

    it('closes diff view on close button', async () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      const versionItem = screen.getByTestId('timeline-item-v1');
      fireEvent.click(versionItem);

      await waitFor(() => {
        const compareBtn = screen.getByTestId('compare-button');
        fireEvent.click(compareBtn);
      });

      await waitFor(() => {
        expect(screen.getByTestId('diff-view')).toBeInTheDocument();
      });

      const closeDiffBtn = screen.getByTestId('close-diff-button');
      fireEvent.click(closeDiffBtn);

      await waitFor(() => {
        expect(screen.queryByTestId('diff-view')).not.toBeInTheDocument();
      });
    });
  });

  // ========== RESTORE ==========
  describe('restore functionality', () => {
    it('shows restore button on version selection', async () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      const versionItem = screen.getByTestId('timeline-item-v1');
      fireEvent.click(versionItem);

      await waitFor(() => {
        expect(screen.getByTestId('restore-button')).toBeInTheDocument();
      });
    });

    it('hides restore button for current version', () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      // Current version is v3, so restore button should not show
      expect(screen.queryByTestId('restore-button')).not.toBeInTheDocument();
    });

    it('triggers onRestore callback with version id', async () => {
      const onRestore = vi.fn();
      render(
        <VersionHistoryDrawer {...baseProps} isOpen={true} onRestore={onRestore} />
      );

      const versionItem = screen.getByTestId('timeline-item-v1');
      fireEvent.click(versionItem);

      await waitFor(() => {
        const restoreBtn = screen.getByTestId('restore-button');
        fireEvent.click(restoreBtn);
      });

      expect(onRestore).toHaveBeenCalledWith('v1');
    });

    it('shows confirmation before restoring', async () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      const versionItem = screen.getByTestId('timeline-item-v1');
      fireEvent.click(versionItem);

      await waitFor(() => {
        const restoreBtn = screen.getByTestId('restore-button');
        fireEvent.click(restoreBtn);
      });

      await waitFor(() => {
        expect(screen.getByTestId('confirm-restore-dialog')).toBeInTheDocument();
        expect(screen.getByText(/are you sure/i)).toBeInTheDocument();
      });
    });

    it('cancels restore on cancel button', async () => {
      const onRestore = vi.fn();
      render(
        <VersionHistoryDrawer {...baseProps} isOpen={true} onRestore={onRestore} />
      );

      const versionItem = screen.getByTestId('timeline-item-v1');
      fireEvent.click(versionItem);

      await waitFor(() => {
        const restoreBtn = screen.getByTestId('restore-button');
        fireEvent.click(restoreBtn);
      });

      await waitFor(() => {
        const cancelBtn = screen.getByTestId('cancel-restore-button');
        fireEvent.click(cancelBtn);
      });

      expect(onRestore).not.toHaveBeenCalled();
    });

    it('confirms restore on confirm button', async () => {
      const onRestore = vi.fn();
      render(
        <VersionHistoryDrawer {...baseProps} isOpen={true} onRestore={onRestore} />
      );

      const versionItem = screen.getByTestId('timeline-item-v1');
      fireEvent.click(versionItem);

      await waitFor(() => {
        const restoreBtn = screen.getByTestId('restore-button');
        fireEvent.click(restoreBtn);
      });

      await waitFor(() => {
        const confirmBtn = screen.getByTestId('confirm-restore-button');
        fireEvent.click(confirmBtn);
      });

      expect(onRestore).toHaveBeenCalledWith('v1');
    });
  });

  // ========== CLOSE INTERACTIONS ==========
  describe('close interactions', () => {
    it('shows close button', () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      expect(screen.getByTestId('close-button')).toBeInTheDocument();
    });

    it('triggers onClose on close button click', async () => {
      const onClose = vi.fn();
      render(
        <VersionHistoryDrawer {...baseProps} isOpen={true} onClose={onClose} />
      );

      const closeBtn = screen.getByTestId('close-button');
      fireEvent.click(closeBtn);

      await waitFor(() => {
        expect(onClose).toHaveBeenCalledTimes(1);
      });
    });

    it('triggers onClose on Escape key', async () => {
      const onClose = vi.fn();
      render(
        <VersionHistoryDrawer {...baseProps} isOpen={true} onClose={onClose} />
      );

      fireEvent.keyDown(window, { key: 'Escape', code: 'Escape' });

      await waitFor(() => {
        expect(onClose).toHaveBeenCalledTimes(1);
      });
    });
  });

  // ========== ACCESSIBILITY ==========
  describe('accessibility', () => {
    it('has no axe violations', async () => {
      const { container } = render(
        <VersionHistoryDrawer {...baseProps} isOpen={true} />
      );
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('timeline has role="list"', () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      const timeline = screen.getByTestId('timeline-list');
      expect(timeline).toHaveAttribute('role', 'list');
    });

    it('timeline items have role="listitem"', () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      const item = screen.getByTestId('timeline-item-v1');
      expect(item).toHaveAttribute('role', 'listitem');
    });

    it('buttons have aria-labels', () => {
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);

      const closeBtn = screen.getByTestId('close-button');
      expect(closeBtn).toHaveAttribute('aria-label');
    });
  });

  // ========== RESPONSIVE ==========
  describe('responsive behavior', () => {
    it('displays at desktop (1280px)', () => {
      window.innerWidth = 1280;
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);
      expect(screen.getByTestId('version-history-drawer')).toBeVisible();
    });

    it('displays at tablet (768px)', () => {
      window.innerWidth = 768;
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);
      expect(screen.getByTestId('version-history-drawer')).toBeVisible();
    });

    it('displays fullscreen at mobile (<500px)', () => {
      window.innerWidth = 375;
      render(<VersionHistoryDrawer {...baseProps} isOpen={true} />);
      const drawer = screen.getByTestId('version-history-drawer');
      expect(drawer).toHaveClass('drawer-mobile-fullscreen');
    });
  });
});
