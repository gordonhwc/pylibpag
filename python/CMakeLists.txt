cmake_minimum_required(VERSION 3.20)
project(pylibpag LANGUAGES C CXX)

set(PYLIBPAG_ROOT "${CMAKE_CURRENT_LIST_DIR}/..")
set(CMAKE_POSITION_INDEPENDENT_CODE ON)
set(CMAKE_CXX_FLAGS "${CMAKE_CXX_FLAGS} -include cstddef -include cstdint")

set(PAG_BUILD_SHARED OFF CACHE BOOL "" FORCE)
set(PAG_BUILD_FRAMEWORK OFF CACHE BOOL "" FORCE)
set(PAG_BUILD_PAGX OFF CACHE BOOL "" FORCE)
set(PAG_BUILD_CLI OFF CACHE BOOL "" FORCE)
set(PAG_BUILD_SVG OFF CACHE BOOL "" FORCE)
set(PAG_BUILD_PPT OFF CACHE BOOL "" FORCE)
set(PAG_USE_C OFF CACHE BOOL "" FORCE)
set(PAG_USE_FREETYPE ON CACHE BOOL "" FORCE)
set(PAG_USE_HARFBUZZ OFF CACHE BOOL "" FORCE)
set(PAG_USE_LIBAVC OFF CACHE BOOL "" FORCE)
set(PAG_USE_PNG_DECODE OFF CACHE BOOL "" FORCE)
set(PAG_USE_PNG_ENCODE OFF CACHE BOOL "" FORCE)
set(PAG_USE_JPEG_DECODE OFF CACHE BOOL "" FORCE)
set(PAG_USE_JPEG_ENCODE OFF CACHE BOOL "" FORCE)
set(PAG_USE_WEBP_DECODE ON CACHE BOOL "" FORCE)
set(PAG_USE_WEBP_ENCODE OFF CACHE BOOL "" FORCE)
set(PAG_USE_OPENGL ON CACHE BOOL "" FORCE)
set(PAG_USE_THREADS ON CACHE BOOL "" FORCE)

if (APPLE)
    set(PAG_USE_SWIFTSHADER OFF CACHE BOOL "" FORCE)
else ()
    set(PAG_USE_SWIFTSHADER ON CACHE BOOL "" FORCE)
endif ()

add_subdirectory("${PYLIBPAG_ROOT}" "${CMAKE_CURRENT_BINARY_DIR}/libpag" EXCLUDE_FROM_ALL)

if (CMAKE_SYSTEM_NAME STREQUAL "Linux" AND CMAKE_SYSTEM_PROCESSOR MATCHES "^(aarch64|arm64)$")
    # tgfx's fixed-size SIMD buffers are incompatible with Highway's SVE targets
    target_compile_definitions(tgfx PRIVATE HWY_DISABLED_TARGETS=HWY_ALL_SVE)
endif ()

add_library(pylibpag_native MODULE native/pylibpag.cpp)
target_compile_features(pylibpag_native PRIVATE cxx_std_17)
target_include_directories(pylibpag_native PRIVATE "${PYLIBPAG_ROOT}/include")
target_link_libraries(pylibpag_native PRIVATE pag)
if (UNIX AND NOT APPLE)
    target_link_options(pylibpag_native PRIVATE "-Wl,--no-undefined")
endif ()
set_target_properties(
    pylibpag_native
    PROPERTIES
        CXX_VISIBILITY_PRESET hidden
        PREFIX ""
        OUTPUT_NAME "_native"
        VISIBILITY_INLINES_HIDDEN ON
)

install(TARGETS pylibpag_native LIBRARY DESTINATION pylibpag RUNTIME DESTINATION pylibpag)
