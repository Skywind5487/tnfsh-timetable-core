from setuptools import setup, find_packages

setup(
    name="tnfsh-timetable-core",
    version="0.0.1",
    description="台南一中課表核心功能庫",
    author="Skywind5487",
    author_email="skywind5487@gmail.com",   
    packages=find_packages(exclude=["tests.*", "tests", "example.*", "example"]),
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.8.0",
        "beautifulsoup4>=4.9.3",
        "pydantic>=2.0.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "pytest-asyncio>=0.14.0",
            "black>=22.0.0",
            "isort>=5.0.0",
            "mypy>=0.900",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Education",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
    ],
    keywords="timetable, scheduling, education",
    project_urls={
        "Source": "https://github.com/skywind5487/tnfsh-timetable-core",
    }
)
