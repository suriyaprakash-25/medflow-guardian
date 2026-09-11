# MedFlow Guardian Patient App Design System

This document outlines the shared visual language, components, and interaction models for the patient portal, ensuring a calm, professional, and accessible healthcare experience.

## 1. Core Principles
- **Professional & Trustworthy**: Avoid overly playful aesthetics (no heavy bounce animations, no neon gradients). 
- **Accessible**: High contrast text, large tap targets, and clear legible typography.
- **Human-centered**: Medical jargon replaced with clear human-readable labels.
- **Calm**: Ample spacing, soft gray backgrounds, and restrained use of primary colors.

## 2. Color Palette
Using HSL variables managed via Tailwind CSS v4 `@theme`.

### Backgrounds & Surfaces
- **App Background**: `--color-background: hsl(210, 40%, 98%)` (Soft slate gray/blue)
- **Card Surface**: `--color-card: hsl(0, 0%, 100%)` (Pure white for depth)
- **Sidebar/Shell**: `--color-slate-900: hsl(222.2, 84%, 4.9%)` (Deep navy for contrast)

### Primary & Accents
- **Primary Brand**: `--color-primary: hsl(221.2, 83.2%, 53.3%)` (Trustworthy medical blue)
- **Primary Hover**: Slightly darker shade of primary for button interactions.
- **Secondary Action**: `--color-secondary: hsl(210, 40%, 96.1%)` (Light gray for less prominent actions)

### Status Colors
- **Success / Resolved**: `--status-resolved: #10b981` (Emerald)
- **Warning / Pending**: `--status-pending: #f59e0b` (Amber)
- **Info / Reviewed**: `--status-reviewed: #3b82f6` (Blue)
- **Critical / Destructive**: `--color-destructive: hsl(0, 84.2%, 60.2%)` (Red)

## 3. Typography
- **Font Family**: Default system sans-serif (Inter, Roboto, SF Pro) tailored for readability.
- **Headings (h1, h2, h3)**: Bold, tight tracking (e.g., `-tracking-tight`), dark slate text (`text-slate-900`).
- **Body Text**: Regular weight, `text-slate-600` for secondary information, `text-slate-800` for primary readable text.
- **Small Text**: `text-sm` (14px) or `text-xs` (12px) for timestamps and metadata.

## 4. Layout & Spacing
- **Responsive Shell**: Fixed left sidebar on desktop (256px), hidden on mobile with a hamburger menu toggle.
- **Content Max-Width**: Main content constrained to `max-w-6xl` for readability on ultrawide monitors.
- **Spacing Scale**: Standard Tailwind spacing. `p-6` for card interiors, `gap-4` or `gap-6` for grid items.
- **Card Styling**: `rounded-xl`, `border border-slate-200`, `bg-white`, `shadow-sm`.

## 5. Components

### Buttons
- **Primary**: Solid blue background, white text, slight hover darkening, rounded-md.
- **Secondary**: White background, light gray border, dark text, slight gray hover.
- **Destructive**: Solid red background, white text.

### Badges/Status Pills
- Rounded full (`rounded-full`), `px-2.5 py-0.5`, `text-xs font-semibold`.
- Colors correspond to the Status Colors above (e.g., light emerald background with dark emerald text for "Resolved").

### Inputs & Selects
- `h-10`, `rounded-md`, `border-slate-200`, `focus:ring-2 focus:ring-primary`, `text-sm`.

### Loading & Empty States
- **Skeleton**: Soft pulsing gray blocks (`animate-pulse bg-slate-200 rounded-md`) matching the shape of the expected content.
- **Empty State**: Centered content, a subtle Lucide icon (e.g., `Inbox`, `FileText`), and reassuring gray text ("No new messages at this time").

## 6. Interaction & Animation Rules
- **Hover States**: Subtle color transitions (`transition-colors duration-200`) on buttons and interactive list items.
- **Page Transitions**: Soft fade-in on initial route load (`animate-in fade-in duration-300`).
- **Feedback**: Non-blocking `react-hot-toast` notifications at `top-right` for successes/errors.
- **Modals**: Centered with a dark, slightly transparent backdrop (`bg-black/50`). Smooth scale-in animation.

## 7. Accessibility
- Minimum contrast ratio of 4.5:1 for all text.
- Interactive elements must be fully keyboard navigable (focus rings).
- `aria-labels` on icon-only buttons (like the mobile menu toggle).
- Respect `prefers-reduced-motion` for all transitions.
