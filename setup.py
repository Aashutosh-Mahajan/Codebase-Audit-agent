from setuptools import setup, find_packages

setup(
    name="codebase-audit-agent",
    version="1.0.0",
    packages=find_packages(),
    py_modules=["cli"],
    include_package_data=True,
    install_requires=[
        "click",
        "rich",
        "python-dotenv>=1.1.0",
        "fastapi>=0.115.0",
        "uvicorn[standard]>=0.34.0",
        "pydantic>=2.10.0",
        "langgraph>=0.4.0",
        "langchain-openai>=0.3.0",
        "langchain-core>=0.3.0",
        "gitpython>=3.1.44",
        "markdown>=3.7",
        "weasyprint>=63.0",
        "pygments>=2.19.0",
        "streamlit>=1.42.0",
        "requests>=2.32.0",
        "tiktoken>=0.9.0",
    ],
    entry_points={
        "console_scripts": [
            "audit-agent=cli:main",
        ],
    },
)
