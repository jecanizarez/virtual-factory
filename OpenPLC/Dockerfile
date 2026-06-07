FROM debian:bookworm
# Ref https://github.com/thiagoralves/OpenPLC_v3/blob/master/Dockerfile

# Install applications
RUN apt-get update && apt-get -y install git sqlite3 python3 dos2unix && apt-get clean

# Install OpenPLC_v3
RUN git clone https://github.com/thiagoralves/OpenPLC_v3.git
WORKDIR /OpenPLC_v3
RUN ./install.sh docker

# copy PLC script and database script over
RUN mkdir /OpenPLC_v3/scripts

ADD entrypoint.sh /OpenPLC_v3
RUN dos2unix /OpenPLC_v3/entrypoint.sh

EXPOSE 502
EXPOSE 8080
EXPOSE 20000
EXPOSE 43628
