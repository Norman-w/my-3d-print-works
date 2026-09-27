#!/usr/bin/env python3
"""Read-only assembly precedence audit; writes only beside this script. No CAD/mesh/tool reruns."""
import json, hashlib, collections
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
OUT=Path(__file__).resolve().parent

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def load(p): return json.loads((ROOT/p).read_text())
inlet_path='output/current-manufacturing/inlet-process/manifest.json'
inlet=load(inlet_path)
assert inlet['status']=='CURRENT_INLET_PROCESS_BINDING_COMPLETE_WITH_EXPLICIT_LIMITS'
assert not inlet['manufacturing_release'] and not inlet['physical_acceptance']
assert len(inlet['evidence_sha256'])==64
for path,digest in inlet['evidence_sha256'].items():
    assert sha(ROOT/path)==digest, path
evidence={}
def E(path,a,b=None):
    b=b or a; p=ROOT/path; lines=p.read_text().splitlines()
    assert 1<=a<=b<=len(lines),(path,a,b)
    key=f'{path}:{a}-{b}'
    evidence[key]={'path':path,'line_start':a,'line_end':b,'sha256':sha(p),'excerpt':'\n'.join(lines[a-1:b])}
    return key
D='current_source_geometry_inference'; B='existing_current_bounded_path'; H='existing_historical_path_scope'; P='paper_sequence_candidate'
reports={}
def R(key,path,scope):
    data=load(path); sources=data.get('source_sha256',data.get('sources_sha256',{})); mismatches=[]; matches=[]
    for f,h in sources.items():
        p=Path(f);p=p if p.is_absolute() else ROOT/p
        if p.is_file() and sha(p)==h:matches.append(f)
        else:mismatches.append({'path':f,'recorded':h,'current':sha(p) if p.is_file() else None})
    reports[key]={'path':path,'sha256':sha(ROOT/path),'recorded_status':data.get('status'),'source_count':len(sources),'matching_source_count':len(matches),'mismatches':mismatches,'all_recorded_sources_match':bool(sources) and not mismatches,'usable_scope':scope,'rerun_in_this_audit':False}
R('terminal','output/cable-direct-adoption/service/20260927T092327953026Z/report.json','Current input bench stage: main cover removed, u=0 supported, short terminal core only; nine bounded cases and wrong-order positive controls. No full flexible cable extraction or handles.')
R('spin','output/spin-complete-hardware/report.json','Current spin source; selected nut feeds, straight driver budgets and finite wrench poses, including keeper/preload wrong-order controls. Not whole actual-tool/grasp proof.')
R('frame-y','output/feeder-frame-y-guide/report.json','Local frame-Y nut/gib assembly and service. Source matches do not expand its archived baseline33 neighbour composition to current complete cable assembly.')
R('inlet','output/inlet-retention-final/report.json','Nominal inlet/beam local paths and wrong-order controls against archived baseline33. Not whole current input/guide assembly path.')
R('beam-old','output/feeder-support-harness/report.json','Historical only if any recorded source differs. Does not prove shared-long-bolt handling or supported assembly motion.')
R('route-local','output/cable-route-retention/report.json','Local guide candidate with historical source set. Unchanged guide geometry supports reading its assembly features, not current whole-system sweep certification.')
R('route-service-old','output/cable-retention-service/20260927T070337333817Z/report.json','Historical 16-service-envelope composition; changed source dependencies explicitly prevent a current whole-machine clearance claim.')

nodes=[]; edges=[]
def N(id,title,parts=(),note=''):
    nodes.append({'id':id,'title':title,'printed_instances':list(parts),'instruction':note})
def F(x):return 'feeder/'+x
def S(x):return 'spin/'+x
def A(before,after,reason,fail,ev,classification=D,report_refs=()):
    edges.append({'id':f'E{len(edges)+1:02d}','before':before,'after':after,'reason':reason,'failure_if_reversed':fail,'classification':classification,'evidence':ev,'existing_report_refs':list(report_refs)})
# Assignment is ownership of the part in an assembly stage, not permission to ignore earlier loose-nut preloads.
N('F01','核对版本、清理及预装送料隐藏螺母',note='当前 co_beam/co_frame 替换旧件；在各散件封闭前预放侧槽螺母。入口后夹后键朝下工艺已限定数字绑定，真实支撑分离与承面质量仍待正式成品确认，不能把本顺序当制造放行。')
N('F02','壳体定位并合拢',[F('positive-half'),F('negative-half')],'先定位销后八M3；接缝胶仅外侧且固化后继续，不能用厚胶垫改变基准。')
N('F03','预装左右支座',[F('right-support'),F('left-support')],'X导向调整螺母和相关支座捕获螺母先入槽；暂不以过拧消间隙。')
N('F04','四个挡指/销座台面子装配',[F(f'{p}-{side}-{end}') for side in ['right','left'] for end in ['front','rear'] for p in ['finger','pin-block']],'每组M2螺母从+Y装入后再放销座；不要在导轨包住销座后尝试原位抬出。')
N('F05','四挡指径向装入',note='将F04子装配按左右/前后身份装入对应导向，保持可装凸轮框架的状态。')
N('F06','装新 co_frame 及原销钉连接',[F('frame')],'先将新拉线耳两M3螺母从−Y装入；再装框架/肩销及M3。M2微调0.9mm六角工具，不拿1.0mm硬塞。')
N('F07','装两公共框架Y压条及四挡指Y导向',[F(f'{p}-{side}') for side in ['right','left'] for p in ['y-cap','frame-y-gib']]+[F(f'{p}-{side}-{end}') for side in ['right','left'] for end in ['front','rear'] for p in ['y-gib','y-keeper']],'每个公共Y盖先预装两内侧螺母，再装gib，最后盖到支座上；公共盖安装M3×20，不能沿用旧M3×12。两套Y导向功能不同，不能漏装或互换。')
N('F08','装X压条与盖并检查无负载行程',[F('x-gib'),F('x-cover')],'先预装盖/调整螺母；调整时先退顶丝，再均匀取隙，检查全行程，不以拧入圈数当间隙值。')
N('F09','装出口柔衬、PC管及分体捕获夹',[F('liner')]+[F(f'{p}-{s}') for s in ['right','left'] for p in ['capture','pipe-clamp']],'柔衬先于PC管入肩；横M4、管夹、长拉杆螺母按次序就位，夹管前松开拉杆上下螺母，避免压塌1mm管壁。PC管保留可裁余量。')
N('F10','装送料回位弹簧端点',[F('fixed-spacer'),F('moving-spacer')],'肩螺钉先穿外DIN433垫片、弹簧钩、内DIN433、打印定距件、承力垫片；再到支座。不能将Ø7螺钉头硬穿钩眼。固定上端先定位，控制弹簧再接移动端。')
N('C01','台面预装新背梁与入口后夹',[F('beam-grip'),F('inlet-rear'),F('inlet-backplate')],'新桥已与背梁一体；后夹M4螺母先入，双端键从梁+Y就位，背板从−Y，先完成M2.5紧固。背梁此时未固定主机，需支承。')
N('C02','护套未入时装导向主座与下托',[F('cable-route-base'),F('cable-route-lower')],'预放六盖螺母和四下托螺母；主座从+Z向下落，下托从后方+Y进入后升+Z8。螺钉闭合夹具自身止面，原平台留名义0.6mm笼隙，不继续拧压平台。')
N('C03','台面输入座预装隐藏螺母/止挡/调节器',[F('cable-input-body')],'先背面盖螺母、止挡捕获螺母和轴系背面螺母；M6螺母/垫片及SW8、SW10工具操作在主盖未装时完成。δ限定±2，先设较小止挡。')
N('C04','输入定距轴、推力片、轴套与扳机',[F('cable-input-lever')],'先预放扳机两端球盖螺母，再装定距管/两推力片/轴套。主轴夹紧的是金属定距管，确认旋转件未夹死。预放端球盖螺母是防散落顺序，不宣称装轴后必无任何入口。')
N('C05','裸线尾贯穿整个线管链',note='Ø5球头留在输入端，以Ø1.5未剪裸尾依次穿输入调节器/端套、护套、输出端套/调节器和Ø1.8夹头横孔。临时护套端部不锁死；允许台面穿线后再把球端坐入。完整柔性穿线/抓持属纸面候选。')
N('C06','球头入座并装端球盖',[F('cable-input-terminal-cap')],'u=0支承扳机，球头从局部+Z入座；两M3×8紧固独立端球盖，留意背面螺母散落。')
N('C07','输入主盖完成',[F('cable-input-cover')],'确认定距轴/推力片/轴套、端球盖、M6与止挡都已处理后再装主盖、轴螺钉和两盖M3；主盖内侧随后靠近背梁，不按原位拆盖设计。')
N('C08','两总成受托后完成共享四M4×60',note='同时承托输入模块与背梁/入口夹/导向总成，键对准后以四M4×60和新垫片完成共享主连接。旧四M4×20和旧垫片不叠装，原壳体M4螺母保留。')
N('C09','装入口软管、柔衬及前夹',[F('inlet-front')],'后夹M2.5已经完成；软管套PC短管，装柔衬与前夹。背带走新增外侧槽，不能占后夹双键/M2.5位置，也不把两层硬塞3mm槽。')
N('C10','护套侧放入导向并合盖',[F('cable-route-cap')],'两端端套暂不坐死，从+N整条敞槽侧放入护套，再合六M3弧盖，最后端套自然坐实并检查自由弯；不得把粗端套穿ID6.2闭孔或拉伸护套迁就长度。')
N('C11','输出端开放定位、标记并裁尾',note='护套/端套完整坐实后确定线芯长度；夹头、cap及M4垫圈保持开放，先按耳的零位基准标记，在+Y可接近侧处理尾长，再进入最终夹持。不得让未剪长尾坐进耳内带动滑架。完整柔性穿线/标记/抓持转移无独立数字路径，不以图上路由长直接下剪。')
N('C12','输出夹头合盖并复核零位/止挡',[F('cable-output-cap')],'受限尾长的夹头+线从+Y入耳，cap/金属垫圈移开时以实际一字起子夹紧，再金属M4保持垫圈、两M3×16合盖。无球无风复核释放零位与输出终点前的止挡；M6变δ或重坐护套后必须重查。尾端中心下≤8mm是最大名义包络，非厂家最低余尾；不能盲设20mm。')
N('S01','旋转头散件预放捕获螺母',note='壳体盖/导块螺母、载体拉杆螺母(+Z)和压条螺母(±Y)、盖保持叉螺母(+Z)、笼螺母先入槽；保持叉螺母工作档也留在盖里。')
N('S02','载体在壳外装TPU垫和压条',[S('carriage'),S('pad'),S('pad-keeper')],'先放拉杆螺母，再TPU垫沿−Z入燕尾、沉头压条固定。压条工具仅在载体拆出状态获独立入口证据。pad按指定TPU，不混列为PETG。')
N('S03','装旋转主体和对侧导块',[S('body'),S('opposite-guide')],'导块从−X装入，以M3×10及垫片固定；主体装原出球PC管，实际三通/风机姿态与管裁长未被本报告补齐。')
N('S04','外盖先装预压M4螺母、弹簧座和笼',[S('cover'),S('spring-cage'),S('spring-seat')],'预压M4螺母先由+Y侧槽入位；弹簧座由笼+X开口装入，再把笼固定于外盖。笼螺钉之后会挡M4螺母路径，外盖关闭弹簧座另一端。')
N('S05','装载体、弹簧及外盖',note='载体沿+X装入主体，弹簧两端定位柱就位并受控，再从+X装盖并均匀紧固四M3；最小预压也不能假定无弹簧力。')
N('S06','装预压螺钉及拉帽',[S('pull-cap')],'装手拧预压螺钉/外锁母，M3×45从+X穿拉帽连接载体预置螺母。拉帽Ø12过不了盖孔Ø6.5，所以维修必须先拆拉帽。')
N('S07','保持叉作为可选停放件',[S('hold-fork')],'正常工作不装叉及其M3×16/垫片；保持档停风清空，拉到5.25mm硬止挡后下放叉固定，再轻放到5mm保持。先拉住卸载才能拆叉。不要重复添加已在盖内的同一保持叉螺母。')

A('F01','F02','壳体捕获螺母/定位销在合壳前处理','合壳后部分侧入口被邻件占用，不能靠总装渲染证明塞入',[E('docs/final-assembly.md',68,69)],P)
A('F02','F03','支座以已合拢壳体为基准','散件松旷状态会改变导向基准',[E('docs/final-assembly.md',68,71)],P)
A('F01','F04','M2螺母入口被销座包住','先装销座会堵螺母入口',[E('docs/feeder-pin-seat-revision.md',28,32),E('cad/feeder-pin-seat-revision.scad',75,88)])
A('F04','F05','销座和螺母在载体外完成','导轨限制销座沿+Y取放',[E('docs/feeder-pin-seat-revision.md',28,32)])
A('F03','F05','径向载体须进入支座导向','不能在导向未固定时完成受控位置关系',[E('docs/final-assembly.md',70,71)],P)
A('F05','F06','先装载体再框架和肩销','框架/肩销阻挡原位销座维护',[E('docs/feeder-pin-seat-revision.md',28,32),E('cad/feeder-pin-seat-revision.scad',104,122)])
A('F01','F06','新耳螺母从−Y预装','成组后背面邻件/抓持未另验证',[E('docs/cable-output-interface.md',30,32),E('cad/cable-output-interface.scad',118,137)])
A('F06','F07','公共Y盖先内侧螺母、再gib、最后装盖','gib先入会占螺母路径；装盖后gib不能从被主机封闭的−Y入口装入',[E('docs/feeder-frame-y-guide.md',40,43),E('cad/feeder-frame-y-guide.scad',83,105)],B,['frame-y'])
A('F07','F08','Y结构与X压条共同限制框架','提前以X强行压紧可能掩盖Y不齐；调节需退顶丝',[E('docs/final-assembly.md',71)],P)
A('F02','F09','出口基准来自合拢主壳','松壳状态不能确认管与肩就座',[E('docs/final-assembly.md',72)],P)
A('F09','C08','出口夹和下部拉杆先于背梁主装','背梁会妨碍部分夹具/拉杆工具；不把历史局部工具路径升级为当前全机',[E('docs/final-assembly.md',72,74)],H,['beam-old'])
A('F08','F10','先完成可滑动导向再接回位弹簧','弹簧力会掩盖卡滞并增加销/框装配负载',[E('docs/feeder-return-spring.md',63,67)],P)
A('F10','C08','在共享梁总成安装前完成弹簧端点叠层','Ø7头不能穿钩；背梁在位不应假定深套筒/抓持仍可达',[E('docs/final-assembly.md',73),E('docs/feeder-return-spring.md',63,67)],P)
A('F01','C01','入口后夹预置M4螺母且台面键/背板M2.5先完成','背梁装机后不能从后面加背板；软管先上会挡M2.5螺母进路',[E('docs/inlet-retention-final.md',57,63),E('docs/inlet-retention-final.md',79,82)],B,['inlet'])
A('C01','C02','导向座从+Z落在新梁一体输出平台','先上护套/盖/下托不能使用已记录的空平台落座路径',[E('docs/cable-route-retention.md',39,44),E('cad/cable-route-retention.scad',132,148)],H,['route-local'])
A('C01','C08','背梁后夹M2.5须台面完成','主机阻挡背板作业；旧四短M4不能先永久固定再叠新长M4',[E('docs/cable-trigger-input.md',52),E('docs/inlet-retention-final.md',79,82)])
A('C03','C04','后侧螺母、止挡及轴栈按开放台面安装','主盖/梁安装后后侧螺母与M6工具入口受限',[E('cad/cable-trigger-input.scad',207,228),E('docs/cable-trigger-input.md',51)])
A('C04','C05','球端与未截线尾须在可访问台面整理','截短或毛刺尾无法保证顺利穿整个已选路线',[E('cad/cable-trigger-input.scad',331,343),E('docs/cable-output-interface.md',31)],P)
A('C05','C06','裸尾先穿细孔，球头留输入端','Ø5球头不能穿Ø3调节器和Ø2.5端套；已锁死两端后不能把球端硬穿过去',[E('cad/cable-trigger-input.scad',331,349),E('docs/cable-output-interface.md',22)],P)
A('C06','C07','独立端球盖及螺钉须主盖移开后操作','主盖在位的工具/螺钉/小盖路径均有碰撞阳性；端球盖在位阻球头取出',[E('output/cable-direct-adoption/service/README.md',13,35),E('cad/cable-trigger-input.scad',262,294)],B,['terminal'])
A('C03','C07','M6薄母锁紧与止挡预设在主盖之前','主盖闭合后不能据台面SW10预算称可调；变δ须重新开盖/放松线管并重定零位',[E('docs/cable-trigger-input.md',41,47),E('docs/cable-service-contract.md',25,27)])
A('C07','C08','输入模块先台面合盖再与背梁共享固定','主盖打开方向局部+Z=CAD+Y在梁侧；装机后不能原位硬拔盖',[E('docs/cable-trigger-input.md',51,54),E('docs/cable-service-contract.md',14,17)])
A('C02','C08','先在受托梁总成上安排导向笼','本顺序选取台面可接近阶段；不是证明其他顺序都不可行',[E('docs/cable-route-retention.md',39,40)],P)
A('C08','C09','共享主固定完成后合入口前夹','软管不能先遮住后夹M2.5作业；前夹应按自身入口就位，不强迫错孔',[E('docs/inlet-retention-final.md',79,82)],B,['inlet'])
A('C05','C10','自由端护套才能从敞槽侧放入','两端锁死强掰147°弧或拉伸护套不可取；粗端套不能穿闭合孔',[E('docs/cable-route-retention.md',41,43)],P)
A('C02','C10','下托/主座先完成，护套后入','先入护套会挡主座安装路径和螺母照料',[E('docs/cable-route-retention.md',39,42),E('cad/cable-route-retention.scad',82,87)],H,['route-local'])
A('C08','C10','位置确定后自然布线并锁导向盖','在浮动总成间先锁线管会把定位误差当成护套拉力',[E('docs/cable-trigger-input.md',52),E('docs/cable-route-retention.md',41,42)],P)
A('C10','C11','端套坐实后才确定线芯有效长度/输出夹紧','路线与端座改变绝对长度；先夹死无法同时保证释放零位和行程',[E('docs/cable-trigger-input.md',43,47),E('docs/cable-output-interface.md',31,34)],P)
A('C11','C12','先按完整路线标记并限制尾包络，再装入耳/闭盖和运动复核','过早按图裁短会无法重新夹持；但保留未剪长尾到闭盖后才裁也不行：中心下15mm尾已撞Y导向盖，不能带长尾全程调试',[E('docs/cable-output-interface.md',31,32),E('docs/cable-output-interface.md',65,67),E('docs/cable-route-retention.md',42),E('docs/cable-service-contract.md',12)],P)
A('C09','C12','软管/自由护套最终形态纳入零位复查','外部牵引变化可能改摩擦与释放位置',[E('docs/cable-trigger-input.md',52,54)],P)
A('S01','S02','拉杆螺母+Z先于TPU垫/压条','不能改从±Y穿过已装两颗压条螺钉；载体在壳内压条工具撞壳',[E('docs/spin-complete-hardware.md',33,34),E('cad/spin-complete-hardware.scad',98,100)],B,['spin'])
A('S01','S03','主体/导块捕获螺母先于封闭件','侧槽螺母应先放，不能后靠薄工具强塞',[E('docs/spin-complete-hardware.md',33),E('cad/spin-complete-hardware.scad',91,97)],B,['spin'])
A('S01','S04','预压M4先于笼和其M3；弹簧座先于笼封口','靠+Y笼M3挡预压螺母装入路径；装笼到盖后另一端封闭',[E('docs/spin-head.md',80),E('cad/spin-head.scad',149,192)],B,['spin'])
A('S02','S05','TPU压条在载体壳外完成','已装机载体的压条工具路径有明确碰撞',[E('docs/spin-complete-hardware.md',34,40)],B,['spin'])
A('S03','S05','主体与导块先作为装载体基准','未形成主体导向时无法定义受控弹簧装配',[E('docs/spin-head.md',80)],P)
A('S04','S05','盖笼座成为可控子组件后装弹簧闭盖','必须控制预压，不能当作无力散件盖上',[E('docs/spin-head.md',80,84)],P)
A('S05','S06','先闭外盖后装拉帽','拉帽Ø12大于导孔Ø6.5，不能带帽穿盖',[E('docs/spin-head.md',80,84)])
A('S06','S07','先装拉帽再允许保持档','没有拉帽无法按定义先拉住卸载叉；正常工作不安装叉及其螺栓',[E('docs/spin-complete-hardware.md',36,38),E('docs/spin-head.md',82)])

# Independent maintenance chain. These are NOT reverse edges in the assembly DAG.
maintenance=[
{'id':'M01','after':[],'action':'无球无风，支承输出滑架/输入及梁总成；打开输出盖、拿住松散金属保持垫圈，再松夹线紧定螺钉。','evidence':[E('docs/cable-service-contract.md',9,11)],'classification':D},
{'id':'M02','after':['M01'],'action':'尾线沿+Z退出封闭Ø1.8横孔后，夹头才可沿+Y拿出。8mm中心下尾需>10.5mm抽线；松夹后u/t解耦，不能把维修仍约束u=20t。','evidence':[E('docs/cable-service-contract.md',12)],'classification':P},
{'id':'M03','after':['M02'],'action':'输出端套拔出，开中段盖侧取护套，解除软管/护套拖拽，托住输入模块以及背梁/入口夹/输出导向总成。','evidence':[E('docs/cable-service-contract.md',13,14)],'classification':P},
{'id':'M04','after':['M03'],'action':'卸四共享M4×60。它们也是背梁主固定，不假定梁仍固定；受托状态相对梁退CAD−Y至少先退出键，再移台面。','evidence':[E('cad/cable-trigger-system.scad',22,28),E('cad/cable-trigger-input.scad',297,301),E('docs/cable-service-contract.md',14)],'classification':D},
{'id':'M05','after':['M04'],'action':'台面移除主轴和两盖M3，主盖沿局部+Z=CAD+Y取下。','evidence':[E('docs/cable-service-contract.md',15)],'classification':D},
{'id':'M06','after':['M05'],'action':'支承零位扳机/松散螺母，拆端球盖两M3，小盖+Z取下再取球头。当前数字证据只含短芯段，不含整条柔线搬出。','evidence':[E('output/cable-direct-adoption/service/README.md',5,17),E('output/cable-direct-adoption/service/README.md',43)],'classification':B,'report_refs':['terminal']},
{'id':'M07','after':['M03'],'action':'若拆中段夹具：取护套、松四平台螺钉并托下托；下托−Z8后−Y100，最后主座+Z。不能直接向下70。','evidence':[E('docs/cable-route-retention.md',44)],'classification':H,'report_refs':['route-local','route-service-old']},
{'id':'MS01','after':[],'action':'旋转头先拉住卸载保持叉，拆叉螺栓/垫片/叉；盖内同一螺母保留。','evidence':[E('docs/spin-head.md',82,84)],'classification':D},
{'id':'MS02','after':['MS01'],'action':'先拆拉帽M3×45和Ø12拉帽；再最小预压但仍控制弹簧力，松四盖M3，盖+X至少20后再移开，最后抽载体以拆TPU压条。','evidence':[E('docs/spin-head.md',84),E('docs/spin-complete-hardware.md',38,40)],'classification':B,'report_refs':['spin']}
]

inventory=load('docs/cable-assembly-inventory.json')
printed=[p['id'] for p in inventory['parts'] if p['role']=='printed']
assigned=[p for n in nodes for p in n['printed_instances']]
assert len(printed)==56 and len(set(assigned))==len(assigned)==56
assert set(assigned)==set(printed),(set(printed)-set(assigned),set(assigned)-set(printed))
node_ids={n['id'] for n in nodes}; indegree={n['id']:0 for n in nodes}; successors=collections.defaultdict(list)
for e in edges:
    assert e['before'] in node_ids and e['after'] in node_ids
    indegree[e['after']]+=1;successors[e['before']].append(e['after'])
queue=[n['id'] for n in nodes if indegree[n['id']]==0]; order=[]
while queue:
    x=queue.pop(0);order.append(x)
    for y in successors[x]:
        indegree[y]-=1
        if indegree[y]==0:queue.append(y)
assert len(order)==len(nodes),'Assembly dependency cycle'

open_items=[
{'id':'U01','subject':'入口后夹真实制造质量','status':'physical_process_quality_unverified','detail':'后键朝下第三候选已限定数字绑定：四键首层、完整名义五金体积、锚板/肩台先后路径和整树接触来源已有自身证据。原严格失败及边界接触保留；退出方向为脱床分离接触后沿−CAD Y。真实分离力、抓持、桥接质量、残屑及承面尺寸尚未证明。','evidence_file':inlet_path},
{'id':'U02','subject':'全机实际工具/抓持','status':'unproved','detail':'未新增任何 CAD、扫掠、切片或实际工具测试；圆杆/有限薄扳手姿态不认证手柄、手指抓持、扭矩、碎料清除或所有角度。'},
{'id':'U03','subject':'共享长栓拆装时的支承','status':'paper_sequence_candidate','detail':'确认四长栓共同固定输入与背梁；移除后的重物/软管牵引必须由外部支承承担。支承夹具和两总成受托搬动的完整路径未设计/模拟。'},
{'id':'U04','subject':'整条成品拉索穿装/端套座深/裁长','status':'unproved','detail':'裸芯先穿顺序由真实孔径决定，但整条柔线穿过、未知端套实际锥面座深、实际夹线槽/起子、供应商最短安全尾长和扭矩仍未闭合；不按746.507mm路线长裁线。'},
{'id':'U09','subject':'长尾标记到受限尾长装入的顺序','status':'paper_sequence_candidate','detail':'旧15mm尾在零位撞Y盖，当前≤8mm包络；不能理解为先带未剪长尾装好并跑完全行程再剪。完整坐实端套后标记、在开放侧处理尾长、再夹头入耳/合盖/零位复核是候选。端套真实坐深、抓持和长度转移没有完整路径或实物证据；不把8mm最大值当供应商夹线最小余长。'},
{'id':'U05','subject':'预压/止挡/释放零位','status':'assembly_adjustment_required','detail':'20mm为工作范围上限，M6±2调整改变绝对长度。固定线芯后须重新检查零位/终点，不把名义20mm或数字几何通过当作实际有效送料、风力、单球释放与回位通过。'},
{'id':'U06','subject':'护套导向安装的全机当前通道','status':'historical_scope_only','detail':'当前guide自身的可拆结构清楚，但本次引用的route-local和route-service旧报告含变更输入/路由源，不能升级为当前全机全部路径的独立新通过；在台面受托梁上预装是本顺序的保守候选。'},
{'id':'U07','subject':'原三通/风机/PC管最终接口','status':'not_modeled_or_not_measured','detail':'原风机、斜三通插入深度、外部握持与软管实际路由未由现有名义PC参考补齐；PC裁长与旋转头在原出球管上的最终方向保留待实际布局。'},
{'id':'U08','subject':'打印捕获螺母和松散垫圈','status':'manual_retention_required','detail':'侧槽限制转动不保证摩擦自锁；端球盖背面螺母、输出金属保持垫圈、导向笼螺母拆装须拿住，实际手指/镊子抓持未认证。'},
]
source_files=sorted({v['path'] for v in evidence.values()}|{'docs/cable-assembly-inventory.json','cad/cable-scene-export.scad','docs/cable-trigger-integration.md',inlet_path})
source_hashes={p:sha(ROOT/p) for p in source_files}
report={
'schema':'current-assembly-sequence-review-v1',
'review_script_sha256':sha(Path(__file__).resolve()),
'status':'ASSEMBLY_PRECEDENCE_REVIEW_COMPLETE_WITH_EXPLICIT_GAPS',
'scope':'Read-only source/evidence audit. No new CAD export, tool collision test, slicing, print or physical assembly. Acyclic sequence is a planning consistency check, not physical clearance proof.',
'inventory':{'path':'docs/cable-assembly-inventory.json','sha256':sha(ROOT/'docs/cable-assembly-inventory.json'),'printed_count':len(printed),'feeder_count':sum(x.startswith('feeder/') for x in printed),'spin_count':sum(x.startswith('spin/') for x in printed),'baseline38_retained_instance_ids':sum(x.startswith('feeder/') and not x.startswith('feeder/cable-') for x in printed),'replacements':['feeder/beam-grip -> co_beam','feeder/frame -> co_frame'],'added8':[x for x in printed if x.startswith('feeder/cable-')],'normal_work_printed_installed_count':55,'optional_parked_printed':['spin/hold-fork'],'note':'56 is package instance count; normal spin work mode excludes the hold fork. 38 - 2 + 2 + 8 = 46 feeder; 46 + 10 = 56.'},
'duplicate_prevention':[
{'item':'beam-grip/frame','rule':'co_beam/co_frame replace corresponding old printed instances; co_fixed_bridge already included in co_beam, no separate bridge layer.','evidence':[E('docs/cable-output-interface.md',10,14),E('cad/cable-scene-export.scad',60,71)]},
{'item':'shared 4 M4 fasteners','rule':'4 M4×60 and new washers replace old sh_bolts 4 M4×20 + old washers; old nuts retained once.','evidence':[E('cad/cable-trigger-system.scad',22,28),E('cad/cable-trigger-input.scad',297,301)]},
{'item':'frame Y guide','rule':'Current two supports/caps replace old pair; two frame gibs are additions. Current cap mounting M3×20 replaces old M3×12; four carrier Y guide systems remain separate.','evidence':[E('docs/feeder-frame-y-guide.md',60)]},
{'item':'spin hold hardware','rule':'Working hardware already retains the latch nut; add only fork and M3×16/washer for hold. Do not duplicate latch nut.','evidence':[E('docs/spin-complete-hardware.md',36,44),E('cad/cable-scene-export.scad',72,88)]}
],
'classification_legend':{D:'Actual current source openings/stack read; no new motion/path test.',B:'Existing bounded test report and current recorded source identities verified; only its stated stage/composition/primitive tested.',H:'Historical path report; changed dependencies or earlier assembly composition prevents blanket current whole-assembly claim.',P:'Practical sequencing proposal/inference; no digital proof of the complete operation.'},
'nodes':nodes,'dependency_edges':edges,'assembly_topological_order':order,'maintenance_nodes':maintenance,
'checks':{'all56_printed_instances_assigned_exactly_once':True,'assembly_graph_acyclic':True,'new_geometry_checks_run':False,'new_tool_checks_run':False,'manufacturing_release':False,'physical_acceptance':False},
'existing_reports':reports,'unproved_items':open_items,'evidence':evidence,
'source_sha256':source_hashes,
}
# Evidence additions above are captured in final hash set (including duplicate rules).
report['source_sha256']={p:sha(ROOT/p) for p in sorted(set(source_files)|{v['path'] for v in evidence.values()})}
report['source_sha256_at_end']={p:sha(ROOT/p) for p in report['source_sha256']}
report['sources_stable']=report['source_sha256']==report['source_sha256_at_end']
assert report['sources_stable']
(OUT/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({'output':str(OUT/'report.json'),'sha256':sha(OUT/'report.json'),'nodes':len(nodes),'edges':len(edges),'printed':len(assigned),'reports':{k:{'match':v['matching_source_count'],'total':v['source_count'],'mismatch':len(v['mismatches'])} for k,v in reports.items()}},ensure_ascii=False,indent=2))
