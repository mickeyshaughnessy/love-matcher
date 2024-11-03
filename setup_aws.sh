#!/bin/bash
set -e

for tool in aws jq; do
    command -v $tool >/dev/null || brew install $tool
done

aws sts get-caller-identity >/dev/null || { echo "Run: aws configure"; exit 1; }

echo "🚀 Love Matcher Setup"

# Get or create VPC
VPC_ID=$(aws ec2 describe-vpcs --filters "Name=tag:Name,Values=love-matcher-vpc" --query 'Vpcs[0].VpcId' --output text)
if [ "$VPC_ID" = "None" ]; then
    VPC_ID=$(aws ec2 create-vpc --cidr-block 10.0.0.0/16 --query 'Vpc.VpcId' --output text)
    aws ec2 create-tags --resources $VPC_ID --tags Key=Name,Value=love-matcher-vpc
    aws ec2 modify-vpc-attribute --vpc-id $VPC_ID --enable-dns-hostnames
    
    # Create and attach internet gateway
    IGW_ID=$(aws ec2 create-internet-gateway --query 'InternetGateway.InternetGatewayId' --output text)
    aws ec2 attach-internet-gateway --vpc-id $VPC_ID --internet-gateway-id $IGW_ID
    
    # Create subnet and route table
    SUBNET_ID=$(aws ec2 create-subnet --vpc-id $VPC_ID --cidr-block 10.0.1.0/24 --availability-zone us-east-1a --query 'SubnetId' --output text)
    RTB_ID=$(aws ec2 create-route-table --vpc-id $VPC_ID --query 'RouteTable.RouteTableId' --output text)
    aws ec2 create-route --route-table-id $RTB_ID --destination-cidr-block 0.0.0.0/0 --gateway-id $IGW_ID
    aws ec2 associate-route-table --route-table-id $RTB_ID --subnet-id $SUBNET_ID
else
    SUBNET_ID=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --query 'Subnets[0].SubnetId' --output text)
fi

# Create or get security group
SG_NAME="lovematcher-web"
SG_ID=$(aws ec2 describe-security-groups --filters "Name=group-name,Values=$SG_NAME" "Name=vpc-id,Values=$VPC_ID" --query 'SecurityGroups[0].GroupId' --output text)
if [ "$SG_ID" = "None" ]; then
    SG_ID=$(aws ec2 create-security-group --group-name $SG_NAME --description "Love Matcher Web" --vpc-id $VPC_ID --query 'GroupId' --output text)
    
    # Allow SSH from current IP
    MY_IP=$(curl -s https://checkip.amazonaws.com)
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 22 --cidr $MY_IP/32
    
    # Allow HTTP/HTTPS from anywhere
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 80 --cidr 0.0.0.0/0
    aws ec2 authorize-security-group-ingress --group-id $SG_ID --protocol tcp --port 443 --cidr 0.0.0.0/0
fi

# Launch EC2 if not exists
INSTANCE_ID=$(aws ec2 describe-instances --filters "Name=tag:Name,Values=love-matcher-app" "Name=instance-state-name,Values=running" --query 'Reservations[0].Instances[0].InstanceId' --output text)
if [ "$INSTANCE_ID" = "None" ]; then
    INSTANCE_ID=$(aws ec2 run-instances \
        --image-id ami-0c7217cdde317cfec \
        --instance-type t2.medium \
        --subnet-id $SUBNET_ID \
        --security-group-ids $SG_ID \
        --tag-specifications 'ResourceType=instance,Tags=[{Key=Name,Value=love-matcher-app}]' \
        --query 'Instances[0].InstanceId' --output text)
    aws ec2 wait instance-running --instance-ids $INSTANCE_ID
fi

# Get or create Elastic IP
EIP=$(aws ec2 describe-addresses --filters "Name=instance-id,Values=$INSTANCE_ID" --query 'Addresses[0].PublicIp' --output text)
if [ "$EIP" = "None" ]; then
    ALLOC_ID=$(aws ec2 allocate-address --domain vpc --query 'AllocationId' --output text)
    aws ec2 associate-address --instance-id $INSTANCE_ID --allocation-id $ALLOC_ID
    EIP=$(aws ec2 describe-addresses --allocation-ids $ALLOC_ID --query 'Addresses[0].PublicIp' --output text)
fi

echo "✨ Done! Server IP: $EIP"