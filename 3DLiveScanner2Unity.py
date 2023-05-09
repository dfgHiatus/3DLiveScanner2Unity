import os, bpy

from bpy.props import (
    StringProperty,
    BoolProperty,
    IntProperty,
    FloatProperty,
    FloatVectorProperty,
    EnumProperty,
    PointerProperty
    )
from bpy.types import (
    Panel,
    Operator,
    AddonPreferences,
    PropertyGroup
)

bl_info = {
    "name": "3DLiveScanner to Unity",
    "blender": (3, 3, 0),
    "category": "Object"
}

HARDWARE_TYPES = (
    ('0','CPU',''),
    ('1','CUDA',''),
    ('2','OptiX',''),
    ('3','HIP',''),
    ('4','OneAPI','')
)

bpy.types.Scene.hardwareTypes = bpy.props.EnumProperty(items = HARDWARE_TYPES)
scene = bpy.context.scene
scene.cycles.bake_type = 'DIFFUSE'
scene.render.engine = 'CYCLES'
scene.render.engine = 'CYCLES'
scene.render.bake.use_pass_indirect = False
scene.render.bake.use_pass_direct = False
scene.render.bake.use_pass_color = True
scene.render.bake.target = 'VERTEX_COLORS'

class BoolSetting(PropertyGroup):
    overwrite : BoolProperty(
        name="Overwrite",
        description="Overwrite existing files",
        default = False
    )

class InputSettings(bpy.types.PropertyGroup):
    file_path: bpy.props.StringProperty(
        name="Input path",
        description="Input path to process",
        default="",
        maxlen=1024,
        subtype="DIR_PATH"
    )
                                        
class OutputSettings(bpy.types.PropertyGroup):
    file_path: bpy.props.StringProperty(
        name="Output path",
        description="Output path to process",
        default="",
        maxlen=1024,
        subtype="DIR_PATH"
    )
                                        
class Importer(bpy.types.Operator):
    bl_idname = "bakery.impoter"
    bl_label = "Bake!"
        
    if bpy.context.scene.hardwareTypes == '0':
        processor = 'CPU'
    else:
        processor = 'GPU'
        
    bpy.context.scene.cycles.device = processor

    def execute(self, context):    
        for root, dirs, files in os.walk(bpy.context.scene.input.file_path):
            for file in files:
                if file.endswith(".obj"):
                    import_obj(os.path.join(root, file))
                    
        return {'FINISHED'}

class Bakery(bpy.types.Panel):
    bl_idname = "bakery"
    bl_label = "3DLiveScanner to Unity"
    bl_category = "3DLiveScanner Tools"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"

    def draw(self, context):
        layout = self.layout
        
        row = layout.row()
        row.label(text="Instructions :")
        row = layout.row()
        row.label(text="1) Create a new material and call it 'Vertex Color'")
        row = layout.row()
        row.label(text="2) Specify the parameters you would like")
        row = layout.row()
        row.label(text="('Input path' points to a directory of obj's)")
        row = layout.row()
        row.label(text="3) Open the Blender system console to monitor progress")
        row = layout.row()
        row.label(text="4) Click Bake to convert!")
        
        row = layout.row()
        input = context.scene.input
        row.prop(input, "file_path")
        
        row = layout.row()
        output = context.scene.output
        row.prop(output, "file_path")
        
        row = layout.row()
        row.label(text="Target Hardware:")
        layout.prop(context.scene, 'hardwareTypes', expand=True)
        
        bool = scene = context.scene.overwrite
        layout.prop(bool, "overwrite", text="Overwrite existing files")
        
        row = layout.row()
        row.operator("bakery.impoter", text="Bake!")

classes = (
    BoolSetting,
    InputSettings,
    OutputSettings,
    Importer,
    Bakery
)

def import_obj(file):
    directory_path = os.path.join(
            bpy.context.scene.output.file_path, 
            os.path.splitext(os.path.basename(file))[0])
    directory_exists = os.path.isdir(directory_path)
    if (
        not bpy.context.scene.overwrite.overwrite 
        and directory_exists
    ):
        print("Path found at %s, skipping..." % directory_path)
        return
    
    # Import the OBJ and select it
    print("Importing the OBJ, selecting...")
    bpy.ops.import_scene.obj(filepath=file)
    bpy.ops.object.select_all(action='DESELECT')
    obj = bpy.context.scene.objects[0]
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True) 
    
    # Strip the existing materials, add our new one, and apply a vertex color layer
    print("Setting up materials, vertex colors...")
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.geometry.color_attribute_add(name='Color', domain='CORNER', data_type='BYTE_COLOR')
    bpy.ops.object.mode_set(mode='OBJECT')
    
    # Execute the bake command
    print("Starting bake...")
    bpy.ops.object.bake(type='DIFFUSE')
    print("Done baking!")
    
    # Cleanup
    mesh = obj.data
    for uv_layer in mesh.uv_layers:
        mesh.uv_layers.remove(uv_layer)
    while mesh.materials: 
        mesh.materials.pop()
    bpy.ops.object.material_slot_add()
    mesh.materials[0] = bpy.data.materials['Vertex Color']
    
    # Merge doubles, triangulate, tris to quads
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.remove_doubles()
    bpy.ops.mesh.quads_convert_to_tris(quad_method='BEAUTY', ngon_method='BEAUTY')
    bpy.ops.mesh.tris_convert_to_quads()
    bpy.ops.object.mode_set(mode='OBJECT')
        
    # Name and save the exported mesh
    filename, _ = os.path.splitext(os.path.basename(file))
    fbx_name = filename + "_Converted.fbx"
    fbx_dir = os.path.join(bpy.context.scene.output.file_path, filename)
    if not os.path.exists(fbx_dir):
        os.makedirs(fbx_dir)
    combined = os.path.join(fbx_dir, fbx_name)
    print("Done, saving as: " + combined)
    bpy.ops.export_scene.fbx(filepath=combined)
    
    # Delete the old file and repeat
    bpy.ops.object.delete(use_global=False, confirm=False)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.input = bpy.props.PointerProperty(type=InputSettings)
    bpy.types.Scene.output = bpy.props.PointerProperty(type=OutputSettings)
    bpy.types.Scene.overwrite = PointerProperty(type=BoolSetting)

def unregister():
    for cls in classes:
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.input
    del bpy.types.Scene.output
    del bpy.types.Scene.overwrite

if __name__ == "__main__":
    register()