"""
Setup script for Remote Desktop Viewer
"""
from setuptools import setup, find_packages

setup(
    name="remote-desktop-viewer",
    version="1.0.0",
    description="Proof-of-concept remote desktop viewing application",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        "cryptography>=41.0.0",
        "Pillow>=10.0.0",
        "mss>=9.0.0",
        "numpy>=1.24.0",
        "opencv-python>=4.8.0",
        "websockets>=12.0",
        "aiofiles>=23.0.0",
    ],
    python_requires=">=3.8",
    entry_points={
        "console_scripts": [
            "rdv-client=client.client:main",
            "rdv-server=server.server:main",
        ],
    },
)
