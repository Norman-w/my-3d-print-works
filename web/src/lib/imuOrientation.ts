//#region 导入/依赖
import * as THREE from 'three';
//#endregion

//#region 常量/配置

/**
 * 真实世界参考姿态（人对着屏幕）：
 *   拍头 → 右（+X）
 *   拍柄 → 左（−X）
 *   人头 → 上（+Y），脚 → 下（−Y）
 *   黑面 / IMU 正面 → 屏幕远端（−Z）
 *   IMU 天线 → 天花板（+Y）
 *   IMU 背面 → 朝向人（+Z，近端）
 *
 * IM948 丝印机体系（右手）：+X 右、+Y 前、+Z 垂直芯片向外（正面外法向）。
 * 在上述参考姿态下：
 *   +Y_imu → +Y_three（天线朝天）
 *   +Z_imu → −Z_three（正面朝屏幕远端）
 *   +X_imu → −X_three（朝拍柄 / 左）
 *   拍头 = −X_imu → +X_three
 *
 * 拍模：+Y=拍头，−Y=拍柄，+Z=黑面外法向。
 */

/** ENU（Z=天）→ Three Y-up：(x,y,z)→(x,z,-y) */
const Q_ENU_TO_THREE = new THREE.Quaternion().setFromEuler(
  new THREE.Euler(-Math.PI / 2, 0, 0, 'XYZ'),
);

/**
 * 拍模 → IMU 丝印（v_imu = R · v_model）：
 *   +X_model → +Y_imu
 *   +Y_model → −X_imu  （拍头 → 丝印 −X）
 *   +Z_model → +Z_imu  （黑面 → 丝印正面外）
 *
 * Matrix4.set 为行优先。
 */
const Q_MODEL_TO_IMU = new THREE.Quaternion().setFromRotationMatrix(
  new THREE.Matrix4().set(
    0, -1, 0, 0,
    1, 0, 0, 0,
    0, 0, 1, 0,
    0, 0, 0, 1,
  ),
);

/** 拍柄/拍头沿桨长轴对调（C4 实装丝印与文档差 180°；俯仰/滚转不变） */
const Q_MODEL_HEAD_TAIL_FLIP = new THREE.Quaternion().setFromEuler(
  new THREE.Euler(0, 0, Math.PI, 'XYZ'),
);

const _qImu = new THREE.Quaternion();
const _qOut = new THREE.Quaternion();
const _qMount = new THREE.Quaternion();

//#endregion

//#region 公开 API

export function applyPaddleMountFrame(paddle: THREE.Object3D): void {
  paddle.scale.set(1, 1, 1);
}

/**
 * p_three = R_enu→three · R_body→enu · R_model→body · p_model
 */
export function setPaddleQuaternionFromImu(
  paddle: THREE.Object3D,
  qw: number,
  qx: number,
  qy: number,
  qz: number,
): void {
  applyPaddleMountFrame(paddle);
  _qImu.set(qx, qy, qz, qw);
  _qMount.copy(Q_MODEL_TO_IMU).multiply(Q_MODEL_HEAD_TAIL_FLIP);
  _qOut.copy(Q_ENU_TO_THREE).multiply(_qImu).multiply(_qMount);
  paddle.quaternion.copy(_qOut);
}

//#endregion
