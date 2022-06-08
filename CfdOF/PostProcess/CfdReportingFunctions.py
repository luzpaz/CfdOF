# ***************************************************************************
# *                                                                         *
# *   Copyright (c) 2022 Jonathan Bergh <bergh.jonathan@gmail.com>          *
# *   Copyright (c) 2022 Oliver Oxtoby <oliveroxtoby@gmail.com>             *
# *                                                                         *
# *   This program is free software: you can redistribute it and/or modify  *
# *   it under the terms of the GNU Lesser General Public License as        *
# *   published by the Free Software Foundation, either version 3 of the    *
# *   License, or (at your option) any later version.                       *
# *                                                                         *
# *   This program is distributed in the hope that it will be useful,       *
# *   but WITHOUT ANY WARRANTY; without even the implied warranty of        *
# *   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the         *
# *   GNU Lesser General Public License for more details.                   *
# *                                                                         *
# *   You should have received a copy of the GNU Lesser General Public      *
# *   License along with this program.  If not,                             *
# *   see <https://www.gnu.org/licenses/>.                                  *
# *                                                                         *
# ***************************************************************************

from __future__ import print_function

import FreeCAD
import FreeCADGui
from pivy import coin
from PySide import QtCore
from CfdOF import CfdTools
from CfdOF.CfdTools import addObjectProperty
import os

# Constants
OBJECT_NAMES = ["Force", "ForceCoefficients", "Probes"]
OBJECT_DESCRIPTIONS = ["Calculate forces on patches", "Calculate force coefficients from patches",
    "Sample fields at specified locations"]

# GUI
FUNCTIONS_UI = [0, 0, 1]
FORCES_UI = [[True, False, True],    # Forces
             [True, True, True, ]]   # Force coefficients


def makeCfdReportingFunctions(name="ReportingFunction"):
    obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", name)
    _CfdReportingFunctions(obj)
    if FreeCAD.GuiUp:
        _ViewProviderCfdReportingFunctions(obj.ViewObject)
    return obj


class _CommandCfdReportingFunctions:
    def GetResources(self):
        icon_path = os.path.join(CfdTools.getModulePath(), "Gui", "Icons", "monitor.svg")
        return {'Pixmap': icon_path,
                'MenuText': QtCore.QT_TRANSLATE_NOOP("Cfd_ReportingFunctions",
                                                     "Reporting function"),
                'ToolTip': QtCore.QT_TRANSLATE_NOOP("Cfd_ReportingFunctions",
                                                    "Create a reporting function for the current case")}

    def IsActive(self):
        return CfdTools.getActiveAnalysis() is not None     # Same as for boundary condition commands

    def Activated(self):
        FreeCAD.ActiveDocument.openTransaction("Create CfdReportingFunctions object")
        FreeCADGui.doCommand("from CfdOF.PostProcess import CfdReportingFunctions")
        FreeCADGui.doCommand("from CfdOF import CfdTools")
        FreeCADGui.doCommand("CfdTools.getActiveAnalysis().addObject(CfdReportingFunctions.makeCfdReportingFunctions())")
        FreeCADGui.ActiveDocument.setEdit(FreeCAD.ActiveDocument.ActiveObject.Name)


class _CfdReportingFunctions:
    """ CFD Function objects properties """

    def __init__(self, obj):
        self.Type = "ReportingFunction"
        self.Object = obj
        obj.Proxy = self
        self.initProperties(obj)

    def initProperties(self, obj):

        # Setup and utility
        addObjectProperty(obj, 'ReportingFunctionType', OBJECT_NAMES, "App::PropertyEnumeration", "",
                          "Type of reporting function")

        addObjectProperty(obj, 'Patch', None, "App::PropertyLink", "Function object",
                          "Patch on which to create the function object")

        # Forces
        addObjectProperty(obj, 'ReferenceDensity', '1 kg/m^3', "App::PropertyQuantity", "Forces",
                          "Reference density")
        addObjectProperty(obj, 'ReferencePressure', '0 Pa', "App::PropertyPressure", "Forces",
                          "Reference pressure")
        addObjectProperty(obj, 'CentreOfRotation', FreeCAD.Vector(0, 0, 0), "App::PropertyPosition", "Forces",
                          "Centre of rotation")
        addObjectProperty(obj, 'WriteFields', False, "App::PropertyBool", "Forces",
                          "Whether to write output fields")

        # Force coefficients
        addObjectProperty(obj, 'Lift', FreeCAD.Vector(1, 0, 0), "App::PropertyVector", "Force coefficients",
                          "Lift direction (x component)")

        addObjectProperty(obj, 'Drag', FreeCAD.Vector(0, 1, 0), "App::PropertyVector", "Force coefficients",
                          "Drag direction")

        addObjectProperty(obj, 'Pitch', FreeCAD.Vector(0, 0, 1), "App::PropertyVector", "Force coefficients",
                          "Centre of pitch")

        addObjectProperty(obj, 'MagnitudeUInf', '1 m/s', "App::PropertyQuantity", "Force coefficients",
                          "Freestream velocity magnitude")
        addObjectProperty(obj, 'LengthRef', '1 m', "App::PropertyQuantity", "Force coefficients",
                          "Coefficient length reference")
        addObjectProperty(obj, 'AreaRef', '1 m^2', "App::PropertyQuantity", "Force coefficients",
                          "Coefficient area reference")

        # Spatial binning
        addObjectProperty(obj, 'NBins', 0, "App::PropertyInteger", "Forces",
                          "Number of bins")
        addObjectProperty(obj, 'Direction', FreeCAD.Vector(1, 0, 0), "App::PropertyVector", "Forces",
                          "Binning direction")
        addObjectProperty(obj, 'Cumulative', True, "App::PropertyBool", "Forces",
                          "Cumulative")

        # Probes
        addObjectProperty(obj, 'SampleFieldName', "p", "App::PropertyString", "Probes",
                          "Name of the field to sample")

        addObjectProperty(obj, 'ProbePosition', FreeCAD.Vector(0, 0, 0), "App::PropertyPosition", "Probes",
                          "Location of the probe sample location")


    def onDocumentRestored(self, obj):
        self.initProperties(obj)

    def execute(self, obj):
        pass

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


class _ViewProviderCfdReportingFunctions:
    """
    A View Provider for the CfdReportingFunctions object
    """
    def __init__(self, vobj):
        vobj.Proxy = self
        self.taskd = None

    def getIcon(self):
        icon_path = os.path.join(CfdTools.getModulePath(), "Gui", "Icons", "monitor.svg")
        return icon_path

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object
        self.standard = coin.SoGroup()
        vobj.addDisplayMode(self.standard, "Standard")
        #self.ViewObject.Transparency = 95
        return

    def getDisplayModes(self, obj):
        modes = []
        return modes

    def getDefaultDisplayMode(self):
        return "Shaded"

    def setDisplayMode(self,mode):
        return mode

    def updateData(self, obj, prop):
        analysis_obj = CfdTools.getParentAnalysisObject(obj)
        if analysis_obj and not analysis_obj.Proxy.loading:
            analysis_obj.NeedsCaseRewrite = True

    def onChanged(self, vobj, prop):
        CfdTools.setCompSolid(vobj)
        return

    def doubleClicked(self, vobj):
        doc = FreeCADGui.getDocument(vobj.Object.Document)
        if not doc.getInEdit():
            doc.setEdit(vobj.Object.Name)
        else:
            FreeCAD.Console.PrintError('Task dialog already active\n')
            FreeCADGui.Control.showTaskView()
        return True

    def setEdit(self, vobj, mode):
        analysis_object = CfdTools.getParentAnalysisObject(self.Object)
        if analysis_object is None:
            CfdTools.cfdErrorBox("Reporting function must have a parent analysis object")
            return False

        from CfdOF.PostProcess import TaskPanelCfdReportingFunctions
        import importlib
        importlib.reload(TaskPanelCfdReportingFunctions)
        taskd = TaskPanelCfdReportingFunctions.TaskPanelCfdReportingFunctions(self.Object)
        self.Object.ViewObject.show()
        taskd.obj = vobj.Object
        FreeCADGui.Control.showDialog(taskd)
        return True

    def unsetEdit(self, vobj, mode):
        FreeCADGui.Control.closeDialog()
        return

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None