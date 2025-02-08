
import os
import time
import pygame
from gtts import gTTS
import streamlit as st
import speech_recognition as sr
from googletrans import LANGUAGES, Translator

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

def translator_function(spoken_text, from_language, to_language):
    """Translate text from one language to another."""
    try:
        return translator.translate(spoken_text, src=from_language, dest=to_language)
    except Exception as e:
        print(f"Translation Error: {e}")
        return None

def detect_language(spoken_text):
    """Detect the language of the spoken text."""
    try:
        detected = translator.detect(spoken_text)
        return detected.lang
    except Exception as e:
        print(f"Language Detection Error: {e}")
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
        print(f"Audio Playback Error: {e}")

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

                # Language detection (if source language is set to auto-detect)
                detected_language = detect_language(spoken_text) if from_language == 'auto' else from_language
                output_placeholder.text(f"Detected Language: {LANGUAGES.get(detected_language, 'Unknown')}")

                output_placeholder.text("Translating...")
                translated_text = translator_function(spoken_text, detected_language, to_language)

                if translated_text:
                    # Store spoken and translated text in session state
                    st.session_state['translation_history'].append({
                        "spoken": spoken_text,
                        "translated": translated_text.text
                    })

                    output_placeholder.text(f"Translated: {translated_text.text}")
                    text_to_voice(translated_text.text, to_language, voice_speed)
            except sr.UnknownValueError:
                output_placeholder.text("Could not understand the audio. Please try again.")
            except Exception as e:
                output_placeholder.text(f"Error: {e}")
                print(e)

# Streamlit UI Layout
st.title("Multilingual Translation System")

# Dropdowns for language selection
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

# Generate and download subtitles
if st.session_state['translation_history']:
    subtitle_content = ""
    for i, item in enumerate(st.session_state['translation_history']):
        subtitle_content += f"{i+1}\n00:00:{i*5},000 --> 00:00:{(i+1)*5},000\n{item['spoken']} ({item['translated']})\n\n"
    
    st.download_button(
        label="Download Subtitles",
        data=subtitle_content,
        file_name="translation_subtitles.srt",
        mime="text/plain"
    )
