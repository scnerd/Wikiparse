from setuptools import setup, find_packages

setup(
    name='wikiparse',
    version='0.9a',
    url='https://github.com/scnerd/Wikiparse',
    license='MIT',
    author='David Maxson',
    author_email='scnerd@gmail.com',
    description='Powerful wikipedia parsing and caching library',
    package_data={'': ['config.json']},
    include_package_data=True,
    install_requires=['unidecode', 'py4j', 'beautifulsoup4']
)
