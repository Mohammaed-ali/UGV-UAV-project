from glob import glob
from setuptools import find_packages, setup

package_name = 'wildlife_perception'

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
            'detector_sim = wildlife_perception.detector_sim:main',
            'opencv_detector = wildlife_perception.opencv_detector:main',
        ],
    },
)
