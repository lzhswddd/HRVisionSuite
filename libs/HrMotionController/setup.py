from setuptools import setup, find_packages

setup(
    name='HrMotionController',
    version='0.2.0',
    packages=find_packages(),
    author='HR',
    author_email='89707731@example.com',
    description='HrMotionController包',
    # long_description=open('README.md').read(),
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    install_requires=[
    ],
    python_requires='>=3.9',    
    package_data={
        'hrmotioncontroller': [
            'components/widget/Axis/_rc/*',
            'components/widget/Axis/_rc/icons/*', 
            'components/zaux/*.dll',
        ],
    },
)

