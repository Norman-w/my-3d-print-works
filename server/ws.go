package main

import (
	"encoding/json"
	"log"
	"net/http"
	"sync"

	"github.com/gorilla/websocket"
)

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool { return true },
}

// Active connections: sessionID → *websocket.Conn
var (
	connsMu sync.RWMutex
	conns   = make(map[string]*websocket.Conn)
)

func handleWebSocket(w http.ResponseWriter, r *http.Request) {
	deviceID := r.URL.Query().Get("device_id")
	if deviceID == "" {
		deviceID = "unknown"
	}

	conn, err := upgrader.Upgrade(w, r, nil)
	if err != nil {
		log.Printf("WS upgrade failed: %v", err)
		return
	}
	defer conn.Close()

	// Create session
	sessionID := newSession(deviceID)
	connsMu.Lock()
	conns[sessionID] = conn
	connsMu.Unlock()
	defer func() {
		connsMu.Lock()
		delete(conns, sessionID)
		connsMu.Unlock()
		endSession(sessionID)
	}()

	// Send hello
	hello := WSMessage{Type: "hello", SessionID: sessionID}
	if b, err := json.Marshal(hello); err == nil {
		conn.WriteMessage(websocket.TextMessage, b)
	}
	log.Printf("Paddle connected: device=%s session=%s", deviceID, sessionID)

	// Read loop: handle both binary (IMU) and text (impact/status) frames
	for {
		msgType, data, err := conn.ReadMessage()
		if err != nil {
			log.Printf("WS read err: %v", err)
			break
		}

		switch msgType {
		case websocket.BinaryMessage:
			handleIMUBinary(sessionID, data)
		case websocket.TextMessage:
			handleTextMessage(sessionID, conn, data)
		}
	}
}

func handleIMUBinary(sessionID string, data []byte) {
	// Parse MessagePack array of IMUFrame structs
	frames, err := decodeIMUBatch(data)
	if err != nil {
		log.Printf("IMU decode error: %v", err)
		return
	}
	if err := storeIMUFrames(sessionID, frames); err != nil {
		log.Printf("IMU store error: %v", err)
	}
}

func handleTextMessage(sessionID string, conn *websocket.Conn, data []byte) {
	// Try parsing as WSMessage first (for "status" type)
	var msg WSMessage
	if json.Unmarshal(data, &msg) == nil {
		switch msg.Type {
		case "status":
			log.Printf("Status: battery=%d rssi=%d heap=%d", msg.Battery, msg.RSSI, msg.HeapFree)
		case "close":
			return
		}
		return
	}

	// Try parsing as ImpactEvent
	var impact ImpactEvent
	if json.Unmarshal(data, &impact) == nil && impact.Type == "impact" {
		handleImpact(sessionID, &impact)
		return
	}
}

func handleImpact(sessionID string, impact *ImpactEvent) {
	// Localize if localizer has active profile
	var x, y, confidence float64
	if localizer != nil && localizer.profile != nil {
		x, y, confidence = localizer.localize(impact.TdoaNs)
	}

	storeImpact(sessionID, impact, x, y, confidence)

	// Send back position to paddle (for LED feedback etc.)
	connsMu.RLock()
	conn, ok := conns[sessionID]
	connsMu.RUnlock()
	if ok {
		resp := map[string]interface{}{
			"type":       "impact_ack",
			"x_mm":       x,
			"y_mm":       y,
			"confidence": confidence,
		}
		b, _ := json.Marshal(resp)
		conn.WriteMessage(websocket.TextMessage, b)
	}
}

func sendACK(conn *websocket.Conn, lastTs uint64) {
	ack := WSMessage{Type: "ack", LastTs: lastTs}
	b, _ := json.Marshal(ack)
	conn.WriteMessage(websocket.TextMessage, b)
}
