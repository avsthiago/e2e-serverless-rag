# Makefile for building and pushing the Docker image to ECR

# You can override the variables being assigned using ?= by passing their values via command line or envvars
AWS_ACCOUNT_ID ?= $(shell aws sts get-caller-identity --query Account --output text)
REGION ?= $(shell aws configure get region)
IMAGE_NAME := house-rag
TAG ?= 0.0.8

ECR_URI := $(AWS_ACCOUNT_ID).dkr.ecr.$(REGION).amazonaws.com/$(IMAGE_NAME):$(TAG)

build:
	docker build --platform linux/amd64 -t $(IMAGE_NAME):$(TAG) .

tag:
	docker tag $(IMAGE_NAME):$(TAG) $(ECR_URI)

login:
	aws ecr get-login-password --region $(REGION) | docker login --username AWS --password-stdin $(AWS_ACCOUNT_ID).dkr.ecr.$(REGION).amazonaws.com

push: login
	docker push $(ECR_URI)

all: build tag push
