from setuptools import setup, find_packages

setup(
    name="fermia_camera",  # Package name
    version="0.1.0",       # Version number
    packages=find_packages(),  # Automatically finds "fermia_camera"
    install_requires=[
        "numpy",
        "opencv-python",
        "redis",
        "pyrealsense2"
    ],  # Dependencies
    python_requires=">=3.6",
    author="Aryan Senthil",
    author_email="aryanyaminisenthil@gmail.com",
    description="A package for managing camera feeds using Redis",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)