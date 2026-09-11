"""Same inn, after dark: blue outside light, warm lamps, no daylight illumination."""
import bpy, os
ROOT=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
bpy.ops.wm.open_mainfile(filepath=os.path.join(ROOT,'modeling','Hush_Inn_Interior.blend'))
scene=bpy.context.scene
settings={
 'Window honey light':(12,(.20,.35,1)),
 'Warm ceiling bounce':(65,(1,.48,.19)),
 'Doorway fill':(14,(.25,.35,.70)),
 'Candle light':(22,(1,.39,.10))
}
for o in scene.objects:
 if o.type=='LIGHT' and o.name in settings:
  energy,color=settings[o.name];o.data.energy=energy;o.data.color=color
m=bpy.data.materials.get('Amber light');bs=m.node_tree.nodes.get('Principled BSDF')
bs.inputs['Base Color'].default_value=(.008,.015,.055,1)
bs.inputs['Emission Color'].default_value=(.06,.13,.42,1)
bs.inputs['Emission Strength'].default_value=.25
m.diffuse_color=(.008,.015,.055,1)
scene.world.color=(.009,.012,.025)
scene.render.resolution_percentage=70;scene.cycles.samples=48
scene.render.filepath=os.path.join(ROOT,'assets','models','interior-night-preview.png')
bpy.context.preferences.filepaths.save_version=0
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(ROOT,'modeling','Hush_Inn_Interior_Night.blend'))
bpy.ops.render.render(write_still=True)
