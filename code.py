from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import re
import os
from typing import List, Dict
from pydantic import BaseModel
from pymongo import MongoClient

app = FastAPI()

# Directory to store uploaded files
UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Serve uploaded files as static files
app.mount("/static", StaticFiles(directory=UPLOAD_DIR), name="static")

# Store uploaded media files
uploaded_media = {}

def parse_whatsapp_txt(file_content: str) -> Dict[str, List]:
    messages = []
    media_messages = []
    pattern = re.compile(r"(\d{2}/\d{2}/\d{4}, \d{2}:\d{2} - )?(.*?): (.*)")
    
    for line in file_content.splitlines():
        match = pattern.match(line)
        if match:
            timestamp, sender, message = match.groups()
            if message and "<Media omitted>" in message:
                media_messages.append({"sender": sender, "message": "Media File", "timestamp": timestamp})
            else:
                messages.append({"sender": sender, "message": message, "timestamp": timestamp})
    
    return {"messages": messages, "media_messages": media_messages}

@app.post("/upload/")
async def upload_files(files: List[UploadFile] = File(...)):
    parsed_data = {"messages": [], "media_messages": [], "uploaded_files": []}

    for file in files:
        content = await file.read()
        
        if file.filename.endswith(".txt") or file.filename.endswith(".json"):
            file_text = content.decode("utf-8")
            data = parse_whatsapp_txt(file_text)
            parsed_data["messages"].extend(data["messages"])
            parsed_data["media_messages"].extend(data["media_messages"])
        else:
            file_path = os.path.join(UPLOAD_DIR, file.filename)
            with open(file_path, "wb") as f:
                f.write(content)
            uploaded_media[file.filename] = file_path
            parsed_data["uploaded_files"].append(file.filename)
    
    return JSONResponse(content=parsed_data)

# MongoDB Connection
client = MongoClient("mongodb://localhost:27017/")
db = client["whatsapp_analyzer"]
feedback_collection = db["feedback"]

# Feedback Model
class FeedbackModel(BaseModel):
    feedback: str

@app.post("/feedback/")
async def submit_feedback(feedback: FeedbackModel):
    feedback_data = {"feedback": feedback.feedback}
    feedback_collection.insert_one(feedback_data)
    return {"message": "Feedback submitted successfully!"}

@app.head("/", response_class=HTMLResponse)
def home_page():
    return """
   <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>WhatsApp Chat Analyzer</title>
    <style>
        :root {
            --bg-color: #ffffff;
            --text-color: #000000;
            --container-bg: rgba(0, 0, 0, 0.1);
            --border-color: #ccc;
             --button-bg: #007BFF;
            --button-text: #ffffff;
        }

        body.dark-mode {
            --bg-color: #000000;
            --text-color: #ffffff;
            --container-bg: rgba(0, 0, 0, 0.1);
            --border-color: #444;
            --button-bg: #007BFF;;
            --button-text: #ffffff;
        }

        body {
            margin: 0;
            font-family: Arial, sans-serif;
            color: var(--text-color);
            background: var(--bg-color);
            overflow-y: auto;
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            flex-direction: column;
            padding-bottom: 20px;
            text-align: center; /* Center-align text */
        }

        .content {
            width: 80vw;
            max-height: 70vh;
            overflow-y: auto;
            background: var(--container-bg);
            padding: 20px;
            border-radius: 10px;
            backdrop-filter: blur(10px);
            border: 1px solid var(--border-color);
            margin-bottom: 20px;
            text-align: center; /* Ensure content is centered */
        }

        .scroll-container {
            max-height: 60vh;
            overflow-y: auto;
            padding: 10px;
            border: 1px solid var(--border-color);
            background: var(--container-bg);
            border-radius: 5px;
            margin-bottom: 10px;
        }

        input, button {
            margin: 5px 0;
            padding: 10px;
            font-size: 1rem;
            border-radius: 5px;
            border: none;
            outline: none;
        }

        input {
            width: 60%;
        }

        button {
            cursor: pointer;
            background: var(--button-bg);
            color: var(--button-text);
        }

        .media-preview img {
            max-width: 100%;
            max-height: 200px;
            border-radius: 5px;
            margin-top: 5px;
        }

        .media-preview iframe {
            width: 100%;
            height: 200px;
            border-radius: 5px;
            margin-top: 5px;
        }

        .upload-box button {
            background-color: #4CAF50;
            color: white;
            padding: 10px 20px;
            border: none;
            cursor: pointer;
            font-size: 16px;
            border-radius: 5px;
        }

        .upload-box button:hover {
            background-color: #45a049;
        }

        /* Contact Us Section */
        .contact-us {
            margin-top: 20px;
            background-color: #f0f0f0;
            padding: 20px;
            border-radius: 10px;
            width: 80%;
            text-align: center;
        }

        .contact-us h3 {
            margin-bottom: 15px;
        }

        .contact-us p {
            margin: 5px 0;
        }

        .feedback {
            margin-top: 20px;
            background-color: #f0f0f0;
            padding: 20px;
            border-radius: 10px;
            width: 80%;
            text-align: center;
        }

        .feedback textarea {
            width: 100%;
            height: 100px;
            padding: 10px;
            border-radius: 5px;
            border: 1px solid #ccc;
        }
    </style>
</head>
<body>
    <div class="content">
        <!-- Button with sun and moon icons -->
        <button onclick="toggleTheme()" id="themeToggleBtn">
            🌙 <!-- Moon icon for Dark Mode -->
        </button>
        <h2>WhatsApp Chat Analyzer</h2>
        <p>Upload the chat file (.txt) along with media files</p>
        <input type="file" id="fileInput" multiple accept=".txt, .json, .jpg, .png, .pdf, .docx, .ppt, .pptx, .webp" />
        <!-- Upload button inside a box -->
        <div class="upload-box">
            <button onclick="uploadFile()">Upload</button>
        </div>

        <br/><br/>
        <input type="text" id="userInput" placeholder="Enter user name" oninput="filterMessages()" />
        <br/><br/>
        <input type="text" id="mediaSearchInput" placeholder="Search media files" oninput="filterMedia()" />

        <div class="scroll-container" id="messageList"></div>
        <div class="scroll-container" id="mediaList"></div>
        <div class="scroll-container" id="mediaPreview"></div>

        <!-- Contact Us Section -->
        <div class="contact-us">
            <h3>Contact Us</h3>
            <p>Location: Kambadala Hosure, Bhadravathi, Shivamogga, Karnataka - 577115</p>
            <p>Email: contact@whatsappchatanalyzer.com</p>
            <p>Phone: +91 123 456 7890</p>
        </div>

        <!-- Feedback Section -->
        <div class="feedback">
            <h3>Feedback</h3>
            <textarea id="feedbackInput" placeholder="Write your feedback here..."></textarea>
            <button onclick="submitFeedback()">Submit Feedback</button>
            <p id="feedbackMessage"></p>
        </div>

    </div>


    <script>
        let chatData = {};

        function toggleTheme() {
            // Toggle dark-mode class on body
            document.body.classList.toggle("dark-mode");

            // Update button icon
            const themeToggleBtn = document.getElementById("themeToggleBtn");
            if (document.body.classList.contains("dark-mode")) {
                themeToggleBtn.innerHTML = "🌞";  // Sun icon for Light Mode
            } else {
                themeToggleBtn.innerHTML = "🌙";  // Moon icon for Dark Mode
            }
        }

        async function uploadFile() {
            let formData = new FormData();
            let fileInput = document.getElementById("fileInput");
            for (let i = 0; i < fileInput.files.length; i++) {
                formData.append("files", fileInput.files[i]);
            }
            
            let response = await fetch("/upload/", {
                method: "POST",
                body: formData
            });
            let result = await response.json();
            chatData = result;
            displayMedia(result.uploaded_files);
            if (result.messages.length > 0) {
                filterMessages();
            }
        }

        function filterMessages() {
            let selectedUser = document.getElementById("userInput").value;
            if (!selectedUser) {
                document.getElementById("messageList").innerHTML = "<p>Please enter a name to search.</p>";
                return;
            }
            let messages = chatData.messages.filter(m => m.sender.toLowerCase().includes(selectedUser.toLowerCase()));
            document.getElementById("messageList").innerHTML = messages.length > 0 ? 
                messages.map(m => `<p><strong>${m.timestamp}:</strong> ${m.sender}: ${m.message}</p>`).join("") :
                "<p>No messages found for this user.</p>";
        }

        function filterMedia() {
            let searchTerm = document.getElementById("mediaSearchInput").value.toLowerCase();
            let mediaList = document.getElementById("mediaList");
            let mediaPreview = document.getElementById("mediaPreview");
            let filteredFiles = chatData.uploaded_files.filter(f => f.toLowerCase().includes(searchTerm));
            
            mediaList.innerHTML = filteredFiles.length > 0 ? 
                "<h3>Uploaded Media</h3>" + filteredFiles.map(f => {
                    let fileUrl = "/static/" + f;
                    return `<p><a href="${fileUrl}" download>${f}</a></p>`;
                }).join("") : "<p>No media found matching your search.</p>";

            mediaPreview.innerHTML = filteredFiles.map(f => {
                let fileUrl = "/static/" + f;
                if (f.endsWith(".jpg") || f.endsWith(".png") || f.endsWith(".webp")) {
                    return `<img src="${fileUrl}" alt="Media Preview" />`;
                } else if (f.endsWith(".pdf")) {
                    return `<iframe src="${fileUrl}" frameborder="0"></iframe>`;
                } else {
                    return `<p>Preview not available for ${f}</p>`;
                }
            }).join("");
        }

        async function submitFeedback() {
                let feedbackText = document.getElementById("feedbackInput").value;
                if (!feedbackText.trim()) {
                    document.getElementById("feedbackMessage").innerText = "Please enter feedback.";
                    return;
                }

                let response = await fetch("/feedback/", {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json"
                    },
                    body: JSON.stringify({ feedback: feedbackText })
                });

                let result = await response.json();
                if (response.ok) {
                    document.getElementById("feedbackMessage").innerText = "Feedback submitted successfully!";
                    document.getElementById("feedbackInput").value = ""; // Clear input field
                } else {
                    document.getElementById("feedbackMessage").innerText = "Error submitting feedback.";
                }
            }


    </script>
</body>
</html>

"""


