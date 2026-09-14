#!/bin/bash

# Set the default build type (Debug, Release, RelWithDebInfo and MinSizeRel)
BUILD_TYPE=RelWithDebInfo

colcon build \
    --merge-install \
    --symlink-install \
    --cmake-args "-DCMAKE_BUILD_TYPE=${BUILD_TYPE}" "-DCMAKE_EXPORT_COMPILE_COMMANDS=On"

BUILD_RESULT=$?

if [ $BUILD_RESULT -eq 0 ]; then
    python3 -c "import json, glob; out=[]; [out.extend(json.load(open(f))) for f in glob.glob('build/*/compile_commands.json')]; json.dump(out, open('compile_commands.json', 'w'), indent=2)"
else
    echo "Build falhou"
fi

exit $BUILD_RESULT