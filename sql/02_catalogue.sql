-- Every node of every X_CBSE tree. Flat: tag.py walks parent_id to build the path.
-- Live today: 3_CBSE .. 10_CBSE and 11_12_CBSE (766 chapters / 5414 topics / 5247 sub-topics).
-- Export as CSV. Re-run only when the tree changes.
WITH trees AS (
  SELECT parentTreeId, ANY_VALUE(parentTreeName) AS parentTreeName
  FROM `prj-prod-ved-srv-data05.vedantu_lms_vedantumoodle.cmdsquestiontagging`
  WHERE LOWER(parentTreeName) LIKE '%cbse%'
  GROUP BY parentTreeId
)
SELECT
  tr.parentTreeName AS tree,
  n.id             AS node_id,
  n.levelType      AS level_type,
  n.name           AS node_name,
  n.parentId       AS parent_id
FROM `prj-prod-ved-srv-data05.vedantu_lms_vedantumoodle.topictree` n
JOIN trees tr ON tr.parentTreeId = n.parentTreeId
