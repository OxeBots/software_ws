import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import ExecuteProcess

def generate_launch_description():
    # Encontra o caminho para a pasta de compartilhamento do seu pacote de estratégia
    strategy_pkg_share = get_package_share_directory('oxebots_strategy')
    
    # Define o caminho completo para o arquivo XML da árvore de comportamento
    behavior_tree_path = os.path.join(strategy_pkg_share, 'test_tree.xml')

    return LaunchDescription([
        # 1. Executa o grSim (Simulador)
        ExecuteProcess(
            cmd=['/home/matheus/grSim/bin/grSim'],
            name='grsim_simulator',
            output='screen'
        ),
        
        # # 2. Executa o nó de comunicação (sender_node)
        # Node(
        #     package='oxebots_comms',
        #     executable='sender_node',
        #     name='sender_node',
        #     output='screen',
        #     parameters=[
        #         {
        #             "grsim_addr": "127.0.0.1",      # IP padrão do grSim
        #             "grsim_port": 20011,            # Porta de comando padrão
        #             "topic": "robot_commands"       # Tópico que a estratégia publica
        #         }
        #     ]
        # ),

        # 3. Executa o nó de estratégia (strategy_node)
        Node(
            package='oxebots_strategy',
            executable='strategy_node',
            name='strategy_node',
            output='screen',
            # Passa o caminho do arquivo da árvore de comportamento como parâmetro
            parameters=[
                {'bt_xml_path': behavior_tree_path}
            ],
            cwd=strategy_pkg_share
        )
    ])