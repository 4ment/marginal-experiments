FROM debian:stretch

LABEL maintainer="Mathieu Fourment"

RUN apt-get update && apt-get install -y --no-install-recommends \
	build-essential \
	ca-certificates \
	cmake \
	libgsl0-dev \
	python2.7 \
	unzip \
	wget
	
RUN wget https://github.com/4ment/physher/archive/marginal-v1.1.zip && unzip marginal-v1.1.zip
WORKDIR /physher-marginal-v1.1/Release
RUN cmake -DBUILD_SHARED_LIBS=OFF .. && make && make install
WORKDIR /data

ENTRYPOINT ["python2.7", "run_simulations.py"]
