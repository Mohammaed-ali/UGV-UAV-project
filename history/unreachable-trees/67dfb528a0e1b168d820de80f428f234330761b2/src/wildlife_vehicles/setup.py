from glob import glob
from setuptools import find_packages, setup

package_name = 'wildlife_vehicles'

setup(
    name=package_name,
    version='0.3.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/params', glob('params/*.yaml')),
    ],
    install_requires=['setuptools'], tests_require=['pytest'],
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'ugv_node = wildlife_vehicles.ugv_node:main',
            'deployment_node = wildlife_vehicles.deployment_node:main',
            'uav_node = wildlife_vehicles.uav_node:main',
            'docking_node = wildlife_vehicles.docking_node:main',
        ],
    },
)
