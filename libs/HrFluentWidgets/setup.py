from setuptools import setup, find_packages

setup(
    name='HrFluentWidgets',
    version='0.1.0',
    packages=find_packages(),
    author='HR',
    author_email='email@example.com',
    description='HR的UI组件包',
    # long_description=open('README.md').read(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    install_requires=[
        'PySide6',
        'PySide6-Fluent-Widgets',
        'pandas',
    ],
    python_requires='>=3.12',    
    package_data={
        'hrfluentwidgets': [
            'common/_rc/*',
            'common/_rc/images/*', 
            'components/_rc/*',
            'components/_rc/images/*', 
            'components/interface/resource/*',
            'components/interface/resource/qss/*', 
            'motion/thirdparty/*.dll'
        ],
    },
)

