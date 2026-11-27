(() => {
  "use strict";

  const models = {
    animation: {
      title: "开合动画 · 实际转轴",
      hint: "上下壳使用真实 STL，盒盖绕后轴在 0–100° 间运动。仅演示刚性开合，未模拟弹片解锁变形；下载仍为 V 形主打印文件。",
      color: [0.33, 0.72, 0.89, 1],
    },
    print: {
      title: "V 形 · 45° 斜置打印态",
      hint: "Rev H · 顶盖凹刻 ORTHO-K / LENS CARE KIT / Candy。2.4 mm 薄壁，开口 90°、两半各斜 45°；短推杆和短支承保留，局部支撑待切片确认，轴孔禁止支撑。",
      asset: "orthokeratology_lens_cleaning_kit_box_print_in_place_open.stl",
      color: [0.52, 0.79, 0.26, 1],
    },
    closed: {
      title: "闭合展示态",
      hint: "顶盖三行浅凹刻：ORTHO-K / LENS CARE KIT / Candy，深 0.4 mm。外形 134.8×121.8×54 mm，净空 130×100×50 mm；侧壁 2.4 mm，顶板原厚 2.0 mm、文字下剩余 1.6 mm。",
      asset: "orthokeratology_lens_cleaning_kit_box_closed_preview.stl",
      color: [0.96, 0.67, 0.16, 1],
    },
    base: {
      title: "底座结构",
      hint: "普通壁厚 2.4 mm，前后内侧挖空减料，仅在隐藏卡齿和轴叉根部保留局部支座。没有环形密封槽；短推杆和短支承保留。下载为完整 V 形打印文件。",
      asset: "orthokeratology_lens_cleaning_kit_box_base.stl",
      color: [0.33, 0.72, 0.89, 1],
    },
    lid: {
      title: "盒盖结构",
      hint: "顶板原厚 2.0 mm、外侧文字凹刻 0.4 mm；转动视角查看 Candy 署名。侧壁 2.4 mm，内部弹片和轴根保持原结构，不侵占净空。下载为完整 V 形打印文件。",
      asset: "orthokeratology_lens_cleaning_kit_box_lid.stl",
      color: [0.86, 0.47, 0.89, 1],
    },
    open90: {
      title: "打开 90°",
      hint: "围绕隐藏轴打开 90°，底座平放用于检查；实际主打印文件会整体再倾斜 45° 成 V 形。几何工作范围检查到 100°。",
      asset: "orthokeratology_lens_cleaning_kit_box_open90.stl",
      color: [0.33, 0.72, 0.89, 1],
    },
    section: {
      title: "闭合剖面",
      hint: "完整矩形净空 130×100×50 mm。剖面显示 2.4 mm 壳壁、2.0 mm 顶底及锁扣根部局部加强；周边密封槽已删除。",
      asset: "orthokeratology_lens_cleaning_kit_box_section.stl",
      color: [0.96, 0.67, 0.16, 1],
    },
    coupon: {
      title: "铰链试片",
      hint: "24 mm 宽局部样件，保留当前隐藏轴及 V 形打印姿态。按同一支撑策略试印，先验证能释放转动；不代替锁扣试验。",
      asset: "orthokeratology_lens_cleaning_kit_box_hinge_coupon.stl",
      color: [0.52, 0.79, 0.26, 1],
    },
  };

  const state = {
    mode: "animation",
    cache: new Map(),
    yaw: 0.68,
    pitch: 0.56,
    zoom: 1,
    dragging: false,
    lastPointer: null,
    gl: null,
    program: null,
    parts: [],
    loadId: 0,
    ready: false,
    angle: 0,
    playing: false,
    phase: 0,
    lastFrame: null,
    frameId: null,
  };
  const motion = window.BoxMotion;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");

  const $ = (id) => document.getElementById(id);
  const canvas = $("viewport");
  const overlay = $("canvasMessage");
  const gl = canvas.getContext("webgl", { antialias: true, alpha: false });
  state.gl = gl;

  function setText(id, text) { $(id).textContent = text; }

  function showOverlay(text, isError = false) {
    overlay.textContent = text;
    overlay.classList.toggle("error", isError);
  }

  function normalize(v) {
    const length = Math.hypot(v[0], v[1], v[2]) || 1;
    return [v[0] / length, v[1] / length, v[2] / length];
  }

  function cross(a, b) {
    return [
      a[1] * b[2] - a[2] * b[1],
      a[2] * b[0] - a[0] * b[2],
      a[0] * b[1] - a[1] * b[0],
    ];
  }

  function sub(a, b) { return [a[0] - b[0], a[1] - b[1], a[2] - b[2]]; }

  function triangleNormal(a, b, c) { return normalize(cross(sub(b, a), sub(c, a))); }

  function parseStl(buffer) {
    const view = new DataView(buffer);
    const binaryCount = buffer.byteLength >= 84 ? view.getUint32(80, true) : 0;
    const binaryExpected = 84 + binaryCount * 50;
    const isBinary = binaryCount > 0 && binaryExpected === buffer.byteLength;
    const triangles = [];
    let signedVolume = 0;

    const pushTriangle = (a, b, c) => {
      const normal = triangleNormal(a, b, c);
      triangles.push({ a, b, c, normal });
      signedVolume += (a[0] * (b[1] * c[2] - b[2] * c[1]) - a[1] * (b[0] * c[2] - b[2] * c[0]) + a[2] * (b[0] * c[1] - b[1] * c[0])) / 6;
    };

    if (isBinary) {
      let offset = 84;
      for (let i = 0; i < binaryCount; i += 1) {
        offset += 12;
        const points = [];
        for (let p = 0; p < 3; p += 1) {
          points.push([view.getFloat32(offset, true), view.getFloat32(offset + 4, true), view.getFloat32(offset + 8, true)]);
          offset += 12;
        }
        pushTriangle(points[0], points[1], points[2]);
        offset += 2;
      }
    } else {
      const text = new TextDecoder().decode(buffer);
      const matches = text.matchAll(/^\s*vertex\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s+([-+0-9.eE]+)\s*$/gim);
      const points = [];
      for (const match of matches) {
        points.push([Number(match[1]), Number(match[2]), Number(match[3])]);
        if (points.length === 3) {
          pushTriangle(points[0], points[1], points[2]);
          points.length = 0;
        }
      }
    }

    if (!triangles.length) throw new Error("没有解析到 STL 三角面。 ");

    const min = [Infinity, Infinity, Infinity];
    const max = [-Infinity, -Infinity, -Infinity];
    for (const tri of triangles) {
      for (const point of [tri.a, tri.b, tri.c]) {
        for (let axis = 0; axis < 3; axis += 1) {
          min[axis] = Math.min(min[axis], point[axis]);
          max[axis] = Math.max(max[axis], point[axis]);
        }
      }
    }
    const center = min.map((value, axis) => (value + max[axis]) / 2);
    const size = max.map((value, axis) => value - min[axis]);
    const maxDimension = Math.max(...size) || 1;
    const positions = [];
    const normals = [];
    for (const tri of triangles) {
      for (const point of [tri.a, tri.b, tri.c]) {
        positions.push((point[0] - center[0]) * (2 / maxDimension), (point[1] - center[1]) * (2 / maxDimension), (point[2] - center[2]) * (2 / maxDimension));
        normals.push(...tri.normal);
      }
    }
    return { positions: new Float32Array(positions), normals: new Float32Array(normals), center, maxDimension, size, min, max, triangleCount: triangles.length, volume: Math.abs(signedVolume) };
  }

  function shader(type, source) {
    const object = gl.createShader(type);
    gl.shaderSource(object, source);
    gl.compileShader(object);
    if (!gl.getShaderParameter(object, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(object));
    return object;
  }

  function initGl() {
    if (!gl) throw new Error("当前浏览器不支持 WebGL。 ");
    const vertex = shader(gl.VERTEX_SHADER, `
      attribute vec3 aPosition;
      attribute vec3 aNormal;
      uniform mat4 uMatrix;
      uniform mat4 uModelView;
      varying vec3 vViewNormal;
      void main() {
        // The model/view transform is rigid: w=0 rotates normals without
        // translating them. Projection must never be applied to a normal.
        vViewNormal = (uModelView * vec4(aNormal, 0.0)).xyz;
        gl_Position = uMatrix * vec4(aPosition, 1.0);
      }
    `);
    const fragment = shader(gl.FRAGMENT_SHADER, `
      precision mediump float;
      uniform vec4 uColor;
      varying vec3 vViewNormal;
      void main() {
        vec3 normal = normalize(vViewNormal);
        // Camera-space studio lights keep newly exposed faces readable.
        // Broad ambient fill preserves cavity detail without harsh dark faces.
        float key = max(0.0, dot(normal, normalize(vec3(-0.45, 0.65, 1.0))));
        float fill = max(0.0, dot(normal, normalize(vec3(0.65, -0.3, 0.75))));
        float head = max(0.0, normal.z);
        float light = 0.55 + 0.23 * key + 0.14 * fill + 0.08 * head;
        gl_FragColor = vec4(uColor.rgb * light, uColor.a);
      }
    `);
    const program = gl.createProgram();
    gl.attachShader(program, vertex);
    gl.attachShader(program, fragment);
    gl.linkProgram(program);
    if (!gl.getProgramParameter(program, gl.LINK_STATUS)) throw new Error(gl.getProgramInfoLog(program));
    state.program = program;
    state.locations = {
      position: gl.getAttribLocation(program, "aPosition"),
      normal: gl.getAttribLocation(program, "aNormal"),
      matrix: gl.getUniformLocation(program, "uMatrix"),
      modelView: gl.getUniformLocation(program, "uModelView"),
      color: gl.getUniformLocation(program, "uColor"),
    };
    gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.CULL_FACE);
  }

  function resizeCanvas() {
    if (!gl) return;
    const ratio = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(1, Math.floor(canvas.clientWidth * ratio));
    const height = Math.max(1, Math.floor(canvas.clientHeight * ratio));
    if (canvas.width !== width || canvas.height !== height) {
      canvas.width = width;
      canvas.height = height;
      gl.viewport(0, 0, width, height);
    }
  }

  function multiply(a, b) {
    const out = new Float32Array(16);
    for (let column = 0; column < 4; column += 1) {
      for (let row = 0; row < 4; row += 1) {
        out[column * 4 + row] = a[row] * b[column * 4] + a[4 + row] * b[column * 4 + 1] + a[8 + row] * b[column * 4 + 2] + a[12 + row] * b[column * 4 + 3];
      }
    }
    return out;
  }

  function perspective(fov, aspect, near, far) {
    const f = 1 / Math.tan(fov / 2);
    const range = near - far;
    return new Float32Array([f / aspect, 0, 0, 0, 0, f, 0, 0, 0, 0, (far + near) / range, -1, 0, 0, (2 * far * near) / range, 0]);
  }

  function lookAt(eye, target, up) {
    const z = normalize(sub(eye, target));
    const x = normalize(cross(up, z));
    const y = cross(z, x);
    return new Float32Array([x[0], y[0], z[0], 0, x[1], y[1], z[1], 0, x[2], y[2], z[2], 0, -x[0] * eye[0] - x[1] * eye[1] - x[2] * eye[2], -y[0] * eye[0] - y[1] * eye[1] - y[2] * eye[2], -z[0] * eye[0] - z[1] * eye[1] - z[2] * eye[2], 1]);
  }

  function rotationX(angle) {
    const c = Math.cos(angle); const s = Math.sin(angle);
    return new Float32Array([1, 0, 0, 0, 0, c, s, 0, 0, -s, c, 0, 0, 0, 0, 1]);
  }

  function rotationY(angle) {
    const c = Math.cos(angle); const s = Math.sin(angle);
    return new Float32Array([c, 0, -s, 0, 0, 1, 0, 0, s, 0, c, 0, 0, 0, 0, 1]);
  }

  function draw() {
    if (!gl || !state.parts.length || !state.program) return;
    resizeCanvas();
    const aspect = canvas.width / canvas.height;
    const distance = 4.1 / state.zoom * Math.max(1, 1 / aspect);
    const projection = perspective(Math.PI / 4, aspect, 0.1, 100);
    const view = lookAt([0, 0, distance], [0, 0, 0], [0, 1, 0]);
    const model = multiply(rotationY(state.yaw), rotationX(state.pitch));
    const sceneView = multiply(view, model);
    gl.clearColor(0.045, 0.075, 0.12, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.useProgram(state.program);
    for (const part of state.parts) {
      const modelView = state.mode === "animation"
        ? multiply(sceneView, motion.partMatrix(part.mesh, state.motionFrame, part.moving ? state.angle : 0))
        : sceneView;
      gl.uniformMatrix4fv(state.locations.matrix, false, multiply(projection, modelView));
      gl.uniformMatrix4fv(state.locations.modelView, false, modelView);
      gl.uniform4fv(state.locations.color, part.color);
      gl.bindBuffer(gl.ARRAY_BUFFER, part.buffers.position);
      gl.enableVertexAttribArray(state.locations.position);
      gl.vertexAttribPointer(state.locations.position, 3, gl.FLOAT, false, 0, 0);
      gl.bindBuffer(gl.ARRAY_BUFFER, part.buffers.normal);
      gl.enableVertexAttribArray(state.locations.normal);
      gl.vertexAttribPointer(state.locations.normal, 3, gl.FLOAT, false, 0, 0);
      gl.drawArrays(gl.TRIANGLES, 0, part.mesh.positions.length / 3);
    }
  }

  function clearParts() {
    for (const part of state.parts) {
      gl.deleteBuffer(part.buffers.position);
      gl.deleteBuffer(part.buffers.normal);
    }
    state.parts = [];
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
  }

  function uploadPart(mesh, color, moving = false) {
    const buffers = {
      position: gl.createBuffer(),
      normal: gl.createBuffer(),
    };
    gl.bindBuffer(gl.ARRAY_BUFFER, buffers.position);
    gl.bufferData(gl.ARRAY_BUFFER, mesh.positions, gl.STATIC_DRAW);
    gl.bindBuffer(gl.ARRAY_BUFFER, buffers.normal);
    gl.bufferData(gl.ARRAY_BUFFER, mesh.normals, gl.STATIC_DRAW);
    state.parts.push({ mesh, color, moving, buffers });
  }

  function updateMeshStats(mesh) {
    const size = mesh.size.map((value) => value.toFixed(2)).join(" × ");
    setText("meshStats", `${mesh.triangleCount.toLocaleString()} 个三角面 · 包围盒 ${size} mm · 体积约 ${mesh.volume.toFixed(1)} mm³ · STL 单位按 mm 解释`);
  }

  async function loadModel(mode) {
    const loadId = ++state.loadId;
    setPlaying(false);
    state.ready = false;
    state.mode = mode;
    clearParts();
    $("motionControls").hidden = mode !== "animation";
    updateMotionControls();
    const model = models[mode];
    setText("viewerTitle", model.title);
    setText("modelHint", model.hint);
    setText("downloadButton", mode === "coupon" ? "下载铰链试片 STL" : "下载 V 形主 STL");
    showOverlay("正在加载 STL…");
    setText("meshStats", "正在加载模型数据…");
    try {
      if (mode === "animation") {
        const [base, lid, metadata] = await Promise.all([fetchMesh(models.base.asset), fetchMesh(models.lid.asset), fetch("/api/model", { cache: "no-store" }).then(readJson)]);
        if (loadId !== state.loadId) return;
        motion.configure(metadata.hingePivot);
        state.motionFrame = motion.frameFor(base, lid);
        uploadPart(base, [0.33, 0.72, 0.89, 1]);
        uploadPart(lid, [0.87, 0.9, 0.94, 1], true);
        setText("meshStats", `${(base.triangleCount + lid.triangleCount).toLocaleString()} 个三角面 · 底座固定 / 盒盖绕 X 轴旋转 · 轴心 Y=${motion.pivot[1].toFixed(1)}、Z=${motion.pivot[2].toFixed(1)} mm · 蓝色底座 / 浅色盒盖`);
        resetView();
      } else {
        const mesh = await fetchMesh(model.asset);
        if (loadId !== state.loadId) return;
        uploadPart(mesh, model.color);
        updateMeshStats(mesh);
      }
      state.ready = true;
      updateMotionControls();
      showOverlay("拖动模型旋转 · 滚轮缩放");
      draw();
    } catch (error) {
      if (loadId !== state.loadId) return;
      clearParts();
      showOverlay(`预览失败：${error.message}`, true);
      setText("meshStats", "模型未加载，请确认已运行 python3 serve.py 并先执行 scripts/build.sh。");
    }
  }

  async function fetchMesh(asset) {
    if (!state.cache.has(asset)) {
      const response = await fetch(`/assets/${encodeURIComponent(asset)}?rev=H`, { cache: "no-store" });
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      state.cache.set(asset, parseStl(await response.arrayBuffer()));
    }
    return state.cache.get(asset);
  }

  function updateMotionControls() {
    const enabled = state.mode === "animation" && state.ready;
    $("motionControls").querySelectorAll("button, input").forEach((el) => { el.disabled = !enabled; });
    setText("playMotionButton", state.playing ? "暂停" : "播放开合");
    $("playMotionButton").setAttribute("aria-pressed", String(state.playing));
    $("openingAngle").value = state.angle.toFixed(1);
    $("openingAngle").setAttribute("aria-valuetext", `${state.angle.toFixed(1)} 度`);
    setText("angleValue", `${state.angle.toFixed(1)}°`);
  }

  function setPlaying(playing) {
    state.playing = playing && state.mode === "animation" && state.ready && !document.hidden;
    if (state.frameId !== null) cancelAnimationFrame(state.frameId);
    state.frameId = null;
    state.lastFrame = null;
    updateMotionControls();
    if (state.playing) state.frameId = requestAnimationFrame(animate);
  }

  function animate(time) {
    state.frameId = null;
    if (!state.playing) return;
    if (state.lastFrame !== null) state.phase += Math.min((time - state.lastFrame) / 1000, .1) * Math.PI / 3;
    state.lastFrame = time;
    state.angle = motion.angleAt(state.phase);
    updateMotionControls();
    draw();
    state.frameId = requestAnimationFrame(animate);
  }

  function setAngle(angle) {
    setPlaying(false);
    state.angle = Math.max(0, Math.min(motion.maxAngle, Number(angle) || 0));
    state.phase = motion.phaseAt(state.angle);
    updateMotionControls();
    draw();
  }

  function resetView() {
    state.yaw = 0.68;
    state.pitch = state.mode === "animation" ? -0.75 : 0.56;
    state.zoom = 1;
    draw();
  }

  function setBusy(button, busy, busyText, idleText) {
    button.disabled = busy;
    if (busy) {
      button.dataset.idleText = idleText || button.textContent;
      button.textContent = busyText;
    } else {
      button.textContent = button.dataset.idleText || idleText || button.textContent;
    }
  }

  async function readJson(response) {
    const data = await response.json().catch(() => ({}));
    if (!response.ok || data.ok === false) throw new Error(data.error || `HTTP ${response.status}`);
    return data;
  }

  async function loadHealth() {
    try {
      const data = await readJson(await fetch("/api/health"));
      const { length, width, height } = data.model.inner;
      setText("innerDimensions", `${length} × ${width} × ${height} mm`);
      setText("innerLength", `${length} mm`);
      setText("innerWidth", `${width} mm`);
      setText("innerHeight", `${height} mm`);
      setText("serverStatus", data.slicerDetected ? "本地服务在线 · 已检测到切片器" : "本地服务在线 · 未检测到 Bambu Studio");
    } catch (error) {
      setText("serverStatus", "本地服务未连接");
    }
  }

  function connectionFields() {
    return {
      ip: $("printerIp").value.trim(),
      serial: $("printerSerial").value.trim(),
      access_code: $("accessCode").value.trim(),
    };
  }

  async function testPrinter(event) {
    event.preventDefault();
    const button = $("testPrinterButton");
    const result = $("printerResult");
    const pill = $("printerState");
    setBusy(button, true, "测试中…", "测试连接");
    result.textContent = "正在检查 MQTT / FTPS 端口与登录…";
    pill.textContent = "测试中";
    pill.className = "status-pill status-warning";
    try {
      const data = await readJson(await fetch("/api/printer/test", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(connectionFields()) }));
      const ports = data.result.ports;
      const mqtt = data.result.mqttAuthenticated === true ? "MQTT 已认证" : (ports.mqtt.reachable ? "MQTT 端口可达" : "MQTT 不可达");
      const ftps = data.result.ftpsAuthenticated === true ? "FTPS 已认证" : (ports.ftps.reachable ? "FTPS 端口可达" : "FTPS 不可达");
      result.textContent = `${mqtt} · ${ftps}`;
      const authenticated = data.result.mqttAuthenticated && data.result.ftpsAuthenticated;
      pill.textContent = authenticated ? "已连接" : "部分可达";
      pill.className = authenticated ? "status-pill" : "status-pill status-warning";
    } catch (error) {
      result.textContent = error.message;
      pill.textContent = "失败";
      pill.className = "status-pill status-error";
    } finally {
      setBusy(button, false, "测试中…", "测试连接");
    }
  }

  async function openSlicer() {
    const button = $("openSlicerButton");
    setBusy(button, true, "启动中…", "用 Bambu Studio 打开");
    try {
      await readJson(await fetch("/api/open-slicer", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ asset: models[state.mode === "coupon" ? "coupon" : "print"].asset }) }));
      showOverlay("已请求 Bambu Studio 打开 STL");
    } catch (error) {
      showOverlay(error.message, true);
    } finally {
      setBusy(button, false, "启动中…", "用 Bambu Studio 打开");
    }
  }

  async function sendPrint() {
    const input = $("jobFile");
    const file = input.files && input.files[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".gcode.3mf")) {
      $("jobResult").textContent = "请选择已切片的 .gcode.3mf 文件。";
      return;
    }
    const button = $("sendPrintButton");
    const form = new FormData();
    const fields = connectionFields();
    for (const [key, value] of Object.entries(fields)) form.append(key, value);
    form.append("use_ams", $("useAms").checked ? "true" : "false");
    form.append("ams_slot", $("amsSlot").value);
    form.append("file", file, file.name);
    setBusy(button, true, "上传并发送中…", "上传并发送打印");
    $("jobResult").textContent = "正在上传到本地服务，再通过 LAN 发送到打印机…";
    try {
      const data = await readJson(await fetch("/api/print", { method: "POST", body: form }));
      $("jobResult").textContent = `已发送：${data.result.printerFile} · MD5 ${data.result.md5}`;
    } catch (error) {
      $("jobResult").textContent = error.message;
    } finally {
      setBusy(button, false, "上传并发送中…", "上传并发送打印");
    }
  }

  function updateJobFile() {
    const input = $("jobFile");
    const file = input.files && input.files[0];
    setText("jobFileName", file ? `${file.name} · ${(file.size / 1024 / 1024).toFixed(2)} MB` : "未选择文件");
    $("sendPrintButton").disabled = !file;
  }

  function downloadCurrent() {
    const link = document.createElement("a");
    const asset = models[state.mode === "coupon" ? "coupon" : "print"].asset;
    link.href = `/assets/${encodeURIComponent(asset)}?download=1&rev=H`;
    link.download = asset;
    document.body.appendChild(link);
    link.click();
    link.remove();
  }

  function bindInteraction() {
    $("playMotionButton").addEventListener("click", () => setPlaying(!state.playing));
    $("openingAngle").addEventListener("input", (event) => setAngle(event.target.value));
    $("closeLidButton").addEventListener("click", () => setAngle(0));
    $("openLidButton").addEventListener("click", () => setAngle(100));
    document.addEventListener("visibilitychange", () => { if (document.hidden) setPlaying(false); });
    reducedMotion.addEventListener("change", () => { if (reducedMotion.matches) setPlaying(false); });
    $("modelSelect").addEventListener("change", (event) => loadModel(event.target.value));
    $("resetViewButton").addEventListener("click", resetView);
    $("downloadButton").addEventListener("click", downloadCurrent);
    $("openSlicerButton").addEventListener("click", openSlicer);
    $("printerForm").addEventListener("submit", testPrinter);
    $("sendPrintButton").addEventListener("click", sendPrint);
    $("jobFile").addEventListener("change", updateJobFile);
    $("useAms").addEventListener("change", () => { $("amsSlot").disabled = !$("useAms").checked; });
    $("amsSlot").disabled = true;

    canvas.addEventListener("pointerdown", (event) => {
      state.dragging = true;
      state.lastPointer = [event.clientX, event.clientY];
      canvas.classList.add("is-dragging");
      canvas.setPointerCapture(event.pointerId);
    });
    canvas.addEventListener("pointermove", (event) => {
      if (!state.dragging) return;
      const current = [event.clientX, event.clientY];
      state.yaw += (current[0] - state.lastPointer[0]) * 0.012;
      state.pitch += (current[1] - state.lastPointer[1]) * 0.012;
      state.pitch = Math.max(-1.45, Math.min(1.45, state.pitch));
      state.lastPointer = current;
      draw();
    });
    const stopDragging = () => { state.dragging = false; canvas.classList.remove("is-dragging"); };
    canvas.addEventListener("pointerup", stopDragging);
    canvas.addEventListener("pointercancel", stopDragging);
    canvas.addEventListener("wheel", (event) => {
      event.preventDefault();
      state.zoom *= Math.exp(-event.deltaY * 0.001);
      state.zoom = Math.max(0.55, Math.min(2.5, state.zoom));
      draw();
    }, { passive: false });
    canvas.addEventListener("keydown", (event) => {
      const amount = 0.12;
      if (event.key === "ArrowLeft") state.yaw -= amount;
      else if (event.key === "ArrowRight") state.yaw += amount;
      else if (event.key === "ArrowUp") state.pitch -= amount;
      else if (event.key === "ArrowDown") state.pitch += amount;
      else return;
      event.preventDefault();
      draw();
    });
    window.addEventListener("resize", draw);
  }

  try {
    initGl();
    bindInteraction();
    loadHealth();
    // Explicit playback only, including when reduced motion is preferred.
    loadModel("animation");
  } catch (error) {
    showOverlay(`初始化失败：${error.message}`, true);
  }
})();
