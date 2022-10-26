"""Setup cognito_client"""
from setuptools import setup, find_namespace_packages

with open("README.md") as f:
    long_description = f.read()

inst_reqs = [
    "aws-cdk-lib==2.27.0",
    "aws_cdk.aws_cognito_identitypool_alpha==2.27.0a0",
    "constructs>=10.0.0,<11.0.0",
    "pydantic==1.9.1",
    "black==22.3.0",
    "boto3==1.24.15",
    "boto3-stubs[cognito-idp,cognito-identity]",
]
extra_reqs = {
    "test": ["pytest"],
}

setup(
    name="cognito_client",
    description="A library for creating short-term AWS credentials for users with Cognito credentials.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    python_requires=">=3.7",
    classifiers=[
        "Intended Audience :: Information Technology",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    keywords="Cognito AWS",
    author="Anthony Lukach",
    author_email="anthony@developmentseed.org",
    url="https://github.com/developmentseed/cognito_client",
    license="MIT",
    packages=find_namespace_packages(exclude=["tests*"]),
    include_package_data=True,
    zip_safe=False,
    install_requires=inst_reqs,
    extras_require=extra_reqs,
)