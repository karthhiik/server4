# SWOT Task 2: TOWS Actions - Integration Guide

## Quick Start

### 1. Import the Component

```tsx
import { TOWSActions } from '@/features/intelligence/swot';
```

### 2. Prepare Your Data

```tsx
import type { SWOTData, Action } from '@/features/intelligence/canvas/types/swot';

const swotData: SWOTData = {
  id: 'swot-1',
  title: 'Market Analysis 2026',
  strengths: [
    {
      id: 's1',
      quadrant: 'strengths',
      text: 'Strong brand recognition',
      description: 'Well-established market presence',
      importance: 8,
      tags: ['brand', 'market'],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ],
  weaknesses: [
    {
      id: 'w1',
      quadrant: 'weaknesses',
      text: 'Limited market reach',
      description: 'Geographic constraints',
      importance: 6,
      tags: ['distribution', 'geography'],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ],
  opportunities: [
    {
      id: 'o1',
      quadrant: 'opportunities',
      text: 'Emerging market demand',
      description: 'New customer segments',
      importance: 7,
      tags: ['growth', 'market'],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ],
  threats: [
    {
      id: 't1',
      quadrant: 'threats',
      text: 'Intense competition',
      description: 'New competitors entering',
      importance: 8,
      tags: ['competition', 'market'],
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ],
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
};

const actions: Action[] = [
  {
    id: 'a1',
    title: 'Expand distribution network',
    description: 'Reach more customers in new regions',
    towsType: 'SO', // Strength + Opportunity
    priority: 'P1',
    owner: 'John Doe',
    dueDate: '2026-06-30',
    status: 'in_progress',
    sourceItems: ['s1', 'o1'],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 'a2',
    title: 'Develop competitive advantage',
    description: 'Address weaknesses to compete better',
    towsType: 'WO', // Weakness + Opportunity
    priority: 'P2',
    owner: 'Jane Smith',
    dueDate: '2026-07-31',
    status: 'not_started',
    sourceItems: ['w1', 'o1'],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 'a3',
    title: 'Defend against competition',
    description: 'Leverage strengths against threats',
    towsType: 'ST', // Strength + Threat
    priority: 'P1',
    owner: 'John Doe',
    dueDate: '2026-05-15',
    status: 'blocked',
    sourceItems: ['s1', 't1'],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  {
    id: 'a4',
    title: 'Crisis management plan',
    description: 'Mitigate risks and weaknesses',
    towsType: 'WT', // Weakness + Threat
    priority: 'P1',
    owner: 'Manager',
    dueDate: '2026-04-30',
    status: 'in_progress',
    sourceItems: ['w1', 't1'],
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
];
```

### 3. Handle Callbacks

```tsx
const handleActionUpdate = async (action: Action) => {
  try {
    // Call your API to update the action
    const response = await fetch(`/api/actions/${action.id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(action),
    });

    if (!response.ok) throw new Error('Failed to update action');

    console.log('Action updated:', action);
    // Optionally refresh data or show success toast
  } catch (error) {
    console.error('Error updating action:', error);
    // Show error toast or message
  }
};

const handleActionDelete = async (actionId: string) => {
  try {
    // Call your API to delete the action
    const response = await fetch(`/api/actions/${actionId}`, {
      method: 'DELETE',
    });

    if (!response.ok) throw new Error('Failed to delete action');

    console.log('Action deleted:', actionId);
    // Optionally refresh data or show success toast
  } catch (error) {
    console.error('Error deleting action:', error);
    // Show error toast or message
  }
};

const handleActionCreate = async (newAction: Omit<Action, 'id'>) => {
  try {
    // Call your API to create the action
    const response = await fetch('/api/actions', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(newAction),
    });

    if (!response.ok) throw new Error('Failed to create action');

    const createdAction = await response.json();
    console.log('Action created:', createdAction);
    // Optionally refresh data or show success toast
  } catch (error) {
    console.error('Error creating action:', error);
    // Show error toast or message
  }
};
```

### 4. Render the Component

```tsx
export function MyTOWSPage() {
  return (
    <div className="w-full h-screen">
      <TOWSActions
        swotData={swotData}
        actions={actions}
        onActionUpdate={handleActionUpdate}
        onActionDelete={handleActionDelete}
        onActionCreate={handleActionCreate}
      />
    </div>
  );
}
```

---

## Component Props

```tsx
interface TOWSActionsProps {
  /**
   * SWOT analysis data containing strengths, weaknesses, opportunities, and threats
   * @required
   */
  swotData: SWOTData;

  /**
   * Array of TOWS actions to display
   * @required
   */
  actions: Action[];

  /**
   * Callback when an action is updated (edit fields)
   * @param action - Updated action object
   * @optional
   */
  onActionUpdate?: (action: Action) => void | Promise<void>;

  /**
   * Callback when an action is deleted
   * @param actionId - ID of deleted action
   * @optional
   */
  onActionDelete?: (actionId: string) => void | Promise<void>;

  /**
   * Callback when a new action is created
   * @param action - New action data (without ID)
   * @optional
   */
  onActionCreate?: (action: Omit<Action, 'id'>) => void | Promise<void>;
}
```

---

## Component Features

### Node Types & Colors

| Node Type | Color | Emoji | Purpose |
|-----------|-------|-------|---------|
| Strength | Emerald (#10b981) | 💪 | Internal positive factors |
| Weakness | Rose (#f43f5e) | ⚠️ | Internal negative factors |
| Opportunity | Blue (#3b82f6) | 🎯 | External positive factors |
| Threat | Amber (#f59e0b) | 🚨 | External negative factors |

### TOWS Action Types & Edge Colors

| Action Type | Color | Meaning |
|------------|-------|---------|
| SO | Emerald (#10b981) | Use Strengths to pursue Opportunities |
| WO | Blue (#3b82f6) | Overcome Weaknesses by pursuing Opportunities |
| ST | Amber (#f59e0b) | Use Strengths to manage Threats |
| WT | Rose (#f43f5e) | Mitigate Weaknesses and Threats |

### Action Node Fields

```tsx
// Editable fields in ActionNode
- title: string              // Action description
- priority: 'P1' | 'P2' | 'P3'  // P1=Critical, P2=High, P3=Medium
- owner: string?             // Assigned person
- dueDate: string?           // ISO date string
- status: ActionStatus       // not_started, in_progress, completed, blocked
```

### Status Colors

```
- not_started: Gray (#6b7280)
- in_progress: Blue (#3b82f6)
- completed: Green (#10b981)
- blocked: Red (#ef4444)
```

---

## Keyboard Navigation

| Key | Action |
|-----|--------|
| `Tab` | Move between interactive elements |
| `Enter` | Activate button / Edit action field |
| `Escape` | Close modal / Cancel editing |
| `Space` | Activate button / Check/uncheck |

---

## Accessibility Features

✅ **WCAG 2.1 AA Compliant**

- Semantic HTML (article, region, list roles)
- ARIA labels and descriptions
- Keyboard navigation support
- Focus indicators (3px blue outline)
- Color contrast ratios > 4.5:1
- Screen reader announcements
- Reduced motion support
- High contrast mode support

---

## Styling & Customization

### CSS Classes

The component uses CSS classes that can be customized:

```css
/* Container */
.tows-actions-container { }

/* Nodes */
.swot-node { }
.strength-node { }
.weakness-node { }
.opportunity-node { }
.threat-node { }
.action-node { }

/* Panels */
.tows-header-panel { }
.legend-panel { }
.status-panel { }
.new-action-panel { }

/* Buttons */
.btn { }
.btn-new-action { }
.btn-edit { }
.btn-delete { }
.btn-save { }
.btn-cancel { }

/* Fields */
.action-field { }
.field-input { }
.field-label { }
.field-value { }
```

### Dark Theme

The component uses a dark theme by default:

```css
Background: rgb(2, 10, 25)
Text: #f1f5f9
Secondary: #cbd5e1
Border: rgba(226, 232, 240, 0.1)
```

To override, target the `.tows-actions-container` and use CSS custom properties:

```css
.tows-actions-container {
  --primary: #3b82f6;
  --success: #10b981;
  --warning: #f59e0b;
  --danger: #ef4444;
  --dark: #1e293b;
  --light: #f1f5f9;
}
```

---

## Testing the Component

### Unit Tests

```bash
# Run all TOWS tests
npm test src/features/intelligence/swot/views/__tests__/test_swot_tows_actions.tsx

# Run specific test suite
npm test src/features/intelligence/swot/views/__tests__/test_swot_tows_actions.tsx -t "Rendering"

# Run with coverage
npm test -- --coverage src/features/intelligence/swot
```

### E2E Testing

Example with Playwright:

```ts
import { test, expect } from '@playwright/test';

test('TOWS Actions flow', async ({ page }) => {
  // Navigate to page with TOWSActions
  await page.goto('/intelligence/tows');

  // Check nodes are rendered
  const flowContainer = await page.locator('[role="region"]').first();
  await expect(flowContainer).toBeVisible();

  // Click edit button on action
  await page.click('button:has-text("Edit")');

  // Fill new owner
  await page.fill('input[aria-label="Action owner"]', 'Jane Doe');

  // Save changes
  await page.click('button:has-text("Save")');

  // Verify update callback was called
  // (depends on your implementation)
});
```

---

## Performance Tips

1. **Memoize Callbacks**: Use `useCallback` for handlers
   ```tsx
   const handleUpdate = useCallback((action: Action) => {
     // ... update logic
   }, []);
   ```

2. **Virtualize Long Lists**: For 100+ actions, consider react-window

3. **Lazy Load**: Load actions on demand
   ```tsx
   const [actions, setActions] = useState<Action[]>([]);

   useEffect(() => {
     fetchActions().then(setActions);
   }, []);
   ```

4. **Debounce Updates**: Avoid excessive API calls
   ```tsx
   const debouncedUpdate = useMemo(
     () => debounce(handleActionUpdate, 500),
     []
   );
   ```

---

## Troubleshooting

### Component Not Rendering

```tsx
// Check SWOT data is provided
if (!swotData) return <div>Loading SWOT data...</div>;

// Check React Flow is properly imported
import { ReactFlow } from '@xyflow/react';
import '@xyflow/react/dist/style.css';
```

### Edges Not Showing

```tsx
// Ensure sourceItems match SWOT item IDs
const action: Action = {
  sourceItems: ['s1', 'o1'], // Must match swotData item IDs
  // ...
};
```

### Focus Issues

```tsx
// If focus is lost, check container has proper tabindex
<div className="tows-actions-container" tabIndex={-1}>
  <TOWSActions {...props} />
</div>
```

### Styling Not Applied

```tsx
// Ensure CSS is imported in component
import '../styles/swot-nodes.css';
import '../styles/tows-actions.css';

// Or in your main app file
import '@/features/intelligence/swot/styles/swot-nodes.css';
import '@/features/intelligence/swot/styles/tows-actions.css';
```

---

## API Integration Example

### Fetch Actions from Backend

```tsx
async function loadTOWSActions(swotId: string): Promise<Action[]> {
  const response = await fetch(`/api/swot/${swotId}/actions`);
  if (!response.ok) throw new Error('Failed to load actions');
  return response.json();
}

// In component
const [actions, setActions] = useState<Action[]>([]);

useEffect(() => {
  loadTOWSActions(swotData.id)
    .then(setActions)
    .catch(console.error);
}, [swotData.id]);
```

### Update Action on Backend

```tsx
const handleActionUpdate = async (action: Action) => {
  const response = await fetch(
    `/api/swot/${swotData.id}/actions/${action.id}`,
    {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(action),
    }
  );

  if (!response.ok) throw new Error('Update failed');

  // Update local state
  setActions(actions.map(a => a.id === action.id ? action : a));
};
```

---

## Related Components

### Other SWOT Views

```tsx
import { QuadrantMatrix } from '@/features/intelligence/swot';
import { RiskRadar } from '@/features/intelligence/swot';
```

### Canvas Types

```tsx
import type {
  SWOTData,
  SWOTItem,
  Action,
  TOWSType,
  ActionPriority,
  ActionStatus,
} from '@/features/intelligence/canvas/types/swot';
```

---

## Support & Documentation

- **Component Docs**: JSDoc comments in source files
- **Type Definitions**: `canvas/types/swot.ts`
- **Test Examples**: `views/__tests__/test_swot_tows_actions.tsx`
- **CSS Variables**: `styles/swot-nodes.css` and `styles/tows-actions.css`

---

## Version Information

- **Component Version**: 1.0.0
- **React Flow**: 11.11.4 / 12.8.2
- **Framer Motion**: 12.6.5
- **React**: 18.3.1
- **TypeScript**: 5.5.3

**Created**: 2026-04-02
**Status**: Production Ready ✅
