output "ec2_instance_id" {
  description = "The EC2 instance ID"
  value       = aws_instance.technews_ec2.id
}

output "ec2_public_ip" {
  description = "The Elastic (public) IP address of the EC2 instance"
  value       = aws_eip.technews_eip.public_ip
}

output "ec2_public_dns" {
  description = "The public DNS of the EC2 instance"
  value       = aws_instance.technews_ec2.public_dns
}

output "ec2_ami_used" {
  description = "The Ubuntu 22.04 AMI ID that was used"
  value       = data.aws_ssm_parameter.ubuntu_2204_ami.value
  sensitive   = true
}

output "security_group_id" {
  description = "The security group ID"
  value       = aws_security_group.technews_sg.id
}

output "ssh_connection_command" {
  description = "Copy-paste SSH command to connect to your instance"
  value       = "ssh -i ~/.ssh/${var.key_pair_name}.pem ubuntu@${aws_eip.technews_eip.public_ip}"
}