package main

import (
	"database/sql"
	"log"
	"os"

	_ "github.com/mattn/go-sqlite3"
)

var db *sql.DB

func initDB(path string) error {
	// Delete old DB in dev mode
	if os.Getenv("DEV") == "1" {
		os.Remove(path)
	}

	var err error
	db, err = sql.Open("sqlite3", path+"?_journal_mode=WAL&_busy_timeout=5000")
	if err != nil {
		return err
	}
	db.SetMaxOpenConns(1)

	schema := []string{
		`CREATE TABLE IF NOT EXISTS sessions (
			id TEXT PRIMARY KEY,
			created_at TEXT NOT NULL DEFAULT (datetime('now')),
			ended_at TEXT,
			calibration_profile_id TEXT,
			metadata TEXT
		)`,
		`CREATE TABLE IF NOT EXISTS imu_frames (
			session_id TEXT NOT NULL,
			timestamp_us INTEGER NOT NULL,
			ax INTEGER, ay INTEGER, az INTEGER,
			gx INTEGER, gy INTEGER, gz INTEGER,
			PRIMARY KEY (session_id, timestamp_us)
		) WITHOUT ROWID`,
		`CREATE TABLE IF NOT EXISTS impacts (
			id INTEGER PRIMARY KEY AUTOINCREMENT,
			session_id TEXT NOT NULL,
			timestamp_us INTEGER NOT NULL,
			tdoa_ns TEXT,
			amplitude TEXT,
			computed_x REAL,
			computed_y REAL,
			confidence REAL,
			calibration_profile_id TEXT,
			FOREIGN KEY (session_id) REFERENCES sessions(id)
		)`,
		`CREATE TABLE IF NOT EXISTS calibration_profiles (
			id TEXT PRIMARY KEY,
			created_at TEXT NOT NULL,
			model_type TEXT,
			model_params TEXT,
			rmse REAL,
			metadata TEXT
		)`,
		`CREATE TABLE IF NOT EXISTS calibration_points (
			profile_id TEXT NOT NULL,
			grid_x REAL, grid_y REAL,
			tdoa_ns TEXT,
			tap_number INTEGER,
			FOREIGN KEY (profile_id) REFERENCES calibration_profiles(id)
		)`,
		`CREATE INDEX IF NOT EXISTS idx_imu_session ON imu_frames(session_id, timestamp_us)`,
		`CREATE INDEX IF NOT EXISTS idx_impacts_session ON impacts(session_id)`,
	}

	for _, q := range schema {
		if _, err := db.Exec(q); err != nil {
			return err
		}
	}
	log.Println("DB initialized (SQLite WAL mode)")
	return nil
}
