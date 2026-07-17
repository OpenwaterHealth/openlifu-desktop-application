if(NOT DEFINED PYTHON_EXECUTABLE OR NOT EXISTS "${PYTHON_EXECUTABLE}")
  message(FATAL_ERROR "PYTHON_EXECUTABLE must name the build-tree PythonSlicer launcher")
endif()
if(NOT DEFINED REQUIREMENTS_FILE OR NOT EXISTS "${REQUIREMENTS_FILE}")
  message(FATAL_ERROR "REQUIREMENTS_FILE must name the CycloneDX tool lock file")
endif()
if(NOT DEFINED TOOL_DIR OR NOT IS_ABSOLUTE "${TOOL_DIR}")
  message(FATAL_ERROR "TOOL_DIR must be an absolute path")
endif()
if(NOT DEFINED ALLOWED_ROOT OR NOT IS_ABSOLUTE "${ALLOWED_ROOT}")
  message(FATAL_ERROR "ALLOWED_ROOT must be an absolute path")
endif()
if(IS_SYMLINK "${TOOL_DIR}")
  message(FATAL_ERROR "TOOL_DIR must not be a symbolic link")
endif()

cmake_path(ABSOLUTE_PATH TOOL_DIR NORMALIZE OUTPUT_VARIABLE _tool_dir)
cmake_path(ABSOLUTE_PATH ALLOWED_ROOT NORMALIZE OUTPUT_VARIABLE _allowed_root)
cmake_path(IS_PREFIX _allowed_root "${_tool_dir}" NORMALIZE _tool_dir_is_allowed)
if(NOT _tool_dir_is_allowed OR _tool_dir STREQUAL _allowed_root)
  message(FATAL_ERROR "TOOL_DIR must be a child of ALLOWED_ROOT")
endif()
set(TOOL_DIR "${_tool_dir}")

set(_ready_marker "${TOOL_DIR}/.openlifu-environment-tools-ready")
file(SHA256 "${REQUIREMENTS_FILE}" _requirements_hash)

set(_verify_code [=[
import importlib
import importlib.metadata
import sys

sys.path.insert(0, sys.argv[1])
if importlib.metadata.version("cyclonedx-bom") != "7.3.0":
    raise RuntimeError("unexpected cyclonedx-bom version")
importlib.import_module("cyclonedx_py")
]=])

set(_marker_matches FALSE)
if(EXISTS "${_ready_marker}")
  file(READ "${_ready_marker}" _marker_hash)
  string(STRIP "${_marker_hash}" _marker_hash)
  if("${_marker_hash}" STREQUAL "${_requirements_hash}")
    set(_marker_matches TRUE)
  endif()
endif()

if(_marker_matches)
  execute_process(
    COMMAND "${PYTHON_EXECUTABLE}" -I -c "${_verify_code}" "${TOOL_DIR}"
    RESULT_VARIABLE _verify_result
    OUTPUT_QUIET
    ERROR_QUIET
    )
  if(_verify_result EQUAL 0)
    message(STATUS "CycloneDX environment tools are ready in ${TOOL_DIR}")
    return()
  endif()
endif()

file(REMOVE_RECURSE "${TOOL_DIR}")
file(MAKE_DIRECTORY "${TOOL_DIR}")

execute_process(
  COMMAND
    "${PYTHON_EXECUTABLE}" -m pip --disable-pip-version-check install
      --no-input
      --ignore-installed
      --only-binary=:all:
      --require-hashes
      --target "${TOOL_DIR}"
      --requirement "${REQUIREMENTS_FILE}"
  RESULT_VARIABLE _install_result
  OUTPUT_VARIABLE _install_output
  ERROR_VARIABLE _install_error
  )

if(NOT _install_result EQUAL 0)
  file(REMOVE_RECURSE "${TOOL_DIR}")
  message(WARNING
    "Could not provision the optional CycloneDX environment tools. "
    "The pip inventory will still be generated, but the CycloneDX artifact "
    "will be omitted until provisioning succeeds.\n"
    "${_install_output}${_install_error}"
    )
  return()
endif()

execute_process(
  COMMAND "${PYTHON_EXECUTABLE}" -I -c "${_verify_code}" "${TOOL_DIR}"
  RESULT_VARIABLE _verify_result
  OUTPUT_VARIABLE _verify_output
  ERROR_VARIABLE _verify_error
  )
if(NOT _verify_result EQUAL 0)
  file(REMOVE_RECURSE "${TOOL_DIR}")
  message(WARNING
    "The optional CycloneDX environment tools were installed but could not "
    "be imported. The CycloneDX artifact will be omitted.\n"
    "${_verify_output}${_verify_error}"
    )
  return()
endif()

file(WRITE "${_ready_marker}" "${_requirements_hash}\n")
message(STATUS "Provisioned CycloneDX environment tools in ${TOOL_DIR}")
