#!/usr/bin/env python3
"""Freeze a bounded review of three official supplier pages and saved drawings.

Re-running verifies local evidence and rebuilds the report. It does not repeat
the web search, authenticate, contact a supplier, buy, or alter mechanical CAD.
"""
from pathlib import Path
from datetime import datetime, timezone
import hashlib,json,re

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(p,v):Path(p).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')

NIPPLE='https://www.norelem.de/en/Product-overview/Flexible-standard-component-system/03000/Accessories-for-indexing-plungers-cam-action-indexing-plungers-and-ball-lock-pins/Screw-nipples-locked-with-grub-screw/p/agid.30769'
FERRULE='https://www.norelem.mx/es/Vista-general-de-productos/Sistema-flexible-de-piezas-est%C3%A1ndar/03000/Accesorios-para-pernos-de-bloqueo-pasadores-de-bloqueo-y-pernos-de-bloqueo-de-bola/Fundas-terminales/Casquillo-terminal-lat%C3%B3n-pasivado-en-azul/p/03096-25-0350'
KIT='https://www.norelemusa.com/en-us/Product-Overview/Flexible-standard-component-system/03000/Accessory-for-indexing-plungers-cam-action-indexing-plungers-and-ball-lock-pins/Bowden-cables-for-indexing-plungers-with-remote-actuation/p/agid.32096'
PDF='https://www.norelem.mx/doc/mx/es/did.278516/03096-35_Datasheet_30769_Bosquillas_roscadas_de_apriete_con_tornillo_prisionero--es.pdf'

def main():
    source_paths=['docs/cable-hardware-evidence.md','cad/cable-output-interface.scad',
        'output/current-cable-supplier-closure/build_report.py',
        'output/current-cable-supplier-closure/retrieval.json',
        'output/current-cable-supplier-closure/retrieval-initial-bundled-python-ssl.json']
    for family in ['03096-35','03096-25','03096-14','03096-30']:
        source_paths += [f'output/cable-hardware-evidence/{family}-drawing.png',f'output/cable-hardware-evidence/{family}-assets.json']
    hashes={p:sha(ROOT/p)for p in source_paths}
    co=(ROOT/'cad/cable-output-interface.scad').read_text()
    scalar=lambda key:float(re.search(r'^'+key+r'=([0-9.]+);',co,re.M)[1])
    tail=scalar('co_wire_tail');diameter=scalar('co_nipple_d')
    assert scalar('co_wire_d')==1.5 and tail==8 and diameter==5
    reviewed={
        'review_date_local':'2026-09-27',
        'method':'Read existing local evidence first; inspect its three saved official drawings; limited official web/text and PDF search only for 03096-35,03096-25,03096-14. Nearby products returned by search were not used as specification substitutes.',
        'pages':[
            {'id':'official-nipple','url':NIPPLE,'scope':'03096-35 family; exact 03180507 dimensions retained from saved drawing/table evidence',
             'observed':'Official text confirms nickel-plated brass and clamping by grub screw. Accessible description does not state wire-specific torque, minimum free tail or retention force.',
             'web_parser_line_ranges':['34-56','58-63'],'cache_note':'Web tool reported crawled today; no authenticated CAD was obtained.'},
            {'id':'official-ferrule','url':FERRULE,'scope':'exact 03096-25-0350 product',
             'observed':'Listed D5.5,L11,D1=5,D2=2.5,L1=9,L2=4.5. Figure note identifies a crimp zone. No crimp force/tool/finished geometry or assembled bearing-seat depth is specified in accessible text.',
             'web_parser_line_ranges':['33-69','105-134'],'cache_note':'Web tool reported crawled today.'},
            {'id':'official-kit','url':KIT,'scope':'03096-14 family',
             'short_quote':'The Bowden cable can be shortened during installation to ensure a perfect fit in the respective application.',
             'observed':'Manufacturer permits installation shortening and adjustment after routing; minimum housing bend radius65 mm also applies during assembly, and housing is compression-only. Components are listed by category, without verified quantities per kit.',
             'web_parser_line_ranges':['48-63','78-83'],'cache_note':'Web tool reported crawled yesterday; permission is for the Bowden assembly, not a complete cut/crimp work instruction.'}],
        'additional_official_nipple_crosschecks':[
            {'url':'https://www.norelem.ch/de/Produkt%C3%BCbersicht/Flexibles-Normteilesystem/03000/Zubeh%C3%B6r-f%C3%BCr-Arretierbolzen-Sperrriegel-und-Kugelsperrbolzen/Schraubnippel-Klemmung-mit-Gewindestift/p/agid.30769',
             'result':'Same limited description; retrieved web extraction reported older cached content. No new numeric force/torque field.'},
            {'url':'https://www.norelem.mx/mx/es/Productos/Vista-general-de-productos/Sistema-flexible-de-piezas-est%C3%A1ndar/Piezas-de-presi%C3%B3n-con-resorte-Pernos-de-bloqueo-Topes-Elementos-de-centrado-y-posicionamiento-Fijaciones-Tuercas-correderas-en-ranura/Perno-de-bloqueo/Bosquillas-roscadas-de-apriete-con-tornillo-prisionero.html',
             'result':'Older official product table confirms exact03180507: D5,M4,D2=1.8,L7,L1=3.5. Exposes a190 kB PDF link, attempted below.'}],
        'pdf_attempt':{'url':PDF,'result':'web fetch404 Not Found','successfully_read':False},
        'access_limits':'Normal raw webpage retrieval separately encountered SSL trust setup failure in bundled Python, then system curl with normal certificate validation returned406/timeout. These are recorded, not bypassed. Web tool text was readable. Downloads headings on current pages exposed no usable PDFs in this bounded review; CAD requested login. No claim that all official PDFs, CAD or nonpublic instructions have been read.',
        'query_scope':['03096-35-03180507 torque/clamping','03096-25-0350 end sleeve','03096-14 installation','03096-35/25/14 official datasheets','03096-35 torque/Drehmoment'],
        'not_performed':['contact supplier','login or account creation','cart or purchase','general torque substitution','other product force-rating substitution','pixel-based dimension inference']}
    dump(OUT/'reviewed-official-evidence.json',reviewed)
    evidence_sha=sha(OUT/'reviewed-official-evidence.json')
    rows=[
        {'field_id':'clamp_torque_for_1p5_wire','part':'03096-35-03180507','requested_value':None,'unit':'N m',
         'status':'NOT_PROVIDED_IN_REVIEWED_ACCESSIBLE_EVIDENCE','needed_definition':'Approved tightening torque/range for this M4 slotted screw, nickel-plated brass body and supplied Ø1.5 stainless core, including lubrication and reuse conditions.',
         'not_a_substitute':'Generic M4 bolt torque is not a cable-clamp torque; it can damage wire/brass and provides no slip-force assurance.'},
        {'field_id':'minimum_free_tail','part':'03096-35-03180507 + Ø1.5 core','requested_value':None,'unit':'mm',
         'status':'NOT_PROVIDED_IN_REVIEWED_ACCESSIBLE_EVIDENCE','needed_definition':'Minimum cable extension beyond the terminal wire-exit surface, with a clearly defined datum and any end treatment.',
         'not_a_substitute':'L7 is nipple axial body length and L1=3.5 locates the transverse hole; neither is wire-tail requirement.'},
        {'field_id':'clamp_retention_force','part':'03096-35-03180507 + Ø1.5 core','requested_value':None,'unit':'N',
         'status':'NOT_PROVIDED_IN_REVIEWED_ACCESSIBLE_EVIDENCE','needed_definition':'Slip/pull-out limit or rated allowable force at stated torque, tail, core construction and load history, including repeat actuation if applicable.',
         'not_a_substitute':'The core material, nominal diameter and hole clearance do not establish clamp retention. Neither M4 thread capacity nor core breaking force alone supplies this rating.'},
        {'field_id':'ferrule_into_adjuster_bearing_depth','part':'03096-25-0350 mated with existing03096-30-0306X24 candidate','requested_value':None,'unit':'mm',
         'status':'NOT_PROVIDED_IN_REVIEWED_ACCESSIBLE_EVIDENCE','needed_definition':'Distance from adjuster inlet face to the actual loaded ferrule reaction datum, including mating nose/cone/chamfers and tolerances.',
         'not_a_substitute':'Ø7 straight-bore depth8.5 belongs to the adjuster, and the CAD shallow-boundary pose is not a measured loaded seat.03096-30 was not newly researched; only existing evidence was reused.'},
        {'field_id':'housing_into_ferrule_final_seat_and_crimp','part':'03096-25-0350 + housing','requested_value':None,'unit':'mm / process',
         'status':'PARTIAL_GEOMETRY_ONLY','known_geometry':{'OD_mm':5.5,'length_mm':11,'housing_bore_mm':5,'straight_bore_depth_mm':9,'wire_bore_mm':2.5,'crimp_zone_offset_mm':4.5},
         'needed_definition':'Final housing insertion/seat datum plus prescribed crimp tool/profile/force and post-crimp dimensions.',
         'not_a_substitute':'L1=9 describes the straight bore; L2=4.5 identifies crimp-zone location, not crimp depth or final compression.'}]
    report={'status':'PARTIAL_SUPPLIER_CLOSURE_SHORTENING_CONFIRMED_FORCE_AND_SEATS_OPEN','created_utc':datetime.now(timezone.utc).isoformat(),
        'scope':'Only three requested cable supplier families. Findings are bounded to accessible official text and the already-saved drawings; no claim of exhaustive official-document absence.',
        'source_sha256':hashes,'web_evidence_file':'output/current-cable-supplier-closure/reviewed-official-evidence.json','web_evidence_sha256':evidence_sha,
        'newly_confirmed':[{'field_id':'shortening_permission','part':'03096-14','status':'OFFICIAL_ASSEMBLY_SHORTENING_PERMISSION',
            'source_url':KIT,'limits':'Does not specify a complete cutter/deburr/liner/crimp procedure, final installed lengths, ferrule seating, clamp torque or minimum tail. Preserve factory-fixed ball end; no inference that arbitrary replacement cable/ends are equivalent.'}],
        'requested_fields':rows,
        'current_candidate_geometric_tail_budget':{'source':'cad/cable-output-interface.scad','wire_diameter_mm':1.5,'tail_below_nipple_center_mm':tail,
            'nominal_tail_outside_body_mm':tail-diameter/2,'interpretation':'CAD installation maximum/space budget only, not a manufacturer minimum or validated holding-force condition.',
            'conditional_gate':'If the supplier-required external tail is larger than this nominal5.5 mm allowance, this exact packaging is incompatible and requires a separately reviewed change. Do not trim below a required tail merely to clear surrounding parts.'},
        'bounded_next_choices':[
            {'choice':'retain_this_candidate','next_evidence':'Obtain an exact-part assembly specification with torque/tail/retention and seat/crimp data, or documented validation on the actual selected hardware/core assembly. No extra printed coupon is required by this report.',
             'current_action':'Keep the force/seat gates open and leave final core trimming until the actual routed and seated assembly is established; do not issue invented setup values.'},
            {'choice':'factory_terminated_rated_cable_assembly','next_evidence':'Use a supplier-defined assembly that specifies terminal geometry, length datums and rated pull/retention performance; review its actual interfaces before substitution.',
             'current_action':'This is an alternative evidence path, not a selected replacement product or permission to change CAD.'}],
        'technical_information_request_fields_not_sent':[
            '03096-35-03180507 with supplied Ø1.5 1.4401 core: permissible tightening range, screw drive dimensions, minimum external tail with drawing datum, slip/rated retention force and repeated-use limits.',
            '03096-25-0350: final housing insertion datum, crimp profile/tool/force and accepted post-crimp dimensions.',
            'Mating03096-25-0350/03096-30-0306X24: dimensioned loaded-seat datum and relevant nose/cone tolerances.',
            '03096-14 exact length SKU: allowed shortening/end-preparation procedure and actual quantities of included ferrules/adjusters/nuts.'],
        'no_physical_release':True,'source_changed':False,'supplier_contacted':False,'purchased':False,'sent_to_printer':False}
    stable=all(sha(ROOT/p)==h for p,h in hashes.items());assert stable
    report['sources_stable']=stable;dump(OUT/'report.json',report)
    text=f'''# 拉索厂家资料的限定复查

本轮只查03096-35-03180507夹头、03096-25-0350端套和03096-14拉索。结论是**裁短许可有官方依据；夹丝扭矩、最短余尾、保持力及实际承力坐深仍未获得数值依据**。没有改CAD、联系厂家、购买或打印。

[03096-14官方页面]({KIT})明确允许安装时缩短拉索，并要求布线后再调节芯套长度；还要求带护套路径始终满足R65、安装时也不能暂时过弯，护套仅承受压缩。这只确认可裁短原则，不等于取得裁切、内管端口和端套压接工艺，也不能给出最终裁切长度。

| 尚缺字段 | 已有证据不能替代它的原因 |
|---|---|
| Ø1.5钢芯对应夹丝扭矩 | M4只是螺纹规格，不能代用通用M4紧固扭矩 |
| 最短外露余尾 | 端头L7、横孔位置L1=3.5均不是钢芯余尾要求 |
| 夹头抗滑/拉脱或允许载荷 | 钢芯材质和孔径不证明夹持能力；还需配套扭矩、尾长及载荷条件 |
| 端套在调节器中的实际承力坐深 | 鼻端、配合锥面与公差不完整，显示位置不是坐实尺寸 |
| 护套插入端套后的止面和压接工艺 | Ø5直孔深9及压接区位置4.5不是最终压入量/压接深度 |

[夹头官方说明]({NIPPLE})和已有原图未给前三项；[端套型号页]({FERRULE})确认标称尺寸及压接区，但没有补出后两项。本轮重新目视检查了保存的三张厂家原图，没有按图片比例猜尺寸。

当前CAD只为余尾提供从端头中心向外8 mm、名义露出本体5.5 mm的空间预算，**不是厂家规定的最短余尾**。若真正需要的余尾大于5.5 mm，不能为了装进去就再剪短，需另行处理接口空间。

访问范围也已记录：官方旧夹头PDF链接返回404；普通文件下载有406和超时，当前页面没有取得可读的新PDF，CAD下载需要登录。因此准确说法是“本轮可访问正文与已保存原图未提供这些数值”，不是断言厂家任何文件都没有。检索仅围绕这三个型号族，没有借用其他产品的扭矩或载荷。

可执行的后续路径有两条：保留现型号，以同一型号的正式装配参数或实际成品五金/钢芯验证补齐；或选择已定义端部尺寸、长度基准和额定保持能力的厂家预制总成，再核对接口。这里没有选新产品，也不要求打印耗材试片。具体应取得的字段已列在[报告]({OUT}/report.json)，尚未向任何人发送。

证据索引：[官方访问记录]({OUT}/reviewed-official-evidence.json)、[原始下载结果]({OUT}/retrieval.json)。脚本仅按已记录证据重建报告并核对本地SHA，不会重新联网或改变设计：

```sh
/Applications/FreeCAD.app/Contents/Resources/bin/python -B output/current-cable-supplier-closure/build_report.py
```
'''
    (OUT/'README.md').write_text(text)
    print(json.dumps({'status':report['status'],'sources_stable':stable,'source_count':len(hashes),'report_sha256':sha(OUT/'report.json'),
        'evidence_sha256':evidence_sha,'readme_sha256':sha(OUT/'README.md')},indent=2))
if __name__=='__main__':main()
