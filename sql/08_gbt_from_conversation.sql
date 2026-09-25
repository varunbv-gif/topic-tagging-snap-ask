-- conversation_id -> user_id -> the student's GBT (grade / board / stream / target).
-- All 271 conversations on 20 Sep 2026 resolve; the profile is complete where the
-- conversation snapshot was not (46 missing grades, 56 missing boards).
--
-- LIMIT: student.board is a 7-value enum (CBSE / ICSE / STATE / MAHARASHTRA / IB /
-- OTHERS / NA). It does NOT say WHICH state, so for 44% of conversations the GBT
-- board names no tree family. state_user_board on the conversation keeps the
-- specific board (BIEAP, BSE Telangana, MH) - fall back to it when the profile is
-- generic. There is NO stored GBT -> parentTreeId mapping anywhere: the tree is
-- derived from the parentTreeName convention <grade band>_<family>.
SELECT
  c.conversation_id,
  c.user_id,
  s.grade                  AS gbt_grade,
  s.board                  AS gbt_board,
  s.stream                 AS gbt_stream,
  s.target                 AS gbt_target,
  c.state_user_grade       AS snapshot_grade,   -- captured at conversation time
  c.state_user_board       AS snapshot_board,   -- keeps the specific state board
  c.state_user_target      AS snapshot_target
FROM `prj-prod-ved-srv-data05.vedantu_aimentor_shownask.conversations` c
LEFT JOIN `prj-prod-ved-srv-data05.analytics_rag.student` s
       ON s.id = c.user_id
WHERE c.conversation_id IN (
  SELECT DISTINCT conversation_id
  FROM `prj-prod-ved-srv-data05.vedantu_aimentor_shownask.conversation_turns`
  WHERE DATE(timestamp, 'Asia/Kolkata') = '2026-09-20'
)
