import setuptools
import os
import subprocess
import shutil
from setuptools.command.build_py import build_py
from setuptools.command.sdist import sdist

# Get the current directory
HERE = os.path.abspath(os.path.dirname(__file__))

def build_jars():
    """Runs Gradle to build the JARs and copies them to the package directory."""
    print("Running Gradle build...")
    if os.name == 'nt':
        gradle_cmd = "gradle" 
        # Check if gradle is in path, otherwise try gradlew if it existed (it doesn't here but good practice)
        if shutil.which("gradle") is None:
             # Fallback or error?
             print("Warning: 'gradle' not found in PATH. Build might fail if JARs are missing.")
    else:
        gradle_cmd = "./gradlew" if os.path.exists("./gradlew") else "gradle"
    
    try:
        subprocess.check_call([gradle_cmd, "installDist"], cwd=HERE)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Gradle build failed or gradle not found. Assuming JARs are already built or this is an install from sdist without gradle.")

    # Copy JARs
    src_lib_dir = os.path.join(HERE, "build", "install", "corewars8086", "lib")
    dest_lib_dir = os.path.join(HERE, "corewars8086_lib", "lib")
    
    if os.path.exists(src_lib_dir):
        if os.path.exists(dest_lib_dir):
            shutil.rmtree(dest_lib_dir)
        os.makedirs(dest_lib_dir)
        
        for f in os.listdir(src_lib_dir):
            if f.endswith(".jar"):
                shutil.copy2(os.path.join(src_lib_dir, f), os.path.join(dest_lib_dir, f))
        print(f"Copied JARs to {dest_lib_dir}")
    else:
        print(f"Warning: Source JAR directory {src_lib_dir} not found. If this is a source install, ensure JARs are present.")

class CustomBuildPy(build_py):
    def run(self):
        build_jars()
        super().run()

class CustomSdist(sdist):
    def run(self):
        build_jars()
        super().run()

# Read the README file
with open(os.path.join(HERE, "README.md"), "r", encoding="utf-8") as f:
    long_description = f.read()

setuptools.setup(
    name="corewars8086-lib",
    version="1.0.0",
    author="CodeGuru",
    author_email="support@codeguru.co.il",
    description="Python wrapper for CoreWars8086 engine",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/daniel-penn/codeguru_2025_py_port_library",
    packages=setuptools.find_packages(),
    include_package_data=True,
    package_data={
        "corewars8086_lib": ["lib/*.jar"],
    },
    cmdclass={
        'build_py': CustomBuildPy,
        'sdist': CustomSdist,
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
