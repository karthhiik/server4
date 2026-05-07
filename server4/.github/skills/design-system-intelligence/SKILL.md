---
name: design-system-intelligence
description: "Handle all visual design decisions for presentations — themes, colors, typography, backgrounds, imagery, animations, layout grids, and spacing systems. Use when: generating or editing themes, selecting color palettes, pairing fonts, choosing backgrounds (solid/gradient/image/pattern), implementing design tokens, building brand DNA extraction, working on visual rhythm and grid systems, selecting or generating images for slides, or ensuring design consistency across a deck."
---

# Design System Intelligence

## Purpose
This skill covers all visual design decisions that make generated presentations look professionally designed rather than AI-generated. Design intelligence is what separates "a deck with content on slides" from "a presentation that commands attention." Every generated slide must look like a human designer made intentional choices.

## The Design Problem in AI Generation

Most AI-generated presentations fail visually because:
- Colors are arbitrarily assigned, not designed as a cohesive palette
- Typography is monotonous (one font, one size, no hierarchy)
- Backgrounds are either white or a random gradient
- Spacing is inconsistent — some slides are cramped, others are empty
- Images are generic stock photos with no relevance to the content
- There's no visual rhythm — every slide feels the same

This skill's job: make every design decision intentional and consistent.

## Theme Architecture

### Design Tokens (DTCG Format)
Every theme is defined as a set of design tokens that cascade through the entire deck:

```
Theme
├── colors
│   ├── primary (brand color, CTAs, emphasis)
│   ├── secondary (supporting accent)
│   ├── background (slide background base)
│   ├── surface (card/container backgrounds)
│   ├── text-primary (headlines, key text)
│   ├── text-secondary (body text, descriptions)
│   ├── text-muted (captions, footnotes)
│   └── accent (highlights, data points, icons)
├── typography
│   ├── font-display (headlines — expressive, distinctive)
│   ├── font-body (body text — readable, clean)
│   ├── scale (type scale ratio, e.g., 1.25 major third)
│   ├── heading-1 (size, weight, letter-spacing, line-height)
│   ├── heading-2
│   ├── body-large
│   ├── body
│   ├── caption
│   └── label
├── spacing
│   ├── base-unit (e.g., 0.125 inches)
│   ├── slide-margin (safe zone from edges)
│   ├── element-gap (space between elements)
│   └── section-gap (space between content groups)
├── backgrounds
│   ├── default (primary slide background)
│   ├── alternate (for visual variety)
│   ├── accent (bold color for emphasis slides)
│   ├── dark (inverted for contrast slides)
│   └── image-overlay (color + opacity for text-over-image)
└── effects
    ├── border-radius
    ├── shadow (for cards, elevated elements)
    └── transition (slide transition default)
```

### Theme Generation from Query
When generating a theme from a user query:
1. **Extract tone signals**: "professional" → muted palette, serif headlines. "startup" → vibrant palette, sans-serif. "creative" → bold palette, display fonts.
2. **Determine industry palette**: FinTech → blues/greens. Healthcare → blues/whites. Education → warm tones. AI/Tech → purples/cyans.
3. **Select font pairing**: Match display + body fonts based on tone (see Font Pairing below)
4. **Generate color palette**: 8-color token set with proper contrast ratios
5. **Set spacing system**: Based on content density expectations

## Color Theory for Presentations

### The 60-30-10 Rule
- **60% dominant color**: Background, large surfaces. Usually neutral (white, dark, muted)
- **30% secondary color**: Headers, containers, section elements. The "brand" feel
- **10% accent color**: CTAs, highlights, data emphasis, icons. The "pop"

### Color Palette Generation
Given a primary brand color, generate the full palette:
1. **Primary**: The given brand color
2. **Secondary**: Analogous or complementary (30° or 180° on the color wheel)
3. **Background**: Very light tint of primary (light themes) or very dark shade (dark themes)
4. **Surface**: Slightly differentiated from background for containers
5. **Text Primary**: Near-black for light themes, near-white for dark themes
6. **Text Secondary**: 70% opacity of text primary
7. **Text Muted**: 50% opacity of text primary
8. **Accent**: Complementary or triadic to primary — must contrast against both background and surface

### Contrast Requirements
- **Headlines on background**: Minimum 7:1 contrast ratio (WCAG AAA)
- **Body text on background**: Minimum 4.5:1 contrast ratio (WCAG AA)
- **Text on images**: Always use an overlay (semi-transparent background behind text)
- **Data highlights**: Accent color must be distinguishable from primary and secondary

### Dark vs. Light Theme Decisions
- **Light themes**: Default for most business/investor presentations. Clean, professional, printable.
- **Dark themes**: Use for creative/tech brands, demo presentations, or when user explicitly requests. Harder to print, but more dramatic on screen.
- **Mixed**: Some decks use dark for impact slides (opener, closer) and light for content slides. This creates visual rhythm.

## Typography for Presentations

### Font Pairing Rules
- **Contrast in structure**: Pair a serif display with a sans-serif body, or a geometric sans with a humanist sans
- **Match in spirit**: Both fonts should feel like they belong to the same era/energy
- **Never pair similar fonts**: Two different sans-serifs that look almost the same creates tension, not harmony
- **Limit to 2 fonts per deck**: Display (headlines) + Body (everything else). A third font is only justified for monospace (code) or special callouts.

### Recommended Safe Pairings (Web-safe / Google Fonts)
| Tone | Display Font | Body Font |
|------|-------------|-----------|
| Professional/Corporate | Playfair Display | Source Sans Pro |
| Modern/Tech | Inter | Inter (weight variation) |
| Startup/Bold | Sora | DM Sans |
| Creative/Expressive | Clash Display | Satoshi |
| Classic/Trustworthy | Lora | Open Sans |
| Minimal/Clean | Space Grotesk | IBM Plex Sans |

### Type Scale for Slides
Presentations need larger sizes than web/print. Base unit: slide height-relative.
| Token | Typical Size (on 1080p) | Usage |
|-------|------------------------|-------|
| heading-1 | 44-60px | Slide title, hero statements |
| heading-2 | 32-40px | Section headers, key points |
| body-large | 24-28px | Primary body text |
| body | 20-24px | Standard body text |
| caption | 16-18px | Footnotes, sources, labels |
| label | 14-16px | Axis labels, tags, metadata |

### Typography Anti-Patterns
- **All caps body text**: Harder to read, only use for short labels
- **Center-aligned body paragraphs**: Ragged both sides kills readability. Left-align body text.
- **Tight line-height on body text**: 1.4-1.6 line height minimum for readability
- **More than 3 font weights on one slide**: Creates visual noise

## Background Strategies

### Solid Color Backgrounds
- **Best for**: Content-heavy slides, data slides, most body slides
- **Use the theme's background token** as the default
- **Alternate between 2-3 background tones** across the deck for visual variety

### Gradient Backgrounds
- **Best for**: Opener, closer, section dividers, emphasis slides
- **Use subtle gradients**: 10-20% shift between two close colors. Dramatic gradients look dated.
- **Direction matters**: Top-to-bottom or diagonal gradients guide the eye

### Image Backgrounds
- **Best for**: Atmosphere slides, product context, emotional impact
- **Always apply an overlay**: Semi-transparent dark or light layer ensures text readability
- **Blur or darken**: Never place text directly on a detailed image without treatment
- **Image relevance**: The image must reinforce the slide's message, not just "look nice"

### Pattern/Texture Backgrounds
- **Best for**: Brand-specific slides, creative decks
- **Keep patterns subtle**: Low contrast, small scale. The content is the focus, not the background.

## Image and Visual Asset Strategy

### Image Selection Criteria
1. **Relevance**: Does this image reinforce the slide's message?
2. **Quality**: High resolution, good composition, professional
3. **Consistency**: Similar style/treatment across the deck (all photos, or all illustrations, not mixed)
4. **Diversity**: Represent diverse people, scenarios, settings
5. **Uniqueness**: Avoid overused stock images (the handshake, the lightbulb, the team high-five)

### AI Image Generation Guidelines
When using available image generation models:
- **Product mockups**: Generate device frames with product UI inside
- **Abstract visuals**: Geometric patterns, data visualizations, conceptual art
- **Avoid**: Generating photorealistic people (uncanny valley risk), text in images (models struggle with text), complex scenes that need precision

### Icon Usage
- **One icon style per deck**: Outlined OR filled OR duotone, not mixed
- **Icons support, not replace text**: Icons next to labels, not icons standing alone without explanation
- **Color icons sparingly**: Most icons should be monochrome (text color), only accent icons for emphasis

## Visual Rhythm Across the Deck

### The Rhythm Rule
A deck should alternate between three visual densities:
1. **Bold/Simple** (hero slides, section dividers): Few elements, large typography, strong visual
2. **Moderate** (most content slides): Balanced text and visuals, clear hierarchy
3. **Dense** (data slides, comparison tables): More information, tighter spacing

Pattern: Bold → Moderate → Moderate → Dense → Bold → Moderate → ...
Never stack 3+ dense slides in a row. Never stack 3+ bold slides in a row.

### Whitespace as a Design Tool
- **Slide margins**: Minimum 0.5 inches from all edges (safe zone for screens and projectors)
- **Between elements**: Consistent gap using the spacing token
- **Empty space is intentional**: An empty area on a slide communicates confidence and focus
- **Crowded slide = unclear message**: If you're filling all the space, you're trying to say too much

## Procedure When Working on Design

1. **Determine the audience and tone** — This drives every color, font, and spacing decision
2. **Generate theme tokens first** — Colors, fonts, spacing before any slide content
3. **Apply the 60-30-10 rule** — Check color distribution across 3-4 sample slides
4. **Verify contrast ratios** — Every text-on-background combination must be readable
5. **Plan visual rhythm** — Map bold/moderate/dense across the deck outline
6. **Select background strategy** — Decide which slides get solid, gradient, image, or accent backgrounds
7. **Choose image approach** — All photos, all illustrations, or illustrations+diagrams (pick one)
8. **Test at actual size** — Design decisions that work at thumbnail fail at full screen and vice versa
