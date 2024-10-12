#!/bin/bash
set -e

# Bash codes for text
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color
BOLD=$(tput bold)
NORMAL=$(tput sgr0)

# Variables
BUILD_TYPE=RelWithDebInfo
RUN_TESTS=false
REFORMAT=false
VALID_ARGS=("test" "reformat" "Debug" "Release" "RelWithDebInfo" "MinSizeRel")

# Parse arguments
for arg in "$@"; do
    case $arg in
        test)
            RUN_TESTS=true
            shift
            ;;
        reformat)
            REFORMAT=true
            shift
            ;;
        Debug|Release|RelWithDebInfo|MinSizeRel)
            BUILD_TYPE=$arg
            shift
            ;;
        *)
            echo -e "${RED}Unknown argument: ${NC}$arg"
            echo -e "${YELLOW}Valid arguments are: ${NC}${VALID_ARGS[*]}"
            exit 1
            ;;
    esac
done

# Ajust code with copyright && style if requested
if [ "$REFORMAT" = true ]; then
    echo -e "\n${GREEN}${BOLD}Reformating code...${NORMAL}${NC}\n"

    set +e
    ament_uncrustify --reformat src/

    echo -e "\n${GREEN}${BOLD}Adding missing copyright disclamer...${NORMAL}${NC}\n"
    ament_copyright --add-missing Oxebots gplv3 src/
fi

# Build the workspace
echo -e "\n${GREEN}${BOLD}Starting build with build type:${NORMAL}${BUILD_TYPE}${NC}\n"
colcon build \
    --merge-install \
    --cmake-args "-DCMAKE_BUILD_TYPE=${BUILD_TYPE}" "-DCMAKE_EXPORT_COMPILE_COMMANDS=On"\
    -Wall -Wextra -Wpedantic

# Run tests if requested
if [ "$RUN_TESTS" = true ]; then
    echo -e "\n${GREEN}${BOLD}Running tests:${NORMAL}${NC}\n"

    if [ -f install/setup.bash ]; then source install/setup.bash; fi

    colcon test --merge-install
    colcon test-result
fi
