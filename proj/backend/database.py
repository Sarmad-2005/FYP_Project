import json
import os
from typing import List, Dict, Optional

class DatabaseManager:
    def __init__(self):
        self.data_dir = 'data'
        self.projects_file = os.path.join(self.data_dir, 'projects.json')
        self.documents_file = os.path.join(self.data_dir, 'documents.json')
        self._ensure_data_directory()
        self._initialize_files()

    def _ensure_data_directory(self):
        """Create data directory if it doesn't exist"""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def _initialize_files(self):
        """Initialize JSON files if they don't exist"""
        if not os.path.exists(self.projects_file):
            with open(self.projects_file, 'w') as f:
                json.dump([], f)
        
        if not os.path.exists(self.documents_file):
            with open(self.documents_file, 'w') as f:
                json.dump([], f)

    def _read_json(self, filepath: str) -> List[Dict]:
        """Read JSON data from file"""
        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []

    def _write_json(self, filepath: str, data: List[Dict]):
        """Write JSON data to file"""
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)

    def create_project(self, project_data: Dict) -> bool:
        """Create a new project"""
        try:
            projects = self._read_json(self.projects_file)
            projects.append(project_data)
            self._write_json(self.projects_file, projects)
            return True
        except Exception as e:
            print(f"Error creating project: {e}")
            return False

    def get_project(self, project_id: str) -> Optional[Dict]:
        """Get a specific project by ID"""
        projects = self._read_json(self.projects_file)
        for project in projects:
            if project['id'] == project_id:
                return project
        return None

    def get_all_projects(self) -> List[Dict]:
        """Get all projects"""
        return self._read_json(self.projects_file)

    def search_projects(self, query: str) -> List[Dict]:
        """Search projects by name or ID"""
        projects = self._read_json(self.projects_file)
        query_lower = query.lower()
        
        results = []
        for project in projects:
            if (query_lower in project['name'].lower() or 
                query_lower in project['id'].lower()):
                results.append(project)
        
        return results

    def create_document(self, document_data: Dict) -> bool:
        """Create a new document record"""
        try:
            documents = self._read_json(self.documents_file)
            documents.append(document_data)
            self._write_json(self.documents_file, documents)
            return True
        except Exception as e:
            print(f"Error creating document: {e}")
            return False

    def get_project_documents(self, project_id: str) -> List[Dict]:
        """Get all documents for a specific project"""
        documents = self._read_json(self.documents_file)
        return [doc for doc in documents if doc['project_id'] == project_id]

    def get_document(self, document_id: str) -> Optional[Dict]:
        """Get a specific document by ID"""
        documents = self._read_json(self.documents_file)
        for document in documents:
            if document['id'] == document_id:
                return document
        return None






