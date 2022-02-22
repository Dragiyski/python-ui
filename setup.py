import setuptools

with open('README.md', 'r', encoding='utf-8') as readme:
    long_description = readme.read()

setuptools.setup(
    name="dragiyski-ui",
    version="0.0.1",
    author="Plamen Dragiyski",
    author_email="plamen@dragiyski.org",
    description="User Interface library based on libSDL2",
    long_description=long_description,
    long_description_content_type="text/markdown",
    classifiers=[
        "Development Status :: 1 - Planning",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)",
        "Topic :: Software Development :: User Interfaces"
    ],
    package_dir={"": "src"},
    packages=setuptools.find_packages(where="src")
)