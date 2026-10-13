from glob import glob
from setuptools import find_packages, setup

package_name = 'wildlife_core'

setup(
    name=package_name,
    version='0.2.0',
    packages=find_packages(exclude=['test']),
    data_files=[
        ('share/ament_index/resource_index/packages', ['resource/' + package_name]),
        ('share/' + package_name, ['package.xml']),
        ('share/' + package_name + '/config', glob('params/*.yaml')),
    ],
    install_requires=['setuptools'], tests_require=['pytest'],
    zip_safe=True,
    entry_points={
        'console_scripts': [
            'visualization_node = wildlife_core.visualization_node:main',
        ],
    },
)
