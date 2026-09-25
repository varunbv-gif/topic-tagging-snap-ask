-- ONE ROW PER CONVERSATION, built from ALL N bot turns (not just the last).
-- Every turn's prior_coverage_recent contributes its notes, and every turn's
-- prior_coverage_older_delivered contributes its running summary; the union is
-- de-duplicated (the 5-note window repeats each note up to 5 times) and kept in
-- the order the notes first appeared. Export as CSV.
WITH bot AS (
  SELECT conversation_id, message_index, prior_coverage_recent, prior_coverage_older_delivered
  FROM `prj-prod-ved-srv-data05.vedantu_aimentor_shownask.conversation_turns`
  WHERE role = 'bot'
    AND DATE(timestamp, 'Asia/Kolkata') BETWEEN '2026-09-20' AND '2026-09-20'
),
notes AS (
  SELECT conversation_id, r.delivered AS note, MIN(message_index) AS first_seen
  FROM bot, UNNEST(prior_coverage_recent) AS r
  WHERE r.delivered IS NOT NULL AND r.delivered != ''
  GROUP BY conversation_id, note
  UNION ALL
  SELECT conversation_id, prior_coverage_older_delivered AS note, MIN(message_index) AS first_seen
  FROM bot
  WHERE prior_coverage_older_delivered IS NOT NULL AND prior_coverage_older_delivered != ''
  GROUP BY conversation_id, note
),
dedup AS (
  SELECT conversation_id, note, MIN(first_seen) AS first_seen
  FROM notes GROUP BY conversation_id, note
)
SELECT
  d.conversation_id,
  ANY_VALUE(c.user_id)          AS user_id,
  ANY_VALUE(c.state_user_grade) AS grade,
  ANY_VALUE(c.state_user_board) AS board,
  COUNT(*)                      AS notes,
  STRING_AGG(d.note, '  ' ORDER BY d.first_seen) AS coverage
FROM dedup d
LEFT JOIN `prj-prod-ved-srv-data05.vedantu_aimentor_shownask.conversations` c
  ON c.conversation_id = d.conversation_id
GROUP BY d.conversation_id
ORDER BY d.conversation_id
