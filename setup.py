from setuptools import setup, find_packages
import weatherov

with open("README.md", "r") as fh:
    long_description = fh.read()
    
    

setup(
        name='weatherov',
        version=weatherov.__version__,
        author='Olivier Vincent',
        author_email='olivier.vincent@univ-lyon1.fr',
        url='https://cameleon.univ-lyon1.fr/ovincent/weatherov',
        description='Get and Plot weather data',
        long_description=long_description,
        long_description_content_type="text/markdown",
        packages=find_packages(),
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: BSD License",
            "Operating System :: OS Independent",
        ],
        python_requires='>=3.6'
)
