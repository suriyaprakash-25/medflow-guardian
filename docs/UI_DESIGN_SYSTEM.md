# MedFlow Guardian UI Design System

## Overview
This document outlines the shared design system implemented across the `patient-app` and `doctor-portal` interfaces in MedFlow Guardian. To prevent monorepo complexity while maintaining strict visual consistency, the design system relies on a common `frontend-shared` directory aliased via Vite (`@shared`).

## Core Technologies
- **CSS Framework**: Tailwind CSS
- **Icons**: Lucide React (`lucide-react`)
- **Notifications**: React Hot Toast (`react-hot-toast`)
- **Components**: Functional React components with Tailwind utility classes.

## Design Principles
1. **Calm & Clinical**: Interfaces should evoke trust, cleanliness, and clarity.
2. **Accessible**: High contrast text, keyboard-navigable forms, and semantic HTML.
3. **Responsive**: Mobile-first grid structures with collapsible sidebars.
4. **Non-Blocking**: Errors and successes use toast notifications, never native `window.alert()`.

---

## Color Palette (Tailwind Configuration)

The system relies on HSL CSS variables defined in `frontend-shared/global.css`.

### Base Theme
- **Background**: `bg-background` (Slate 50 / #f8fafc) - Soft, non-straining white.
- **Card**: `bg-card` (Pure White) - Elevated containers.
- **Primary**: `bg-primary` (Blue 500 / #3b82f6) - Main actionable color.
- **Destructive**: `bg-destructive` (Red 500 / #ef4444) - Dangerous actions (Revoke, Reject).
- **Muted**: `bg-muted` (Slate 100) - For secondary backgrounds and empty states.
- **Border**: `border-border` (Slate 200) - Subtle separation lines.

### Healthcare Status Colors
Explicit overrides for medical terminology:
- **Pending**: Amber (`--status-pending`)
- **Reviewed**: Blue (`--status-reviewed`)
- **Resolved**: Emerald (`--status-resolved`)
- **Critical Priority**: Red (`--priority-critical`)
- **High Priority**: Orange (`--priority-high`)

---

## Shared UI Components (`@shared/ui`)

### `Button`
A highly reusable button with built-in disabled states and focus rings.
**Variants**:
- `default`: Primary action (Blue).
- `secondary`: Alternative action (Slate).
- `outline`: Bordered, transparent background.
- `ghost`: Transparent background, hover effects only.
- `destructive`: Red background for destructive actions.
**Sizes**: `default`, `sm`, `lg`, `icon`.

### `Card`
A composed component for content grouping.
Sub-components: `<Card>`, `<CardHeader>`, `<CardTitle>`, `<CardDescription>`, `<CardContent>`, `<CardFooter>`.

### `Badge`
Inline status indicators.
**Variants**: `default`, `secondary`, `destructive`, `outline`, `success`, `warning`.

### `Input` & `Select`
Standardized form controls with consistent padding, borders, and focus rings (`focus-visible:ring-ring`).

### `Skeleton`
An animated pulse block (`animate-pulse`) used to indicate loading states and prevent layout shift before data arrives.

### `EmptyState`
A composed fallback component displaying an icon, title, description, and optional call-to-action button when lists (like Triage Queue or Access History) are empty.

### `ConfirmModal`
A reusable, accessible modal overlay (using fixed positioning and backdrop blur) to intercept dangerous actions (like revoking access) before firing the API request.

---

## Notification System
Native `window.alert()` and `window.confirm()` are strictly prohibited.
- **Success/Error**: Use `toast.success()` and `toast.error()`.
- **Placement**: `<Toaster position="top-right" />` is mounted at the `<App>` root level in both applications.
