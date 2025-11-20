import setuptools
import os

# Get the current directory
HERE = os.path.abspath(os.path.dirname(__file__))

# Read the README file
with open(os.path.join(HERE, "README.md"), "r", encoding="utf-8") as f:
    long_description = f.read()

# List of JARs to include
# We assume 'gradle installDist' has been run and JARs are in build/install/corewars8086/lib
JAR_DIR = os.path.join("build", "install", "corewars8086", "lib")
JARS = []
if os.path.exists(JAR_DIR):
    JARS = [os.path.join(JAR_DIR, f) for f in os.listdir(JAR_DIR) if f.endswith(".jar")]

setuptools.setup(
    name="corewars8086-lib",
    version="5.0.1",
    author="CodeGuru",
    author_email="support@codeguru.co.il",
    description="Python wrapper for CoreWars8086 engine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/daniel-penn/codeguru_2025_py_port_library",
    packages=setuptools.find_packages(),
    include_package_data=True,
    package_data={
        "corewars8086_lib": ["*.jar", "lib/*.jar"],  # Expecting JARs to be copied here during build
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        "py4j>=0.10.9",
    ],
)

