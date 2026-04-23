# Javaab Azure Infrastructure Setup Guide

Welcome! This guide will walk you through setting up all the necessary Azure infrastructure for the Javaab platform. It assumes you are starting from scratch.

## 1. Prerequisites

First, we need to install the required tools: **Azure CLI**, **Python**, and **uv** (a fast Python package manager).

### Install Azure CLI
**macOS:**
```bash
brew install azure-cli
```
**Windows:**
Download the installer from [https://aka.ms/installazurecliwindows](https://aka.ms/installazurecliwindows)

Verify the installation:
```bash
az --version
```

### Install Python 3.12
**macOS:**
```bash
brew install python@3.12
```
**Windows:**
Download from [python.org/downloads](https://www.python.org/downloads/)

### Install `uv` Package Manager
```bash
pip install uv
```

---

## 2. Authentication & Core Setup

Log in to your Azure account and select your subscription.

```bash
# Log in to Azure (this will open a browser window)
az login

# Set your active subscription (replace with your actual Subscription ID)
az account set --subscription "YOUR_SUBSCRIPTION_ID"
```

### Create a Resource Group
A resource group is a container that holds related resources for an Azure solution. We'll use `javaab-rg` in the `centralindia` region.

```bash
az group create \
 --name javaab-rg \
 --location centralindia
```

Verify it was created:
```bash
az group show --name javaab-rg
```

---

## 3. Storage Account

This is used for storing files, such as PDFs and images.

```bash
# Create the storage account
az storage account create \
 --name javaabstorage \
 --resource-group javaab-rg \
 --location centralindia \
 --sku Standard_LRS \
 --kind StorageV2

# Get the connection string. ⚠️ SAVE THIS for your .env file!
az storage account show-connection-string \
 --name javaabstorage \
 --resource-group javaab-rg \
 --query connectionString -o tsv
```

---

## 4. Azure AI Search

Used for semantic search and Retrieval-Augmented Generation (RAG).

```bash
# Create the search service
az search service create \
 --name javaab-search \
 --resource-group javaab-rg \
 --location centralindia \
 --sku basic

# Get the admin key. ⚠️ SAVE THIS for your .env file!
az search admin-key show \
 --service-name javaab-search \
 --resource-group javaab-rg \
 --query primaryKey -o tsv
```

---

## 5. Azure OpenAI Services

We need to register the Cognitive Services provider and create an OpenAI account to deploy our AI models.

```bash
# Register the provider
az provider register --namespace Microsoft.CognitiveServices
az provider show --namespace Microsoft.CognitiveServices --query "registrationState"

# Create the OpenAI account
az cognitiveservices account create \
 --name javaab-openai \
 --resource-group javaab-rg \
 --location eastus \
 --kind OpenAI \
 --sku S0

# Get the endpoint and keys. ⚠️ SAVE THESE for your .env file!
az cognitiveservices account show \
 --name javaab-openai \
 --resource-group javaab-rg \
 --query properties.endpoint -o tsv

az cognitiveservices account keys list \
 --name javaab-openai \
 --resource-group javaab-rg \
 --query key1 -o tsv
```

### Deploy Models

We need an embedding model for search and a language model for processing.

```bash
# Deploy the embedding model (text-embedding-3-small)
az cognitiveservices account deployment create \
 --name javaab-openai \
 --resource-group javaab-rg \
 --deployment-name text-embedding-3-small \
 --model-name text-embedding-3-small \
 --model-version "1" \
 --model-format OpenAI \
 --sku-capacity 120 \
 --sku-name Standard

# Deploy the LLM (gpt-4.1-mini) for OCR and classification
az cognitiveservices account deployment create \
 --name javaab-openai \
 --resource-group javaab-rg \
 --deployment-name gpt-4.1-mini \
 --model-name gpt-4.1-mini \
 --model-version "2025-04-14" \
 --model-format OpenAI \
 --sku-capacity 10 \
 --sku-name GlobalStandard
```

---

## 6. Redis Cache

Used for caching frequently accessed data and speeding up the application.

```bash
# Register the cache provider
az provider register --namespace Microsoft.Cache
az provider show --namespace Microsoft.Cache --query "registrationState"

# Create the Redis cache
az redis create \
 --name javaab-cache \
 --resource-group javaab-rg \
 --location centralindia \
 --sku Basic \
 --vm-size C0

# ⏳ NOTE: This takes ~15 minutes to complete! 
# Get host and key after it finishes. ⚠️ SAVE THESE for your .env file!
az redis show \
 --name javaab-cache \
 --resource-group javaab-rg \
 --query hostName -o tsv

az redis list-keys \
 --name javaab-cache \
 --resource-group javaab-rg \
 --query primaryKey -o tsv
```

---

## 7. Cosmos DB (Database)

We use Cosmos DB to store user data, chat conversations, and support tickets.

```bash
# Register the DocumentDB provider
az provider register --namespace Microsoft.DocumentDB
az provider show --namespace Microsoft.DocumentDB --query "registrationState"

# Create the Cosmos DB account
az cosmosdb create \
 --name javaab-db \
 --resource-group javaab-rg \
 --locations regionName=centralindia \
 --enable-free-tier true \
 --default-consistency-level Session

# Create the SQL Database
az cosmosdb sql database create \
 --account-name javaab-db \
 --resource-group javaab-rg \
 --name javaab
```

### Create Database Containers

```bash
# Users container
az cosmosdb sql container create \
 --account-name javaab-db \
 --resource-group javaab-rg \
 --database-name javaab \
 --name users \
 --partition-key-path "/userId"

# Conversations container
az cosmosdb sql container create \
 --account-name javaab-db \
 --resource-group javaab-rg \
 --database-name javaab \
 --name conversations \
 --partition-key-path "/studentId"

# Tickets container
az cosmosdb sql container create \
 --account-name javaab-db \
 --resource-group javaab-rg \
 --database-name javaab \
 --name tickets \
 --partition-key-path "/studentId"
```

---

## 8. Deployment & Security Infrastructure

Set up registries for Docker containers and a Key Vault for secrets.

```bash
# Create Azure Container Registry (for storing Docker images)
az provider register --namespace Microsoft.ContainerRegistry

az acr create \
 --name javaabregistry \
 --resource-group javaab-rg \
 --location centralindia \
 --sku Basic \
 --admin-enabled true

# Create Azure Key Vault (for securely storing secrets)
az provider register --namespace Microsoft.KeyVault

az keyvault create \
 --name javaab-vault \
 --resource-group javaab-rg \
 --location centralindia \
 --sku standard
```

---

## 9. Container Apps Environment

Finally, create the environment where our frontend and backend containers will run.

```bash
# Register operational insights provider
az provider register -n Microsoft.OperationalInsights --wait

# Create the Container Apps environment
az containerapp env create \
 --name javaab-env \
 --resource-group javaab-rg \
 --location centralindia
```

**Congratulations!** You have finished setting up the foundational Azure resources for Javaab. Make sure to copy all the keys, connection strings, and endpoints you saved into your backend `.env` file.