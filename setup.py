from setuptools import setup, find_packages
from pathlib import Path

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8") if (this_directory / "README.md").exists() else ""

setup(
    name="unibo-downloader",
    version="1.0.0",
    description="Applicazione grafica macOS per la sincronizzazione e il download dei materiali didattici da Virtuale UniBo.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    py_modules=["main"],
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "playwright>=1.40.0",
        "python-dotenv>=1.0.0",
        "PyQt6>=6.5.0",
        "Pillow>=10.0.0",
    ],
    python_requires=">=3.9",
)
