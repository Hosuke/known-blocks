# Design System Specification: The Digital Curator

## 1. Overview & Creative North Star
The "Digital Curator" is a design philosophy that rejects the cluttered, utility-first aesthetic of traditional software in favor of an **Editorial Intelligence** approach. It treats data not as "content" to be displayed, but as "knowledge" to be curated.

This design system moves beyond standard UI patterns by embracing **intentional asymmetry** and **tonal depth**. Rather than using rigid boxes and heavy lines, we use space and light to guide the eye. The experience should feel like a high-end digital archive: scholarly and precise, yet deeply sophisticated. We achieve this through "breathable" layouts, high-contrast typography scales, and a departure from the 1px-border-everything mentality.

---

## 2. Colors & Surface Logic

### The Dark Mode Palette (High-Fidelity)
Our Dark Mode isn't just "inverted light mode." It is a deep, immersive environment built on the foundation of `surface_dim` (#0c1324).

*   **Primary (Indigo 400):** `#bdc2ff` — Used for focal points and core brand actions.
*   **Secondary (Cyan):** `#5de6ff` — Represents the "AI Layer"—precision and insight.
*   **Tertiary (Emerald):** `#45dfa4` — Success and validation.
*   **Neutrals:** Built on the Slate 950 base to ensure a cold, scholarly sophistication.

### The "No-Line" Rule
**Explicit Instruction:** Do not use 1px solid borders for sectioning or layout containment. 
Boundaries must be defined through **Background Color Shifts**. For example, a main content area (`surface`) should transition into a sidebar using `surface_container_low` or `surface_container_high`. If two elements must be separated, use white space (8px grid) rather than a divider line.

### Surface Hierarchy & Nesting
Treat the UI as a series of physical layers—like stacked sheets of vellum. 
*   **Base:** `surface_dim` (#0c1324)
*   **Floating Navigation:** `surface_container_low`
*   **Main Content Cards:** `surface_container`
*   **Active/Pop-over Elements:** `surface_container_highest`

### The "Glass & Gradient" Rule
To avoid a "flat" feel, floating elements (Modals, Hover Cards) should use **Glassmorphism**. Apply `surface_container` with a 70% opacity and a `20px` backdrop-blur. 
*   **Signature CTA:** Main buttons should not be flat. Use a subtle linear gradient from `primary` (#bdc2ff) to `primary_container` (#444fb7) at a 135-degree angle to provide a sense of "physical soul."

---

## 3. Typography
Our typography is a dialogue between the modern UI (Inter) and the timeless authority of the serif (Noto Serif SC).

| Level | Token | Font | Size | Intent |
| :--- | :--- | :--- | :--- | :--- |
| **Display** | `display-lg` | Noto Serif | 3.5rem | Editorial impact; used for "The Curator" voice. |
| **Headline**| `headline-md` | Noto Serif | 1.75rem | Section headers; scholarly and authoritative. |
| **Title**   | `title-md` | Noto Serif | 1.125rem | Specific document or card titles. |
| **Body**    | `body-lg` | Noto Serif | 1.0rem | Long-form reading; prioritized for legibility. |
| **Label**   | `label-md` | Inter | 0.75rem | Functional UI labels; lowercase for sophistication. |
| **Code**    | JetBrains Mono | — | — | Precise, technical data and citations. |

*   **Editorial Contrast:** Use `display-lg` in a light weight alongside `label-md` in all-caps (spaced 0.05em) to create a "Vogue-meets-Research-Paper" aesthetic.

---

## 4. Elevation & Depth: Tonal Layering

We convey hierarchy through **Tonal Layering** rather than structural lines.

1.  **The Layering Principle:** Instead of a drop shadow, place a `surface_container_lowest` (#070d1f) element on top of a `surface_container` (#191f31) background to create a "sunken" or "embedded" feel.
2.  **Ambient Shadows:** For floating elements, use "The Invisible Lift."
    *   `box-shadow: 0 20px 40px rgba(0, 0, 0, 0.4);`
    *   The shadow color must never be pure black; it should be a deep indigo-tinted slate to match the background atmosphere.
3.  **The "Ghost Border" Fallback:** If a boundary is strictly required for accessibility, use the `outline_variant` token (#454652) at **15% opacity**. This creates a suggestion of a border that disappears into the background.

---

## 5. Components

### Buttons
*   **Primary:** Rounded `8px` (`md`). Gradient fill (Primary to Primary-Container). No border.
*   **Secondary:** Ghost style. No background. `outline_variant` at 20% opacity. Text color: `primary`.
*   **Interaction:** On hover, primary buttons should "glow" subtly using a box-shadow that matches the button color at 30% opacity.

### Knowledge Cards
*   **Styling:** Radius `12px` (`lg`). Use `surface_container` background. 
*   **Strict Rule:** No dividers between card header and body. Use a `24px` vertical gap to separate the title from content.
*   **Footer:** Use `surface_container_high` as a subtle "shelf" at the bottom of the card for metadata.

### The "Curator" Citation (Custom Component)
A specific component for scholarly references. 
*   **Style:** Vertical line (2px wide) using the `secondary` (Cyan) token on the left.
*   **Background:** `surface_container_lowest`.
*   **Typography:** Noto Serif, italicized.

### Inputs
*   **Style:** Minimalist. No bottom line or box. Use a slightly darker background (`surface_container_lowest`) than the parent container.
*   **Focus:** Transition the background color to `surface_bright` and add a subtle `primary` glow.

---

## 6. Do’s and Don’ts

### Do:
*   **Do** use asymmetrical margins (e.g., a wider left margin than right) to give the layout an editorial, magazine-like feel.
*   **Do** use `body-lg` for any text longer than two sentences to maintain the "Scholarly" brand identity.
*   **Do** lean into "whitespace as a luxury." Space is the primary indicator of premium quality.

### Don’t:
*   **Don't** use 100% opaque borders. They clutter the visual field and break the "Curator" immersion.
*   **Don't** use standard "Material" or "Bootstrap" blue. Always refer to the Indigo-Slate palette provided.
*   **Don't** use sharp 0px corners. Even in a scholarly app, hard edges feel "industrial." Stick to the `8px` and `12px` scale.
*   **Don't** use dividers. If you feel you need a divider, add 16px of extra padding instead.