FROM rockylinux:9
ARG ROOT_PASSWORD=cyberfleet
RUN dnf -y install openssh-server python3 python3-dnf sudo iproute procps-ng passwd findutils hostname tar gzip \
    && dnf clean all \
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
