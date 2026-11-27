function getInt24(dataView, offset, littleEndian) {
    let byte1 = dataView.getUint8(offset);
    let byte2 = dataView.getUint8(offset + 1);
    let byte3 = dataView.getUint8(offset + 2);
    let value;

    if (littleEndian) {
        value = byte1 | (byte2 << 8) | (byte3 << 16);
    } else {
        value = byte3 | (byte2 << 8) | (byte1 << 16);
    }

    // Sign extension for negative values
    if (value & 0x800000) {
        value = value | 0xFF000000;
    }

    return value;
}

function parse_imu(buf) {
    const scaleAccel = 0.00478515625;         // 加速度 [-16g~+16g]    9.8*16/32768
    const scaleQuat = 0.000030517578125;      // 四元数 [-1~+1]         1/32768
    const scaleAngle = 0.0054931640625;       // 角度   [-180~+180]     180/32768
    const scaleAngleSpeed = 0.06103515625;    // 角速度 [-2000~+2000]   2000/32768
    const scaleMag = 0.15106201171875;        // 磁场 [-4950~+4950]    4950/32768
    const scaleTemperature = 0.01;            // 温度
    const scaleAirPressure = 0.0002384185791; // 气压 [-2000~+2000]    2000/8388608
    const scaleHeight = 0.0010728836;         // 高度 [-9000~+9000]    9000/8388608

    let imu_dat = new Array(34).fill(0.0);

    if (buf[0] === 0x11) {
        let ctl = (buf[2] << 8) | buf[1];
        console.log(`\n subscribe tag: 0x${ctl.toString(16).padStart(4, '0')}`);

        // 创建 DataView，处理字节数据
        let dataView = new DataView(buf.buffer, buf.byteOffset, buf.byteLength);

        let ms = dataView.getUint32(3, true); // 小端模式
        console.log(" ms: ", ms);

        let L = 7; // 从第7字节开始解析

        if ((ctl & 0x0001) !== 0) {
            let tmpX = dataView.getInt16(L, true) * scaleAccel; L += 2;
            console.log(`\taX: ${tmpX.toFixed(3)}`); // x加速度aX
            let tmpY = dataView.getInt16(L, true) * scaleAccel; L += 2;
            console.log(`\taY: ${tmpY.toFixed(3)}`); // y加速度aY
            let tmpZ = dataView.getInt16(L, true) * scaleAccel; L += 2;
            console.log(`\taZ: ${tmpZ.toFixed(3)}`); // z加速度aZ

            imu_dat[0] = tmpX;
            imu_dat[1] = tmpY;
            imu_dat[2] = tmpZ;
        }

        if ((ctl & 0x0002) !== 0) {
            let tmpX = dataView.getInt16(L, true) * scaleAccel; L += 2;
            console.log(`\tAX: ${tmpX.toFixed(3)}`); // x加速度AX
            let tmpY = dataView.getInt16(L, true) * scaleAccel; L += 2;
            console.log(`\tAY: ${tmpY.toFixed(3)}`); // y加速度AY
            let tmpZ = dataView.getInt16(L, true) * scaleAccel; L += 2;
            console.log(`\tAZ: ${tmpZ.toFixed(3)}`); // z加速度AZ

            imu_dat[3] = tmpX;
            imu_dat[4] = tmpY;
            imu_dat[5] = tmpZ;
        }

        if ((ctl & 0x0004) !== 0) {
            let tmpX = dataView.getInt16(L, true) * scaleAngleSpeed; L += 2;
            console.log(`\tGX: ${tmpX.toFixed(3)}`); // x角速度GX
            let tmpY = dataView.getInt16(L, true) * scaleAngleSpeed; L += 2;
            console.log(`\tGY: ${tmpY.toFixed(3)}`); // y角速度GY
            let tmpZ = dataView.getInt16(L, true) * scaleAngleSpeed; L += 2;
            console.log(`\tGZ: ${tmpZ.toFixed(3)}`); // z角速度GZ

            imu_dat[6] = tmpX;
            imu_dat[7] = tmpY;
            imu_dat[8] = tmpZ;
        }

        if ((ctl & 0x0008) !== 0) {
            let tmpX = dataView.getInt16(L, true) * scaleMag; L += 2;
            console.log(`\tCX: ${tmpX.toFixed(3)}`); // x磁场CX
            let tmpY = dataView.getInt16(L, true) * scaleMag; L += 2;
            console.log(`\tCY: ${tmpY.toFixed(3)}`); // y磁场CY
            let tmpZ = dataView.getInt16(L, true) * scaleMag; L += 2;
            console.log(`\tCZ: ${tmpZ.toFixed(3)}`); // z磁场CZ

            imu_dat[9] = tmpX;
            imu_dat[10] = tmpY;
            imu_dat[11] = tmpZ;
        }

        if ((ctl & 0x0010) !== 0) {
            let tmpX = dataView.getInt16(L, true) * scaleTemperature; L += 2;
            console.log(`\ttemperature: ${tmpX.toFixed(2)}`); // 温度

            let tmpY = getInt24(dataView, L, true) * scaleAirPressure; L += 3;
            console.log(`\tairPressure: ${tmpY.toFixed(3)}`); // 气压

            let tmpZ = getInt24(dataView, L, true) * scaleHeight; L += 3;
            console.log(`\theight: ${tmpZ.toFixed(3)}`); // 高度

            imu_dat[12] = tmpX;
            imu_dat[13] = tmpY;
            imu_dat[14] = tmpZ;
        }

        if ((ctl & 0x0020) !== 0) {
            let tmpAbs = dataView.getInt16(L, true) * scaleQuat; L += 2;
            console.log(`\tw: ${tmpAbs.toFixed(3)}`); // w
            let tmpX = dataView.getInt16(L, true) * scaleQuat; L += 2;
            console.log(`\tx: ${tmpX.toFixed(3)}`); // x
            let tmpY = dataView.getInt16(L, true) * scaleQuat; L += 2;
            console.log(`\ty: ${tmpY.toFixed(3)}`); // y
            let tmpZ = dataView.getInt16(L, true) * scaleQuat; L += 2;
            console.log(`\tz: ${tmpZ.toFixed(3)}`); // z

            imu_dat[15] = tmpAbs;
            imu_dat[16] = tmpX;
            imu_dat[17] = tmpY;
            imu_dat[18] = tmpZ;
        }

        if ((ctl & 0x0040) !== 0) {
            let tmpX = dataView.getInt16(L, true) * scaleAngle; L += 2;
            console.log(`\tangleX: ${tmpX.toFixed(3)}`); // x角度
            let tmpY = dataView.getInt16(L, true) * scaleAngle; L += 2;
            console.log(`\tangleY: ${tmpY.toFixed(3)}`); // y角度
            let tmpZ = dataView.getInt16(L, true) * scaleAngle; L += 2;
            console.log(`\tangleZ: ${tmpZ.toFixed(3)}`); // z角度

            imu_dat[19] = tmpX;
            imu_dat[20] = tmpY;
            imu_dat[21] = tmpZ;
        }

        if ((ctl & 0x0080) !== 0) {
            let tmpX = dataView.getInt16(L, true) / 1000.0; L += 2;
            console.log(`\toffsetX: ${tmpX.toFixed(3)}`); // x坐标
            let tmpY = dataView.getInt16(L, true) / 1000.0; L += 2;
            console.log(`\toffsetY: ${tmpY.toFixed(3)}`); // y坐标
            let tmpZ = dataView.getInt16(L, true) / 1000.0; L += 2;
            console.log(`\toffsetZ: ${tmpZ.toFixed(3)}`); // z坐标

            imu_dat[22] = tmpX;
            imu_dat[23] = tmpY;
            imu_dat[24] = tmpZ;
        }

        if ((ctl & 0x0100) !== 0) {
            let tmpU32 = dataView.getUint32(L, true); L += 4;
            console.log(`\tsteps: ${tmpU32}`); // 计步数

            let tmpU8 = dataView.getUint8(L); L += 1;

            imu_dat[25] = (tmpU8 & 0x01) ? 100 : 0;
            imu_dat[26] = (tmpU8 & 0x02) ? 100 : 0;
            imu_dat[27] = (tmpU8 & 0x04) ? 100 : 0;
            imu_dat[28] = (tmpU8 & 0x08) ? 100 : 0;

            console.log(`\t walking ${imu_dat[25] ? 'yes' : 'no'}`);
            console.log(`\t running ${imu_dat[26] ? 'yes' : 'no'}`);
            console.log(`\t biking ${imu_dat[27] ? 'yes' : 'no'}`);
            console.log(`\t driving ${imu_dat[28] ? 'yes' : 'no'}`);
        }

        if ((ctl & 0x0200) !== 0) {
            let tmpX = dataView.getInt16(L, true) * scaleAccel; L += 2;
            console.log(`\tasX: ${tmpX.toFixed(3)}`); // x加速度asX
            let tmpY = dataView.getInt16(L, true) * scaleAccel; L += 2;
            console.log(`\tasY: ${tmpY.toFixed(3)}`); // y加速度asY
            let tmpZ = dataView.getInt16(L, true) * scaleAccel; L += 2;
            console.log(`\tasZ: ${tmpZ.toFixed(3)}`); // z加速度asZ

            imu_dat[29] = tmpX;
            imu_dat[30] = tmpY;
            imu_dat[31] = tmpZ;
        }

        if ((ctl & 0x0400) !== 0) {
            let tmpU16 = dataView.getUint16(L, true); L += 2;
            console.log(`\tadc: ${tmpU16}`); // ADC电压值，单位mv
            imu_dat[32] = tmpU16;
        }

        if ((ctl & 0x0800) !== 0) {
            let tmpU8 = dataView.getUint8(L); L += 1;
            let M = (tmpU8 >> 4) & 0x0F;
            let N = tmpU8 & 0x0F;
            console.log(`\t GPIO1  M:${M.toString(16).toUpperCase()}, N:${N.toString(16).toUpperCase()}`);
            imu_dat[33] = tmpU8;
        }

        // 返回解析后的数据
        return imu_dat;

    } else {
        console.log("[error] data head not define");
        return null;
    }
}

function main() {
    let data = new Uint8Array([
        0x11, 0xFF, 0x0F, 0xF5, 0xF5, 0x49, 0x47, 0x10, 0x00, 0xF6, 0xFF, 0xD5, 0xFF,
        0x5A, 0xFF, 0x1F, 0xFD, 0x4A, 0x07, 0x09, 0x00, 0x0A, 0x00, 0x05, 0x00, 0x00,
        0x00, 0x00, 0x00, 0x00, 0x00, 0x3A, 0x0B, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 
        0x50, 0x78, 0x9F, 0xEB, 0x5C, 0x0C, 0x64, 0xDB, 0x2C, 0xF1, 0xB0, 0x03, 0x40,
        0xE7, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x08, 0x00, 0x00, 0x00, 0x00, 0xFC,
        0xFF, 0xE4, 0xFF, 0xDA, 0xFF, 0xFE, 0x09, 0x01
    ]);

    let imu_dat = parse_imu(data);
    console.log('imu_dat:', imu_dat);
}

main();
