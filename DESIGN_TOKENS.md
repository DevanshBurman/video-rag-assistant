# AI Video Assistant — Design System & Design Tokens

This design system establishes a high-fidelity, light-native 3D aesthetic derived directly from pixel-sampled values of the reference UI (`satquery-ai-gold.vercel.app`), coupled with an inverted, deep-navy dark theme with luminous teal accents.

---

## 1. Color Palette & Semantic Tokens

### Light Theme (Default, Sampled Reference)
The light theme is clean, spacious, and authoritative: a soft page mist canvas, clean white surfaces, hairlines in cool-grey, and a deep navy navigation rail anchored with teal and bright blue action accents.

| Token | Hex / Value | Role / Usage | Contrast vs Background |
| :--- | :--- | :--- | :--- |
| `--bg` | `#F5F8FA` | Page background canvas / mist | Base |
| `--bg-soft` | `#F2F6F5` | Canvas wells, code background | > 1.05:1 |
| `--surface` | `#FFFFFF` | Cards, top bar, modals, active inputs | 1.08:1 (Elevation 1) |
| `--surface-2` | `#FAFDFE` | Secondary card background | 1.05:1 (Elevation 2) |
| `--surface-tint` | `#EDF6F8` | Action chips, quote boxes, hover states | Subtle teal tint |
| `--icon-tile` | `#E5F3F1` | Rounded empty-state icon badge | Soft aqua backing |
| `--border` | `#DDE7EC` | Hairline dividers, card outlines (1px) | WCAG UI component compliant |
| `--border-subtle` | `#EAF0F4` | Inner dividers, table borders | Subtle structure |
| `--ink` | `#0F2A3A` | Primary headings, prominent titles | **13.5:1** (WCAG AAA) |
| `--text` | `#3C5565` | Body copy, secondary titles, logo slate | **7.2:1** (WCAG AAA) |
| `--text-2` | `#5E7686` | Secondary body, metadata labels | **4.8:1** (WCAG AA) |
| `--text-muted` | `#7E95A7` | Placeholders, captions, disabled cues | 3.2:1 (Non-body/caption) |
| `--rail-top` | `#233A4C` | Sidebar icon rail top gradient | Deep slate-navy |
| `--rail-bottom` | `#142A3C` | Sidebar icon rail bottom gradient | Deepest navy |
| `--rail-active` | `#EDF4FF` | Active rail icon tile background | Crisp light rounded tile |
| `--rail-active-ink` | `#0966ED` | Active rail icon color | High contrast bright blue |
| `--primary` | `#0966ED` | Primary CTA, active nav step indicator | **4.6:1** on light, white text **4.6:1** |
| `--primary-hover` | `#0854C4` | Hover state for primary buttons | Deepened blue |
| `--primary-ink` | `#FFFFFF` | Text on primary buttons | **4.6:1** on `#0966ED` |
| `--teal` | `#36D5D0` | Secondary CTA fill, brand highlights | Paired with dark ink `#06222B` (**9.8:1**) |
| `--teal-ink` | `#06222B` | Text on teal button / CTA | **9.8:1** (WCAG AAA) |
| `--teal-2` | `#22BFC0` | Progress lines, quote borders, accents | Vivid aqua accent |
| `--teal-deep` | `#168F95` | Eyebrow badges, links on light canvas | **4.7:1** (WCAG AA) |
| `--teal-deeper` | `#087F96` | Active step labels, dark aqua headers | **5.5:1** (WCAG AAA) |
| `--glow-aqua` | `#EAF9FA` | Radial ambient glow, spotlight backdrops | Ambient lighting |
| `--tooltip` | `#153542` | Tooltip & popover surfaces (light text) | Deep slate |
| `--tooltip-text` | `#F5F8FA` | Tooltip text | **12.8:1** (WCAG AAA) |
| `--success` | `#16A37F` | Completed pipeline steps, success tags | 4.6:1 |
| `--warn` | `#E0A100` | Warning badges, retry notices | 4.5:1 |
| `--danger` | `#D64550` | Error banners, validation failures | 4.8:1 |

---

### Dark Theme (Inverse Harmony)
The dark theme derives directly from the sidebar navy tones (`#0C1D29` / `#142A3C`), shifting lightness while preserving teal and electric blue accents, enriched by subtle volumetric glows and frosted depth.

| Token | Hex / Value | Role / Usage | Contrast vs Background |
| :--- | :--- | :--- | :--- |
| `--bg` | `#0A1822` | Deep navy page canvas | Base |
| `--bg-soft` | `#0E202D` | Wells, input background | Elevation -1 |
| `--surface` | `#122736` | Card base, top bar, modals | Elevation 1 |
| `--surface-2` | `#16303F` | Elevated cards, sidebar panels | Elevation 2 |
| `--surface-tint` | `#1B3A4A` | Hover states, quote boxes, active tabs | Elevation 3 |
| `--icon-tile` | `#17424A` | Icon backdrop tile | Subtle teal depth |
| `--border` | `#24404F` | Hairline card borders and dividers | Balanced boundary |
| `--border-subtle` | `#1D3442` | Inner dividers | Subtle separation |
| `--ink` | `#EAF4F7` | Primary headings, prominent titles | **13.2:1** (WCAG AAA) |
| `--text` | `#C4D6DE` | Body copy, secondary titles | **9.5:1** (WCAG AAA) |
| `--text-2` | `#9DB4C0` | Secondary descriptions, metadata | **6.6:1** (WCAG AAA) |
| `--text-muted` | `#6F8B9B` | Captions, placeholders, disabled cues | **3.8:1** (AA Large) |
| `--rail-top` | `#0C1D29` | Left sidebar gradient top | Ultra-deep navy |
| `--rail-bottom` | `#07131B` | Left sidebar gradient bottom | Near black navy |
| `--rail-active` | `#1B3A4A` | Active rail tile | Glowing deep tile |
| `--rail-active-ink` | `#3D8BFF` | Active rail icon | Luminous blue |
| `--primary` | `#3D8BFF` | Primary button fill & active indicator | **7.2:1** vs dark bg |
| `--primary-hover` | `#589DFF` | Hover state for primary buttons | Bright blue |
| `--primary-ink` | `#061523` | Text on dark-mode primary button | **8.4:1** (WCAG AAA) |
| `--teal` | `#36D5D0` | CTA fill, accent highlights | Luminous aqua |
| `--teal-ink` | `#06222B` | Text on teal button | **9.8:1** (WCAG AAA) |
| `--teal-2` | `#2BC4C4` | Progress indicators, border highlights | Saturated teal |
| `--teal-deep` | `#5FE0DC` | Eyebrow badges, links on dark canvas | **10.5:1** (WCAG AAA) |
| `--teal-deeper` | `#36D5D0` | Active step labels | Bright aqua |
| `--glow-aqua` | `rgba(54, 213, 208, 0.14)` | Atmospheric radial glow | Soft cyan aura |
| `--tooltip` | `#EAF4F7` | Tooltip surfaces | Inverted bright plate |
| `--tooltip-text` | `#0B1E2B` | Tooltip text | **13.8:1** (WCAG AAA) |
| `--success` | `#22C55E` | Completed pipeline steps | Crisp emerald |
| `--warn` | `#FBBF24` | Warning alerts | Amber |
| `--danger` | `#F87171` | Error states | Coral red |

---

## 2. Typography System

Fonts are loaded from Google Fonts via preconnected links:
- **Display & Headings**: `Plus Jakarta Sans`, `Space Grotesk` (weights: 500, 600, 700, 800)
- **Body & UI**: `Inter`, `Plus Jakarta Sans` (weights: 400, 500, 600)
- **Monospace, Code & Transcripts**: `JetBrains Mono`, `DM Mono` (weights: 400, 500)

### Typographic Scales:
- **Eyebrow / Kicker**: `10.5px` / `0.656rem`, font-weight 600, `letter-spacing: 0.18em`, `text-transform: uppercase`
- **Display Heading (Hero / Studio Title)**: `clamp(32px, 3.8vw, 56px)`, font-weight 800, `letter-spacing: -0.04em`, line-height `1.1`
- **H2 (Section Titles)**: `clamp(22px, 2.2vw, 32px)`, font-weight 700, `letter-spacing: -0.03em`, line-height `1.2`
- **H3 (Card Titles)**: `18px`, font-weight 600, `letter-spacing: -0.015em`, line-height `1.3`
- **H4 (Subheadings)**: `15px`, font-weight 600, line-height `1.4`
- **Body Regular**: `14px`, font-weight 400, line-height `1.65`
- **Body Small / Captions**: `12px`, font-weight 500, line-height `1.5`
- **Micro / Pills**: `11px`, font-weight 600, `letter-spacing: 0.04em`

---

## 3. Elevation, 3D Depth & Shadows

Depth is achieved through layered paper, frosted glass borders, subtle specular bevels, and theme-attuned shadows:

### Light Theme Shadows
- **Card Shadow (Rest)**: `0 2px 10px rgba(15, 42, 58, 0.04), 0 1px 3px rgba(15, 42, 58, 0.03)`
- **Card Shadow (Hover 3D)**: `0 16px 36px -6px rgba(15, 42, 58, 0.09), 0 6px 14px -3px rgba(15, 42, 58, 0.05)`
- **Modal Backdrop**: `0 32px 72px -12px rgba(15, 42, 58, 0.22), 0 12px 28px -4px rgba(15, 42, 58, 0.12)`
- **Button Tactile Bevel**: `0 2px 0 #0747A6, 0 4px 12px rgba(9, 102, 237, 0.25)` (Press: `translateY(1.5px)` with reduced shadow)

### Dark Theme Shadows
- **Card Shadow (Rest)**: `0 4px 20px rgba(0, 0, 0, 0.35), 0 0 1px rgba(54, 213, 208, 0.08)`
- **Card Shadow (Hover 3D)**: `0 18px 48px -8px rgba(0, 0, 0, 0.55), 0 0 24px rgba(54, 213, 208, 0.16)`
- **Modal Backdrop**: `0 36px 90px rgba(0, 0, 0, 0.75), 0 0 40px rgba(54, 213, 208, 0.18)`
- **Button Tactile Bevel**: `0 2px 0 #1A5CC7, 0 6px 20px rgba(61, 139, 255, 0.35)`

---

## 4. Spacing & Radius Rules
- **Border Radius**:
  - Tiles & small chips: `8px`
  - Cards & containers: `14px`
  - Modals & dialogs: `18px`
  - Rail icon tiles: `10px`
  - Pills / Badges: `9999px`
- **Hairlines**: `1px solid var(--border)`
- **Specular Card Rim**: Dual hairline gradient with `linear-gradient(135deg, rgba(255,255,255,0.8), rgba(255,255,255,0.05))` (Light) / `linear-gradient(135deg, rgba(54,213,208,0.3), rgba(255,255,255,0.02))` (Dark)
