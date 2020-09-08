
import FreeCAD,FreeCADGui, WebGui


class Hermes ( Workbench ):
    "Web workbench object"
    def __init__(self):
        self.__class__.Icon = FreeCAD.getResourceDir() + "Mod/Hermes/Resources/icons/hermes.png"
        self.__class__.MenuText = "Hermes"
        self.__class__.ToolTip = "Hermes"

    def Initialize(self):
        # load the module
        import HermesGui

        list = ["CreateWorkflow"]
        self.appendToolbar("HermesToolbar", list)


#    def GetClassName(self):
#        return "Hermes::Workbench"

Gui.addWorkbench(Hermes())



