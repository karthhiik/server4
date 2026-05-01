# Sandbox Display/Rendering Issues Design Document
**Date:** 2026-05-01
**Topic:** Fixing sandbox display and rendering issues for slide presentations

## Problem Statement
Based on user feedback, the sandbox implementation used for displaying presentations has several critical issues:
1. Slides are generating but not showing correctly in the sandbox
2. Sandbox implementation is problematic for displaying slides (considered the "worst implementation")
3. Images are not getting shown in slides
4. Slides are not correctly generating as per pitch deck designs, styles, and typography
5. The sandbox approach prevents proper slide editing and interaction

## Root Cause Analysis
After examining the codebase, the issues stem from:

1. **Complex iframe sandbox architecture**: The sandbox uses a separate origin (`http://localhost:5174`) with strict postMessage communication, which adds complexity and failure points.

2. **Multiple rendering layers**: 
   - Parent app renders slides via `useCompiledDeck` hook
   - Slides are sent to sandbox via `renderSlide` 
   - Sandbox renders them again via `PresentMode` or `SlideRuntime`
   - This double-rendering can cause synchronization issues

3. **Image handling complexity**: Images require special handling through the `useCompiledDeck` hook's WebSocket listeners for `slide_image_ready` events, which can fail or be delayed.

4. **Presentation mode complexity**: The sandbox's `PresentMode` has its own keyboard handlers and presentation logic that may conflict with parent app controls.

5. **Missing exit/navigation controls**: While the sandbox PresentMode has exit and navigation controls, they may not be properly triggered or visible in certain contexts.

## Proposed Solution
Instead of fixing the complex sandbox architecture, I propose replacing the sandbox-based presentation system with a simpler, more direct approach:

### Approach: Direct In-Page Presentation System
Remove the sandbox iframe complexity and render presentations directly in the parent application using the same slide components already used for preview.

#### Key Changes:
1. **Replace SandboxFrame with direct slide rendering**: Instead of sending slides to an iframe, render them directly in the SandboxPresentationViewer component
2. **Simplify presentation controls**: Use the existing PresentMode logic but render it directly in the DOM instead of in an iframe
3. **Maintain image patching**: Keep the WebSocket-based image updating system but apply it directly to the rendered slides
4. **Preserve editing capabilities**: Keep the ability to edit slides through the same mechanisms
5. **Remove sandbox complexity**: Eliminate the postMessage protocol, iframe management, and origin validation overhead

### Why This Approach:
- **Simpler architecture**: Removes iframe and postMessage complexity
- **Better performance**: Eliminates double-rendering and cross-origin communication overhead
- **More reliable**: Fewer failure points in the rendering pipeline
- **Easier debugging**: All rendering happens in the same context
- **Maintains functionality**: Keeps all existing features (image patching, editing, presentation controls)

## Detailed Design

### Component Changes

#### 1. SandboxPresentationViewer.tsx (Modified)
Instead of mounting a SandboxFrame and calling `enterPresent`, this component will:
- Render slides directly using the same SlideRuntime components used in preview
- Apply presentation styling and controls directly
- Handle keyboard navigation and presentation controls internally
- Still use useCompiledDeck for slide data and image updates

#### 2. Presentation Mode Logic
Extract the core presentation logic from PresentMode.tsx into a reusable hook or component that can be used both in the sandbox (for backward compatibility) and directly in the parent app.

#### 3. Image Handling
Keep the existing `patch` function in useCompiledDeck but apply it to directly rendered slides instead of sending through postMessage.

#### 4. Styling and Tokens
Apply design tokens directly to the rendered slides instead of passing them through to the sandbox.

### Data Flow
1. `useCompiledDeck` fetches slides and tokens from API
2. Slides are stored in state and passed directly to presentation renderer
3. Design tokens are applied to the container element
4. Image updates from WebSocket are applied directly to slide objects
5. Presentation controls (keyboard, buttons) manipulate slide index directly
6. Exit presentation simply hides the presentation viewer

### Error Handling
- Fallback to last known good state if API fails
- Clear error presentation when slides fail to load
- Graceful degradation when image patching fails

## Trade-offs Considered

### Alternative 1: Fix Existing Sandbox Architecture
**Pros:**
- Maintains isolation benefits of sandbox
- Less disruptive change
**Cons:**
- Still complex and prone to the same issues
- Requires significant debugging of postMessage timing
- Doesn't address fundamental complexity

### Alternative 2: Remove Sandbox Entirely, Use Preview Mode
**Pros:**
- Simplest possible solution
**Cons:**
- Doesn't provide true fullscreen presentation experience
- Lacks presentation-specific controls (black/white screen, etc.)
- May not match user expectations for "Present" button

### Alternative 3: Hybrid Approach (Recommended)
Use direct rendering for presentation but keep sandbox for preview where isolation is beneficial.

## Implementation Plan
1. Extract core presentation logic into reusable components/hooks
2. Modify SandboxPresentationViewer to render directly instead of using iframe
3. Ensure image patching works with direct rendering
4. Test presentation controls (navigation, exit, editing, blank screens)
5. Verify styling and token application works correctly
6. Remove or deprecate sandbox-specific presentation code over time

## Success Criteria
1. Slides display correctly in presentation mode with proper styling
2. Images load and display correctly in slides
3. Presentation controls work: next/previous slide, exit, black/white screen, edit
4. Slide editing functionality preserved
5. No regressions in slide preview functionality
6. Improved performance and reliability compared to sandbox approach

## Open Questions
1. Should we maintain the sandbox for preview mode while using direct rendering for presentation?
2. How should we handle the transition period where both systems might coexist?
3. What backup strategy should we use if direct rendering fails?

## References
- SandboxFrame.tsx - Current sandbox implementation
- SandboxPresentationViewer.tsx - Current presentation viewer
- PresentMode.tsx - Sandbox presentation mode
- useCompiledDeck.ts - Slide data and image patching hook
- PitchDeckCanvas.tsx - Main slide rendering component