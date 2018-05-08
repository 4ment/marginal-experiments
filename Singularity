Bootstrap: docker
From: debian:stretch

%labels
	Maintainer Mathieu Fourment

%post
 	apt-get update && apt-get install -y --no-install-recommends \
		build-essential \
		ca-certificates \
		cmake \
		git \
		libgsl0-dev \
		python2.7
	
	git clone https://github.com/4ment/physher.git
	cd physher/
	mkdir Release
	cd Release
 	git checkout listener
	cmake -DBUILD_SHARED_LIBS=OFF .. && make && make install

%runscript
	python2.7 run_simulations.py "$@"

%test
	physher