---
name: /design-review
description: Designer Who Codes — audit design quality, fix issues, atomic commits with before/after
---

## When to use
When user wants design quality audit and fixes on a feature or component.

## How it works
1. Examine the UI component or page
2. Rate each design dimension (0-10):
   - Visual hierarchy
   - Color usage
   - Typography
   - Spacing/whitespace
   - Accessibility
   - Responsiveness
   - Consistency
3. Identify AI slop patterns (generic AI-generated look)
4. Fix issues with atomic commits
5. Document before/after changes

## Usage
```
/design-review
```

## Design Audit Checklist

### Visual Hierarchy (0-10)
- Clear primary vs secondary actions
- Proper heading levels
- Visual weight on important elements

### Color Usage (0-10)
- Consistent palette
- Proper contrast ratios
- Meaningful semantic colors (success, error, warning)

### Typography (0-10)
- Readable fonts and sizes
- Proper line-height
- Consistent font weights

### Spacing (0-10)
- Consistent margins/padding
- Proper alignment
- Visual breathing room

### Accessibility (0-10)
- Keyboard navigation
- Screen reader support
- Focus indicators
- Color contrast AA+

### Responsiveness (0-10)
- Mobile-first approach
- Proper breakpoints
- No horizontal scroll

### Consistency (0-10)
- Same patterns across app
- Consistent button styles
- Consistent form inputs

### AI Slop Detection
- Generic gradients
- Overused shadows
- Unoriginal illustrations
- Mass-produced icon styles

## Output
For each issue found:
1. Describe the problem
2. Rate current vs target
3. Fix with atomic commit
4. Document the change