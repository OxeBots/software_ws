#!/bin/bash
# set -e

# Set the default build type (Debug, Release, RelWithDebInfo and MinSizeRel)
BUILD_TYPE=RelWithDebInfo

colcon build \
    --merge-install \
    --cmake-args "-DCMAKE_BUILD_TYPE=RelWithDebInfo" "-DCMAKE_EXPORT_COMPILE_COMMANDS=On"\
    -Wall -Wextra -Wpedantic

if [ -f install/setup.bash ]; then source install/setup.bash; fi
