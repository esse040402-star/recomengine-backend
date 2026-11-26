CREATE OR REPLACE FUNCTION public.claim_guest_diagnosis_sessions(
  p_session_ids uuid[], p_user_id uuid
) RETURNS integer LANGUAGE plpgsql SECURITY DEFINER SET search_path = '' AS $$
DECLARE requested_count integer; eligible_count integer; claimed_count integer;
BEGIN
  SELECT count(DISTINCT sid) INTO requested_count
  FROM unnest(coalesce(p_session_ids, ARRAY[]::uuid[])) AS sid;
  IF requested_count = 0 THEN RETURN 0; END IF;
  IF requested_count > 20 OR p_user_id IS NULL THEN
    RAISE EXCEPTION 'invalid guest session claim request';
  END IF;
  SELECT count(*) INTO eligible_count FROM public.diagnosis_sessions
  WHERE id = ANY(p_session_ids) AND status = 'completed'
    AND (user_id IS NULL OR user_id = p_user_id);
  IF eligible_count <> requested_count THEN
    RAISE EXCEPTION 'one or more guest sessions are unavailable';
  END IF;
  UPDATE public.diagnosis_sessions SET user_id = p_user_id
  WHERE id = ANY(p_session_ids) AND user_id IS NULL AND status = 'completed';
  GET DIAGNOSTICS claimed_count = ROW_COUNT;
  RETURN requested_count;
END; $$;
REVOKE ALL ON FUNCTION public.claim_guest_diagnosis_sessions(uuid[], uuid) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.claim_guest_diagnosis_sessions(uuid[], uuid) TO service_role;
