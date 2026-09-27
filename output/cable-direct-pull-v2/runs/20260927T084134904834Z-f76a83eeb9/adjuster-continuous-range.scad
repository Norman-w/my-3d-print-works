include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/output/cable-direct-pull-v2/candidate.scad>
intersection(){union(){cdp_body();cdp_cover();}cdp_to_cad(){cdp_xhex(60,2,-65,14,8);cdp_xcyl(60,2,-55,28,6);cdp_xcyl(60,2,cdp_ferrule_mouth(-2),15,5.5);}}
