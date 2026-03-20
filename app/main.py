"""
Build Service - Microservice for building projects from code blocks
Port: 8003
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import json
import uuid
import shutil
from datetime import datetime

app = FastAPI(
    title="Resonant Genesis Build Service",
    description="Microservice for building projects from code blocks",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Storage directory for built projects
PROJECTS_DIR = "/tmp/resonant_projects"
os.makedirs(PROJECTS_DIR, exist_ok=True)


class CodeBlock(BaseModel):
    language: str
    code: str
    filename: Optional[str] = None


class BuildRequest(BaseModel):
    code_blocks: List[CodeBlock]
    project_name: Optional[str] = None
    project_type: Optional[str] = "web"  # web, react, node, python


class ProjectFile(BaseModel):
    path: str
    content: str
    language: str


class BuildResponse(BaseModel):
    project_id: str
    project_name: str
    project_type: str
    files: List[ProjectFile]
    entry_point: str
    created_at: str
    preview_url: Optional[str] = None


class ProjectListResponse(BaseModel):
    projects: List[Dict[str, Any]]


def detect_project_type(code_blocks: List[CodeBlock]) -> str:
    """Detect project type from code blocks"""
    languages = [b.language.lower() for b in code_blocks]
    
    if 'jsx' in languages or 'tsx' in languages:
        return 'react'
    elif 'html' in languages:
        return 'web'
    elif 'python' in languages or 'py' in languages:
        return 'python'
    elif 'javascript' in languages or 'js' in languages:
        if any('require(' in b.code or 'import' in b.code for b in code_blocks):
            return 'node'
        return 'web'
    return 'web'


def generate_filename(language: str, index: int) -> str:
    """Generate appropriate filename for language"""
    extensions = {
        'html': 'index.html',
        'htm': 'index.html',
        'css': 'styles.css',
        'javascript': 'script.js',
        'js': 'script.js',
        'jsx': 'App.jsx',
        'tsx': 'App.tsx',
        'typescript': 'index.ts',
        'ts': 'index.ts',
        'python': 'main.py',
        'py': 'main.py',
        'json': 'data.json',
    }
    
    base = extensions.get(language.lower(), f'file{index}.txt')
    return base


def create_project_structure(
    code_blocks: List[CodeBlock],
    project_type: str,
    project_name: str
) -> List[ProjectFile]:
    """Create project file structure from code blocks"""
    files = []
    used_filenames = set()
    
    # Track what we have
    has_html = any(b.language.lower() in ['html', 'htm'] for b in code_blocks)
    has_css = any(b.language.lower() == 'css' for b in code_blocks)
    has_js = any(b.language.lower() in ['javascript', 'js'] for b in code_blocks)
    has_jsx = any(b.language.lower() in ['jsx', 'tsx'] for b in code_blocks)
    
    for i, block in enumerate(code_blocks):
        lang = block.language.lower()
        
        # Use provided filename or generate one
        if block.filename:
            filename = block.filename
        else:
            filename = generate_filename(lang, i)
        
        # Handle duplicates
        base_filename = filename
        counter = 1
        while filename in used_filenames:
            name, ext = os.path.splitext(base_filename)
            filename = f"{name}_{counter}{ext}"
            counter += 1
        
        used_filenames.add(filename)
        
        files.append(ProjectFile(
            path=filename,
            content=block.code,
            language=lang
        ))
    
    # Generate index.html if we have JS/CSS but no HTML (for web projects)
    if project_type == 'web' and not has_html and (has_js or has_css):
        css_files = [f.path for f in files if f.language == 'css']
        js_files = [f.path for f in files if f.language in ['javascript', 'js']]
        
        css_links = '\n    '.join([f'<link rel="stylesheet" href="{f}">' for f in css_files])
        js_scripts = '\n    '.join([f'<script src="{f}"></script>' for f in js_files])
        
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name}</title>
    {css_links}
</head>
<body>
    <canvas id="game" width="600" height="400"></canvas>
    {js_scripts}
</body>
</html>"""
        
        files.insert(0, ProjectFile(
            path='index.html',
            content=html_content,
            language='html'
        ))
    
    # Generate React boilerplate if JSX but no HTML
    if project_type == 'react' and has_jsx and not has_html:
        # Add index.html for React
        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{project_name}</title>
</head>
<body>
    <div id="root"></div>
    <script src="https://unpkg.com/react@18/umd/react.development.js"></script>
    <script src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
    <script src="https://unpkg.com/@babel/standalone/babel.min.js"></script>
    <script type="text/babel" src="App.jsx"></script>
</body>
</html>"""
        
        files.insert(0, ProjectFile(
            path='index.html',
            content=html_content,
            language='html'
        ))
    
    # Add package.json for node/react projects
    if project_type in ['node', 'react']:
        package_json = {
            "name": project_name.lower().replace(' ', '-'),
            "version": "1.0.0",
            "description": f"Generated project: {project_name}",
            "main": "index.js" if project_type == 'node' else "src/index.js",
            "scripts": {
                "start": "node index.js" if project_type == 'node' else "react-scripts start",
                "build": "react-scripts build" if project_type == 'react' else "echo 'No build step'",
            },
            "dependencies": {}
        }
        
        if project_type == 'react':
            package_json["dependencies"] = {
                "react": "^18.2.0",
                "react-dom": "^18.2.0"
            }
        
        files.append(ProjectFile(
            path='package.json',
            content=json.dumps(package_json, indent=2),
            language='json'
        ))
    
    # Add requirements.txt for Python projects
    if project_type == 'python':
        files.append(ProjectFile(
            path='requirements.txt',
            content='# Add your dependencies here\n',
            language='text'
        ))
    
    return files


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "build-service"}


@app.post("/build", response_model=BuildResponse)
async def build_project(request: BuildRequest):
    """Build a project from code blocks"""
    try:
        # Generate project ID and name
        project_id = str(uuid.uuid4())
        project_name = request.project_name or f"Project-{project_id[:8]}"
        
        # Detect project type if not specified
        project_type = request.project_type or detect_project_type(request.code_blocks)
        
        # Create project structure
        files = create_project_structure(
            request.code_blocks,
            project_type,
            project_name
        )
        
        # Save project to disk
        project_dir = os.path.join(PROJECTS_DIR, project_id)
        os.makedirs(project_dir, exist_ok=True)
        
        for file in files:
            file_path = os.path.join(project_dir, file.path)
            os.makedirs(os.path.dirname(file_path) if os.path.dirname(file_path) else project_dir, exist_ok=True)
            with open(file_path, 'w') as f:
                f.write(file.content)
        
        # Save project metadata
        metadata = {
            "project_id": project_id,
            "project_name": project_name,
            "project_type": project_type,
            "files": [{"path": f.path, "language": f.language} for f in files],
            "created_at": datetime.utcnow().isoformat(),
        }
        
        with open(os.path.join(project_dir, '.project.json'), 'w') as f:
            json.dump(metadata, f, indent=2)
        
        # Determine entry point
        entry_point = 'index.html'
        if project_type == 'python':
            entry_point = 'main.py'
        elif project_type == 'node':
            entry_point = 'index.js'
        
        return BuildResponse(
            project_id=project_id,
            project_name=project_name,
            project_type=project_type,
            files=files,
            entry_point=entry_point,
            created_at=datetime.utcnow().isoformat(),
            preview_url=f"/projects/{project_id}/{entry_point}"
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/projects", response_model=ProjectListResponse)
async def list_projects():
    """List all built projects"""
    projects = []
    
    if os.path.exists(PROJECTS_DIR):
        for project_id in os.listdir(PROJECTS_DIR):
            metadata_path = os.path.join(PROJECTS_DIR, project_id, '.project.json')
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
                    projects.append(metadata)
    
    return ProjectListResponse(projects=projects)


@app.get("/projects/{project_id}")
async def get_project(project_id: str):
    """Get project details and files"""
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    metadata_path = os.path.join(project_dir, '.project.json')
    
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="Project not found")
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    # Load file contents
    files = []
    for file_info in metadata.get('files', []):
        file_path = os.path.join(project_dir, file_info['path'])
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            files.append({
                "path": file_info['path'],
                "language": file_info['language'],
                "content": content
            })
    
    metadata['files'] = files
    return metadata


@app.get("/projects/{project_id}/files")
async def get_all_project_files(project_id: str):
    """Get all files from a project"""
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    metadata_path = os.path.join(project_dir, '.project.json')
    
    if not os.path.exists(metadata_path):
        raise HTTPException(status_code=404, detail="Project not found")
    
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    # Load file contents
    files = []
    for file_info in metadata.get('files', []):
        file_path = os.path.join(project_dir, file_info['path'])
        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                content = f.read()
            files.append({
                "path": file_info['path'],
                "language": file_info.get('language', 'plaintext'),
                "content": content
            })
    
    return {
        "project_id": project_id,
        "files": files,
        "total_files": len(files)
    }


@app.get("/projects/{project_id}/files/{file_path:path}")
async def get_project_file(project_id: str, file_path: str):
    """Get a specific file from a project"""
    full_path = os.path.join(PROJECTS_DIR, project_id, file_path)
    
    if not os.path.exists(full_path):
        raise HTTPException(status_code=404, detail="File not found")
    
    with open(full_path, 'r') as f:
        content = f.read()
    
    return {"path": file_path, "content": content}


@app.put("/projects/{project_id}/files/{file_path:path}")
async def update_project_file(project_id: str, file_path: str, content: Dict[str, str]):
    """Update a file in a project"""
    full_path = os.path.join(PROJECTS_DIR, project_id, file_path)
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    
    if not os.path.exists(project_dir):
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create directory if needed
    os.makedirs(os.path.dirname(full_path) if os.path.dirname(full_path) else project_dir, exist_ok=True)
    
    with open(full_path, 'w') as f:
        f.write(content.get('content', ''))
    
    return {"status": "updated", "path": file_path}


@app.delete("/projects/{project_id}")
async def delete_project(project_id: str):
    """Delete a project"""
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    
    if not os.path.exists(project_dir):
        raise HTTPException(status_code=404, detail="Project not found")
    
    shutil.rmtree(project_dir)
    return {"status": "deleted", "project_id": project_id}


@app.post("/projects/{project_id}/download")
async def download_project(project_id: str):
    """Generate downloadable zip of project"""
    project_dir = os.path.join(PROJECTS_DIR, project_id)
    
    if not os.path.exists(project_dir):
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Create zip file
    zip_path = f"/tmp/{project_id}.zip"
    shutil.make_archive(f"/tmp/{project_id}", 'zip', project_dir)
    
    return {"download_url": f"/download/{project_id}.zip"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
