-- Databricks notebook source
-- MAGIC %md
-- MAGIC # Warehouse Cost Investigation
-- MAGIC
-- MAGIC Locate an `INSUFFICIENT_PERMISSIONS` failure window on a SQL warehouse, then
-- MAGIC quantify that warehouse's DBU usage across the same window.
-- MAGIC
-- MAGIC **How to run**
-- MAGIC 1. Set `warehouse_id` in the widgets above.
-- MAGIC 2. Run **Query 1** to find when the failures started/stopped.
-- MAGIC 3. Copy those timestamps into the `start_ts` / `end_ts` widgets (UTC).
-- MAGIC 4. Run **Query 2** and **Query 3**.
-- MAGIC
-- MAGIC Widgets keep this file environment-agnostic, so the same notebook runs in the
-- MAGIC dev and customer workspaces without edits.

-- COMMAND ----------

CREATE WIDGET TEXT warehouse_id DEFAULT '';
CREATE WIDGET TEXT start_ts DEFAULT '';  -- UTC, e.g. 2026-07-01 00:00:00
CREATE WIDGET TEXT end_ts DEFAULT '';  -- UTC, e.g. 2026-07-02 00:00:00

-- COMMAND ----------

-- MAGIC %md ## Query 1 — Failure window and volume

-- COMMAND ----------

SELECT
  MIN(start_time) AS first_failed_query_time,
  MAX(start_time) AS last_failed_query_time,
  COUNT(*) AS failed_query_count
FROM system.query.history
WHERE
  compute.warehouse_id = :warehouse_id
  AND execution_status = 'FAILED'
  AND error_message LIKE '%INSUFFICIENT_PERMISSIONS%';

-- COMMAND ----------

-- MAGIC %md ## Query 2 — Total DBUs during the window

-- COMMAND ----------

SELECT
  usage_metadata.warehouse_id,
  SUM(usage_quantity) AS total_dbus
FROM system.billing.usage
WHERE
  usage_metadata.warehouse_id = :warehouse_id
  AND usage_unit = 'DBU'
  AND usage_start_time >= CAST(:start_ts AS TIMESTAMP)
  AND usage_end_time < CAST(:end_ts AS TIMESTAMP)
GROUP BY usage_metadata.warehouse_id;

-- COMMAND ----------

-- MAGIC %md ## Query 3 — Daily DBU trend

-- COMMAND ----------

SELECT
  usage_date,
  sku_name,
  ROUND(SUM(usage_quantity), 2) AS total_dbus
FROM system.billing.usage
WHERE
  usage_metadata.warehouse_id = :warehouse_id
  AND usage_unit = 'DBU'
  AND usage_start_time >= CAST(:start_ts AS TIMESTAMP)
  AND usage_end_time < CAST(:end_ts AS TIMESTAMP)
GROUP BY usage_date, sku_name
ORDER BY usage_date;

-- COMMAND ----------

-- MAGIC %md ## Query 4 — DBUs during hours that had failures

-- COMMAND ----------

WITH failed_hours AS (
  SELECT DISTINCT DATE_TRUNC('hour', start_time) AS failure_hour
  FROM system.query.history
  WHERE
    compute.warehouse_id = :warehouse_id
    AND execution_status = 'FAILED'
    AND error_message LIKE '%INSUFFICIENT_PERMISSIONS%'
),

warehouse_usage AS (
  SELECT
    DATE_TRUNC('hour', usage_start_time) AS usage_hour,
    SUM(usage_quantity) AS dbus
  FROM system.billing.usage
  WHERE
    usage_metadata.warehouse_id = :warehouse_id
    AND usage_unit = 'DBU'
  GROUP BY DATE_TRUNC('hour', usage_start_time)
)

SELECT
  u.usage_hour,
  u.dbus
FROM warehouse_usage AS u
INNER JOIN failed_hours AS f
  ON u.usage_hour = f.failure_hour
ORDER BY u.usage_hour;
