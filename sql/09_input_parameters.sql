-- THE NINE INPUT PARAMETERS, one row per conversation.
-- user_id, conversation_id, what the student sent, what the bot responded,
-- prior_coverage_recent (student + delivered), prior_coverage_older_delivered,
-- and grade / board / target from the central student profile.
WITH turns AS (
  SELECT *
  FROM `prj-prod-ved-srv-data05.vedantu_aimentor_shownask.conversation_turns`
  WHERE DATE(timestamp, 'Asia/Kolkata') = '2026-09-20'
),
input AS (                                   -- what was the input
  SELECT conversation_id,
         STRING_AGG(p.text, ' ~ ' ORDER BY message_index) AS student_input
  FROM turns, UNNEST(input_parts) AS p
  WHERE p.kind = 'text'
  GROUP BY conversation_id
),
response AS (                                -- what did the bot respond
  SELECT conversation_id,
         CONCAT(
           IFNULL(STRING_AGG(IF(x.kind = '', x.text, NULL), ' ' ORDER BY message_index), ''), ' ',
           IFNULL(STRING_AGG(NULLIF(x.md, ''),            ' ' ORDER BY message_index), '')
         ) AS bot_response
  FROM turns, UNNEST(response) AS x
  WHERE role = 'bot'
  GROUP BY conversation_id
),
recent AS (                                  -- prior recent coverage, de-duplicated
  SELECT conversation_id,
         STRING_AGG(IF(kind = 'student',   note, NULL), ' || ' ORDER BY first_seen) AS wanted,
         STRING_AGG(IF(kind = 'delivered', note, NULL), ' || ' ORDER BY first_seen) AS taught
  FROM (
    SELECT conversation_id, 'student' AS kind, r.student AS note, MIN(message_index) AS first_seen
    FROM turns, UNNEST(prior_coverage_recent) AS r
    WHERE role = 'bot' AND r.student != '' GROUP BY conversation_id, note
    UNION ALL
    SELECT conversation_id, 'delivered', r.delivered, MIN(message_index)
    FROM turns, UNNEST(prior_coverage_recent) AS r
    WHERE role = 'bot' AND r.delivered != '' GROUP BY conversation_id, note
  ) GROUP BY conversation_id
),
older AS (                                   -- prior coverage older delivered
  SELECT conversation_id, STRING_AGG(note, ' || ' ORDER BY first_seen) AS earlier
  FROM (
    SELECT conversation_id, prior_coverage_older_delivered AS note, MIN(message_index) AS first_seen
    FROM turns WHERE role = 'bot' AND prior_coverage_older_delivered != ''
    GROUP BY conversation_id, note
  ) GROUP BY conversation_id
)
SELECT
  c.user_id,                                 -- 1
  c.conversation_id,                         -- 2
  i.student_input,                           -- 3  what was the input
  r.bot_response,                            -- 4  what did the bot respond
  rc.wanted,                                 -- 5  prior recent coverage (student side)
  rc.taught,                                 -- 6  prior recent coverage (delivered side)
  o.earlier,                                 -- 7  prior coverage older delivered
  s.grade,                                   -- 8
  s.board,                                   -- 9
  s.target                                   -- 10
FROM `prj-prod-ved-srv-data05.vedantu_aimentor_shownask.conversations` c
LEFT JOIN `prj-prod-ved-srv-data05.analytics_rag.student` s ON s.id = c.user_id
LEFT JOIN input    i  ON i.conversation_id  = c.conversation_id
LEFT JOIN response r  ON r.conversation_id  = c.conversation_id
LEFT JOIN recent   rc ON rc.conversation_id = c.conversation_id
LEFT JOIN older    o  ON o.conversation_id  = c.conversation_id
WHERE c.conversation_id IN (SELECT DISTINCT conversation_id FROM turns)
ORDER BY c.conversation_id
