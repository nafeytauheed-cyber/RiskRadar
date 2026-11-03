ALTER TABLE replay_runs ADD UNIQUE(tenant_id,run_id);
ALTER TABLE replay_runs ADD COLUMN status text NOT NULL DEFAULT 'complete'
    CHECK(status IN ('ready','running','complete','cancelled','failed'));
ALTER TABLE replay_runs ADD COLUMN processed bigint NOT NULL DEFAULT 0 CHECK(processed>=0);
ALTER TABLE replay_runs ADD COLUMN total bigint NOT NULL DEFAULT 0 CHECK(total>=0);
ALTER TABLE replay_runs ADD COLUMN lease_token bigint NOT NULL DEFAULT 0;
ALTER TABLE replay_runs ADD COLUMN lease_until timestamptz;
ALTER TABLE replay_runs ADD COLUMN error text;
CREATE TABLE replay_inputs(
    tenant_id text NOT NULL,
    run_id text NOT NULL,
    ordinal bigint NOT NULL CHECK(ordinal>0),
    event_id text NOT NULL,
    PRIMARY KEY(tenant_id,run_id,ordinal),
    UNIQUE(tenant_id,run_id,event_id),
    FOREIGN KEY(tenant_id,run_id) REFERENCES replay_runs(tenant_id,run_id),
    FOREIGN KEY(tenant_id,event_id) REFERENCES events(tenant_id,event_id)
);
CREATE TRIGGER replay_inputs_immutable BEFORE UPDATE OR DELETE ON replay_inputs
    FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();
CREATE INDEX replay_prediction_pages ON predictions(tenant_id,scope,prediction_id);
INSERT INTO schema_migrations(version) VALUES (4);
CREATE FUNCTION protect_replay_identity() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    IF NEW.manifest IS DISTINCT FROM OLD.manifest OR NEW.mode<>OLD.mode
       OR NEW.tenant_id<>OLD.tenant_id OR NEW.run_id<>OLD.run_id
       OR NEW.total<>OLD.total THEN
        RAISE EXCEPTION 'pinned replay identity is immutable';
    END IF;
    RETURN NEW;
END;
$$;
CREATE TRIGGER replay_identity_immutable BEFORE UPDATE ON replay_runs
    FOR EACH ROW EXECUTE FUNCTION protect_replay_identity();
