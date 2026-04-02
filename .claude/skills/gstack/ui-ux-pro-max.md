---
name: /ui-ux-pro-max
description: UI/UX Pro Max — Design intelligence for building professional UI/UX with 67 styles, 161 color palettes, and industry-specific reasoning rules
---

## When to use
When user wants to build a landing page, dashboard, mobile app UI, or any UI/UX design task.

## How it works
1. Analyze user request for product type, industry, and requirements
2. Generate complete design system (pattern, style, colors, typography, effects)
3. Implement code with proper colors, fonts, spacing, and best practices
4. Validate against anti-patterns before delivery

## Usage
```
/ui-ux-pro-max Build a landing page for my SaaS product
/ui-ux-pro-max Create a dashboard for healthcare analytics
/ui-ux-pro-max Design a portfolio with dark mode
```

## Supported Stacks
- HTML + Tailwind (default)
- React, Next.js, shadcn/ui
- Vue, Nuxt.js, Nuxt UI
- Svelte, Astro
- SwiftUI, React Native, Flutter

## Design System Output
Generates complete design system including:
- **Pattern**: Landing page structure (Hero-Centric, Conversion-Optimized, etc.)
- **Style**: 67 available styles (Glassmorphism, Minimalism, Dark Mode, etc.)
- **Colors**: 161 industry-specific palettes
- **Typography**: 57 font pairings
- **Effects**: Animations, transitions, hover states
- **Anti-patterns**: What to avoid for this industry

## Pre-delivery Checklist
- [ ] No emojis as icons (use SVG: Heroicons/Lucide)
- [ ] cursor-pointer on clickable elements
- [ ] Hover states with smooth transitions (150-300ms)
- [ ] Light mode: text contrast 4.5:1 minimum
- [ ] Focus states for keyboard navigation
- [ ] prefers-reduced-motion respected
- [ ] Responsive: 375px, 768px, 1024px, 1440px