import os
from glob import glob
from setuptools import setup, find_packages

package_name = 'robot_arm_nlp'

setup(
    name=package_name,
    version='1.0.0',
    packages=find_packages(where='.'),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name] if os.path.exists('resource/' + package_name) else []),
        ('share/' + package_name, ['package.xml']),
        (os.path.join('share', package_name, 'launch'), glob('launch/*.launch.py')),
        (os.path.join('share', package_name, 'config'), glob('config/*.yaml')),
        (os.path.join('share', package_name, 'urdf'), glob('urdf/*.urdf')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='Hamza',
    maintainer_email='hamza@example.com',
    description='Natural-Language-Controlled Robot Arm',
    license='MIT',
    tests_require=['pytest'],
    entry_points={
        'console_scripts': [
            'input_handler = src.input_handler.input_handler_node:main',
            'task_planner = src.task_planner.task_planner_node:main',
            'perception = src.perception.perception_node:main',
            'motion = src.motion.motion_node:main',
            'orchestrator = src.orchestrator.orchestrator_node:main',
            'calibrate = src.perception.calibrate:main',
            'tune_hsv = src.perception.tune_hsv:main',
            'standalone_sim = src.simulation.standalone_runner:main',
        ],
    },
)
