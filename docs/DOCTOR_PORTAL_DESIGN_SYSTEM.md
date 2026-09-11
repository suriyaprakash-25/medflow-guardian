# Doctor Portal Design System

This design system defines the visual language for the MedFlow Guardian Doctor Portal, ensuring a clinical, reliable, and efficient user experience.

## 1. Design Philosophy
- **Clinical & Trustworthy**: Clean lines, ample whitespace, and legible typography.
- **Efficient**: High information density without feeling cluttered.
- **Urgency-Aware**: Calm under normal conditions; uses color strategically to highlight critical triage requests or abnormal vitals.

## 2. Color Palette
The app uses Tailwind CSS v4 colors.

**Brand & Primary:**
- Primary: `blue-600` (Main actions, active states)
- Primary Hover: `blue-700`

**Clinical Semantics (Priority & Status):**
- Critical/High Urgency: `rose-600` text, `rose-100` background.
- Warning/Pending: `amber-600` text, `amber-100` background.
- Success/Completed: `emerald-600` text, `emerald-100` background.
- Info/Low Urgency: `slate-600` text, `slate-100` background.

**Neutrals (Backgrounds & Text):**
- App Background: `slate-50`
- Surface/Card: `white`
- Text Primary: `slate-900`
- Text Secondary: `slate-500`
- Borders: `slate-200`

## 3. Typography
- **Font**: Inter (or system sans-serif like Roboto/San Francisco).
- **Hierarchy**:
  - H1 (Page Title): `text-2xl font-bold tracking-tight text-slate-900`
  - H2 (Section Title): `text-lg font-semibold text-slate-800`
  - H3 (Card Title): `text-base font-semibold text-slate-900`
  - Body Text: `text-sm text-slate-600`
  - Small/Meta: `text-xs text-slate-500`

## 4. Components

### Cards
- **Style**: `bg-white border border-slate-200 rounded-xl shadow-sm`.
- **Usage**: Used to contain discrete sections of information (e.g., a patient summary, a chart, a list of documents).

### Buttons
- **Primary**: `bg-blue-600 hover:bg-blue-700 text-white rounded-md px-4 py-2 text-sm font-medium transition-colors`.
- **Secondary/Outline**: `border border-slate-200 bg-white hover:bg-slate-50 text-slate-700 rounded-md px-4 py-2 text-sm font-medium`.
- **Destructive**: `bg-rose-600 hover:bg-rose-700 text-white`.
- **Ghost**: `hover:bg-slate-100 text-slate-600`.

### Badges (Status & Priority)
- Rounded pills (`rounded-full px-2.5 py-0.5 text-xs font-semibold`).
- Rely on text labels ("Critical", "Pending") in addition to color for accessibility.

### Tables & Lists
- Clean rows with subtle `border-b border-slate-100`.
- Hover states (`hover:bg-slate-50`) to indicate interactivity.
- Avatars or icons on the left to anchor the row.

## 5. Layout & Spacing
- **Sidebar**: Fixed width (`w-64`), dark theme (`bg-slate-900`).
- **Header**: Sticky top, `h-16`, white background, bottom border.
- **Main Content**: Max-width container (`max-w-7xl mx-auto`) with `p-6` or `p-8` padding.
- **Spacing Scale**: Rely on standard Tailwind spacing (`gap-4`, `gap-6`, `mb-4`, `mb-8`).

## 6. Motion & Feedback
- **Page Transitions**: Use `animate-in fade-in slide-in-from-bottom-4 duration-500` for smooth load.
- **Hover Effects**: Subtle transitions on buttons and cards (`transition-all duration-200`).
- **Feedback**: Use Toast notifications (react-hot-toast) for async actions (uploads, approvals).
- **Empty States**: Centered illustration/icon with a descriptive title and subtitle.

## 7. Responsive Rules
- **Desktop (lg+)**: Sidebar visible, complex tables show all columns.
- **Tablet (md)**: Sidebar visible, some table columns hide.
- **Mobile (sm)**: Sidebar hides behind a hamburger menu, cards stack vertically, tables convert to stacked lists.
