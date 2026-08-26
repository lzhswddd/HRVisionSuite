from setuptools import setup, find_packages

setup(
    name='HRVision',
    version='0.2.0',
    packages=find_packages(),
    author='HR',
    author_email='89707731@example.com',
    description='HRVision包',
    # long_description=open('README.md').read(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    install_requires=[
        'pycryptodome',
        'numpy',
        'psutil',
        'wmi',
        'cryptography'
    ],
    python_requires='>=3.9',    
    package_data={
        '': ['*.pyd', '*.pyi'],  # 指定需要包含的文件类型
        'HRVision': ['bin/*'],
    },
)

