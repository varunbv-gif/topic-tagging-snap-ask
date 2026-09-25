-- One row per exchange (student question + bot reply) in ShowNAsk.
-- The note for exchange N is the LAST element of prior_coverage_recent on the Nth bot turn,
-- so the 5-note rolling window never loses anything. Export as CSV.
WITH bot_turns AS (
  SELECT
    conversation_id,
    ROW_NUMBER() OVER (PARTITION BY conversation_id ORDER BY message_index) AS exchange_no,
    ARRAY_REVERSE(prior_coverage_recent)[SAFE_OFFSET(0)] AS note
  FROM `prj-prod-ved-srv-data05.vedantu_aimentor_shownask.conversation_turns`
  WHERE role = 'bot'
    AND DATE(timestamp) BETWEEN '2026-09-01' AND '2026-09-21'
)
SELECT
  b.conversation_id,
  c.user_id,
  c.state_user_grade AS grade,
  c.state_user_board AS board,
  b.exchange_no,
  b.note.student   AS student_note,
  b.note.delivered AS delivered_note
FROM bot_turns b
LEFT JOIN `prj-prod-ved-srv-data05.vedantu_aimentor_shownask.conversations` c
  ON c.conversation_id = b.conversation_id
ORDER BY b.conversation_id, b.exchange_no
