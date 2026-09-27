"""Read source contracts and solve the explicitly supported direct-pull law.

No legacy wrap fallback, STL inference, implicit domain clamping, or cut-length
claim. The geometric law describes a taut core on the specified fixed guide.
"""
from pathlib import Path
import hashlib
import json
import math
import re
import subprocess

MOTION_LAW = 'fixed-guide-direct-pull-v2'
EXE = '/Applications/OpenSCAD.app/Contents/MacOS/OpenSCAD'


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def pairs(value, label='contract'):
    if not isinstance(value, list):
        raise ValueError(f'{label}: expected a list of key/value pairs')
    result = {}
    for row in value:
        if not isinstance(row, list) or len(row) != 2 or not isinstance(row[0], str):
            raise ValueError(f'{label}: malformed key/value pair')
        if row[0] in result:
            raise ValueError(f'{label}: duplicate key {row[0]}')
        result[row[0]] = row[1]
    return result


def number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f'{label}: expected a finite number')
    return float(value)


def vector(value, size, label):
    if not isinstance(value, (list, tuple)) or len(value) != size:
        raise ValueError(f'{label}: expected {size} numbers')
    return tuple(number(v, label) for v in value)


def source_hashes(scad_roots, extra_files=()):
    """Resolve every static include/use recursively; missing dependencies fail."""
    pending = [Path(p).resolve() for p in scad_roots]
    found = set()
    strip = re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"')
    while pending:
        path = pending.pop()
        if path in found:
            continue
        if not path.is_file():
            raise ValueError(f'Missing SCAD dependency: {path}')
        found.add(path)
        source = strip.sub('', path.read_text())
        for name in re.findall(r'\b(?:include|use)\s*<([^>]+)>', source):
            dependency = Path(name)
            pending.append((dependency if dependency.is_absolute() else path.parent/dependency).resolve())
    found.update(Path(p).resolve() for p in extra_files)
    return {str(p): sha(p) for p in sorted(found)}


# Default OpenSCAD echo rounds numbers to six significant digits. Emit numeric
# strings with twelve decimal places, then decode JSON, to preserve contract
# coordinates and frame orthogonality. Two six-digit chunks avoid str()'s
# scientific notation/precision reduction on large fractional integers.
SCAD_JSON = r'''
function ac_pad6(x)=let(s=str(x))str(len(s)<6?"0":"",len(s)<5?"0":"",len(s)<4?"0":"",len(s)<3?"0":"",len(s)<2?"0":"",s);
function ac_num(x)=assert(abs(x)<100000,"Contract number too large for fixed-decimal encoder")let(a=abs(x),i=floor(a),f=round((a-i)*1000000000000),carry=floor(f/1000000000000),v=f-carry*1000000000000)str(x<0?"-":"",i+carry,".",ac_pad6(floor(v/1000000)),ac_pad6(v%1000000));
function ac_escape(s,i=0)=i>=len(s)?"":str(s[i]=="\\"?"\\\\":s[i]=="\""?"\\\"":s[i]=="\n"?"\\n":s[i]=="\r"?"\\r":s[i]=="\t"?"\\t":s[i],ac_escape(s,i+1));
function ac_join(a,i=0)=i>=len(a)?"":str(i>0?",":"",ac_json(a[i]),ac_join(a,i+1));
function ac_json(x)=is_undef(x)?"null":is_bool(x)?(x?"true":"false"):is_num(x)?ac_num(x):is_string(x)?str("\"",ac_escape(x),"\""):is_list(x)?str("[",ac_join(x),"]"):assert(false,"Unsupported contract value");
'''


def export_contract(wrapper, expression, imports, *, cwd):
    """Read a native expression without exporting geometry; returns data/evidence."""
    wrapper = Path(wrapper)
    content = ''.join(f'use <{Path(p).resolve()}>\n' for p in imports)
    content += SCAD_JSON + '\necho("ACTUATION_JSON",ac_json('+expression+'));\n'
    wrapper.write_text(content)
    target = wrapper.with_suffix('.echo')
    command = [EXE, '--hardwarnings', '-o', str(target), str(wrapper)]
    run = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
    log = run.stdout+run.stderr
    wrapper.with_suffix('.log').write_text(log)
    emitted = target.read_text() if target.exists() else ''
    if run.returncode or 'WARNING:' in log+emitted or 'ERROR:' in log+emitted:
        raise RuntimeError('Native contract failed: '+log+emitted)
    prefix = 'ECHO: "ACTUATION_JSON", '
    lines = [s[len(prefix):] for s in emitted.splitlines() if s.startswith(prefix)]
    if len(lines) != 1:
        raise ValueError('Expected exactly one high-precision native contract')
    # OpenSCAD echo wraps a string in quotes but emits its internal quotes
    # verbatim (it is not a Python/JSON string literal). The payload itself is
    # JSON produced by ac_json; remove only the outer echo delimiters.
    if not (lines[0].startswith('"') and lines[0].endswith('"')):
        raise ValueError('Unexpected native JSON string framing')
    decoded = json.loads(lines[0][1:-1])
    return decoded, {'command':command, 'returncode':run.returncode,
                     'wrapper':str(wrapper), 'wrapper_sha256':sha(wrapper),
                     'echo':str(target), 'echo_sha256':sha(target),
                     'numeric_encoding':'12 decimal places; no six-significant-digit echo coordinates'}


class DirectPullContract:
    def __init__(self, spec):
        self.spec = spec
        if spec.get('motion_law') != MOTION_LAW:
            raise ValueError('Unsupported motion_law; legacy circular-wrap fallback is forbidden')
        self.R = number(spec['ball_orbit_radius'], 'ball_orbit_radius')
        self.guide_R = number(spec['fairlead_core_radius'], 'fairlead_core_radius')
        self.C = vector(spec['fairlead_center'], 3, 'fairlead_center')
        self.terminal = vector(spec['wire_terminal_local'], 3, 'wire_terminal_local')
        self.tangent = vector(spec['wire_tangent_local'], 3, 'wire_tangent_local')
        self.exit_current = vector(spec['adjuster_exit_local'], 3, 'adjuster_exit_local')
        self.mouth_current = vector(spec['ferrule_mouth_display_local'], 3, 'ferrule_mouth_display_local')
        self.angle_domain = vector(spec['angle_solve_deg'], 2, 'angle_solve_deg')
        self.u_domain = vector(spec['input_u_domain'], 2, 'input_u_domain')
        self.delta_domain = vector(spec['adjuster_delta_range'], 2, 'adjuster_delta_range')
        self.delta = number(spec['adjuster_delta'], 'adjuster_delta')
        self.stroke = number(spec['stroke'], 'stroke')
        self.finger_R = number(spec['radius_finger'], 'radius_finger')
        self.z = number(spec['wire_z'], 'wire_z')
        self.extent = number(spec['fairlead_extent_deg'], 'fairlead_extent_deg')
        if self.R <= 0 or self.finger_R <= 0 or self.C[0] >= 0:
            raise ValueError('Positive orbit/finger radii and a guide centre left of the axis are required')
        if not (self.angle_domain[0] == 0 < self.angle_domain[1] < 90):
            raise ValueError('Supported angle solve domain is [0, upper<90 degrees]')
        if not (self.u_domain[0] == 0 < self.stroke <= self.u_domain[1]):
            raise ValueError('Working stroke must lie within the declared zero-based input domain')
        if not self.delta_domain[0] < self.delta_domain[1]:
            raise ValueError('Invalid adjustment domain')
        self.check_delta(self.delta)
        # This version is the stated tangent +X, equal-radius, zero-angle law.
        # Refuse another geometric arrangement instead of adapting it silently.
        expected = [(self.guide_R,self.R),(self.C[1],0),(self.C[2],self.z)]
        expected += list(zip(self.terminal, (0,self.R,self.z)))
        expected += list(zip(self.tangent, (self.C[0],self.R,self.z)))
        expected += [(self.exit_current[1],self.R),(self.exit_current[2],self.z),
                     (self.mouth_current[1],self.R),(self.mouth_current[2],self.z)]
        if any(abs(a-b)>1e-9 for a,b in expected):
            raise ValueError('Unsupported direct-pull geometry: rest ball/tangent/guide/axis relation changed')
        if any(self.leadin(d) <= 0 for d in self.delta_domain):
            raise ValueError('An adjustment endpoint crosses the fixed tangent start')
        self.monotonic_arm_lower_bound = self.R*math.cos(math.radians(self.angle_domain[1]))
        if self._takeup(self.angle_domain[1]) < self.u_domain[1]:
            raise ValueError('Angle interval does not bracket declared input travel')
        if self.state(self.u_domain[1])['guide_contact_angle_deg'] > self.extent+1e-9:
            raise ValueError('Input domain exceeds the physical guide extent')

    def check_delta(self, delta):
        d = number(delta, 'delta')
        if not self.delta_domain[0] <= d <= self.delta_domain[1]:
            raise ValueError('delta outside the exact declared adjustment domain')
        return d

    def leadin(self, delta):
        d = self.check_delta(delta)
        return self.C[0]-(self.exit_current[0]+d-self.delta)

    def _geometry(self, angle_deg):
        a = math.radians(angle_deg)
        B = (self.R*math.sin(a), self.R*math.cos(a), self.z)
        dx,dy = B[0]-self.C[0], B[1]-self.C[1]
        rho = math.hypot(dx,dy)
        if rho <= self.guide_R:
            raise ValueError('Ball is not exterior to the guide circle')
        phi = math.atan2(dx,dy)-math.acos(self.guide_R/rho)
        if phi < -1e-12:
            raise ValueError('Forward contact branch invalid; no unconstrained spline fallback')
        phi = max(0.0,phi)  # roundoff only at exact zero contact, not input clamping.
        tangent_length = math.sqrt(rho*rho-self.guide_R*self.guide_R)
        return B,phi,tangent_length,self.R*math.cos(a-phi)

    def path_length(self, angle_deg, delta=None):
        a = number(angle_deg, 'angle_deg')
        if not self.angle_domain[0] <= a <= self.angle_domain[1]:
            raise ValueError('angle outside the exact solve domain')
        _,phi,length,_ = self._geometry(a)
        return self.leadin(self.delta if delta is None else delta)+self.guide_R*phi+length

    def _takeup(self, angle_deg):
        return self.path_length(angle_deg)-self.path_length(0)

    def solve(self, u, delta=None):
        u = number(u, 'u')
        self.check_delta(self.delta if delta is None else delta)
        if not self.u_domain[0] <= u <= self.u_domain[1]:
            raise ValueError('u outside the exact declared input domain')
        if u == 0:
            return 0.0
        lo,hi = self.angle_domain
        for _ in range(64):
            mid = (lo+hi)/2
            if self._takeup(mid) < u:
                lo = mid
            else:
                hi = mid
        return (lo+hi)/2

    def state(self, u, delta=None):
        d = self.check_delta(self.delta if delta is None else delta)
        theta = self.solve(u,d)
        B,phi,tangent_length,arm = self._geometry(theta)
        path = self.path_length(theta,d)
        rest = self.path_length(0,d)
        finger_jacobian = self.finger_R*math.cos(math.radians(theta))
        return {'input_take_up_requested_mm':float(u),'adjuster_delta_mm':d,'angle_deg':theta,
                'ball_local':list(B),'guide_contact_angle_deg':math.degrees(phi),
                'straight_leadin_mm':self.leadin(d),'guide_arc_length_mm':self.guide_R*phi,
                'guide_to_ball_tangent_mm':tangent_length,'exit_to_ball_path_mm':path,
                'exit_to_ball_rest_path_mm':rest,'input_path_change_mm':path-rest,
                'effective_cable_arm_mm_per_rad':arm,
                'finger_rearward_mm':self.finger_R*math.sin(math.radians(theta)),
                'finger_jacobian_mm_per_rad':finger_jacobian,
                'horizontal_finger_force_ratio_ideal':arm/finger_jacobian}
