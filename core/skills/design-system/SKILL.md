# Skill: Design System

## วัตถุประสงค์
UI/UX mobile-first dashboard design tokens components Storybook Penpot

## Design Tokens
- Primary color: #2563EB
- Success: #16A34A
- Warning: #D97706
- Error: #DC2626
- Background: #0F172A (dark) / #F8FAFC (light)
- Font: Noto Sans Thai, Inter (fallback sans-serif)
- Base font size: 16px
- Spacing unit: 4px

## Mobile-first Breakpoints
- xs: 375px
- sm: 640px
- md: 768px
- lg: 1024px
- xl: 1280px

## Component Checklist
- [ ] Loading state
- [ ] Error state
- [ ] Empty state
- [ ] Success state
- [ ] Mobile-friendly touch targets (44px min)
- [ ] Dark mode support
- [ ] Thai font rendering

## Dashboard Pages
- index.vue — System status overview
- command.vue — Send command
- jobs.vue — Task list
- approvals.vue — Pending approvals
- knowledge.vue — RAG document browser
- logs.vue — Service logs

## Profiles
- Storybook: Docker profile `design` port 6006
- Penpot: Docker profile `design` port 9001
