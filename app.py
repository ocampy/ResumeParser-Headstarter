from flask import Flask, render_template, request, redirect, url_for, send_from_directory
import os
import PyPDF2
import textract
import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.probability import FreqDist
from io import StringIO
from pdfminer.converter import TextConverter
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

nltk.download('stopwords')
nltk.download('punkt')


def extract_keywords(resume_text):
    # Removes punctuation and converts it to lowercase
    resume_text = resume_text.lower()

    # Tokenize the text into words
    words = word_tokenize(resume_text)

    # Filter out stopwords
    stop_words = set(stopwords.words('english'))
    words = [word for word in words if word.isalnum() and word not in stop_words]

    # Calculate word frequencies
    fdist = FreqDist(words)

    # Select the most common keywords
    num_keywords = 5
    keywords = [word for word, _ in fdist.most_common(num_keywords)]

    return keywords


def extract_resume_text(resume_path):
    _, file_extension = os.path.splitext(resume_path)
    if file_extension == '.pdf':
        # Extract text from PDF resume
        text = extract_pdf_text(resume_path)
    else:
        # Extract text from other types of resume (e.g., .doc, .docx)
        text = textract.process(resume_path).decode('utf-8')

    return text


def extract_pdf_text(pdf_path):
    text = ''
    resource_manager = PDFResourceManager()
    string_io = StringIO()
    laparams = LAParams()
    device = TextConverter(resource_manager, string_io, laparams=laparams)

    with open(pdf_path, 'rb') as file:
        interpreter = PDFPageInterpreter(resource_manager, device)
        for page in PDFPage.get_pages(file, check_extractable=True):
            interpreter.process_page(page)

        text = string_io.getvalue()

    device.close()
    string_io.close()

    return text


def store_keywords(resume_filename, keywords):
    # Store the keywords in a separate text file
    keywords_filename = os.path.splitext(resume_filename)[0] + '.txt'
    keywords_path = os.path.join(app.config['UPLOAD_FOLDER'], keywords_filename)
    with open(keywords_path, 'w') as file:
        file.write('\n'.join(keywords))


def retrieve_keywords(resume_filename):
    # Retrieve the stored keywords from the text file
    keywords_filename = os.path.splitext(resume_filename)[0] + '.txt'
    keywords_path = os.path.join(app.config['UPLOAD_FOLDER'], keywords_filename)
    with open(keywords_path, 'r') as file:
        keywords = file.read().splitlines()

    return keywords


@app.route('/', methods=['GET', 'POST'])
def resume_parser():
    if request.method == 'POST':
        resume_file = request.files['resume']
        keywords = request.form.get('keywords')

        # Save the uploaded resume to the uploads folder
        resume_filename = resume_file.filename
        resume_path = os.path.join(app.config['UPLOAD_FOLDER'], resume_filename)
        resume_file.save(resume_path)

        # Extract text from the resume file
        resume_text = extract_resume_text(resume_path)

        # Extract keywords from the resume text
        keyword_results = extract_keywords(resume_text)

        # Store the keywords in a separate text file
        store_keywords(resume_filename, keyword_results)

        return redirect(url_for('resumes'))

    return render_template('index.html')


@app.route('/resumes')
def resumes():
    resumes = []

    # Get the list of uploaded resumes
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if filename.endswith('.pdf'):
            # Retrieve the keywords for each resume
            keywords = retrieve_keywords(filename)

            resumes.append({
                'name': filename,
                'keywords': keywords
            })

    return render_template('resumes.html', resumes=resumes)


@app.route('/download/<filename>')
def download_resume(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


if __name__ == '__main__':
    app.run(debug=True)
