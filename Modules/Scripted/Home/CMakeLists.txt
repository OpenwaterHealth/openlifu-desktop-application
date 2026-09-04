#-----------------------------------------------------------------------------
set(MODULE_NAME Home)

#-----------------------------------------------------------------------------
set(MODULE_PYTHON_SCRIPTS
  ${MODULE_NAME}.py
  HomeLib/__init__.py
  HomeLib/update_check.py
  )

set(MODULE_PYTHON_RESOURCES
  Resources/Icons/${MODULE_NAME}.png
  Resources/Icons/Gears.png
  Resources/Icons/ArrowDown.png
  Resources/Icons/ArrowUp.png
  Resources/UI/${MODULE_NAME}.ui
  Resources/UI/Settings.ui
  Resources/Home.qss
  )

slicerFunctionAddPythonQtResources(MODULE_PYTHON_QRC_RESOURCES
  Resources/${MODULE_NAME}.qrc
  )

#-----------------------------------------------------------------------------
slicerMacroBuildScriptedModule(
  NAME ${MODULE_NAME}
  SCRIPTS ${MODULE_PYTHON_SCRIPTS} ${MODULE_PYTHON_QRC_RESOURCES}
  RESOURCES ${MODULE_PYTHON_RESOURCES}
  )

#-----------------------------------------------------------------------------
if(BUILD_TESTING)
  slicer_add_python_unittest(
    SCRIPT ${CMAKE_CURRENT_SOURCE_DIR}/Testing/Python/test_update_check.py
    SLICER_ARGS --no-main-window --disable-modules
    TESTNAME_PREFIX nomainwindow_
    )
endif()

#-----------------------------------------------------------------------------
set(_download_assets_script "${CMAKE_CURRENT_BINARY_DIR}/openlifu_download_assets.py")

file(WRITE ${_download_assets_script} [==[
import openlifu.util.assets
openlifu.util.assets.download_and_install_modnet()
openlifu.util.assets.download_and_install_kwave_assets()
]==])

set(_download_assets_sentinel_script "${CMAKE_CURRENT_BINARY_DIR}/openlifu_download_assets.done")

add_custom_command(
  DEPENDS
    OpenLIFUConfigureLauncher
    ${_download_assets_script}
  OUTPUT
    ${_download_assets_sentinel_script}
  COMMAND ${PYTHON_EXECUTABLE} ${_download_assets_script}
  COMMAND ${CMAKE_COMMAND} -E touch ${_download_assets_sentinel_script}
  COMMENT "Downloading external assets needed by openlifu"
)

add_custom_target(OpenLIFUDownloadAssets ALL
  DEPENDS
    ${_download_assets_sentinel_script}
)
