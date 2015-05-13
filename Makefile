all: build install test 

clean:
	rm -rf build dist *.egg-info *.pyc 

test: 
	time -p tests/simple-topo-pingall/test.py

build: 
	python setup.py build

install: 
# some setuptools versions have a bug, need to run install
# twice to overcome caching issues
	-./setup.py install
	-./setup.py install

