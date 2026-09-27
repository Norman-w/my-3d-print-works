include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-direct-pull-v2/candidate.scad>
intersection(){union(){cdp_body();cdp_cover();difference(){cdp_fixed_hardware(-2);cdp_to_cad()for(z=[-3.75,7.5])cdp_zring(0,0,z,.25,16,8.4);}}cdp_moving(14);}
