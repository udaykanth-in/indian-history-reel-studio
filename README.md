# Indian History Reel Studio v1

A Streamlit app for the Master Indian History Reel workflow.

## Workflow
Research + fact-check → Telugu narration → visual bible → timed image storyboard → AI images → optional Telugu TTS → subtitles → editing timeline → ZIP export.

## Run locally

Python 3.11+ recommended.

```bash
python -m venv .venv
# Windows
.venv\\Scripts\\activate
# macOS/Linux
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

Create `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "your_key_here"
```

Do not commit the secrets file.

## Notes

The app uses the OpenAI Responses API for research/story generation and the Images API for still-image generation. Image continuity is reinforced through a project visual bible and continuity text in every prompt; perfect pixel-level character identity cannot be guaranteed by a generic image model.

The generated project folder contains research JSON, story JSON, visual bible JSON, scenes JSON, numbered images, Telugu voiceover text, optional MP3 narration, subtitles and an editing timeline CSV.
