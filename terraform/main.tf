
locals {
  project_prefix = "${var.project_name}-${var.environment}"
}

module "network" {
  source = "./modules/network"

  project_prefix     = local.project_prefix
  vpc_cidr           = "10.20.0.0/16"
  public_subnet_cidr = "10.20.1.0/24"
}

module "compute" {
  source = "./modules/compute"

  project_prefix    = local.project_prefix
  subnet_id         = module.network.public_subnet_id
  security_group_id = module.network.web_security_group_id
  instance_type     = "t3.micro"
}

module "monitoring" {
  source = "./modules/monitoring"

  project_prefix = local.project_prefix
  instance_id    = module.compute.instance_id
}
