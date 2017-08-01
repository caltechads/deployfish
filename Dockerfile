FROM centos:7

MAINTAINER IMSS ADS <imss-ads-staff@caltech.edu>

USER root

RUN yum -y install epel-release && yum -y makecache fast && yum -y update && yum -y install \
    mysql \
    && yum -y clean all

# set our timezone to pacific time
WORKDIR /etc
RUN rm -rf localtime && ln -s /usr/share/zoneinfo/America/Los_Angeles localtime

# ---------------
# deployfish
# ---------------
COPY . /deployfish
WORKDIR /deployfish

# ---------------
# Entrypoint
# ---------------
RUN curl "https://bootstrap.pypa.io/get-pip.py" -o "get-pip.py" && python get-pip.py && \
    pip install awscli && \
    python setup.py install && \
    cp /deployfish/bin/entrypoint.sh /entrypoint.sh && \
    chmod a+x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
