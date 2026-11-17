from setuptools import find_packages, setup
from pathlib import Path

package_name = 'lego_stacking'

setup(
    name=package_name,
    version='0.0.0',
    packages=find_packages(), #exclude=['test']),
    data_files=[
#        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        (str(Path('share') / package_name), ['package.xml']),
#        (str(Path('share') / package_name / "config"), ['config/' + "planning_pipelines_configuration.yaml"]),
#        (str(Path('share') / package_name / "launch"), ['launch/' + 'lego_stacking.launch.py']),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    maintainer='frtn80_group8_2026',
    maintainer_email='frtn80_group8_2026@todo.todo',
    description='TODO: Package description',
    license='TODO: License declaration',
    entry_points={
        'console_scripts': [
            'lego_planner = lego_stacking.lego_planner:main',
            'new_planner = lego_stacking.new_planner:main',
            'lego_planner_boris = lego_stacking.lego_planner_boris:main',
            'test_jo = lego_stacking.test_Jo:main',
        ],
    },
)
