FROM node:18-bookworm

# Disable signature checks because of the simulated 2026 date
RUN echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99no-check-valid-until && \
    echo 'Acquire::AllowInsecureRepositories "true";' >> /etc/apt/apt.conf.d/99no-check-valid-until && \
    echo 'Acquire::AllowDowngradeToInsecureRepositories "true";' >> /etc/apt/apt.conf.d/99no-check-valid-until

# Install dependencies for odbc module compilation
RUN apt-get update -y || true
RUN apt-get install -y --allow-unauthenticated unixodbc-dev && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create app directory
WORKDIR /usr/src/app

RUN git clone --depth 1 --branch v1.3.2 https://github.com/frangoteam/FUXA.git
WORKDIR /usr/src/app/FUXA

# Install server
WORKDIR /usr/src/app/FUXA/server
RUN npm install

# Workaround for sqlite3 https://stackoverflow.com/questions/71894884/sqlite3-err-dlopen-failed-version-glibc-2-29-not-found
RUN apt-get update -y || true
RUN apt-get install -y --allow-unauthenticated sqlite3 libsqlite3-dev && \
  npm install --build-from-source --sqlite=/usr/bin sqlite3 && \
  apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /usr/src/app/FUXA/server
ADD entrypoint.sh /usr/src/app/FUXA/server

EXPOSE 1881
CMD [ "npm", "start" ]