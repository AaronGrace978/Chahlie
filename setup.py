"""
Setup script for Chahlie
Official Product of Cursor Boston
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="chahlie",
    version="1.0.0",
    author="Cursor Boston",
    author_email="hello@cursorboston.com",
    description="The Boston Coding Agent - An agentic AI assistant with Boston personality",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cursor-boston/chahlie",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Environment :: Console",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Software Development",
        "Topic :: Utilities",
    ],
    python_requires=">=3.10",
    install_requires=[
        "anthropic>=0.25.0",
        "rich>=13.7.0",
        "textual>=0.50.0",
        "click>=8.1.0",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "chahlie=chahlie.__main__:main",
        ],
    },
    keywords="ai, coding, assistant, boston, claude, anthropic, agent, cursor",
    project_urls={
        "Bug Tracker": "https://github.com/cursor-boston/chahlie/issues",
        "Documentation": "https://github.com/cursor-boston/chahlie#readme",
        "Source": "https://github.com/cursor-boston/chahlie",
        "Cursor Boston": "https://cursorboston.com",
    },
)
