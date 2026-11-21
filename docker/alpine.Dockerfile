FROM alpine:3.20
ARG ROOT_PASSWORD=cyberfleet
RUN apk add --no-cache openssh-server openssh-keygen python3 sudo iproute2 shadow \
    && mkdir -p /run/sshd /root/.ssh /var/log \
    && echo "root:${ROOT_PASSWORD}" | chpasswd \
    && sed -i -E '/^\s*#?\s*(PermitRootLogin|PasswordAuthentication|PermitEmptyPasswords|PubkeyAuthentication|Banner)\b/d' /etc/ssh/sshd_config \
    && (sed -i -E '/^\s*#?\s*(PermitRootLogin|PasswordAuthentication|PermitEmptyPasswords|PubkeyAuthentication|Banner)\b/d' /etc/ssh/sshd_config.d/*.conf 2>/dev/null || true) \
    && printf 'PermitRootLogin yes\nPasswordAuthentication yes\nPubkeyAuthentication yes\nPermitEmptyPasswords no\n' >> /etc/ssh/sshd_config
COPY sensor_tick.sh /usr/local/bin/sensor_tick.sh
COPY node-entrypoint.sh /usr/local/bin/node-entrypoint.sh
RUN chmod +x /usr/local/bin/sensor_tick.sh /usr/local/bin/node-entrypoint.sh \
    && echo '* * * * * /usr/local/bin/sensor_tick.sh' > /etc/crontabs/root \
    && /usr/local/bin/sensor_tick.sh
EXPOSE 22
ENTRYPOINT ["/usr/local/bin/node-entrypoint.sh"]
