cmake_minimum_required(VERSION 3.22)

# Ensure CMake always finds ninja regardless of shell environment
if(NOT DEFINED CMAKE_MAKE_PROGRAM AND EXISTS "C:/Espressif/tools/ninja/1.12.1/ninja.exe")
    set(CMAKE_MAKE_PROGRAM "C:/Espressif/tools/ninja/1.12.1/ninja.exe" CACHE FILEPATH "Ninja build tool" FORCE)
endif()

# Disable ccache to prevent Ninja CreateProcess 'system cannot find the file specified' error
set(CCACHE_ENABLE OFF CACHE BOOL "Disable ccache" FORCE)
set(IDF_CCACHE_ENABLE OFF CACHE BOOL "Disable ccache" FORCE)

list(APPEND CMAKE_PROGRAM_PATH
    "C:/Espressif/tools/ninja/1.12.1"
    "C:/Espressif/tools/ccache/4.12.1/ccache-4.12.1-windows-x86_64"
    "C:/Espressif/tools/cmake/4.0.3/bin"
    "C:/Espressif/tools/xtensa-esp-elf/esp-15.2.0_20251204/xtensa-esp-elf/bin"
)

include($ENV{IDF_PATH}/tools/cmake/project.cmake)
project(km_bridge_firmware)

