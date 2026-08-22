FROM kalilinux/kali-rolling

ENV DEBIAN_FRONTEND=noninteractive

# Fix Kali Linux repository GPG key issues
RUN apt-get update --allow-insecure-repositories && \
    apt-get install -y --no-install-recommends --allow-unauthenticated kali-archive-keyring && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Pentesting toolset
RUN apt-get update && apt-get -y install --no-install-recommends \
        net-tools python3 python3-pip python3-venv \
        curl gnupg nmap netcat-traditional iputils-ping ssh git \
        dnsutils wget dirb gobuster whatweb seclists sshpass tcpdump \
        build-essential python3-dev ca-certificates

# Metasploit (from Kali repos, works on amd64 and arm64)
RUN apt-get update && apt-get -y install --no-install-recommends metasploit-framework

# Allow pip to install system-wide on Kali
RUN mkdir -p /root/.pip && touch /root/.pip/pip.conf && \
    echo "[global]" > /root/.pip/pip.conf && \
    echo "break-system-packages = true" >> /root/.pip/pip.conf

# CAI framework (open-source mode, no Alias license needed)
RUN pip3 install --upgrade setuptools && pip3 install cai-framework
