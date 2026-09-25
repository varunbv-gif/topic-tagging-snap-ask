-- ONE ROW PER CONVERSATION. This replaces 01_exchanges.sql for the simple pipeline.
-- The bot's LAST turn already carries the whole conversation:
--   prior_coverage_older_delivered = everything before the last 5 exchanges (a running summary)
--   prior_coverage_recent          = the last 5 exchanges
-- so there is nothing to stitch together. Export as CSV.
WITH last_turn AS (
  SELECT
    conversation_id,
    prior_coverage_older_delivered AS older,
    prior_coverage_recent          AS recent,
    COUNT(*)     OVER (PARTITION BY conversation_id) AS exchanges,
    ROW_NUMBER() OVER (PARTITION BY conversation_id ORDER BY message_index DESC) AS rn
  FROM `prj-prod-ved-srv-data05.vedantu_aimentor_shownask.conversation_turns`
  WHERE role = 'bot'
    AND DATE(timestamp, 'Asia/Kolkata') BETWEEN '2026-09-20' AND '2026-09-20'
)
SELECT
  l.conversation_id,
  c.user_id,
  c.state_user_grade AS grade,
  c.state_user_board AS board,
  l.exchanges,
  -- one summary per conversation: the older running summary, then the last five notes
  TRIM(CONCAT(
    IFNULL(l.older, ''), ' ',
    (SELECT STRING_AGG(r.delivered, ' ') FROM UNNEST(l.recent) AS r WHERE r.delivered != '')
  )) AS coverage_summary
FROM last_turn l
LEFT JOIN `prj-prod-ved-srv-data05.vedantu_aimentor_shownask.conversations` c
  ON c.conversation_id = l.conversation_id
WHERE l.rn = 1
ORDER BY l.conversation_id
