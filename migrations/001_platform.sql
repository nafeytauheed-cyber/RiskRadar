CREATE TABLE IF NOT EXISTS schema_migrations(version integer PRIMARY KEY, applied_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE tenants(tenant_id text PRIMARY KEY, active_model text);
CREATE TABLE api_keys(key_hash text PRIMARY KEY, tenant_id text NOT NULL REFERENCES tenants, role text NOT NULL CHECK(role IN ('reader','operator','admin','device')), equipment_id text);
CREATE TABLE equipment(tenant_id text NOT NULL REFERENCES tenants, equipment_id text NOT NULL, lifecycle_id text NOT NULL, lease_token bigint NOT NULL DEFAULT 0, lease_until timestamptz, PRIMARY KEY(tenant_id,equipment_id));
CREATE TABLE model_versions(model_id text PRIMARY KEY, artifact jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
ALTER TABLE tenants ADD FOREIGN KEY(active_model) REFERENCES model_versions(model_id);
CREATE TABLE events(
 id bigserial UNIQUE NOT NULL, tenant_id text NOT NULL, event_id text NOT NULL, equipment_id text NOT NULL,
 lifecycle_id text NOT NULL, session_id text NOT NULL, sequence bigint NOT NULL CHECK(sequence>=0), cycle bigint NOT NULL CHECK(cycle>=0),
 observed_at timestamptz NOT NULL, received_at timestamptz NOT NULL DEFAULT clock_timestamp(), schema_version integer NOT NULL CHECK(schema_version=1),
 payload jsonb NOT NULL, payload_hash text NOT NULL,
 PRIMARY KEY(tenant_id,event_id), FOREIGN KEY(tenant_id,equipment_id) REFERENCES equipment,
 UNIQUE(tenant_id,equipment_id,lifecycle_id,session_id,sequence), UNIQUE(tenant_id,equipment_id,lifecycle_id,session_id,cycle));
CREATE INDEX events_observation ON events(tenant_id,equipment_id,observed_at,received_at);
CREATE TABLE jobs(job_id bigserial PRIMARY KEY,tenant_id text NOT NULL,event_id text NOT NULL,equipment_id text NOT NULL,
 status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','leased','done','dead')), attempts integer NOT NULL DEFAULT 0,
 token bigint, lease_until timestamptz, available_at timestamptz NOT NULL DEFAULT now(), error text,
 UNIQUE(tenant_id,event_id), FOREIGN KEY(tenant_id,event_id) REFERENCES events, FOREIGN KEY(tenant_id,equipment_id) REFERENCES equipment);
CREATE INDEX jobs_ready ON jobs(status,available_at,job_id);
CREATE TABLE processing_state(tenant_id text NOT NULL,equipment_id text NOT NULL, latest_event_id text, latest_cycle bigint, lifecycle_id text, session_id text, last_observed_at timestamptz, high_streak integer NOT NULL DEFAULT 0, low_streak integer NOT NULL DEFAULT 0, version bigint NOT NULL DEFAULT 0, PRIMARY KEY(tenant_id,equipment_id), FOREIGN KEY(tenant_id,equipment_id) REFERENCES equipment);
CREATE TABLE replay_runs(run_id text PRIMARY KEY,tenant_id text NOT NULL REFERENCES tenants,mode text NOT NULL CHECK(mode IN ('arrival','corrected')),manifest jsonb NOT NULL, created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE feature_snapshots(snapshot_id text NOT NULL,tenant_id text NOT NULL REFERENCES tenants,content jsonb NOT NULL,PRIMARY KEY(tenant_id,snapshot_id));
CREATE TABLE predictions(prediction_id bigserial PRIMARY KEY,tenant_id text NOT NULL,event_id text NOT NULL,revision integer NOT NULL CHECK(revision>=0),scope text NOT NULL DEFAULT 'live',model_id text NOT NULL REFERENCES model_versions,snapshot_id text NOT NULL,output jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),UNIQUE(tenant_id,event_id,scope,model_id,revision),FOREIGN KEY(tenant_id,event_id) REFERENCES events,FOREIGN KEY(tenant_id,snapshot_id) REFERENCES feature_snapshots);
CREATE INDEX predictions_equipment_lookup ON predictions(tenant_id,event_id,scope,revision DESC);
CREATE TABLE incidents(incident_id bigserial PRIMARY KEY,tenant_id text NOT NULL,equipment_id text NOT NULL,status text NOT NULL CHECK(status IN ('open','acknowledged','investigating','resolved')),version integer NOT NULL DEFAULT 1,opened_prediction bigint NOT NULL REFERENCES predictions,created_at timestamptz NOT NULL DEFAULT now(),FOREIGN KEY(tenant_id,equipment_id) REFERENCES equipment);
CREATE UNIQUE INDEX one_active_incident ON incidents(tenant_id,equipment_id) WHERE status<>'resolved';
CREATE TABLE incident_transitions(transition_id bigserial PRIMARY KEY,incident_id bigint NOT NULL REFERENCES incidents,tenant_id text NOT NULL REFERENCES tenants,from_status text,to_status text NOT NULL,note text NOT NULL,actor text NOT NULL,created_at timestamptz NOT NULL DEFAULT now());
CREATE TABLE evidence(evidence_id text NOT NULL,tenant_id text NOT NULL REFERENCES tenants,prediction_id bigint NOT NULL REFERENCES predictions,content jsonb NOT NULL,PRIMARY KEY(tenant_id,evidence_id));
CREATE TABLE maintenance_outcomes(outcome_id bigserial PRIMARY KEY,tenant_id text NOT NULL,equipment_id text NOT NULL,lifecycle_id text NOT NULL,cycle bigint NOT NULL,kind text NOT NULL CHECK(kind IN ('failure','inspection','maintenance','censored')),notes text NOT NULL,created_at timestamptz NOT NULL DEFAULT now(),FOREIGN KEY(tenant_id,equipment_id) REFERENCES equipment);
CREATE TABLE outbox(outbox_id bigserial PRIMARY KEY,tenant_id text NOT NULL REFERENCES tenants,dedupe_key text NOT NULL,payload jsonb NOT NULL,status text NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','leased','sent','dead')),attempts integer NOT NULL DEFAULT 0,lease_token bigint NOT NULL DEFAULT 0,lease_until timestamptz,available_at timestamptz NOT NULL DEFAULT now(),UNIQUE(tenant_id,dedupe_key));
CREATE TABLE audit_events(audit_id bigserial PRIMARY KEY,tenant_id text NOT NULL REFERENCES tenants,actor text NOT NULL,action text NOT NULL,details jsonb NOT NULL,created_at timestamptz NOT NULL DEFAULT now());
INSERT INTO schema_migrations(version) VALUES (1);
