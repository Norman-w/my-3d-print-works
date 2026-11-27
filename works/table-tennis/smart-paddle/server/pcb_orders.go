package main

import (
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strings"
	"time"
)

type pcbOrderFile struct {
	Name        string `json:"name"`
	Path        string `json:"path"`
	DownloadURL string `json:"download_url"`
	Size        int64  `json:"size"`
	ModifiedAt  string `json:"modified_at"`
}

type pcbOrderExportRequest struct {
	Target string `json:"target"`
}

func projectRoot() (string, error) {
	cwd, err := os.Getwd()
	if err != nil {
		return "", err
	}
	root := filepath.Clean(filepath.Join(cwd, ".."))
	if _, err := os.Stat(filepath.Join(root, "pcb", "scripts", "export_order_packages.py")); err != nil {
		return "", fmt.Errorf("cannot locate project root from %s: %w", cwd, err)
	}
	return root, nil
}

func pcbOrdersRoot() (string, error) {
	root, err := projectRoot()
	if err != nil {
		return "", err
	}
	return filepath.Join(root, "fab", "jlcpcb-orders"), nil
}

func listPCBOrderFiles() ([]pcbOrderFile, error) {
	base, err := pcbOrdersRoot()
	if err != nil {
		return nil, err
	}
	if err := os.MkdirAll(base, 0o755); err != nil {
		return nil, err
	}
	files := []pcbOrderFile{}
	err = filepath.Walk(base, func(path string, info os.FileInfo, walkErr error) error {
		if walkErr != nil {
			return walkErr
		}
		if info.IsDir() || (!strings.HasSuffix(info.Name(), ".zip") && info.Name() != "ORDER_PACKAGE_INDEX.json") {
			return nil
		}
		rel, err := filepath.Rel(base, path)
		if err != nil {
			return err
		}
		files = append(files, pcbOrderFile{
			Name:        info.Name(),
			Path:        path,
			DownloadURL: "/api/pcb-orders/download?path=" + strings.ReplaceAll(rel, string(filepath.Separator), "/"),
			Size:        info.Size(),
			ModifiedAt:  info.ModTime().Format(time.RFC3339),
		})
		return nil
	})
	sort.Slice(files, func(i, j int) bool { return files[i].ModifiedAt > files[j].ModifiedAt })
	return files, err
}

func handlePCBOrders(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	files, err := listPCBOrderFiles()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	writeJSON(w, map[string]any{"files": files})
}

func handlePCBOrderExport(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var req pcbOrderExportRequest
	if err := json.NewDecoder(io.LimitReader(r.Body, 4096)).Decode(&req); err != nil {
		http.Error(w, "invalid JSON", http.StatusBadRequest)
		return
	}
	allowed := map[string]bool{"main": true, "tail": true, "separate": true, "panel": true}
	if !allowed[req.Target] {
		http.Error(w, "target must be main, tail, separate, or panel", http.StatusBadRequest)
		return
	}
	root, err := projectRoot()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	base, _ := pcbOrdersRoot()
	out := filepath.Join(base, time.Now().Format("20060102-150405")+"-"+req.Target)
	cmd := exec.Command("python3", filepath.Join(root, "pcb", "scripts", "export_order_packages.py"), "--target", req.Target, "--output", out)
	cmd.Dir = root
	output, err := cmd.CombinedOutput()
	if err != nil {
		w.WriteHeader(http.StatusConflict)
		writeJSON(w, map[string]any{"ok": false, "error": err.Error(), "output": string(output), "path": out})
		return
	}
	files, listErr := listPCBOrderFiles()
	if listErr != nil {
		http.Error(w, listErr.Error(), http.StatusInternalServerError)
		return
	}
	writeJSON(w, map[string]any{"ok": true, "output": string(output), "path": out, "files": files})
}

func handlePCBOrderDownload(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	base, err := pcbOrdersRoot()
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	rel := filepath.Clean(filepath.FromSlash(r.URL.Query().Get("path")))
	if rel == "." || filepath.IsAbs(rel) || strings.HasPrefix(rel, ".."+string(filepath.Separator)) || rel == ".." {
		http.Error(w, "invalid path", http.StatusBadRequest)
		return
	}
	path := filepath.Join(base, rel)
	resolvedBase, _ := filepath.Abs(base)
	resolvedPath, _ := filepath.Abs(path)
	if !strings.HasPrefix(resolvedPath, resolvedBase+string(filepath.Separator)) {
		http.Error(w, "path outside order directory", http.StatusForbidden)
		return
	}
	info, err := os.Stat(resolvedPath)
	if err != nil || info.IsDir() {
		http.NotFound(w, r)
		return
	}
	w.Header().Set("Content-Disposition", fmt.Sprintf("attachment; filename=%q", info.Name()))
	http.ServeFile(w, r, resolvedPath)
}
