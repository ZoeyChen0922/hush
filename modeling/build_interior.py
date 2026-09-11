"""Hush inn interior. Run with Blender 4.5 --background --python this_file.
Coordinates: X across room, Y toward back wall, Z up. Entrance behind camera.
"""
import bpy, math, random, os
from mathutils import Vector
random.seed(23)
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT=os.path.join(ROOT,'assets','models'); os.makedirs(OUT,exist_ok=True)
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=False)
# Packed image textures survive GLB export; procedural shader-only textures do not.
def grain_image():
    w,h=512,256; im=bpy.data.images.new('Walnut • hand finished grain',width=w,height=h)
    px=[]
    for y in range(h):
        for x in range(w):
            u=x/w; v=y/h
            warp=v*110+1.7*math.sin(u*7+v*13)+.7*math.sin(u*19+v*12)
            g=.87+.055*math.sin(warp)+.035*math.sin(warp*3.2)+.025*math.sin(warp*9)+random.random()*.04
            px.extend((g,g,g,1))
    im.pixels=px; im.pack(); return im
tex=grain_image()
def mat(name,c,rough=.6,metal=0,wood=False,emission=0):
    m=bpy.data.materials.new(name); m.diffuse_color=(*c,1); m.use_nodes=True
    bs=m.node_tree.nodes.get('Principled BSDF'); bs.inputs['Base Color'].default_value=(*c,1); bs.inputs['Roughness'].default_value=rough; bs.inputs['Metallic'].default_value=metal
    if wood:
        # Texture tint is stored in image pixels for interoperable glTF materials.
        im=tex.copy(); im.name=name+' grain'; pix=list(tex.pixels)
        for i in range(0,len(pix),4):
            for j in range(3): pix[i+j]*=c[j]**.82
        im.pixels=pix; im.pack()
        n=m.node_tree.nodes.new('ShaderNodeTexImage'); n.image=im; m.node_tree.links.new(n.outputs['Color'],bs.inputs['Base Color'])
    if emission:
        bs.inputs['Emission Color'].default_value=(*c,1); bs.inputs['Emission Strength'].default_value=emission
    return m
wood=mat('01 • warm walnut',(.24,.095,.034),wood=True)
oak=mat('02 • honey oak',(.39,.19,.074),wood=True)
darkwood=mat('03 • aged edges',(.12,.042,.017),wood=True)
floors=[mat('Floor %02d'%i,(.24+i*.013,.103+i*.006,.042+i*.003),wood=True) for i in range(5)]
plaster=mat('Warm lime plaster',(.64,.49,.31),.94)
stone=[mat('Basalt %d'%i,(.105+i*.012,.108+i*.011,.10+i*.01),.95) for i in range(4)]
black=mat('Recess and ink',(.028,.018,.011),.9)
paper=mat('Ivory paper',(.77,.65,.43),.9)
paperedge=mat('Page edges',(.5,.38,.23),.88)
leather=mat('Oxblood leather',(.13,.044,.025),.82)
brass=mat('Antique brass',(.48,.28,.078),.3,.72)
iron=mat('Blackened iron',(.09,.085,.067),.46,.68)
wax=mat('Beeswax',(.82,.62,.31),.5)
glow=mat('Amber light', (1,.54,.14),.4,emission=2.4)
flame=mat('Candle flame',(1,.72,.3),.35,emission=5)
ceramic=mat('Cream glazed stoneware',(.59,.47,.3),.24)
terracotta=mat('Terracotta',(.31,.115,.045),.77)
leaves=[mat('Leaf %d'%i,(.09+i*.018,.16+i*.022,.035+i*.005),.72) for i in range(3)]
blue=mat('Rain glass',(.08,.23,.22),.2,.18)
water=mat('Still water',(.045,.13,.14),.2,.25)
red=mat('Sealing wax',(.36,.065,.027),.48)
cloth=mat('Woven welcome mat',(.135,.082,.044),1)
# All geometry has true softened edges, including small furniture details.
def finish(o,name,ma,bevel=0):
    o.name=name; o.data.materials.append(ma)
    if bevel:
        mod=o.modifiers.new('Soft worn edges','BEVEL'); mod.width=bevel; mod.segments=3
        mod=o.modifiers.new('Weighted corner normals','WEIGHTED_NORMAL')
    return o
def box(name,loc,size,ma=wood,b=.018,rot=0):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc); o=bpy.context.object; o.dimensions=size
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True); o.rotation_euler.z=rot
    return finish(o,name,ma,b)
def cyl(name,loc,r,depth,ma,verts=32,rotation=None):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts,radius=r,depth=depth,location=loc,rotation=rotation or (0,0,0)); return finish(bpy.context.object,name,ma,.008)
def sphere(name,loc,scale,ma):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20,ring_count=12,location=loc); o=bpy.context.object; o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    for p in o.data.polygons:p.use_smooth=True
    return finish(o,name,ma)
def torus(name,loc,major,minor,ma,rot=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_segments=32,minor_segments=8,location=loc,major_radius=major,minor_radius=minor,rotation=rot); return finish(bpy.context.object,name,ma)
def beam(name,a,b,width,depth=None,ma=wood):
    mid=(Vector(a)+Vector(b))*.5; d=Vector(b)-Vector(a); o=box(name,mid,(width,depth or width,d.length),ma,.014); o.rotation_euler=d.to_track_quat('Z','Y').to_euler(); return o
def curve(name,points,r,ma):
    cv=bpy.data.curves.new(name,'CURVE');cv.dimensions='3D';cv.resolution_u=1;cv.bevel_depth=r;cv.bevel_resolution=2
    sp=cv.splines.new('POLY');sp.points.add(len(points)-1)
    for p,co in zip(sp.points,points):p.co=(*co,1)
    o=bpy.data.objects.new(name,cv);bpy.context.collection.objects.link(o);o.data.materials.append(ma);return o
def text(name,body,loc,size,ma,rot=(math.pi/2,0,0)):
    cv=bpy.data.curves.new(name,'FONT');cv.body=body;cv.size=size;cv.align_x='CENTER';cv.extrude=.0005
    o=bpy.data.objects.new(name,cv);bpy.context.collection.objects.link(o);o.location=loc;o.rotation_euler=rot;o.data.materials.append(ma);return o
# Room shell, with open front for entry camera and editable diorama inspection.
box('Foundation',(0,0,-.15),(5.7,7,.25),stone[1])
for i in range(17):
    x=-2.64+i*.33
    for j in range(4):
        y=-3.1+j*1.72+(i%2)*.18
        box('Individual oak floorboard',(x,y,.006),(.321,1.705,.09),random.choice(floors),.008)
box('Back lime wall',(0,3.15,1.85),(5.65,.18,3.7),plaster)
# Left window opening, not a luminous rectangle laid over a solid wall.
for loc,sz in [((-2.77,0,.66),(.18,6.4,1.32)),((-2.77,0,3.25),(.18,6.4,.9)),((-2.77,-1.88,2.04),(.18,2.64,1.45)),((-2.77,2.22,2.04),(.18,1.85,1.45))]: box('Left plaster around window',loc,sz,plaster)
box('Right side plaster',(2.77,.2,1.85),(.18,6.1,3.7),plaster)
for row in range(3):
    for col in range(10):
        x=-2.52+col*.56
        box('Back stone dado',(x+(row%2)*.12,3.015,.16+row*.22),(.545,.1,.207),random.choice(stone),.012)
    for side in (-1,1):
        for col in range(12):box('Side stone dado',(side*2.655,-3.03+col*.52,.16+row*.22),(.1,.505,.207),random.choice(stone),.012)
for x in [-2.62,-.55,2.62]:box('Rear upright',(x,2.96,1.86),(.19,.24,3.75),wood)
for z in [.09,.76,3.5]:
    box('Rear continuous beam',(0,2.96,z),(5.5,.24,.18),wood)
    for x in [-2.62,2.62]:box('Side horizontal timber',(x,-.1,z),(.24,6.3,.18),wood)
for x in [-2.62,2.62]:
    for y in [-3.05,-1.3,1.55]:box('Side post',(x,y,1.84),(.23,.18,3.7),wood)
for a,b in [((-2.5,2.91,2.62),(-1.91,2.91,3.45)),((1.96,2.91,3.44),(2.53,2.91,2.58))]:beam('Diagonal brace',a,b,.17,.14)
beam('Left diagonal brace',(-2.59,1.7,2.42),(-2.59,2.5,3.43),.15)
# Closed ceiling for immersive doorway view; rafters lead toward reception.
box('Plaster ceiling',(0,-.1,3.84),(5.65,6.65,.14),plaster)
for y in [-2.7,-1.15,.4,1.95]:box('Ceiling oak rafter',(0,y,3.67),(5.56,.16,.25),wood)
# Deep, cross-mullioned window on left.
box('Evening glowing window',(-2.80,.25,2.12),(.045,1.65,1.48),glow,.004)
for y in [-.65,1.15]:box('Window side casing',(-2.57,y,2.12),(.24,.13,1.8),oak)
for z in [1.29,2.94]:box('Window lintel and sill',(-2.54,.25,z),(.32,1.98,.14),oak)
box('Broad window ledge',(-2.43,.25,1.31),(.53,1.99,.12),oak)
box('Window vertical mullion',(-2.59,.25,2.12),(.12,.068,1.57),wood,.006)
box('Window cross mullion',(-2.59,.25,2.12),(.12,1.67,.068),wood,.006)
# Pigeonholes and folded envelopes.
box('Mail cabinet back',(-.65,2.84,2.17),(1.74,.15,1.55),darkwood)
for z in [1.37,2.96]:box('Cabinet crown / base',(-.65,2.61,z),(1.92,.62,.13),oak)
for i in range(5):box('Mail divider',(-1.5+i*.425,2.61,2.16),(.065,.51,1.52),wood,.009)
for i in range(1,4):box('Mail shelf',(-.65,2.61,1.37+i*.397),(1.77,.53,.055),wood,.008)
for row in range(4):
    for col in range(4):
        if random.random()<.25:continue
        x=-1.28+col*.425; z=1.45+row*.397
        for n in range(random.randint(1,3)):box('Folded correspondence',(x,2.53,z+n*.019),(.28,.26,.014),paper,.003,random.uniform(-.13,.13))
# Shelf with sun card, jar, and candle.
box('Curiosity shelf',(1.5,2.67,2.21),(1.62,.60,.105),oak)
for x in [.86,2.12]:beam('Shelf bracket',(x,2.92,1.94),(x,2.54,2.16),.09,ma=wood)
box('Sun card border',(1.03,2.55,2.58),(.32,.055,.55),brass,.015)
box('Sun card face',(1.03,2.514,2.59),(.286,.017,.507),water,.007)
sphere('Sun emblem',(1.03,2.498,2.64),(.072,.009,.072),brass)
for i in range(12):
    a=i*math.tau/12;beam('Sun ray',(1.03+math.sin(a)*.09,2.495,2.64+math.cos(a)*.09),(1.03+math.sin(a)*.127,2.495,2.64+math.cos(a)*.127),.01,ma=brass)
text('Tarot caption','THE SUN',(1.03,2.491,2.40),.035,paper)
cyl('Rain jar',(1.49,2.56,2.43),.125,.31,blue)
torus('Jar rim',(1.49,2.56,2.59),.125,.015,blue)
cyl('Cork',(1.49,2.56,2.62),.115,.055,oak)
cyl('Water in jar',(1.49,2.56,2.38),.129,.12,water)
# Candle and melted wax drips.
def candle(x,y,z,s=1):
    cyl('Candle saucer',(x,y,z+.018),.14*s,.036*s,brass)
    torus('Saucer rolled edge',(x,y,z+.039),.132*s,.012*s,brass)
    cyl('Candle wax',(x,y,z+.18*s),.069*s,.29*s,wax)
    for i in range(6):
        a=i*math.tau/6; sphere('Melted wax drip',(x+math.sin(a)*.061*s,y+math.cos(a)*.061*s,z+.26*s),(.013*s,.014*s,random.uniform(.025,.085)*s),wax)
    cyl('Wick',(x,y,z+.34*s),.006,.04,black,12)
    sphere('Flame',(x,y,z+.397*s),(.027*s,.023*s,.075*s),flame)
candle(1.98,2.53,2.265)
# Hanging room key beneath shelf, with bow, shaft and teeth.
torus('Key bow',(1.56,2.91,1.88),.065,.019,brass,(math.pi/2,0,0))
beam('Key shaft',(1.56,2.89,1.82),(1.56,2.89,1.53),.025,ma=brass)
for z in [1.54,1.60]:box('Key teeth',(1.61,2.89,z),(.10,.035,.035),brass,.005)
# Arched postal chest, individual staves rather than a rectangular lid.
box('post | chest body',(-.73,2.2,.45),(1.02,.73,.83),oak,.03)
for i in range(7):box('Chest stave',(-1.16+i*.143,1.824,.45),(.137,.035,.77),wood,.008)
# Half barrel roof along Y.
verts=[];faces=[]
for y in [1.82,2.59]:
    for i in range(25):
        a=i*math.pi/24;verts.append((-.73+.54*math.cos(a),y,.83+.38*math.sin(a)))
for i in range(24):faces.append((i,i+1,i+26,i+25))
faces.extend([tuple(range(24,-1,-1)),tuple(range(25,50))])
faces=[tuple(reversed(f)) for f in faces]
me=bpy.data.meshes.new('Barrel lid mesh');me.from_pydata(verts,[],faces);me.update();o=bpy.data.objects.new('post | curved chest lid',me);bpy.context.collection.objects.link(o);finish(o,o.name,oak,.008)
for x in [-1.15,-.31]:
    box('Chest iron strap',(x,1.788,.50),(.095,.05,.84),iron,.009)
    for z in [.18,.8]:sphere('Hand forged rivet',(x,1.753,z),(.022,.012,.022),brass)
box('Postal slot',(-.73,1.778,.94),(.43,.015,.087),black,.008)
box('Mail emblem plaque',(-.73,1.756,.53),(.37,.025,.23),brass,.01)
for a,b in [((- .9,1.737,.62),(-.73,1.737,.5)),((-.56,1.737,.62),(-.73,1.737,.5))]:beam('Envelope engraving',a,b,.008,ma=darkwood)
for x in [-1.16,-.3]:box('Chest foot',(x,2.2,.1),(.16,.8,.16),iron)
# Left writing table with drawer and open journal.
box('Writing table top',(-1.81,.25,1.03),(1.42,1.43,.13),oak,.025)
for x in [-2.37,-1.24]:
    for y in [-.29,.79]:box('Writing table leg',(x,y,.5),(.105,.105,.95),wood)
box('Desk apron',(-1.81,-.33,.87),(1.21,.12,.23),wood)
box('Desk drawer',(-1.81,-.406,.89),(.73,.042,.155),oak)
sphere('Drawer knob',(-1.81,-.445,.89),(.035,.035,.035),brass)
# Chair in front-left, with open ladder back and rounded rails.
box('Chair seat',(-1.86,-.94,.57),(.69,.65,.12),oak)
for x in [-2.13,-1.59]:
    for y in [-1.18,-.69]:box('Chair legs',(x,y,.29),(.075,.075,.56),wood,.012)
    box('Chair tall upright',(x,-1.19,.98),(.08,.085,.86),wood,.012)
for z in [.97,1.27]:box('Chair backrest',(-1.86,-1.19,z),(.62,.09,.12),oak)
# True layered open pages, with ink strokes.
box('Open journal cover',(-1.9,.08,1.119),(.71,.48,.038),leather,.011)
for side in [-1,1]:
    ob=box('book | open journal pages',(-1.9+side*.167,.08,1.152),(.327,.444,.042),paper,.009); ob.rotation_euler.y=side*.085
    for row in range(9):
        yy=-.09+row*.037
        for seg in range(3):box('Handwritten ink',(-1.9+side*.163+seg*.068-.067,yy,1.18),(.047+random.random()*.015,.0023,.0017),paperedge,.0005)
curve('Journal ribbon',[(-1.9,.2,1.187),(-1.9,-.18,1.18),(-1.92,-.24,1.105),(-1.95,-.3,1.105)],.009,red)
box('Loose letter',(-1.42,.6,1.104),(.30,.36,.006),paper,.003,-.22)
# Mug with hollow dark interior and torus handle.
cyl('Mug',(-2.12,.69,1.25),.096,.28,ceramic)
cyl('Tea',(-2.12,.69,1.394),.081,.005,darkwood)
torus('Mug lip',(-2.12,.69,1.391),.088,.011,ceramic)
torus('Mug handle',(-1.999,.69,1.28),.066,.019,ceramic,(math.pi/2,0,0))
# Reception desk: panelling, moldings, inset front, guest ledger and brass bell.
box('Reception cabinet',(1.02,.52,.58),(2.02,.82,1.13),darkwood,.025)
for i in range(8):box('Reception front raised panel',(.14+i*.25,.091,.59),(.243,.05,.88),wood,.009)
for x in [.03,2.01]:box('Reception corner stile',(x,.035,.60),(.10,.10,1.13),oak)
for z in [.13,1.03]:box('Reception horizontal molding',(1.02,.01,z),(2.12,.13,.11),oak)
for i in range(4):box('Reception countertop plank',(1.02,.11+i*.267,1.19),(2.29,.264,.135),oak,.017)
box('Reception bottom plinth',(1.02,.49,.08),(2.18,.97,.14),wood,.018)
# Guest ledger has layered pages, leather covers, corner guards and straps.
x,y,z=.68,.43,1.31
box('book | guest ledger pages',(x,y,z),(.72,.53,.095),paperedge,.018,-.13)
for dz in [-.063,.063]:box('book | leather cover',(x,y,z+dz),(.77,.57,.035),leather,.018,-.13)
for dz in [-.023,0,.026]:box('Ledger page line',(x,y-.269,z+dz),(.66,.006,.004),paper,.001,-.13)
for dx in [-.26,.26]:box('Ledger brass band',(x+dx,y,z+.09),(.046,.55,.014),brass,.005,-.13)
box('Ledger name plate',(x,y,z+.092),(.30,.115,.012),brass,.008,-.13)
text('Guest label','GUESTS',(x,y-.026,z+.104),.053,darkwood,(0,0,-.13))
# Lathed bell silhouette.
def lathe(name,xy,profile,ma):
    vs=[];fs=[];N=48
    for r,z in profile:
        for i in range(N):a=i*math.tau/N;vs.append((xy[0]+r*math.cos(a),xy[1]+r*math.sin(a),z))
    for j in range(len(profile)-1):
        for i in range(N):a=j*N+i;b=j*N+(i+1)%N;fs.append((a,b,b+N,a+N))
    me=bpy.data.meshes.new(name);me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new(name,me);bpy.context.collection.objects.link(o);finish(o,name,ma)
    for p in me.polygons:p.use_smooth=True
    return o
lathe('Polished reception bell',(1.64,.38),[(0,1.265),(.16,1.265),(.17,1.29),(.15,1.31),(.12,1.33),(.105,1.46),(.07,1.5),(0,1.51)],brass)
cyl('Bell button',(1.64,.38,1.545),.037,.056,brass)
# Potted foliage: curved, solid individual leaves.
def plant(x,y,z,s=1):
    lathe('Tapered clay pot',(x,y),[(.13*s,z),(.19*s,z+.29*s),(.205*s,z+.3*s),(.21*s,z+.34*s),(.17*s,z+.34*s),(.15*s,z+.27*s)],terracotta)
    cyl('Pot soil',(x,y,z+.29*s),.173*s,.014,darkwood)
    for i in range(13):
        a=i*2.399;length=random.uniform(.32,.62)*s;reach=random.uniform(.15,.36)*s
        base=Vector((x,y,z+.29*s)); tip=base+Vector((math.cos(a)*reach,math.sin(a)*reach,length*.7));mid=(base+tip)*.5+Vector((0,0,.14*s));off=Vector((-math.sin(a)*.065*s,math.cos(a)*.065*s,0))
        vs=[base,mid+off,tip,mid-off,mid+Vector((0,0,.022*s))];fs=[(0,1,4),(1,2,4),(2,3,4),(3,0,4)]
        me=bpy.data.meshes.new('Leaf');me.from_pydata(vs,[],fs);me.update();o=bpy.data.objects.new('Sculpted leaf',me);bpy.context.collection.objects.link(o);finish(o,'Sculpted leaf',random.choice(leaves));sol=o.modifiers.new('Leaf thickness','SOLIDIFY');sol.thickness=.006
        curve('Leaf central vein',[base,mid,tip],.003*s,leaves[2])
plant(2.30,-.42,.05,1.35)
plant(-2.38,.7,1.38,.6)
# Runner brings the eye from the doorway toward the counter.
box('Woven entry runner',(.38,-1.65,.074),(1.51,1.7,.018),cloth,.02)
for x in [-.32,1.08]:box('Runner stitched border',(x,-1.65,.087),(.016,1.59,.002),paperedge,.001)
for y in [-2.42,-.88]:box('Runner stitched border',(.38,y,.087),(1.4,.016,.002),paperedge,.001)
for i in range(39):box('Runner weave',(-.32+i*.036,-1.65,.085),(.005,1.6,.002),darkwood,.001)
# Exterior entrance is behind the arrival camera; threshold denotes entry direction.
box('Entry threshold',(.9,-3.31,.09),(1.48,.19,.15),oak)
# Soft warm evening lighting, also recreated in Three.js.
def area(name,loc,energy,color,size,target):
    bpy.ops.object.light_add(type='AREA',location=loc);o=bpy.context.object;o.name=name;o.data.energy=energy;o.data.color=color;o.data.shape='DISK';o.data.size=size;o.rotation_euler=(Vector(target)-o.location).to_track_quat('-Z','Y').to_euler()
area('Window honey light',(-2.3,.25,2.35),230,(1,.71,.4),1.7,(0,.5,.7))
area('Warm ceiling bounce',(0,-.7,3.5),180,(1,.83,.62),4,(0,1,0))
area('Doorway fill',(0,-3,2.4),100,(.67,.75,1),3,(0,1,1))
bpy.ops.object.light_add(type='POINT',location=(1.98,2.40,2.67));bpy.context.object.name='Candle light';bpy.context.object.data.energy=9;bpy.context.object.data.color=(1,.52,.20);bpy.context.object.data.shadow_soft_size=.17
# Actual doorway POV, no exterior dollhouse view used in the app.
bpy.ops.object.camera_add(location=(1.15,-3.9,2.15));cam=bpy.context.object;cam.name='Arrival • portrait camera';target=Vector((-.15,1.25,1.05));cam.rotation_euler=(target-cam.location).to_track_quat('-Z','Y').to_euler();cam.data.type='PERSP';cam.data.lens=20;cam.data.sensor_fit='HORIZONTAL';cam.data.sensor_width=25
scene=bpy.context.scene;scene.camera=cam;scene.render.engine='CYCLES';scene.cycles.samples=32;scene.cycles.use_denoising=True
scene.world.color=(.16,.16,.16);scene.render.resolution_x=900;scene.render.resolution_y=1500;scene.render.resolution_percentage=70
scene.view_settings.view_transform='AgX';scene.render.image_settings.file_format='PNG';scene.render.filepath=os.path.join(OUT,'interior-preview.png')
# Editable master first. GLB merges static meshes by material to reduce draw calls.
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'modeling','Hush_Inn_Interior.blend'))
for o in list(scene.objects):
    if o.type in {'MESH','CURVE','FONT'}:
        bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o
        bpy.ops.object.convert(target='MESH')
# Keep interactive semantic meshes separate from the static room.
groups={}
for o in list(scene.objects):
    if o.type!='MESH':continue
    route='book' if o.name.startswith('book |') else 'post' if o.name.startswith('post |') else 'static'
    if route!='static':o['go']=route
    key=(route,o.data.materials[0].name if o.data.materials else '')
    groups.setdefault(key,[]).append(o)
for (route,material),objects in groups.items():
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:o.select_set(True)
    bpy.context.view_layer.objects.active=objects[0];bpy.ops.object.join();o=bpy.context.object;o.name=route+' • '+material
    if route!='static':o['go']=route
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT,'hush-inn-interior.glb'),export_format='GLB',export_extras=True,export_cameras=False,export_lights=False)
bpy.ops.render.render(write_still=True)
print('HUSH_BUILD_COMPLETE')
