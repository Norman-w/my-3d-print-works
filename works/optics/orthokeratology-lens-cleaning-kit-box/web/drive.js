(() => {
  "use strict";

  //#region 常量/配置
  const MM = 16;
  const PINION_TEETH = 8;
  const WHEEL_TEETH = 40;
  const MODULE_MM = 0.5;
  const CENTER_MM = 12;
  const PLAYBACK_DEFAULT = 0.1;
  //#endregion

  //#region 模型/类型
  const state = {
    playing: true,
    rate: PLAYBACK_DEFAULT,
    pinionRad: 0,
    lastFrame: null,
    frameId: null,
    report: null,
  };
  //#endregion

  //#region 私有成员
  const canvas = document.getElementById("driveCanvas");
  const ctx = canvas.getContext("2d");
  const playButton = document.getElementById("playButton");
  const resetButton = document.getElementById("resetButton");
  const rateInput = document.getElementById("playbackRate");
  const rateValue = document.getElementById("rateValue");
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  //#endregion

  //#region 方法/工具
  function setText(id, text) {
    const node = document.getElementById(id);
    if (node) node.textContent = text;
  }

  function gearRadii(teeth) {
    const pitch = MODULE_MM * teeth / 2;
    return {
      pitch,
      outer: pitch + MODULE_MM,
      root: Math.max(pitch - 1.25 * MODULE_MM, 1.1),
    };
  }

  function drawGear(context, x, y, teeth, angle, fill, stroke) {
    const radii = gearRadii(teeth);
    const toothWidth = Math.PI / teeth;
    context.save();
    context.translate(x, y);
    context.rotate(angle);
    context.beginPath();
    for (let i = 0; i < teeth; i += 1) {
      const a0 = i * 2 * Math.PI / teeth - toothWidth * 0.32;
      const a1 = i * 2 * Math.PI / teeth + toothWidth * 0.32;
      const aMid0 = i * 2 * Math.PI / teeth - toothWidth * 0.16;
      const aMid1 = i * 2 * Math.PI / teeth + toothWidth * 0.16;
      const next = (i + 1) * 2 * Math.PI / teeth - toothWidth * 0.32;
      if (i === 0) context.moveTo(Math.cos(a0) * radii.root * MM, Math.sin(a0) * radii.root * MM);
      context.lineTo(Math.cos(a0) * radii.root * MM, Math.sin(a0) * radii.root * MM);
      context.lineTo(Math.cos(aMid0) * radii.outer * MM, Math.sin(aMid0) * radii.outer * MM);
      context.lineTo(Math.cos(aMid1) * radii.outer * MM, Math.sin(aMid1) * radii.outer * MM);
      context.lineTo(Math.cos(a1) * radii.root * MM, Math.sin(a1) * radii.root * MM);
      context.arc(0, 0, radii.root * MM, a1, next, false);
    }
    context.closePath();
    context.fillStyle = fill;
    context.strokeStyle = stroke;
    context.lineWidth = 1.5;
    context.fill();
    context.stroke();
    context.beginPath();
    context.arc(0, 0, Math.max(1.2, radii.root * 0.35) * MM, 0, Math.PI * 2);
    context.fillStyle = "#0b1220";
    context.fill();
    context.beginPath();
    context.moveTo(0, 0);
    context.lineTo(radii.pitch * MM, 0);
    context.strokeStyle = "#f8fafc";
    context.lineWidth = 2;
    context.stroke();
    context.restore();
  }

  function drawMotor(context, x, y) {
    context.save();
    context.translate(x, y);
    context.fillStyle = "rgba(51, 184, 227, 0.92)";
    context.strokeStyle = "#7dd3fc";
    roundRect(context, -92, -40, 84, 80, 10);
    context.fill();
    context.stroke();
    context.fillStyle = "rgba(14, 116, 144, 0.95)";
    roundRect(context, -8, -22, 22, 44, 4);
    context.fill();
    context.fillStyle = "#cbd5e1";
    context.beginPath();
    context.arc(28, 0, 5, 0, Math.PI * 2);
    context.fill();
    drawScrew(context, -48, -22);
    drawScrew(context, -48, 22);
    context.fillStyle = "#e2e8f0";
    context.font = "700 13px Inter, sans-serif";
    context.textAlign = "center";
    context.fillText("N20 MOTOR", -50, 4);
    context.restore();
  }

  function drawScrew(context, x, y) {
    context.beginPath();
    context.arc(x, y, 7, 0, Math.PI * 2);
    context.fillStyle = "#94a3b8";
    context.fill();
    context.strokeStyle = "#e2e8f0";
    context.stroke();
    context.beginPath();
    for (let i = 0; i < 6; i += 1) {
      const a = i * Math.PI / 3;
      const cmd = i === 0 ? "moveTo" : "lineTo";
      context[cmd](x + Math.cos(a) * 3.4, y + Math.sin(a) * 3.4);
    }
    context.closePath();
    context.fillStyle = "#0f172a";
    context.fill();
  }

  function roundRect(context, x, y, w, h, r) {
    context.beginPath();
    context.moveTo(x + r, y);
    context.arcTo(x + w, y, x + w, y + h, r);
    context.arcTo(x + w, y + h, x, y + h, r);
    context.arcTo(x, y + h, x, y, r);
    context.arcTo(x, y, x + w, y, r);
    context.closePath();
  }

  function label(context, x, y, title, detail) {
    context.fillStyle = "#f8fafc";
    context.font = "700 15px Inter, sans-serif";
    context.textAlign = "center";
    context.fillText(title, x, y);
    context.fillStyle = "#91a0b5";
    context.font = "12px Inter, sans-serif";
    context.fillText(detail, x, y + 18);
  }
  //#endregion

  //#region 视图层
  function draw() {
    const width = canvas.width;
    const height = canvas.height;
    ctx.clearRect(0, 0, width, height);
    const wheel = { x: width * 0.64, y: height * 0.52 };
    const pinion = { x: wheel.x - CENTER_MM * MM, y: wheel.y };
    const wheelAngle = -state.pinionRad * PINION_TEETH / WHEEL_TEETH;
    drawMotor(ctx, pinion.x - 96, pinion.y);
    drawGear(ctx, wheel.x, wheel.y, WHEEL_TEETH, wheelAngle + Math.PI / WHEEL_TEETH, "rgba(251, 191, 36, 0.92)", "#fde68a");
    drawGear(ctx, pinion.x, pinion.y, PINION_TEETH, state.pinionRad, "rgba(34, 197, 94, 0.92)", "#bbf7d0");
    label(ctx, wheel.x, 64, "大齿轮 Z40", "输出轴 · 反向 · 1/5 转速");
    label(ctx, pinion.x, height - 42, "小齿轮 Z8", "与电机同轴 · 快转");
    const rpmIn = 100 * state.rate;
    const rpmOut = rpmIn * PINION_TEETH / WHEEL_TEETH;
    ctx.fillStyle = "#a3e635";
    ctx.font = "700 18px Inter, sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(`${rpmIn.toFixed(1)} rpm`, 36, 48);
    ctx.fillStyle = "#fbbf24";
    ctx.fillText(`${rpmOut.toFixed(1)} rpm`, 36, 76);
    ctx.fillStyle = "#91a0b5";
    ctx.font = "12px Inter, sans-serif";
    ctx.fillText("电机 / 小齿轮", 36, 96);
    ctx.fillText("大齿轮输出", 36, 114);
  }
  //#endregion

  //#region 业务逻辑
  function tick(now) {
    if (state.playing) {
      if (state.lastFrame != null) {
        const dt = Math.min(0.05, (now - state.lastFrame) / 1000);
        const motorRpm = 100 * state.rate;
        state.pinionRad += motorRpm / 60 * Math.PI * 2 * dt;
      }
      state.lastFrame = now;
    } else {
      state.lastFrame = null;
    }
    draw();
    state.frameId = window.requestAnimationFrame(tick);
  }

  function applyReport(report) {
    state.report = report;
    const drive = report.drive || {};
    setText("metricRatio", `${Number(drive.gear_ratio || 5).toFixed(0)} : 1`);
    setText("metricTorque", `${Number(drive.output_shaft_nm || 0).toFixed(3)} N·m`);
    setText("metricRpm", `${Number(drive.output_no_load_rpm || 0).toFixed(0)} rpm`);
    setText("metricScrews", drive.screws_hold_stall ? "通过" : "不足");
    setText("simState", report.ok ? "仿真通过 · 无壳体" : "仿真有未通过项");
  }
  //#endregion

  //#region 公开 API
  function setPlaying(playing) {
    state.playing = playing;
    playButton.textContent = playing ? "暂停" : "播放";
    playButton.setAttribute("aria-pressed", playing ? "true" : "false");
  }

  rateInput.addEventListener("input", () => {
    state.rate = Number(rateInput.value);
    rateValue.textContent = `${state.rate.toFixed(2)}× 实速`;
  });
  playButton.addEventListener("click", () => setPlaying(!state.playing));
  resetButton.addEventListener("click", () => {
    state.pinionRad = 0;
    draw();
  });

  if (reducedMotion.matches) setPlaying(false);

  fetch("/parts-report.json")
    .then((response) => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json();
    })
    .then(applyReport)
    .catch(() => {
      setText("simState", "未读到报告，仍按 5:1 演示");
      applyReport({
        ok: true,
        drive: { gear_ratio: 5, output_shaft_nm: 0.2125, output_no_load_rpm: 20, screws_hold_stall: true },
      });
    });

  rateValue.textContent = `${state.rate.toFixed(2)}× 实速`;
  state.frameId = window.requestAnimationFrame(tick);
  //#endregion
})();
