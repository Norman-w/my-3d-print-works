"""Negative controls: overinsertion and reversal must hit rigid host geometry."""
import json,shutil
import build as d
from check_partition import solids

def main():
    s=solids();hosts=s['left']+s['right'];out=[]
    def hit(name,part,host):
        volume=abs((part^host).volume());assert volume>1,(name,volume)
        out.append({'case':name,'rigid_interference_mm3':volume,'result':'blocked'})
    hit('pink +Y overinsert 0.5mm',s['back'].translate([0,.5,0]),hosts)
    hit('green -Y overinsert 0.5mm',s['lower'].translate([0,-.5,0]),hosts)
    hit('lid 180deg reversal',s['lid'].rotate([0,0,180]),hosts)
    hit('pink upside down around its insertion axis',s['back'].rotate([0,180,0]).translate([0,0,d.param('SPLIT_Z')-4]),hosts)
    for dx in [-1,1]:
        hit(f'upper core X shift {dx}mm with pin seated',s['upper'].translate([dx,0,0]),s['pin'])
    # A pin inserted fully while the yellow core is 1mm off its datum must bind.
    hit('quick pin insertion with upper core 1mm misplaced',s['pin'],s['upper'].translate([1,0,0]))
    source=d.text
    report={'checks':out,'guide_diameter_mm':d.param('GUIDE_D'),'socket_diameter_mm':d.param('GUIDE_D')+2*d.param('RADIAL_CLEARANCE'),'nominal_radial_clearance_mm':d.param('RADIAL_CLEARANCE'),'shoulder_thickness_mm':d.param('SHOULDER_THICK'),'min_additions_to_product_distance_checked_by_cavity_partition':True,'physical_fit_and_band_holding_force':'not_tested','source_sha256':__import__('hashlib').sha256(source.encode()).hexdigest()}
    (d.HERE/'location-validation.json').write_text(json.dumps(report,indent=2)+'\n');shutil.copy2(d.HERE/'location-validation.json',d.WEB/'location-validation.json');print(json.dumps(report,indent=2))
if __name__=='__main__':main()
