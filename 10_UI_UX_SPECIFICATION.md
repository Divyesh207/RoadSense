# UI/UX SPECIFICATION

**Project:** Road Intelligence & Pothole Management Platform  
**Document:** 10 — UI/UX Specification  
**Status:** Approved Specification  
**Version:** 1.0  
**Parent Documents:** `PROJECT_CONTEXT.md`, `PRD.md`, `SRS.md`, `SYSTEM_ARCHITECTURE.md`, `TECH_STACK.md`, `DATABASE_SCHEMA.md`, `API_SPECIFICATION.md`, `USER_ROLES_PERMISSIONS.md`

---

# 1. Purpose

This document defines the user interface and user experience requirements for the Road Intelligence & Pothole Management Platform.

It is the source of truth for:

- Web application layout
- Navigation
- Dashboard design
- Road management interface
- Inspection interface
- AI damage review
- GIS/map interface
- Road health visualization
- Deterioration prediction interface
- Maintenance management
- Repair verification
- Recurrence monitoring
- Analytics and reporting
- User management
- Notifications
- Loading/error/empty states
- Responsive behavior
- Accessibility
- Design system
- Frontend interaction patterns

The UI MUST represent the actual backend capabilities and MUST NOT create fake functionality.

---

# 2. UX Goals

The platform should make complex road-condition intelligence understandable and actionable.

The primary UX goals are:

1. **See what is happening**
2. **Understand where problems are located**
3. **Understand why a road requires attention**
4. **Review AI findings**
5. **Convert findings into maintenance actions**
6. **Verify completed work**
7. **Track recurring problems**
8. **Understand historical road condition**
9. **Support evidence-based operational decisions**
10. **Minimize unnecessary interaction complexity**

The interface should prioritize clarity over visual decoration.

---

# 3. Product UX Principle

The primary user journey is:

```text
OBSERVE
  ↓
UNDERSTAND
  ↓
REVIEW
  ↓
PRIORITIZE
  ↓
ACT
  ↓
VERIFY
  ↓
LEARN
```

The UI should reflect this operational lifecycle.

---

# 4. Design Language

The visual language should communicate:

- Infrastructure intelligence
- Reliability
- GIS/data analysis
- Field operations
- Engineering
- Public-service operations

The design should avoid looking like:

- A generic social dashboard
- A consumer finance application
- A gaming interface
- An overly decorative AI demo

The interface should feel like a professional road-management platform.

---

# 5. Technology

The web application uses:

```text
Next.js
React
TypeScript
Tailwind CSS
shadcn/ui
Framer Motion
Recharts
Leaflet
OpenStreetMap
```

The UI MUST remain compatible with the approved architecture.

---

# 6. Application Shell

The web application uses a persistent application shell.

Conceptually:

```text
┌──────────────────────────────────────────────────────────────┐
│ Top Bar                                                      │
├───────────────┬──────────────────────────────────────────────┤
│               │                                              │
│ Sidebar       │              Main Content                    │
│ Navigation    │                                              │
│               │                                              │
│               │                                              │
├───────────────┴──────────────────────────────────────────────┤
│ Optional Status / Footer                                    │
└──────────────────────────────────────────────────────────────┘
```

---

# 7. Sidebar Navigation

Primary navigation:

```text
Dashboard

Roads
Road Segments

Inspections
Damage

Map Intelligence

Road Health
Predictions

Maintenance
Repair Verification
Recurrence

Analytics
Reports

Notifications

Administration
```

The sidebar MUST be permission-aware.

Users should only see navigation items relevant to their permissions.

However, hiding a navigation item is only a UX feature. Backend authorization remains authoritative.

---

# 8. Top Bar

The top bar should contain:

- Page title/context
- Global search
- Organization selector where applicable
- Notifications
- User profile
- Optional system status
- Mobile menu trigger

Example:

```text
┌────────────────────────────────────────────────────────────┐
│ Dashboard     Search roads, damages...   🔔   User ▼      │
└────────────────────────────────────────────────────────────┘
```

---

# 9. Organization Selector

For users belonging to multiple organizations, the active organization should be clearly visible.

Example:

```text
Organization
Municipal Road Authority ▼
```

Changing organization MUST:

1. Update the active organization context.
2. Clear incompatible cached data.
3. Reload organization-scoped resources.
4. Revalidate permissions.
5. Prevent stale data from appearing under the new organization.

---

# 10. Dashboard

The dashboard is the primary operational overview.

It should answer:

- What is the current road condition?
- How many damages are active?
- Which roads require attention?
- What maintenance is pending?
- What repairs require verification?
- What problems are recurring?
- What changed recently?

---

# 11. Dashboard Layout

Recommended structure:

```text
┌──────────────────────────────────────────────────────────────┐
│ Dashboard                                                    │
│ Overview of current road intelligence                        │
├────────────┬────────────┬────────────┬──────────────────────┤
│ Roads      │ Active     │ Critical   │ Maintenance          │
│ Monitored  │ Damages    │ Damages    │ Pending              │
├────────────┴────────────┴────────────┴──────────────────────┤
│                                                              │
│                  Road Intelligence Map                       │
│                                                              │
├──────────────────────────────┬───────────────────────────────┤
│ Damage Trends                │ Maintenance Status            │
├──────────────────────────────┼───────────────────────────────┤
│ Road Health                  │ Recurring Problems            │
└──────────────────────────────┴───────────────────────────────┘
```

---

# 12. Dashboard KPI Cards

Initial KPI cards:

### Roads Monitored

Displays:

- Number of roads
- Optional change over selected period

### Active Damages

Displays:

- Open/confirmed unresolved damage
- Severity distribution where useful

### Critical Damages

Displays:

- Critical unresolved damage count

### Maintenance Pending

Displays:

- Open
- Assigned
- In-progress
- Verification pending

KPI values MUST come from real backend data.

No hardcoded demonstration values should remain in production.

---

# 13. Dashboard Filters

Dashboard filters should support:

- Date range
- Road
- Road segment
- Damage type
- Severity
- Inspection status
- Maintenance status
- Geographic area

Filters should clearly display their current state.

Example:

```text
Date: Last 30 days
Severity: All
Damage: All
Road: All
```

---

# 14. Dashboard Map

The dashboard map provides a high-level geographic overview.

It may display:

- Roads
- Road segments
- Damage points
- Severity indicators
- Maintenance locations
- Inspection locations

The map MUST NOT attempt to display every possible detail simultaneously.

Clustering SHOULD be used for dense areas.

---

# 15. Road Management

The Roads section manages road-level information.

Road list should support:

- Search
- Filtering
- Sorting
- Pagination
- Status
- Geographic area
- Health
- Damage count
- Last inspection

Example:

```text
Road Name
Area
Length
Segments
Health
Active Damages
Last Inspection
Actions
```

---

# 16. Road Detail Page

The road detail page should provide a complete road intelligence view.

Recommended structure:

```text
Road Header
    ↓
Overview
    ↓
Map
    ↓
Segments
    ↓
Damage
    ↓
Health
    ↓
Predictions
    ↓
Maintenance
    ↓
History
```

---

# 17. Road Header

Display:

- Road name
- Road identifier
- Area/location
- Road type where available
- Length
- Current health indicator
- Last inspection
- Actions available to current role

Example actions:

```text
Edit
Inspect
View Map
Create Maintenance
Generate Report
```

Only authorized actions should be shown.

---

# 18. Road Segment Interface

Road segments are important because predictions and maintenance intelligence may operate at segment level.

Segment table:

| Segment | Health | Damages | Severity | Last Inspection | Prediction |
|---|---|---|---|---|---|

Segment detail should include:

- Segment geometry
- Damage history
- Road health history
- Prediction history
- Maintenance history
- Repair history
- Recurrence history

---

# 19. Inspection Interface

The web application should show inspection lifecycle status.

Statuses:

```text
DRAFT
SUBMITTED
UPLOADING
PROCESSING
ANALYZED
REVIEW_REQUIRED
REVIEWED
COMPLETED
```

Failure states:

```text
UPLOAD_FAILED
PROCESSING_FAILED
ANALYSIS_FAILED
```

---

# 20. Inspection Detail Page

Inspection page should display:

- Inspector
- Date/time
- Location
- Road
- Segment
- Media
- Processing status
- AI processing status
- AI detections
- Review status
- Damage records
- Audit history

Example:

```text
Inspection #INS-00124

Inspector: User
Road: Main Road
Segment: SEG-004
Date: 30 Sep 2026

Processing
████████████████░░░░

AI Results
8 detections

Review
Required
```

---

# 21. AI Damage Review Interface

The AI review interface is a core workflow.

It should allow authorized users to:

- View original media
- View detection bounding boxes
- View damage type
- View confidence
- View location
- View severity
- Confirm damage
- Reject damage
- Correct classification
- Adjust severity where permitted
- Add review notes

The original AI result MUST remain preserved.

---

# 22. AI Detection Visualization

For image-based inspection:

```text
┌────────────────────────────────────┐
│                                    │
│        Road Image                  │
│                                    │
│    ┌──────────────┐                │
│    │   POTHOLE    │                │
│    │  confidence  │                │
│    └──────────────┘                │
│                                    │
└────────────────────────────────────┘
```

Bounding boxes should be visually distinct and understandable.

The interface should avoid excessive overlays.

---

# 23. Damage Detail Panel

When a detection is selected:

```text
Damage Type
POTHOLE

Confidence
91.2%

Severity
HIGH

Location
Road Segment 04

Status
UNDER REVIEW

Detected
30 Sep 2026

Model
YOLO-vX.Y
```

Actions:

```text
Confirm
Reject
Correct
Add Note
```

Only authorized users may perform review actions.

---

# 24. Severity Visualization

Severity levels:

```text
LOW
MEDIUM
HIGH
CRITICAL
```

The UI should communicate severity using:

- Label
- Icon where appropriate
- Visual emphasis
- Consistent semantic styling

Severity MUST NOT be represented by color alone.

For example:

```text
HIGH
▲
```

is preferable to relying only on a color.

---

# 25. Map Intelligence

The Map Intelligence page is a major product surface.

It should provide:

- Full-screen map
- Layer controls
- Search
- Filters
- Damage clustering
- Road segments
- Maintenance locations
- Inspection locations
- Detail panel

Conceptual layout:

```text
┌──────────────────────────────────────────────────────────────┐
│ Search / Filters                                             │
├───────────────┬──────────────────────────────────────────────┤
│ Filters        │                                              │
│               │                  MAP                         │
│ Damage Type   │                                              │
│ Severity      │                                              │
│ Status        │                                              │
│ Road          │                                              │
│ Date          │                                              │
│               │                                              │
└───────────────┴──────────────────────────────────────────────┘
```

---

# 26. GIS Layers

Initial layers:

```text
Roads
Road Segments
Damages
Inspections
Maintenance
Repair Evidence
```

Layer visibility should be independently controlled.

The platform uses:

```text
PostGIS
+
Leaflet
+
OpenStreetMap
```

PostGIS is the authoritative geographic data source.

OpenStreetMap is used as the basemap.

---

# 27. Map Interaction

Users should be able to:

- Pan
- Zoom
- Select features
- Filter features
- Open detail panels
- Cluster dense markers
- Navigate from map feature to resource detail

Selecting a damage marker should show:

```text
Damage
↓
Road
↓
Segment
↓
Inspection
↓
Maintenance
↓
Repair
↓
Verification
```

This creates the platform's traceability chain.

---

# 28. Road Health Interface

Road Health should show both current and historical condition.

Example:

```text
Road Health

Current Health
72 / 100

Trend
↘ Declining

Last Updated
30 Sep 2026
```

Supporting factors may include:

- Damage density
- Severity
- Unresolved damage
- Recurrence
- Inspection freshness
- Historical trend
- Maintenance history

The exact scoring formula is governed by the AI/ML and backend specifications.

The UI MUST display the calculated result rather than inventing a separate frontend formula.

---

# 29. Road Health History

Historical health should be visualized using charts.

Example:

```text
Health
100 ┤
 90 ┤──────╮
 80 ┤      ╰────╮
 70 ┤           ╰──────
 60 ┤
    └────────────────────
       Time →
```

Users should be able to:

- Select time range
- Hover for exact values
- Identify significant changes
- View related events

---

# 30. Deterioration Prediction

Prediction pages should clearly distinguish:

```text
Historical Observation
vs
Model Prediction
```

Example:

```text
Segment 004

Predicted deterioration:
HIGH

Prediction horizon:
90 days

Model:
XGBoost v1.2

Generated:
30 Sep 2026
```

The interface MUST NOT present predictions as guaranteed outcomes.

---

# 31. Prediction Explainability

Where supported, the UI should show relevant model features.

Example:

```text
Prediction Factors

Historical damage     ████████
Unresolved damage     ██████
Health trend          ███████
Recurrence             █████
Maintenance history    ███
```

These visualizations MUST correspond to actual model outputs or validated explanatory data.

The UI MUST NOT invent feature importance.

---

# 32. Maintenance Dashboard

The maintenance interface should show:

```text
Open
Assigned
In Progress
Completed
Verification Pending
Verified
Rejected
Cancelled
```

Example board:

```text
OPEN
──────
Job 102
Job 108

ASSIGNED
────────
Job 104

IN PROGRESS
───────────
Job 099

VERIFICATION
────────────
Job 096
```

A table view SHOULD also be available for large datasets.

---

# 33. Maintenance Job Detail

Display:

- Job ID
- Linked road
- Segment
- Linked damage
- Severity
- Maintenance type
- Assigned contractor
- Current status
- Created date
- Due date where available
- Work history
- Repair evidence
- Verification
- Recurrence

The user should be able to follow the entire lifecycle from damage to verified repair.

---

# 34. Repair Evidence

Repair evidence may include:

- Before images
- After images
- Videos where supported
- Notes
- Timestamp
- GPS
- Uploaded by
- Upload status

Evidence should be displayed chronologically.

---

# 35. Repair Verification Interface

The verification page should compare:

```text
Before Repair
        ↓
Maintenance Work
        ↓
After Repair
        ↓
AI Verification
        ↓
Human Review
```

Example:

```text
Repair Verification

AI Result
PASS

Confidence
89%

Evidence
3 images

Human Review
Pending
```

The interface MUST distinguish AI-generated verification from human approval.

---

# 36. Recurrence Interface

Recurrence tracking identifies repeated problems associated with a location/segment.

Display:

- Original damage
- Repair event
- Verification result
- New damage
- Time between events
- Location
- Damage type
- Severity

Example:

```text
Recurring Problem

Road Segment: SEG-004

Initial damage
↓
Repair
↓
Verified
↓
New pothole
↓
Recurrence detected
```

---

# 37. Analytics

Analytics should provide operational insights without overwhelming users.

Initial analytics:

- Damage by type
- Damage by severity
- Damage over time
- Road health trends
- Maintenance completion
- Verification outcomes
- Recurrence
- Inspection activity
- Geographic distribution

Charts should support:

- Tooltips
- Date ranges
- Filters
- Export where authorized

---

# 38. Reports

Reports may include:

- Road condition report
- Damage report
- Maintenance report
- Road health report
- Inspection report
- Repair verification report
- Recurrence report

Reports should be generated asynchronously where processing may take significant time.

The UI should show:

```text
Report
QUEUED
↓
GENERATING
↓
COMPLETED
↓
DOWNLOAD
```

---

# 39. Notifications

Notification center should show:

- New critical damage
- Review required
- Maintenance assignment
- Maintenance completion
- Verification required
- Verification rejection
- Recurrence detected
- Processing failure
- Report completion

Notifications should link directly to the relevant resource.

---

# 40. Global Search

Global search should support relevant resources such as:

```text
Roads
Segments
Inspections
Damages
Maintenance Jobs
Reports
```

Search results should display resource type.

Example:

```text
Search: "Main Road"

ROADS
Main Road

SEGMENTS
Main Road - Segment 04

MAINTENANCE
MJ-104 - Main Road
```

Search MUST respect authorization.

---

# 41. Forms

Forms should follow consistent rules.

Each form should provide:

- Clear labels
- Required-field indicators
- Inline validation
- Helpful error messages
- Loading state
- Disabled submit during processing
- Success feedback
- Server-side validation errors

Client-side validation MUST NOT replace backend validation.

---

# 42. Confirmation Dialogs

Confirmation dialogs should be used for destructive or significant actions.

Examples:

```text
Delete Road?
```

```text
Reject Damage?
```

```text
Assign Maintenance Job?
```

```text
Approve Repair Verification?
```

The dialog should explain the consequence clearly.

Avoid confirmation dialogs for routine low-risk actions.

---

# 43. Loading States

Every asynchronous page or operation MUST have a meaningful loading state.

Use:

- Skeleton loaders
- Progress indicators
- Button loading states
- Map loading indicators
- Processing status indicators

Avoid blank screens.

Example:

```text
Road Details

████████████
██████ ████
████████████
```

Skeletons should resemble the eventual content layout.

---

# 44. Empty States

Empty states should explain what happened and what action is available.

Bad:

```text
No data.
```

Better:

```text
No inspections found

There are no inspections matching the selected filters.

[Clear Filters]
```

For first-use states:

```text
No roads added yet

Add your first road to begin monitoring road condition.

[Add Road]
```

---

# 45. Error States

Errors must be understandable and actionable.

Example:

```text
Unable to load road data

The server could not retrieve the requested information.

Request ID: abc123

[Retry]
```

Do not expose:

- Stack traces
- Database errors
- Secrets
- Internal credentials
- Sensitive infrastructure details

---

# 46. AI Processing States

AI processing should be visible.

Example:

```text
Inspection Processing

Media uploaded       ✓
Preprocessing        ✓
AI detection         ●
Classification       ○
Severity             ○
Completed            ○
```

If processing fails:

```text
AI Analysis Failed

The inspection was uploaded successfully, but AI analysis could not be completed.

[Retry Analysis]
```

---

# 47. Offline/Sync States

Where web functionality interacts with asynchronous/offline-generated data, show clear synchronization state.

Example:

```text
Synced
Pending Sync
Uploading
Processing
Failed
```

The Android application must have richer offline UX as defined in `ANDROID_APP_SPEC.md`.

---

# 48. Responsive Design

The web application MUST support:

- Desktop
- Laptop
- Tablet
- Mobile browser where practical

Primary operational workflows are desktop-first, especially:

- GIS
- Analytics
- Road management
- Maintenance management

Mobile web should prioritize:

- Dashboard overview
- Search
- Notifications
- Basic resource inspection

The dedicated Android application remains the primary field interface.

---

# 49. Accessibility

The interface MUST support:

- Keyboard navigation
- Semantic HTML
- Accessible labels
- Focus states
- Screen-reader-compatible controls
- Sufficient text contrast
- Non-color indicators
- Accessible dialogs
- Accessible form errors

Interactive map features should provide an alternative textual representation where practical.

---

# 50. Color System

The interface should use a consistent semantic color system.

Suggested semantic categories:

```text
Success
Warning
Danger
Info
Neutral
```

Severity should have consistent visual treatment.

Important:

**Color MUST NOT be the only way information is communicated.**

For example:

```text
CRITICAL
!
```

should accompany a visual severity treatment.

---

# 51. Typography

Typography should prioritize readability.

Recommended hierarchy:

```text
Page Title
Section Heading
Card Heading
Body
Supporting Text
Metadata
```

Numbers such as:

- Damage counts
- Health scores
- Maintenance counts
- Prediction values

may use stronger typography to support rapid scanning.

---

# 52. Component System

Reusable UI components SHOULD include:

```text
Button
Input
Select
DatePicker
Dialog
Drawer
Tabs
Badge
Card
Table
Pagination
Dropdown
Toast
Tooltip
Skeleton
EmptyState
ErrorState
StatusIndicator
MetricCard
ChartCard
MapPanel
FilterBar
SearchBar
Timeline
```

Components should be reusable rather than recreated separately for every page.

---

# 53. Animation

Framer Motion may be used for:

- Page transitions
- Panel transitions
- Dialog transitions
- Dashboard card entrance
- Map detail panels
- Loading transitions

Animation MUST:

- Be purposeful
- Be short
- Not block workflows
- Respect reduced-motion preferences

Avoid excessive animation.

---

# 54. Data Visualization Rules

Charts MUST:

- Have clear labels
- Show units where applicable
- Support exact values through tooltips
- Use consistent scales
- Avoid misleading axes
- Distinguish historical and predicted values
- Provide accessible summaries where practical

Do not create a chart merely for decoration.

---

# 55. Tables

Tables should support:

- Sorting
- Pagination
- Filtering
- Search
- Row actions
- Responsive behavior
- Loading states
- Empty states

Large datasets MUST use pagination or another controlled data-loading mechanism.

---

# 56. Detail Drawers

For map and list workflows, detail drawers may be used to avoid constant page navigation.

Example:

```text
Map
       ┌───────────────────────────┐
       │ Damage Details            │
       │                           │
       │ Pothole                   │
       │ HIGH                      │
       │ Segment 004               │
       │                           │
       │ [View Full Details]       │
       └───────────────────────────┘
```

Drawers should not hide critical information permanently.

---

# 57. Role-Aware UI

The UI should dynamically adapt to user permissions.

Example:

```text
Authority:
[Create Maintenance]

Inspector:
[Create Inspection]

Contractor:
[Upload Repair Evidence]
```

Unauthorized actions should generally not be presented as active controls.

However, the backend remains responsible for enforcing permissions.

---

# 58. Audit Visibility

Authorized users should be able to see relevant audit/history information.

Example:

```text
30 Sep 10:42
Damage confirmed
by Divyesh

30 Sep 11:08
Maintenance created
by Authority User

02 Oct 15:21
Repair evidence uploaded
by Contractor

03 Oct 09:14
Verification completed
by Authority User
```

This improves traceability.

---

# 59. Data Freshness

The interface should communicate when information was last updated.

Examples:

```text
Updated 2 minutes ago
```

```text
Last inspection:
30 Sep 2026, 10:42 AM
```

Real-time updates SHOULD NOT be simulated.

If polling or refresh is used, it must reflect actual backend behavior.

---

# 60. Performance UX

The interface should avoid blocking the user unnecessarily.

Use:

- Skeleton loading
- Optimistic updates only where safe
- Pagination
- Lazy loading
- Image thumbnails
- Progressive media loading
- Map clustering
- Virtualized large lists where required

AI processing and report generation MUST remain asynchronous.

---

# 61. Media UX

Images and videos should use:

- Thumbnail previews
- Lazy loading
- Full-resolution viewer
- Zoom where appropriate
- Metadata panel
- Upload progress
- Processing status

Large media MUST NOT be unnecessarily loaded at full resolution.

---

# 62. Security UX

The UI must not expose:

- Access tokens
- API keys
- Database credentials
- Internal service credentials
- Private storage credentials

Signed media URLs should be handled securely.

Sensitive actions should communicate their consequences clearly.

---

# 63. Authentication Screens

Required screens:

```text
Login
Forgot Password
Reset Password
Change Password
Organization Selection
Profile
```

Where registration is enabled:

```text
Register
Email Verification
```

Authentication UI must reflect the actual backend authentication flow.

---

# 64. Administration Screens

Authorized administrators may access:

```text
Organization Settings
Members
Roles
System Configuration
Audit Logs
```

Administration screens should clearly distinguish configuration changes from operational actions.

---

# 65. Profile

Profile should show:

- Name
- Email
- Organization
- Role
- Account status
- Last login where available
- Password/security controls

The user should not be able to arbitrarily change their organization role.

---

# 66. UX Traceability

Every major operational action should allow users to navigate through the lifecycle.

Example:

```text
Damage
  ↓
Inspection
  ↓
Road Segment
  ↓
Maintenance
  ↓
Repair Evidence
  ↓
Verification
  ↓
Recurrence
```

This traceability is a central product feature, not merely a database relationship.

---

# 67. Error Recovery

Where possible, errors should provide a recovery action.

Examples:

```text
Processing failed
→ Retry

Upload failed
→ Retry upload

Report generation failed
→ Generate again

Network unavailable
→ Retry / continue where offline workflow supports it
```

The UI MUST NOT claim an operation succeeded unless the backend confirms success.

---

# 68. Notifications UX

Unread notifications should be visually distinguishable.

Each notification should provide:

- Title
- Short description
- Timestamp
- Resource reference
- Read/unread state

Example:

```text
Critical pothole detected

Main Road · Segment 04

10 minutes ago

[View Damage]
```

---

# 69. Search and Filter Persistence

Where useful, filters should remain active during navigation within the same workflow.

Example:

```text
Damage
Filter: HIGH
↓
Open damage
↓
Return
↓
HIGH filter remains
```

The implementation must avoid confusing stale filters after organization changes.

---

# 70. Design Consistency Rules

All screens MUST follow:

- Same spacing system
- Same typography hierarchy
- Same button semantics
- Same status terminology
- Same severity terminology
- Same date/time formatting
- Same error patterns
- Same loading patterns
- Same empty-state patterns

The UI should not introduce alternate terminology for backend states.

For example, use:

```text
VERIFICATION_PENDING
```

consistently rather than switching between:

```text
Awaiting Verification
Pending Check
Verification Needed
```

unless a deliberate presentation label is documented.

---

# 71. Date, Time & Location

The system stores timestamps in UTC.

The UI should display dates/times in the user's configured/local timezone where appropriate.

Locations should clearly communicate:

- Latitude
- Longitude where necessary
- Road
- Segment
- Geographic area

Map coordinates should use the approved GIS representation.

---

# 72. Frontend Architecture Rules

The UI implementation should follow the architecture defined in `SYSTEM_ARCHITECTURE.md`.

Recommended feature structure:

```text
features/
├── auth/
├── dashboard/
├── roads/
├── inspections/
├── damages/
├── map/
├── health/
├── predictions/
├── maintenance/
├── verification/
├── recurrence/
├── analytics/
├── reports/
├── notifications/
└── administration/
```

Shared UI components belong in the shared component system.

Business logic should not be duplicated across pages.

---

# 73. API Integration Rules

Frontend components MUST use the centralized API client.

They MUST NOT:

- Hardcode API URLs throughout components
- Directly access PostgreSQL
- Expose Supabase service-role credentials
- Duplicate authentication logic
- Invent response formats
- Assume operations succeeded without server confirmation

API behavior must follow `API_SPECIFICATION.md`.

---

# 74. Demo / Seed Data

If a demo environment exists, demo data must be explicitly identifiable as demo/seed data.

Production UI MUST NOT silently mix fake data with real operational data.

The UI should not fabricate:

- AI detections
- Road health scores
- Predictions
- Maintenance jobs
- Repair verification
- Analytics

---

# 75. UI Testing Requirements

The frontend MUST include tests for:

### Component Tests

- Buttons
- Forms
- Dialogs
- Tables
- Status indicators
- Filters
- Loading states
- Error states

### Integration Tests

- Login
- Dashboard loading
- Road navigation
- Damage review
- Maintenance workflow
- Report generation

### End-to-End Tests

At minimum:

```text
Login
→ Dashboard
→ Road
→ Inspection
→ Damage Review
→ Maintenance
→ Repair Verification
```

Tests MUST also cover unauthorized states.

---

# 76. Coding-Agent Rules

Coding agents implementing UI MUST:

1. Read all parent documentation before changing architecture.
2. Follow approved navigation.
3. Reuse existing components.
4. Avoid duplicate business logic.
5. Use real API contracts.
6. Never fabricate backend data.
7. Preserve permission rules.
8. Preserve loading/error/empty states.
9. Follow responsive design rules.
10. Follow accessibility requirements.
11. Keep animation purposeful.
12. Never expose secrets.
13. Update documentation when UI architecture changes.
14. Test important workflows.
15. Avoid introducing new frameworks without approval.

---

# 77. Definition of Done

A UI feature is complete only when:

- [ ] Design matches the approved UX specification.
- [ ] Correct navigation exists.
- [ ] Correct permissions are enforced.
- [ ] API integration uses approved contracts.
- [ ] Loading state exists.
- [ ] Empty state exists.
- [ ] Error state exists.
- [ ] Success state exists where applicable.
- [ ] Responsive behavior is implemented.
- [ ] Accessibility is considered.
- [ ] Backend-confirmed state is displayed.
- [ ] No fake functionality exists.
- [ ] Tests are implemented.
- [ ] No secrets are exposed.
- [ ] Documentation is updated if architecture changes.

---

# 78. Final UX Architecture

The canonical web experience is:

```text
APPLICATION SHELL
        ↓
DASHBOARD
        ↓
ROAD / SEGMENT INTELLIGENCE
        ↓
INSPECTION
        ↓
AI DAMAGE REVIEW
        ↓
GIS / MAP INTELLIGENCE
        ↓
ROAD HEALTH
        ↓
DETERIORATION PREDICTION
        ↓
MAINTENANCE
        ↓
REPAIR EVIDENCE
        ↓
REPAIR VERIFICATION
        ↓
RECURRENCE
        ↓
ANALYTICS / REPORTS
```

The interface must make the complete operational chain understandable:

```text
WHO
→ WHAT
→ WHERE
→ WHEN
→ AI RESULT
→ HUMAN REVIEW
→ MAINTENANCE
→ REPAIR
→ VERIFICATION
→ RECURRENCE
```

The core UX principle is:

> **Every important road-condition observation should be understandable, traceable, actionable, and verifiable.**

This document is the canonical UI/UX source of truth for the platform.