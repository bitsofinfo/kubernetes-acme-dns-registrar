#-----------------------------------------
# Build layer: here we setup the base
# python environment, install core modules
# including the pre-requisites for talking
# to a private Azure Artifacts repo
#
# https://docs.microsoft.com/en-us/azure/devops/artifacts/quickstarts/python-packages
#-----------------------------------------
#
FROM python:3.11.1-alpine3.17 as build

# the system dependencies required for any of our 
# app specific python modules we will be installing
#
RUN apk add --no-cache libxml2-dev libxslt-dev python3-dev gcc build-base libxslt libxml2 libffi-dev

#
# Create a virtual env for our python environment
# where all modules will go that will be copied
# out of this base layer in the build below
#
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN mkdir /opt/build

COPY requirements-dev.txt /opt/build 
COPY requirements.txt /opt/build

RUN cd /opt/build && \
    source /opt/venv/bin/activate && \
    pip install -r requirements-dev.txt && \
    pip install -r requirements.txt && \
    pip uninstall -y setuptools 

# ----------------
# END build layer
# ----------------

# --------------------------------
# RELEASE LAYER
#
# Here is where you actually pull
# the virtual python environment
# out of the build layer + any
# system level libraries your modules
# depend on, install your python app
# and anything else you need
# 
# --------------------------------
FROM python:3.11.1-alpine3.17 as release
COPY --from=build /opt/venv /opt/venv

RUN pip uninstall -y setuptools

# install app etc
COPY main.py /opt/scripts/main.py
COPY core /opt/scripts/core
ENV PATH="/opt/scripts:/opt/venv/bin:$PATH"


# https://www.uvicorn.org/#command-line-options
COPY docker_resources/entrypoint.sh /entrypoint.sh

ARG USER=kadr
RUN adduser -D $USER
ENV HOME /home/${USER}

RUN chown -R ${USER}:${USER} /opt/venv 
RUN chown -R ${USER}:${USER} /opt/scripts
RUN chown -R ${USER}:${USER} /entrypoint.sh
RUN chmod 750 /entrypoint.sh

USER ${USER}
WORKDIR /opt/scripts
ENTRYPOINT ["sh","/entrypoint.sh"]