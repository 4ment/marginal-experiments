FROM debian:stretch

RUN apt-get install -y --no-install-recommends \
	ca-certificates \
	cmake \
	git \
	libgsl0-dev \
	python2.7
	
RUN git clone https://github.com/4ment/physher.git
WORKDIR /physher/Release
RUN git checkout listener
RUN cmake -DBUILD_SHARED_LIBS=OFF .. && make && make install

ENTRYPOINT ["python2.7", "run_simulations.py"]
