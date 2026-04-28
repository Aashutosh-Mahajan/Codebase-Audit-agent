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
        "python-dotenv",
    ],
    entry_points={
        "console_scripts": [
            "audit-agent=cli:main",
        ],
    },
)
