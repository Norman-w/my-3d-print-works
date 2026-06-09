const scaleAccel = 0.00478515625; // 加速度 [-16g~+16g]    9.8*16/32768
const scaleQuat = 0.000030517578125; // 四元数 [-1~+1]         1/32768
const scaleAngle = 0.0054931640625; // 角度   [-180~+180]     180/32768
const scaleAngleSpeed = 0.06103515625; // 角速度 [-2000~+2000]    2000/32768
const scaleMag = 0.15106201171875; // 磁场 [-4950~+4950]   4950/32768
const scaleTemperature = 0.01; // 温度
const scaleAirPressure = 0.0002384185791; // 气压 [-2000~+2000]    2000/8388608
const scaleHeight = 0.0010728836; // 高度 [-9000~+9000]    9000/8388608

function pow2(x) {
  return x * x;
}

function int16(buffer, offset) {
  let value = buffer[offset] | (buffer[offset + 1] << 8);
  return value & 0x8000 ? value - 0x10000 : value;
}

function int24(buffer, offset) {
  let value = buffer[offset] | (buffer[offset + 1] << 8) | (buffer[offset + 2] << 16);
  return value & 0x800000 ? value - 0x1000000 : value;
}

function int32(buffer, offset) {
  return buffer[offset] | (buffer[offset + 1] << 8) | (buffer[offset + 2] << 16) | (buffer[offset + 3] << 24);
}

function Cmd_RxUnpack(buf, Dlen) {
  let ctl;
  let L;
  let tmpU8;
  let tmpU16;
  let tmpU32;
  let tmpX, tmpY, tmpZ, tmpAbs;

  switch (buf[0]) {
    case 0x02:
      console.log("sensor off success");
      break;
    case 0x03:
      console.log("sensor on success");
      break;
    case 0x32:
      console.log("compass calibrate begin");
      break;
    case 0x04:
      console.log("compass calibrate end");
      break;
    case 0x05:
      console.log("z-axes to zero success");
      break;
    case 0x06:
      console.log("WorldXYZ-axes to zero success");
      break;
    case 0x07:
      console.log("acceleration calibration, Hold still for 9 seconds");
      break;
    case 0x08:
      console.log("axesZ WorldXYZ-axes to zero success");
      break;
    case 0x10:
      console.log("still limit: " + buf[1]);
      console.log("still to zero: " + buf[2]);
      console.log("move to zero: " + buf[3]);
      console.log("compass: " + ((buf[4] >> 0) & 0x01 ? "on" : "off"));
      console.log("barometer filter: " + ((buf[4] >> 1) & 0x03));
      console.log("IMU: " + ((buf[4] >> 3) & 0x01 ? "on" : "off"));
      console.log("auto report: " + ((buf[4] >> 4) & 0x01 ? "on" : "off"));
      console.log("FPS: " + buf[5]);
      console.log("gyro filter: " + buf[6]);
      console.log("acc filter: " + buf[7]);
      console.log("compass filter: " + buf[8]);
      console.log("subscribe tag: 0x" + ((buf[10] << 8) | buf[9]).toString(16));
      console.log("charged state: " + buf[11]);
      console.log("battery level: " + buf[12] + "%");
      console.log("battery voltage: " + ((buf[14] << 8) | buf[13]) + " mv");
      console.log("Mac: " + buf.slice(15, 21).map(x => x.toString(16).padStart(2, '0')).join(':'));
      console.log("version: " + String.fromCharCode.apply(null, buf.slice(21, 27)));
      console.log("product model: " + String.fromCharCode.apply(null, buf.slice(27, 33)));
      break;
    case 0x11:
      ctl = (buf[2] << 8) | buf[1];
      console.log("subscribe tag: 0x" + ctl.toString(16));
      console.log("ms: " + int32(buf, 3));
      L = 7;
      if (ctl & 0x0001) {
        tmpX = int16(buf, L) * scaleAccel; L += 2; console.log("aX: " + tmpX.toFixed(3));
        tmpY = int16(buf, L) * scaleAccel; L += 2; console.log("aY: " + tmpY.toFixed(3));
        tmpZ = int16(buf, L) * scaleAccel; L += 2; console.log("aZ: " + tmpZ.toFixed(3));
        tmpAbs = Math.sqrt(pow2(tmpX) + pow2(tmpY) + pow2(tmpZ)); console.log("a_abs: " + tmpAbs.toFixed(3));
      }
      if (ctl & 0x0002) {
        tmpX = int16(buf, L) * scaleAccel; L += 2; console.log("AX: " + tmpX.toFixed(3));
        tmpY = int16(buf, L) * scaleAccel; L += 2; console.log("AY: " + tmpY.toFixed(3));
        tmpZ = int16(buf, L) * scaleAccel; L += 2; console.log("AZ: " + tmpZ.toFixed(3));
        tmpAbs = Math.sqrt(pow2(tmpX) + pow2(tmpY) + pow2(tmpZ)); console.log("A_abs: " + tmpAbs.toFixed(3));
      }
      if (ctl & 0x0004) {
        tmpX = int16(buf, L) * scaleAngleSpeed; L += 2; console.log("GX: " + tmpX.toFixed(3));
        tmpY = int16(buf, L) * scaleAngleSpeed; L += 2; console.log("GY: " + tmpY.toFixed(3));
        tmpZ = int16(buf, L) * scaleAngleSpeed; L += 2; console.log("GZ: " + tmpZ.toFixed(3));
        tmpAbs = Math.sqrt(pow2(tmpX) + pow2(tmpY) + pow2(tmpZ)); console.log("G_abs: " + tmpAbs.toFixed(3));
      }
      if (ctl & 0x0008) {
        tmpX = int16(buf, L) * scaleMag; L += 2; console.log("CX: " + tmpX.toFixed(3));
        tmpY = int16(buf, L) * scaleMag; L += 2; console.log("CY: " + tmpY.toFixed(3));
        tmpZ = int16(buf, L) * scaleMag; L += 2; console.log("CZ: " + tmpZ.toFixed(3));
        tmpAbs = Math.sqrt(pow2(tmpX) + pow2(tmpY) + pow2(tmpZ)); console.log("C_abs: " + tmpAbs.toFixed(3));
      }
      if (ctl & 0x0010) {
        tmpX = int16(buf, L) * scaleTemperature; L += 2; console.log("temperature: " + tmpX.toFixed(2));

        tmpU32 = int24(buf, L);
        tmpY = tmpU32 * scaleAirPressure; L += 3; console.log("airPressure: " + tmpY.toFixed(3));

        tmpU32 = int24(buf, L);
        tmpZ = tmpU32 * scaleHeight; L += 3; console.log("height: " + tmpZ.toFixed(3));
      }
      if (ctl & 0x0020) {
        tmpAbs = int16(buf, L) * scaleQuat; L += 2; console.log("w: " + tmpAbs.toFixed(3));
        tmpX = int16(buf, L) * scaleQuat; L += 2; console.log("x: " + tmpX.toFixed(3));
        tmpY = int16(buf, L) * scaleQuat; L += 2; console.log("y: " + tmpY.toFixed(3));
        tmpZ = int16(buf, L) * scaleQuat; L += 2; console.log("z: " + tmpZ.toFixed(3));
      }
      if (ctl & 0x0040) {
        tmpX = int16(buf, L) * scaleAngle; L += 2; console.log("angleX: " + tmpX.toFixed(3));
        tmpY = int16(buf, L) * scaleAngle; L += 2; console.log("angleY: " + tmpY.toFixed(3));
        tmpZ = int16(buf, L) * scaleAngle; L += 2; console.log("angleZ: " + tmpZ.toFixed(3));
      }
      if (ctl & 0x0080) {
        tmpX = int16(buf, L) / 1000.0; L += 2; console.log("offsetX: " + tmpX.toFixed(3));
        tmpY = int16(buf, L) / 1000.0; L += 2; console.log("offsetY: " + tmpY.toFixed(3));
        tmpZ = int16(buf, L) / 1000.0; L += 2; console.log("offsetZ: " + tmpZ.toFixed(3));
      }
      if (ctl & 0x0100) {
        tmpU32 = int32(buf, L); L += 4; console.log("steps: " + tmpU32);
        tmpU8 = buf[L]; L += 1;
        console.log("walking: " + (tmpU8 & 0x01 ? "yes" : "no"));
        console.log("running: " + (tmpU8 & 0x02 ? "yes" : "no"));
        console.log("biking: " + (tmpU8 & 0x04 ? "yes" : "no"));
        console.log("driving: " + (tmpU8 & 0x08 ? "yes" : "no"));
      }
      if (ctl & 0x0200) {
        tmpX = int16(buf, L) * scaleAccel; L += 2; console.log("asX: " + tmpX.toFixed(3));
        tmpY = int16(buf, L) * scaleAccel; L += 2; console.log("asY: " + tmpY.toFixed(3));
        tmpZ = int16(buf, L) * scaleAccel; L += 2; console.log("asZ: " + tmpZ.toFixed(3));
        tmpAbs = Math.sqrt(pow2(tmpX) + pow2(tmpY) + pow2(tmpZ)); console.log("as_abs: " + tmpAbs.toFixed(3));
      }
      if (ctl & 0x0400) {
        tmpU16 = (buf[L + 1] << 8) | buf[L]; L += 2; console.log("adc: " + tmpU16);
      }
      if (ctl & 0x0800) {
        tmpU8 = buf[L]; L += 1;
        console.log("GPIO1  M:" + ((tmpU8 >> 4) & 0x0f).toString(16) + ", N:" + (tmpU8 & 0x0f).toString(16));
      }
      break;
    case 0x12:
      console.log("set parameters success");
      break;
    case 0x13:
      console.log("clear INS position success");
      break;
    case 0x14:
      console.log("Restore calibration parameters from factory mode success");
      break;
    case 0x15:
      console.log("Save calibration parameters to factory mode success");
      break;
    case 0x16:
      console.log("clear steps success");
      break;
    case 0x17:
      if (buf[1] === 255) {
        console.log("calibration success, please wait 10 seconds");
      } else if (buf[1] === 254) {
        console.log("calibration fail, gyro error");
      } else if (buf[1] === 253) {
        console.log("calibration fail, accelerometer error");
      } else if (buf[1] === 252) {
        console.log("calibration fail, compass error");
      } else if (buf[1] === 251) {
        console.log("calibration fail, Hasn't started");
      } else if (buf[1] !== 0) {
        console.log("calibration, Points collected is " + buf[1]);
      } else {
        console.log("calibration is running");
      }
      break;
    case 0x18:
      console.log("auto report off");
      break;
    case 0x19:
      console.log("auto report on");
      break;
    case 0x20:
      console.log("set PCB direction success");
      break;
    case 0x21:
      console.log("get PCB direction: 0x" + buf.slice(1, 10).map(x => x.toString(16).padStart(2, '0')).join(' '));
      console.log("get PCB direction: 0x" + buf.slice(10, 19).map(x => x.toString(16).padStart(2, '0')).join(' '));
      break;
    case 0x22:
      console.log("set BLE name success");
      break;
    case 0x23:
      console.log("get BLE name: " + String.fromCharCode.apply(null, buf.slice(1, 17)));
      break;
    case 0x24:
      console.log("set PowerDownVoltage and charge parameters success");
      break;
    case 0x25:
      console.log("PowerDownVoltageFlag: " + buf[1]);
      console.log("charge_full_mV: " + buf[2]);
      console.log("charge_full_mA: " + buf[3] + " ma");
      console.log("charge_mA: " + buf[4] + " ma");
      break;
    case 0x27:
      console.log("set gpio success");
      break;
    case 0x2A:
      console.log("will reset");
      break;
    case 0x2B:
      console.log("will power off");
      break;
    case 0x2C:
      console.log("set idleToPowerOffTime success");
      break;
    case 0x2D:
      console.log("idleToPowerOffTime: " + (buf[1] * 10) + " minutes");
      break;
    case 0x2E:
      console.log("set FlagForDisableBleSetNameAndCahrge success");
      break;
    case 0x2F:
      console.log("FlagForDisableBleSetNameAndCahrge: " + buf[1]);
      break;
    case 0x30:
      console.log("set address success");
      break;
    case 0x31:
      console.log("address: " + buf[1]);
      break;
    case 0x33:
      console.log("set accelRange and gyroRange success");
      break;
    case 0x34:
      console.log("accelRange: " + buf[1] + " gyroRange: " + buf[2]);
      break;
    case 0x35:
      console.log("set GyroAutoFlag success");
      break;
    case 0x36:
      console.log("GyroAutoFlag: " + buf[1]);
      break;
    case 0x37:
      console.log("set EcoTime success");
      break;
    case 0x38:
      console.log("EcoTime: " + buf[1]);
      break;
    case 0x42:
      console.log("set Height success");
      break;
    case 0x43:
      console.log("set HeightAutoFlag success");
      break;
    case 0x44:
      console.log("HeightAutoFlag: " + buf[1]);
      break;
    case 0x47:
      console.log("set BaudRate success");
      break;
    case 0x48:
      console.log("BaudRate: " + buf[1]);
      break;
    case 0x50:
      console.log("DTU: " + buf.slice(1, Dlen).map(x => x.toString(16).padStart(2, '0')).join(' '));
      break;
    case 0x51:
      console.log("set Cycle success");
      break;
    default:
      break;
  }
}
