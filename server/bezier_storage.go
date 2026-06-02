package main

import (
	"encoding/json"
	"fmt"
	"net/http"
	"os"
	"path/filepath"
	"regexp"
	"sort"
	"strings"
	"time"
)

var bezierProfileKeys = map[string]bool{
	"blade-front":   true,
	"handle-front":  true,
	"side":          true,
	"handle-bottom": true,
}

var snapshotIDRe = regexp.MustCompile(`^[a-zA-Z0-9][a-zA-Z0-9._-]{0,63}$`)

type bezierStoreRequest struct {
	Profiles map[string]json.RawMessage `json:"profiles"`
}

type bezierStoreResponse struct {
	Path           string   `json:"path"`
	SavedKeys      []string `json:"saved_keys"`
	MergedFromDisk []string `json:"merged_from_disk"`
	StoredAt       string   `json:"stored_at"`
}

type bezierProjectResponse struct {
	Path     string                     `json:"path"`
	Profiles map[string]json.RawMessage `json:"profiles"`
	Keys     []string                   `json:"keys"`
}

type snapshotMeta struct {
	ID        string   `json:"id"`
	Label     string   `json:"label"`
	CreatedAt string   `json:"created_at"`
	Keys      []string `json:"keys"`
}

type snapshotFile struct {
	ID        string                     `json:"id"`
	Label     string                     `json:"label"`
	CreatedAt string                     `json:"created_at"`
	Profiles  map[string]json.RawMessage `json:"profiles"`
}

type snapshotCreateRequest struct {
	Label    string                     `json:"label"`
	Profiles map[string]json.RawMessage `json:"profiles"`
}

func setBezierCORS(w http.ResponseWriter) {
	w.Header().Set("Access-Control-Allow-Origin", "*")
	w.Header().Set("Access-Control-Allow-Methods", "GET, POST, PUT, OPTIONS")
	w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
}

func bezierProfilesFilePath() (string, error) {
	if p := os.Getenv("BEZIER_PROFILES_PATH"); p != "" {
		return filepath.Abs(p)
	}
	candidates := []string{
		filepath.Join("..", "web", "src", "data", "userBezierProfiles.json"),
		filepath.Join("web", "src", "data", "userBezierProfiles.json"),
	}
	for _, rel := range candidates {
		abs, err := filepath.Abs(rel)
		if err != nil {
			continue
		}
		if _, err := os.Stat(filepath.Dir(abs)); err == nil {
			return abs, nil
		}
	}
	return "", fmt.Errorf("cannot locate web/src/data/userBezierProfiles.json (set BEZIER_PROFILES_PATH)")
}

func relPathIfPossible(abs string) string {
	if wd, err := os.Getwd(); err == nil {
		if r, err := filepath.Rel(wd, abs); err == nil && !strings.HasPrefix(r, "..") {
			return r
		}
	}
	return abs
}

func loadBezierProfilesFile(path string) (map[string]json.RawMessage, error) {
	out := make(map[string]json.RawMessage)
	raw, err := os.ReadFile(path)
	if err != nil {
		if os.IsNotExist(err) {
			return out, nil
		}
		return nil, err
	}
	if err := json.Unmarshal(raw, &out); err != nil {
		return nil, err
	}
	return out, nil
}

func writeBezierProfilesFile(path string, data map[string]json.RawMessage) error {
	if err := os.MkdirAll(filepath.Dir(path), 0o755); err != nil {
		return err
	}
	encoded, err := json.MarshalIndent(data, "", "  ")
	if err != nil {
		return err
	}
	encoded = append(encoded, '\n')
	tmp := path + ".tmp"
	if err := os.WriteFile(tmp, encoded, 0o644); err != nil {
		return err
	}
	return os.Rename(tmp, path)
}

func profileKeys(data map[string]json.RawMessage) []string {
	keys := make([]string, 0, len(data))
	for k := range data {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	return keys
}

func validateProfileMap(data map[string]json.RawMessage, requireCore bool) error {
	if len(data) == 0 {
		return fmt.Errorf("profiles is empty")
	}
	for key, raw := range data {
		if !bezierProfileKeys[key] {
			return fmt.Errorf("unknown profile key: %s", key)
		}
		if !json.Valid(raw) {
			return fmt.Errorf("invalid profile JSON for %s", key)
		}
	}
	if requireCore {
		if _, ok := data["blade-front"]; !ok {
			return fmt.Errorf("blade-front required")
		}
		if _, ok := data["handle-front"]; !ok {
			return fmt.Errorf("handle-front required")
		}
	}
	return nil
}

func mergeProfileMaps(base, incoming map[string]json.RawMessage) {
	for k, v := range incoming {
		base[k] = v
	}
}

func newSnapshotID() string {
	return time.Now().UTC().Format("20060102-150405") + "-" + newUUID()[:8]
}

func handleBezierProfilesProjectRoute(w http.ResponseWriter, r *http.Request) {
	setBezierCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusOK)
		return
	}
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	handleBezierProfilesProject(w, r)
}

func handleBezierProfilesStoreRoute(w http.ResponseWriter, r *http.Request) {
	setBezierCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusOK)
		return
	}
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	handleBezierProfilesStore(w, r)
}

func handleBezierReimportFileRoute(w http.ResponseWriter, r *http.Request) {
	setBezierCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusOK)
		return
	}
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	if err := bezierImportFromProjectFile(); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	data, err := bezierDBGetAll()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	jsonPath, _ := bezierProfilesFilePath()
	writeJSON(w, map[string]interface{}{
		"keys":   profileKeys(data),
		"path":   relPathIfPossible(jsonPath),
		"source": "userBezierProfiles.json",
	})
}

func handleBezierProfilesRouter(w http.ResponseWriter, r *http.Request) {
	setBezierCORS(w)
	if r.Method == http.MethodOptions {
		w.WriteHeader(http.StatusOK)
		return
	}

	path := strings.TrimPrefix(r.URL.Path, "/api/bezier-profiles")
	path = strings.Trim(path, "/")

	switch {
	case strings.HasPrefix(path, "profile/") && r.Method == http.MethodPut: {
		target := strings.TrimPrefix(path, "profile/")
		handleBezierProfilePut(w, r, target)
	}
	case path == "snapshots" && r.Method == http.MethodGet:
		handleBezierSnapshotsList(w, r)
	case path == "snapshots" && r.Method == http.MethodPost:
		handleBezierSnapshotsCreate(w, r)
	case strings.HasSuffix(path, "/restore") && r.Method == http.MethodPost: {
		snapID := strings.TrimPrefix(strings.Trim(strings.TrimSuffix(path, "/restore"), "/"), "snapshots/")
		handleBezierSnapshotRestore(w, r, snapID)
	}
	case strings.HasPrefix(path, "snapshots/") && r.Method == http.MethodGet: {
		snapID := strings.TrimPrefix(path, "snapshots/")
		handleBezierSnapshotGet(w, r, snapID)
	}
	default:
		http.Error(w, "not found", http.StatusNotFound)
	}
}

func handleBezierProfilesProject(w http.ResponseWriter, r *http.Request) {
	data, err := bezierDBGetAll()
	if err != nil {
		http.Error(w, "read db: "+err.Error(), http.StatusInternalServerError)
		return
	}
	if len(data) == 0 {
		if err := migrateBezierProfilesFromFileIfEmpty(); err == nil {
			data, err = bezierDBGetAll()
		}
	}
	if err := validateProfileMap(data, true); err != nil {
		http.Error(w, "project: "+err.Error(), http.StatusBadRequest)
		return
	}
	jsonPath, _ := bezierProfilesFilePath()
	writeJSON(w, map[string]interface{}{
		"storage":  "sqlite",
		"path":     relPathIfPossible(jsonPath),
		"profiles": data,
		"keys":     profileKeys(data),
	})
}

func handleBezierProfilePut(w http.ResponseWriter, r *http.Request, target string) {
	if !bezierProfileKeys[target] {
		http.Error(w, "unknown target", http.StatusBadRequest)
		return
	}
	var raw json.RawMessage
	if err := json.NewDecoder(r.Body).Decode(&raw); err != nil {
		http.Error(w, "invalid JSON", http.StatusBadRequest)
		return
	}
	if err := bezierDBPutOne(target, raw); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	writeJSON(w, map[string]interface{}{
		"target":     target,
		"stored_at":  time.Now().UTC().Format(time.RFC3339),
		"storage":    "sqlite",
	})
}

func handleBezierProfilesStore(w http.ResponseWriter, r *http.Request) {
	var req bezierStoreRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid JSON body", http.StatusBadRequest)
		return
	}
	if err := validateProfileMap(req.Profiles, false); err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}

	if err := bezierDBMerge(req.Profiles); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	merged, _ := bezierDBGetAll()
	var saved []string
	for k := range req.Profiles {
		saved = append(saved, k)
	}
	sort.Strings(saved)
	var kept []string
	for k := range merged {
		found := false
		for _, s := range saved {
			if s == k {
				found = true
				break
			}
		}
		if !found {
			kept = append(kept, k)
		}
	}
	sort.Strings(kept)
	jsonPath, _ := bezierProfilesFilePath()
	writeJSON(w, bezierStoreResponse{
		Path:           relPathIfPossible(jsonPath) + " (+ SQLite)",
		SavedKeys:      saved,
		MergedFromDisk: kept,
		StoredAt:       time.Now().UTC().Format(time.RFC3339),
	})
}

func handleBezierSnapshotsList(w http.ResponseWriter, r *http.Request) {
	list, err := bezierDBListSnapshots()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	if list == nil {
		list = []snapshotMeta{}
	}
	writeJSON(w, map[string]interface{}{"snapshots": list})
}

func handleBezierSnapshotsCreate(w http.ResponseWriter, r *http.Request) {
	var req snapshotCreateRequest
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "invalid JSON body", http.StatusBadRequest)
		return
	}

	var data map[string]json.RawMessage
	var err error
	if len(req.Profiles) > 0 {
		data = req.Profiles
	} else {
		data, err = bezierDBGetAll()
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
	}
	label := strings.TrimSpace(req.Label)
	snap, err := bezierDBCreateSnapshot(label, data)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadRequest)
		return
	}
	writeJSON(w, map[string]interface{}{
		"id":         snap.ID,
		"label":      snap.Label,
		"created_at": snap.CreatedAt,
		"keys":       profileKeys(snap.Profiles),
		"storage":    "sqlite",
	})
}

func handleBezierSnapshotGet(w http.ResponseWriter, r *http.Request, id string) {
	if !snapshotIDRe.MatchString(id) {
		http.Error(w, "invalid snapshot id", http.StatusBadRequest)
		return
	}
	snap, err := bezierDBGetSnapshot(id)
	if err != nil {
		http.Error(w, "not found", http.StatusNotFound)
		return
	}
	writeJSON(w, snap)
}

func handleBezierSnapshotRestore(w http.ResponseWriter, r *http.Request, id string) {
	if !snapshotIDRe.MatchString(id) {
		http.Error(w, "invalid snapshot id", http.StatusBadRequest)
		return
	}
	snap, err := bezierDBRestoreSnapshot(id)
	if err != nil {
		http.Error(w, "not found", http.StatusNotFound)
		return
	}
	jsonPath, _ := bezierProfilesFilePath()
	writeJSON(w, map[string]interface{}{
		"restored_id": id,
		"label":       snap.Label,
		"path":        relPathIfPossible(jsonPath),
		"keys":        profileKeys(snap.Profiles),
		"stored_at":   time.Now().UTC().Format(time.RFC3339),
		"storage":     "sqlite",
	})
}
