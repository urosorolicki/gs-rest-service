FROM jenkins/jenkins:lts

USER root

RUN apt-get update && apt-get install -y curl \
    && curl -fsSL https://download.docker.com/linux/static/stable/x86_64/docker-24.0.5.tgz -o docker.tgz \
    && tar --extract --file=docker.tgz --strip-components=1 --directory=/usr/local/bin docker/docker \
    && chmod +x /usr/local/bin/docker \
    && rm docker.tgz

USER jenkins
