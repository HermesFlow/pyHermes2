﻿# FreeCAD Part module
# (c) 2001 Juergen Riegel
#
# Part design module

# ***************************************************************************
# *   (c) Juergen Riegel (juergen.riegel@web.de) 2002                       *
# *                                                                         *
# *   This file is part of the FreeCAD CAx development system.              *
# *                                                                         *
#*   This program is free software; you can redistribute it and/or modify  *
#*   it under the terms of the GNU Lesser General Public License (LGPL)    *
#*   as published by the Free Software Foundation; either version 2 of     *
#*   the License, or (at your option) any later version.                   *
#*   for detail see the LICENCE text file.                                 *
#*                                                                         *
#*   FreeCAD is distributed in the hope that it will be useful,            *
#*   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
#*   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
#*   GNU Library General Public License for more details.                  *
#*                                                                         *
#*   You should have received a copy of the GNU Library General Public     *
#*   License along with FreeCAD; if not, write to the Free Software        *
#*   Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  *
#*   USA                                                                   *
#*                                                                         *
#*   Juergen Riegel 2002                                                   *
#***************************************************************************/

# import FreeCAD modules
import FreeCAD,FreeCADGui, WebGui
import HermesTools
from HermesTools import addObjectProperty
from PyQt5 import QtGui,QtCore

if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide import QtCore

import json
import pydoc

import HermesGeometryDefinerNode
from HermesBlockMesh import HermesBlockMesh



def makeNode(name, workflowObj, nodeId, nodeData):
    """ Create a Hermes Node object """

    test = pydoc.locate('HermesNode._HermesNode')
    # test = pydoc.locate('HermesGui._HermesNode')

    if test is None:
        FreeCAD.Console.PrintMessage("Not found\n")

    # Object with option to have children
    obj = FreeCAD.ActiveDocument.addObject("App::DocumentObjectGroupPython", name)
    #print ("HermesNode make node\n")

    #    # Object can not have children
    #    obj = FreeCAD.ActiveDocument.addObject("App::FeaturePython", name)

    # add Nodeobj(obj) as child of workflowObj
    workflowObj.addObject(obj)

    # ----------------dynamic find class--------------------

    # find the class of the node from the its type
    #nodecls = pydoc.locate("HermesGui." + nodeData["TypeFC"])
    nodecls = pydoc.locate("HermesNode." +'_'+ nodeData["TypeFC"])


    #    # if the class is not exist, create a new class
    #    if nodecls is None:
    #        nodecls = pydoc.locate("HermesGui.%s" % nodeData["TypeFC"])

    # call to the class
    if nodecls is not None:
        nodecls(obj, nodeId, nodeData, name)

        # ----------------static find class------------------
        # =============================================================================
        #     if nodeData["TypeFC"]=="webGui":
        #         _WebGuiNode(obj, nodeId,nodeData,name)
        #     elif nodeData["TypeFC"]=="GE":
        #         _GeometryDefinerNode(obj, nodeId,nodeData,name)
        #     else:
        #         _HermesNode(obj, nodeId,nodeData,name)
        # =============================================================================

        obj.Proxy.initializeFromJson(obj)

        if FreeCAD.GuiUp:
            _ViewProviderNode(obj.ViewObject)
    return obj

#**********************************************************************
class _CommandHermesNodeSelection:
    """ CFD physics selection command definition """

    def GetResources(self):
        ResourceDir = FreeCAD.getResourceDir() if list(FreeCAD.getResourceDir())[-1] == '/' else FreeCAD.getResourceDir() + "/"
        icon_path = ResourceDir + "Mod/Hermes/Resources/icons/NewNode.png"
        return {'Pixmap': icon_path,
                'MenuText': QtCore.QT_TRANSLATE_NOOP("Hermes_Node", "Hermes Node"),
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("Hermes_Node", "Creates new Hermes Node")}

    def IsActive(self):
        return HermesTools.getActiveHermes() is not None

    def Activated(self):
        FreeCAD.ActiveDocument.openTransaction("Choose appropriate Node")
        isPresent = False
        members = HermesTools.getActiveHermes().Group
        for i in members:
            if isinstance(i.Proxy, _HermesNode):
                FreeCADGui.activeDocument().setEdit(i.Name)
                isPresent = True

        # Allow to re-create if deleted
        if not isPresent:
            FreeCADGui.doCommand("")
            FreeCADGui.addModule("HermesNode")
            FreeCADGui.addModule("HermesTools")
            FreeCADGui.doCommand(
                "HermesTools.getActiveHermes().addObject(HermesNode.makeNode())")
            FreeCADGui.ActiveDocument.setEdit(FreeCAD.ActiveDocument.ActiveObject.Name)



if FreeCAD.GuiUp:
    FreeCADGui.addCommand('Hermes_Node', _CommandHermesNodeSelection())

#**********************************************************************
class _SlotHandler:
    """ Slot Handler """

    def __init__(self):
        pass

    def process(self, data):
        FreeCAD.Console.PrintMessage("Process Data\n" + str(data))


# =============================================================================
# Hermes Node class
# =============================================================================
class _HermesNode(_SlotHandler):
    """ The Hermes Node """

    #    def __init__(self, obj, nodeId,nodeData):
    def __init__(self, obj, nodeId, nodeData, name):

        obj.Proxy = self
        self.nodeId = nodeId
        self.nodeData = nodeData
        self.name = name
        self.initProperties(obj)

    def initializeFromJson(self, obj):

        # get list of properties from nodeData
        NodeProperties = self.nodeData["Properties"]

        # update the current value of all properties in  node object
        for x in NodeProperties:
            # get property'num' object ; num =1,2,3 ...
            propertyNum = NodeProperties[x]

            # get the prop parameter
            prop = propertyNum["prop"]

            # get the prop current_val
            current_val = propertyNum["current_val"]

            # get the current_val at the prop
            setattr(obj, prop, current_val)

        # additional properties RunOsCommand node
        if self.name == "RunOsCommand":

            # get the choosen methon
            method = getattr(obj, "ChooseMethod")

            # make read only the property that hasnt been choosen
            if method == "Commands list":
                obj.setEditorMode("batchFile", 1)  # Make read-only
            elif method == "batchFile":
                obj.setEditorMode("Commands", 1)  # Make read-only

    def initProperties(self, obj):

        # ^^^ Constant properties ^^^

        # References property - keeping the faces and part data attached to the GE obj
        addObjectProperty(obj, 'References', [], "App::PropertyPythonObject", "", "Boundary faces")

        # Node Id
        # Todo- is necessary?
        addObjectProperty(obj, "NodeId", "-1", "App::PropertyString", "Node Id", "Id of node",
                          4)  # the '4' hide the property

        # Type of the Object - (web/GE)
        addObjectProperty(obj, "Type", "-1", "App::PropertyString", "Node Type", "Type of node")
        obj.setEditorMode("Type", 1)  # Make read-only (2 = hidden)

        # Is Avtive property- Boolean -keep if obj has been activated (douuble clicked get active)
        addObjectProperty(obj, "IsActiveNode", False, "App::PropertyBool", "", "Active Node object in document")
        obj.setEditorMode("IsActiveNode", 1)  # Make read-only (2 = hidden)

        # link property - link to other object (beside parent)
        addObjectProperty(obj, "linkToOtherObjects", [], "App::PropertyLinkList", "Links", "Link to")

        # NodeDataString property - keep the json  node data as a string
        addObjectProperty(obj, "NodeDataString", "-1", "App::PropertyString", "NodeData", "Data of the node", 4)

        # Exportile property- get the directory path of where we want to export our files
        addObjectProperty(obj, "ExportNodeJSONFile", "", "App::PropertyPath", "IO", "Path to save Node JSON File")

        # RunWorkflow property - Run the workflow as a basic to luigi if change to true
        addObjectProperty(obj, "RunNodeWorkflow", False, "App::PropertyBool", "Run",
                          "Run the Node workflow as a basic to luigi")

        # RunLuigi property - Run luigi
        addObjectProperty(obj, "RunNodeLuigi", False, "App::PropertyBool", "Run", "Run Node luigi")

        # Update Values at the properties from nodeData
        obj.NodeId = self.nodeId
        nodeType = self.nodeData["TypeFC"]
        obj.Type = nodeType
        obj.Label = self.name  # automatically created with object.
        obj.setEditorMode("Label", 1)  # Make read-only
        obj.NodeDataString = json.dumps(self.nodeData)  # convert from json to string

        # ^^^^^ Properties from Json  ^^^

        # get Web node List of properties
        ListProperties = self.nodeData["Properties"]

        # Create each property from the list
        for x in ListProperties:
            # get property'num' ; num =1,2,3 ...
            propertyNum = ListProperties[x]

            # get needed parameters to create a property
            prop = propertyNum["prop"]
            init_val = propertyNum["init_val"]
            Type = propertyNum["type"]
            Heading = propertyNum["Heading"]
            tooltip = propertyNum["tooltip"]

            # add Object's Property
            addObjectProperty(obj, prop, init_val, Type, Heading, tooltip)

    def onDocumentRestored(self, obj):

        workflowObj = obj.getParentGroup()
        workflowObj.Proxy.nLastNodeId = "-1"

        # parse json data
        self.nodeData = json.loads(obj.NodeDataString)

        # when restored- initilaize properties
        self.initProperties(obj)

        FreeCAD.Console.PrintMessage("Node onDocumentRestored\n")

        if FreeCAD.GuiUp:
            _ViewProviderNode(obj.ViewObject)

    # just an example - not used
    def changeLabel(self):
        #        FreeCAD.Console.PrintMessage("\nChange Label\n")
        return

    def doubleClickedNode(self, obj):

        # get "workflowObj" from been parent of the node obj
        workflowObj = obj.getParentGroup()

        # backup last node and update "nLastNodeId" in Hermes workflow
        workflowObj.Proxy.updateLastNode(workflowObj, obj.NodeId)

        # update is active
        obj.IsActiveNode = True

        return

    def backupNodeData(self, obj):
        pass

    def UpdateNodePropertiesData(self, obj):
        # update the properties in the "nodeData"
        # use this func before exporting Json

        # get node List of properties
        ListProperties = self.nodeData["Properties"]

        for y in ListProperties:

            # get property'num' object ; num =1,2,3 ...
            propertyNum = ListProperties[y]

            # get the prop parameter
            prop = propertyNum["prop"]

            # get the Object Property current value from property object
            current_val = getattr(obj, prop)

            # update the value at the propertyNum[prop]
            if type(current_val) is not int and type(current_val) is not float and type(current_val) is not list:
                # In case of 'Quantity property' (velocity,length etc.), 'current_val' need to be export as a string
                propertyNum["current_val"] = str(current_val)

            else:
                propertyNum["current_val"] = current_val

            # update propertyNum in ListProperties
            ListProperties[y] = propertyNum

        # update ListProperties in nodeData
        self.nodeData["Properties"] = ListProperties

        # Update nodeData  at the NodeDataString by converting from json to string
        obj.NodeDataString = json.dumps(self.nodeData)

        return

    def RemoveNodeObj(self, obj):
        # remove NodeObj Children
        # use when importing new json file
        for child in obj.Group:
            obj.Document.removeObject(child.Name)

        return


# =============================================================================
#      "_ViewProviderNode" class
# =============================================================================
class _ViewProviderNode:
    """ A View Provider for the Hermes Node container object. """

    # =============================================================================
    #     General interface for all visual stuff in FreeCAD This class is used to
    #     generate and handle all around visualizing and presenting Node objects from
    #     the FreeCAD App layer to the user.
    # =============================================================================

    def __init__(self, vobj):
        vobj.Proxy = self
        self.NodeObjName = vobj.Object.Name
        self.NodeObjType = vobj.Object.Type

    def getIcon(self):
        # Define Resource dir end with ','
        ResourceDir = FreeCAD.getResourceDir() if list(FreeCAD.getResourceDir())[-1] == '/' else FreeCAD.getResourceDir() + "/"

        if self.NodeObjType == "WebGuiNode":
            icon_path = ResourceDir + "Mod/Hermes/Resources/icons/Web.png"
        elif self.NodeObjType == "GeometryDefinerNode":
            icon_path = ResourceDir + "Mod/Hermes/Resources/icons/GeometryDefiner.png"
        else:
            icon_path = ResourceDir + "Mod/Hermes/Resources/icons/NewNode.png"

        return icon_path

    def attach(self, vobj):
        self.ViewObject = vobj
        #        self.Object = vobj.Object
        self.bubbles = None

    def updateData(self, obj, prop):
        # We get here when the object of Node changes

        # Check if the JSONFile parameter changed and its not empty path
        # =============================================================================
        #         #not in use, just an example
        #         if (str(prop) == 'Label' and len(str(obj.Label)) > 0):
        #             obj.Proxy.changeLabel()
        #             return
        # =============================================================================

        if (str(prop) == 'ExportNodeJSONFile' and len(str(obj.ExportNodeJSONFile)) > 0):
            # get "workflowObj" from been parent of the node obj
            workflowObj = obj.getParentGroup()
            workflowObj.Proxy.prepareJsonVar(workflowObj, obj.Name)
            workflowObj.Proxy.saveJson(workflowObj, obj.ExportNodeJSONFile, obj.Label)
            obj.ExportNodeJSONFile = ''

        if (str(prop) == 'RunNodeWorkflow' and (obj.RunNodeWorkflow)):
            workflowObj = obj.getParentGroup()
            workflowObj.Proxy.prepareJsonVar(workflowObj, obj.Name)
            workflowObj.Proxy.RunworkflowCreation(workflowObj)

        if (str(prop) == 'RunNodeLuigi' and (obj.RunNodeLuigi)):
            workflowObj = obj.getParentGroup()
            workflowObj.Proxy.RunLuigiScript()

            # ----------------------------------------------------------------------------------

        # edit properties RunOsCommand node
        if str(prop) == "ChooseMethod" and obj.Name == "RunOsCommand":

            # get the choosen methon
            method = getattr(obj, "ChooseMethod")

            # make read only the property that hasnt been choosen, and read/write the one been choose
            if method == "Commands list":
                obj.setEditorMode("batchFile", 1)  # Make read-only
                obj.setEditorMode("Commands", 0)  # read/write


            elif method == "batchFile":
                obj.setEditorMode("Commands", 1)  # Make read-only
                obj.setEditorMode("batchFile", 0)  # read/write

    #    def onChanged(self,obj, vobj, prop):
    def onChanged(self, obj, prop):
        # not it use, just an example
        if (str(prop) == 'Label' and len(str(obj.Label)) > 0):
            obj.Proxy.changeLabel()
            return

    def doubleClicked(self, vobj):
        vobj.Object.Proxy.doubleClickedNode(vobj.Object)

    def __getstate__(self):

        # Create NodeObj using Object name
        NodeObj = FreeCAD.ActiveDocument.getObject(self.NodeObjName)

        # if node has been active - backup
        if NodeObj.IsActiveNode:
            NodeObj.Proxy.backupNodeData(NodeObj)

        # get the last updated NodeDataString
        getNodeString = NodeObj.NodeDataString

        # return an array with NodeObj name and the updated NodeDataString -
        # it will be recieved by "__setstate__" when opening the project
        return [self.NodeObjName, getNodeString]

    def __setstate__(self, state):

        #    #state - recieved from 'getstate', while saving the project "Hermesworkflow"
        #        type :array ,including 2 variebelles,
        #             state[0]= Name of the Node Object
        #             state[1]= nodeDataString - the last uppdated Json string before saving.

        NodeObjName = state[0]
        nodeDataString = state[1]

        # get Object using OBject name
        NodeObj = FreeCAD.ActiveDocument.getObject(NodeObjName)

        # update the nodeDataString at the NodeObj
        NodeObj.NodeDataString = nodeDataString

        return None


# =============================================================================
# #_WebGuiNode
# =============================================================================
class _WebGuiNode(_HermesNode):
    #    super().funcName(var1,var,2..) - allow to use the function of the Parent,
    #    and add current class functionalites

    def __init__(self, obj, nodeId, nodeData, name):
        super().__init__(obj, nodeId, nodeData, name)

    def doubleClickedNode(self, obj):
        super().doubleClickedNode(obj)

        self.selectNode(obj)

    def selectNode(self, obj):

        # get node WebGui- Scheme,uiScheme,FormData
        nodeWebGUI = self.nodeData["WebGui"]

        # Check if webGui is empty
        if not ((len(nodeWebGUI) == 0)):
            # define web address & pararmeters
            ResourceDir = FreeCAD.getResourceDir() if list(FreeCAD.getResourceDir())[-1] == '/' else FreeCAD.getResourceDir() + "/"
            path = ResourceDir + 'Mod/Hermes/Resources/jsonReactWebGui.html?parameters='
            address = 'file:///' + path

            # str JSON 'nodeWebGUI' using "dumps"
            parameters = json.dumps(nodeWebGUI)

            # open the jsonReact html page using the following command
            browser = WebGui.openSingleBrowser(address + parameters)
            sRegName = '0,' + self.name;
            browser.registerHandler(sRegName)

        return

    def process(self, data):

        UpdateWebGUI = data
        #        FreeCAD.Console.PrintMessage("WebGUI Process Data\n" + str(data))

        if (0 == len(UpdateWebGUI)):
            return

        # parse the 'UpdateWebGUI'
        UpdateWebGUIJson = json.loads(UpdateWebGUI)

        # update in our global json data the updated parsed 'WebGUI'
        # first update the node
        self.nodeData["WebGui"] = UpdateWebGUIJson

    #        formData=UpdateWebGUIJson["formData"]
    #        FreeCAD.Console.PrintMessage("----------------------------------------------------------------\n")
    #        FreeCAD.Console.PrintMessage("backup--nodedata.webgui['formData']="+str(formData)+"\n")

    def backupNodeData(self, obj):
        # backup the data of the last node pressed
        super().backupNodeData(obj)

        # then Update nodeData  at the NodeDataString by converting from json to string
        obj.NodeDataString = json.dumps(self.nodeData)


# =============================================================================
# #_GeometryDefinerNode
# =============================================================================
class _GeometryDefinerNode(_HermesNode):
    #    super().funcName(var1,var,2..) - allow to use the function of the Parent,
    #    and add current class functionalites

    def __init__(self, obj, nodeId, nodeData, name):
        super().__init__(obj, nodeId, nodeData, name)

    def initializeFromJson(self, obj):
        super().initializeFromJson(obj)

        # get Geometry Face types section from json
        GeometryFaceTypes = self.nodeData["GeometryFaceTypes"]

        # get the list of available Geometry Face types
        TypeList = GeometryFaceTypes["TypeList"]

        # get the list of Geometry Entities that has been saved
        GeometryEntityList = self.nodeData["GeometryEntityList"]

        # Loop all the Geometry Entities that has been saved (GE = GeometryEntity )
        for y in GeometryEntityList:
            # get GE'num' object ; num =1,2,3 ...
            GEnum = GeometryEntityList[y]

            # get Name,Type and Properties of the GE
            GEName = GEnum["Name"]
            GEType = GEnum["Type"]

            # Create the GE node
            GENodeObj = HermesGeometryDefinerNode.makeGENode('GEtemp', TypeList, GEnum, obj)

            # get the GE properties, and update their current value
            GEProperties = GEnum["Properties"]
            GENodeObj.Proxy.setCurrentPropertyGE(GENodeObj, GEProperties)

            # Update the faces attach to the GE (also create the parts)
            GENodeObj.Proxy.initFacesFromJson(GENodeObj)

            # get GE Name and update his Label property
            GEName = GEnum["Name"]
            GENodeObj.Label = GEName

            # get GE type and update his Type property
            GEType = GEnum["Type"]
            GENodeObj.Type = GEType

    def doubleClickedNode(self, obj):
        super().doubleClickedNode(obj)

        # create CGEDialogPanel Object
        geDialog = HermesGeometryDefinerNode.CGEDialogPanel(obj)

        # get GEtypes section from json
        GETypes = self.nodeData["GeometryFaceTypes"]

        # get the list of available GE types from GEtypes section
        TypeList = GETypes["TypeList"]

        # add the GE types to options at GE dialog
        for types in TypeList:
            geDialog.addGE(types)

        # update the first value to be showen in the comboBox
        geDialog.setCurrentGE(types[0])

        # add node Object name to the geDialog name
        geDialog.setCallingObject(obj.Name)

        # show the Dialog in FreeCAD
        FreeCADGui.Control.showDialog(geDialog)

    def backupNodeData(self, obj):
        super().backupNodeData(obj)
        # Update faceList in GeometryEntityList section to each Geometry Entity node
        for child in obj.Group:
            child.Proxy.UpdateFacesInJson(child)

    def UpdateNodePropertiesData(self, obj):
        super().UpdateNodePropertiesData(obj)

        # in case amount of GE has been changed
        # Create basic structure of a GeometryEntityList (string) in the length of Children's obj amount
        # structure example:
        # -- "GeometryEntityList":{
        # --     "GE1":{ },
        # --     "GE2":{ },
        # --     "GE3":{ }
        # --  }
        x = 1
        GEListStr = "{"
        for child in obj.Group:
            if (x > 1):
                GEListStr += ','
            childStr = '"GeometryDefiner' + str(x) + '":{}'
            GEListStr += childStr
            x = x + 1
        GEListStr += "}"

        # convert structure from string to json
        GeometryEntityList = json.loads(GEListStr)

        # loop all GE(Geometry Entities) objects in Nodeobj
        x = 1
        for child in obj.Group:
            # update current properties value of the GE-child
            child.Proxy.UpdateGENodePropertiesData(child)

            # get GE-child nodeDate from GENodeDataString property
            GEnodeData = json.loads(child.GENodeDataString)

            # get GE'node' object ; node =1,2,3 ...
            GEnode = 'GE' + str(x)

            # update the GE-child nodeDate in the Geometry Entity List section
            GeometryEntityList[BGEnode] = GEnodeData

            x = x + 1

        # update the Geometry Entity List section data in nodeData
        self.nodeData['GeometryEntityList'] = GeometryEntityList

        # Update nodeData  at the NodeDataString by converting from json to string
        obj.NodeDataString = json.dumps(self.nodeData)

        # update properties of the current node(before updated only the children)
        super().UpdateNodePropertiesData(obj)

        # update block mesh with its vertices and boundry
        HermesBlockMesh().updateJson(obj)


    def geDialogClosed(self, obj, GEtype):
        # call when created new GE node

        # Create basic structure of a GENodeData
        GENodeData = {
            "Name": "",
            "Type": "",
            "Properties": {}
        }

        # get the GE Type available from Json, and their list of properties
        GETypes = self.nodeData["GeometryFaceTypes"]
        TypeList = GETypes["TypeList"]
        TypeProperties = GETypes["TypeProperties"]

        # take the properties of the choosen GEtype from dialog
        GEJsonType = TypeProperties[GEtype]
        GEProperties = GEJsonType["Properties"]

        # update values in GENodeData structure
        GENodeData["Name"] = GEtype  # meaningful name is thr type
        GENodeData["Type"] = GEtype
        GENodeData["Properties"] = GEProperties

        # Create the GEObject
        GENodeObj = HermesGeometryDefinerNode.makeGENode('GEtemp', TypeList, GENodeData, obj)

        # get the References from the parent node to the the new GE child
        GENodeObj.References = obj.References
        # print(GENodeObj.References)

        # Empty the parent node References for further use
        obj.References = []

        return




