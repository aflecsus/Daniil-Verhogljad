FROM ubuntu:24.04 AS node
ENV DEBIAN_FRONTEND=noninteractive
ARG ROOT_PASSWORD=cyberfleet
RUN apt-get update && apt-get install -y --no-install-recommends \
      openssh-server python3 python3-apt sudo iproute2 procps ca-certificates curl tar gzip \
    && rm -rf /var/lib/apt/lists/* \
    && mkdir -p /run/sshd /root/.ssh \
    && echo "root:${ROOT_PASSWORD}" | chpasswd \
    && sed -i -E '/^\s*#?\s*(PermitRootLogin|PasswordAuthentication|PermitEmptyPasswords|PubkeyAuthentication|Banner)\b/d' /etc/ssh/sshd_config \
    && (sed -i -E '/^\s*#?\s*(PermitRootLogin|PasswordAuthentication|PermitEmptyPasswords|PubkeyAuthentication|Banner)\b/d' /etc/ssh/sshd_config.d/*.conf 2>/dev/null || true) \
    && printf 'PermitRootLogin yes\nPasswordAuthentication yes\nPubkeyAuthentication yes\nPermitEmptyPasswords no\n' >> /etc/ssh/sshd_config \
    && sed -i 's@session\s*required\s*pam_loginuid.so@session optional pam_loginuid.so@' /etc/pam.d/sshd
COPY node-entrypoint.sh /usr/local/bin/node-entrypoint.sh
RUN chmod +x /usr/local/bin/node-entrypoint.sh
EXPOSE 22
ENTRYPOINT ["/usr/local/bin/node-entrypoint.sh"]

# ---------------------------------------------------------------------------
FROM ubuntu:24.04 AS controller
ENV DEBIAN_FRONTEND=noninteractive \
    ANSIBLE_CONFIG=/ansible/ansible.cfg \
    LC_ALL=C.UTF-8 LANG=C.UTF-8
RUN apt-get update && apt-get install -y --no-install-recommends \
      ansible openssh-client sshpass nginx cron python3 python3-yaml openssl \
      curl ca-certificates iproute2 procps git vim less tar gzip util-linux iputils-ping \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /ansible
COPY controller-entrypoint.sh /usr/local/bin/controller-entrypoint.sh
RUN chmod +x /usr/local/bin/controller-entrypoint.sh
EXPOSE 8080
ENTRYPOINT ["/usr/local/bin/controller-entrypoint.sh"]
