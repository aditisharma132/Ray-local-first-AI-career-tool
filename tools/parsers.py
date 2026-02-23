import PyPDF2
import re

def extract_text_from_pdf(uploaded_file) -> str:
    """
    Extracts text from a loaded PDF bytes object.
    """
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + " "
        
        text = re.sub(r'\s+', ' ', text).strip()
        return text
    except Exception as e:
        raise Exception(f"Failed to read PDF: {str(e)}")
