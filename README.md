# Project Management System with AI Document Processing

A modern, AI-powered project management system built with Flask and ChromaDB that allows users to create projects, upload PDF documents, and automatically process them into searchable embeddings.

## Features

### 🎯 Project Management
- Create projects with unique UUIDs
- Search projects by name or UUID
- Beautiful, responsive dashboard interface
- Project details pages with document management

### 📄 Document Processing
- Upload PDF documents to projects
- Automatic sentence extraction and parsing
- Table detection and extraction
- Real-time processing feedback

### 🧠 AI-Powered Embeddings
- Automatic embedding generation using Sentence Transformers
- ChromaDB integration for vector storage
- Organized by project and document structure
- View embeddings for each document

### 🎨 Modern UI/UX
- Professional, gradient-based design
- Responsive layout for all devices
- Interactive modals and animations
- Intuitive user experience

## Technology Stack

- **Backend**: Flask (Python)
- **Database**: ChromaDB (Vector Database)
- **AI/ML**: Sentence Transformers (all-MiniLM-L6-v2)
- **PDF Processing**: PyPDF2
- **Frontend**: HTML5, CSS3, JavaScript
- **Styling**: Custom CSS with modern design patterns

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup Instructions

1. **Clone or download the project**
   ```bash
   cd your-project-directory
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**
   ```bash
   python app.py
   ```

4. **Access the application**
   Open your browser and navigate to: `http://localhost:5000`

## Project Structure

```
PROJ.AI/
├── app.py                          # Main Flask application
├── requirements.txt                 # Python dependencies
├── README.md                       # This file
├── backend/                        # Backend modules
│   ├── __init__.py
│   ├── database.py                 # JSON-based data storage
│   ├── pdf_processor.py           # PDF text and table extraction
│   └── embeddings.py              # ChromaDB and embeddings management
├── templates/                      # HTML templates
│   ├── base.html                  # Base template with styling
│   ├── dashboard.html             # Main dashboard
│   └── project_details.html       # Project details page
├── data/                          # JSON data storage
├── uploads/                       # Temporary file uploads
└── chroma_db/                     # ChromaDB vector storage
```

## Usage Guide

### Creating a Project

1. **Start at the Dashboard**
   - Open the application in your browser
   - You'll see the main dashboard with project management options

2. **Create New Project**
   - Click "Create New Project" button
   - Enter project name (required)
   - Add description (optional)
   - Click "Create Project"

3. **Project is Created**
   - Project gets a unique UUID automatically
   - You'll be redirected back to dashboard
   - Project appears in your projects list

### Managing Documents

1. **Access Project Details**
   - Click "View" on any project card
   - You'll see the project details page

2. **Upload PDF Document**
   - Click in the upload area or drag & drop a PDF file
   - Click "Upload & Process Document"
   - System will automatically:
     - Extract text from PDF
     - Parse sentences and tables
     - Generate embeddings
     - Store in ChromaDB

3. **View Document Information**
   - See processing results (sentence count, table count)
   - View document metadata
   - Access embeddings viewer

### Viewing Embeddings

1. **Open Embeddings Viewer**
   - Click "View Embeddings" on any document
   - Modal opens showing all embeddings

2. **Explore Embeddings**
   - **Sentences**: Each sentence as a separate embedding
   - **Tables**: Each table as a single embedding
   - View embedding metadata and vector information

### Searching Projects

1. **Use Search Function**
   - Enter project name or UUID in search box
   - Click "Search" or press Enter
   - View filtered results

2. **Clear Search**
   - Click "Clear Search" to return to full project list

## Technical Details

### Embeddings Architecture

- **Model**: `all-MiniLM-L6-v2` (384-dimensional vectors)
- **Storage**: ChromaDB collections named `project_{project_id}_doc_{document_id}`
- **Content Types**:
  - **Sentences**: Individual text sentences
  - **Tables**: Complete table structures as text

### PDF Processing

- **Text Extraction**: PyPDF2 for reliable PDF text extraction
- **Sentence Parsing**: Regex-based sentence splitting
- **Table Detection**: Pattern recognition for table identification
- **Table Processing**: Structured data extraction and text conversion

### Data Storage

- **Projects**: JSON file storage (`data/projects.json`)
- **Documents**: JSON file storage (`data/documents.json`)
- **Embeddings**: ChromaDB vector database
- **Files**: Temporary uploads in `uploads/` directory

## API Endpoints

- `GET /` - Dashboard
- `POST /create_project` - Create new project
- `POST /search_project` - Search projects
- `GET /project/<id>` - Project details
- `POST /upload_document` - Upload PDF document
- `GET /get_embeddings/<project_id>/<document_id>` - Get document embeddings

## Customization

### Styling
- Modify `templates/base.html` for global styling changes
- Update CSS variables for color schemes
- Add custom animations in the `<style>` sections

### AI Model
- Change embedding model in `backend/embeddings.py`
- Update `SentenceTransformer('model-name')` with your preferred model

### PDF Processing
- Enhance table detection in `backend/pdf_processor.py`
- Add support for other file formats
- Implement custom text preprocessing

## Troubleshooting

### Common Issues

1. **PDF Upload Fails**
   - Ensure file is a valid PDF
   - Check file size limits
   - Verify PDF is not password-protected

2. **Embeddings Not Generated**
   - Check ChromaDB installation
   - Verify sentence-transformers model download
   - Check console for error messages

3. **Search Not Working**
   - Ensure projects exist in database
   - Check search query format
   - Verify JSON data integrity

### Debug Mode

Run with debug mode for detailed error information:
```bash
export FLASK_DEBUG=1
python app.py
```

## Future Enhancements

- [ ] Document search within projects
- [ ] Semantic search across all documents
- [ ] Document versioning
- [ ] User authentication
- [ ] Team collaboration features
- [ ] Advanced analytics dashboard
- [ ] Export functionality
- [ ] API documentation

## License

This project is open source and available under the MIT License.

## Support

For issues and questions:
1. Check the troubleshooting section
2. Review console logs for errors
3. Ensure all dependencies are properly installed
4. Verify file permissions for data directories

---

**Built with ❤️ using Flask, ChromaDB, and modern web technologies**






