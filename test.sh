#!/bin/bash
# ==============================================================================
# Script para executar a suíte de testes unitários do workspace OxeBots
# Suporta execução local ou redirecionamento automático para o DevContainer
# ==============================================================================

# Se estiver executando no host e o container estiver ativo, redireciona para o DevContainer
if [ ! -f /.dockerenv ] && command -v docker >/dev/null 2>&1; then
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    CONTAINER_NAME=$(docker ps --filter "label=devcontainer.local_folder=$SCRIPT_DIR" --format "{{.Names}}" | head -n 1)
    if [ -z "$CONTAINER_NAME" ]; then
        CONTAINER_NAME=$(docker ps --format "{{.Names}}" | grep -E "software_ws|jolly_nash" | head -n 1)
    fi
    if [ -n "$CONTAINER_NAME" ]; then
        echo "Redirecionando execução dos testes para o DevContainer ($CONTAINER_NAME)..."
        exec docker exec -it "$CONTAINER_NAME" bash -c "/software_ws/test.sh $*"
    fi
fi

# Carrega ambiente ROS2 e workspace
if [ -f "/opt/ros/jazzy/setup.bash" ]; then
    source /opt/ros/jazzy/setup.bash
elif [ -f "/opt/ros/humble/setup.bash" ]; then
    source /opt/ros/humble/setup.bash
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

if [ -f "install/setup.bash" ]; then
    source install/setup.bash
fi

PARALLEL_WORKERS=2

echo "=========================================================="
echo "          EXECUTANDO TESTES UNITÁRIOS DO OXEBOTS         "
echo "=========================================================="

LOGIC_TEST_PACKAGES="oxebots_observers oxebots_prediction oxebots_strategy oxebots_comms oxebots_trajectory_analysis"

if [ $# -eq 0 ]; then
    echo "Executando testes dos pacotes de lógica: $LOGIC_TEST_PACKAGES"
    colcon test --parallel-workers ${PARALLEL_WORKERS} --packages-select ${LOGIC_TEST_PACKAGES}
else
    echo "Executando testes com argumentos customizados: $@"
    colcon test --parallel-workers ${PARALLEL_WORKERS} "$@"
fi

echo ""
echo "=========================================================="
echo "         RELATÓRIO DOS TESTES UNITÁRIOS DE LÓGICA         "
echo "=========================================================="

python3 - << 'EOF'
import glob
import xml.etree.ElementTree as ET

header = f"{'PACOTE':<30} | {'TESTES':<8} | {'FALHAS':<8} | {'ERROS':<8} | STATUS"
print(header)
print("-" * len(header))

total_tests = 0
total_failures = 0

xml_files = sorted(
    glob.glob("build/**/test_*.gtest.xml", recursive=True) +
    glob.glob("build/**/pytest.xml", recursive=True)
)

for f in xml_files:
    try:
        tree = ET.parse(f)
        root = tree.getroot()
        tests = int(root.attrib.get("tests", 0))
        failures = int(root.attrib.get("failures", 0))
        errors = int(root.attrib.get("errors", 0))
        if tests == 0:
            for suite in root.findall(".//testsuite"):
                tests += int(suite.attrib.get("tests", 0))
                failures += int(suite.attrib.get("failures", 0))
                errors += int(suite.attrib.get("errors", 0))
        total_tests += tests
        total_failures += failures + errors
        pkg = f.split("/")[1]
        status = "✅ APROVADO" if (failures + errors == 0) else "❌ FALHOU"
        print(f"{pkg:<30} | {tests:<8} | {failures:<8} | {errors:<8} | {status}")
    except Exception:
        pass

print("-" * len(header))
print(f"TOTAL: {total_tests} testes executados | FALHAS/ERROS: {total_failures}")
EOF

echo ""
