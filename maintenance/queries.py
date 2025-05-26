COMBINED_YEARLY_DATA_QUERY = """
                             WITH yearly_costs AS (SELECT EXTRACT(YEAR FROM start_date) AS year, SUM (total_cost) AS total_cost
                             FROM maintenance_maintenancereport
                             WHERE vehicle_id = %s
                               AND profile_id = %s
                             GROUP BY EXTRACT (YEAR FROM start_date)
                                 ),
                                 monthly_costs AS (
                             SELECT
                                 EXTRACT (YEAR FROM start_date) AS year, EXTRACT (MONTH FROM start_date) AS month, SUM (total_cost) AS total_cost
                             FROM maintenance_maintenancereport
                             WHERE vehicle_id = %s
                               AND profile_id = %s
                             GROUP BY EXTRACT (YEAR FROM start_date), EXTRACT (MONTH FROM start_date)
                                 ),
                                 monthly_costs_with_lag AS (
                             SELECT
                                 year, month, total_cost, LAG(total_cost, 1, 0) OVER (PARTITION BY year ORDER BY month) AS previous_month_cost, CASE
                                 WHEN LAG(total_cost, 1, 0) OVER (PARTITION BY year ORDER BY month) = 0 THEN NULL
                                 ELSE 100.0 * (total_cost - LAG(total_cost, 1, 0) OVER (PARTITION BY year ORDER BY month)) /
                                 LAG(total_cost, 1, 0) OVER (PARTITION BY year ORDER BY month)
                                 END AS mom_change
                             FROM monthly_costs
                                 ), yearly_costs_with_lag AS (
                             SELECT
                                 year, total_cost, LAG(total_cost, 1, 0) OVER (ORDER BY year) AS previous_year_cost, CASE
                                 WHEN LAG(total_cost, 1, 0) OVER (ORDER BY year) = 0 THEN NULL
                                 ELSE 100.0 * (total_cost - LAG(total_cost, 1, 0) OVER (ORDER BY year)) /
                                 LAG(total_cost, 1, 0) OVER (ORDER BY year)
                                 END AS yoy_change
                             FROM yearly_costs
                                 ), yearly_part_data AS (
                             SELECT
                                 EXTRACT (YEAR FROM mr.start_date) AS year, p.name AS part_name, COUNT (ppe.id) AS count, SUM (ppe.cost) AS part_cost
                             FROM maintenance_partpurchaseevent ppe
                                 JOIN maintenance_maintenancereport mr
                             ON ppe.maintenance_report_id = mr.id
                                 JOIN maintenance_part p ON ppe.part_id = p.id
                             WHERE mr.vehicle_id = %s
                               AND mr.profile_id = %s
                             GROUP BY EXTRACT (YEAR FROM mr.start_date), p.name
                                 ),
                                 monthly_part_data AS (
                             SELECT
                                 EXTRACT (YEAR FROM mr.start_date) AS year, EXTRACT (MONTH FROM mr.start_date) AS month, p.name AS part_name, COUNT (ppe.id) AS count, SUM (ppe.cost) AS part_cost
                             FROM maintenance_partpurchaseevent ppe
                                 JOIN maintenance_maintenancereport mr
                             ON ppe.maintenance_report_id = mr.id
                                 JOIN maintenance_part p ON ppe.part_id = p.id
                             WHERE mr.vehicle_id = %s
                               AND mr.profile_id = %s
                             GROUP BY EXTRACT (YEAR FROM mr.start_date), EXTRACT (MONTH FROM mr.start_date), p.name
                                 ),
                                 yearly_ranked_parts AS (
                             SELECT
                                 year, part_name, count, part_cost, ROW_NUMBER() OVER (PARTITION BY year ORDER BY count DESC) AS rank
                             FROM yearly_part_data
                                 ), monthly_ranked_parts AS (
                             SELECT
                                 year, month, part_name, count, part_cost, ROW_NUMBER() OVER (PARTITION BY year, month ORDER BY count DESC) AS rank
                             FROM monthly_part_data
                                 ) \
                             SELECT *
                             FROM (SELECT 'yearly_cost' AS data_type, yc.year, NULL :: numeric AS month, yc.total_cost, yc.previous_year_cost, yc.yoy_change, NULL AS part_name, NULL ::bigint AS part_count, NULL :: numeric AS part_cost, NULL ::bigint AS part_rank
                                   FROM yearly_costs_with_lag yc

                                   UNION ALL

                                   SELECT 'monthly_cost' AS data_type, mc.year, mc.month, mc.total_cost, mc.previous_month_cost, mc.mom_change, NULL AS part_name, NULL ::bigint AS part_count, NULL :: numeric AS part_cost, NULL ::bigint AS part_rank
                                   FROM monthly_costs_with_lag mc

                                   UNION ALL

                                   SELECT 'yearly_part' AS data_type, yr.year, NULL :: numeric AS month, NULL :: numeric AS total_cost, NULL :: numeric AS previous_cost, NULL :: numeric AS change_percent, yr.part_name, yr.count::bigint AS part_count, yr.part_cost:: numeric, yr.rank::bigint AS part_rank
                                   FROM yearly_ranked_parts yr
                                   WHERE yr.rank <= 3

                                   UNION ALL

                                   SELECT 'monthly_part' AS data_type, mr.year, mr.month, NULL :: numeric AS total_cost, NULL :: numeric AS previous_cost, NULL :: numeric AS change_percent, mr.part_name, mr.count::bigint AS part_count, mr.part_cost:: numeric, mr.rank::bigint AS part_rank
                                   FROM monthly_ranked_parts mr
                                   WHERE mr.rank <= 3) AS combined_data
                             ORDER BY CASE
                                          WHEN data_type = 'yearly_cost' THEN 1
                                          WHEN data_type = 'monthly_cost' THEN 2
                                          WHEN data_type = 'yearly_part' THEN 3
                                          WHEN data_type = 'monthly_part' THEN 4
                                          END,
                                 year,
                                 month,
                                 part_rank \
                             """
