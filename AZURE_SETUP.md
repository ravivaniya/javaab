# Install Azure CLI

# macOS:

brew install azure-cli

# Windows: download from https://aka.ms/installazurecliwindows

# Verify

az --version

# Install Python 3.12

# macOS: brew install python@3.12

# Windows: python.org/downloads

# Install uv (fast Python package manager)

pip install uv

az login
az account set --subscription "YOUR_SUBSCRIPTION_ID"

# Create resource group in Central India

az group create \
 --name javaab-rg \
 --location centralindia

# Verify

az group show --name javaab-rg

# This command we did via GUI

az storage account create \
 --name javaabstorage \
 --resource-group javaab-rg \
 --location centralindia \
 --sku Standard_LRS \
 --kind StorageV2

# Get connection string (save this!)

az storage account show-connection-string \
 --name javaabstorage \
 --resource-group javaab-rg \
 --query connectionString -o tsv

az search service create \
 --name javaab-search \
 --resource-group javaab-rg \
 --location centralindia \
 --sku basic

# Get admin key (save this!)

az search admin-key show \
 --service-name javaab-search \
 --resource-group javaab-rg \
 --query primaryKey -o tsv

az provider register --namespace Microsoft.CognitiveServices
az provider show --namespace Microsoft.CognitiveServices --query "registrationState"

az cognitiveservices account create \
 --name javaab-openai \
 --resource-group javaab-rg \
 --location eastus \
 --kind OpenAI \
 --sku S0

# Get endpoint and key

az cognitiveservices account show \
 --name javaab-openai \
 --resource-group javaab-rg \
 --query properties.endpoint -o tsv

az cognitiveservices account keys list \
 --name javaab-openai \
 --resource-group javaab-rg \
 --query key1 -o tsv

# Deploy embedding model

az cognitiveservices account deployment create \
 --name javaab-openai \
 --resource-group javaab-rg \
 --deployment-name text-embedding-3-small \
 --model-name text-embedding-3-small \
 --model-version "1" \
 --model-format OpenAI \
 --sku-capacity 120 \
 --sku-name Standard

# Deploy GPT-4.1-mini (for OCR + classification)

az cognitiveservices account deployment create \
 --name javaab-openai \
 --resource-group javaab-rg \
 --deployment-name gpt-4.1-mini \
 --model-name gpt-4.1-mini \
 --model-version "2025-04-14" \
 --model-format OpenAI \
 --sku-capacity 10 \
 --sku-name GlobalStandard

az provider register --namespace Microsoft.Cache

az provider show --namespace Microsoft.Cache --query "registrationState"

az redis create \
 --name javaab-cache \
 --resource-group javaab-rg \
 --location centralindia \
 --sku Basic \
 --vm-size C0

# This takes ~15 minutes. Get host and key after:

az redis show \
 --name javaab-cache \
 --resource-group javaab-rg \
 --query hostName -o tsv

az redis list-keys \
 --name javaab-cache \
 --resource-group javaab-rg \
 --query primaryKey -o tsv

az provider register --namespace Microsoft.DocumentDB

az provider show --namespace Microsoft.DocumentDB --query "registrationState"

az cosmosdb create \
 --name javaab-db \
 --resource-group javaab-rg \
 --locations regionName=centralindia \
 --enable-free-tier true \
 --default-consistency-level Session

az cosmosdb sql database create \
 --account-name javaab-db \
 --resource-group javaab-rg \
 --name javaab

az cosmosdb sql container create \
 --account-name javaab-db \
 --resource-group javaab-rg \
 --database-name javaab \
 --name users \
 --partition-key-path "/userId"

az cosmosdb sql container create \
 --account-name javaab-db \
 --resource-group javaab-rg \
 --database-name javaab \
 --name conversations \
 --partition-key-path "/studentId"

az cosmosdb sql container create \
 --account-name javaab-db \
 --resource-group javaab-rg \
 --database-name javaab \
 --name tickets \
 --partition-key-path "/studentId"
