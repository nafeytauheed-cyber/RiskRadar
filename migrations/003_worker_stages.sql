ALTER TABLE jobs ADD COLUMN phase text NOT NULL DEFAULT 'features' CHECK(phase IN ('features','inference'));
ALTER TABLE jobs ADD COLUMN prepared jsonb;
INSERT INTO schema_migrations(version) VALUES (3);
