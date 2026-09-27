<p align="center">
  <img src="https://github-readme-stats.vercel.app/api/pin/?username=ImranDev3&repo=Gild-AI-Terminal&theme=radical&show_owner=true" alt="GILD-AI Stats" />
</p>

<p align="center">
  <img src="https://img.shields.io/github/languages/top/ImranDev3/Gild-AI-Terminal?style=flat-square" />
  <img src="https://img.shields.io/github/repo-size/ImranDev3/Gild-AI-Terminal?style=flat-square" />
  <img src="https://img.shields.io/github/last-commit/ImranDev3/Gild-AI-Terminal?style=flat-square" />
</p>

---

# 🚀 GILD-AI: Automated Trading Terminal (v1.0)

**GILD-AI v1** is a cross-platform algorithmic trading engine optimized for **XAUUSD (Gold)**. It utilizes a multi-layer technology stack to deliver real-time data from MetaTrader 5 to a modern web interface and Telegram mobile.

---

## 🛠 Tech Stack & Languages
This project is built using a professional multi-language architecture:

![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=for-the-badge&logo=javascript&logoColor=black)
![HTML5](https://img.shields.io/badge/HTML5-E34F26?style=for-the-badge&logo=html5&logoColor=white)
![CSS3](https://img.shields.io/badge/CSS3-1572B6?style=for-the-badge&logo=css3&logoColor=white)
![JSON](https://img.shields.io/badge/JSON-000000?style=for-the-badge&logo=json&logoColor=white)
![MetaTrader5](https://img.shields.io/badge/MT5-Connector-2D3436?style=for-the-badge)

---

## 🛰 System Architecture (v1)
| Component | Technology | Logic Flow |
| :--- | :--- | :--- |
| **Backend Engine** | **Python** | Processes raw MT5 ticks and generates signals. |
| **API Layer** | **Flask / JSON** | Broadcasts live trading data via REST API. |
| **Frontend UI** | **JavaScript / HTML** | Fetches JSON data to render a live dashboard. |
| **Alert Gateway** | **Telegram API** | Routes critical signals to mobile devices. |

---

## 💎 v1 Features
* **Multi-Language Sync:** Seamless communication between Python backend and JavaScript frontend.
* **MT5 Data Bridge:** Stable tick fetching for Gold (XAUUSD).
* **Smart Alerting:** Intelligent signal filtering via custom algorithmic logic.
* **Zero-Latency Dashboard:** Dynamic UI updates using Vanilla JavaScript.

---

## 📂 Project Structure
* `main.py` — Python core engine & Flask API handler.
* `accuracy.py` — Algorithmic signal detection logic.
* `index.html` — JavaScript-powered live monitoring dashboard.
* `script.js` — Frontend logic for real-time updates.
* `data.json` — System configuration manifest.
* `style.css` — Modern UI styling for the terminal interface.

---

## ⚠️ Disclaimer
*This is a v1 release for testing and monitoring. Trading involves significant risk. Always validate strategies on a demo account before live deployment.*