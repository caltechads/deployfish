RAWVERSION = $(filter-out __version__ = , $(shell grep __version__ deployfish/__init__.py))
VERSION = $(strip $(shell echo $(RAWVERSION)))

PACKAGE = deployfish

clean:
	rm -rf *.tar.gz dist build *.egg-info *.rpm
	find . -name "*.pyc" | xargs rm
	find . -name "__pycache__" | xargs rm -rf

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
	# activate that ve before running this
	@tox
