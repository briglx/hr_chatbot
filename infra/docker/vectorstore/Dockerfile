FROM postgres:15

# Install dependencies
RUN apt-get update && apt-get install -y \
    postgresql-server-dev-15 build-essential git

# Install pgvector extension
RUN git clone https://github.com/pgvector/pgvector.git \
    && cd pgvector \
    && make && make install

# hadolint ignore=SC2016
RUN echo 'alias ll='"'"'ls $LS_OPTIONS -al'"'"'' >> ~/.bashrc
