# app/resume_parser.py
# ...existing code...
import PyPDF2
import docx
import re

class ResumeParser:
    def parse(self, file):
        """Parse resume file and extract relevant information"""
        content = self._read_file(file)
        return {
            'skills': self._extract_skills(content),
            'experience': self._extract_experience(content),
            'education': self._extract_education(content)
        }
    
    def _read_file(self, file):
        """Read different file formats"""
        if file.filename.endswith('.pdf'):
            return self._read_pdf(file)
        elif file.filename.endswith(('.doc', '.docx')):
            return self._read_docx(file)
        else:
            raise ValueError("Unsupported file format")
    
    def _read_pdf(self, file):
        pdf_reader = PyPDF2.PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    
    def _read_docx(self, file):
        doc = docx.Document(file)
        return " ".join([paragraph.text for paragraph in doc.paragraphs])
    
    def _extract_skills(self, content):
        # Add your skill extraction logic here
        # This is a simple example
        common_skills = ['python', 'java', 'javascript', 'react', 'node.js', 'sql']
        found_skills = []
        for skill in common_skills:
            if re.search(r'\b' + skill + r'\b', content.lower()):
                found_skills.append(skill)
        return found_skills
    
    def _extract_experience(self, content):
        # Add your experience extraction logic here
        # This is a simplified version
        experience = []
        # Look for common job title patterns
        job_patterns = r'(Software Engineer|Developer|Project Manager|Team Lead)'
        matches = re.finditer(job_patterns, content)
        for match in matches:
            experience.append(match.group(0))
        return experience
    
    def _extract_education(self, content):
        # Add education extraction logic
        # Simplified version
        education = []
        edu_patterns = r'(Bachelor|Master|PhD|BSc|MSc)'
        matches = re.finditer(edu_patterns, content)
        for match in matches:
            education.append(match.group(0))
        return education
