# Google Sign-In Button

The `/signin` button uses Google's official HTML button configurator output,
not a hand-drawn logo or a Google Identity Services SDK-rendered button.
Authentication continues through the existing Supabase `signInWithOAuth` flow.

Source (retrieved 2026-09-27):

- https://developers.google.com/identity/branding-guidelines
- Official HTML configurator, standard / light / rectangular / left-aligned logo.
- The SVG paths and their brand colors are copied unchanged from that configurator.
- Google Developers code samples are licensed under Apache 2.0, as stated on the source page.

Local adaptations: Japanese label, existing button ID and OAuth handler,
decorative elements hidden from assistive technology, a visible keyboard focus
outline, responsive width capped at 400px, and zero letter spacing to match the
site's typography. The 40px height, 20px logo, 12px button padding, 10px logo gap,
border, colors and interaction states follow the official snippet. Roboto is
loaded from Google Fonts with a system fallback.

Regression checks: `node scripts/test_signin.cjs` covers button markup, official
colors, OAuth return URL, disabled/error recovery and existing email/session flows.
