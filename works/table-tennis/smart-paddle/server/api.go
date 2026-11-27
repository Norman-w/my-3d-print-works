package main

import (
	"encoding/json"
	"log"
	"net/http"
	"strings"
)

// --- REST API handlers ---

func handleHealth(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, map[string]string{"status": "ok"})
}

func handleSessions(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case "GET":
		sessions, _ := getSessions()
		writeJSON(w, sessions)
	case "POST":
		id := newSession("manual")
		writeJSON(w, map[string]string{"session_id": id})
	default:
		http.Error(w, "method not allowed", 405)
	}
}

func handleSessionByID(w http.ResponseWriter, r *http.Request) {
	// URL: /api/sessions/{id}
	parts := strings.Split(strings.TrimPrefix(r.URL.Path, "/api/sessions/"), "/")
	if len(parts) == 0 || parts[0] == "" {
		http.Error(w, "missing session id", 400)
		return
	}
	sessionID := parts[0]
	action := ""
	if len(parts) > 1 {
		action = parts[1]
	}

	switch {
	case action == "imu" && r.Method == "GET":
		handleSessionIMU(w, r, sessionID)
	case action == "impacts" && r.Method == "GET":
		handleSessionImpacts(w, r, sessionID)
	case action == "" && r.Method == "DELETE":
		endSession(sessionID)
		writeJSON(w, map[string]string{"status": "ended"})
	case action == "" && r.Method == "GET":
		row := db.QueryRow(`SELECT id, created_at, ended_at, calibration_profile_id, metadata
			FROM sessions WHERE id = ?`, sessionID)
		var s Session
		if err := row.Scan(&s.ID, &s.CreatedAt, &s.EndedAt, &s.CalibrationProfileID, &s.Metadata); err != nil {
			http.Error(w, "not found", 404)
			return
		}
		writeJSON(w, s)
	default:
		http.Error(w, "not found", 404)
	}
}

func handleSessionIMU(w http.ResponseWriter, r *http.Request, sessionID string) {
	afterUs := int64(0)
	limit := 10000
	r.ParseForm()
	if v := r.FormValue("after"); v != "" {
		_ = json.Unmarshal([]byte(v), &afterUs)
	}
	if v := r.FormValue("limit"); v != "" {
		_ = json.Unmarshal([]byte(v), &limit)
	}
	frames, err := getSessionImuData(sessionID, afterUs, limit)
	if err != nil {
		writeJSON(w, map[string]string{"error": err.Error()})
		return
	}
	writeJSON(w, frames)
}

func handleSessionImpacts(w http.ResponseWriter, r *http.Request, sessionID string) {
	impacts, err := getSessionImpacts(sessionID)
	if err != nil {
		writeJSON(w, map[string]string{"error": err.Error()})
		return
	}
	writeJSON(w, impacts)
}

func handleCalibrationSessions(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case "POST":
		// Start new calibration session
		var req struct{ GridSize int }
		if r.Body != nil {
			json.NewDecoder(r.Body).Decode(&req)
		}
		if req.GridSize == 0 {
			req.GridSize = 7
		}
		session, err := newCalibrationSession(req.GridSize)
		if err != nil {
			writeJSON(w, map[string]string{"error": err.Error()})
			return
		}
		writeJSON(w, session)
	case "GET":
		// List calibration profiles
		rows, err := db.Query(`SELECT id, created_at, model_type, model_params, rmse
			FROM calibration_profiles ORDER BY created_at DESC`)
		if err != nil {
			writeJSON(w, []interface{}{})
			return
		}
		defer rows.Close()

		var profiles []CalibrationProfile
		for rows.Next() {
			var p CalibrationProfile
			if err := rows.Scan(&p.ID, &p.CreatedAt, &p.ModelType, &p.ModelParams, &p.RMSE); err != nil {
				continue
			}
			profiles = append(profiles, p)
		}
		writeJSON(w, profiles)
	default:
		http.Error(w, "method not allowed", 405)
	}
}

func handleCalibrationByID(w http.ResponseWriter, r *http.Request) {
	// URL: /api/calibration/{id} or /api/calibration/{id}/points or /api/calibration/{id}/complete
	path := strings.TrimPrefix(r.URL.Path, "/api/calibration/")
	parts := strings.Split(path, "/")
	if len(parts) == 0 || parts[0] == "" {
		http.Error(w, "missing profile id", 400)
		return
	}
	profileID := parts[0]
	action := ""
	if len(parts) > 1 {
		action = parts[1]
	}

	switch {
	case action == "points" && r.Method == "POST":
		// Add calibration point
		var p CalibrationPoint
		if err := json.NewDecoder(r.Body).Decode(&p); err != nil {
			writeJSON(w, map[string]string{"error": "invalid body"})
			return
		}
		if err := addCalibrationPoint(profileID, p); err != nil {
			writeJSON(w, map[string]string{"error": err.Error()})
			return
		}
		writeJSON(w, map[string]string{"status": "ok"})

	case action == "complete" && r.Method == "POST":
		// Finish calibration, fit model
		profile, err := completeCalibration(profileID)
		if err != nil {
			writeJSON(w, map[string]string{"error": err.Error()})
			return
		}
		writeJSON(w, profile)

	default:
		http.Error(w, "not found", 404)
	}
}

func handleLocalize(w http.ResponseWriter, r *http.Request) {
	if r.Method != "POST" {
		http.Error(w, "method not allowed", 405)
		return
	}
	var req LocalizeRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeJSON(w, map[string]string{"error": "invalid body"})
		return
	}
	if localizer == nil || localizer.model == nil {
		writeJSON(w, map[string]string{"error": "no calibration profile loaded"})
		return
	}

	x, y, conf := localizer.localize(req.TdoaNs)
	writeJSON(w, ImpactPosition{X: x, Y: y, Confidence: conf})
}

// --- Helpers ---

func writeJSON(w http.ResponseWriter, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Access-Control-Allow-Origin", "*")
	if err := json.NewEncoder(w).Encode(v); err != nil {
		log.Printf("JSON encode error: %v", err)
	}
}
