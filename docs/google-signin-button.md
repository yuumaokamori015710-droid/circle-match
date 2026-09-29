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
outline, full width inside the centered single-column login form, a 52px touch
target, and zero letter spacing to match the site's typography. The 20px logo,
12px button padding, 10px logo gap, border, colors and interaction states follow
the official snippet. Roboto is
loaded from Google Fonts with a system fallback.

The introduction stays above the login methods at every viewport width; email
and Google controls have the same width. The email input uses 16px text to avoid
focus zoom on iPhone. Authentication and callback handling are unchanged.

Regression checks: `node scripts/test_signin.cjs` covers button markup, official
colors, OAuth return URL, disabled/error recovery and existing email/session flows.
