import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess

def generate_launch_description():
    # Encontra o caminho para a pasta de compartilhamento do seu pacote de estratégia
    strategy_pkg_share = get_package_share_directory('oxebots_strategy')

    return LaunchDescription([
        # 1. Executa o grSim
        ExecuteProcess(
            cmd=['/home/matheus/grSim/bin/grSim'],
            name='grsim_simulator'
        ),
        
        # 2. Executa o nó de comunicação (a ponte)
        # Verifique se o nome do 'executable' está correto conforme o seu CMakeLists.txt
        Node(
            package='oxebots_comms',
            executable='sender_node', # <--- NOME ATUALIZADO
            name='grsim_bridge'
        ),

        # 3. Executa o nó de estratégia com GDB
        Node(
            package='oxebots_strategy',
            executable='strategy_node',
            name='strategy_node',
            output='screen',
            #prefix=['xterm -e gdb -ex run --args'],
            cwd=strategy_pkg_share
        )
    ])