from glob import glob
from setuptools import find_packages, setup

package_name = 'wildlife_targets'

setup(
    name=package_name,
    version='0.1.1',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/params', glob('params/*.yaml')),
    ],
    install_requires=['setuptools'],
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'detection_mux = wildlife_targets.detection_mux:main',
            'tracker = wildlife_targets.tracker:main',
            'target_manager = wildlife_targets.target_manager:main',
        ],
    },
)
