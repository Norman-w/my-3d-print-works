// v1.19 PU浇注硬模方案 v1，mm。X=上横梁，Y=下脚，Z向上。
// 本模具以经倒角/阴刻的成品STL为精确型腔；成品参数化源仍保留在v1.19目录。
// 名义配合：不加全局缩放、不预设未选定PU的收缩率。夹具合模，无定位销/卡扣。
// 仅适用于弹性PU：下卡臂端部0.6mm小倒扣需要弹性让位，非全刚性无干涉脱模。
FEATURE="assembly";
BX=84; BY=102; Z0=-33.5; Z1=43; SPLIT_Z=30.2;
CORE_DROP=1;
module box(lo,hi){translate(lo)cube(hi-lo);}
module product(){import("../exports/perpendicular-u-joint-v1.19-engraved-logo/guard-v1.19.stl",convexity=20);}
module stock(){box([-BX/2,-BY/2,Z0],[BX/2,BY/2,Z1]);}
module upper_envelope(){union(){
    box([-BX/2,-10.5,0],[BX/2,10.5,23]);
    // 通孔下缘凸倒角归上梁芯，先下降1mm再沿X抽出，避免圆孔倒扣。
    translate([0,0,23])cylinder(d=17.2,h=.6,$fn=64);
}}
module upper_core(){union(){
    difference(){upper_envelope();product();}
    // 等截面延长握持区：避免肩部挡住左右外模的X向移动。
    box([BX/2,-10.5,0],[BX/2+10,10.5,23]);
}}
module lower_envelope(){union(){
    box([-10.9,-BY/2,-22],[10.9,BY/2,0]);
    // 最底部扣唇之间18.8mm开口，芯从Y端抽出，不从Z硬拔。
    box([-9.4,-BY/2,Z0],[9.4,BY/2,-22]);
}}
module end_envelope(s=1){scale([1,s,1])box([-20.9,21.5,0],[20.9,BY/2,SPLIT_Z]);}
module end_core(s=1){difference(){end_envelope(s);product();}}
module back_core(){union(){end_core(-1);
    box([-20.9,-BY/2-10,0],[20.9,-BY/2,SPLIT_Z]);
}}
module lower_core(){union(){difference(){lower_envelope();product();}
    end_core(1);
    // 型腔之外的连接桥，把+Y端部芯和下脚芯连成一个件。
    box([-10.9,40,-1],[10.9,BY/2,1]);
    box([-15.9,BY/2,Z0],[15.9,BY/2+10,4]);
}}
module ports(){
    // 顶部主浇口：成品顶面+Y侧，避开孔柱和阴刻字样。
    translate([0,15.5,30])cylinder(d=6,h=14,$fn=40);
    translate([0,15.5,37])cylinder(d1=6,d2=16,h=6.1,$fn=48);
    for(x=[-23,23])for(y=[-18,18])
        translate([x,y,30])cylinder(d=1.2,h=14,$fn=16);
}
module lid_envelope(){union(){
    box([-BX/2,-BY/2,SPLIT_Z],[BX/2,BY/2,Z1]);
    // 圆孔芯与顶盖一体：下口扩径部分已分配给可下降的上梁芯。
    translate([0,0,23.6])cylinder(d=17.2,h=SPLIT_Z-23.6+.1,$fn=64);
}}
module lid(){difference(){lid_envelope();product();ports();}}
module shell(sign=1){difference(){
    if(sign>0)box([0,-BY/2,Z0],[BX/2,BY/2,SPLIT_Z]);
    else box([-BX/2,-BY/2,Z0],[0,BY/2,SPLIT_Z]);
    product();upper_envelope();lower_envelope();end_envelope(1);end_envelope(-1);lid_envelope();ports();
}}
if(FEATURE=="ports")intersection(){ports();stock();}
else if(FEATURE=="left")shell(-1);
else if(FEATURE=="right")shell(1);
else if(FEATURE=="lid")lid();
else if(FEATURE=="upper")upper_core();
else if(FEATURE=="lower")lower_core();
else if(FEATURE=="back")back_core();
else if(FEATURE=="product")product();
else {color("#48a8dd",.35)shell(-1);color("#6383ed",.35)shell(1);
 color("#a877df",.6)lid();color("#eeb750")upper_core();
 color("#4dbda6")lower_core();color("#f08eae")back_core();color("#ec7956")product();}
