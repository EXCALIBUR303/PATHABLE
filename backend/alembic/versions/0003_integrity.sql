CREATE UNIQUE INDEX one_enabled_model ON model_versions ((1)) WHERE enabled;

CREATE FUNCTION pathable_ml_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'ML provenance is retained'; END IF;
  IF TG_TABLE_NAME = 'model_versions' AND
     (to_jsonb(NEW) - 'enabled') IS DISTINCT FROM (to_jsonb(OLD) - 'enabled') THEN
    RAISE EXCEPTION 'Model versions are immutable';
  ELSIF TG_TABLE_NAME = 'inference_jobs' THEN
    IF (NEW.id,NEW.report_id,NEW.evidence_id,NEW.requested_by,NEW.model_version_id,NEW.evidence_sha256,NEW.created_at)
       IS DISTINCT FROM (OLD.id,OLD.report_id,OLD.evidence_id,OLD.requested_by,OLD.model_version_id,OLD.evidence_sha256,OLD.created_at) THEN
      RAISE EXCEPTION 'Job provenance is immutable';
    END IF;
    IF OLD.status IN ('succeeded','failed','unavailable') THEN RAISE EXCEPTION 'Terminal job is immutable'; END IF;
  ELSIF TG_TABLE_NAME = 'predictions' THEN
    IF (to_jsonb(NEW) - ARRAY['status','reviewer_id','reviewed_at','review_reason','row_version'])
       IS DISTINCT FROM (to_jsonb(OLD) - ARRAY['status','reviewer_id','reviewed_at','review_reason','row_version'])
       OR OLD.status <> 'proposed' OR NEW.status NOT IN ('accepted','rejected')
       OR NEW.row_version <> OLD.row_version + 1 THEN RAISE EXCEPTION 'Invalid prediction review'; END IF;
  END IF;
  RETURN NEW;
END $$;

CREATE TRIGGER model_immutable BEFORE UPDATE OR DELETE ON model_versions FOR EACH ROW EXECUTE FUNCTION pathable_ml_immutable();
CREATE TRIGGER job_immutable BEFORE UPDATE OR DELETE ON inference_jobs FOR EACH ROW EXECUTE FUNCTION pathable_ml_immutable();
CREATE TRIGGER prediction_immutable BEFORE UPDATE OR DELETE ON predictions FOR EACH ROW EXECUTE FUNCTION pathable_ml_immutable();

CREATE FUNCTION pathable_prediction_source() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.status <> 'proposed' OR NEW.row_version <> 1 OR NOT EXISTS
    (SELECT 1 FROM inference_jobs j JOIN model_versions m ON m.id=j.model_version_id
     WHERE j.id=NEW.job_id AND j.status='running' AND m.preprocessing_json->'classes' ? NEW.class_name) THEN
    RAISE EXCEPTION 'Prediction requires a running job and declared class';
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER prediction_source BEFORE INSERT ON predictions FOR EACH ROW EXECUTE FUNCTION pathable_prediction_source();
