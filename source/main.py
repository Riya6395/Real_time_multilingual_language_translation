
import os
import time
import pygame
import fitz  # PyMuPDF for PDF handling
from gtts import gTTS
import streamlit as st
import speech_recognition as sr
from googletrans import LANGUAGES, Translator
from io import BytesIO
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
import argostranslate.package
import argostranslate.translate
import concurrent.futures

# Global flag to manage translation state
isTranslateOn = False

# Initialize translator and mixer
translator = Translator()
pygame.mixer.init()

# Map language names to codes
language_mapping = {name: code for code, name in LANGUAGES.items()}

def get_language_code(language_name):
    """Retrieve the language code for a given language name."""
    return language_mapping.get(language_name, language_name)

def offline_translate(text, from_lang, to_lang):
    """Translate text using Argos Translate (Offline Mode)."""
    try:
        return argostranslate.translate.translate(text, from_lang, to_lang)
    except Exception as e:
        st.error(f"Offline Translation Failed: {e}")
        return None

def translator_function(spoken_text, from_language, to_language, max_retries=3):
    """Translate text from one language to another with retry logic and better timeout handling."""
    try:
        if not spoken_text.strip():
            st.warning("No text provided for translation.")
            return None  

        if not from_language or not to_language:
            st.error("Invalid source or target language.")
            return None  

        max_length = 500  # ✅ Limit text size per request
        chunks = [spoken_text[i:i + max_length] for i in range(0, len(spoken_text), max_length)]

        translated_chunks = []
        translator = Translator(service_urls=[
            'translate.google.com',
            'translate.google.co.in',
            'translate.google.co.uk'
        ])

        for chunk in chunks:
            for attempt in range(max_retries):  # ✅ Retry failed requests
                try:
                    translated_part = translator.translate(chunk, src=from_language, dest=to_language)
                    translated_chunks.append(translated_part.text if translated_part else "")
                    time.sleep(1)  # ✅ Small delay to prevent rate limiting
                    break  # ✅ Exit retry loop if successful
                except Exception as e:
                    if attempt < max_retries - 1:
                        time.sleep(2)  # ✅ Wait before retrying
                    else:
                        st.error(f"Chunk Translation Failed after {max_retries} retries: {e}")
                        translated_chunks.append("")  

        return "\n".join(translated_chunks)  
    except Exception as e:
        st.error(f"Translation Error: {e}")
        return None
    
    
def detect_language(spoken_text):
    """Detect the language of the spoken text."""
    try:
        detected = translator.detect(spoken_text)
        return detected.lang
    except Exception as e:
        st.error(f"Language Detection Error: {e}")
        return None

def text_to_voice(text_data, to_language, voice_speed):
    """Convert translated text to voice output."""
    try:
        myobj = gTTS(text=text_data, lang=to_language, slow=(voice_speed < 1.0))
        myobj.save("cache_file.mp3")
        pygame.mixer.Sound("cache_file.mp3").play()
        time.sleep(2)  # Wait for audio playback
        os.remove("cache_file.mp3")
    except Exception as e:
        st.error(f"Audio Playback Error: {e}")

def extract_text_from_pdf(uploaded_pdf):
    """Extracts text from an uploaded PDF file."""
    try:
        text = ""
        with fitz.open(stream=uploaded_pdf.read(), filetype="pdf") as doc:
            for page in doc:
                text += page.get_text("text") + "\n"

        return text.strip() if text.strip() else None
    except Exception as e:
        st.error(f"Error extracting text from PDF: {e}")
        return None

def create_pdf(text):
    """Creates a multi-page PDF from the given text and returns a BytesIO object."""
    try:
        pdf_buffer = BytesIO()
        pdf = canvas.Canvas(pdf_buffer, pagesize=letter)
        width, height = letter  # Get page size

        pdf.setFont("Helvetica", 12)  # Set font
        y_position = height - 50  # Start position (top of page)

        lines = text.split("\n")  # Split text into lines
        for line in lines:
            if y_position < 50:  # If near bottom, start a new page
                pdf.showPage()  # End current page
                pdf.setFont("Helvetica", 12)  # Reset font for new page
                y_position = height - 50  # Reset y position

            pdf.drawString(100, y_position, line)
            y_position -= 20  # Move text down

        pdf.save()
        pdf_buffer.seek(0)
        return pdf_buffer
    except Exception as e:
        st.error(f"Error creating PDF: {e}")
        return None

def main_process(output_placeholder, from_language, to_language, voice_speed):
    """Main processing loop for listening, translating, and speaking."""
    global isTranslateOn
    rec = sr.Recognizer()

    while isTranslateOn:
        with sr.Microphone() as source:
            output_placeholder.text("Listening...")
            rec.pause_threshold = 1
            try:
                audio = rec.listen(source, phrase_time_limit=10)
                output_placeholder.text("Processing...")
                spoken_text = rec.recognize_google(audio, language=from_language)
                output_placeholder.text(f"You said: {spoken_text}")

                detected_language = detect_language(spoken_text) if from_language == 'auto' else from_language
                output_placeholder.text(f"Detected Language: {LANGUAGES.get(detected_language, 'Unknown')}")

                output_placeholder.text("Translating...")
                translated_text = translator_function(spoken_text, detected_language, to_language)

                if translated_text:
                    st.session_state['translation_history'].append({
                        "spoken": spoken_text,
                        "translated": translated_text
                    })

                    output_placeholder.text(f"Translated: {translated_text}")
                    text_to_voice(translated_text, to_language, voice_speed)
            except sr.UnknownValueError:
                output_placeholder.text("Could not understand the audio. Please try again.")
            except Exception as e:
                output_placeholder.text(f"Error: {e}")

# Streamlit UI Layout
st.title("Multilingual Translation System")

# Dropdowns for language selection (Common for Voice & PDF Translation)
from_language_name = st.selectbox("Select Source Language (or Auto-Detect):", ["Auto-Detect"] + list(LANGUAGES.values()))
to_language_name = st.selectbox("Select Target Language:", list(LANGUAGES.values()))

# Get language codes
from_language = "auto" if from_language_name == "Auto-Detect" else get_language_code(from_language_name)
to_language = get_language_code(to_language_name)

# Voice customization options
voice_speed = st.slider("Select Voice Speed:", min_value=0.5, max_value=1.5, value=1.0)

# Initialize session state for translation history
if 'translation_history' not in st.session_state:
    st.session_state['translation_history'] = []

# Buttons to control the translator
start_button = st.button("Start")
stop_button = st.button("Stop")

# Start translation process
if start_button:
    if not isTranslateOn:
        isTranslateOn = True
        output_placeholder = st.empty()
        main_process(output_placeholder, from_language, to_language, voice_speed)

# Stop translation process
if stop_button:
    isTranslateOn = False
    st.write("Translation ended! Thank you.")

# Display translation history
st.subheader("Translation History")
for item in st.session_state['translation_history']:
    st.write(f"**You said:** {item['spoken']}")
    st.write(f"**Translated:** {item['translated']}")

# Download translation history as text file
if st.session_state['translation_history']:
    history_text = "\n\n".join([f"You said: {item['spoken']}\nTranslated: {item['translated']}" 
                                for item in st.session_state['translation_history']])
    st.download_button(
        label="Download Translation History",
        data=history_text,
        file_name="translation_history.txt",
        mime="text/plain"
    )

# ✅ **Fixed PDF Translation Section**
st.subheader("Upload and Translate a PDF")

uploaded_pdf = st.file_uploader("Upload a PDF file:", type=["pdf"])

if uploaded_pdf is not None:
    with st.spinner("Extracting text from PDF..."):
        extracted_text = extract_text_from_pdf(uploaded_pdf)

    if extracted_text:
        st.subheader("Extracted Text:")
        st.text_area("Text from PDF:", extracted_text, height=300, disabled=True)

        
        with st.spinner("Translating..."):
            translated_text = translator_function(extracted_text, from_language, to_language)

        if translated_text:
            st.subheader("Translated Text:")
            st.text_area("Translated PDF Content:", translated_text, height=300)

            pdf_file = create_pdf(translated_text)
            if pdf_file:
                st.download_button(
                    label="Download Translated PDF",
                    data=pdf_file,
                    file_name="translated_document.pdf",
                    mime="application/pdf"
                )
            else:
                st.error("Error creating the translated PDF.")
                  
        else:
            st.warning("Translation failed or no text found to translate.")
            
    else:
        st.warning("No valid text extracted from the PDF. Please upload a different file.")
        
