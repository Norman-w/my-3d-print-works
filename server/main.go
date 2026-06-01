// SmartPaddle: Go server entry point.
// - WebSocket endpoint for paddle data ingestion
// - REST API for sessions, calibration, analysis
// - SQLite storage (WAL mode)
// - TDOA impact localizer with polynomial regression

package main

import (
	"log"
	"net/http"
	"os"
	"os/signal"
)

func main() {
	// Init DB
	if err := initDB("smartpaddle.db"); err != nil {
		log.Fatalf("DB init failed: %v", err)
	}
	defer db.Close()

	// Init localizer (load latest calibration profile)
	localizer = NewLocalizer()
	loadLatestProfile()

	// Routes
	http.HandleFunc("/ws/paddle", handleWebSocket)
	http.HandleFunc("/api/sessions", handleSessions)
	http.HandleFunc("/api/sessions/", handleSessionByID)
	http.HandleFunc("/api/calibration/sessions", handleCalibrationSessions)
	http.HandleFunc("/api/calibration/", handleCalibrationByID)
	http.HandleFunc("/api/impact/localize", handleLocalize)
	http.HandleFunc("/api/health", handleHealth)

	// Static: OpenAPI spec + calibration grid PDFs
	http.Handle("/api/openapi.yaml", http.FileServer(http.Dir(".")))
	http.Handle("/api/grids/", http.StripPrefix("/api/grids/", http.FileServer(http.Dir("grids"))))

	port := os.Getenv("PORT")
	if port == "" {
		port = "8000"
	}

	// Graceful shutdown
	go func() {
		sig := make(chan os.Signal, 1)
		signal.Notify(sig, os.Interrupt)
		<-sig
		log.Println("Shutting down...")
		db.Close()
		os.Exit(0)
	}()

	log.Printf("SmartPaddle server on :%s", port)
	log.Fatal(http.ListenAndServe(":"+port, nil))
}
