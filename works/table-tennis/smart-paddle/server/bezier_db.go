package main

import (
	"encoding/json"
	"fmt"
	"log"
	"sort"
	"time"
)

func initBezierDB() error {
	queries := []string{
		`CREATE TABLE IF NOT EXISTS bezier_profiles (
			target TEXT PRIMARY KEY,
			json TEXT NOT NULL,
			updated_at TEXT NOT NULL
		)`,
		`CREATE TABLE IF NOT EXISTS bezier_snapshots (
			id TEXT PRIMARY KEY,
			label TEXT NOT NULL,
			profiles_json TEXT NOT NULL,
			created_at TEXT NOT NULL
		)`,
	}
	for _, q := range queries {
		if _, err := db.Exec(q); err != nil {
			return err
		}
	}
	return migrateBezierProfilesFromFileIfEmpty()
}

func migrateBezierProfilesFromFileIfEmpty() error {
	var n int
	if err := db.QueryRow(`SELECT COUNT(*) FROM bezier_profiles`).Scan(&n); err != nil {
		return err
	}
	if n > 0 {
		return nil
	}
	path, err := bezierProfilesFilePath()
	if err != nil {
		return nil
	}
	data, err := loadBezierProfilesFile(path)
	if err != nil || len(data) == 0 {
		return err
	}
	if err := validateProfileMap(data, true); err != nil {
		log.Printf("bezier: skip file migration: %v", err)
		return nil
	}
	if err := bezierDBReplaceAll(data); err != nil {
		return err
	}
	log.Printf("bezier: migrated %d profiles from %s into SQLite", len(data), path)
	return syncBezierProfilesToJSONFile(data)
}

func bezierDBGetAll() (map[string]json.RawMessage, error) {
	rows, err := db.Query(`SELECT target, json FROM bezier_profiles ORDER BY target`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	out := make(map[string]json.RawMessage)
	for rows.Next() {
		var target, raw string
		if err := rows.Scan(&target, &raw); err != nil {
			return nil, err
		}
		out[target] = json.RawMessage(raw)
	}
	return out, rows.Err()
}

func bezierDBReplaceAll(data map[string]json.RawMessage) error {
	tx, err := db.Begin()
	if err != nil {
		return err
	}
	defer tx.Rollback()
	if _, err := tx.Exec(`DELETE FROM bezier_profiles`); err != nil {
		return err
	}
	now := time.Now().UTC().Format(time.RFC3339)
	keys := profileKeys(data)
	for _, k := range keys {
		raw := data[k]
		if _, err := tx.Exec(
			`INSERT INTO bezier_profiles (target, json, updated_at) VALUES (?, ?, ?)`,
			k, string(raw), now,
		); err != nil {
			return err
		}
	}
	return tx.Commit()
}

func bezierDBMerge(incoming map[string]json.RawMessage) error {
	merged, err := bezierDBGetAll()
	if err != nil {
		return err
	}
	if merged == nil {
		merged = make(map[string]json.RawMessage)
	}
	mergeProfileMaps(merged, incoming)
	if err := validateProfileMap(merged, true); err != nil {
		return err
	}
	if err := bezierDBReplaceAll(merged); err != nil {
		return err
	}
	return syncBezierProfilesToJSONFile(merged)
}

func bezierDBPutOne(target string, raw json.RawMessage) error {
	if !bezierProfileKeys[target] {
		return fmt.Errorf("unknown profile key: %s", target)
	}
	if !json.Valid(raw) {
		return fmt.Errorf("invalid profile JSON for %s", target)
	}
	now := time.Now().UTC().Format(time.RFC3339)
	_, err := db.Exec(
		`INSERT INTO bezier_profiles (target, json, updated_at) VALUES (?, ?, ?)
		 ON CONFLICT(target) DO UPDATE SET json=excluded.json, updated_at=excluded.updated_at`,
		target, string(raw), now,
	)
	if err != nil {
		return err
	}
	all, err := bezierDBGetAll()
	if err != nil {
		return err
	}
	return syncBezierProfilesToJSONFile(all)
}

func syncBezierProfilesToJSONFile(data map[string]json.RawMessage) error {
	path, err := bezierProfilesFilePath()
	if err != nil {
		return err
	}
	return writeBezierProfilesFile(path, data)
}

func bezierDBListSnapshots() ([]snapshotMeta, error) {
	rows, err := db.Query(`SELECT id, label, created_at, profiles_json FROM bezier_snapshots ORDER BY created_at DESC`)
	if err != nil {
		return nil, err
	}
	defer rows.Close()
	var out []snapshotMeta
	for rows.Next() {
		var id, label, created, raw string
		if err := rows.Scan(&id, &label, &created, &raw); err != nil {
			return nil, err
		}
		var data map[string]json.RawMessage
		if err := json.Unmarshal([]byte(raw), &data); err != nil {
			continue
		}
		out = append(out, snapshotMeta{
			ID:        id,
			Label:     label,
			CreatedAt: created,
			Keys:      profileKeys(data),
		})
	}
	if out == nil {
		out = []snapshotMeta{}
	}
	return out, rows.Err()
}

func bezierDBCreateSnapshot(label string, data map[string]json.RawMessage) (*snapshotFile, error) {
	if err := validateProfileMap(data, true); err != nil {
		return nil, err
	}
	id := newSnapshotID()
	if label == "" {
		label = id
	}
	created := time.Now().UTC().Format(time.RFC3339)
	encoded, err := json.Marshal(data)
	if err != nil {
		return nil, err
	}
	_, err = db.Exec(
		`INSERT INTO bezier_snapshots (id, label, profiles_json, created_at) VALUES (?, ?, ?, ?)`,
		id, label, string(encoded), created,
	)
	if err != nil {
		return nil, err
	}
	return &snapshotFile{ID: id, Label: label, CreatedAt: created, Profiles: data}, nil
}

func bezierDBGetSnapshot(id string) (*snapshotFile, error) {
	var label, created, raw string
	err := db.QueryRow(
		`SELECT label, created_at, profiles_json FROM bezier_snapshots WHERE id = ?`, id,
	).Scan(&label, &created, &raw)
	if err != nil {
		return nil, err
	}
	var data map[string]json.RawMessage
	if err := json.Unmarshal([]byte(raw), &data); err != nil {
		return nil, err
	}
	return &snapshotFile{ID: id, Label: label, CreatedAt: created, Profiles: data}, nil
}

func bezierDBRestoreSnapshot(id string) (*snapshotFile, error) {
	snap, err := bezierDBGetSnapshot(id)
	if err != nil {
		return nil, err
	}
	if err := bezierDBReplaceAll(snap.Profiles); err != nil {
		return nil, err
	}
	return snap, nil
}

// Export file for OpenSCAD scripts when DB is authoritative.
func bezierExportProjectFile() error {
	data, err := bezierDBGetAll()
	if err != nil {
		return err
	}
	if len(data) == 0 {
		return nil
	}
	return syncBezierProfilesToJSONFile(data)
}

// Optional: import file into DB (manual API).
func bezierImportFromProjectFile() error {
	path, err := bezierProfilesFilePath()
	if err != nil {
		return err
	}
	data, err := loadBezierProfilesFile(path)
	if err != nil {
		return err
	}
	if err := validateProfileMap(data, true); err != nil {
		return err
	}
	if err := bezierDBReplaceAll(data); err != nil {
		return err
	}
	sort.Strings(profileKeys(data))
	return nil
}
