# Photography & API Portfolio

A full-stack portfolio application designed to showcase photography work alongside software engineering capabilities. The project features a public-facing gallery and a secure administrative dashboard with automated, AI-driven metadata generation.

## Architecture & Technology Stack

### Frontend
- **Framework:** React with Vite build system
- **Styling:** Custom Vanilla CSS with responsive design principles
- **Deployment:** Cloudflare Pages
- **Features:** 
  - Dynamic image gallery with category and tag-based filtering
  - Client-side routing with React Router
  - Optimized image loading and lightbox viewing

### Backend
- **Framework:** FastAPI (Python)
- **Database:** MongoDB Atlas via Beanie ODM (Asynchronous object-document mapper)
- **Storage:** Cloudflare R2 (S3-compatible object storage)
- **Authentication:** JWT-based secure authentication using passlib and bcrypt
- **Deployment:** Render
- **Features:**
  - Automated deployment pipeline via Render native integration
  - Rate limiting and CORS configurations for security
  - In-memory caching for performance optimization

### AI Integration
- **Service:** Google Gemini API
- **Implementation:** Custom Singleton Python service implementing exponential backoff and graceful degradation
- **Functionality:** Automated generation of image metadata (titles, descriptions, categories, contextual tags, and qualitative ratings) directly upon upload within the admin dashboard.

## Project Structure

```
portfolio/
├── frontend/             # Single Page Application (React)
│   ├── src/
│   │   ├── api/          # API client and request configuration
│   │   ├── components/   # Reusable UI components
│   │   ├── pages/        # Route components (Home, Admin, Login)
│   │   └── styles/       # Application styling
│   └── public/           # Static assets and SPA routing configurations
│
├── backend/              # RESTful API (FastAPI)
│   ├── app/
│   │   ├── api/          # Route handlers (auth, images, ai analysis)
│   │   ├── core/         # Configuration, security, and database initialization
│   │   ├── models/       # Beanie/MongoDB document schemas
│   │   ├── schemas/      # Pydantic data validation schemas
│   │   └── services/     # External integrations (R2 storage, Gemini AI)
│   ├── Dockerfile        # Production container configuration
│   └── main.py           # Application entry point
│
└── .github/workflows/    # CI/CD pipelines
```

## Features and Capabilities

1. **Public Portfolio Gallery:**
   - High-performance grid layout for viewing images.
   - Dynamic filtering by context-aware tags and defined categories.
   - Responsive design tailored for cross-device compatibility.

2. **Administrative Dashboard:**
   - Protected route accessible only via authenticated session.
   - Batch upload capabilities (up to 20 images simultaneously).
   - Full CRUD (Create, Read, Update, Delete) operations on image objects.

3. **Automated Metadata Curation:**
   - Integration with Google Gemini to analyze image bytes in real-time.
   - Automatically populates metadata fields, reducing manual data entry.
   - Configured with robust error handling to guarantee upload continuity during API downtime.

## Deployment Architecture

The application utilizes a distributed deployment model engineered for performance, security, and scalability.

- **Frontend Hosting (Cloudflare Pages):** The React SPA is continuously deployed via Cloudflare Pages. This ensures the static assets are cached globally across Cloudflare's edge network, providing low-latency delivery and automatic SSL encryption.
- **Backend Hosting (Render):** The FastAPI Python backend is deployed as a Web Service on Render. It operates securely with environment-driven configurations and connects directly to the MongoDB Atlas cluster.
- **Continuous Integration/Continuous Deployment (CI/CD):**
  - **Frontend:** GitHub Actions pipeline triggers on main branch pushes to build the Vite bundle and deploy directly to the Cloudflare network.
  - **Backend:** Native Render GitHub integration automatically detects updates, and it rebuilds, and performs zero-downtime deployments.

## Local Development Setup

To run this project locally, ensure you have Python 3.12+ and Node.js installed.

### Environment Configuration
The backend requires a `.env` file detailing database URIs, storage keys, and API tokens. Reference the `.env.example` (or define the requisite keys) in the `backend/` directory.

### Running the Services

A convenience script `start_services.sh` is provided to initialize both environments. Alternatively, start them manually:

**1. Backend Initialization:**
```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
fastapi dev main.py
```

**2. Frontend Initialization:**
```bash
cd frontend
npm install
npm run dev
```

## License

This project is proprietary and intended as a personal showcase of coding and photographic work. Please reach out for permissions regarding source code use or replication.
