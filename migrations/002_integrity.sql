-- Cross-tenant constraints even if an application query is accidentally wrong.
ALTER TABLE predictions ADD UNIQUE(tenant_id,prediction_id);
ALTER TABLE incidents ADD UNIQUE(tenant_id,incident_id);
ALTER TABLE incidents ADD FOREIGN KEY(tenant_id,opened_prediction) REFERENCES predictions(tenant_id,prediction_id);
ALTER TABLE evidence ADD FOREIGN KEY(tenant_id,prediction_id) REFERENCES predictions(tenant_id,prediction_id);
ALTER TABLE incident_transitions ADD FOREIGN KEY(tenant_id,incident_id) REFERENCES incidents(tenant_id,incident_id);
CREATE FUNCTION reject_immutable_change() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'append-only data: update/delete forbidden'; END;
$$;
CREATE TRIGGER events_immutable BEFORE UPDATE OR DELETE ON events FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();
CREATE TRIGGER models_immutable BEFORE UPDATE OR DELETE ON model_versions FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();
CREATE TRIGGER predictions_immutable BEFORE UPDATE OR DELETE ON predictions FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();
CREATE TRIGGER snapshots_immutable BEFORE UPDATE OR DELETE ON feature_snapshots FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();
CREATE TRIGGER audit_immutable BEFORE UPDATE OR DELETE ON audit_events FOR EACH ROW EXECUTE FUNCTION reject_immutable_change();
INSERT INTO schema_migrations(version) VALUES (2);
