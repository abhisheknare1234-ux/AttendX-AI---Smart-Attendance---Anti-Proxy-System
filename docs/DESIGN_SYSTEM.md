# Design System — AttendX AI

## 1. Visual identity

A premium institutional SaaS language: white surfaces, a light-gray workspace, restrained royal-blue
accents, clear typography and minimal shadows. The same tokens drive the desktop and mobile
experiences.

| Token | Value | Use |
|---|---|---|
| Royal blue | `#2864E8` | Primary actions, active states, brand |
| Hover blue | `#1F55C7` | Primary hover |
| Workspace | `#F7F9FC` | Page background |
| Card | `#FFFFFF` | Surfaces |
| Primary text | `#202938` | Headings/body |
| Secondary text | `#728096` | Hints, metadata |
| Border | `#E5EAF1` | Dividers, inputs, cards |
| Active navigation | `#EDF4FF` | Selected nav/active chips |
| Success | `#12855A` | Accepted/present |
| Warning | `#B45309` | Review/pending |
| Danger | `#B42318` | Rejected/disabled |

Tailwind 4 `@theme` tokens in `apps/web/app/globals.css` expose these as `bg-brand`, `text-ink`,
`text-muted`, `border-line`, `bg-workspace`, `bg-active`, etc.

## 2. Typography

- Family: `Inter, "Segoe UI", system-ui, -apple-system, "Helvetica Neue", Arial, sans-serif`.
- Base body: 15 px, line-height 1.5.
- Page title: 20–24 px semibold; section title: 14–16 px semibold; labels: 12 px semibold; metadata:
  11–12 px.
- Uppercase micro-labels use `letter-spacing: 0.14em` for navigation context, never for long body text.

## 3. Spacing and shape

- 4 px spacing rhythm; page padding 16 px mobile / 24 px desktop; card padding 16–20 px.
- Card radius 14 px (`--radius-card`); controls 8 px; modal 16–24 px; badges/pills fully rounded.
- Borders over shadows; one subtle shadow for modals and floating cards.
- No decorative gradients inside the workspace. The landing hero uses a soft radial wash; the login
  panel uses the brand colour with a subtle grid.

## 4. Core components

| Component | Behaviour |
|---|---|
| `Button` | Variants primary/secondary/ghost/danger/success; sizes sm/md/lg; loading spinner; disabled cursor |
| `Card` / `CardHeader` | Bordered white surface with optional header action |
| `Field`, `Input`, `Select`, `Textarea` | Label/hint/error, focus ring, 44 px touch height |
| `Switch` | Accessible `role="switch"` with label and hint |
| `Badge` | Semantic tones; status → tone mapping |
| `Alert` | info/success/warning/danger with title |
| `StatCard` | Label, value, hint and tinted icon |
| `Table` | Horizontal scroll wrapper on small screens; uppercase headers |
| `Modal` | Backdrop, Escape close, focus-visible close, scroll lock, bottom-sheet on mobile |
| `EmptyState` | Icon, title, explanation, action |
| `Spinner`, `Skeleton` | Loading states without layout shift |
| `PageHeader` | Eyebrow, title, description, actions |

## 5. Layout language

- **Desktop shell:** fixed 260 px white sidebar, role chip, scrollable navigation, account footer;
  sticky top bar; workspace content capped at 1400 px.
- **Mobile student shell:** sticky branded header, single-column content capped at 640 px, fixed
  bottom navigation with five destinations, safe-area padding.
- **Landing:** 7xl container, alternating white/soft-gray sections, one dark security band, clear
  headings and honest status labels.
- **Login:** split screen. Left: royal-blue brand, welcome copy and a verification-chain illustration.
  Right: light background with a white card, email, password with visibility toggle, validation,
  loading and error states.

## 6. States and feedback

- Loading: skeletons for list/dashboard regions; button-level spinner for actions.
- Empty: explain what will appear and what the user can do.
- Error: inline alert with a specific message; never a fabricated success.
- Success: explicit confirmation (e.g., attendance reference) and the next action.
- Verification states use the same vocabulary everywhere: PASSED / FAILED / UNAVAILABLE /
  NOT_REQUIRED / PENDING_REVIEW.

## 7. Accessibility

- Semantic headings and landmarks (`header`, `nav`, `main`, `footer`).
- Visible focus rings (`:focus-visible`, 3 px translucent brand outline).
- Dialog roles, `aria-modal`, labelled title and Escape close.
- Switch semantics (`aria-checked`), table headers, button labels and `aria-current` navigation.
- Touch targets at least 40–44 px; bottom navigation is thumb-reachable.
- Colour is never the only signal: badges include text/status labels.
- Reduced motion is respected implicitly by avoiding large decorative animation; only spinner and a
  subtle pulse dot animate.

## 8. Content rules for this product

- Never claim perfect prevention or proven accuracy.
- Distinguish implemented features from provider-dependent or planned features.
- Use "review required" language rather than implying guilt when evidence is missing.
- Explain permission requests before the browser prompt.
- Do not display fake institutional statistics or adoption claims.
