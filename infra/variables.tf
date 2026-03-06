variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-north-1"
}

variable "instance_type" {
  description = "EC2 instance type"
  type        = string
  default     = "t3.micro"
}

variable "key_pair_name" {
  description = "Existing AWS EC2 key pair name"
  type        = string
}

variable "project_name" {
  description = "Project name used for naming and tagging resources"
  type        = string
  default     = "technews"
}

variable "environment" {
  description = "Deployment environment (e.g. production, staging)"
  type        = string
  default     = "production"
}

variable "my_ip_cidr" {
  description = "Your public IP in CIDR notation for SSH access (e.g. 203.0.113.10/32)"
  type        = string

  validation {
    condition     = can(cidrnetmask(var.my_ip_cidr))
    error_message = "my_ip_cidr must be a valid CIDR block, e.g. 203.0.113.10/32"
  }
}

variable "root_volume_size_gb" {
  description = "Root EBS volume size in GB"
  type        = number
  default     = 20
}