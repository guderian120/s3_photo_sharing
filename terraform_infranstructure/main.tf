provider "aws" {
  region = "eu-west-1"
  profile = "sandbox"
  
}

data "template_file" "user_data" {
  template = file("${path.module}/user_data.sh") 

  
}


resource "aws_instance" "photo_share_instance" {
   ami            = "ami-01f23391a59163da9" # Amazon Linux 2
   instance_type = "t2.micro"
  key_name      = "MyLTemplate" # Replace with your key pair 
    associate_public_ip_address = true
    subnet_id = aws_subnet.photo_share_subnet.id
    vpc_security_group_ids = [ aws_security_group.photo_share_security_group.id ]
    user_data = data.template_file.user_data.rendered

  tags = {
    Name = "PhotoShareInstance"
  }
  
}

resource "aws_vpc" "photoshare_vpc" {
  cidr_block = "10.0.0.0/24"
  enable_dns_support = true
  enable_dns_hostnames = true
  tags = {
    Name = "PhotoShareVPC"
  }
}

resource "aws_internet_gateway" "photo_share_gateway" {
  vpc_id = aws_vpc.photoshare_vpc.id
  tags = {
    Name = "PhotoShareInternetGateway"
  } 
  
}

resource "aws_route_table" "photo_share_route_table" {
  vpc_id = aws_vpc.photoshare_vpc.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.photo_share_gateway.id
  }
  tags = {
    Name = "PhotoShareRouteTable"
  }
}

resource "aws_subnet" "photo_share_subnet" {
  vpc_id            = aws_vpc.photoshare_vpc.id
  cidr_block        = "10.0.0.0/24"
  availability_zone = "eu-west-1a"
  map_public_ip_on_launch = true
  tags = {
    Name = "PhotoShareSubnet"
  }
}
resource "aws_route_table_association" "photo_share_route_table_association" {
  subnet_id      = aws_subnet.photo_share_subnet.id
  route_table_id = aws_route_table.photo_share_route_table.id
}


resource "aws_security_group" "photo_share_security_group" {
  name        = "photo_share_security_group"
  description = "Allow HTTP and SSH access"
  vpc_id      = aws_vpc.photoshare_vpc.id

  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"] # Allow SSH from anywhere
  
}

ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
}

ingress {
    from_port   = 3000
    to_port     = 3000
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
}

ingress {
    from_port   = 9090
    to_port     = 9090
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
}

ingress {
    from_port   = 9093
    to_port     = 9093
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
}

ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
}
egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1" # Allow all outbound traffic
    cidr_blocks = ["0.0.0.0/0"]
}

  tags = {
    Name = "PhotoShareSecurityGroup"
  }
}


output "instance_ip" {
  value = "https://${aws_instance.photo_share_instance.public_ip}.sslip.io"
}