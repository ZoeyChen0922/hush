"""Bake Blender soft lighting into one mobile-friendly UV atlas, keep semantic meshes."""
import bpy, os, time
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PHASE=os.environ.get('HUSH_PHASE','day')
SOURCE='Hush_Inn_Interior_Night.blend' if PHASE=='night' else 'Hush_Inn_Interior.blend'
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT,'modeling',SOURCE))
scene=bpy.context.scene
# Soft indoor illumination; the emissive window is also an area source.
scene.cycles.samples=32
scene.cycles.use_denoising=True
scene.render.bake.margin=6
meshes=[]
for o in list(scene.objects):
    if o.type not in {'MESH','CURVE','FONT'}:continue
    bpy.ops.object.select_all(action='DESELECT');o.select_set(True);bpy.context.view_layer.objects.active=o;bpy.ops.object.convert(target='MESH')
    o=bpy.context.object
    route=1 if o.name.startswith('book |') else 2 if o.name.startswith('post |') else 0
    vg=o.vertex_groups.new(name='route_%d'%route);vg.add(list(range(len(o.data.vertices))),1,'REPLACE');meshes.append(o)
bpy.ops.object.select_all(action='DESELECT')
for o in meshes:o.select_set(True)
bpy.context.view_layer.objects.active=meshes[0];bpy.ops.object.join();obj=bpy.context.object;obj.name='Hush • baked room'
# Preserve the source wood coordinates while baking to a second UV set.
old_uv=obj.data.uv_layers.active
old_uv.name='SourceUV'
for ma in obj.data.materials:
    if not ma or not ma.use_nodes:continue
    for node in list(ma.node_tree.nodes):
        if node.type=='TEX_IMAGE' and node.image:
            uv=ma.node_tree.nodes.new('ShaderNodeUVMap');uv.uv_map='SourceUV';ma.node_tree.links.new(uv.outputs['UV'],node.inputs['Vector'])
light_uv=obj.data.uv_layers.new(name='Lightmap')
obj.data.uv_layers.active=light_uv
light_uv.active_render=True
# Single UV atlas shared by all geometry, consistent texel density.
bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='SELECT');bpy.ops.uv.smart_project(angle_limit=1.15192,island_margin=.003,area_weight=.5);bpy.ops.object.mode_set(mode='OBJECT')
im=bpy.data.images.new('Hush • soft evening light atlas',width=4096,height=4096,alpha=False)
for ma in obj.data.materials:
    if not ma:continue
    ma.use_nodes=True
    node=ma.node_tree.nodes.new('ShaderNodeTexImage');node.image=im;ma.node_tree.nodes.active=node;node.select=True
scene.render.engine='CYCLES';scene.cycles.bake_type='COMBINED'
print('HUSH_BAKE_BEGIN',flush=True)
bpy.ops.object.bake(type='COMBINED',use_clear=True)
im.filepath_raw=os.path.join(ROOT,'assets','models','interior-'+PHASE+'-light-atlas.png');im.file_format='PNG';im.save();im.pack()
print('HUSH_BAKE_DONE',flush=True)
ma=bpy.data.materials.new('Baked evening • Blender soft shadows');ma.use_nodes=True
bs=ma.node_tree.nodes.get('Principled BSDF');bs.inputs['Base Color'].default_value=(0,0,0,1);bs.inputs['Roughness'].default_value=1
bs.inputs['Emission Strength'].default_value=1
node=ma.node_tree.nodes.new('ShaderNodeTexImage');node.image=im;ma.node_tree.links.new(node.outputs['Color'],bs.inputs['Emission Color'])
# Export only baked UVs so the GLB material defaults to the correct set.
obj.data.uv_layers.remove(obj.data.uv_layers['SourceUV'])
obj.data.materials.clear();obj.data.materials.append(ma)
for p in obj.data.polygons:p.material_index=0
# Semantic hit targets use their own mesh; they remain part of the same atlas.
for n,route in [(1,'book'),(2,'post')]:
    bpy.context.view_layer.objects.active=obj;bpy.ops.object.select_all(action='DESELECT');obj.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.select_all(action='DESELECT');bpy.ops.object.mode_set(mode='OBJECT')
    vg=obj.vertex_groups.get('route_%d'%n)
    if not vg:continue
    for v in obj.data.vertices:v.select=any(g.group==vg.index for g in v.groups)
    bpy.ops.object.mode_set(mode='EDIT');bpy.ops.mesh.separate(type='SELECTED');bpy.ops.object.mode_set(mode='OBJECT')
    for o in list(bpy.context.selected_objects):
        if o!=obj:o.name=route+' • interactive';o['go']=route
obj['bakedLighting']=True
for o in scene.objects:
    if o.type=='MESH':o['bakedLighting']=True
bpy.ops.export_scene.gltf(filepath=os.path.join(ROOT,'assets','models','hush-inn-'+PHASE+'.glb'),export_format='GLB',export_extras=True,export_cameras=False,export_lights=False)
# The master remains fully editable with lights and original PBR materials.
for screen in bpy.data.screens:
    for area in screen.areas:
        if area.type=='VIEW_3D':
            area.spaces.active.region_3d.view_perspective='CAMERA'
            area.spaces.active.shading.type='MATERIAL'
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'modeling','Hush_Inn_Interior_'+PHASE.title()+'_Mobile.blend'))
print('HUSH_MOBILE_COMPLETE',flush=True)
