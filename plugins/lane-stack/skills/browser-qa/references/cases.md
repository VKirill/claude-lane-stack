# Cases `<slug>`

Source: SPEC.md / acceptance / PM bullets.
Surface for this agent is `browser-ui`. Other surfaces → L0/L1, not this skill.

## TC-001 Example checkout button
- Surface: browser-ui
- Priority: high
- Viewport: 375, 1280
- Preconditions: logged-out local app
- Steps: open `/pricing`; click `Get started`
- Expected: `/signup` renders an enabled primary button
