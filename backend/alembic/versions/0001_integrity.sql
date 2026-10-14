CREATE FUNCTION validate_map_geometry() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE shape geometry;
BEGIN
  IF TG_TABLE_NAME = 'path_edges' THEN shape := NEW.geometry; ELSE shape := NEW.point; END IF;
  IF ST_IsEmpty(shape) OR NOT ST_IsValid(shape) OR NOT ST_CoveredBy(shape, ST_MakeEnvelope(-180,-90,180,90,4326)) THEN
    RAISE EXCEPTION 'invalid WGS84 geometry' USING ERRCODE='23514';
  END IF;
  IF TG_TABLE_NAME = 'path_edges' THEN
    NEW.distance_m := ST_Length(shape::geography);
  END IF;
  RETURN NEW;
END $$;
CREATE TRIGGER edge_geometry BEFORE INSERT OR UPDATE ON path_edges FOR EACH ROW EXECUTE FUNCTION validate_map_geometry();
CREATE TRIGGER node_geometry BEFORE INSERT OR UPDATE ON path_nodes FOR EACH ROW EXECUTE FUNCTION validate_map_geometry();
CREATE TRIGGER location_geometry BEFORE INSERT OR UPDATE ON locations FOR EACH ROW EXECUTE FUNCTION validate_map_geometry();
CREATE TRIGGER infrastructure_geometry BEFORE INSERT OR UPDATE ON infrastructure FOR EACH ROW EXECUTE FUNCTION validate_map_geometry();

CREATE FUNCTION validate_edge_endpoints() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM path_edges e JOIN path_nodes s ON s.id=e.source_node_id JOIN path_nodes t ON t.id=e.target_node_id
    WHERE (CASE WHEN TG_TABLE_NAME='path_edges' THEN e.id=NEW.id ELSE (e.source_node_id=NEW.id OR e.target_node_id=NEW.id) END)
      AND (NOT ST_Equals(ST_StartPoint(e.geometry),s.point) OR NOT ST_Equals(ST_EndPoint(e.geometry),t.point)
        OR s.level <> t.level
        OR e.distance_m < ST_3DDistance(ST_Transform(ST_Force3D(s.point),4978),ST_Transform(ST_Force3D(t.point),4978)))
  ) THEN RAISE EXCEPTION 'edge endpoints, levels or distance lower bound invalid' USING ERRCODE='23514'; END IF;
  RETURN NULL;
END $$;
CREATE CONSTRAINT TRIGGER edge_endpoints AFTER INSERT OR UPDATE ON path_edges DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validate_edge_endpoints();
CREATE CONSTRAINT TRIGGER node_edges AFTER INSERT OR UPDATE ON path_nodes DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION validate_edge_endpoints();

CREATE FUNCTION immutable_history() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'history is append-only' USING ERRCODE='42501'; END $$;
CREATE TRIGGER audit_immutable BEFORE UPDATE OR DELETE ON admin_actions FOR EACH ROW EXECUTE FUNCTION immutable_history();
CREATE TRIGGER events_immutable BEFORE UPDATE OR DELETE ON graph_events FOR EACH ROW EXECUTE FUNCTION immutable_history();
