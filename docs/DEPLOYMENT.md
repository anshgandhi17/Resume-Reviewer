# Resume Analyzer - Deployment Guide

## Table of Contents
- [Deployment Options](#deployment-options)
- [Local Development](#local-development)
- [Hybrid Deployment](#hybrid-deployment)
- [Full Cloud Deployment](#full-cloud-deployment)
- [Environment Variables](#environment-variables)
- [Monitoring and Logging](#monitoring-and-logging)
- [Backup Strategies](#backup-strategies)

## Deployment Options

### Option 1: Local Development
Run everything locally for development and testing.

### Option 2: Hybrid Deployment (Recommended)
- Frontend: Hosted on Vercel/Netlify
- Backend: Hosted on AWS/GCP/Azure
- Ollama: User's local machine

### Option 3: Full Cloud Deployment
Host all services including Ollama on cloud infrastructure.

## Local Development

See main [README.md](../README.md) for local development setup.

## Hybrid Deployment

TODO: Step-by-step guide for hybrid deployment.

### Frontend Deployment (Vercel)

TODO: Vercel deployment instructions.

### Backend Deployment (AWS/Docker)

TODO: Backend deployment instructions.

## Full Cloud Deployment

TODO: Complete cloud deployment guide.

## Environment Variables

### Backend

```env
# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Application Settings
UPLOAD_DIR=./uploads
VECTOR_DB_DIR=./vectordb
MAX_FILE_SIZE=10485760

# CORS
CORS_ORIGINS=["http://localhost:3000"]
```

### Frontend

```env
NEXT_PUBLIC_API_URL=http://localhost:8000/api
```

## Monitoring and Logging

TODO: Monitoring setup with Arize Phoenix.

## Backup Strategies

TODO: Vector database and data backup procedures.
