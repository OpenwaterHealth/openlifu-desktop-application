#============================================================================
#
# Copyright (c) Kitware, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0.txt
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#============================================================================

project(OpenLIFUApp)

include(SlicerMacroBuildApplication)

# --------------------------------------------------------------------------
# Properties
# --------------------------------------------------------------------------
SlicerReadApplicationProperties()

# --------------------------------------------------------------------------
# Folder
# --------------------------------------------------------------------------
set(${PROJECT_NAME}_FOLDER "App-${PROJECT_NAME}")

# --------------------------------------------------------------------------
# Application library
# --------------------------------------------------------------------------
set(APPLIB_NAME "q${PROJECT_NAME}")

set(APPLIB_SRCS
  qOpenLIFUAppMainWindow.cxx
  qOpenLIFUAppMainWindow.h
  Widgets/qAppStyle.cxx
  Widgets/qAppStyle.h
  )

set(APPLIB_MOC_SRCS
  qOpenLIFUAppMainWindow.h
  Widgets/qAppStyle.h
  )

set(APPLIB_UI_SRCS
  )

set(APPLIB_RESOURCES
  Resources/App.qrc
  )

slicerMacroBuildAppLibrary(
  NAME ${APPLIB_NAME}
  DESCRIPTION_SUMMARY ${${PROJECT_NAME}_DESCRIPTION_SUMMARY}
  DESCRIPTION_FILE ${${PROJECT_NAME}_DESCRIPTION_FILE}
  APPLICATION_NAME ${${PROJECT_NAME}_APPLICATION_NAME}
  EXPORT_DIRECTIVE "Q_OPENLIFU_APP_EXPORT"
  FOLDER ${${PROJECT_NAME}_FOLDER}
  SRCS ${APPLIB_SRCS}
  MOC_SRCS ${APPLIB_MOC_SRCS}
  UI_SRCS ${APPLIB_UI_SRCS}
  RESOURCES ${APPLIB_RESOURCES}
  )

# --------------------------------------------------------------------------
# Application executable
# --------------------------------------------------------------------------

# Configure launcher only for the main application
set(extra_args)
if(${PROJECT_NAME} STREQUAL ${Slicer_MAIN_PROJECT})
  set(extra_args CONFIGURE_LAUNCHER)
endif()

set(APP_SRCS
  Main.cxx
  )

set(APP_TARGET_LIBRARIES ${APPLIB_NAME})

slicerMacroBuildApplication(
  NAME ${PROJECT_NAME}
  APPLICATION_NAME ${${PROJECT_NAME}_APPLICATION_NAME}
  LAUNCHER_SPLASHSCREEN_FILE ${${PROJECT_NAME}_LAUNCHER_SPLASHSCREEN_FILE}
  APPLE_ICON_FILE ${${PROJECT_NAME}_APPLE_ICON_FILE}
  WIN_ICON_FILE ${${PROJECT_NAME}_WIN_ICON_FILE}
  LICENSE_FILE ${${PROJECT_NAME}_LICENSE_FILE}
  FOLDER ${${PROJECT_NAME}_FOLDER}
  SRCS ${APP_SRCS}
  TARGET_LIBRARIES ${APP_TARGET_LIBRARIES}
  TARGET_NAME_VAR "APP_TARGET_NAME"
  DEFAULT_SETTINGS_FILE Resources/Settings/DefaultSettings.ini
  ${extra_args}
  )

# On Windows, embed the application icon into OpenLIFUApp-real.exe using
# CTKResEdit as a post-build step, mirroring how the launcher (OpenLIFU.exe)
# already gets its icon. Without this, Windows populates its icon cache with
# the generic default icon after the first run, causing subsequent runs to
# display the wrong icon in the taskbar/system tray.
if(WIN32)
  add_custom_target(${APP_TARGET_NAME}UpdateAppIcon ALL
    COMMAND
      ${CTKResEdit_EXECUTABLE}
        --update-resource-ico "$<TARGET_FILE:${APP_TARGET_NAME}>"
        IDI_ICON1 "${CMAKE_CURRENT_SOURCE_DIR}/Resources/Icons/DesktopIcon.ico"
    COMMENT "Updating icon in OpenLIFUApp-real.exe"
    )
  add_dependencies(${APP_TARGET_NAME}UpdateAppIcon ${APP_TARGET_NAME})
endif()
