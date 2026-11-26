# Supabase schema and migration workflow

## What is included

- `migrations/20261112013753_...sql` through `20261116020253_...sql`: migration-ledger markers recovered from the connected project. The ZIP did not contain the original SQL bodies, so these markers are intentionally no-op.
- `migrations/20261117000000_rebuild_current_public_schema.sql`: idempotent snapshot of the current 19-table `public` schema, its indexes, RLS policies, functions and triggers. It does not drop tables or delete application data.
- `seed.sql`: canonical survey questions/options and the six-axis trait model. It can be re-run safely.

The remote project's migration ledger contained eight versions through `20261116020253`. The original SQL text for those historical versions was not available in the supplied ZIP or through the migration-list API. The current schema snapshot is therefore the reproducible source of truth for a fresh local database; the marker files preserve version ordering but do not pretend to reconstruct the unavailable historical diffs.

## Fresh local database

From the project root (requires Docker and Supabase CLI):

```powershell
supabase start
supabase db reset
```

`db reset` applies the migration snapshot and then `seed.sql`.

## Link and deploy to the existing remote project

Do not run `supabase db reset` against production. First link the local project:

```powershell
supabase login
supabase link --project-ref fppojuzgnyolrzwhisbn
supabase migration list
```

Confirm that the eight historical versions are shown as applied remotely and that only `20261117000000` is pending. Then deploy the additive snapshot and seed:

```powershell
supabase db push --include-seed
```

The snapshot uses `IF NOT EXISTS`, recreates only the known deny-direct-client-access policies and trigger definitions, and preserves existing rows. Review the SQL before deploying in any environment you care about.

## Trait model refresh

After applying the schema and seed, the six `taste_traits`, `survey_options`, `option_trait_scores`, and `game_trait_tag_rules` tables are populated. The backend writes `survey_trait_scores` when a session is completed and refreshes `game_trait_scores` when games are synced. To refresh existing game rows after changing tag rules, run:

```powershell
python -m scripts.seed_trait_model
```

This script uses the server-side `SUPABASE_SERVICE_KEY` from `.env`; never expose that key in frontend code.
