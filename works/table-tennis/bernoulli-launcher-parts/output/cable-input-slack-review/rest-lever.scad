include </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/parameters.scad>
use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-trigger-input.scad>
module probe(){translate(ci_point(62,80,2))sphere(d=1.5,$fn=72);}
intersection(){probe();ci_local_lever(0);}
