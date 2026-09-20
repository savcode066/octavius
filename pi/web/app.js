'use strict';
const $ = (id) => document.getElementById(id);
let camera = null, recorder = null, microphone = null, audioBlob = null;
let recordTimer, playbackUrl, pending = null, paired = false, asking = false, omniReady = false;
let recordingEpoch = 0;

async function api(path, options = {}) {
  const abort = new AbortController();
  const timer = setTimeout(() => abort.abort(), path === '/interpret' ? 42000 : ['/pickup', '/putdown'].includes(path) ? 30000 : 8000);
  try {
    const response = await fetch(path, {...options, headers: {'X-Octavius': '1', ...(options.headers || {})}, signal: abort.signal});
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || 'Request failed.');
    return data;
  } catch (e) {
    if (e.name === 'AbortError') throw new Error('Request timed out. Check the Pi connection; do not repeat a paid request immediately.');
    throw e;
  } finally { clearTimeout(timer); }
}
const jsonPost = (path, body) => api(path, {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(body)});
async function refresh() {
  try {
    const info = await api('/health');
    paired = info.paired;
    $('connection').textContent = paired ? 'Connected' : 'Pair to control';
    $('pair-panel').hidden = paired;
    omniReady = info.omni.available;
    $('ask').disabled = !omniReady || !paired;
    $('omni-note').textContent = info.omni.available
      ? 'Every Send request makes one paid OMNI call. Recording and camera preview are free.'
      : 'No API key on the Pi. Set YIBU_API_KEY in the Pi .env to use voice. Manual controls still work.';
    $('arm-state').textContent = info.arm.simulated ? 'Simulated' : info.arm.connected ? 'Nano connected' : 'Nano not connected yet';
    $('secure-help').hidden = window.isSecureContext;
  } catch(e) { $('connection').textContent = 'Pi offline'; $('status').textContent = e.message; }
}
$('pair-form').onsubmit = async e => {
  e.preventDefault();
  try { await jsonPost('/pair', {code:$('pair-code').value}); $('pair-code').value=''; await refresh(); }
  catch(e) { $('status').textContent=e.message; }
};
async function command(cmd) {
  pending = null; $('confirm').hidden = true;
  try {
    if (!paired) throw new Error('Enter the pairing code first.');
    $('status').textContent = 'Sending ' + cmd + '…';
    const result = await jsonPost('/command', {command:cmd});
    $('status').textContent = result.nano_response;
  } catch(e) { $('status').textContent=e.message; }
}
async function task(path, body, label) {
  pending = null; $('confirm').hidden = true;
  $('pickup').disabled = $('putdown').disabled = true;
  try {
    if (!paired) throw new Error('Enter the pairing code first.');
    $('status').textContent = label + '…';
    const result = await jsonPost(path, body);
    $('status').textContent = result.aborted ? label + ' stopped.'
      : label + ' done: ' + result.steps.join(', ') + '.';
  } catch(e) { $('status').textContent = e.message; }
  finally { $('pickup').disabled = $('putdown').disabled = false; }
}
$('pickup').onclick = () => task('/pickup', {width_cm: $('width').valueAsNumber}, 'Picking up');
$('putdown').onclick = () => task('/putdown', {}, 'Putting down');
document.querySelectorAll('[data-command]').forEach(b => b.onclick = () => command(b.dataset.command));
$('stop').onclick = () => command('STOP');
$('command-form').onsubmit = e => { e.preventDefault(); command($('command').value); };

function requireMedia() {
  if (!window.isSecureContext || !navigator.mediaDevices?.getUserMedia) {
    $('secure-help').hidden = false;
    throw new Error('Complete the phone certificate setup, then reopen the HTTPS page in Safari.');
  }
}
$('camera').onclick = async () => {
  try {
    requireMedia();
    if (camera) return;
    $('camera').disabled = true;
    camera = await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'},width:{ideal:640},height:{ideal:480},frameRate:{ideal:15,max:20}},audio:false});
    $('preview').srcObject = camera;
    await $('preview').play();
    $('camera-placeholder').hidden = true;
    $('camera-state').textContent = 'Camera on';
    $('media-status').textContent = 'Live preview. A 640px frame is sent only when you tap Send request.';
  } catch(e) {
    if (camera) camera.getTracks().forEach(t=>t.stop());
    camera = null;
    $('media-status').textContent = e.message;
  } finally { $('camera').disabled = false; }
};
function mediaOff() {
  recordingEpoch++;
  if (recorder?.state === 'recording') recorder.stop();
  clearTimeout(recordTimer);
  microphone?.getTracks().forEach(t=>t.stop()); microphone=null;
  camera?.getTracks().forEach(t=>t.stop()); camera=null;
  $('preview').srcObject=null; $('camera-placeholder').hidden=false;
  $('camera-state').textContent='Camera off';
  micState('idle');
  $('media-status').textContent='Camera and microphone are off.';
}
$('media-off').onclick = mediaOff;
document.addEventListener('visibilitychange', () => { if(document.hidden) mediaOff(); });
window.addEventListener('pagehide', mediaOff);
function frame() {
  return new Promise(resolve => {
    const v=$('preview');
    if (!camera || !v.videoWidth) return resolve(null);
    const c=document.createElement('canvas');
    c.width=Math.min(640,v.videoWidth); c.height=Math.round(v.videoHeight*c.width/v.videoWidth);
    c.getContext('2d').drawImage(v,0,0,c.width,c.height);
    c.toBlob(resolve,'image/jpeg',0.7);
  });
}
// Convert browser-native M4A/WebM to the WAV format in the supplied Yibu example.
async function wav(blob) {
  const Context = window.AudioContext || window.webkitAudioContext;
  const context = new Context();
  try {
    const decoded = await context.decodeAudioData(await blob.arrayBuffer());
    const Offline = window.OfflineAudioContext || window.webkitOfflineAudioContext;
    const offline = new Offline(1,Math.min(Math.ceil(decoded.duration*16000),160000),16000);
    const source=offline.createBufferSource(); source.buffer=decoded; source.connect(offline.destination); source.start();
    const samples=(await offline.startRendering()).getChannelData(0);
    const buffer=new ArrayBuffer(44+samples.length*2), view=new DataView(buffer);
    function text(offset,value){for(let i=0;i<value.length;i++)view.setUint8(offset+i,value.charCodeAt(i));}
    text(0,'RIFF');view.setUint32(4,36+samples.length*2,true);text(8,'WAVE');
    text(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);
    view.setUint32(24,16000,true);view.setUint32(28,32000,true);view.setUint16(32,2,true);view.setUint16(34,16,true);
    text(36,'data');view.setUint32(40,samples.length*2,true);
    samples.forEach((v,i)=>view.setInt16(44+i*2,Math.max(-1,Math.min(1,v))*(v<0?32768:32767),true));
    return new Blob([buffer],{type:'audio/wav'});
  } finally { await context.close(); }
}
// idle | recording | preparing. Record starts, Stop ends; neither one sends.
function micState(state) {
  $('record').disabled = state !== 'idle';
  $('stop-record').disabled = state !== 'recording';
}
$('record').onclick = async () => {
  if (recorder?.state === 'recording') return;
  const epoch = ++recordingEpoch;
  try {
    requireMedia();
    if (!window.MediaRecorder) throw new Error('Recording is unavailable in this browser; try current Safari.');
    micState('preparing');
    microphone=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,noiseSuppression:true},video:false});
    if (epoch!==recordingEpoch) {microphone.getTracks().forEach(t=>t.stop());return;}
    const type=['audio/mp4','audio/webm;codecs=opus','audio/webm'].find(t=>MediaRecorder.isTypeSupported(t));
    const active=new MediaRecorder(microphone,type?{mimeType:type}:{});
    recorder=active;const chunks=[];audioBlob=null;
    active.ondataavailable=e=>{if(e.data.size)chunks.push(e.data);};
    // Reached by the Stop button and by the 10 second cap alike.
    active.onstop=async()=>{
      clearTimeout(recordTimer);microphone?.getTracks().forEach(t=>t.stop());microphone=null;
      micState('preparing');
      try {
        if (epoch!==recordingEpoch) return;
        $('record-state').textContent='Preparing audio…';
        const converted=await wav(new Blob(chunks,{type:active.mimeType}));
        if(epoch!==recordingEpoch)return;
        audioBlob=converted;
        if(playbackUrl)URL.revokeObjectURL(playbackUrl);
        playbackUrl=URL.createObjectURL(audioBlob);$('playback').src=playbackUrl;$('playback').hidden=false;
        $('record-state').textContent='Voice ready. Tap Send request to spend one OMNI call.';
      } catch(e){$('record-state').textContent='Recording failed: '+e.message;}
      finally{micState('idle');}
    };
    active.onerror=()=>{mediaOff();$('record-state').textContent='Microphone recording failed. Try again.';};
    active.start();micState('recording');
    $('record-state').textContent='Listening… tap Stop recording, or it stops itself after 10 seconds.';
    recordTimer=setTimeout(()=>{if(active.state==='recording')active.stop();},10000);
  } catch(e){mediaOff();$('record-state').textContent=e.message;}
};
$('stop-record').onclick = () => { if (recorder?.state === 'recording') recorder.stop(); };
function confirmLabel(action) {
  if (action==='PICK_UP') return 'Run: Pick up ('+$('width').value+' cm)';
  if (action==='PUT_DOWN') return 'Run: Put down';
  return 'Run: '+action;
}
$('width').oninput = () => { if (pending) $('confirm').textContent = confirmLabel(pending); };
$('ask-form').onsubmit=async e=>{
  e.preventDefault();
  if(asking)return;
  try{
    if(!paired)throw new Error('Enter the pairing code first.');
    if(recorder?.state==='recording')throw new Error('Stop recording before sending.');
    if($('record').disabled)throw new Error('Wait for the audio to finish preparing.');
    asking=true;$('ask').disabled=true;pending=null;$('confirm').hidden=true;
    const form=new FormData();form.append('text',$('prompt').value);
    const image=await frame();if(image)form.append('photo',image,'frame.jpg');
    if(audioBlob)form.append('audio',audioBlob,'voice.wav');
    $('reply').textContent='OMNI is looking and listening…';
    const result=await api('/interpret',{method:'POST',body:form});
    $('reply').textContent=result.reply;
    $('heard').textContent=result.heard?'Heard: '+result.heard:'';
    pending=result.command;$('confirm').hidden=!pending;
    if(pending)$('confirm').textContent=confirmLabel(pending);
  }catch(e){$('reply').textContent=e.message;}
  finally{asking=false;$('ask').disabled=!omniReady||!paired;}
};
// PICK_UP and PUT_DOWN are tasks, not Nano commands, so they take their own route.
$('confirm').onclick=()=>{
  const action=pending;
  if(!action)return;
  if(action==='PICK_UP')task('/pickup',{width_cm:$('width').valueAsNumber},'Picking up');
  else if(action==='PUT_DOWN')task('/putdown',{},'Putting down');
  else command(action);
};
refresh();
setInterval(()=>{if(!document.hidden)refresh();},10000);
