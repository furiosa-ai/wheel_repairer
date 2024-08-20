from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()
setup(
    name="wheel_repairer",
    version="0.1.0",
    author="Hyeokjune Jeon",
    author_email="hyeokjune.jeon@furiosa.ai",
    description="A tool to repair wheel files using auditwheel",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/furiosa-ai/wheel_repairer.git",
    packages=find_packages(where="src"),
    package_dir={"": "src"},
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    python_requires=">=3.6",
    install_requires=[
        "auditwheel",
    ],
    entry_points={
        "console_scripts": [
            "wheel_repairer=wheel_repairer.repairer:main",
        ],
    },
)