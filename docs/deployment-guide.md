# Deployment Guide: Render (Backend) & Vercel (Frontend)

This guide provides step-by-step instructions for deploying **PortFlow** with the **FastAPI Backend on Render** and the **React Frontend on Vercel**.

---

## Part 1: Deploy Backend on Render

Render hosts the FastAPI service (`src/backend/app/main.py`).

### Option A: Using Render Blueprints (Recommended)

1. Push your repository to **GitHub**.
2. Log in to [Render Dashboard](https://dashboard.render.com/).
3. Click **New +** and select **Blueprint**.
4. Connect your GitHub repository (`bob-ai-hackathon-Innovexa`).
5. Render will automatically detect `render.yaml` and configure the Web Service:
   - **Name**: `portflow-backend`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn src.backend.app.main:app --host 0.0.0.0 --port $PORT`
6. Click **Apply**.
7. Once deployed, Render will provide a service URL (e.g. `https://portflow-backend.onrender.com`).
8. Verify deployment by visiting `https://<your-render-url>/health` in your browser. You should see `{"status":"ok","service":"portflow-api"}`.

### Option B: Manual Setup on Render

1. On [Render Dashboard](https://dashboard.render.com/), click **New +** -> **Web Service**.
2. Connect your GitHub repository.
3. Configure the following fields:
   - **Name**: `portflow-backend`
   - **Language**: `Python 3`
   - **Branch**: `main` (or your default branch)
   - **Region**: Select closest region (e.g. Oregon)
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn src.backend.app.main:app --host 0.0.0.0 --port $PORT`
4. Under **Environment Variables**, add:
   - `PYTHONPATH`: `.`
   - *(Optional for IBM watsonx.ai)*: `WATSONX_URL`, `WATSONX_API_KEY`, `WATSONX_PROJECT_ID`
5. Click **Create Web Service**.

---

## Part 2: Deploy Frontend on Vercel

Vercel hosts the React + Vite dashboard (`src/frontend`).

### Setup Steps on Vercel

1. Log in to [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New...** -> **Project**.
3. Import your GitHub repository (`bob-ai-hackathon-Innovexa`).
4. In the **Configure Project** settings:
   - **Framework Preset**: Vite
   - **Root Directory**: Click *Edit* and select `src/frontend` (or leave as root if using top-level configuration).
   - **Build and Output Settings**:
     - Build Command: `npm run build`
     - Output Directory: `dist`
5. Expand **Environment Variables** and add:
   - **Key**: `VITE_API_BASE_URL`
   - **Value**: `https://<your-render-backend-url>.onrender.com` *(replace with your actual Render URL)*
6. Click **Deploy**.
7. Vercel will build the frontend and provide a URL (e.g. `https://portflow-frontend.vercel.app`).

---

## Part 3: Verification & Testing

1. Open your Vercel URL in a web browser.
2. Open Browser Developer Tools (F12) -> **Network** tab.
3. Verify that the dashboard successfully fetches data from your Render API (e.g. requests to `https://<your-render-url>/api/v1/timeline` and `/api/v1/hotspots`).
4. Test interactive scenario loading and shift supervisor summary generation.

---

## Troubleshooting

- **CORS Error in Browser Console**:
  - Ensure CORS middleware is enabled in `src/backend/app/main.py` (included by default).
  - Ensure `VITE_API_BASE_URL` in Vercel does not end with a trailing slash (e.g., use `https://portflow-backend.onrender.com`, not `https://portflow-backend.onrender.com/`).

- **Render Service Sleeping (Free Tier)**:
  - Render free tier web services spin down after 15 minutes of inactivity. The first request after sleep may take ~30 seconds to wake up.

- **Vite Environment Variable Not Updating**:
  - Vite bakes `VITE_*` environment variables at build time. If you update `VITE_API_BASE_URL` in Vercel, trigger a **Redeploy** on Vercel.
