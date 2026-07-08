# RG Build Service

> **Part of the [ResonantGenesis](https://dev-swat.com) platform** — Microservice for building projects from code blocks.

[![Status: Production](https://img.shields.io/badge/Status-Production-brightgreen.svg)]()
[![Port: 8003](https://img.shields.io/badge/Port-8003-orange.svg)]()
[![License: RG Source Available](https://img.shields.io/badge/License-RG%20Source%20Available-blue.svg)](LICENSE.txt)

Compiles and builds user projects from code blocks submitted via the platform. Supports multi-file project assembly, build execution, and artifact storage.

## Quick Start

```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8003 --reload
```

## Deployment Status

- **Extracted from**: `genesis2026_production_backend/build_service/`
- **Server path**: `/home/deploy/RG_Build_Service`
- **Docker service**: `build_service`
- **Volume**: `build_projects:/tmp/resonant_projects`

---
**Organization**: [DevSwat-ResonantGenesis](https://github.com/DevSwat-ResonantGenesis) | **Platform**: [dev-swat.com](https://dev-swat.com)
