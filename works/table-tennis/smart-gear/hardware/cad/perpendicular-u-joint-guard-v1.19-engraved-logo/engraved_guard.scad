// 围挡止转卡 v1.19：v1.18 加强结构，顶部字样改为深0.6mm阴刻。
// mm; X=上管长度，Y=下脚长度，Z向上。顶面Z=31。
use <../perpendicular-u-joint-guard-v1.18-toe-bridge/toe_bridge_guard.scad>;
FEATURE="all";
ENGRAVE_DEPTH=0.6;
module logo_cutter(){
    translate([0,-15.5,31-ENGRAVE_DEPTH])
        linear_extrude(height=ENGRAVE_DEPTH+0.2,convexity=10)
        text("Norman@PingCloud",size=3,font="Arial:style=Bold",
             halign="center",valign="center",spacing=1,$fn=24);
}
if(FEATURE=="cutter")logo_cutter();
else if(FEATURE=="raw")toe_bridge_raw();
else difference(){toe_bridge_raw();logo_cutter();}
// 最终倒角成品由build.py生成；此入口保留原生参数化实体。
