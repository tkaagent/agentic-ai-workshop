#!/bin/sh
# SSH Setup Script for Alpine Linux CE Routers

# Install OpenSSH server
apk add --no-cache openssh

# Create claude user with sudo privileges
adduser -D -s /bin/sh claude
echo "claude:claude" | chpasswd

# Add claude to wheel group (if exists) or create sudoers entry
if ! getent group wheel > /dev/null; then
    addgroup wheel
fi
adduser claude wheel

# Install sudo if not present
apk add --no-cache sudo

# Allow wheel group to sudo without password
echo "%wheel ALL=(ALL) NOPASSWD: ALL" > /etc/sudoers.d/wheel
chmod 0440 /etc/sudoers.d/wheel

# Create SSH directory for claude user
mkdir -p /home/claude/.ssh
chmod 700 /home/claude/.ssh

# Add the SSH public key (same as used in PE routers)
cat > /home/claude/.ssh/authorized_keys << 'EOF'
ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABgQC8GvwANwot/1lhpoM3ILOfgXwkVVPHLlpL8BZUCLdAKaLjMX7q6HM9a3TY/MnkNWtaAtl9VolN3eF6C/s1nKoqU3PX8n64ex2sIVJUyZ6p5HELB0fpr2Q89SwA7L9YBsaqmCtCIS0NOQ+/SEf6FgY5aEbDbrTvIKcgqTV1e86lHt4fKPDCaYKR5I1eDDISd3IenkrQsdG/CoBPqXbXN3C08uFRL+Vvyt6f/LX7KRE4KrhMNLC1N5cVKL/icv8SMAB89XhsqF2G7rqaZLYritroatT5BLrUbadinhWKB1Qp6jkmF2fVydVMZLWtNORAXfI7LKyA/ECso8jUKByPImGKdod6kG9OZafxgbybRzBdD7q7gjAp4JVW/26Btk+X2+XsyzhL5NHwFhDjaAreOnYokOwxly7g4LsM4ru+RbogBH2BZ2RmjKIaXODu/vyuiAhIz1gAnS1ZWPSQoWkGQ/Jz9JvQ7SVrfbBgRZbAaW/O+GPa2S7GCLyQgQkADx7yHls= jizquierdo@jizquierdo-mbp
EOF

chmod 600 /home/claude/.ssh/authorized_keys
chown -R claude:claude /home/claude/.ssh

# Configure custom prompt for root
echo 'export PS1="\u@\h:\w\$ "' >> /root/.profile

# Configure custom prompt for claude user
echo 'export PS1="\u@\h:\w\$ "' >> /home/claude/.profile
chown claude:claude /home/claude/.profile

# Configure SSH daemon
# Enable root login and pubkey authentication
sed -i 's/#PermitRootLogin.*/PermitRootLogin yes/' /etc/ssh/sshd_config
sed -i 's/#PubkeyAuthentication.*/PubkeyAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/#PasswordAuthentication.*/PasswordAuthentication yes/' /etc/ssh/sshd_config
sed -i 's/#PermitEmptyPasswords.*/PermitEmptyPasswords no/' /etc/ssh/sshd_config

# Generate host keys if they don't exist
ssh-keygen -A

# Start SSH daemon
/usr/sbin/sshd

# Display status
echo "SSH setup completed successfully"
echo "User 'claude' created with SSH key authentication"
echo "Custom prompt configured for root and claude users"
echo "SSH daemon started on port 22"
