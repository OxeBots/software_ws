#!/bin/bash

# Set the default build type (Debug, Release, RelWithDebInfo and MinSizeRel)
BUILD_TYPE=RelWithDebInfo
EXTRA_COLCON_ARGS=""

# Verifica se a flag --slow foi passada na linha de comandos
for arg in "$@"; do
    if [ "$arg" == "--slow" ]; then
        echo "Modo lento ativado: A limitar recursos de CPU e RAM para evitar sobrecarga do cp"

        # Limita o colcon pra processar 8 pacote do ROS de cada vez
        EXTRA_COLCON_ARGS="--parallel-workers 8"

        # Limita o motor de compilação (Make/Ninja) pra usar 10 threads
        export CMAKE_BUILD_PARALLEL_LEVEL=10
        export MAKEFLAGS="-j 10"
    fi
done

colcon build \
    --base-paths src \
    --merge-install \
    --symlink-install \
    $EXTRA_COLCON_ARGS \
    --cmake-args "-DCMAKE_BUILD_TYPE=${BUILD_TYPE}" "-DCMAKE_EXPORT_COMPILE_COMMANDS=On"

BUILD_RESULT=$?

if [ $BUILD_RESULT -eq 0 ]; then
    python3 -c "import json, glob; out=[]; [out.extend(json.load(open(f))) for f in glob.glob('build/*/compile_commands.json')]; json.dump(out, open('compile_commands.json', 'w'), indent=2)"
else
    echo "Build falhou"
fi

exit $BUILD_RESULT
