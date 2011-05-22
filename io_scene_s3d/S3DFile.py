#!/usr/bin/python3
#
# io_scene_s3d
#
# Copyright (C) 2011 Steven J Thompson
#
# ##### BEGIN GPL LICENSE BLOCK #####
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software Foundation,
# Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA.
#
# ##### END GPL LICENSE BLOCK #####

import bpy
import struct
import os
from .BinaryFile import BinaryFile

class S3DFile(BinaryFile):

    def open(self, path, switchGLSL):

        ####################
        ## S3D file
        ####################

        self.openFile(path, "rb")

        file_type = ""
        for x in range(4):
            file_type += bytes.decode(struct.unpack("c", self.f.read(1))[0])

        version = self.readFromFile("i", 1)[0]

        textureCount = self.readFromFile("H", 1)[0]
        materialCount = self.readFromFile("H", 1)[0]
        objectCount = self.readFromFile("H", 1)[0]
        lightCount = self.readFromFile("H", 1)[0]
        helperCount = self.readFromFile("H", 1)[0]

        boneid = self.readFromFile("i", 1)[0]

        textures = []
        materials = []

        ## for all the textures in the file
        for t in range(textureCount):

            ## read texture filename
            textureName = self.readFromFile("c")

            ## put the texture into the textures list
            textures.append(textureName)
            
            texId = self.readFromFile("L", 1)
            texStartFrame = self.readFromFile("H", 1)[0]
            texFrameChangeTime = self.readFromFile("H", 1)[0]
            texDynamic = self.readFromFile("B", 1)

        ## for all the materials in the file
        for m in range(materialCount):

            ## read material name
            materialName = self.readFromFile("c")

            ## get the details of the material texture
            materialTextureBase = self.readFromFile("h", 1)[0]
            materialTextureBase2 = self.readFromFile("h", 1)[0]
            materialTextureBump = self.readFromFile("h", 1)[0]
            materialTextureReflection = self.readFromFile("h", 1)[0]

            if version >= 14:
                materialTextureDistortion = self.readFromFile("h", 1)[0]

            materialColour = self.readFromFile("f", 3)
            materialSelfIllum = self.readFromFile("f", 3)
            materialSpecular = self.readFromFile("f", 3)
            materialSpecularSharpness = self.readFromFile("f", 1)

            materialDoubleSided = self.readFromFile("B", 1)
            materialWireframe = self.readFromFile("B", 1)

            materialReflectionTexgen = self.readFromFile("i", 1)
            materialAlphablendType = self.readFromFile("i", 1)

            materialTransparency = self.readFromFile("f", 1)

            if version >= 12:
                materialGlow = self.readFromFile("f", 1)

            if version >= 13:
                materialScrollSpeed = self.readFromFile("f", 2)
                materialScrollStart = self.readFromFile("B", 1)

            if materialTextureBase2 >= 0:
                tlayer = self.readFromFile("f", 2)
            
            if materialTextureReflection >= 0:
                tlayer = self.readFromFile("f", 2)

            mat = bpy.data.materials.new(materialName)
            mat.diffuse_color[0] = materialColour[0]
            mat.diffuse_color[1] = materialColour[1]
            mat.diffuse_color[2] = materialColour[2]

            tex = bpy.data.textures.new(materialName, type = 'IMAGE')
            texSlot = mat.texture_slots.add()
            texSlot.texture = tex
            texSlot.texture_coords = 'UV'

            try:
                image = bpy.data.images.load(self.getDirectory() + textures[materialTextureBase])
                tex.image = image
                print("Image loaded from: " + textures[materialTextureBase])
                imageLoaded = True
            except:
                print("Could not load image id: " + str(materialTextureBase))
                imageLoaded = False

            if imageLoaded == True:
                ## set material to use transparency
                mat.use_transparency = True
                mat.alpha = 0

                ## set the texture to use the alpha as transparency
                texSlot.use_map_alpha = True

            ## append material name to the materials list
            materials.append(mat)

        ## for all the objects in the file
        for o in range(objectCount):

            objectName = self.readFromFile("c")
            objectParent = self.readFromFile("c")

            materialIndex = self.readFromFile("H", 1)[0]

            ## object position
            objectPositionX = self.readFromFile("f", 1)[0]
            objectPositionY = self.readFromFile("f", 1)[0]
            objectPositionZ = self.readFromFile("f", 1)[0]

            ## object rotation
            objectRotationW = self.readFromFile("f", 1)[0]
            objectRotationX = self.readFromFile("f", 1)[0]
            objectRotationY = self.readFromFile("f", 1)[0]
            objectRotationZ = self.readFromFile("f", 1)[0]

            ## object scale
            objectScaleX = self.readFromFile("f", 1)[0]
            objectScaleY = self.readFromFile("f", 1)[0]
            objectScaleZ = self.readFromFile("f", 1)[0]

            objectNoCollision = self.readFromFile("B", 1)
            objectNoRender = self.readFromFile("B", 1)
            objectLightObject = self.readFromFile("B", 1)

            objectVertexAmount = self.readFromFile("H", 1)[0]
            objectFaceAmount = self.readFromFile("H", 1)[0]
            
            objectLOD = self.readFromFile("B", 1)
            objectWeights = self.readFromFile("B", 1)

            ## Create new mesh in Blender for this object
            mesh = bpy.data.meshes.new(name = str(objectName))

            ## Create new object in Blender for this object
            obj = bpy.data.objects.new(str(objectName), mesh)

            ## Add this object to the Blender scene
            base = bpy.context.scene.objects.link(obj)

            ## Set the object location
            obj.location = (objectPositionX, objectPositionY, objectPositionZ)

            ## Set the object rotation
            obj.rotation_quaternion = (objectRotationX, objectRotationY, objectRotationZ, objectRotationW)

            vertex = []
            faces = []
            uvTex = []

            ## For all the vertex in the object
            for n in range(objectVertexAmount):
                vertexPosition = self.readFromFile("f", 3)
                vertexNormal = self.readFromFile("f", 3)
                vertexTextureCoords = self.readFromFile("f", 2)
                vertexTextureCoords2 = self.readFromFile("f", 2)

                ## store vertex data
                ## y and z are swapped due to differences between which axis is 'up' between Blender and Storm3D
                vertex.append((vertexPosition[0], vertexPosition[2], vertexPosition[1]))

                ## store texture coord data
                uvTex.append((vertexTextureCoords[0], -(vertexTextureCoords[1])))

            ## For all the faces in the object
            for n in range(objectFaceAmount):
                face = self.readFromFile("H", 3)
                faces.append(face)

            bonesList = {}
            if objectWeights == True:
                ## For all the weights in the object
                for n in range(objectVertexAmount):
                    bone1 = str(self.readFromFile("i", 1)[0])
                    bone2 = str(self.readFromFile("i", 1)[0])
                    weight1 = self.readFromFile("B", 1)
                    weight2 = self.readFromFile("B", 1)

                    ## Create the vertex group if it does not already exist.
                    if obj.vertex_groups.get(bone1) == None:
                        obj.vertex_groups.new(bone1)

                    ## Put the vertex data into the dictionary.
                    if bone1 in bonesList:
                        if weight1 in bonesList[bone1]:
                            bonesList[bone1][weight1].append(n)
                        else:
                            bonesList[bone1][weight1] = [n]
                    else:
                        bonesList[bone1] = {}

            ## Send data to the mesh in Blender
            mesh.from_pydata(vertex, [], faces)
            mesh.update()

            ## Put weight data into the vertex groups
            for b in bonesList.keys():
                for w in bonesList[b].keys():
                    obj.vertex_groups[b].add(bonesList[b][w], (w / 100), 'REPLACE')

            bpy.context.scene.objects.active = obj
            bpy.ops.mesh.uv_texture_add()
            uv = obj.data.uv_textures.active
            faces = obj.data.faces

            for face, i in enumerate(uv.data):
                i.uv1 = uvTex[faces[face].vertices[0]]
                i.uv2 = uvTex[faces[face].vertices[1]]
                i.uv3 = uvTex[faces[face].vertices[2]]

            bpy.ops.object.mode_set(mode = 'EDIT')
            bpy.ops.mesh.remove_doubles()
            bpy.ops.mesh.normals_make_consistent()
            bpy.ops.object.mode_set(mode = 'OBJECT')

            if switchGLSL == True:
                ## Set GLSL shading
                bpy.context.scene.game_settings.material_mode = 'GLSL'

            ## Set all the 3d viewports to textured
            for a in bpy.context.screen.areas:
                if a.type == 'VIEW_3D':
                    a.active_space.viewport_shade = 'TEXTURED'

            ## Set the material in Blender
            mesh.materials.append(materials[materialIndex])

        if (objectCount > 0):
            bpy.ops.object.select_all(action = 'SELECT')
            bpy.ops.object.shade_smooth()
            bpy.ops.object.select_all(action = 'DESELECT')

        ## for all the lights in the file
        for l in range(lightCount):
            lightName = self.readFromFile("c")
            lightParentName = self.readFromFile("c")

            lightType = self.readFromFile("i", 1)
            lightLensflareIndex = self.readFromFile("i", 1)
            lightColour = self.readFromFile("f", 3)
            lightPosition = self.readFromFile("f", 3)
            lightDirection = self.readFromFile("f", 3)

            lightConeInner = self.readFromFile("f", 1)
            lightConeOuter = self.readFromFile("f", 1)
            lightMultiplier = self.readFromFile("f", 1)
            lightDecay = self.readFromFile("f", 1)

            lightKeyframeEndtime = self.readFromFile("i", 1)

            lightPoskeyAmount = self.readFromFile("B", 2)
            lightDirkeyAmount = self.readFromFile("B", 2)
            lightLumkeyAmount = self.readFromFile("B", 2)
            lightConekeyAmount = self.readFromFile("B", 2)

        ## for all the helpers in the file
        for h in range(helperCount):
            helpName = self.readFromFile("c")
            helpParentName = self.readFromFile("c")

            helpType = self.readFromFile("i", 1)
            helpPosition = self.readFromFile("f", 3)
            helpOther = self.readFromFile("f", 3)
            helpOther2 = self.readFromFile("f", 3)

            helpKeyframeEndtime = self.readFromFile("i", 1)

            helpPoskeyAmount = self.readFromFile("B", 2)
            helpO1keyAmount = self.readFromFile("B", 2)
            helpO2keyAmount = self.readFromFile("B", 2)

        ## Close the S3D file
        self.closeFile()

    def getObjectsOfType(self, objType):
        objectList = []
        for o in bpy.data.objects:
            if o.type == objType:
                objectList.append(bpy.data.objects[o.name])
        return objectList

    def write(self, path):

        ####################
        ## S3D file
        ####################

        ## Create and open the target S3D file
        self.openFile(path, "wb")

        file_type = "S3D0"
        version = 14
        self.writeToFile("s", file_type, False)
        self.writeToFile("i", version)

        textures = bpy.data.textures
        self.writeToFile("H", len(textures))

        materials = bpy.data.materials
        self.writeToFile("H", len(materials))

        objects = self.getObjectsOfType('MESH')
        self.writeToFile("H", len(objects))

        lights = 0
        self.writeToFile("H", lights)

        num_hel = 0
        self.writeToFile("H", num_hel)

        boneid = 0
        self.writeToFile("i", boneid)

        texturesIdList = []
        for t in textures:

            ## textureName
            self.writeToFile("s", t.image.name)

            texturesIdList.append(t.image.name)

            ## texId
            self.writeToFile("L", 0)

            ## texStartFrame
            self.writeToFile("H", 0)

            ## texFrameChangeTime
            self.writeToFile("H", 0)

            ## texDynamic
            self.writeToFile("B", 0)

        materialsIdList = []
        for m in materials:

            ## write material name
            self.writeToFile("s", m.name)

            materialsIdList.append(m.name)

            ## materialTextureBase
            textureBase = bpy.data.textures[m.texture_slots[0].name].image.name
            textureId = texturesIdList.index(textureBase)
            self.writeToFile("h", textureId)

            ## materialTextureBase2
            materialTextureBase2 = -1
            self.writeToFile("h", materialTextureBase2)

            ## materialTextureBump
            self.writeToFile("h", -1)

            ## materialTextureReflection
            materialTextureReflection = -1
            self.writeToFile("h", materialTextureReflection)

            if version >= 14:
                ## materialTextureDistortion
                self.writeToFile("h", -1)

            ## materialColour
            self.writeToFile("f", m.diffuse_color[0])
            self.writeToFile("f", m.diffuse_color[1])
            self.writeToFile("f", m.diffuse_color[2])

            ## materialSelfIllum
            self.writeToFile("f", 0.0)
            self.writeToFile("f", 0.0)
            self.writeToFile("f", 0.0)

            ## materialSpecular
            self.writeToFile("f", 0.0)
            self.writeToFile("f", 0.0)
            self.writeToFile("f", 0.0)

            ## materialSpecularSharpness
            self.writeToFile("f", 1.0)

            ## materialDoubleSided
            self.writeToFile("B", 0)

            ## materialDoubleWireframe
            self.writeToFile("B", 0)

            ## materialReflectionTexgen
            self.writeToFile("i", 0)

            ## materialAlphablendType
            self.writeToFile("i", 0)

            ## materialTransparency
            self.writeToFile("f", 0.0)

            if version >= 12:
                ## materialGlow
                self.writeToFile("f", 0.0)

            if version >= 13:
                ## materialScrollSpeed
                self.writeToFile("f", 0.0)
                self.writeToFile("f", 0.0)

                ## materialScrollStart
                self.writeToFile("B", 0)

            if materialTextureBase2 >= 0:
                self.writeToFile("f", 1.0)
                self.writeToFile("f", 1.0)

            if materialTextureReflection >= 0:
                self.writeToFile("f", 1.0)
                self.writeToFile("f", 1.0)

        for o in objects:
            bpy.context.scene.objects.active = o
            bpy.ops.object.mode_set(mode = 'EDIT')
            bpy.ops.mesh.select_all(action = 'SELECT')
            bpy.ops.mesh.quads_convert_to_tris()
            bpy.ops.mesh.flip_normals()
            bpy.ops.object.mode_set(mode = 'OBJECT')
            bpy.ops.object.rotation_apply()
            
            ## objectName
            self.writeToFile("s", o.name)
            ## objectParent
            self.writeToFile("s", "")

            ## materialIndex
            materialId = materialsIdList.index(o.material_slots[0].name)
            self.writeToFile("H", materialId)

            ## object position
            self.writeToFile("f", o.location[0])
            self.writeToFile("f", o.location[1])
            self.writeToFile("f", o.location[2])

            ## object rotation
            self.writeToFile("f", o.rotation_quaternion[1])
            self.writeToFile("f", o.rotation_quaternion[2])
            self.writeToFile("f", o.rotation_quaternion[3])
            self.writeToFile("f", o.rotation_quaternion[0])

            ## object scale
            self.writeToFile("f", 1.0)
            self.writeToFile("f", 1.0)
            self.writeToFile("f", 1.0)

            ## objectNoCollision
            self.writeToFile("B", 0)
            ## objectNoRender
            self.writeToFile("B", 0)
            ## objectLightObject
            self.writeToFile("B", 0)

            vertex = o.data.vertices
            faces = o.data.faces

            ## objectVertexAmount
            self.writeToFile("H", len(vertex))
            ## objectFaceAmount
            self.writeToFile("H", len(faces))

            ## objectLOD
            self.writeToFile("B", 0)

            ## objectWeights
            objectWeights = 0
            self.writeToFile("B", objectWeights)

            vertexUVs = []

            for v in vertex:
                vertexUVs.append(v)

            ## If there is no UVs, then automatically generate some.
            if len(o.data.uv_textures) == 0:
                bpy.context.scene.objects.active = o
                bpy.ops.object.mode_set(mode = 'EDIT')
                bpy.ops.uv.unwrap(method = 'ANGLE_BASED', fill_holes = True, correct_aspect = True)
                bpy.ops.object.mode_set(mode = 'OBJECT')

            for i, face in enumerate(o.data.uv_textures.active.data):
                vertexUVs[faces[i].vertices[0]] = face.uv1
                vertexUVs[faces[i].vertices[1]] = face.uv2
                vertexUVs[faces[i].vertices[2]] = face.uv3

            for i, v in enumerate(vertex):
                ## vertexPosition
                self.writeToFile("f", v.co[0])
                self.writeToFile("f", v.co[2])
                self.writeToFile("f", v.co[1])

                ## vertexNormal
                self.writeToFile("f", v.normal[0])
                self.writeToFile("f", v.normal[1])
                self.writeToFile("f", v.normal[2])

                ## vertexTextureCoords
                self.writeToFile("f", vertexUVs[i][0])
                self.writeToFile("f", -(vertexUVs[i][1]))

                ## vertexTextureCoords2
                self.writeToFile("f", 0.1)
                self.writeToFile("f", -0.1)

            for fa in faces:
                ## face index
                self.writeToFile("H", fa.vertices[0])
                self.writeToFile("H", fa.vertices[1])
                self.writeToFile("H", fa.vertices[2])

            if objectWeights == True:
                pass
                ## objectWeights

            bpy.ops.object.mode_set(mode = 'EDIT')
            bpy.ops.mesh.select_all(action = 'SELECT')
            bpy.ops.mesh.flip_normals()
            bpy.ops.object.mode_set(mode = 'OBJECT')

        ## Close the S3D file
        self.closeFile()
