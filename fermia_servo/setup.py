from setuptools import setup, find_packages

# Read the contents of README file
with open("README.md", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="fermia_servo",
    version="0.1.0",
    author="Aryan Senthil",
    author_email="aryanyaminisenthil@example.com",
    description="A library for controlling servo motors with Redis persistence",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "redis",
    ],
    # Optional: uncomment to include package data files
    # package_data={
    #     "fermia_servo": ["data/*.json"],
    # },
)