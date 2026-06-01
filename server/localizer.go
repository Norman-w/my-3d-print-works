package main

import "gonum.org/v1/gonum/mat"

// Localizer: converts TDOA values [d21, d31, d41] (ns) → paddle XY position (mm).
// Uses a 2nd-order polynomial model per axis, calibrated per-paddle.

type CalModel struct {
	// Polynomial coefficients for X and Y
	// x = a0 + a1*d21 + a2*d31 + a3*d41 + a4*d21² + a5*d31² + a6*d41² + a7*d21*d31 + a8*d21*d41 + a9*d31*d41
	CoeffX []float64 // len 10
	CoeffY []float64 // len 10
}

type Localizer struct {
	profile *CalibrationProfile
	model   *CalModel
}

var localizer *Localizer

func NewLocalizer() *Localizer {
	return &Localizer{}
}

func loadLatestProfile() {
	row := db.QueryRow(`SELECT id, created_at, model_type, model_params, rmse
		FROM calibration_profiles ORDER BY created_at DESC LIMIT 1`)
	var p CalibrationProfile
	var params string
	err := row.Scan(&p.ID, &p.CreatedAt, &p.ModelType, &params, &p.RMSE)
	if err != nil {
		return
	}
	p.ModelParams = params

	l := NewLocalizer()
	if err := l.loadModel(&p); err != nil {
		return
	}
	localizer = l
}

func (l *Localizer) loadModel(profile *CalibrationProfile) error {
	l.profile = profile
	l.model = &CalModel{
		CoeffX: make([]float64, 10),
		CoeffY: make([]float64, 10),
	}
	// Parse model_params JSON into coefficient arrays
	// format: {"cx":[a0..a9], "cy":[b0..b9]}
	var params struct {
		Cx []float64 `json:"cx"`
		Cy []float64 `json:"cy"`
	}
	if err := jsonUnmarshal(profile.ModelParams, &params); err != nil {
		return err
	}
	copy(l.model.CoeffX, params.Cx)
	copy(l.model.CoeffY, params.Cy)
	return nil
}

// localize converts TDOA values to paddle coordinates.
// tdoaNs = [d21, d31, d41] where d21 = (ch1_ts - ch0_ts) in nanoseconds, etc.
// Returns x, y in mm relative to blade center, and confidence [0-1].
func (l *Localizer) localize(tdoaNs []int64) (x, y, confidence float64) {
	if l.model == nil || len(tdoaNs) < 3 {
		return 0, 0, 0
	}

	d21 := float64(tdoaNs[0])
	d31 := float64(tdoaNs[1])
	d41 := float64(tdoaNs[2])

	cx := l.model.CoeffX
	cy := l.model.CoeffY

	// 2nd-order polynomial evaluation
	x = cx[0] +
		cx[1]*d21 + cx[2]*d31 + cx[3]*d41 +
		cx[4]*d21*d21 + cx[5]*d31*d31 + cx[6]*d41*d41 +
		cx[7]*d21*d31 + cx[8]*d21*d41 + cx[9]*d31*d41

	y = cy[0] +
		cy[1]*d21 + cy[2]*d31 + cy[3]*d41 +
		cy[4]*d21*d21 + cy[5]*d31*d31 + cy[6]*d41*d41 +
		cy[7]*d21*d31 + cy[8]*d21*d41 + cy[9]*d31*d41

	// Confidence based on TDOA magnitude (stronger signal = higher confidence)
	confidence = 0.85
	if l.profile != nil {
		confidence = clamp(1.0-l.profile.RMSE/10.0, 0, 1)
	}
	return x, y, confidence
}

// fitPolynomial computes least-squares 2nd-order polynomial coefficients.
// points: calibration data (grid_x, grid_y, d21, d31, d41).
// Returns [coeffX, coeffY].
func fitPolynomial(points []struct{ Gx, Gy, D21, D31, D41 float64 }) ([]float64, []float64, float64) {
	n := len(points)
	if n < 10 {
		return nil, nil, 0
	}

	// Design matrix A: n × 10, each row = [1, d21, d31, d41, d21², d31², d41², d21*d31, d21*d41, d31*d41]
	A := mat.NewDense(n, 10, nil)
	bx := mat.NewVecDense(n, nil)
	by := mat.NewVecDense(n, nil)

	for i, p := range points {
		row := []float64{
			1, p.D21, p.D31, p.D41,
			p.D21 * p.D21, p.D31 * p.D31, p.D41 * p.D41,
			p.D21 * p.D31, p.D21 * p.D41, p.D31 * p.D41,
		}
		A.SetRow(i, row)
		bx.SetVec(i, p.Gx)
		by.SetVec(i, p.Gy)
	}

	// Solve: (AᵀA)x = Aᵀb via QR decomposition
	var qr mat.QR
	qr.Factorize(A)

	var cx, cy mat.VecDense
	qr.SolveVecTo(&cx, false, bx)
	qr.SolveVecTo(&cy, false, by)

	// Compute RMSE
	var residualX, residualY mat.VecDense
	residualX.MulVec(A, &cx)
	residualY.MulVec(A, &cy)
	residualX.SubVec(&residualX, bx)
	residualY.SubVec(&residualY, by)

	rmseX := mat.Norm(&residualX, 2) / float64(n)
	rmseY := mat.Norm(&residualY, 2) / float64(n)
	rmse := (rmseX + rmseY) / 2

	return cx.RawVector().Data, cy.RawVector().Data, rmse
}
