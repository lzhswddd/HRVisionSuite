# 设置项目名称
cmake_minimum_required(VERSION 3.5)
get_filename_component(DEMO_NAME VisionMasterCore NAME)
project(${DEMO_NAME} VERSION 1.0)
# set(DEMO_NAME TemplateWidget)
# project(${PROJECT_NAME} VERSION 1.0)
set(PYBIND11_DIRECTORY "D:/Python/pybind11")
set(PYTHON_DIRECTORY "D:/Anaconda3/envs/HRVision")
# set(THIRDPARTY_DIRECTORY "D:/Python/frame/HRVision/Bin")
set(CMAKE_RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}/bin)
set(PROGRAM_OUTPUT_DIRECTORY "D:/Python/frame/package/PyHRVision/HRVision")

# 设置了 C++ 的标准为 C++17
set(CMAKE_CXX_STANDARD 17)
#开启了当前目录的自动包含，这意味着 CMake 会自动将当前源码目录和构建目录添加到编译器的包含路径中
set(CMAKE_INCLUDE_CURRENT_DIR ON)

# Specify MSVC UTF-8 encoding
add_compile_options("$<$<C_COMPILER_ID:MSVC>:/utf-8>")
add_compile_options("$<$<CXX_COMPILER_ID:MSVC>:/utf-8>")

# pybind11 字符串统一按 UTF-8 编解码（与 VisionMasterProcess 一致；否则 Windows ANSI 模式下中文按 GBK 转码）
add_compile_definitions(PYBIND11_STRINGS_UTF8)

# 设置MSVC编译器的执行字符集为UTF-8
if(MSVC)
    add_compile_options("/utf-8")
    add_compile_options("/wd4828")
    set(CMAKE_CXX_FLAGS_RELEASE "${CMAKE_CXX_FLAGS_RELEASE} /Zi")
	set(CMAKE_SHARED_LINKER_FLAGS_RELEASE "${CMAKE_SHARED_LINKER_FLAGS_RELEASE} /DEBUG /OPT:REF /OPT:ICF")
endif()

# -----------------------------------------------------------------------------
file(GLOB_RECURSE inc_files ${CMAKE_CURRENT_SOURCE_DIR}/include/*.h)
file(GLOB_RECURSE src_files ${CMAKE_CURRENT_SOURCE_DIR}/src/*.cpp ${CMAKE_CURRENT_SOURCE_DIR}/bindings/*.cpp)
add_library(${PROJECT_NAME} SHARED ${src_files} ${inc_files})

# 添加VIsionMasterCore_SHARED_EXPORT宏定义

target_include_directories(${PROJECT_NAME} PRIVATE "D:/Program Files/VisionMaster4.3.0/Development/V4.x/Includes")
target_include_directories(${PROJECT_NAME} PRIVATE "D:/Program Files/VisionMaster4.3.0/Development/V4.x/ComControls/Includes/VS2017")
target_link_directories(${PROJECT_NAME} PRIVATE "D:/Program Files/VisionMaster4.3.0/Development/V4.x/ComControls/Libraries/win64")
target_link_directories(${PROJECT_NAME} PRIVATE "D:/Program Files/VisionMaster4.3.0/Development/V4.x/Libraries/win64/C")

target_include_directories(${PROJECT_NAME} PRIVATE include "${CMAKE_CURRENT_SOURCE_DIR}/src" "${PYBIND11_DIRECTORY}/include" "${PYTHON_DIRECTORY}/include" "${CMAKE_CURRENT_SOURCE_DIR}/../HRInclude")
target_link_libraries(${PROJECT_NAME} PRIVATE "${PYTHON_DIRECTORY}/libs/python3.lib" "${PYTHON_DIRECTORY}/libs/python312.lib")
target_link_libraries(${PROJECT_NAME} PRIVATE iMVS-6000PlatformSDK.lib)

set_target_properties(${PROJECT_NAME} PROPERTIES SUFFIX ".pyd")

# add_custom_command(TARGET ${PROJECT_NAME}
#     POST_BUILD
#     COMMAND ${CMAKE_COMMAND} -E echo "Running Python script..."
#     COMMAND ${PYTHON_DIRECTORY}/python.exe ${CMAKE_CURRENT_SOURCE_DIR}/build_pyi.py ${PROJECT_NAME} "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/$<CONFIG>" "${THIRDPARTY_DIRECTORY}"
#     WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR} 
# )


include(CMakePackageConfigHelpers)
set(CMAKE_INSTALL_PREFIX ${PROGRAM_OUTPUT_DIRECTORY})
configure_package_config_file(
    "${CMAKE_CURRENT_SOURCE_DIR}/${PROJECT_NAME}Config.cmake.in"
    "${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}Config.cmake"
    INSTALL_DESTINATION ${PROJECT_NAME}
)

write_basic_package_version_file(
    "${CMAKE_CURRENT_BINARY_DIR}/${PROJECT_NAME}ConfigVersion.cmake"
    VERSION ${PROJECT_VERSION}
    COMPATIBILITY AnyNewerVersion
)

install(TARGETS ${PROJECT_NAME}
    EXPORT ${PROJECT_NAME}Targets
    RUNTIME DESTINATION /
)

install(FILES
    "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/$<CONFIG>/${PROJECT_NAME}.pyi"
    # "${CMAKE_RUNTIME_OUTPUT_DIRECTORY}/$<CONFIG>/${PROJECT_NAME}.pdb"
    DESTINATION /
)