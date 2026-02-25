# Short-Alpha Pod | Synthesis Matrix

A high-fidelity quantitative analysis terminal for detecting short-squeeze precursors and validating lag correlations.

## 🚀 Live Demo
[Link Placeholder: e.g., https://your-username.github.io/short-alpha-pod/]

## 🛠 Local Verification
To run the dashboard locally in a server environment (simulating a live host):
1. **Navigate to the docs folder**:
   ```bash
   cd docs
   ```
2. **Start a local server**:
   ```bash
   python -m http.server 8000
   ```
3. **Open in Browser**: [http://localhost:8000](http://localhost:8000)

## 📦 GitHub Pages Deployment
This project is configured to deploy via the `/docs` folder on the `main` branch.
1. Push this project to a new GitHub repository.
2. Go to **Settings** > **Pages**.
3. Under **Build and deployment** > **Branch**, select `main` and `/docs`.
4. Click **Save**.

## 📊 Project Structure
- `docs/`: Deployment folder containing the optimized `index.html` and `data/`.
- `data/`: Source raw data files.
- `stage*.py`: Python analysis agents for discovery, scouting, and synthesis.

## 🛡 Security & Privacy
- **No API Keys**: The frontend runs entirely on local/demo data.
- **Static Site**: No backend required for core dashboard functionality.

---
*Built with React, D3-style Visuals, and Multi-Agent Orchestration.*
