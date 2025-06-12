from setuptools import setup, find_packages

setup(
    name="qalia",
    version="1.0.0",
    packages=find_packages(),
    install_requires=[
        "playwright",
        "openai",
        "rich",
        "pytest",
        "pytest-asyncio",
        "beautifulsoup4",
        "requests",
    ],
    entry_points={
        "console_scripts": [
            "qalia=main:main",
        ],
    },
    python_requires=">=3.9",
    author="Webisoft",
    author_email="info@webisoft.com",
    description="QA AI - Automated Test Generation Tool",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/webisoftSoftware/qalia",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
    ],
) 