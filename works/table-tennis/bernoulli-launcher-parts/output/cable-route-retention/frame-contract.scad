use </Users/norman/CodexProjects/Pingpang-BernoulliLauncherParts/cad/cable-route-retention.scad>
function pack(v)=[for(x=v)let(i=floor(x),j=floor((x-i)*1e6))[i,j,round(((x-i)*1e6-j)*1e6)]];
echo("FRAME12",[pack(crr_C()),pack(crr_N())]);
