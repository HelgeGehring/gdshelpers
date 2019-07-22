import bpy
import bmesh
import sys
import os
import numpy as np

# Remove the standard cube and the lamp of blender
blender_objects = bpy.data.objects
blender_objects.remove(blender_objects["Cube"], True)
blender_objects.remove(blender_objects["Lamp"], True)

scene = bpy.context.scene

# Load the 3d objects
argv = sys.argv
argv = argv[argv.index("--") + 1:]
raw_input_from_file = open(argv[0] + ".tmp").read()

for end_string in [".tmp", ".png", ".blend"]:
    if os.path.exists(argv[0] + end_string):
        os.remove(argv[0] + end_string)

blocks = raw_input_from_file.split('\n')
config = blocks[0].split(';')

index = 1
material_dict = {}

# Saves the meshes and the merge index
meshes = []
meshes_index = []

merge_index = -1

# Buffer variables needed for the calculation of the camera position
x_min = x_max = y_min = y_max = z_min = z_max = 0

# Create the meshes and link them to the scene
while index < len(blocks) - 1:
    # Read information about the mesh object
    info = blocks[index].split(';')
    merge_index = int(info[0])
    block_len = int(info[1])
    extrude_val_min = float(info[2])
    extrude_val_max = float(info[3])
    scale = float(info[4])
    rgb = [int(info[5]), int(info[6]), int(info[7])]
    index += 1

    # Read the vertices
    vertices = [(float(blocks[i].split()[0]) * scale, float(blocks[i].split()[1]) * scale, extrude_val_min * scale)
                for i in range(index, index + block_len)]

    # Have a look at the dimensions of the objects -> to set the camera position
    for vertex in vertices:
        if vertex[0] > x_max:
            x_max = vertex[0]
        if vertex[0] < x_min:
            x_min = vertex[0]
        if vertex[1] > y_max:
            y_max = vertex[1]
        if vertex[1] < y_min:
            y_min = vertex[1]

    if extrude_val_min < z_min:
        z_min = extrude_val_min
    if extrude_val_max > z_max:
        z_max = extrude_val_max

    index += block_len

    # Create the mesh, color and extrude it
    mesh = bpy.data.meshes.new("mesh_" + str(index))
    b_mesh = bmesh.new()
    b_vertices = [b_mesh.verts.new(vertex) for vertex in vertices]
    b_face = b_mesh.faces.new(b_vertices)
    b_face.normal = (0, 0, -1)
    bmesh.ops.solidify(b_mesh, geom=[b_face], thickness=extrude_val_max * scale)
    b_mesh.to_mesh(mesh)
    mesh_object = bpy.data.objects.new("obj_" + str(index), mesh)
    material_name = str(rgb[0]).ljust(3) + str(rgb[1]).ljust(3) + str(rgb[2]).ljust(3)
    structure_material = bpy.data.materials.new(material_name)
    structure_material.diffuse_color = (rgb[0] / 255, rgb[1] / 255, rgb[2] / 255)
    if material_name not in material_dict.keys():
        material_dict.update({material_name: structure_material})
    mesh_object.data.materials.append(material_dict[material_name])
    # Add to the mesh lists
    meshes_index.append(merge_index)
    meshes.append(mesh_object)
    scene.objects.link(mesh_object)


#
# Join the meshes corresponding to a specific Shapely3D object
#

def get_first_of_equal_index(index_list):
    buffer_list = []

    for test_index in index_list:
        if test_index in buffer_list:
            for j, ind in enumerate(buffer_list):
                if ind == test_index and ind != -1:
                    return j
        buffer_list.append(test_index)
    return -1


def join_on_scene(mesh_list, index_list):
    fuse = get_first_of_equal_index(index_list)
    new_list = list(index_list)

    if fuse != -1:
        bpy.ops.object.select_all(action='DESELECT')
        mesh_list[fuse].select = True
        bpy.context.scene.objects.active = mesh_list[fuse]
        for k in range(fuse + 1, len(new_list)):
            if new_list[fuse] == new_list[k]:
                mesh_list[k].select = True
                bpy.context.scene.objects.active = mesh_list[k]
                new_list[k] = -1
        new_list[fuse] = -1
        bpy.ops.object.join()
        join_on_scene(mesh_list, new_list)


join_on_scene(meshes, meshes_index)

#
# Do the calculation for the camera position
#

# The diagonal line of the floor follows the equation y(x) = m * x + b
if config[7] == 'right':
    m = (y_max - y_min) / (x_max - x_min) if config[6] == 'above' else - (y_max - y_min) / (x_max - x_min)
    b = y_min - m * x_min if config[6] == 'above' else y_min - m * x_max
else:
    m = (y_max - y_min) / (x_max - x_min) if config[6] == 'under' else - (y_max - y_min) / (x_max - x_min)
    b = y_min - m * x_min if config[6] == 'under' else y_min - m * x_max

# Length of the diagonal line
m_width = np.sqrt((x_max - x_min) ** 2 + (y_max - y_min) ** 2)
ratio = 2.5  # Define an arbitrary value which sets the distance between the camera and the objects

alpha = np.arctan(m)
m_width_cam = m_width * ratio

cam_pos_x = np.cos(alpha) * m_width_cam if config[7] == 'right' else - np.cos(alpha) * m_width_cam
cam_pos_y = m * cam_pos_x + b
cam_pos_z = m_width_cam / 2

# Set the point on the floor at which the camera will look
mid_x = (x_max + x_min) / 2
mid_y = (y_max + y_min) / 2

rot_y = 0
rot_x = 90 - 180 / np.pi * np.arctan(cam_pos_z / np.sqrt((cam_pos_x - mid_x) ** 2 + (cam_pos_y - mid_y) ** 2))

if config[6] == 'above':
    rot_z = np.abs(180 / np.pi * np.arctan(m)) + 90 if config[7] == 'right' else np.abs(
        180 / np.pi * np.arctan(m)) + 225
else:
    rot_z = np.abs(180 / np.pi * np.arctan(m)) + 45 if config[7] == 'right' else np.abs(
        180 / np.pi * np.arctan(m)) + 270

#
# Add the new lamp to the scene and set the calculated camera parameters
#

lamp_data = bpy.data.lamps.new(name="New Lamp", type='SUN')
lamp_object = bpy.data.objects.new(name="New Lamp", object_data=lamp_data)
scene.objects.link(lamp_object)
lamp_object.location = (cam_pos_x, cam_pos_y, cam_pos_z)  # Place the lamp exactly on the camera

lamp_object.data.use_nodes = True
lamp_object.data.node_tree.nodes['Emission'].inputs['Strength'].default_value = 1

scene.camera.location.x = cam_pos_x
scene.camera.location.y = cam_pos_y
scene.camera.location.z = cam_pos_z

scene.camera.rotation_mode = 'XYZ'
scene.camera.rotation_euler[0] = rot_x * (np.pi / 180.0)
scene.camera.rotation_euler[1] = rot_y * (np.pi / 180.0)
scene.camera.rotation_euler[2] = rot_z * (np.pi / 180.0)

scene.camera.data.clip_end = 500

bpy.data.scenes["Scene"].render.resolution_x = int(config[2])
bpy.data.scenes["Scene"].render.resolution_y = int(config[3])
bpy.data.scenes["Scene"].render.resolution_percentage = int(config[4])
bpy.context.scene.render.engine = config[5]
bpy.context.scene.cycles.samples = 128
if config[0] == '1':
    bpy.data.scenes["Scene"].render.filepath = sys.argv[3].rsplit('\\', 1)[0] + '\\' + argv[0] + '.png'
    bpy.ops.render.render(write_still=True)
if config[1] == '1':
    bpy.ops.wm.save_mainfile(filepath=argv[0] + ".blend")
