set(proj python-openlifu-environment-tools)

set(${proj}_DEPENDENCIES python python-pip)
ExternalProject_Include_Dependencies(${proj} PROJECT_VAR proj DEPENDS_VAR ${proj}_DEPENDENCIES)

set(_requirements_file
  "${CMAKE_CURRENT_LIST_DIR}/python-openlifu-environment-tools-requirements.txt"
  )
set(_provision_script
  "${CMAKE_CURRENT_LIST_DIR}/ProvisionPythonEnvironmentTools.cmake"
  )
set(OPENLIFU_PYTHON_ENVIRONMENT_TOOLS_DIR
  "${CMAKE_BINARY_DIR}/${proj}-install"
  )
file(SHA256
  "${_requirements_file}"
  OPENLIFU_PYTHON_ENVIRONMENT_TOOLS_LOCK_HASH
  )
mark_as_superbuild(
  OPENLIFU_PYTHON_ENVIRONMENT_TOOLS_DIR:PATH
  OPENLIFU_PYTHON_ENVIRONMENT_TOOLS_LOCK_HASH:STRING
  )

ExternalProject_Add(${proj}
  ${${proj}_EP_ARGS}
  DOWNLOAD_COMMAND ""
  SOURCE_DIR "${CMAKE_BINARY_DIR}/${proj}"
  BUILD_IN_SOURCE 1
  CONFIGURE_COMMAND ""
  BUILD_COMMAND ""
  INSTALL_COMMAND ""
  DEPENDS
    ${${proj}_DEPENDENCIES}
  )

ExternalProject_Add_Step(${proj} provision
  COMMAND
    "${CMAKE_COMMAND}"
      "-DPYTHON_EXECUTABLE:FILEPATH=${PYTHON_EXECUTABLE}"
      "-DREQUIREMENTS_FILE:FILEPATH=${_requirements_file}"
      "-DTOOL_DIR:PATH=${OPENLIFU_PYTHON_ENVIRONMENT_TOOLS_DIR}"
      "-DALLOWED_ROOT:PATH=${CMAKE_BINARY_DIR}"
      -P "${_provision_script}"
  COMMENT "Provisioning optional CycloneDX environment tools"
  DEPENDEES configure
  DEPENDERS build
  DEPENDS
    "${_requirements_file}"
    "${_provision_script}"
  )

add_custom_target(OpenLIFUProvisionPythonEnvironmentTools
  COMMAND
    "${CMAKE_COMMAND}"
      "-DPYTHON_EXECUTABLE:FILEPATH=${PYTHON_EXECUTABLE}"
      "-DREQUIREMENTS_FILE:FILEPATH=${_requirements_file}"
      "-DTOOL_DIR:PATH=${OPENLIFU_PYTHON_ENVIRONMENT_TOOLS_DIR}"
      "-DALLOWED_ROOT:PATH=${CMAKE_BINARY_DIR}"
      -P "${_provision_script}"
  COMMENT "Retrying optional CycloneDX environment tool provisioning"
  VERBATIM
  )
add_dependencies(OpenLIFUProvisionPythonEnvironmentTools python-pip)
