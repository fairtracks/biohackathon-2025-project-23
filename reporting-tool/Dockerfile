FROM ubuntu:plucky

WORKDIR /home/ubuntu

# Install curl
RUN apt-get update && \
    apt-get install -y curl xz-utils git libjson-perl libyaml-dev cpanminus gcc

RUN curl -sL https://github.com/typst/typst/releases/download/v0.14.0/typst-x86_64-unknown-linux-musl.tar.xz -o typst.tar.xz
RUN tar xJf typst.tar.xz --strip-components=1 typst-x86_64-unknown-linux-musl/typst

RUN cpanm YAML::XS

RUN git clone --depth 1 https://github.com/fairtracks/biohackathon-2025-project-23.git

ENV PATH=/home/ubuntu:$PATH

RUN mkdir /data

WORKDIR /data

ENTRYPOINT ["perl", "/home/ubuntu/biohackathon-2025-project-23/reporting-tool/reporter.pl"]


# 
# WORKDIR /srv/generate-genome-data
# RUN cpanm --installdeps ./bin && \
#     pip3 install -r ./bin/requirements.txt
