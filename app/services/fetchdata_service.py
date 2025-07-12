import os
from .langchain_service import create_embeddings_and_store_text
from .document_service import split_text_for_txt

# Static content about Umar Azhar
UMAR_AZHAR_CONTENT = """
Umar Azhar is a passionate and skilled software engineer from Lahore, Pakistan, with a strong foundation in computer science and hands-on experience across software development, research, and cloud technologies. He graduated with a Bachelor's degree in Computer Science from the National University of Computer and Emerging Sciences (FAST) in 2024. His academic background is further distinguished by a research publication titled "Machine Learning-Based Fileless Malware Threats Analysis for the Detection of Cybersecurity Attacks Based on Memory Forensics," published in the Asian Bulletin of Big Data Management. This research explored advanced memory forensics techniques to detect fileless malware, showcasing Umar's analytical depth and interest in cybersecurity and machine learning.

Professionally, Umar has accumulated a diverse range of experiences. He is currently employed at Softpers as a Software Engineer, where he builds full-stack web applications using Python (FastAPI) and React.js, and contributes to SSR projects using Next.js for performance optimization. Prior to this, he worked remotely with SHARE Mobility (USA), where he played a key role in modernizing their admin portal using Angular (upgraded from version 6 to 18), developed a ride-hailing app, implemented backend rate limiting for DDoS mitigation, and created a RAG-based chatbot integrated with Confluence for intelligent document retrieval. He also served at i2c Inc. as an Associate Software Engineer, offering technical support for global clients and working with technologies like IBM Informix, Redhat, and SQL, while ensuring PCI and ISO-8583 compliance.

Beyond his full-time roles, Umar has a proven freelance track record. As a Level 2 seller on Fiverr, he completed over 80 client projects involving Python automation, data scraping, machine learning, and chatbot development using LangChain and RAG methods. His practical expertise extends to DevOps (CI/CD pipelines), backend development, and cloud technologies, supported by certifications from IBM, AWS, Stanford (via Coursera), and others. Umar's final year project, Botanic Sense, involved building a plant identification app trained on a 300k+ image dataset, coupled with community features to engage plant lovers.

He also interned at KFC Pakistan, where he built automated tools that significantly reduced manual data collection time and contributed to a computer vision project using number plate recognition to optimize drive-thru service. His tech stack includes Python, C++, JavaScript, SQL, and tools like TensorFlow, React.js, Node.js, Express.js, Tailwind, and Bootstrap. Umar complements his technical skills with strong soft skills—communication, problem-solving, collaboration, and adaptability. Outside of work, he enjoys horse riding and has competed in inter-university cricket tournaments, demonstrating a well-rounded and dynamic personality.
"""

def get_umar_azhar_content():
    """
    Returns the static content about Umar Azhar.
    
    Returns:
        str: The processed content about Umar Azhar.
    """
    return UMAR_AZHAR_CONTENT.strip()

async def save_processed_output_service():
    """
    Processes the static content about Umar Azhar, 
    splits it into chunks, and creates embeddings to store 
    them in Pinecone.
    """
    output_content = get_umar_azhar_content()
    # create chunks to creating embedding
    chunks = split_text_for_txt(output_content) 
    # Create embeddings and store them in Pinecone
    create_embeddings_and_store_text(chunks)