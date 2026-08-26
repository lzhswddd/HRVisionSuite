from setuptools import setup, find_packages

setup(
    name='PLCInterface',
    version='1.0.0',
    packages=find_packages(),
    author='HR',
    description='PLC通信库（Modbus/Profinet 等，基于 HslCommunication）',
    package_data={
        'PLCInterface': ['*.pyd', '*.pyi', '*.dll'],
    },
    python_requires='>=3.9',
)
