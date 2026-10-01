# React + TypeScript + Vite

## Live Results Setup

The public site reads settled play records through the restricted Supabase
`public.public_settled_results()` RPC. It returns only posted, settled plays
and fields needed for the public ledger and capper summaries. Open plays,
Discord IDs, message IDs, and account data are not exposed.

1. In Supabase Dashboard, open **SQL Editor** and run
   `supabase/migrations/20260930230000_public_settled_results.sql` from the
   repository root.
2. Run `supabase/migrations/20260930240000_public_capper_avatars.sql` to add
   public avatar support to capper pages.
3. Copy `web/.env.example` to `web/.env.local`; set the project URL and public
  anon/publishable key from **Project Settings → API**.
4. Restart Vite after changing local environment variables.

The public key is intended for browser use. Never put the bot's `service_role`
key in a `VITE_*` variable, website setting, or frontend source. The SQL
function grants anonymous access only to the restricted settled-results query.

## Brand Logo

The brand mark is stored at
`website-assets/brand/playmaker-logo-512.webp` in the dedicated public Supabase
Storage bucket. The existing `Media` bucket remains private. The site uses the
public logo URL by default and falls back to the optimized local WebP in
`web/public/playmaker-logo.webp` if storage is unavailable. Apply
`supabase/migrations/20260930250000_website_assets_bucket.sql` when setting up a
new Supabase project.

## Capper Pages

Each capper has a URL at `/cappers/<slug>` with their settled record, cumulative
net-unit graph, sport-by-sport net graph, and full results ledger. To show a
capper's own image instead of the generated initials avatar, set their approved
HTTPS image URL in `public.users.public_avatar_url`. Only this dedicated avatar
field is returned by the public results function.

For AWS Amplify, add `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` as
environment variables. These values are public in the browser build; data
access remains restricted by the RPC and its grants. In **Hosting → Rewrites
and redirects**, add a rewrite from `/<*>` to `/index.html` with status `200`
so direct visits and bookmarks to capper pages load the SPA.

## Member Accounts

1. Run `supabase/migrations/20260930270000_member_accounts_favorites.sql` in
  Supabase SQL Editor.
2. In Supabase **Authentication → Providers**, enable Discord and enter the
  Discord application's client ID and newly rotated client secret.
3. Copy the Supabase Discord callback URL shown for the provider (typically
  `https://<project-ref>.supabase.co/auth/v1/callback`) into Discord Developer
  Portal → OAuth2 → Redirects. Do not use the website's `/OauthURI/redirect`
  path as the provider callback.
4. In Supabase **Authentication → URL Configuration**, set the production Site
  URL to `https://playmakersportsanalytics.com` and allow the production and
  local `/account` redirect URLs.

The account page signs members in with Discord. It sends date of birth to the
`verify_member_age` database function, which checks the 21+ threshold and saves
only a verification timestamp; it does not store the birth date. Favorites are
available only after verification and are restricted to the signed-in user by
row-level security. This is self-attested age verification, not an identity or
document verification service.

## NFL API-Sports Feed

1. Run `supabase/migrations/20260930260000_api_sports_nfl.sql` in Supabase SQL
  Editor. It creates private cache tables and public read-only RPCs.
2. Add `API_SPORTS_KEY` to the Proxmox bot's `/opt/discord-bot/.env`. Keep this
  key server-side; never add it to Amplify or a `VITE_*` variable.
3. Deploy/restart the bot. It performs an initial sync, then a daily sync at
  6:10 AM Eastern for the full-season schedule, standings, and teams: three
  API requests per successful daily sync.
4. During cached game windows only, the bot checks scores every 15 minutes with
  one date-scoped request. Outside those windows it makes no live-score calls.

The website reads `public_nfl_games`, `public_nfl_standings`, and
`public_nfl_data_status` from Supabase. It never calls API-Sports directly.

This template provides a minimal setup to get React working in Vite with HMR and some ESLint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the ESLint configuration

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...

      // Remove tseslint.configs.recommended and replace with this
      tseslint.configs.recommendedTypeChecked,
      // Alternatively, use this for stricter rules
      tseslint.configs.strictTypeChecked,
      // Optionally, add this for stylistic rules
      tseslint.configs.stylisticTypeChecked,

      // Other configs...
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])

```

You can also install [eslint-plugin-react-x](https://npmx.dev/package/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://npmx.dev/package/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default defineConfig([
  globalIgnores(['dist']),
  {
    files: ['**/*.{ts,tsx}'],
    extends: [
      // Other configs...
      // Enable lint rules for React
      reactX.configs['recommended-typescript'],
      // Enable lint rules for React DOM
      reactDom.configs.recommended,
    ],
    languageOptions: {
      parserOptions: {
        project: ['./tsconfig.node.json', './tsconfig.app.json'],
        tsconfigRootDir: import.meta.dirname,
      },
      // other options...
    },
  },
])

```
