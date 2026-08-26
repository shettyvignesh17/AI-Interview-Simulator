import io
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

from werkzeug.utils import secure_filename

from interview_simulator.utils.common import unique_list

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover - optional dependency
    try:
        from PyPDF2 import PdfReader
    except ImportError:  # pragma: no cover - optional dependency
        PdfReader = None


SKILL_GLOSSARY = [
    "Python", "Java", "C++", "C#", "JavaScript", "TypeScript", "HTML", "CSS",
    "Flask", "Django", "FastAPI", "React", "Angular", "Vue", "Node.js", "Express",
    "SQL", "PostgreSQL", "MySQL", "SQLite", "MongoDB", "Redis", "Oracle",
    "Machine Learning", "Deep Learning", "Random Forest", "Decision Tree", "XGBoost",
    "TensorFlow", "Keras", "PyTorch", "Scikit-learn", "Pandas", "NumPy",
    "Natural Language Processing", "NLP", "Computer Vision", "OpenCV", "LLMs",
    "Generative AI", "RAG", "Prompt Engineering", "Statistics", "Data Science",
    "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Git", "GitHub", "CI/CD",
    "REST", "REST API", "GraphQL", "Microservices", "System Design", "Testing",
    "Linux", "Power BI", "Tableau", "MATLAB", "CAD", "SolidWorks", "ANSYS",
    "Six Sigma", "Lean Manufacturing", "Spark", "Hadoop", "Kafka", "Airflow",
]

TOOL_SKILLS = {
    "Docker", "Kubernetes", "AWS", "Azure", "GCP", "Git", "GitHub", "CI/CD",
    "Linux", "Power BI", "Tableau", "MATLAB", "CAD", "SolidWorks", "ANSYS",
    "Spark", "Hadoop", "Kafka", "Airflow", "PostgreSQL", "MySQL", "SQLite",
    "MongoDB", "Redis", "Oracle",
}

SECTION_ALIASES = {
    "skills": "technical_skills",
    "technical skills": "technical_skills",
    "skills & technologies": "technical_skills",
    "technical expertise": "technical_skills",
    "technologies": "technical_skills",
    "projects": "projects",
    "academic projects": "projects",
    "personal projects": "projects",
    "experience": "professional_experience",
    "work experience": "professional_experience",
    "professional experience": "professional_experience",
    "employment": "professional_experience",
    "internships": "professional_experience",
    "education": "education",
    "academic background": "education",
    "certifications": "certifications",
    "certificates": "certifications",
    "research": "research",
    "publications": "research",
    "achievements": "achievements",
    "awards": "achievements",
    "summary": "summary",
    "professional summary": "summary",
    "profile": "summary",
}

CONTACT_PATTERN = re.compile(
    r"(?:[\w.+-]+@[\w.-]+\.[a-z]{2,}|https?://|linkedin\.com|github\.com|"
    r"\b(?:phone|mobile|address|date of birth|dob|gender|nationality|religion)\b)",
    re.IGNORECASE,
)
PHONE_PATTERN = re.compile(r"(?:\+?\d[\d ()-]{8,}\d)")
DURATION_PATTERN = re.compile(
    r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}"
    r"(?:\s*[-–—]\s*(?:present|current|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s+\d{4}))?"
    r"|\b\d{4}\s*[-–—]\s*(?:present|current|\d{4})\b",
    re.IGNORECASE,
)


def parse_resume(file_storage, allowed_extensions=None):
    filename = secure_filename(file_storage.filename or "resume")
    extension = Path(filename).suffix.lower()
    content = file_storage.read()
    allowed = set(allowed_extensions or {".pdf", ".docx", ".txt"})

    if extension not in allowed:
        raise ValueError("Unsupported resume format. Upload a PDF or DOCX resume.")
    if not content:
        raise ValueError("Uploaded resume is empty.")

    try:
        if extension == ".pdf":
            if PdfReader is None:
                raise RuntimeError(
                    "PDF support requires the optional 'pypdf' package. "
                    "Install dependencies from requirements.txt and try again."
                )
            text = _extract_pdf_text(content)
        elif extension == ".docx":
            text = _extract_docx_text(content)
        else:
            try:
                text = content.decode("utf-8")
            except UnicodeDecodeError:
                text = content.decode("latin-1", errors="ignore")
    except (ValueError, RuntimeError):
        raise
    except Exception as exc:
        raise ValueError(
            "We couldn't read this resume. Please upload a valid PDF or DOCX resume."
        ) from exc

    cleaned = _normalize_text(text)
    if len(cleaned) < 80 or len(re.findall(r"[A-Za-z]{2,}", cleaned)) < 18:
        raise ValueError(
            "We couldn't read meaningful resume text. Please upload a valid text-based PDF or DOCX resume."
        )
    profile = extract_resume_profile(cleaned)

    return {
        "filename": filename,
        "content_type": file_storage.mimetype or "application/octet-stream",
        "file_size": len(content),
        "text": cleaned,
        "profile": profile,
        "analysis": profile["analysis"],
    }


def _extract_pdf_text(content):
    reader = PdfReader(io.BytesIO(content))
    if getattr(reader, "is_encrypted", False):
        try:
            reader.decrypt("")
        except Exception as exc:
            raise ValueError("Encrypted PDF resumes are not supported.") from exc
    chunks = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(chunks)


def _extract_docx_text(content):
    try:
        with zipfile.ZipFile(io.BytesIO(content)) as archive:
            document_xml = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile) as exc:
        raise ValueError(
            "We couldn't read this resume. Please upload a valid PDF or DOCX resume."
        ) from exc

    root = ElementTree.fromstring(document_xml)
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs = []
    for paragraph in root.iter(f"{namespace}p"):
        text = "".join(node.text or "" for node in paragraph.iter(f"{namespace}t"))
        if text.strip():
            paragraphs.append(text.strip())
    return "\n".join(paragraphs)


def _normalize_text(text):
    text = text.replace("\x00", " ")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _skill_pattern(skill):
    escaped = re.escape(skill.lower())
    return rf"(?<![a-z0-9]){escaped}(?![a-z0-9])"


def detect_skills(text):
    lower_text = text.lower()
    return unique_list(
        [skill for skill in SKILL_GLOSSARY if re.search(_skill_pattern(skill), lower_text)]
    )


def extract_resume_profile(text):
    skills = detect_skills(text)
    sections = _split_sections(text)
    project_lines = _professional_lines(sections.get("projects", []))
    experience_lines = _professional_lines(sections.get("professional_experience", []))
    if not project_lines:
        project_lines = _extract_project_like_lines(text)

    projects = [_project_entry(line, index) for index, line in enumerate(project_lines[:8])]
    experience = [_experience_entry(line, index) for index, line in enumerate(experience_lines[:8])]
    education = _professional_lines(sections.get("education", []))[:8]
    certifications = _professional_lines(sections.get("certifications", []))[:12]
    research = _professional_lines(sections.get("research", []))[:8]
    achievements = _professional_lines(sections.get("achievements", []))[:8]
    tools = [skill for skill in skills if skill in TOOL_SKILLS]

    mention_counts = {
        skill: len(re.findall(_skill_pattern(skill), text.lower())) for skill in skills
    }
    analysis = {
        "technicalSkills": skills,
        "professionalExperience": experience,
        "projects": projects,
        "education": education,
        "certifications": certifications,
        "tools": tools,
        "research": research,
        "achievements": achievements,
        "skillMentions": mention_counts,
    }

    summary_parts = []
    if skills:
        summary_parts.append("Skills: " + ", ".join(skills[:8]))
    if projects:
        summary_parts.append("Projects: " + "; ".join(item["name"] for item in projects[:2]))
    if experience:
        summary_parts.append("Experience: " + "; ".join(item["role"] for item in experience[:2]))

    return {
        "skills": skills[:30],
        "projects": [item["description"] for item in projects],
        "experience": [item["description"] for item in experience],
        "summary": " | ".join(summary_parts) or "Resume analyzed without supported technical claims.",
        "analysis": analysis,
    }


def _normalize_header(line):
    value = re.sub(r"[^a-z& /]", "", line.lower()).strip(" :|-_")
    return SECTION_ALIASES.get(value)


def _split_sections(text):
    sections = {"general": []}
    current_header = "general"
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        normalized = _normalize_header(line)
        if normalized:
            current_header = normalized
            sections.setdefault(current_header, [])
            continue
        sections.setdefault(current_header, []).append(line)
    return sections


def _professional_lines(lines):
    output = []
    for raw_line in lines:
        line = raw_line.strip(" -*•\t")
        if len(line) < 4 or CONTACT_PATTERN.search(line) or PHONE_PATTERN.search(line):
            continue
        output.append(line)
    return unique_list(output)


def _entry_title(line, fallback):
    first = re.split(r"\s*[|:]\s*|\s+[–—]\s+", line, maxsplit=1)[0].strip()
    if not first or len(first) > 80:
        first = line[:77].rstrip() + ("..." if len(line) > 77 else "")
    return first or fallback


def _project_entry(line, index):
    return {
        "name": _entry_title(line, f"Project {index + 1}"),
        "description": line,
        "technologies": detect_skills(line),
        "objective": line,
        "contribution": line,
    }


def _experience_entry(line, index):
    duration_match = DURATION_PATTERN.search(line)
    role = _entry_title(line, f"Experience {index + 1}")
    organization = ""
    at_match = re.search(r"\bat\s+([^|,–—]+)", line, re.IGNORECASE)
    if at_match:
        organization = at_match.group(1).strip()
    return {
        "role": role,
        "organization": organization,
        "duration": duration_match.group(0) if duration_match else "",
        "description": line,
        "technologies": detect_skills(line),
        "responsibilities": [line],
        "achievements": [],
    }


def _extract_project_like_lines(text):
    lines = []
    for raw_line in text.splitlines():
        stripped = raw_line.strip(" -*•\t")
        lowered = stripped.lower()
        if len(stripped) < 8 or CONTACT_PATTERN.search(stripped):
            continue
        if "project" in lowered or "built" in lowered or "developed" in lowered:
            lines.append(stripped)
    return unique_list(lines)[:8]
