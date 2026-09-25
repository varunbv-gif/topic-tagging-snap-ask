-- ONE ROW PER CONVERSATION, built from EVERY column that carries content.
-- Supersedes 04_conversation_all_turns.sql, which used only the two coverage
-- columns. text/image are empty on every row; metadata_title is a bare timestamp.
-- Export as CSV.
WITH turns AS (
  SELECT *
  FROM `prj-prod-ved-srv-data05.vedantu_aimentor_shownask.conversation_turns`
  WHERE DATE(timestamp, 'Asia/Kolkata') = '2026-09-20'
),
-- what the student typed, and how many photos they sent
asked AS (
  SELECT conversation_id,
         COUNTIF(p.kind = 'image') AS images,
         STRING_AGG(IF(p.kind = 'text', p.text, NULL), ' ~ ' ORDER BY message_index) AS student_typed
  FROM turns, UNNEST(input_parts) AS p
  GROUP BY conversation_id
),
-- the bot's own notes, all four flavours, de-duplicated (the 5-note window repeats)
notes AS (
  SELECT conversation_id, kind, STRING_AGG(note, ' || ' ORDER BY first_seen) AS text
  FROM (
    SELECT conversation_id, 'taught' AS kind, r.delivered AS note, MIN(message_index) AS first_seen
    FROM turns, UNNEST(prior_coverage_recent) AS r
    WHERE role = 'bot' AND r.delivered != '' GROUP BY conversation_id, note
    UNION ALL
    SELECT conversation_id, 'wanted', r.student, MIN(message_index)
    FROM turns, UNNEST(prior_coverage_recent) AS r
    WHERE role = 'bot' AND r.student != '' GROUP BY conversation_id, note
    UNION ALL
    SELECT conversation_id, 'older_delivered', prior_coverage_older_delivered, MIN(message_index)
    FROM turns WHERE role = 'bot' AND prior_coverage_older_delivered != '' GROUP BY conversation_id, note
    UNION ALL
    SELECT conversation_id, 'older_student', prior_coverage_older_student, MIN(message_index)
    FROM turns WHERE role = 'bot' AND prior_coverage_older_student != '' GROUP BY conversation_id, note
  ) GROUP BY conversation_id, kind
),
-- the bot's verbatim reply and its written worked solution
said AS (
  SELECT conversation_id,
         STRING_AGG(IF(x.kind = '', x.text, NULL), ' ' ORDER BY message_index) AS answer,
         STRING_AGG(NULLIF(x.md, ''), ' ' ORDER BY message_index)              AS worked
  FROM turns, UNNEST(response) AS x
  WHERE role = 'bot'
  GROUP BY conversation_id
)
SELECT
  t.conversation_id,
  COUNTIF(t.role = 'bot')        AS exchanges,
  ANY_VALUE(a.images)            AS images,
  ANY_VALUE(c.state_user_grade)  AS grade,
  ANY_VALUE(c.state_user_board)  AS board,
  ANY_VALUE(c.state_user_stream) AS stream,
  ANY_VALUE(c.state_user_target) AS target,
  ANY_VALUE(ARRAY_TO_STRING(c.state_user_examTargets, ','))         AS exam_targets,
  ANY_VALUE(a.student_typed)                                        AS asked,
  ANY_VALUE((SELECT text FROM notes n WHERE n.conversation_id = t.conversation_id AND n.kind = 'wanted'))          AS wanted,
  ANY_VALUE((SELECT text FROM notes n WHERE n.conversation_id = t.conversation_id AND n.kind = 'taught'))          AS taught,
  ANY_VALUE((SELECT text FROM notes n WHERE n.conversation_id = t.conversation_id AND n.kind = 'older_delivered')) AS older_delivered,
  ANY_VALUE((SELECT text FROM notes n WHERE n.conversation_id = t.conversation_id AND n.kind = 'older_student'))   AS older_student,
  ANY_VALUE(s.answer)  AS answer,
  ANY_VALUE(s.worked)  AS worked
FROM turns t
LEFT JOIN asked a  ON a.conversation_id = t.conversation_id
LEFT JOIN said  s  ON s.conversation_id = t.conversation_id
LEFT JOIN `prj-prod-ved-srv-data05.vedantu_aimentor_shownask.conversations` c
       ON c.conversation_id = t.conversation_id
GROUP BY t.conversation_id
ORDER BY t.conversation_id
