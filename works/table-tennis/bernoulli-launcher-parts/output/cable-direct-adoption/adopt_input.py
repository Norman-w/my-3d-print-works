"""Adopt the frozen direct-pull geometry, preserving the public ci contract.

Does not publish a page or manufacture anything. Historical source is archived.
"""
from pathlib import Path
import hashlib, json

ROOT=Path(__file__).resolve().parents[2]
V2=ROOT/'output/cable-direct-pull-v2'
OLD=V2/'pre-adoption'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(V2/'candidate.scad')=='f76a83eeb95644bd3c856922b31da749cc47c083d688d271116f946493994588'
old=(OLD/'cad/cable-trigger-input.scad').read_text()
body=(V2/'candidate.scad').read_text().replace('cdp_', 'ci_')
body=body.replace('include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/parameters.scad>', 'include <parameters.scad>')
body=body.replace('// Direct pull v2: 5 mm nominal axial lead-in; input adjuster budget +/-2 mm. NOT RELEASED.',
 '// Fixed-guide direct-pull input. Adopted from frozen v2 geometry; manufacturing open.\n// Nominal 5 mm lead, assembly setting +/-2 mm. See ci_spec() for one source contract.')
body=body.replace('ci_part="none";', 'ci_part="assembly";')
body=body.replace('function ci_angle(u,delta=ci_delta,lo=0,hi=30,n=0)=n>=48?',
 'function ci_angle(u,delta=ci_delta,lo=0,hi=30,n=0)=assert(is_num(u)&&u>=0&&u<=22,"Input travel is restricted to 0..22 mm; system work stroke is 20")assert(abs(delta)<=2,"Input setting outside +/-2 mm")n>=48?')
body=body.replace('module ci_contract(){ci_direct_contract();}', 'module ci_contract(){echo(ci_contract=ci_spec());}')
spec=old[old.index('function ci_spec()='):old.index('module ci_contract()')]
replacements={
 '["status","unreleased-input-candidate"]':'["status","direct-pull-adopted-manufacturing-open"]',
 '["radius_cable",ci_R]':'["motion_law","fixed-guide-direct-pull-v2"],\n ["ball_orbit_radius",ci_ball_arm_R],["fairlead_center",ci_fairlead_C],\n ["fairlead_core_radius",ci_fairlead_R],["fairlead_surface_radius",ci_fairlead_surface_R],\n ["fairlead_extent_deg",ci_fairlead_extent_deg],["wire_terminal_local",ci_terminal],\n ["angle_solve_deg",[0,30]],["input_u_domain",[0,22]],\n ["adjuster_delta",ci_delta],["adjuster_delta_range",ci_delta_bounds],\n ["axial_leadin",ci_axial_leadin()],["radius_cable",ci_R],\n ["radius_cable_semantics","legacy alias of guide core radius; not constant takeup arm"]',
 '["wire_tangent_local",[0,60,2]]':'["wire_tangent_local",ci_fairlead_C+[0,ci_fairlead_R,0]]',
 '["adjuster_exit_local",[-29,60,2]]':'["adjuster_exit_local",ci_exit()]',
 '["adjuster_head_x",[-63,-53]]':'["adjuster_head_x",[-63+ci_delta,-53+ci_delta]]',
 '["ferrule_mouth_display_local",[ci_ferrule_mouth_display,60,2]]':'["ferrule_mouth_display_local",[ci_ferrule_mouth(),60,2]]',
 '["ferrule_tip_display_local",[ci_ferrule_tip_display,60,2]]':'["ferrule_tip_display_local",[ci_ferrule_tip_display+ci_delta,60,2]]',
 '["housing_end_display_local",[ci_ferrule_mouth_display+9,60,2]]':'["housing_end_display_local",[ci_ferrule_mouth()+9,60,2]]',
 '["adjuster_thread_x",[-53,-29]],["adjuster_overall_x",[-63,-29]]':'["adjuster_thread_x",[-53+ci_delta,-29+ci_delta]],["adjuster_overall_x",[-63+ci_delta,-29+ci_delta]]',
 '["adjuster_exposed_thread_each",3.2]':'["adjuster_exposed_thread_each",min(ci_thread_exposure())],["adjuster_exposed_thread_sides",ci_thread_exposure()]',
 '["part_selectors",[':'["cap_bolts_local_xy",ci_cap_bolts],["cap_split_local_z",3.1],\n ["cap_fasteners",[["M3x8 socket screw D5.5 H3",2],["M3 nut SW5.5 H2.4",2]]],\n ["setup","Lock delta after reseating housing and resetting output core zero; stop coordinated to output stroke"],\n ["part_selectors",[',
 '"lever","cover"':'"lever","terminal-cap","cover"',
}
for a,b in replacements.items():
 assert a in spec,a
 spec=spec.replace(a,b)
body=body.replace('module ci_contract(){', 'function ci_install_delta()=ci_delta;\n'+spec+'\nmodule ci_contract(){')
probe=old[old.index('module ci_probe('):old.index('module ci_assembly()')]
probe=probe.replace('ci_lever(u);','ci_lever(u);ci_terminal_cap(u);')
probe=probe.replace('translate(ci_point(ci_R,45,2))','translate(ci_terminal)')
probe=probe.replace('translate(ci_point(ci_R,45,22))','translate(ci_terminal+[0,0,20])')
# terminal-entry is intentionally with its small cap removed.
probe=probe.replace('intersection(){ci_lever(u);ci_terminal_cap(u);ci_to_cad()', 'intersection(){ci_lever(u);ci_to_cad()')
body=body.replace('module ci_assembly(){',probe+'\nmodule ci_assembly(){')
body=body.replace('else if(ci_part=="contract")ci_direct_contract();',
 'else if(ci_part=="probe")ci_probe();\nelse if(ci_part=="contract")ci_contract();')
(ROOT/'cad/cable-trigger-input.scad').write_text(body)

# Every moving-printed union now includes the terminal cap.
p=ROOT/'cad/cable-trigger-system.scad';s=(OLD/'cad/cable-trigger-system.scad').read_text()
s=s.replace('ci_lever(cam_stroke*t);','ci_lever(cam_stroke*t);ci_terminal_cap(cam_stroke*t);')
s=s.replace('ci_lever(cam_stroke*ct_t);','ci_lever(cam_stroke*ct_t);ci_terminal_cap(cam_stroke*ct_t);')
# When the first operand was a bare lever, it must remain one union operand.
s=s.replace('intersection(){ci_lever(cam_stroke*ct_t);ci_terminal_cap(cam_stroke*ct_t);',
            'intersection(){union(){ci_lever(cam_stroke*ct_t);ci_terminal_cap(cam_stroke*ct_t);}')
s=s.replace('intersection(){union(){ci_body();ci_cover();}ci_lever(cam_stroke*ct_t);ci_terminal_cap(cam_stroke*ct_t);}',
            'intersection(){union(){ci_body();ci_cover();}union(){ci_lever(cam_stroke*ct_t);ci_terminal_cap(cam_stroke*ct_t);}}')
s=s.replace('else if(ct_part=="input-lever")ci_lever(cam_stroke*ct_t);ci_terminal_cap(cam_stroke*ct_t);',
            'else if(ct_part=="input-lever")ci_lever(cam_stroke*ct_t);\nelse if(ct_part=="input-terminal-cap")ci_terminal_cap(cam_stroke*ct_t);')
s=s.replace('    // Positive control:', '''    else if(ct_probe=="input-core-free")intersection(){
        union(){difference(){ci_body();ci_to_cad()ci_guide_solid();}
            ci_cover();ci_lever(cam_stroke*ct_t);ci_terminal_cap(cam_stroke*ct_t);}
        ci_cable(cam_stroke*ct_t);
    }
    // Positive control:''')
p.write_text(s)

p=ROOT/'cad/cable-service-contract.scad';s=(OLD/'cad/cable-service-contract.scad').read_text()
s=s.replace('ci_body();ci_cover();ci_lever(u);', 'ci_body();ci_cover();ci_lever(u);ci_terminal_cap(u);')
p.write_text(s)

p=ROOT/'cad/cable-scene-export.scad';s=(OLD/'cad/cable-scene-export.scad').read_text()
s=s.replace('else if(part=="input-cover")','else if(part=="input-terminal-cap")ci_terminal_cap(20*t);\n    else if(part=="input-cover")')
p.write_text(s)
report=dict(status='INPUT_GEOMETRY_AND_PUBLIC_CONTRACT_ADOPTED_REVIEW_PENDING',
    candidate_sha256=sha(V2/'candidate.scad'),
    changed_source_sha256={str(p.relative_to(ROOT)):sha(p) for p in [ROOT/'cad/cable-trigger-input.scad',ROOT/'cad/cable-trigger-system.scad',ROOT/'cad/cable-service-contract.scad',ROOT/'cad/cable-scene-export.scad']},
    note='Same frozen geometry renamed into ci namespace; contract and parent unions updated. Geometry parity and native checks must be run before publication.',manufacturing_release=False)
(Path(__file__).parent/'input-adoption.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
