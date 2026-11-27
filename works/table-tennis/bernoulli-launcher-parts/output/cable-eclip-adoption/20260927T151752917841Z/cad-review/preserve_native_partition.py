from pathlib import Path
import difflib
R=Path(__file__).resolve().parents[4];O=Path(__file__).resolve().parent
p=R/'cad/cable-trigger-input.scad';s=p.read_text()
a='module ci_local_lever_zero(){difference(){\n ci_local_lever_blank();\n translate([0,0,-4])linear_extrude(height=12)ci_bush_hex_2d(ci_bush_socket_af);'
b='''// Retain the frozen Boolean construction partition for exact export comparison.
// The old round construction opening is wholly contained by the new hex socket.
module ci_local_lever_before_hex_socket(){difference(){
 ci_local_lever_blank();
 ci_zcyl(0,0,-4,12,12.2);'''
assert s.count(a)==1;s=s.replace(a,b)
a='module ci_local_terminal_cap(sweep=0){'
b='''module ci_local_lever_zero(){difference(){
 ci_local_lever_before_hex_socket();
 translate([0,0,-4])linear_extrude(height=12)ci_bush_hex_2d(ci_bush_socket_af);
}}
module ci_local_terminal_cap(sweep=0){''';assert s.count(a)==1;s=s.replace(a,b)
a='''module ci_local_cover(sweep=0){difference(){
 ci_local_cover_blank(sweep);
 ci_zcyl(0,0,7,8+sweep,ci_axis_bore_D);
 // For +Z continuous cover removal, the wider recess remains only at the
 // leading outer end; lower shifted small-bore material fills its old location.
 ci_zcyl(0,0,ci_axis_root_relief_z[0]+sweep,
   ci_axis_root_relief_z[1]-ci_axis_root_relief_z[0],ci_axis_root_relief_D);'''
b='''// These construction holes are fully swallowed by the final D8.3 through bore;
// no old spacer seat survives. Preserve the reviewed native Boolean partition.
module ci_local_cover_before_through_bore(sweep=0){difference(){
 ci_local_cover_blank(sweep);
 ci_zcyl(0,0,7,8+sweep,4.5);
 ci_zcyl(0,0,7.9,1.6,8.3);''';assert s.count(a)==1;s=s.replace(a,b)
a='module ci_mount_hardware_cad(){'
b='''module ci_local_cover_through(sweep=0){difference(){
 ci_local_cover_before_through_bore(sweep);
 ci_zcyl(0,0,7,8+sweep,ci_axis_bore_D);
}}
module ci_local_cover(sweep=0){difference(){
 ci_local_cover_through(sweep);
 // Continuous +Z sweep: the wider recess stays at the leading outer end.
 ci_zcyl(0,0,ci_axis_root_relief_z[0]+sweep,
   ci_axis_root_relief_z[1]-ci_axis_root_relief_z[0],ci_axis_root_relief_D);
}}
module ci_mount_hardware_cad(){''';assert s.count(a)==1;s=s.replace(a,b);p.write_text(s)
paths=['cad/cable-trigger-input.scad','cad/cable-housing-route.scad','cad/cable-scene-export.scad']
(O/'adoption.patch').write_text(''.join(''.join(difflib.unified_diff((O/'frozen-baseline'/n).read_text().splitlines(True),(R/n).read_text().splitlines(True),fromfile='before/'+n,tofile='after/'+n))for n in paths))
