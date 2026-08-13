import os, json, re, zipfile, base64
from pathlib import Path
from datetime import datetime
import streamlit as st
from openai import OpenAI

APP_DIR=Path(__file__).parent
OUT=APP_DIR/'output'; OUT.mkdir(exist_ok=True)
SYSTEM='''You are the Master Indian History Reel Agent. Communicate with the user in English. Viewer-facing narration, subtitles and on-screen text are natural modern Telugu. Historical characters never speak; only a third-person narrator speaks. Use still AI images, Telugu voiceover, music and SFX. Research and fact-check first. Only verified claims may be stated as facts. Keep disputed/partial/unverified claims clearly out of factual narration. Maintain strict continuity across images: recurring characters, faces, age, physique, costume, accessories, weapons, locations, architecture, landscape, weather, lighting, historical period and cinematic treatment. Every image must be numbered and synchronized to an exact narration time range.'''

def key(): return st.secrets.get('OPENAI_API_KEY',os.getenv('OPENAI_API_KEY',''))
def cli():
    k=key()
    if not k: st.error('OPENAI_API_KEY is missing. Add it to .streamlit/secrets.toml or your environment.'); st.stop()
    return OpenAI(api_key=k)
def ask(prompt, model, web=False):
    kw={'model':model,'input':[{'role':'system','content':SYSTEM},{'role':'user','content':prompt}]}
    if web: kw['tools']=[{'type':'web_search_preview'}]
    r=cli().responses.create(**kw)
    return r.output_text

def j(s):
    s=re.sub(r'^```json\s*|\s*```$','',s.strip(),flags=re.S)
    try:return json.loads(s)
    except: 
        m=re.search(r'\{.*\}',s,re.S)
        if not m: raise
        return json.loads(m.group(0))

def research(topic,audience,platform,duration,style,series,episode,prev,nxt,model):
    p=f'''Research this Indian history topic rigorously. TOPIC={topic}; AUDIENCE={audience}; PLATFORM={platform}; LENGTH={duration}s; STYLE={style}; SERIES={series or 'none'}; EPISODE={episode or 'none'}; PREVIOUS={prev or 'none'}; NEXT={nxt or 'none'}.
Use authoritative sources and cross-check important claims. Separate evidence from legends and disputed interpretations. Return JSON with topic, one_sentence_summary, historical_context, why_it_matters, timeline[{"date":"","event":"","significance":""}], key_people[{"name":"","role":"","significance":""}], key_locations[{"location":"","significance":""}], verified_facts[], partially_verified_claims[], disputed_claims[], common_myths[], trend_signals[], references[{"source":"","source_type":"","what_it_supports":""}], confidence_score.'''
    return j(ask(p,model,True))

def story(kb,duration,style,model):
    p=f'''Using ONLY this approved research package, create a {duration}-second short-form historical documentary in {style}. Narration MUST be natural modern Telugu. No character dialogue, no invented quotes, thoughts, motives or conversations. Fit the voiceover naturally to ~{duration} seconds. Return JSON with title (English), hook_telugu, setup_telugu, beat1_telugu, beat2_telugu, beat3_telugu, resolution_telugu, outro_telugu, voiceover_telugu, subtitle_telugu. Research: {json.dumps(kb,ensure_ascii=False)}'''
    return j(ask(p,model))

def bible(kb,story,model):
    p=f'''Create a project visual bible for a historical documentary. Research={json.dumps(kb,ensure_ascii=False)} Story={json.dumps(story,ensure_ascii=False)}. Return JSON with characters[{"name":"","age_range":"","physique":"","face":"","hair":"","facial_hair":"","skin_tone":"","costume":"","headwear":"","accessories":"","weapons":"","distinctive_features":""}], locations[{"name":"","period":"","geography":"","architecture":"","materials":"","fortifications":"","landscape":"","vegetation":"","weather":"","landmarks":""}], cinematic_bible:{"lighting":"","lens_language":"","atmosphere":"","realism":"","color_character":"","composition":""}, timeline_bible. Never claim an exact appearance unless supported; use historically plausible representation where uncertain.'''
    return j(ask(p,model))

def scenes(kb,story,vb,duration,model):
    p=f'''Create an editing-ready still-image storyboard for a {duration}-second reel. Use only approved facts. Use 7-12 images as needed. Exact timestamps must total exactly {duration} seconds. Image changes happen on meaningful visual changes, not arbitrary equal intervals. Voiceover is Telugu; image prompts and production notes are English. Each scene JSON must include image_number,start,end,duration,voiceover_segment,visual_purpose,visual_description,characters,costume,location,period,camera,lighting,environment,image_prompt,motion_suggestion,sfx,music,onscreen_text. Every later prompt must inherit the visual bible and explicitly preserve recurring character/location continuity. Research={json.dumps(kb,ensure_ascii=False)} Story={json.dumps(story,ensure_ascii=False)} VisualBible={json.dumps(vb,ensure_ascii=False)}'''
    return j(ask(p,model))['scenes']

def img(prompt,model,path):
    r=cli().images.generate(model=model,prompt=prompt,size='1024x1536',quality='high')
    path.write_bytes(base64.b64decode(r.data[0].b64_json))

def tts(text,path,voice,model='gpt-4o-mini-tts'):
    with cli().audio.speech.with_streaming_response.create(model=model,voice=voice,input=text,response_format='mp3') as r:r.stream_to_file(path)

def srt(text,dur):
    parts=[x.strip() for x in re.split(r'(?<=[.!?।])\s+',text) if x.strip()]
    if not parts:return ''
    w=[max(1,len(x)) for x in parts]; total=sum(w); cur=0
    def ts(v):
        h=int(v//3600);m=int(v%3600//60);s=int(v%60);ms=int((v-int(v))*1000);return f'{h:02}:{m:02}:{s:02},{ms:03}'
    out=[]
    for i,x in enumerate(parts,1):
        d=dur*w[i-1]/total; out.append(f'{i}\n{ts(cur)} --> {ts(cur+d)}\n{x}\n');cur+=d
    return '\n'.join(out)

def build_project(topic,kb,stt,vb,sc,makeimgs,makeaudio,imgmodel,voice):
    slug=re.sub(r'[^a-z0-9]+','-',topic.lower()).strip('-')+'-'+datetime.now().strftime('%Y%m%d%H%M%S')
    p=OUT/slug;(p/'images').mkdir(parents=True);(p/'audio').mkdir()
    (p/'research.json').write_text(json.dumps(kb,ensure_ascii=False,indent=2),encoding='utf-8')
    (p/'story.json').write_text(json.dumps(stt,ensure_ascii=False,indent=2),encoding='utf-8')
    (p/'visual_bible.json').write_text(json.dumps(vb,ensure_ascii=False,indent=2),encoding='utf-8')
    (p/'scenes.json').write_text(json.dumps(sc,ensure_ascii=False,indent=2),encoding='utf-8')
    (p/'voiceover_telugu.txt').write_text(stt['voiceover_telugu'],encoding='utf-8')
    dur=max(float(s['end']) for s in sc);(p/'subtitles.srt').write_text(srt(stt['voiceover_telugu'],dur),encoding='utf-8')
    rows=['image,start,end,duration,visual_purpose,voiceover_segment']
    for s in sc:rows.append(f'''IMAGE_{int(s['image_number']):02d},{s['start']},{s['end']},{s['duration']},"{s['visual_purpose'].replace('"','""')}","{s['voiceover_segment'].replace('"','""')}"''')
    (p/'editing_timeline.csv').write_text('\n'.join(rows),encoding='utf-8')
    results=[]
    if makeimgs:
        for s in sc:
            n=int(s['image_number']); path=p/'images'/f'IMAGE_{n:02d}.png'
            prompt=s['image_prompt']+'\n\nCONTINUITY LOCK: Follow the established visual bible. Preserve recurring character identity, costume, location, architecture, landscape, period, weather and lighting. No modern elements. CINEMATIC HISTORICAL DOCUMENTARY, PHOTOREALISTIC, HISTORICALLY GROUNDED, VERTICAL 9:16.'+json.dumps(vb,ensure_ascii=False)
            img(prompt,imgmodel,path);results.append({'image_number':n,'path':str(path),'prompt':prompt})
    if makeaudio: tts(stt['voiceover_telugu'],p/'audio'/'voiceover.mp3',voice)
    (p/'image_generation_log.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    z=OUT/f'{slug}.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as zz:
        for f in p.rglob('*'):
            if f.is_file():zz.write(f,f.relative_to(p.parent))
    return slug,z

st.set_page_config(page_title='Indian History Reel Studio',page_icon='🎬',layout='wide')
st.title('🎬 Indian History Reel Studio')
st.caption('Research → Fact-check → Telugu narration → Visual Bible → Timed images → Export')
with st.sidebar:
    st.header('Reel Setup')
    topic=st.text_input('Topic','Chhatrapati Shivaji Maharaj\'s early rise')
    audience=st.text_input('Audience','General audience')
    duration=st.number_input('Duration (seconds)',15,180,45,5)
    platform=st.selectbox('Platform',['YouTube Shorts','Instagram Reels','Facebook Reels'])
    style=st.selectbox('Content style',['Cinematic Historical Documentary','Suspense Documentary','Epic Historical Documentary','Emotional Historical Documentary'])
    series=st.text_input('Series name','');episode=st.text_input('Episode','')
    prev=st.text_area('Previous episode context','');nxt=st.text_area('Next episode context','')
    tm=st.text_input('Text model','gpt-4.1-mini'); im=st.text_input('Image model','gpt-image-1')
    makeimgs=st.checkbox('Generate actual images',True);makeaudio=st.checkbox('Generate Telugu voiceover MP3',True)
    voice=st.selectbox('TTS voice',['alloy','echo','fable','onyx','nova','shimmer'])
    go=st.button('🚀 Generate Reel',type='primary',use_container_width=True)
if go:
    with st.status('Generating reel...',expanded=True) as q:
        q.write('Research + fact-check');kb=research(topic,audience,platform,duration,style,series,episode,prev,nxt,tm)
        q.write('Telugu narration');stt=story(kb,duration,style,tm)
        q.write('Visual Bible');vb=bible(kb,stt,tm)
        q.write('Timed image sequence');sc=scenes(kb,stt,vb,duration,tm)
        q.write('Generating assets');slug,z=build_project(topic,kb,stt,vb,sc,makeimgs,makeaudio,im,voice)
        q.update(label='Reel package complete',state='complete')
    st.session_state.result=(slug,z,kb,stt,vb,sc)
if 'result' in st.session_state:
    slug,z,kb,stt,vb,sc=st.session_state.result
    a,b,c,d,e=st.tabs(['Research','Script','Visual Bible','Image Timeline','Export'])
    with a: st.json(kb)
    with b:
        st.subheader(stt['title']);st.write(stt['hook_telugu']);st.write(stt['setup_telugu']);st.write(stt['beat1_telugu']);st.write(stt['beat2_telugu']);st.write(stt['beat3_telugu']);st.write(stt['resolution_telugu']);st.write(stt['outro_telugu']);st.text_area('Clean Telugu voiceover',stt['voiceover_telugu'],height=260)
    with c: st.json(vb)
    with d:
        st.dataframe([{'Image':f"IMAGE_{int(s['image_number']):02d}",'Start':s['start'],'End':s['end'],'Duration':s['duration'],'Purpose':s['visual_purpose'],'Narration':s['voiceover_segment']} for s in sc],use_container_width=True)
        for s in sc:
            n=int(s['image_number']);p=OUT/slug/'images'/f'IMAGE_{n:02d}.png';st.markdown(f"### IMAGE {n:02d} — {s['start']}–{s['end']} sec");st.write(s['visual_description'])
            if p.exists():st.image(str(p),width=300)
            with st.expander('Prompt & production details'):st.code(s['image_prompt']);st.write('Motion:',s['motion_suggestion']);st.write('On-screen:',s['onscreen_text'])
    with e:
        st.download_button('⬇️ Download complete project ZIP',z.read_bytes(),file_name=z.name,mime='application/zip')
        st.info('Project includes research, Telugu script, visual bible, numbered images, voiceover MP3 when enabled, subtitles and editing timeline.')
else: st.info('Enter the topic and settings, then click Generate Reel.')
