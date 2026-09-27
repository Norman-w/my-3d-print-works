include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-input-lip-candidate/candidate.scad>
intersection(){union(){cil_body();cil_cover();difference(){cil_fixed_hardware();cil_to_cad()for(z=[-3.75,7.5])cil_zring(0,0,z,.25,16,8.4);}}cil_moving(10);}
