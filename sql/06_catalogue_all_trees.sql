-- Every chapter of EVERY tree, not just the CBSE ones.
-- 4,463 chapters across 73 trees (1,811 distinct names - see 'tree faults' below).
-- Stage 2 expands only the chapters the run actually chose; see 07.
-- Export as CSV. Re-run only when the tree changes.
SELECT
  IFNULL(tr.parentTreeName, CONCAT('UNNAMED_', SUBSTR(c.parentTreeId, 1, 8))) AS tree,
  IFNULL(s.name, '?')  AS subject,
  c.name               AS chapter,
  c.id                 AS chapter_id
FROM `prj-prod-ved-srv-data05.vedantu_lms_vedantumoodle.topictree` c
LEFT JOIN (
  SELECT parentTreeId, ANY_VALUE(parentTreeName) AS parentTreeName
  FROM `prj-prod-ved-srv-data05.vedantu_lms_vedantumoodle.cmdsquestiontagging`
  WHERE parentTreeName != ''
  GROUP BY parentTreeId
) tr ON tr.parentTreeId = c.parentTreeId
LEFT JOIN `prj-prod-ved-srv-data05.vedantu_lms_vedantumoodle.topictree` s
       ON s.id = c.parentId AND s.levelType = 'SUBJECT'
WHERE c.levelType = 'CHAPTER'
-- tree faults this exposes, all real:
--   * 14 trees list the same chapters twice under 'Math'/'Maths' and 'Mathematics' (209 rows)
--   * 5 trees have no name in cmdsquestiontagging (2,202 nodes); 3 are grade-10 clones
--   * 12_Tamilnadu has a 'Miscellaneous examples' chapter in every subject
