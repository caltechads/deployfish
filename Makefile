RAWVERSION = $(filter-out __version__ = , $(shell grep __version__ deployfish/__init__.py))
VERSION = $(strip $(shell echo $(RAWVERSION)))

PACKAGE = deployfish

clean:
	rm -rf *.tar.gz dist *.egg-info *.rpm
	find . -name "*.pyc" -exec rm '{}' ';'

version:
	@echo $(VERSION)

dist: clean
	@python setup.py sdist
	@python setup.py bdist_wheel --universal

pypi: dist
	@twine upload dist/*

tox:
	# create a tox pyenv virtualenv based on 2.7.x
	# install tox and tox-pyenv in that ve
	# actiave that ve before running this
	@tox