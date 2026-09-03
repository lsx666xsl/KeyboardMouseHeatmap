use chrono::{Datelike, Duration, Local, NaiveDate, Timelike};
use rusqlite::{params, Connection};
use serde::Serialize;
use std::path::Path;
use std::sync::{Arc, Mutex};

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct KeyStat {
    pub key_id: String,
    pub label: String,
    pub count: u64,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct MouseStat {
    pub action_id: String,
    pub label: String,
    pub count: u64,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct ActivityStat {
    pub hour: u8,
    pub count: u64,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DashboardData {
    pub date: String,
    pub total_key_presses: u64,
    pub total_mouse_actions: u64,
    pub keys: Vec<KeyStat>,
    pub mouse: Vec<MouseStat>,
    pub activity: Vec<ActivityStat>,
}

pub struct StatsStore {
    connection: Mutex<Connection>,
}

impl StatsStore {
    pub fn open(path: &Path) -> Result<Arc<Self>, String> {
        let connection = Connection::open(path).map_err(|error| error.to_string())?;
        Self::from_connection(connection).map(Arc::new)
    }

    #[cfg(test)]
    fn open_in_memory() -> Result<Self, String> {
        Self::from_connection(Connection::open_in_memory().map_err(|error| error.to_string())?)
    }

    fn from_connection(connection: Connection) -> Result<Self, String> {
        connection
            .execute_batch(
                "
                PRAGMA journal_mode = WAL;
                CREATE TABLE IF NOT EXISTS key_stats (
                    stat_date TEXT NOT NULL,
                    stat_hour INTEGER NOT NULL,
                    key_id TEXT NOT NULL,
                    key_label TEXT NOT NULL,
                    press_count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (stat_date, stat_hour, key_id)
                );
                CREATE TABLE IF NOT EXISTS mouse_stats (
                    stat_date TEXT NOT NULL,
                    stat_hour INTEGER NOT NULL,
                    action_id TEXT NOT NULL,
                    action_label TEXT NOT NULL,
                    action_count INTEGER NOT NULL DEFAULT 0,
                    PRIMARY KEY (stat_date, stat_hour, action_id)
                );
                CREATE INDEX IF NOT EXISTS idx_key_stats_date ON key_stats(stat_date);
                CREATE INDEX IF NOT EXISTS idx_mouse_stats_date ON mouse_stats(stat_date);
                ",
            )
            .map_err(|error| error.to_string())?;

        Ok(Self {
            connection: Mutex::new(connection),
        })
    }

    pub fn record_key(&self, key_id: &str, label: &str) -> Result<(), String> {
        let now = Local::now();
        self.record_key_at(
            &now.format("%Y-%m-%d").to_string(),
            now.hour() as u8,
            key_id,
            label,
        )
    }

    fn record_key_at(&self, date: &str, hour: u8, key_id: &str, label: &str) -> Result<(), String> {
        let connection = self.connection.lock().map_err(|error| error.to_string())?;
        connection
            .execute(
                "
                INSERT INTO key_stats (stat_date, stat_hour, key_id, key_label, press_count)
                VALUES (?1, ?2, ?3, ?4, 1)
                ON CONFLICT(stat_date, stat_hour, key_id)
                DO UPDATE SET press_count = press_count + 1, key_label = excluded.key_label
                ",
                params![date, hour, key_id, label],
            )
            .map(|_| ())
            .map_err(|error| error.to_string())
    }

    pub fn record_mouse(&self, action_id: &str, label: &str) -> Result<(), String> {
        let now = Local::now();
        self.record_mouse_at(
            &now.format("%Y-%m-%d").to_string(),
            now.hour() as u8,
            action_id,
            label,
        )
    }

    fn record_mouse_at(
        &self,
        date: &str,
        hour: u8,
        action_id: &str,
        label: &str,
    ) -> Result<(), String> {
        let connection = self.connection.lock().map_err(|error| error.to_string())?;
        connection
            .execute(
                "
                INSERT INTO mouse_stats (stat_date, stat_hour, action_id, action_label, action_count)
                VALUES (?1, ?2, ?3, ?4, 1)
                ON CONFLICT(stat_date, stat_hour, action_id)
                DO UPDATE SET action_count = action_count + 1, action_label = excluded.action_label
                ",
                params![date, hour, action_id, label],
            )
            .map(|_| ())
            .map_err(|error| error.to_string())
    }

    pub fn dashboard_today(&self) -> Result<DashboardData, String> {
        self.dashboard_range("today")
    }

    pub fn dashboard_range(&self, range: &str) -> Result<DashboardData, String> {
        let (start, end) = range_bounds(range)?;
        self.dashboard_custom(
            &start.format("%Y-%m-%d").to_string(),
            &end.format("%Y-%m-%d").to_string(),
        )
    }

    pub fn dashboard_custom(
        &self,
        start_date: &str,
        end_date: &str,
    ) -> Result<DashboardData, String> {
        let start = parse_date(start_date)?;
        let end = parse_date(end_date)?;
        if start > end {
            return Err("custom dashboard range start date must not be after end date".to_string());
        }

        self.dashboard_between(
            &start.format("%Y-%m-%d").to_string(),
            &end.format("%Y-%m-%d").to_string(),
        )
    }

    fn dashboard_between(&self, start_date: &str, end_date: &str) -> Result<DashboardData, String> {
        let connection = self.connection.lock().map_err(|error| error.to_string())?;
        let total_key_presses = scalar_count(
            &connection,
            "SELECT COALESCE(SUM(press_count), 0) FROM key_stats WHERE stat_date BETWEEN ?1 AND ?2",
            start_date,
            end_date,
        )?;
        let total_mouse_actions = scalar_count(
            &connection,
            "SELECT COALESCE(SUM(action_count), 0) FROM mouse_stats WHERE stat_date BETWEEN ?1 AND ?2",
            start_date,
            end_date,
        )?;

        let mut key_query = connection
            .prepare(
                "
                SELECT key_id, key_label, SUM(press_count) AS total
                FROM key_stats WHERE stat_date BETWEEN ?1 AND ?2
                GROUP BY key_id, key_label ORDER BY total DESC, key_id ASC
                ",
            )
            .map_err(|error| error.to_string())?;
        let keys = key_query
            .query_map(params![start_date, end_date], |row| {
                Ok(KeyStat {
                    key_id: row.get(0)?,
                    label: row.get(1)?,
                    count: row.get::<_, i64>(2)?.max(0) as u64,
                })
            })
            .map_err(|error| error.to_string())?
            .collect::<Result<Vec<_>, _>>()
            .map_err(|error| error.to_string())?;

        let mut mouse_query = connection
            .prepare(
                "
                SELECT action_id, action_label, SUM(action_count) AS total
                FROM mouse_stats WHERE stat_date BETWEEN ?1 AND ?2
                GROUP BY action_id, action_label ORDER BY total DESC, action_id ASC
                ",
            )
            .map_err(|error| error.to_string())?;
        let mouse = mouse_query
            .query_map(params![start_date, end_date], |row| {
                Ok(MouseStat {
                    action_id: row.get(0)?,
                    label: row.get(1)?,
                    count: row.get::<_, i64>(2)?.max(0) as u64,
                })
            })
            .map_err(|error| error.to_string())?
            .collect::<Result<Vec<_>, _>>()
            .map_err(|error| error.to_string())?;

        let mut activity = vec![0_u64; 24];
        let mut activity_query = connection
            .prepare(
                "
                SELECT stat_hour, SUM(total) FROM (
                    SELECT stat_hour, SUM(press_count) AS total FROM key_stats
                    WHERE stat_date BETWEEN ?1 AND ?2 GROUP BY stat_hour
                    UNION ALL
                    SELECT stat_hour, SUM(action_count) AS total FROM mouse_stats
                    WHERE stat_date BETWEEN ?1 AND ?2 GROUP BY stat_hour
                ) GROUP BY stat_hour ORDER BY stat_hour
                ",
            )
            .map_err(|error| error.to_string())?;
        let rows = activity_query
            .query_map(params![start_date, end_date], |row| {
                Ok((row.get::<_, u8>(0)?, row.get::<_, i64>(1)?.max(0) as u64))
            })
            .map_err(|error| error.to_string())?;
        for row in rows {
            let (hour, count) = row.map_err(|error| error.to_string())?;
            if let Some(slot) = activity.get_mut(hour as usize) {
                *slot = count;
            }
        }

        Ok(DashboardData {
            date: end_date.to_string(),
            total_key_presses,
            total_mouse_actions,
            keys,
            mouse,
            activity: activity
                .into_iter()
                .enumerate()
                .map(|(hour, count)| ActivityStat {
                    hour: hour as u8,
                    count,
                })
                .collect(),
        })
    }

    pub fn clear(&self) -> Result<(), String> {
        let connection = self.connection.lock().map_err(|error| error.to_string())?;
        connection
            .execute_batch("DELETE FROM key_stats; DELETE FROM mouse_stats;")
            .map_err(|error| error.to_string())
    }
}

fn range_bounds(range: &str) -> Result<(NaiveDate, NaiveDate), String> {
    let today = Local::now().date_naive();
    let start = match range {
        "today" => today,
        "week" => today - Duration::days(today.weekday().num_days_from_monday() as i64),
        "month" => NaiveDate::from_ymd_opt(today.year(), today.month(), 1)
            .ok_or_else(|| "could not calculate current month".to_string())?,
        _ => return Err(format!("unsupported dashboard range: {range}")),
    };
    Ok((start, today))
}

fn parse_date(value: &str) -> Result<NaiveDate, String> {
    NaiveDate::parse_from_str(value, "%Y-%m-%d")
        .map_err(|_| format!("invalid dashboard date: {value}; expected YYYY-MM-DD"))
}

fn scalar_count(
    connection: &Connection,
    query: &str,
    start_date: &str,
    end_date: &str,
) -> Result<u64, String> {
    connection
        .query_row(query, params![start_date, end_date], |row| {
            row.get::<_, i64>(0)
        })
        .map(|value| value.max(0) as u64)
        .map_err(|error| error.to_string())
}

#[cfg(test)]
mod tests {
    use super::StatsStore;

    #[test]
    fn aggregates_key_and_mouse_counts_by_day() {
        let store = StatsStore::open_in_memory().expect("database should initialize");
        store.record_key_at("2026-09-04", 10, "a", "A").unwrap();
        store.record_key_at("2026-09-04", 10, "a", "A").unwrap();
        store
            .record_key_at("2026-09-04", 11, "space", "Space")
            .unwrap();
        store
            .record_mouse_at("2026-09-04", 10, "left-click", "左键")
            .unwrap();

        let dashboard = store.dashboard_between("2026-09-04", "2026-09-04").unwrap();
        assert_eq!(dashboard.total_key_presses, 3);
        assert_eq!(dashboard.total_mouse_actions, 1);
        assert_eq!(dashboard.keys[0].key_id, "a");
        assert_eq!(dashboard.keys[1].key_id, "space");
        assert_eq!(dashboard.keys[0].count, 2);
        assert_eq!(dashboard.activity[10].count, 3);
    }

    #[test]
    fn clear_removes_all_aggregates() {
        let store = StatsStore::open_in_memory().expect("database should initialize");
        store.record_key_at("2026-09-04", 8, "e", "E").unwrap();
        store
            .record_mouse_at("2026-09-04", 8, "wheel-up", "滚轮向上")
            .unwrap();
        store.clear().unwrap();

        let dashboard = store.dashboard_between("2026-09-04", "2026-09-04").unwrap();
        assert_eq!(dashboard.total_key_presses, 0);
        assert_eq!(dashboard.total_mouse_actions, 0);
        assert!(dashboard.keys.is_empty());
        assert!(dashboard.mouse.is_empty());
    }

    #[test]
    fn range_query_includes_all_days_inclusive() {
        let store = StatsStore::open_in_memory().expect("database should initialize");
        store.record_key_at("2026-09-01", 8, "a", "A").unwrap();
        store.record_key_at("2026-09-03", 9, "b", "B").unwrap();
        store.record_key_at("2026-09-04", 9, "c", "C").unwrap();

        let dashboard = store.dashboard_between("2026-09-01", "2026-09-03").unwrap();
        assert_eq!(dashboard.total_key_presses, 2);
        assert_eq!(dashboard.activity[8].count, 1);
        assert_eq!(dashboard.activity[9].count, 1);
    }

    #[test]
    fn custom_range_validates_dates_and_includes_boundaries() {
        let store = StatsStore::open_in_memory().expect("database should initialize");
        store.record_key_at("2026-09-01", 8, "a", "A").unwrap();
        store.record_key_at("2026-09-02", 9, "b", "B").unwrap();
        store.record_key_at("2026-09-04", 10, "c", "C").unwrap();

        let dashboard = store.dashboard_custom("2026-09-01", "2026-09-02").unwrap();
        assert_eq!(dashboard.total_key_presses, 2);
        assert_eq!(dashboard.date, "2026-09-02");
        assert!(store.dashboard_custom("2026-09-03", "2026-09-02").is_err());
        assert!(store.dashboard_custom("2026-09-99", "2026-09-30").is_err());
    }
}
