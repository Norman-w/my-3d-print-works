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
	if err := initBezierDB(); err != nil {
		log.Fatalf("Bezier DB init failed: %v", err)
	}

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
	// Explicit routes (Go ServeMux: trailing-slash pattern alone misses some paths on older mux)
	http.HandleFunc("/api/bezier-profiles/project", handleBezierProfilesProjectRoute)
	http.HandleFunc("/api/bezier-profiles/store", handleBezierProfilesStoreRoute)
	http.HandleFunc("/api/bezier-profiles/reimport-file", handleBezierReimportFileRoute)
	http.HandleFunc("/api/bezier-profiles/", handleBezierProfilesRouter)
	http.HandleFunc("/api/pcb-orders", handlePCBOrders)
	http.HandleFunc("/api/pcb-orders/export", handlePCBOrderExport)
	http.HandleFunc("/api/pcb-orders/download", handlePCBOrderDownload)

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
