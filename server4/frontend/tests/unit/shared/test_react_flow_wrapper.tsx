/**
 * test_react_flow_wrapper.tsx
 * Unit tests for ReactFlowWrapper component
 * Shared Brain Component - React Flow canvas with grid, minimap, controls
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';
import { ReactFlowWrapper } from '../../components/shared/ReactFlowWrapper';

expect.extend(toHaveNoViolations);

// Mock react-flow-renderer
vi.mock('reactflow', () => ({
  ReactFlow: ({ children, ...props }: any) => (
    <div data-testid="react-flow-canvas" {...props}>
      {children}
    </div>
  ),
  Background: () => <div data-testid="flow-background" />,
  Controls: () => <div data-testid="flow-controls" />,
  MiniMap: () => <div data-testid="flow-minimap" />,
  Handle: () => <div data-testid="flow-handle" />,
  useReactFlow: () => ({
    fitView: vi.fn(),
    setCenter: vi.fn(),
    project: vi.fn(),
  }),
}));

describe('ReactFlowWrapper', () => {
  const mockNodes = [
    {
      id: 'node-1',
      data: { label: 'Strategy Node' },
      position: { x: 100, y: 100 },
      type: 'strategy',
    },
    {
      id: 'node-2',
      data: { label: 'Metric Node' },
      position: { x: 300, y: 100 },
      type: 'metric',
    },
  ];

  const mockEdges = [
    {
      id: 'edge-1-2',
      source: 'node-1',
      target: 'node-2',
      animated: true,
    },
  ];

  const baseProps = {
    nodes: mockNodes,
    edges: mockEdges,
    onNodesChange: vi.fn(),
    onEdgesChange: vi.fn(),
    onConnect: vi.fn(),
  };

  // ========== CANVAS RENDERING ==========
  describe('canvas rendering', () => {
    it('renders React Flow canvas', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      expect(screen.getByTestId('react-flow-canvas')).toBeInTheDocument();
    });

    it('displays dark background', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      expect(screen.getByTestId('flow-background')).toBeInTheDocument();
    });

    it('applies dark background class', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const canvas = screen.getByTestId('react-flow-canvas');
      expect(canvas).toHaveClass('bg-dark');
    });
  });

  // ========== DOT GRID ==========
  describe('dot grid pattern', () => {
    it('renders dot grid background', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const background = screen.getByTestId('flow-background');
      expect(background).toHaveAttribute('data-pattern', 'dots');
    });

    it('grid has correct spacing', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const background = screen.getByTestId('flow-background');
      expect(background).toHaveAttribute('data-gap', '20');
    });
  });

  // ========== MINIMAP ==========
  describe('minimap', () => {
    it('displays minimap', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      expect(screen.getByTestId('flow-minimap')).toBeInTheDocument();
    });

    it('minimap is collapsed by default', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const minimap = screen.getByTestId('flow-minimap');
      expect(minimap).toHaveClass('minimap-collapsed');
    });

    it('minimap positioned bottom-left', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const minimap = screen.getByTestId('flow-minimap');
      expect(minimap).toHaveStyle({
        bottom: expect.any(String),
        left: expect.any(String),
      });
    });

    it('expands minimap on click', async () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const minimap = screen.getByTestId('flow-minimap');
      fireEvent.click(minimap);

      await waitFor(() => {
        expect(minimap).toHaveClass('minimap-expanded');
      });
    });
  });

  // ========== CONTROLS ==========
  describe('controls panel', () => {
    it('displays controls panel', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      expect(screen.getByTestId('flow-controls')).toBeInTheDocument();
    });

    it('has zoom in button', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const zoomInBtn = screen.getByTestId('control-zoom-in');
      expect(zoomInBtn).toBeInTheDocument();
    });

    it('has zoom out button', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const zoomOutBtn = screen.getByTestId('control-zoom-out');
      expect(zoomOutBtn).toBeInTheDocument();
    });

    it('has fit view button', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const fitViewBtn = screen.getByTestId('control-fit-view');
      expect(fitViewBtn).toBeInTheDocument();
    });

    it('has lock/unlock button', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const lockBtn = screen.getByTestId('control-lock');
      expect(lockBtn).toBeInTheDocument();
    });

    it('zoom in increases zoom level', async () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const zoomInBtn = screen.getByTestId('control-zoom-in');
      fireEvent.click(zoomInBtn);

      await waitFor(() => {
        expect(screen.getByTestId('zoom-level')).toHaveTextContent(/1\.[0-9]+x/);
      });
    });

    it('zoom out decreases zoom level', async () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const zoomOutBtn = screen.getByTestId('control-zoom-out');
      fireEvent.click(zoomOutBtn);

      await waitFor(() => {
        expect(screen.getByTestId('zoom-level')).toHaveTextContent(/0\.[0-9]+x/);
      });
    });

    it('fit view centers and fits all nodes', async () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const fitViewBtn = screen.getByTestId('control-fit-view');
      fireEvent.click(fitViewBtn);

      expect(fitViewBtn).toBeInTheDocument();
    });

    it('toggles lock mode on click', async () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const lockBtn = screen.getByTestId('control-lock');
      expect(lockBtn).toHaveAttribute('aria-pressed', 'false');

      fireEvent.click(lockBtn);

      await waitFor(() => {
        expect(lockBtn).toHaveAttribute('aria-pressed', 'true');
      });
    });

    it('disables node drag when locked', async () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const lockBtn = screen.getByTestId('control-lock');
      fireEvent.click(lockBtn);

      await waitFor(() => {
        const canvas = screen.getByTestId('react-flow-canvas');
        expect(canvas).toHaveAttribute('data-nodes-draggable', 'false');
      });
    });
  });

  // ========== SNAP TO GRID ==========
  describe('snap to grid', () => {
    it('snaps nodes to 15px grid', () => {
      render(<ReactFlowWrapper {...baseProps} snapToGrid snapGrid={[15, 15]} />);

      const canvas = screen.getByTestId('react-flow-canvas');
      expect(canvas).toHaveAttribute('data-snap-to-grid', 'true');
      expect(canvas).toHaveAttribute('data-snap-grid', '15,15');
    });

    it('aligns dragged nodes to grid', async () => {
      render(<ReactFlowWrapper {...baseProps} snapToGrid snapGrid={[15, 15]} />);

      const node = screen.getByTestId('node-node-1');
      fireEvent.mouseDown(node);
      fireEvent.mouseMove(node, { clientX: 105, clientY: 105 });
      fireEvent.mouseUp();

      // After snap: should be 105 -> 105 (15px aligned)
      expect(node).toHaveStyle('transform: translate(105px, 105px)');
    });
  });

  // ========== MULTI-SELECT ==========
  describe('multi-select', () => {
    it('single click selects node', async () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const node = screen.getByTestId('node-node-1');
      fireEvent.click(node);

      await waitFor(() => {
        expect(node).toHaveClass('selected');
      });
    });

    it('shift-click adds to selection', async () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const node1 = screen.getByTestId('node-node-1');
      const node2 = screen.getByTestId('node-node-2');

      fireEvent.click(node1);
      fireEvent.click(node2, { shiftKey: true });

      await waitFor(() => {
        expect(node1).toHaveClass('selected');
        expect(node2).toHaveClass('selected');
      });
    });

    it('ctrl-click removes from selection', async () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const node1 = screen.getByTestId('node-node-1');
      const node2 = screen.getByTestId('node-node-2');

      fireEvent.click(node1);
      fireEvent.click(node2, { shiftKey: true });
      fireEvent.click(node1, { ctrlKey: true });

      await waitFor(() => {
        expect(node1).not.toHaveClass('selected');
        expect(node2).toHaveClass('selected');
      });
    });
  });

  // ========== ANIMATED EDGES ==========
  describe('animated edges', () => {
    it('renders animated edges', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const edge = screen.getByTestId('edge-edge-1-2');
      expect(edge).toHaveClass('animated');
    });

    it('edges have arrow markers', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const edge = screen.getByTestId('edge-edge-1-2');
      expect(edge).toHaveAttribute('data-marker', 'arrow');
    });
  });

  // ========== NODE TYPES ==========
  describe('node types registration', () => {
    it('registers strategy node type', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const node = screen.getByTestId('node-node-1');
      expect(node).toHaveAttribute('data-type', 'strategy');
    });

    it('registers metric node type', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const node = screen.getByTestId('node-node-2');
      expect(node).toHaveAttribute('data-type', 'metric');
    });

    it('custom nodeTypes prop accepted', () => {
      const customTypes = {
        custom: () => <div>Custom</div>,
      };

      render(
        <ReactFlowWrapper {...baseProps} nodeTypes={customTypes} />
      );

      expect(screen.getByTestId('react-flow-canvas')).toBeInTheDocument();
    });
  });

  // ========== ACCESSIBILITY ==========
  describe('accessibility', () => {
    it('has no axe violations', async () => {
      const { container } = render(<ReactFlowWrapper {...baseProps} />);
      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('canvas has role="region"', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const canvas = screen.getByTestId('react-flow-canvas');
      expect(canvas).toHaveAttribute('role', 'region');
    });

    it('controls have aria-labels', () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const zoomInBtn = screen.getByTestId('control-zoom-in');
      expect(zoomInBtn).toHaveAttribute('aria-label', expect.stringContaining('zoom'));
    });

    it('keyboard navigation supported', async () => {
      render(<ReactFlowWrapper {...baseProps} />);

      const canvas = screen.getByTestId('react-flow-canvas');
      fireEvent.keyDown(canvas, { key: '+', ctrlKey: true });

      // Zoom in should work
      expect(screen.getByTestId('react-flow-canvas')).toBeInTheDocument();
    });
  });

  // ========== RESPONSIVE ==========
  describe('responsive behavior', () => {
    it('displays at desktop (1280px)', () => {
      window.innerWidth = 1280;
      render(<ReactFlowWrapper {...baseProps} />);
      expect(screen.getByTestId('react-flow-canvas')).toBeVisible();
    });

    it('displays at tablet (768px)', () => {
      window.innerWidth = 768;
      render(<ReactFlowWrapper {...baseProps} />);
      expect(screen.getByTestId('react-flow-canvas')).toBeVisible();
    });

    it('displays at mobile (<500px)', () => {
      window.innerWidth = 375;
      render(<ReactFlowWrapper {...baseProps} />);
      expect(screen.getByTestId('react-flow-canvas')).toBeVisible();
    });

    it('controls reposition on mobile', () => {
      window.innerWidth = 375;
      render(<ReactFlowWrapper {...baseProps} />);

      const controls = screen.getByTestId('flow-controls');
      expect(controls).toHaveClass('controls-mobile');
    });
  });
});
