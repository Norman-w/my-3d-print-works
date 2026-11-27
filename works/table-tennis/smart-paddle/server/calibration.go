package main

import (
	"encoding/json"
	"log"
	"math"
	"time"
)

// calibration.go: Calibration session management + polynomial model fitting.

func newCalibrationSession(gridSize int) (*CalibrationSession, error) {
	id := newUUID()
	now := time.Now().UTC()
	_, err := db.Exec(`INSERT INTO calibration_profiles
		(id, created_at, model_type, model_params, rmse, metadata)
		VALUES (?, ?, 'pending', '', 0, ?)`,
		id, now.Format(time.RFC3339), `{"grid_size":`+itoa(gridSize)+`}`)
	if err != nil {
		return nil, err
	}
	return &CalibrationSession{
		ID:        id,
		CreatedAt: now,
		Status:    "collecting",
		GridSize:  gridSize,
	}, nil
}

func addCalibrationPoint(profileID string, p CalibrationPoint) error {
	tdoaJSON, _ := json.Marshal(p.TdoaNs)
	_, err := db.Exec(`INSERT INTO calibration_points
		(profile_id, grid_x, grid_y, tdoa_ns, tap_number)
		VALUES (?, ?, ?, ?, ?)`,
		profileID, p.GridX, p.GridY, string(tdoaJSON), p.TapNum)
	return err
}

func completeCalibration(profileID string) (*CalibrationProfile, error) {
	// Load all calibration points
	rows, err := db.Query(`SELECT grid_x, grid_y, tdoa_ns, tap_number
		FROM calibration_points WHERE profile_id = ?`, profileID)
	if err != nil {
		return nil, err
	}
	defer rows.Close()

	// Group points by grid position, average TDOA across taps
	type gridKey struct{ gx, gy float64 }
	tdoaAccum := make(map[gridKey][]int64)
	tapCount := make(map[gridKey]int)

	for rows.Next() {
		var gx, gy float64
		var tdoaStr string
		var tapNum int
		if err := rows.Scan(&gx, &gy, &tdoaStr, &tapNum); err != nil {
			continue
		}

		var tdoa []int64
		json.Unmarshal([]byte(tdoaStr), &tdoa)

		k := gridKey{math.Round(gx*10) / 10, math.Round(gy*10) / 10}
		if _, ok := tdoaAccum[k]; !ok {
			tdoaAccum[k] = []int64{0, 0, 0}
		}
		for i := range tdoa {
			if i < 3 {
				tdoaAccum[k][i] += tdoa[i]
			}
		}
		tapCount[k]++
	}

	// Average TDOA per grid point
	var fitPoints []struct{ Gx, Gy, D21, D31, D41 float64 }
	for k, accum := range tdoaAccum {
		n := float64(tapCount[k])
		fitPoints = append(fitPoints, struct{ Gx, Gy, D21, D31, D41 float64 }{
			k.gx, k.gy,
			float64(accum[0]) / n, float64(accum[1]) / n, float64(accum[2]) / n,
		})
	}

	if len(fitPoints) < 10 {
		return nil, errBadRequest("need at least 10 grid points for calibration")
	}

	// Fit polynomial model
	coeffX, coeffY, rmse := fitPolynomial(fitPoints)
	if coeffX == nil {
		return nil, errInternal("polynomial fit failed")
	}

	// Save model
	paramsJSON, _ := json.Marshal(map[string][]float64{"cx": coeffX, "cy": coeffY})
	_, err = db.Exec(`UPDATE calibration_profiles
		SET model_type = 'polynomial', model_params = ?, rmse = ?, metadata = json_set(COALESCE(metadata,'{}'), '$.point_count', ?)
		WHERE id = ?`,
		string(paramsJSON), rmse, len(fitPoints), profileID)
	if err != nil {
		return nil, err
	}

	profile := &CalibrationProfile{
		ID:          profileID,
		ModelType:   "polynomial",
		ModelParams: string(paramsJSON),
		RMSE:        rmse,
	}
	log.Printf("Calibration complete: profile=%s rmse=%.2fmm points=%d", profileID, rmse, len(fitPoints))

	// Reload localizer
	loadLatestProfile()
	return profile, nil
}
