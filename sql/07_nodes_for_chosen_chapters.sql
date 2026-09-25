-- Stage 2: topics and sub-topics under the chapters stage 1 chose.
-- Substitute the chapter_id list produced by the chapter pass.
WITH ch AS (
  SELECT id, name FROM `prj-prod-ved-srv-data05.vedantu_lms_vedantumoodle.topictree`
  WHERE id IN UNNEST(@chapter_ids)
),
topic AS (
  SELECT n.id, n.name, n.levelType, c.id AS chapter_id, c.name AS chapter
  FROM `prj-prod-ved-srv-data05.vedantu_lms_vedantumoodle.topictree` n
  JOIN ch c ON c.id = n.parentId
),
subtopic AS (
  SELECT n.id, n.name, n.levelType, t.chapter_id, t.chapter
  FROM `prj-prod-ved-srv-data05.vedantu_lms_vedantumoodle.topictree` n
  JOIN topic t ON t.id = n.parentId
)
SELECT * FROM topic UNION ALL SELECT * FROM subtopic
ORDER BY chapter, levelType, name
