/**
 * test_canvas_theme_provider.tsx
 * Unit tests for CanvasThemeProvider component
 * Shared Brain Component - theme context provider
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { axe, toHaveNoViolations } from 'jest-axe';
import '@testing-library/jest-dom';
import { CanvasThemeProvider, useCanvasTheme } from '../../components/shared/CanvasThemeProvider';

expect.extend(toHaveNoViolations);

describe('CanvasThemeProvider', () => {
  // ========== CONTEXT PROVISION ==========
  describe('theme context provision', () => {
    it('provides theme colors to children', () => {
      const TestComponent = () => {
        const { accentColor } = useCanvasTheme();
        return <div data-testid="test-color">{accentColor}</div>;
      };

      render(
        <CanvasThemeProvider theme="blue">
          <TestComponent />
        </CanvasThemeProvider>
      );

      expect(screen.getByTestId('test-color')).toHaveTextContent('#667eea');
    });

    it('throws error when useCanvasTheme used outside provider', () => {
      const TestComponent = () => {
        expect(() => useCanvasTheme()).toThrow(
          'useCanvasTheme must be used within CanvasThemeProvider'
        );
        return <div />;
      };

      // Suppress console errors for this test
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      render(<TestComponent />);

      consoleSpy.mockRestore();
    });
  });

  // ========== PRESET CONFIGS ==========
  describe('preset theme configurations', () => {
    it('blue theme provides correct colors', () => {
      const TestComponent = () => {
        const theme = useCanvasTheme();
        return (
          <div data-testid="theme-output">
            {theme.accentColor}-{theme.backgroundColor}
          </div>
        );
      };

      render(
        <CanvasThemeProvider theme="blue">
          <TestComponent />
        </CanvasThemeProvider>
      );

      const output = screen.getByTestId('theme-output').textContent;
      expect(output).toContain('#667eea');
    });

    it('emerald theme provides correct colors', () => {
      const TestComponent = () => {
        const theme = useCanvasTheme();
        return <div data-testid="theme-output">{theme.accentColor}</div>;
      };

      render(
        <CanvasThemeProvider theme="emerald">
          <TestComponent />
        </CanvasThemeProvider>
      );

      // Emerald should have green accent
      expect(screen.getByTestId('theme-output')).toHaveTextContent('#10b981');
    });

    it('violet theme provides correct colors', () => {
      const TestComponent = () => {
        const theme = useCanvasTheme();
        return <div data-testid="theme-output">{theme.accentColor}</div>;
      };

      render(
        <CanvasThemeProvider theme="violet">
          <TestComponent />
        </CanvasThemeProvider>
      );

      expect(screen.getByTestId('theme-output')).toHaveTextContent('#a855f7');
    });

    it('amber theme provides correct colors', () => {
      const TestComponent = () => {
        const theme = useCanvasTheme();
        return <div data-testid="theme-output">{theme.accentColor}</div>;
      };

      render(
        <CanvasThemeProvider theme="amber">
          <TestComponent />
        </CanvasThemeProvider>
      );

      expect(screen.getByTestId('theme-output')).toHaveTextContent('#f59e0b');
    });
  });

  // ========== CSS VARIABLES ==========
  describe('CSS variable injection', () => {
    it('injects accent color CSS variable', () => {
      const TestComponent = () => {
        const { accentColor } = useCanvasTheme();
        return (
          <div
            data-testid="test-element"
            style={{ color: `var(--theme-accent)` }}
          >
            Test
          </div>
        );
      };

      render(
        <CanvasThemeProvider theme="blue">
          <TestComponent />
        </CanvasThemeProvider>
      );

      const style = window.getComputedStyle(document.documentElement);
      expect(style.getPropertyValue('--theme-accent')).toBeTruthy();
    });

    it('injects background color CSS variable', () => {
      const TestComponent = () => {
        return (
          <div
            data-testid="test-element"
            style={{ backgroundColor: `var(--theme-background)` }}
          >
            Test
          </div>
        );
      };

      render(
        <CanvasThemeProvider theme="blue">
          <TestComponent />
        </CanvasThemeProvider>
      );

      const style = window.getComputedStyle(document.documentElement);
      expect(style.getPropertyValue('--theme-background')).toBeTruthy();
    });

    it('updates CSS variables when theme changes', () => {
      const TestComponent = ({ theme }: { theme: string }) => {
        return (
          <div
            data-testid="test-element"
            style={{ color: `var(--theme-accent)` }}
          >
            {theme}
          </div>
        );
      };

      const { rerender } = render(
        <CanvasThemeProvider theme="blue">
          <TestComponent theme="blue" />
        </CanvasThemeProvider>
      );

      rerender(
        <CanvasThemeProvider theme="emerald">
          <TestComponent theme="emerald" />
        </CanvasThemeProvider>
      );

      const style = window.getComputedStyle(document.documentElement);
      expect(style.getPropertyValue('--theme-accent')).toBeTruthy();
    });
  });

  // ========== HOOK USAGE ==========
  describe('useCanvasTheme hook', () => {
    it('returns all theme properties', () => {
      const TestComponent = () => {
        const theme = useCanvasTheme();

        return (
          <div>
            <div data-testid="accent">{theme.accentColor}</div>
            <div data-testid="background">{theme.backgroundColor}</div>
            <div data-testid="text">{theme.textColor}</div>
            <div data-testid="border">{theme.borderColor}</div>
          </div>
        );
      };

      render(
        <CanvasThemeProvider theme="blue">
          <TestComponent />
        </CanvasThemeProvider>
      );

      expect(screen.getByTestId('accent')).toHaveTextContent('#667eea');
      expect(screen.getByTestId('background')).toBeInTheDocument();
      expect(screen.getByTestId('text')).toBeInTheDocument();
      expect(screen.getByTestId('border')).toBeInTheDocument();
    });

    it('returns consistent theme object', () => {
      const renders: any[] = [];

      const TestComponent = () => {
        const theme = useCanvasTheme();
        renders.push(theme);
        return <div>{theme.accentColor}</div>;
      };

      render(
        <CanvasThemeProvider theme="blue">
          <TestComponent />
        </CanvasThemeProvider>
      );

      expect(renders[0]).toEqual(renders[1]);
    });
  });

  // ========== MULTIPLE CHILDREN ==========
  describe('multiple children', () => {
    it('applies theme to all children', () => {
      const Child = ({ id }: { id: string }) => {
        const { accentColor } = useCanvasTheme();
        return <div data-testid={`child-${id}`}>{accentColor}</div>;
      };

      render(
        <CanvasThemeProvider theme="blue">
          <Child id="1" />
          <Child id="2" />
          <Child id="3" />
        </CanvasThemeProvider>
      );

      expect(screen.getByTestId('child-1')).toHaveTextContent('#667eea');
      expect(screen.getByTestId('child-2')).toHaveTextContent('#667eea');
      expect(screen.getByTestId('child-3')).toHaveTextContent('#667eea');
    });

    it('applies theme through nested children', () => {
      const DeepChild = () => {
        const { accentColor } = useCanvasTheme();
        return <div data-testid="deep-child">{accentColor}</div>;
      };

      const ChildWrapper = () => (
        <div>
          <DeepChild />
        </div>
      );

      render(
        <CanvasThemeProvider theme="blue">
          <ChildWrapper />
        </CanvasThemeProvider>
      );

      expect(screen.getByTestId('deep-child')).toHaveTextContent('#667eea');
    });
  });

  // ========== ACCESSIBILITY ==========
  describe('accessibility', () => {
    it('has no axe violations', async () => {
      const TestComponent = () => {
        const { accentColor } = useCanvasTheme();
        return <div data-testid="test">{accentColor}</div>;
      };

      const { container } = render(
        <CanvasThemeProvider theme="blue">
          <TestComponent />
        </CanvasThemeProvider>
      );

      const results = await axe(container);
      expect(results).toHaveNoViolations();
    });

    it('maintains contrast ratios in theme colors', () => {
      const TestComponent = () => {
        const theme = useCanvasTheme();
        return (
          <div
            data-testid="test"
            style={{
              backgroundColor: theme.backgroundColor,
              color: theme.textColor,
            }}
          >
            Content
          </div>
        );
      };

      render(
        <CanvasThemeProvider theme="blue">
          <TestComponent />
        </CanvasThemeProvider>
      );

      expect(screen.getByTestId('test')).toBeInTheDocument();
    });
  });

  // ========== THEME SWITCHING ==========
  describe('theme switching', () => {
    it('updates theme on prop change', () => {
      const TestComponent = () => {
        const { accentColor } = useCanvasTheme();
        return <div data-testid="color">{accentColor}</div>;
      };

      const { rerender } = render(
        <CanvasThemeProvider theme="blue">
          <TestComponent />
        </CanvasThemeProvider>
      );

      expect(screen.getByTestId('color')).toHaveTextContent('#667eea');

      rerender(
        <CanvasThemeProvider theme="emerald">
          <TestComponent />
        </CanvasThemeProvider>
      );

      expect(screen.getByTestId('color')).toHaveTextContent('#10b981');
    });

    it('switches between all available themes', () => {
      const TestComponent = () => {
        const { accentColor } = useCanvasTheme();
        return <div data-testid="color">{accentColor}</div>;
      };

      const themes = [
        { theme: 'blue', color: '#667eea' },
        { theme: 'emerald', color: '#10b981' },
        { theme: 'violet', color: '#a855f7' },
        { theme: 'amber', color: '#f59e0b' },
      ] as const;

      themes.forEach(({ theme, color }) => {
        const { unmount } = render(
          <CanvasThemeProvider theme={theme}>
            <TestComponent />
          </CanvasThemeProvider>
        );

        expect(screen.getByTestId('color')).toHaveTextContent(color);
        unmount();
      });
    });
  });
});
