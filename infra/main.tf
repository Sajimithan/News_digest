# ─────────────────────────────────────────────
# AMI Lookup via AWS SSM Parameter Store
# Avoids hardcoding AMI IDs which change per region
# ─────────────────────────────────────────────
data "aws_ssm_parameter" "ubuntu_2204_ami" {
  name = "/aws/service/canonical/ubuntu/server/22.04/stable/current/amd64/hvm/ebs-gp2/ami-id"
}

# ─────────────────────────────────────────────
# Security Group
# ─────────────────────────────────────────────
resource "aws_security_group" "technews_sg" {
  name        = "${var.project_name}-${var.environment}-sg"
  description = "Security group for ${var.project_name} EC2 instance"

  # SSH — restricted to your IP only
  ingress {
    description = "SSH from my IP only"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.my_ip_cidr]
  }

  # HTTP — open to public
  ingress {
    description = "HTTP from anywhere"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # HTTPS — open to public
  ingress {
    description = "HTTPS from anywhere"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  # All outbound traffic allowed
  egress {
    description = "Allow all outbound"
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-sg"
  }
}

# ─────────────────────────────────────────────
# EC2 Instance
# ─────────────────────────────────────────────
resource "aws_instance" "technews_ec2" {
  ami                    = data.aws_ssm_parameter.ubuntu_2204_ami.value
  instance_type          = var.instance_type
  key_name               = var.key_pair_name
  vpc_security_group_ids = [aws_security_group.technews_sg.id]

  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size_gb
    delete_on_termination = true
    encrypted             = true
  }

  metadata_options {
    http_endpoint               = "enabled"
    http_tokens                 = "required" # IMDSv2 enforced (security best practice)
    http_put_response_hop_limit = 1
  }

  # ── Auto-bootstrap on first boot ────────────────────────────
  # Runs once when the instance starts for the first time.
  # Installs all server dependencies so GitHub Actions can deploy
  # immediately after terraform apply completes.
  user_data = base64encode(<<-BOOTSTRAP
    #!/bin/bash
    set -euo pipefail
    exec >> /var/log/technews-bootstrap.log 2>&1
    echo "=== Bootstrap started: $(date) ==="

    export DEBIAN_FRONTEND=noninteractive
    apt-get update -y
    apt-get upgrade -y

    # Python 3.11
    apt-get install -y python3.11 python3.11-venv python3-pip

    # Node.js 20
    curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    apt-get install -y nodejs

    # Nginx + Certbot
    apt-get install -y nginx certbot python3-certbot-nginx
    systemctl enable nginx
    systemctl start nginx

    # App directories owned by ubuntu
    mkdir -p /var/www/technews/backend
    mkdir -p /var/www/technews/frontend/dist
    mkdir -p /var/www/technews/deploy
    chown -R ubuntu:ubuntu /var/www/technews

    # Allow ubuntu to manage services without password (required for CI/CD)
    echo "ubuntu ALL=(ALL) NOPASSWD: /usr/bin/systemctl, /bin/systemctl, /usr/sbin/nginx, /usr/bin/nginx" \
      > /etc/sudoers.d/technews-deploy
    chmod 440 /etc/sudoers.d/technews-deploy

    echo "=== Bootstrap complete: $(date) ==="
  BOOTSTRAP
  )

  # Do not replace the instance if user_data is later modified
  user_data_replace_on_change = false

  tags = {
    Name = "${var.project_name}-${var.environment}-ec2"
  }

  lifecycle {
    # Prevent accidental instance replacement
    ignore_changes = [ami]
  }
}

# ─────────────────────────────────────────────
# Elastic IP
# ─────────────────────────────────────────────
resource "aws_eip" "technews_eip" {
  domain = "vpc"

  tags = {
    Name = "${var.project_name}-${var.environment}-eip"
  }
}

# ─────────────────────────────────────────────
# Elastic IP Association
# ─────────────────────────────────────────────
resource "aws_eip_association" "technews_eip_assoc" {
  instance_id   = aws_instance.technews_ec2.id
  allocation_id = aws_eip.technews_eip.id
}