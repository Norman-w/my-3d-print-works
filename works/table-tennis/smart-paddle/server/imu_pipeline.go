package main

import (
	"math"
)

// imu_pipeline.go: Madgwick orientation filter + trajectory reconstruction
// Processes raw IMU frames into quaternion orientation and 3D position.

const (
	// Madgwick filter gain
	beta = 0.1
	// Sampling period in seconds (1kHz)
	samplePeriod = 1.0 / 1000.0
)

// Quaternion representation
type Quaternion struct{ W, X, Y, Z float64 }

// MadgwickAHRS updates the quaternion using gyroscope + accelerometer data.
// gx, gy, gz: gyroscope in rad/s
// ax, ay, az: accelerometer in g
// q: previous quaternion, updated in place.
func MadgwickAHRS(gx, gy, gz, ax, ay, az float64, q *Quaternion) {
	// Normalize accelerometer
	norm := math.Sqrt(ax*ax + ay*ay + az*az)
	if norm == 0 {
		return
	}
	ax /= norm
	ay /= norm
	az /= norm

	// Gradient descent algorithm corrective step
	// Objective function: f(q, a) = [2(qx*qz - qw*qy) - ax, ...]
	qw, qx, qy, qz := q.W, q.X, q.Y, q.Z

	// Compute Jacobian and gradient
	f1 := 2*(qx*qz-qw*qy) - ax
	f2 := 2*(qw*qx+qy*qz) - ay
	f3 := 2*(0.5-qx*qx-qy*qy) - az

	J11 := -2 * qy
	J12 := 2 * qz
	J13 := -2 * qw
	J14 := 2 * qx
	J21 := 2 * qx
	J22 := 2 * qw
	J23 := 2 * qz
	J24 := 2 * qy
	J31 := 0.0
	J32 := -4 * qx
	J33 := -4 * qy
	J34 := 0.0

	// Gradient
	gw := J11*f1 + J21*f2 + J31*f3
	gxG := J12*f1 + J22*f2 + J32*f3
	gyG := J13*f1 + J23*f2 + J33*f3
	gzG := J14*f1 + J24*f2 + J34*f3

	// Normalize gradient
	norm = math.Sqrt(gw*gw + gxG*gxG + gyG*gyG + gzG*gzG)
	if norm == 0 {
		return
	}
	gw /= norm
	gxG /= norm
	gyG /= norm
	gzG /= norm

	// Gyroscope quaternion derivative
	qDotW := 0.5*(-qx*gx - qy*gy - qz*gz)
	qDotX := 0.5*(qw*gx + qy*gz - qz*gy)
	qDotY := 0.5*(qw*gy - qx*gz + qz*gx)
	qDotZ := 0.5*(qw*gz + qx*gy - qy*gx)

	// Apply feedback
	qDotW -= beta * gw
	qDotX -= beta * gxG
	qDotY -= beta * gyG
	qDotZ -= beta * gzG

	// Integrate
	q.W += qDotW * samplePeriod
	q.X += qDotX * samplePeriod
	q.Y += qDotY * samplePeriod
	q.Z += qDotZ * samplePeriod

	// Normalize
	norm = math.Sqrt(q.W*q.W + q.X*q.X + q.Y*q.Y + q.Z*q.Z)
	q.W /= norm
	q.X /= norm
	q.Y /= norm
	q.Z /= norm
}

// Vec3 is a 3D vector.
type Vec3 struct{ X, Y, Z float64 }

// TrajectoryPoint is a single point in the reconstructed trajectory.
type TrajectoryPoint struct {
	TimestampUs uint64
	Position    Vec3
	Velocity    Vec3
	Orientation Quaternion
}

// RotateVec rotates a vector by a quaternion.
func (q *Quaternion) RotateVec(v Vec3) Vec3 {
	qw, qx, qy, qz := q.W, q.X, q.Y, q.Z
	// v' = q * v * q_conjugate
	// Optimized:
	return Vec3{
		X: v.X*(qw*qw+qx*qx-qy*qy-qz*qz) + v.Y*(2*qx*qy-2*qw*qz) + v.Z*(2*qx*qz+2*qw*qy),
		Y: v.X*(2*qx*qy+2*qw*qz) + v.Y*(qw*qw-qx*qx+qy*qy-qz*qz) + v.Z*(2*qy*qz-2*qw*qx),
		Z: v.X*(2*qx*qz-2*qw*qy) + v.Y*(2*qy*qz+2*qw*qx) + v.Z*(qw*qw-qx*qx-qy*qy+qz*qz),
	}
}

// ReconstructTrajectory processes IMU frames into trajectory points.
// Uses ZUPT (zero-velocity update) when gyro magnitude is below threshold.
// input: raw IMU frames (accel in mg, gyro in dps * 1000)
// output: trajectory points in paddle-local frame
func ReconstructTrajectory(frames []IMUFrame) []TrajectoryPoint {
	if len(frames) == 0 {
		return nil
	}

	var points []TrajectoryPoint
	var q Quaternion = Quaternion{W: 1, X: 0, Y: 0, Z: 0} // Identity
	var pos Vec3
	var vel Vec3

	gravity := Vec3{Z: -1.0} // Gravity in world frame (1g down)

	const gyroThreshold = 50.0  // dps, below this = stationary
	const accelDeadband = 0.05  // g, below this = noise

	for _, f := range frames {
		// Convert raw values to physical units
		// IMU raw: mg, dps*1000 (from ICM-42688-P scaling)
		ax := float64(f.Ax) / 1000.0 // mg → g
		ay := float64(f.Ay) / 1000.0
		az := float64(f.Az) / 1000.0
		gx := float64(f.Gx) / 57296.0 // LSB → rad/s (assuming ±2000dps = 16.4 LSB/dps)
		gy := float64(f.Gy) / 57296.0
		gz := float64(f.Gz) / 57296.0

		// Gyro magnitude
		gyroMag := math.Sqrt(gx*gx + gy*gy + gz*gz)

		// Madgwick update
		MadgwickAHRS(gx, gy, gz, ax, ay, az, &q)

		// Rotate accel to world frame and subtract gravity
		accelWorld := q.RotateVec(Vec3{ax, ay, az})
		accelWorld.X -= gravity.X
		accelWorld.Y -= gravity.Y
		accelWorld.Z -= gravity.Z

		// Apply deadband
		if math.Abs(accelWorld.X) < accelDeadband {
			accelWorld.X = 0
		}
		if math.Abs(accelWorld.Y) < accelDeadband {
			accelWorld.Y = 0
		}
		if math.Abs(accelWorld.Z) < accelDeadband {
			accelWorld.Z = 0
		}

		// Zero-Velocity Update: if stationary, force velocity to zero
		if gyroMag*57.3 < gyroThreshold { // rad/s → dps
			vel = Vec3{}
		}

		// Integrate acceleration → velocity (m/s), velocity → position (m)
		// 1g = 9.81 m/s²
		dt := samplePeriod
		vel.X += accelWorld.X * 9.81 * dt
		vel.Y += accelWorld.Y * 9.81 * dt
		vel.Z += accelWorld.Z * 9.81 * dt

		// High-pass filter on velocity to remove residual drift
		const alpha = 0.999
		vel.X *= alpha
		vel.Y *= alpha
		vel.Z *= alpha

		pos.X += vel.X * dt
		pos.Y += vel.Y * dt
		pos.Z += vel.Z * dt

		points = append(points, TrajectoryPoint{
			TimestampUs: uint64(f.Ts),
			Position:     pos,
			Velocity:     vel,
			Orientation:  q,
		})
	}

	return points
}
