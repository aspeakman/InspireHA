from setuptools import setup

install_requires = list(val.strip() for val in open('requirements.txt'))

setup(name='inspire_ha',
      version='0.1.0',
      description='A client for Inspire Home Automation thermostats',
      author='Andrew Speakman',
      author_email='andrew@speakman.org.uk',
      url='https://github.com/aspeakman/inspire_ha',
      packages=['inspire_ha'],
      install_requires=install_requires
      )