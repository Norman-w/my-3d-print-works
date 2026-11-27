/**
 * Frontend-only position demonstration, in the CAD's millimetre coordinates.
 * u is carriage displacement 0..20 mm, NOT elapsed time or a force solution.
 * STL assets already contain their la_t=0 assembly positions; these are deltas.
 *
 * Position law: cad/cam-study.scad cam_gate_r()/cam_gate_z();
 * carriage: cad/feeder-supports.scad feeder_carriage();
 * spring reference outline: cad/feeder-return-spring.scad rs_spring().
 * No CAD, mesh validation, physical dynamics, or printer is invoked here.
 */

const STROKE = 20;
const BALL_DIAMETER = 41;
const FRONT_GATE_Z = 0;
const REAR_GATE_Z = -28.5;
const PARKED_OFFSET = Math.sqrt((BALL_DIAMETER / 2 + 2.5) ** 2 - 21 ** 2);
const FIRST_READY_Z = FRONT_GATE_Z - PARKED_OFFSET;
const REAR_HELD_Z = REAR_GATE_Z - PARKED_OFFSET;
const EXIT_SHOWN_Z = 80;

function clamp(value, min, max, name) {
  if (typeof value !== 'number' || !Number.isFinite(value)) {
    throw new TypeError(`${name} must be a finite number`);
  }
  return Math.max(min, Math.min(max, value));
}

function mix(a, b, amount) {
  return a + (b - a) * amount;
}

/** Tip-centre radii. Each gate is a mirrored LEFT/RIGHT pair of fingers. */
export function radii(u) {
  const stroke = clamp(u, 0, STROKE, 'u');
  return {
    rear: 26 - 5 * clamp(stroke / 8, 0, 1, 'rear fraction'),
    front: 21 + 5 * clamp((stroke - 12) / 8, 0, 1, 'front fraction'),
  };
}

/** Translation relative to the uncentred, already assembled la_t=0 STL. */
export function partTranslation(id, u) {
  const stroke = clamp(u, 0, STROKE, 'u');
  if (id === 'frame' || id === 'moving-spacer') return [0, 0, stroke];
  const match = /^(?:finger|pin-block)-(right|left)-(front|rear)$/.exec(id);
  if (!match) return [0, 0, 0]; // Covers fixed caps, keepers, gibs and body parts.
  const side = match[1] === 'right' ? 1 : -1;
  const gate = match[2];
  const initialRadius = gate === 'rear' ? 26 : 21;
  return [side * (radii(stroke)[gate] - initialRadius), 0, 0];
}

/**
 * Spring pin axes at Y33.1, eye-outline centres, and variable-length coil span.
 * Draw fixed lower eye + translated upper eye + lengthened middle separately.
 * Uniformly scaling the entire spring STL would incorrectly move/deform eyes.
 */
export function springPose(u) {
  const stroke = clamp(u, 0, STROKE, 'u');
  const fixedPinZ = -14 + (3.4 - 3) / 2 - 0.02;
  const movingPinZ = 13 + stroke;
  const hookOffset = (7 - 2 * 0.63 - 4) / 2;
  const coilOffset = hookOffset + 7 / 2;
  return {
    x: -72,
    y: 33.1,
    fixedPinZ,
    movingPinZ,
    lowerLoopZ: fixedPinZ + hookOffset,
    upperLoopZ: movingPinZ - hookOffset,
    coilStartZ: fixedPinZ + coilOffset,
    coilEndZ: movingPinZ - coilOffset,
  };
}

/**
 * Six presentation intervals, with deliberately paused ball motion while the
 * gates move. Ball translation occurs only after the relevant gate is fully
 * open. This is a readable flow illustration, NOT simulated pneumatic motion.
 * balls[] retain A/B/C identities during one cycle; at p=1 B is the ready ball.
 */
export function cyclePose(p) {
  const phase = clamp(p, 0, 1, 'p');
  const ready = [FIRST_READY_Z, FIRST_READY_Z - BALL_DIAMETER,
    FIRST_READY_Z - 2 * BALL_DIAMETER];
  const held = [EXIT_SHOWN_Z, REAR_HELD_Z, REAR_HELD_Z - BALL_DIAMETER];
  if (phase === 0) {
    return { u: 0, phase: '待发', title: '待发：第一球已到前挡',
      detail: '前挡关闭、后挡开放。第一球停在前挡，后两球依次排队；每道挡位都有左右两根挡指。',
      returning: false, balls: ready };
  }
  if (phase < 0.18) {
    return { u: mix(0, 8, phase / 0.18), phase: '后挡关闭', title: '先关后挡，拦住后续球',
      detail: '滑架向出球方向移动，后侧斜槽带动两根后挡指向内收；前挡保持关闭。',
      returning: false, balls: ready };
  }
  if (phase < 0.30) {
    return { u: mix(8, 12, (phase - 0.18) / 0.12), phase: '双挡关闭', title: '经过双挡都关的过渡段',
      detail: '滑架继续走，但四根挡指保持关闭。两道挡位的关闭阶段重叠，第一球暂不放行。',
      returning: false, balls: ready };
  }
  if (phase < 0.50) {
    return { u: mix(12, 20, (phase - 0.30) / 0.20), phase: '前挡开放', title: '再开前挡，准备放行第一球',
      detail: '前侧斜槽带动两根前挡指向外退；后挡保持关闭。本演示先把挡指打开，再单独展示球流转。',
      returning: false, balls: ready };
  }
  if (phase < 0.65) {
    const f = (phase - 0.50) / 0.15;
    return { u: 20, phase: '保持并出球', title: '向虎口扣到底并保持：只放走前面的球',
      detail: '示意气流将第一球送走；第二、第三球一同前移，第二球停到后挡。球速与动画时间不是动力学计算。',
      returning: false, balls: ready.map((z, i) => mix(z, held[i], f)) };
  }
  if (phase < 0.85) {
    const u = mix(20, 0, (phase - 0.65) / 0.20);
    return { u, phase: '松手回程',
      title: u > 12 ? '松手：先关闭前挡' : u > 8 ? '回程经过双挡关闭段' : '前挡已关，再开放后挡',
      detail: '弹簧示意拉回公共架，同一组槽按相反顺序驱动挡指。已发出的第一球应先离开，回程速度未作物理计算。',
      returning: true, balls: held };
  }
  const f = (phase - 0.85) / 0.15;
  const balls = [EXIT_SHOWN_Z, mix(REAR_HELD_Z, FIRST_READY_Z, f),
    mix(REAR_HELD_Z - BALL_DIAMETER, FIRST_READY_Z - BALL_DIAMETER, f)];
  return { u: 0, phase: phase === 1 ? '下颗就绪' : '补球',
    title: phase === 1 ? '下颗就绪：完成一次点射循环' : '完整松回后，下一球补到前挡',
    detail: '前挡关闭、后挡开放。第二球成为下一次待发球，第三球随之排队；这是球流转示意。',
    returning: false, balls };
}
