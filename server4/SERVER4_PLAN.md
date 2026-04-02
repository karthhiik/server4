# Server 4 - Presentation/Pitch Deck Backend (FastAPI)

## Overview
Server 4 is the backend service for the Pitch Deck/Presentation module. Built with FastAPI, it handles AI-powered slide generation, content creation, design management, and export functionality. It includes two MCP (Model Context Protocol) servers: one for slide content generation and one for presentation assembly/export.

## Architecture

```
server4/
├── main.py                          # FastAPI app entry point
├── requirements.txt                 # Python dependencies
├── .env.example                     # Environment variables template
├── Dockerfile                       # Container configuration
│
├── app/
│   ├── __init__.py
│   ├── config.py                    # Settings & env configuration
│   ├── database.py                  # Database connection (Azure Cosmos DB)
│   ├── dependencies.py              # FastAPI dependency injection
│   │
│   ├── models/                      # Pydantic models & DB schemas
│   │   ├── __init__.py
│   │   ├── presentation.py          # Presentation, Slide, Theme models
│   │   ├── export.py                # Export job models
│   │   └── user.py                  # User presentation preferences
│   │
│   ├── routers/                     # API route handlers
│   │   ├── __init__.py
│   │   ├── presentations.py         # CRUD for presentations
│   │   ├── generation.py            # AI content generation endpoints
│   │   ├── slides.py                # Individual slide operations
│   │   ├── themes.py                # Theme management
│   │   ├── export.py                # Export to PPTX/PDF/HTML/PNG
│   │   └── templates.py             # Presentation templates
│   │
│   ├── services/                    # Business logic
│   │   ├── __init__.py
│   │   ├── ai_generator.py          # AI slide content generation
│   │   ├── content_optimizer.py     # Content refinement & enhancement
│   │   ├── layout_engine.py         # Smart layout selection
│   │   ├── export_service.py        # Multi-format export logic
│   │   ├── template_service.py      # Template management
│   │   ├── image_service.py         # AI image generation (Premium)
│   │   └── presentation_service.py  # Core presentation CRUD
│   │
│   ├── mcp/                         # Model Context Protocol servers
│   │   ├── __init__.py
│   │   ├── slide_content_mcp/       # MCP Server 1: Slide Content
│   │   │   ├── __init__.py
│   │   │   ├── server.py            # MCP server entry point
│   │   │   ├── tools.py             # MCP tools definition
│   │   │   │   ├── generate_outline     # Generate presentation outline from topic
│   │   │   │   ├── generate_slide       # Generate content for single slide
│   │   │   │   ├── refine_content       # Improve/rewrite slide content
│   │   │   │   ├── generate_notes       # Create speaker notes (Premium)
│   │   │   │   ├── suggest_visuals      # Suggest charts/images for slides
│   │   │   │   └── translate_content    # Translate slide content
│   │   │   └── prompts.py           # System prompts for each tool
│   │   │
│   │   └── presentation_mcp/        # MCP Server 2: Presentation Assembly
│   │       ├── __init__.py
│   │       ├── server.py            # MCP server entry point
│   │       ├── tools.py             # MCP tools definition
│   │       │   ├── assemble_deck        # Assemble full presentation from slides
│   │       │   ├── apply_theme          # Apply theme to presentation
│   │       │   ├── export_pptx          # Export to PowerPoint format
│   │       │   ├── export_pdf           # Export to PDF format
│   │       │   ├── export_html          # Export to interactive HTML
│   │       │   ├── export_images        # Export slides as PNG images
│   │       │   ├── generate_thumbnail   # Create presentation thumbnail
│   │       │   └── validate_deck        # Validate deck structure & content
│   │       └── prompts.py           # System prompts for assembly
│   │
│   ├── utils/                       # Utility functions
│   │   ├── __init__.py
│   │   ├── auth.py                  # JWT token validation (shared with Server 1)
│   │   ├── pptx_builder.py          # python-pptx presentation builder
│   │   ├── pdf_renderer.py          # PDF generation using WeasyPrint/ReportLab
│   │   ├── html_renderer.py         # Interactive HTML slide renderer
│   │   ├── image_renderer.py        # Slide-to-image converter
│   │   └── storage.py               # Azure Blob Storage for exports
│   │
│   └── middleware/                   # FastAPI middleware
│       ├── __init__.py
│       ├── cors.py                  # CORS configuration
│       ├── rate_limit.py            # Rate limiting per user
│       └── auth_middleware.py       # Authentication middleware
│
└── tests/                           # Test suite
    ├── __init__.py
    ├── test_presentations.py
    ├── test_generation.py
    ├── test_export.py
    └── test_mcp_tools.py
```

## API Endpoints

### Presentations CRUD
```
POST   /api/presentations              # Create new presentation
GET    /api/presentations               # List user's presentations
GET    /api/presentations/{id}          # Get presentation details
PUT    /api/presentations/{id}          # Update presentation
DELETE /api/presentations/{id}          # Delete presentation
POST   /api/presentations/{id}/duplicate # Duplicate presentation
```

### AI Generation
```
POST   /api/generate/outline            # Generate presentation outline from input
POST   /api/generate/slide              # Generate content for a single slide
POST   /api/generate/refine             # Refine/improve slide content
POST   /api/generate/notes              # Generate speaker notes (Premium)
POST   /api/generate/visuals            # Suggest/generate visuals (Premium)
```

### Slides
```
POST   /api/presentations/{id}/slides          # Add slide
PUT    /api/presentations/{id}/slides/{sid}     # Update slide
DELETE /api/presentations/{id}/slides/{sid}     # Remove slide
PUT    /api/presentations/{id}/slides/reorder   # Reorder slides
```

### Themes
```
GET    /api/themes                      # List available themes
GET    /api/themes/{id}                 # Get theme details
POST   /api/themes/custom               # Create custom theme (Premium)
PUT    /api/presentations/{id}/theme     # Apply theme to presentation
```

### Export
```
POST   /api/export/pptx/{id}           # Export as PowerPoint
POST   /api/export/pdf/{id}            # Export as PDF
POST   /api/export/html/{id}           # Export as interactive HTML (Premium)
POST   /api/export/images/{id}         # Export as PNG images (Premium)
GET    /api/export/status/{job_id}     # Check export job status
GET    /api/export/download/{job_id}   # Download exported file
```

### Templates
```
GET    /api/templates                   # List available templates
GET    /api/templates/{id}              # Get template details
POST   /api/templates/from-presentation # Save presentation as template (Premium)
```

## MCP Server Details

### MCP 1: Slide Content Server
- **Purpose**: AI-powered content generation for individual slides and outlines
- **Transport**: stdio (local) or SSE (remote)
- **AI Models**: Claude (primary), with fallback routing
- **Tools**:
  - `generate_outline` - Takes topic, audience, purpose → returns structured outline
  - `generate_slide` - Takes slide title, context, layout → returns formatted content
  - `refine_content` - Takes existing content, instructions → returns improved version
  - `generate_notes` - Takes slide content → returns speaker talking points
  - `suggest_visuals` - Takes slide content → returns chart/image suggestions
  - `translate_content` - Takes content, target language → returns translated version

### MCP 2: Presentation Assembly Server
- **Purpose**: Presentation assembly, theming, validation, and multi-format export
- **Transport**: stdio (local) or SSE (remote)
- **Tools**:
  - `assemble_deck` - Combines slides into cohesive presentation structure
  - `apply_theme` - Applies color scheme, fonts, layouts to all slides
  - `export_pptx` - Generates .pptx file using python-pptx
  - `export_pdf` - Generates PDF using WeasyPrint
  - `export_html` - Generates interactive HTML presentation (reveal.js based)
  - `export_images` - Renders each slide as high-res PNG
  - `generate_thumbnail` - Creates preview thumbnail for gallery
  - `validate_deck` - Checks structure, content quality, consistency

## Technology Stack

| Component | Technology |
|-----------|-----------|
| Framework | FastAPI 0.110+ |
| Python | 3.11+ |
| Database | Azure Cosmos DB (MongoDB API) |
| File Storage | Azure Blob Storage |
| AI/LLM | Claude API (Anthropic SDK) |
| PPTX Generation | python-pptx |
| PDF Generation | WeasyPrint / ReportLab |
| HTML Presentations | reveal.js templates |
| Image Rendering | Playwright / Pillow |
| MCP SDK | mcp[cli] (Python SDK) |
| Auth | JWT (shared secret with Server 1) |
| Task Queue | Azure Service Bus (for async exports) |
| Caching | Redis (for generation caching) |

## Standard vs Premium Mode Differences

| Feature | Standard | Premium |
|---------|----------|---------|
| AI generation quality | Base model | Enhanced multi-pass |
| Slide count limit | Up to 15 | Up to 50 |
| Theme selection | 8 built-in themes | Custom + built-in |
| Speaker notes | No | Yes |
| Export formats | PPTX, PDF | PPTX, PDF, HTML, PNG |
| Image generation | No | AI-generated visuals |
| Custom branding | No | Logo, colors, fonts |
| Templates | Basic | Full library |
| Content refinement | 1 pass | Multi-pass with feedback |

## Environment Variables

```env
# Server
PORT=8003
ENV=development

# Database
COSMOS_CONNECTION_STRING=
COSMOS_DATABASE_NAME=barise_presentations

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=
AZURE_STORAGE_CONTAINER=presentation-exports

# AI
ANTHROPIC_API_KEY=
AI_MODEL=claude-sonnet-4-20250514

# Auth
JWT_SECRET=<shared with server1>

# MCP
MCP_SLIDE_CONTENT_PORT=5010
MCP_PRESENTATION_PORT=5011

# Redis
REDIS_URL=redis://localhost:6379/2

# Rate Limiting
RATE_LIMIT_STANDARD=20/hour
RATE_LIMIT_PREMIUM=100/hour
```

## Frontend Integration

The frontend (lliveupdatedstreaming) connects to Server 4 via:
- **Base URL**: `VITE_API_BASE_URL4` (default: `http://127.0.0.1:8003` / production Azure URL)
- **Auth**: JWT token from `localStorage['jwt_token']` sent as `Authorization: Bearer <token>`
- **Real-time progress**: WebSocket at `/ws/generation/{task_id}` for generation progress updates

## Deployment

- **Local**: `uvicorn main:app --host 0.0.0.0 --port 8003 --reload`
- **Production**: Azure App Service (Canada Central region, consistent with other servers)
- **MCP Servers**: Run as subprocess from main FastAPI app or as separate services

## Next Steps (Implementation Order)

1. Set up FastAPI project structure with `main.py`, config, and dependencies
2. Create Pydantic models for presentations, slides, themes
3. Implement database connection and CRUD operations
4. Build MCP Server 1 (slide_content_mcp) with outline and content generation tools
5. Build MCP Server 2 (presentation_mcp) with assembly and export tools
6. Implement PPTX export using python-pptx
7. Implement PDF export
8. Add Premium features (custom themes, speaker notes, HTML export, image export)
9. Connect frontend to Server 4 API endpoints
10. Add WebSocket progress tracking for generation
11. Deploy to Azure App Service
