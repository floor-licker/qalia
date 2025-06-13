from setuptools import setup, find_packages

setup(
    name="qalia",
    version="2.0.0",
    packages=find_packages(),
    install_requires=[
        "playwright>=1.40.0",
        "openai>=1.0.0",
        "rich",
        "pytest>=7.0.0",
        "pytest-asyncio",
        "beautifulsoup4>=4.12.0",
        "requests",
        "asyncio-mqtt>=0.13.0",
        "dataclasses-json>=0.6.0",
        "python-dotenv>=1.0.0",
        # GitHub App dependencies
        "fastapi>=0.109.2",
        "uvicorn>=0.27.1",
        "PyGithub>=2.1.1",
        "PyJWT>=2.8.0",
        "aiofiles>=23.2.1",
        "httpx>=0.25.2",
    ],
    entry_points={
        "console_scripts": [
            "qalia-cli=main:main",
        ],
    },
    python_requires=">=3.9",
    author="Webisoft",
    author_email="info@webisoft.com",
    description="QA AI - GitHub App for Automated Test Generation",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/floor-licker/qalia",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
) 