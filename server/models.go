package main

import "time"

// --- IMU Data ---
type IMUFrame struct {
	Ts uint32 `json:"ts"`
	Ax int16  `json:"ax"`
	Ay int16  `json:"ay"`
	Az int16  `json:"az"`
	Gx int16  `json:"gx"`
	Gy int16  `json:"gy"`
	Gz int16  `json:"gz"`
}

type IMUBatch struct {
	Frames []IMUFrame `json:"frames"`
}

// --- Impact Events ---
type ImpactEvent struct {
	Type      string  `json:"type"` // "impact"
	Ts        uint64  `json:"ts"`
	TdoaNs    []int64 `json:"tdoa_ns"`    // [d21, d31, d41] relative to first-triggered sensor
	Amplitude []float64 `json:"amplitude"` // [a1, a2, a3, a4] normalized
}

// --- WebSocket Messages ---
type WSMessage struct {
	Type      string  `json:"type"`
	SessionID string  `json:"session_id,omitempty"`
	LastTs    uint64  `json:"last_ts,omitempty"`
	Battery   int     `json:"battery,omitempty"`
	RSSI      int     `json:"rssi,omitempty"`
	HeapFree  uint32  `json:"heap_free,omitempty"`
}

// --- REST Models ---
type Session struct {
	ID                   string  `json:"id"`
	CreatedAt            string  `json:"created_at"`
	EndedAt              *string `json:"ended_at,omitempty"`
	CalibrationProfileID *string `json:"calibration_profile_id,omitempty"`
	Metadata             *string `json:"metadata,omitempty"`
}

type SessionSummary struct {
	ID        string `json:"id"`
	CreatedAt string `json:"created_at"`
	Swings    int    `json:"swings"`
	DurationS int    `json:"duration_s"`
}

type ImpactPosition struct {
	X          float64 `json:"x_mm"`
	Y          float64 `json:"y_mm"`
	Confidence float64 `json:"confidence"`
	ProfileID  string  `json:"profile_id"`
}

// --- Calibration ---
type CalibrationSession struct {
	ID        string    `json:"id"`
	CreatedAt time.Time `json:"created_at"`
	Status    string    `json:"status"` // collecting, complete
	GridSize  int       `json:"grid_size"`
	Points    []CalibrationPoint `json:"points,omitempty"`
}

type CalibrationPoint struct {
	GridX  float64 `json:"grid_x"`
	GridY  float64 `json:"grid_y"`
	TdoaNs []int64 `json:"tdoa_ns"`
	TapNum int     `json:"tap_number"`
}

type CalibrationProfile struct {
	ID          string             `json:"id"`
	CreatedAt   string             `json:"created_at"`
	ModelType   string             `json:"model_type"`
	ModelParams string             `json:"model_params,omitempty"`
	RMSE        float64            `json:"rmse"`
	Metadata    string             `json:"metadata,omitempty"`
}

type LocalizeRequest struct {
	TdoaNs    []int64 `json:"tdoa_ns"` // [d21, d31, d41]
	ProfileID string  `json:"profile_id,omitempty"`
}
