CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS locations (
    id BIGSERIAL PRIMARY KEY,
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    title VARCHAR(180) NOT NULL,
    geom geometry(Point, 4326) NOT NULL
);

CREATE TABLE IF NOT EXISTS points_of_interest (
    location_id BIGINT PRIMARY KEY REFERENCES locations(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'unsorted',
    category VARCHAR(64) NOT NULL DEFAULT 'other',
    subcategory VARCHAR(64) NOT NULL DEFAULT 'other',
    rating VARCHAR(16) NOT NULL DEFAULT 'unrated',
    accessibility VARCHAR(32) NOT NULL DEFAULT 'unknown',
    CONSTRAINT points_of_interest_status_check
        CHECK (status IN ('unsorted', 'unverified', 'functional', 'nonfunctional', 'documented', 'visited', 'vanished')),
    CONSTRAINT points_of_interest_category_check
        CHECK (category IN ('residential', 'industrial', 'public', 'commercial', 'military', 'other')),
    CONSTRAINT points_of_interest_subcategory_check
        CHECK (subcategory IN (
            'family_house', 'villa', 'apartment_building', 'recreational_building', 'historical_residence',
            'other_residential', 'manufacturing', 'energy', 'chemical', 'mining', 'storage', 'agriculture',
            'other_industrial', 'healthcare', 'education', 'sacral', 'public_administration', 'culture_sport',
            'transport', 'other_public', 'accommodation', 'gastronomy', 'retail', 'services', 'administration',
            'other_commercial', 'barracks_accommodation', 'military_storage', 'technical_facilities',
            'defensive_structure', 'other_military', 'other'
        )),
    CONSTRAINT points_of_interest_category_subcategory_check
        CHECK (
            (category = 'residential' AND subcategory IN ('family_house', 'villa', 'apartment_building', 'recreational_building', 'historical_residence', 'other_residential'))
            OR (category = 'industrial' AND subcategory IN ('manufacturing', 'energy', 'chemical', 'mining', 'storage', 'agriculture', 'other_industrial'))
            OR (category = 'public' AND subcategory IN ('healthcare', 'education', 'sacral', 'public_administration', 'culture_sport', 'transport', 'other_public'))
            OR (category = 'commercial' AND subcategory IN ('accommodation', 'gastronomy', 'retail', 'services', 'administration', 'other_commercial'))
            OR (category = 'military' AND subcategory IN ('barracks_accommodation', 'military_storage', 'technical_facilities', 'defensive_structure', 'other_military'))
            OR (category = 'other' AND subcategory = 'other')
        ),
    CONSTRAINT points_of_interest_rating_check
        CHECK (rating IN ('unrated', '1', '2', '3', '4', '5')),
    CONSTRAINT points_of_interest_accessibility_check
        CHECK (accessibility IN ('unknown', 'freely_accessible', 'by_arrangement', 'inaccessible'))
);

CREATE TABLE IF NOT EXISTS location_photos (
    id BIGSERIAL PRIMARY KEY,
    location_id BIGINT NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    file_path TEXT NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS favorite_locations (
    user_id BIGINT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    location_id BIGINT NOT NULL REFERENCES locations(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, location_id)
);

CREATE INDEX IF NOT EXISTS idx_locations_user_id ON locations(user_id);
CREATE INDEX IF NOT EXISTS idx_locations_geom ON locations USING gist (geom);
CREATE INDEX IF NOT EXISTS idx_location_photos_location_id ON location_photos(location_id);
CREATE INDEX IF NOT EXISTS idx_favorite_locations_location_id ON favorite_locations(location_id);
