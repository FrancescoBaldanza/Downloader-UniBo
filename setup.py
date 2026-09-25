from setuptools import setup, find_packages

setup(
    name="unibo-downloader",
    version="1.0.0",
    packages=find_packages(),
    py_modules=["dlub", "main"],
    install_requires=[
        "requests>=2.31.0",
        "beautifulsoup4>=4.12.0",
        "playwright>=1.40.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "dlub=dlub:main",
        ],
    },
    python_requires=">=3.9",
)
