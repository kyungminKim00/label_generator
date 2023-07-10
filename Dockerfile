FROM python:3.9-slim
ENV DEBIAN_FRONTEND noninteractive
RUN mkdir /dev_env
WORKDIR /dev_env
COPY . .
RUN apt-get update && apt-get upgrade -y && apt-get install -y --no-install-recommends apt-utils
RUN apt-get install -y git
RUN apt-get autoremove -y
RUN python3 -m pip install --upgrade pip
RUN pip3 install --no-cache-dir -r /dev_env/requirements.txt
RUN pip3 install --no-cache-dir -r /dev_env/ci_requirements.txt
