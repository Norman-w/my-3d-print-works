package main

import (
	"database/sql"
	"encoding/json"
	"log"
)

// --- MessagePack decoding (simplified: fixed struct layout) ---
// In production, use github.com/vmihailenco/msgpack.
// For MVP, IMU batch is a JSON array of objects (compact wire format TBD).

func decodeIMUBatch(data []byte) ([]IMUFrame, error) {
	var batch struct{ Frames []IMUFrame }
	if err := json.Unmarshal(data, &batch); err != nil {
		return nil, err
	}
	return batch.Frames, nil
}

// --- DB operations ---

func newSession(deviceID string) string {
	id := newUUID()
	meta, _ := json.Marshal(map[string]string{"device_id": deviceID})
	db.Exec(`INSERT INTO sessions (id, metadata) VALUES (?, ?)`, id, string(meta))
	return id
}

func endSession(sessionID string) {
	db.Exec(`UPDATE sessions SET ended_at = datetime('now') WHERE id = ?`, sessionID)
}

func storeIMUFrames(sessionID string, frames []IMUFrame) error {
	tx, err := db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()

	stmt, err := tx.Prepare(`INSERT OR IGNORE INTO imu_frames
		(session_id, timestamp_us, ax, ay, az, gx, gy, gz)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)`)
	if err != nil {
		return err
	}
	defer stmt.Close()

	for _, f := range frames {
		_, err := stmt.Exec(sessionID, f.Ts, f.Ax, f.Ay, f.Az, f.Gx, f.Gy, f.Gz)
		if err != nil {
			log.Printf("IMU insert err: %v", err)
		}
	}
	return tx.Commit()
}

func storeImpact(sessionID string, impact *ImpactEvent, x, y, confidence float64) error {
	tdoaJSON, _ := json.Marshal(impact.TdoaNs)
	ampJSON, _ := json.Marshal(impact.Amplitude)
	profileID := ""
	if localizer.profile != nil {
		profileID = localizer.profile.ID
	}
	_, err := db.Exec(`INSERT INTO impacts
		(session_id, timestamp_us, tdoa_ns, amplitude, computed_x, computed_y, confidence, calibration_profile_id)
		VALUES (?, ?, ?, ?, ?, ?, ?, ?)`,
		sessionID, impact.Ts, string(tdoaJSON), string(ampJSON), x, y, confidence, profileID)
	return err
}

// --- Session queries ---
func getSessions() ([]SessionSummary, error) {
	rows, err := db.Query(`SELECT s.id, s.created_at,
		COALESCE((SELECT COUNT(*) FROM impacts WHERE session_id = s.id), 0),
		COALESCE((SELECT (MAX(timestamp_us) - MIN(timestamp_us))/1000000 FROM imu_frames WHERE session_id = s.id), 0)
		FROM sessions s ORDER BY s.created_at DESC LIMIT 50`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var sessions []SessionSummary
	for rows.Next() {
		var s SessionSummary
		if err := rows.Scan(&s.ID, &s.CreatedAt, &s.Swings, &s.DurationS); err != nil {
			continue
		}
		sessions = append(sessions, s)
	}
	return sessions, nil
}

func getSessionImuData(sessionID string, afterUs int64, limit int) ([]IMUFrame, error) {
	rows, err := db.Query(`SELECT timestamp_us, ax, ay, az, gx, gy, gz
		FROM imu_frames WHERE session_id = ? AND timestamp_us > ?
		ORDER BY timestamp_us LIMIT ?`, sessionID, afterUs, limit)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var frames []IMUFrame
	for rows.Next() {
		var f IMUFrame
		var ts uint32
		if err := rows.Scan(&ts, &f.Ax, &f.Ay, &f.Az, &f.Gx, &f.Gy, &f.Gz); err != nil {
			continue
		}
		f.Ts = ts
		frames = append(frames, f)
	}
	return frames, nil
}

func getSessionImpacts(sessionID string) ([]map[string]interface{}, error) {
	rows, err := db.Query(`SELECT timestamp_us, tdoa_ns, amplitude, computed_x, computed_y, confidence
		FROM impacts WHERE session_id = ? ORDER BY timestamp_us`, sessionID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	var impacts []map[string]interface{}
	for rows.Next() {
		var ts uint64
		var tdoaStr, ampStr sql.NullString
		var x, y, conf sql.NullFloat64
		if err := rows.Scan(&ts, &tdoaStr, &ampStr, &x, &y, &conf); err != nil {
			continue
		}
		m := map[string]interface{}{"ts": ts}
		if tdoaStr.Valid {
			var tdoa []int64
			json.Unmarshal([]byte(tdoaStr.String), &tdoa)
			m["tdoa_ns"] = tdoa
		}
		if ampStr.Valid {
			var amp []float64
			json.Unmarshal([]byte(ampStr.String), &amp)
			m["amplitude"] = amp
		}
		if x.Valid {
			m["x_mm"] = x.Float64
		}
		if y.Valid {
			m["y_mm"] = y.Float64
		}
		if conf.Valid {
			m["confidence"] = conf.Float64
		}
		impacts = append(impacts, m)
	}
	return impacts, nil
}
