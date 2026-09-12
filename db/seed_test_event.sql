-- ============================================================================
-- Seed a FAKE Stripe changelog event — for the Phase 1 end-to-end test only.
-- ============================================================================
-- Usage: run this in the Supabase SQL editor AFTER you have scanned a repo that
-- contains a Stripe `Charge` usage (the sample below references "Charge" and
-- "source" so it matches a detection whose snippet contains `stripe.Charge.`).
--
-- Then POST /internal/alerts/process (or run the cron) to generate + email the
-- alert. `processed_at` is left NULL on purpose so the processor picks it up.
--
-- The content_hash is a fixed sentinel so re-running this file is a no-op
-- (ON CONFLICT DO NOTHING) rather than creating duplicates.
-- ============================================================================

insert into changelog_events
  (api_name, change_type, old_value, new_value, description, source_url, content_hash, symbols, processed_at)
values
  (
    'stripe',
    'field_removed',
    'Charge.source',
    null,
    'The `source` property on the Charge object is being removed. Use the `payment_method` and `payment_method_details` properties instead. Update any code that reads `charge.source`.',
    'https://docs.stripe.com/changelog',
    'seed-fake-e2e-charge-source-removed-v1',
    'charge,source',
    null
  )
on conflict (api_name, content_hash) do nothing;

-- Inspect what got inserted:
-- select id, change_type, old_value, new_value, symbols, processed_at from changelog_events order by detected_at desc;
