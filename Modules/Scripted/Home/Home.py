from pathlib import Path
import os

import qt

import slicer
from slicer.ScriptedLoadableModule import (
    ScriptedLoadableModule,
    ScriptedLoadableModuleLogic,
    ScriptedLoadableModuleWidget,
)
from slicer.util import VTKObservationMixin

import SlicerCustomAppUtilities

# Import to ensure the files are available through the Qt resource system
from Resources import HomeResources

def print_message():
    print("This special version of OpenLIFU is patched to work with the SlicerOpenLIFU v1.19.0+legacy.io which is patched to work with the openlifu-python tag v0.20.0+legacy.io.0.9.0 which is essentially just openlifu v0.20.0 with the io module reverted to the v0.9.0 state.")
class Home(ScriptedLoadableModule):
    """The home module allows to orchestrate and style the overall application workflow.

    It is a "special" module in the sense that its role is to customize the application and
    coordinate a workflow between other "regular" modules.

    Associated widget and logic are not intended to be initialized multiple times.
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Home"
        self.parent.categories = [""]
        self.parent.dependencies = []
        self.parent.contributors = ["Sam Horvath (Kitware Inc.)", "Jean-Christophe Fillion-Robin (Kitware Inc.)"]
        self.parent.helpText = """This module orchestrates and styles the overall application workflow."""
        self.parent.helpText += self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = """..."""  # replace with organization, grant and thanks.

        # Force start guided mode once the styling and UI modifications are complete
        def start_guided_mode():
            openLIFUHomeLogic = slicer.util.getModuleLogic("OpenLIFUHome")
            openLIFUHomeLogic.start_guided_mode()
        slicer.app.connect("startupCompleted()", start_guided_mode)

        # Force start user account mode
        def start_user_account_mode():
            openLIFULoginLogic = slicer.util.getModuleLogic("OpenLIFULogin")
            openLIFULoginLogic.start_user_account_mode()
        slicer.app.connect("startupCompleted()", start_user_account_mode)

        def ensure_database_exists_and_attempt_connect():
            openLIFUDatabaseWidget = slicer.util.getModuleWidget("OpenLIFUDatabase")
            openLIFUDatabaseLogic = slicer.util.getModuleLogic("OpenLIFUDatabase")

            # 1) Check if the path was set to something. If the setting points
            # to a directory that exists and is an openlifu database, we attempt
            # to connect silently and then return
            qsettings = qt.QSettings()
            qsettings.beginGroup("OpenLIFU")
            db_setting = qsettings.value("databaseDirectory", "")
            qsettings.endGroup()
            
            db_setting = Path(db_setting)
            if db_setting.exists() and db_setting.is_dir() and openLIFUDatabaseLogic.path_is_openlifu_database_root(db_setting):
                openLIFUDatabaseWidget.onLoadDatabaseClicked(checked=True)
                return

            # 2) Check if the default location has a database. If it does, we
            # set the qsetting back to default, and then we return
            db_default = openLIFUDatabaseLogic.get_database_destination()
            if db_default.exists() and db_default.is_dir() and openLIFUDatabaseLogic.path_is_openlifu_database_root(db_default):
                openLIFUDatabaseLogic.getParameterNode().databaseDirectory = Path(db_default)
                openLIFUDatabaseWidget.onLoadDatabaseClicked(checked=True)
                return

            # 3) If nothing above is satisfied, we ask if the user wants to
            # create a new database directory (in the default location)
            reply = qt.QMessageBox.question(slicer.util.mainWindow(), "Initialize Confirmation", f"An openlifu database was not found in {db_default}.\nWould you like to initialize one?", qt.QMessageBox.Yes | qt.QMessageBox.No)
            if reply == qt.QMessageBox.No:
                return  # don't do anything. The admin can do things themself

            openLIFUDatabaseLogic.copy_preinitialized_database(db_default)
            openLIFUDatabaseLogic.getParameterNode().databaseDirectory = Path(db_default)
            openLIFUDatabaseWidget.onLoadDatabaseClicked(checked=True)

        slicer.app.connect("startupCompleted()", ensure_database_exists_and_attempt_connect)

        def configure_views():
            threeDController = slicer.app.layoutManager().threeDWidget(0).threeDController()
            threeDController.setBlackBackground()
            threeDController.set3DAxisVisible(False)
            threeDController.set3DAxisLabelVisible(False)

            for sliceNode in slicer.util.getNodesByClass("vtkMRMLSliceNode"):
                sliceNode.SliceEdgeVisibility3DOff()

        slicer.app.connect("startupCompleted()", configure_views)

        slicer.app.connect("startupCompleted()", lambda : slicer.util.getModuleLogic("OpenLIFUHome").workflow_jump_ahead())

        slicer.app.connect("startupCompleted()", print_message)

class HomeWidget(ScriptedLoadableModuleWidget, VTKObservationMixin):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        """Called when the application opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.__init__(self, parent)
        VTKObservationMixin.__init__(self)

    def setup(self):
        """Called when the application opens the module the first time and the widget is initialized."""
        ScriptedLoadableModuleWidget.setup(self)

        # Load widget from .ui file (created by Qt Designer)
        self.uiWidget = slicer.util.loadUI(self.resourcePath("UI/Home.ui"))
        self.layout.addWidget(self.uiWidget)
        self.ui = slicer.util.childWidgetVariables(self.uiWidget)

        # Remove unneeded UI elements
        self.modifyWindowUI()

        # Create logic class
        self.logic = HomeLogic()

        # Setup scene defaults
        self.setupNodes()

        # Dark palette does not propagate on its own?
        self.uiWidget.setPalette(slicer.util.mainWindow().style().standardPalette())

        self.setCustomUIVisible(True)

        # Apply style
        self.applyApplicationStyle()

        # Hide widgets that should be hidden in guided mode
        # This shouldn't need to be done because we already enabled guided mode above!
        # See https://github.com/OpenwaterHealth/OpenLIFU-app/issues/20
        # This is a terrible way to fix it, but it's our patch solution for now.
        # For me, even setting this timer to 1ms works! But without a timer it doesn't work.
        qt.QTimer.singleShot(500, lambda : slicer.util.getModuleLogic("OpenLIFUHome").workflow.enforceGuidedModeVisibility(True))

        # Call routine that ends up showing login module banners
        qt.QTimer.singleShot(1, lambda : slicer.util.getModuleWidget('OpenLIFULogin').onParameterNodeModified(None, None))

    def setupNodes(self):
        self.logic.setup3DView()
        self.logic.setupSliceViewers()

    def cleanup(self):
        """Called when the application closes and the module widget is destroyed."""
        pass

    def setSlicerUIVisible(self, visible):
        slicer.util.setDataProbeVisible(visible)
        slicer.util.setMenuBarsVisible(visible, ignore=["MainToolBar", "ViewToolBar"])
        slicer.util.setModuleHelpSectionVisible(visible)
        slicer.util.setModulePanelTitleVisible(visible)
        slicer.util.setPythonConsoleVisible(visible)
        slicer.util.setApplicationLogoVisible(visible)
        keepToolbars = [
            slicer.util.findChild(slicer.util.mainWindow(), "MainToolBar"),
            slicer.util.findChild(slicer.util.mainWindow(), "ViewToolBar"),
            slicer.util.findChild(slicer.util.mainWindow(), "CustomToolBar"),
        ]
        slicer.util.setToolbarsVisible(visible, keepToolbars)

    def modifyWindowUI(self):

        # Custom toolbar
        mainToolBar = slicer.util.findChild(slicer.util.mainWindow(), "MainToolBar")
        self.CustomToolBar = qt.QToolBar("CustomToolBar")
        self.CustomToolBar.name = "CustomToolBar"
        slicer.util.mainWindow().insertToolBar(mainToolBar, self.CustomToolBar)

        # Settings dialog
        gearIcon = qt.QIcon(self.resourcePath("Icons/Gears.png"))
        self.settingsAction = self.CustomToolBar.addAction(gearIcon, "")
        self.settingsDialog = slicer.util.loadUI(self.resourcePath("UI/Settings.ui"))
        self.settingsUI = slicer.util.childWidgetVariables(self.settingsDialog)
        self.settingsUI.CustomUICheckBox.toggled.connect(self.setCustomUIVisible)
        self.settingsUI.CustomStyleCheckBox.toggled.connect(self.toggleStyle)
        self.settingsAction.triggered.connect(self.raiseSettings)

    def toggleStyle(self, visible):
        if visible:
            self.applyApplicationStyle()
        else:
            slicer.app.styleSheet = ""

    def raiseSettings(self, unused):
        self.settingsDialog.exec()

    def setCustomUIVisible(self, visible):
        self.setSlicerUIVisible(not visible)

    def applyApplicationStyle(self):
        SlicerCustomAppUtilities.applyStyle([slicer.app], self.resourcePath("Home.qss"))


class HomeLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    Uses ScriptedLoadableModuleLogic base class, available at:
    https://github.com/Slicer/Slicer/blob/main/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def run(self, inputVolume, outputVolume, imageThreshold, enableScreenshots=0):
        """
        Run the actual algorithm
        """
        pass

    def setup3DView(self):
        layoutManager = slicer.app.layoutManager()
        # layoutManager.setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutOneUp3DView)
        # controller = slicer.app.layoutManager().threeDWidget(0).threeDController()
        # controller.setBlackBackground()
        # controller.set3DAxisVisible(False)
        # controller.set3DAxisLabelVisible(False)
        # controller.setOrientationMarkerType(3)  # Axis marker
        # controller.setStyleSheet("background-color: #000000")

    def setupSliceViewers(self):
        for name in slicer.app.layoutManager().sliceViewNames():
            sliceWidget = slicer.app.layoutManager().sliceWidget(name)
            self.setupSliceViewer(sliceWidget)

    def setupSliceViewer(self, sliceWidget):
        controller = sliceWidget.sliceController()
        # controller.setStyleSheet("background-color: #000000")
        # controller.sliceViewLabel = ""
        # slicer.util.findChild(sliceWidget, "PinButton").visible = False
        # slicer.util.findChild(sliceWidget, "ViewLabel").visible = False
        # slicer.util.findChild(sliceWidget, "FitToWindowToolButton").visible = False
        # slicer.util.findChild(sliceWidget, "SliceOffsetSlider").spinBoxVisible = False
