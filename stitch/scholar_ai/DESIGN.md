# Design System Strategy: The Scholarly Synthesis

## 1. Overview & Creative North Star
The Creative North Star for this system is **"The Digital Curator."** 

Unlike standard productivity tools that feel like cold, mechanical databases, this system is designed to feel like a premium, bespoke research library. We are moving away from the "app-like" rigid grid and moving toward an **Editorial High-End** experience. This is achieved through intentional asymmetry—where the density of information is balanced by expansive, high-quality whitespace—and a sophisticated "Mixed-Media" typography approach. The goal is to make the user feel like an author, not just a data entry clerk.

By leveraging scholarly serif body text against a hyper-modern sans-serif UI, we create a "New Academic" aesthetic: one that respects the tradition of knowledge (Obsidian) while embracing the velocity of AI (Perplexity).

---

## 2. Colors & Surface Philosophy

### The "No-Line" Rule
To achieve a premium feel, **1px solid borders are strictly prohibited for sectioning.** 
Structural definition must be achieved through:
- **Tonal Shifts:** Placing a `surface-container-low` sidebar against a `surface` main content area.
- **Negative Space:** Using the spacing scale to create clear mental boundaries without visual noise.

### Surface Hierarchy & Nesting
Treat the UI as a physical stack of fine paper and frosted glass.
- **Base Layer:** `surface` (#f9f9f9) – The desk on which everything sits.
- **Primary Content Areas:** `surface-container-lowest` (#ffffff) – Used for the active writing/reading space to provide maximum focus and "sheet-like" clarity.
- **Navigation/Utility:** `surface-container` (#eeeeee) or `surface-container-high` (#e8e8e8) – Used for background elements that need to feel "recessed" or secondary.

### The "Glass & Gradient" Rule
AI-powered features should not feel like static boxes. 
- **AI Surfaces:** Use `secondary_container` at 40% opacity with a `backdrop-blur` of 12px. This creates a "Glassmorphism" effect that signifies the fluid, generative nature of AI.
- **Signature Gradients:** For primary actions or AI entry points, use a subtle linear gradient from `primary` (#24389c) to `primary_container` (#3f51b5) at a 135-degree angle. This adds "soul" and depth that flat hex codes cannot provide.

---

## 3. Typography: The Dual-Tone System
We use a high-contrast typography strategy to distinguish between "System" (The Tool) and "Knowledge" (The Content).

*   **UI Elements (Inter):** Used for labels, buttons, and navigation. It is functional, neutral, and precise.
    *   *Headline-LG:* Bold, tight tracking (-2%) to feel authoritative.
*   **Body Content (Noto Serif SC):** Used for the "Wiki" content and AI responses. The serif evokes a scholarly, published feel, making long-form reading effortless.
*   **Code & Logic (JetBrains Mono):** Used for technical snippets and metadata. It provides a distinct visual "texture" change for non-narrative data.

---

## 4. Elevation & Depth

### The Layering Principle
Avoid "Drop Shadows" on standard components. Instead, use **Tonal Layering**. 
*   An "Information Card" should be `surface-container-lowest` sitting on a `surface-container` background. The 12px (`md`) radius provides the "objectness" needed without the clutter of a shadow.

### Ambient Shadows
When an element must float (e.g., a Command Palette or Context Menu):
- **Shadow:** Use the `on_surface` color at 6% opacity.
- **Blur:** 32px to 64px.
- **Spread:** -4px (to keep the shadow tucked under the element, mimicking soft overhead studio lighting).

### The "Ghost Border" Fallback
If a visual divider is functionally required for accessibility:
- Use `outline_variant` at **15% opacity**. It should be felt rather than seen.

---

## 5. Components

### The "Intelligent" Input
Text areas should not look like empty boxes.
- **Default:** `surface-container-low` with a `md` (0.75rem) radius.
- **Active/Focus:** Transition to `surface-container-lowest` with a signature "Cyan" (`secondary`) glow using a 2px `secondary_fixed` outer glow (8% opacity).

### AI Interaction Chips
- **Research Chips:** Use `secondary_container` with `on_secondary_container` text. 
- **Organic/Wiki Chips:** Use `tertiary_container` (Sage) with `on_tertiary_container` text.
- **Shape:** Always `full` (pill-shaped) to contrast against the `md` radius of the main containers.

### Buttons (The "Editorial" Style)
- **Primary:** Gradient-filled (`primary` to `primary_container`), `on_primary` text, no border.
- **Secondary:** Transparent background, `primary` text, and a "Ghost Border" (15% `outline`).
- **Tertiary/Ghost:** No background, `on_surface_variant` text. High-density whitespace (padding: 12px 24px).

### Cards & Lists
- **Rule:** Forbid divider lines between list items.
- **Implementation:** Use 8px of vertical whitespace between items. On hover, the background shifts to `surface-container-highest` with a 150ms fluid transition.

---

## 6. Do's and Don'ts

### Do:
*   **DO** use `surface-container-lowest` for the main writing canvas to make it feel like a "fresh sheet of paper."
*   **DO** use asymmetric margins. For example, a wider left margin for the main text body to allow for "marginalia" or AI annotations.
*   **DO** use 150ms "Ease-Out" transitions for all hover states to maintain the "Subtle & Fluid" motion requirement.

### Don't:
*   **DON'T** use 100% black text. Always use `on_surface` (#1a1c1c) to maintain a soft, ink-on-paper feel.
*   **DON'T** use sharp corners. Every surface must adhere to the 12px (`md`) or higher radius scale.
*   **DON'T** use "Standard Blue" for links. Use the `primary` Indigo for internal wiki links and `secondary` Cyan for AI-generated citations.

### Accessibility Note
While we prioritize "Ghost Borders" and "Tonal Layering," always ensure the contrast ratio between `surface-container` tiers and `on_surface` text meets WCAG AA standards (4.5:1). If a tonal shift is too subtle for certain displays, rely on the `outline-variant` at its 15% "Ghost" opacity to provide a structural hint.