\set ON_ERROR_STOP on
\timing on

-- Vstupní data -------------------------------------------------------------
-- Před spuštěním seedu pro jiného testovacího uživatele nebo běh uprav tyto hodnoty.
\set target_email example@example.com
\set total_locations 20000
\set batch_size 500
\set sleep_seconds 0.15
\set run_prefix LOADTEST

SELECT
  :'run_prefix'
  || ' '
  || to_char(clock_timestamp(), 'YYYYMMDDHH24MISS')
  || '-'
  || substr(md5(random()::text), 1, 8) AS run_id
\gset

\echo Starting load test seed for :target_email
\echo Run marker: :run_id

CREATE TEMP TABLE _loadtest_config ON COMMIT PRESERVE ROWS AS
SELECT
  id AS user_id,
  :'target_email'::text AS target_email,
  :'run_id'::text AS run_id,
  :total_locations::int AS total_locations,
  :batch_size::int AS batch_size,
  :sleep_seconds::numeric AS sleep_seconds
FROM users
WHERE email = :'target_email';

SELECT
  1 / count(*) AS target_user_must_exist,
  min(user_id) AS target_user_id
FROM _loadtest_config;

CREATE TEMP TABLE _loadtest_category_subcategories (
  category text NOT NULL,
  subcategory text NOT NULL
) ON COMMIT PRESERVE ROWS;

INSERT INTO _loadtest_category_subcategories (category, subcategory)
VALUES
  ('residential', 'family_house'),
  ('residential', 'villa'),
  ('residential', 'apartment_building'),
  ('residential', 'recreational_building'),
  ('residential', 'historical_residence'),
  ('residential', 'other_residential'),
  ('industrial', 'manufacturing'),
  ('industrial', 'energy'),
  ('industrial', 'chemical'),
  ('industrial', 'mining'),
  ('industrial', 'storage'),
  ('industrial', 'agriculture'),
  ('industrial', 'other_industrial'),
  ('public', 'healthcare'),
  ('public', 'education'),
  ('public', 'sacral'),
  ('public', 'public_administration'),
  ('public', 'culture_sport'),
  ('public', 'transport'),
  ('public', 'other_public'),
  ('commercial', 'accommodation'),
  ('commercial', 'gastronomy'),
  ('commercial', 'retail'),
  ('commercial', 'services'),
  ('commercial', 'administration'),
  ('commercial', 'other_commercial'),
  ('military', 'barracks_accommodation'),
  ('military', 'military_storage'),
  ('military', 'technical_facilities'),
  ('military', 'defensive_structure'),
  ('military', 'other_military'),
  ('other', 'other');

CREATE TEMP TABLE _loadtest_statuses (status text NOT NULL) ON COMMIT PRESERVE ROWS;
INSERT INTO _loadtest_statuses (status)
VALUES
  ('unsorted'),
  ('unverified'),
  ('functional'),
  ('nonfunctional'),
  ('documented'),
  ('visited'),
  ('vanished');

CREATE TEMP TABLE _loadtest_ratings (rating text NOT NULL) ON COMMIT PRESERVE ROWS;
INSERT INTO _loadtest_ratings (rating)
VALUES
  ('unrated'),
  ('1'),
  ('2'),
  ('3'),
  ('4'),
  ('5');

CREATE TEMP TABLE _loadtest_icon_variants ON COMMIT PRESERVE ROWS AS
SELECT
  row_number() OVER (
    ORDER BY
      s.status,
      r.rating,
      cs.category,
      cs.subcategory,
      f.is_favorite
  )::int AS ordinal,
  s.status,
  cs.category,
  cs.subcategory,
  r.rating,
  f.is_favorite
FROM _loadtest_statuses s
CROSS JOIN _loadtest_ratings r
CROSS JOIN _loadtest_category_subcategories cs
CROSS JOIN (VALUES (false), (true)) AS f(is_favorite);

WITH cfg AS (
  SELECT
    total_locations,
    batch_size,
    ceil(total_locations::numeric / batch_size)::int AS batch_count,
    sleep_seconds
  FROM _loadtest_config
),
batches AS (
  SELECT
    batch_no,
    cfg.batch_count,
    (batch_no - 1) * cfg.batch_size AS batch_offset,
    least(cfg.batch_size, cfg.total_locations - ((batch_no - 1) * cfg.batch_size)) AS rows_in_batch,
    cfg.sleep_seconds
  FROM cfg
  CROSS JOIN generate_series(1, cfg.batch_count) AS batch_no
)
SELECT format(
$batch$
SELECT 'LOADTEST batch %1$s/%2$s inserting rows %3$s-%4$s' AS loadtest_progress;
BEGIN;
WITH
cfg AS (
  SELECT * FROM _loadtest_config
),
variant_count AS (
  SELECT count(*)::int AS value FROM _loadtest_icon_variants
),
generated AS (
  SELECT
    (%5$s + gs) AS seq,
    cfg.run_id || ' #' || lpad((%5$s + gs)::text, 5, '0') AS title,
    12.09 + (random() * (18.86 - 12.09)) AS longitude,
    48.55 + (random() * (51.06 - 48.55)) AS latitude,
    v.status,
    v.category,
    v.subcategory,
    v.rating,
    (ARRAY['unknown', 'freely_accessible', 'by_arrangement', 'inaccessible'])[
      (((%5$s + gs - 1) %% 4) + 1)
    ] AS accessibility,
    v.is_favorite
  FROM cfg
  CROSS JOIN generate_series(1, %6$s) AS gs
  CROSS JOIN variant_count vc
  JOIN _loadtest_icon_variants v
    ON v.ordinal = (((%5$s + gs - 1) %% vc.value) + 1)
),
inserted_locations AS (
  INSERT INTO locations (user_id, title, geom)
  SELECT
    cfg.user_id,
    generated.title,
    ST_SetSRID(ST_MakePoint(generated.longitude, generated.latitude), 4326)
  FROM generated
  CROSS JOIN cfg
  RETURNING id, title
),
inserted_poi AS (
  INSERT INTO points_of_interest (
    location_id,
    status,
    category,
    subcategory,
    rating,
    accessibility
  )
  SELECT
    inserted_locations.id,
    generated.status,
    generated.category,
    generated.subcategory,
    generated.rating,
    generated.accessibility
  FROM inserted_locations
  JOIN generated USING (title)
  RETURNING location_id
)
INSERT INTO favorite_locations (user_id, location_id)
SELECT
  cfg.user_id,
  inserted_locations.id
FROM inserted_locations
JOIN generated USING (title)
CROSS JOIN cfg
WHERE generated.is_favorite
ON CONFLICT (user_id, location_id) DO NOTHING;
COMMIT;
SELECT 'LOADTEST batch %1$s/%2$s committed' AS loadtest_progress;
SELECT pg_sleep(%7$s);
$batch$,
  batch_no,
  batch_count,
  batch_offset + 1,
  batch_offset + rows_in_batch,
  batch_offset,
  rows_in_batch,
  sleep_seconds
)
FROM batches
ORDER BY batch_no
\gexec

\echo Import complete. Save this run marker:
\echo :run_id
