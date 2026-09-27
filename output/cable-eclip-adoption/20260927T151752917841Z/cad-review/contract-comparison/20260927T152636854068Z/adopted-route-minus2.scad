use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-input.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-housing-route.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-contract-codec.scad>
cr_require_valid()echo(cc_pack([ci_install_delta(),cr_corner_shift(),cr_input_port(),cr_output_port(),cr_vertices(),cr_lines(),[for(i=[1:3])cr_arc(i)],cr_length(),cr_base_length()]));
