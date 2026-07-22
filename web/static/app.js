let currentPanel='dashboard';
const panelMeta={
  dashboard:{title:'Dashboard',desc:'Quick search - auto-detect target type'},
  network:{title:'Network Intelligence',desc:'IP geolocation, Shodan, Censys, SecurityTrails, AbuseIPDB'},
  domain:{title:'Domain',desc:'WHOIS and DNS enumeration'},
  subdomain:{title:'Subdomains',desc:'crt.sh, AlienVault OTX, rapiddns'},
  harvest:{title:'Harvest',desc:'Extract emails, hosts, names from search engines'},
  email:{title:'Email',desc:'Validation, HIBP, Gravatar, linked accounts'},
  username:{title:'Username Search',desc:'Search 119 platforms with aggressive detection'},
  search:{title:'People Search',desc:'Search by name across web and directories'},
  dorks:{title:'Google Dorks',desc:'Execute real Google Dork queries'},
  person:{title:'Person',desc:'Combined email+username+graph'},
  phone:{title:'Phone OSINT',desc:'Deep phone analysis: social, leaks, forums, paste sites'},
  leaks:{title:'Leaks',desc:'Breach databases and paste sites'},
  pii:{title:'PII Search',desc:'Reverse search: CURP, SSN, phone to find linked data'},
  docs:{title:'Documents',desc:'Search docs and pastes'},
  web:{title:'Web',desc:'Tech detection, Wayback Machine'},
  face:{title:'Face',desc:'Detection + reverse image search'},
  discord:{title:'Discord',desc:'Public profile lookup, IDs, badges, linked accounts'},
  company:{title:'Company OSINT',desc:'Employees, domains, technologies, LinkedIn, Crunchbase'},
  crypto:{title:'Crypto Lookup',desc:'BTC/ETH address balance, transactions, explorers, OFAC'},
  twitter:{title:'Twitter/X Intel',desc:'Profile lookup, followers, bio, recent tweets'},
  telegram:{title:'Telegram Intel',desc:'Profile, bio, avatar, members, recent messages'},
  geoint:{title:'Geo Intelligence',desc:'IP to address, WiFi BSSID lookup, reverse geocoding'},
  investigate:{title:'Auto-Investigate',desc:'Auto-detect type and run all relevant modules'},
  graph:{title:'Graph View',desc:'Interactive entity graph visualization for saved cases'},
  cases:{title:'Cases',desc:'View and manage saved investigations'},
  metadata:{title:'Metadata',desc:'EXIF, PDF, DOCX, XLSX'},
  settings:{title:'Settings',desc:'Configure API keys'},
};

function switchPanel(n){
  currentPanel=n;
  document.querySelectorAll('#form-card .panel-form').forEach(function(f){f.style.display='none'});
  var form=document.getElementById('form-'+n);
  if(form)form.style.display='block';
  document.getElementById('panel-title').textContent=panelMeta[n].title;
  document.getElementById('panel-desc').textContent=panelMeta[n].desc;
  document.querySelectorAll('.nav-item').forEach(function(n){n.classList.remove('active')});
  var nav=document.querySelector('.nav-item[data-panel="'+n+'"]');
  if(nav)nav.classList.add('active');
  document.getElementById('results-container').classList.remove('visible');
}
document.querySelectorAll('.nav-item').forEach(function(i){i.addEventListener('click',function(){switchPanel(i.dataset.panel)})});

function getTarget(m){var map={network:'network-target',domain:'domain-target',subdomain:'subdomain-target',harvest:'harvest-target',email:'email-target',username:'username-target',search:'search-target',dorks:'dorks-target',phone:'phone-target',leaks:'leaks-target',pii:'pii-target',docs:'docs-target',web:'web-target',company:'company-target',crypto:'crypto-target',twitter:'twitter-target',telegram:'telegram-target',geoint:'geoint-target',investigate:'investigate-target',graph:'graph-target',discord:'discord-target'};var el=document.getElementById(map[m]);return el?el.value.trim():''}

function showToast(m){var t=document.createElement('div');t.className='toast';t.textContent=m;document.body.appendChild(t);setTimeout(function(){t.remove()},3000)}

function quickSearch(){
  var t=document.getElementById('quick-target').value.trim();
  if(!t){showToast('Enter a target');return}
  var m;
  if(t.indexOf('@')>-1)m='email';
  else if(/^\d+\.\d+\.\d+\.\d+$/.test(t))m='network';
  else if(t.startsWith('@'))m='username';
  else if(t.startsWith('+')||/^\d[\d\s\-]+$/.test(t))m='phone';
  else if(t.indexOf('.')>-1&&t.indexOf(' ')===-1)m='domain';
  else m='search';
  switchPanel(m);
  if(m==='username')document.getElementById('username-target').value=t.startsWith('@')?t.substring(1):t;
  else if(m==='search')document.getElementById('search-target').value=t;
  else if(m==='network')document.getElementById('network-target').value=t;
  else if(m==='email')document.getElementById('email-target').value=t;
  else if(m==='domain')document.getElementById('domain-target').value=t;
  else if(m==='phone')document.getElementById('phone-target').value=t;
  runModule(m);
}

async function runModule(module){
  var target=getTarget(module);
  if(!target&&module!=='metadata'&&module!=='face'&&module!=='person'){showToast('Enter target');return}
  var el=document.getElementById('results-content');
  el.innerHTML='<div class="card"><div class="skeleton"><div class="skeleton-line w80"></div><div class="skeleton-line w60"></div><div class="skeleton-line w40"></div></div></div>';
  document.getElementById('results-container').classList.add('visible');
  var body,url;
  if(module==='metadata'){var f=document.getElementById('metadata-file');if(!f||!f.files[0]){showToast('Select file');return}body=new FormData();body.append('file',f.files[0]);url='/api/metadata'}
  else if(module==='face'){var f=document.getElementById('face-file');if(!f||!f.files[0]){showToast('Select image');return}body=new FormData();body.append('file',f.files[0]);url='/api/face'}
  else if(module==='person'){body=new FormData();body.append('email_addr',document.getElementById('person-email').value.trim());body.append('username_target',document.getElementById('person-username').value.trim());url='/api/person'}
  else if(module==='email'){body=new FormData();body.append('target',target);body.append('accounts',document.getElementById('email-accounts').checked);url='/api/email'}
  else if(module==='phone'){body=new FormData();body.append('target',target);url='/api/phone'}
  else if(module==='network'){body=new FormData();body.append('target',target);body.append('ports',document.getElementById('network-ports').checked);url='/api/network'}
  else if(module==='search'){body=new FormData();body.append('name',target);url='/api/search'}
  else if(module==='dorks'){body=new FormData();body.append('name',target);url='/api/dorks'}
  else if(module==='leaks'){body=new FormData();body.append('target',target);url='/api/leaks'}
  else if(module==='pii'){body=new FormData();body.append('target',target);url='/api/pii'}
  else if(module==='docs'){body=new FormData();body.append('query',target);url='/api/docs'}
  else if(module==='discord'){body=new FormData();body.append('target',target);url='/api/discord'}
  else if(module==='company'){body=new FormData();body.append('name',target);url='/api/company'}
  else if(module==='crypto'){body=new FormData();body.append('address',target);url='/api/crypto'}
  else if(module==='twitter'){body=new FormData();body.append('username',target);url='/api/twitter'}
  else if(module==='telegram'){body=new FormData();body.append('target',target);url='/api/telegram'}
  else if(module==='geoint'){body=new FormData();body.append('target',target);url='/api/geoint'}
  else if(module==='investigate'){body=new FormData();body.append('target',target);body.append('depth',document.getElementById('investigate-depth')?document.getElementById('investigate-depth').value:2);url='/api/investigate'}
  else if(module==='graph'){if(!target){showToast('Enter Case ID from Auto-Investigate');return}url='/api/graph/'+encodeURIComponent(target)+'?depth=2';body=null}
  else if(module==='cases'){url='/api/cases';body=null}
  else{body=new FormData();body.append('target',target);url='/api/'+module}
  try{
    var resp=await fetch(url,{method:body?'POST':'GET',body:body});
    if(!resp.ok)throw new Error('HTTP '+resp.status);
    var data=await resp.json();
    renderResults(module,data);
  }catch(err){el.innerHTML='<div class="card"><div style="color:var(--red)">Error: '+esc(err.message)+'</div></div>'}
}

function renderResults(m,d){var el=document.getElementById('results-content');try{
switch(m){
case'network':el.innerHTML=renderNetwork(d);break;case'domain':el.innerHTML=renderDomain(d);break;
case'subdomain':el.innerHTML=renderSubdomain(d);break;case'harvest':el.innerHTML=renderHarvest(d);break;
case'email':el.innerHTML=renderEmail(d);break;case'username':el.innerHTML=renderUsername(d);break;
case'search':el.innerHTML=renderPeopleSearch(d);break;case'dorks':el.innerHTML=renderDorks(d);break;
case'person':el.innerHTML=renderPerson(d);break;case'phone':el.innerHTML=renderPhone(d);break;
case'leaks':el.innerHTML=renderLeaks(d);break;case'pii':el.innerHTML=renderPii(d);break;
case'docs':el.innerHTML=renderDocs(d);break;case'web':el.innerHTML=renderWeb(d);break;
case'face':el.innerHTML=renderFace(d);break;case'discord':el.innerHTML=renderDiscord(d);break;
case'company':el.innerHTML=renderCompany(d);break;
case'crypto':el.innerHTML=renderCrypto(d);break;
case'twitter':el.innerHTML=renderTwitterIntel(d);break;
case'telegram':el.innerHTML=renderTelegramIntel(d);break;
case'geoint':el.innerHTML=renderGeoIntel(d);break;
case'investigate':el.innerHTML=renderInvestigate(d);break;
case'graph':el.innerHTML=renderGraphView(d);break;
case'cases':el.innerHTML=renderCasesList(d);break;
case'metadata':el.innerHTML=renderMetadata(d);break;
default:el.innerHTML='<div class="card"><pre style="font-size:0.78rem;overflow-x:auto">'+JSON.stringify(d,null,2)+'</pre></div>';
}}catch(err){el.innerHTML='<div class="card"><div style="color:var(--red)">Render error: '+esc(err.message)+'</div><pre style="font-size:0.7rem">'+JSON.stringify(d,null,2)+'</pre></div>'}}

function esc(s){var d=document.createElement('div');d.textContent=String(s||'');return d.innerHTML}
function fmtKey(k){return k.replace(/_/g,' ').replace(/\b\w/g,function(c){return c.toUpperCase()})}
function fmtBytes(b){if(b<1024)return b+' B';if(b<1048576)return(b/1024).toFixed(1)+' KB';return(b/1048576).toFixed(1)+' MB'}
function buildStat(l,v,t){return'<div class="stat '+t+'"><div class="stat-value">'+esc(String(v))+'</div><div class="stat-label">'+l+'</div></div>'}
function copyText(t){navigator.clipboard.writeText(t).then(function(){showToast('Copied!')})}
function saveSettings(){showToast('Settings saved (client-side)')}

// RENDER FUNCTIONS

function renderNetwork(d){var h='';var g=d.geolocation||{};if(Object.keys(g).length){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">&#127758; Geolocation</div><span class="badge badge-info">'+esc(g.country||'?')+'</span></div><div class="kv-grid">';for(var k in g){if(g[k]&&k!=='maps_url'&&k!=='street_view')h+='<div class="kv-item"><div class="kv-key">'+fmtKey(k)+'</div><div class="kv-value">'+esc(g[k])+'</div></div>'}h+='</div>';if(g.maps_url)h+='<a class="map-link" href="'+g.maps_url+'" target="_blank">&#128205; Google Maps</a>';h+='</div>'}if(d.shodan&&d.shodan.available){var s=d.shodan;h+='<div class="card"><div class="result-card-header"><div class="result-card-title">&#128737; Shodan</div></div>';h+='<div class="kv-row"><span>Org</span><span>'+esc(s.org||'?')+'</span></div>';h+='<div class="kv-row"><span>Ports</span><span>'+(s.ports||[]).join(', ')+'</span></div>';h+='</div>'}if(d.censys&&d.censys.available){var cs=d.censys;h+='<div class="card"><div class="result-card-header"><div class="result-card-title">&#128268; Censys (Free)</div></div>';if(cs.os)h+='<div class="kv-row"><span>OS</span><span>'+esc(cs.os)+'</span></div>';h+='</div>'}if(d.risk_summary&&d.risk_summary.length){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">&#9888; Risk</div></div>';d.risk_summary.forEach(function(r){var c=r.level==='critical'?'var(--red)':r.level==='high'?'var(--orange)':'var(--yellow)';h+='<div style="color:'+c+';padding:0.3rem 0">&#9888; '+esc(r.type)+'</div>'});h+='</div>'}return h||'<div class="card">No results</div>'}

function renderDomain(d){var h='';if(d.whois){var w=d.whois;h+='<div class="card"><div class="stat-grid">';h+=buildStat('Registrar',w.registrar||'?','info');h+=buildStat('Nameservers',(w.name_servers&&w.name_servers.length)||0,'info');h+='</div></div>'}if(d.dns&&d.dns.dns_records){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">DNS Records</div></div>';for(var rtype in d.dns.dns_records){var recs=d.dns.dns_records[rtype];if(recs.length)h+='<div style="margin-top:0.4rem"><span class="badge badge-info">'+rtype+'</span> '+recs.map(function(r){return'<span class="tag" style="font-family:monospace">'+esc(r)+'</span>'}).join(' ')+'</div>'}h+='</div>'}return h||'<div class="card">No data</div>'}

function renderSubdomain(d){var h='<div class="card"><div class="stat-grid">';h+=buildStat('Total',d.total_unique||0,'success');h+='</div></div>';if(d.sources){for(var src in d.sources){var info=d.sources[src];h+='<div class="card"><div class="result-card-header"><div class="result-card-title">'+esc(String(src).toUpperCase())+'</div><span class="badge badge-info">'+(info.count||0)+'</span></div>';if(info.subdomains&&info.subdomains.length){h+='<div style="max-height:200px;overflow-y:auto">';info.subdomains.slice(0,50).forEach(function(s){h+='<div class="kv-row"><span style="font-family:monospace;font-size:0.78rem">'+esc(s)+'</span></div>'});h+='</div>'}h+='</div>'}}return h}

function renderHarvest(d){var h='<div class="card"><div class="stat-grid">';h+=buildStat('Emails',d.emails_count||0,'success');h+=buildStat('Hosts',d.hosts_count||0,'info');h+='</div></div>';if(d.emails&&d.emails.length){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">Emails ('+d.emails.length+')</div><button class="copy-btn" onclick="copyText('+JSON.stringify(d.emails.slice(0,50).join('\\n'))+')">Copy</button></div>';d.emails.slice(0,50).forEach(function(e){h+='<div class="kv-row"><span style="font-family:monospace;font-size:0.78rem">'+esc(e)+'</span></div>'});h+='</div>'}return h}

function renderEmail(d){var h='';var v=d.validation||{};h+='<div class="card"><div class="stat-grid">';h+=buildStat('Valid',v.valid_format?'Yes':'No',v.valid_format?'success':'danger');h+=buildStat('Score',v.score||0,'info');h+=buildStat('Free',v.free_provider?'Yes':'No','info');h+='</div></div>';if(d.mx&&d.mx.mx_providers&&d.mx.mx_providers.length)h+='<div class="card"><div class="result-card-header"><div class="result-card-title">Provider</div></div>'+d.mx.mx_providers.map(function(p){return'<span class="tag" style="font-size:0.8rem">'+esc(p)+'</span>'}).join(' ')+'</div>';if(d.breaches&&d.breaches.pwned){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">Breaches</div><span class="badge badge-danger">'+d.breaches.breaches_count+'</span></div>';var sorted=[].concat(d.breaches.breaches||[]).sort(function(a,b){return(b.sensitive||0)-(a.sensitive||0)});sorted.forEach(function(b){h+='<div class="breach-card"><div style="display:flex;justify-content:space-between"><strong>'+esc(b.name||'?')+'</strong><span class="badge '+(b.sensitive?'badge-critical':'badge-info')+'">'+(b.sensitive?'SENSITIVE':b.date||'')+'</span></div>';if(b.description)h+='<div style="font-size:0.72rem;color:var(--text-dim)">'+esc(b.description).substring(0,200)+'</div>';h+='</div>';h+='</div>'});h+='</div>'}if(d.gravatar&&d.gravatar.has_gravatar){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">Gravatar</div><span class="badge badge-success">Found</span></div>';var gp=d.gravatar.profile||{};if(gp.display_name)h+='<div class="kv-row"><span>Name</span><span>'+esc(gp.display_name)+'</span></div>';h+='</div>'}if(d.linked_accounts&&d.linked_accounts.accounts_found>0){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">Linked Accounts</div><span class="badge badge-success">'+d.linked_accounts.accounts_found+'</span></div>';d.linked_accounts.accounts.forEach(function(a){h+='<div class="profile-card"><div class="profile-avatar">&#128279;</div><div class="profile-info"><div class="profile-name">'+esc(a.platform)+'</div></div></div>'});h+='</div>'}return h||'<div class="card">No results</div>'}

function renderUsername(d){var h='<div class="card"><div class="stat-grid">';h+=buildStat('Checked',d.sites_checked||0,'info');h+=buildStat('Found',d.found_count||0,d.found_count>0?'success':'danger');h+='</div></div>';var found=d.found||[];found.forEach(function(f){if(!f)return;var sn=(f.name||f.site||'Unknown').toString();h+='<div class="profile-card">';var pd=f.profile_data||{};var av=pd.avatar||'';h+='<div class="profile-avatar">';if(av)h+='<img src="'+esc(av)+'" alt="" onerror="this.style.display=none" style="display:none">';else h+=esc((sn[0]||'?').toUpperCase());h+='</div><div class="profile-info"><div class="profile-platform">'+esc(sn)+'</div>';if(pd.display_name)h+='<div class="profile-name">'+esc(pd.display_name)+'</div>';if(pd.description)h+='<div class="profile-bio">'+esc(pd.description).substring(0,100)+'</div>';if(pd.location)h+='<div class="profile-location">&#128205; '+esc(pd.location)+'</div>';h+='</div>';if(f.url)h+='<a class="profile-link" href="'+esc(f.url)+'" target="_blank">Open &#8599;</a>';h+='</div>'});return h||renderRaw(d)}

function renderPeopleSearch(d){var h='';h+='<div class=\"card\"><div class=\"stat-grid\">';h+=buildStat('Total Sources',d.total_sources||0,'info');h+=buildStat('Mentions',(d.web_mentions||[]).length,'info');h+=buildStat('Social',(d.social_search_urls||[]).length,'info');h+=buildStat('Directories',(d.people_directories||[]).length,'info');h+=buildStat('Dorks',(d.dorks||[]).length,'info');h+='</div></div>';
if(d.social_search_urls&&d.social_search_urls.length){h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">&#128270; Social Media Searches ('+d.social_search_urls.length+')</div><span class=\"badge badge-info\">Click to open</span></div>';d.social_search_urls.forEach(function(s){h+='<div class=\"kv-row\"><span>'+esc(s.platform)+'</span><a href=\"'+esc(s.url)+'\" target=\"_blank\" style=\"color:var(--accent);font-size:0.8rem\">Search '+esc(s.platform)+' &#8599;</a></div>'});h+='</div>'}
if(d.people_directories&&d.people_directories.length){h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">&#128203; People Directories ('+d.people_directories.length+')</div><span class=\"badge badge-info\">Click to open</span></div>';d.people_directories.forEach(function(dir){h+='<div class=\"kv-row\"><span>'+esc(dir.name)+'</span><a href=\"'+esc(dir.url)+'\" target=\"_blank\" style=\"color:var(--accent);font-size:0.8rem\">Search &#8599;</a></div>'});h+='</div>'}
if(d.dorks&&d.dorks.length){h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">&#128736; Google Dorks ('+d.dorks.length+')</div><span class=\"badge badge-warn\">Click to open</span></div>';d.dorks.forEach(function(dk){h+='<div style=\"padding:0.5rem;margin-bottom:0.3rem;background:var(--surface);border-radius:4px;border-left:3px solid var(--accent)\"><strong style=\"font-size:0.82rem\">'+esc(dk.label)+'</strong><br><a href=\"'+esc(dk.url)+'\" target=\"_blank\" class=\"map-link\" style=\"font-size:0.72rem;margin-top:0.25rem\">Open in Google &#8599;</a></div>'});h+='</div>'}
if(d.web_mentions&&d.web_mentions.length){h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">&#127760; Web Mentions ('+d.web_mentions.length+')</div></div>';d.web_mentions.slice(0,10).forEach(function(w){h+='<div class=\"dork-result\"><strong>'+esc(w.title||'Untitled')+'</strong>';if(w.url)h+='<a href=\"'+esc(w.url)+'\" target=\"_blank\">'+esc(w.url).substring(0,80)+'</a>';h+='</div>'});h+='</div>'}return h||'<div class=\"card\">No results</div>'}

function renderDorks(d){var h='';h+='<div class=\"card\"><div class=\"stat-grid\">';h+=buildStat('Dorks',d.dorks_executed||0,'info');h+=buildStat('Results',d.total_results||0,d.total_results>0?'success':'warn');h+='</div></div>';if(d.results_by_category){var hasAny=false;for(var cat in d.results_by_category){var data=d.results_by_category[cat];if(data.results&&data.results.length){hasAny=true;break}}if(hasAny){h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">&#127760; Search Results</div></div>';for(var cat in d.results_by_category){var data=d.results_by_category[cat];if(!data.results||!data.results.length)continue;h+='<div class=\"result-card-header\" style=\"margin-top:0.5rem\"><div class=\"result-card-title\">'+esc(data.label)+'</div><span class=\"badge badge-info\">'+data.results_count+' results</span></div>';data.results.slice(0,4).forEach(function(r){h+='<div class=\"dork-result\"><strong>'+esc(r.title||'?')+'</strong>';if(r.url)h+='<a href=\"'+esc(r.url)+'\" target=\"_blank\">'+esc(r.url).substring(0,80)+'</a>';if(r.snippet)h+='<div style=\"font-size:0.72rem;color:var(--text-dim)\">'+esc(r.snippet).substring(0,150)+'</div>';h+='</div>'});h+='</div>'}h+='</div>'}else{for(var cat in d.results_by_category){var data=d.results_by_category[cat];if(!data.query)continue;h+='<div style=\"padding:0.5rem;margin-bottom:0.3rem;background:var(--surface);border-radius:4px;border-left:3px solid var(--accent)\"><strong style=\"font-size:0.82rem\">'+esc(data.label)+'</strong><br><a href=\"https://www.google.com/search?q='+encodeURIComponent(data.query)+'\" target=\"_blank\" class=\"map-link\" style=\"font-size:0.72rem;margin-top:0.25rem\">Open in Google &#8599;</a></div>'}}}return h||'<div class=\"card\">No results</div>'}

function renderPerson(d){var h='';var cross=d.cross_reference||{};var risk=cross.risk_level||'unknown';h+='<div class="card"><div class="result-card-header"><div class="result-card-title">Person Report</div><span class="badge badge-'+(risk==='critical'||risk==='high'?'danger':risk==='medium'?'warn':'success')+'">'+risk.toUpperCase()+'</span></div>';h+='<div style="height:4px;background:var(--border);border-radius:2px;margin:0.5rem 0"><div style="height:100%;border-radius:2px;background:'+(risk==='critical'?'var(--red)':'var(--green)')+';width:'+(risk==='critical'?'100':'25')+'%"></div></div>';(cross.findings||[]).forEach(function(f){h+='<div style="display:flex;gap:0.5rem;padding:0.4rem 0;border-bottom:1px solid var(--border)"><div>&#128994;</div><div><strong style="font-size:0.82rem">'+esc(f.type)+'</strong><div style="font-size:0.75rem;color:var(--text-dim)">'+esc(f.detail)+'</div></div></div>'});h+='</div>';h+=renderEmail(d.email_intel||{});h+=renderUsername(d.username_intel||{});return h}

function renderPhone(d){var basic=d.basic||d;var h='';h+='<div class="card"><div class="stat-grid">';h+=buildStat('Valid',basic.valid?'Yes':'No',basic.valid?'success':'danger');h+=buildStat('Country',basic.country||'?','info');h+=buildStat('Carrier',basic.carrier||'?',basic.carrier&&basic.carrier!=='Unknown'?'success':'warn');h+=buildStat('Type',basic.line_type||'?','info');h+='</div>';h+='<div class="kv-grid">';if(basic.international)h+='<div class="kv-item"><div class="kv-key">International</div><div class="kv-value">'+esc(basic.international)+'</div></div>';if(basic.national)h+='<div class="kv-item"><div class="kv-key">National</div><div class="kv-value">'+esc(basic.national)+'</div></div>';if(basic.e164)h+='<div class="kv-item"><div class="kv-key">E.164</div><div class="kv-value">'+esc(basic.e164)+'</div></div>';if(basic.region)h+='<div class="kv-item"><div class="kv-key">Region</div><div class="kv-value">'+esc(basic.region)+'</div></div>';if(basic.timezone&&basic.timezone.length)h+='<div class="kv-item"><div class="kv-key">Timezone</div><div class="kv-value">'+esc(basic.timezone.join(', '))+'</div></div>';h+='</div></div>';if(d.social_media&&d.social_media.accounts){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">&#128172; Linked Apps ('+d.social_media.linked_count+'/5)</div></div>';d.social_media.accounts.forEach(function(a){var icon=a.found?'&#9989;':'&#10060;';var name=a.platform;var detail=a.detail||'';h+='<div class="profile-card"><div class="profile-avatar" style="font-size:1.1rem">'+icon+'</div><div class="profile-info"><div class="profile-name">'+esc(name)+'</div><div style="font-size:0.72rem;color:var(--text-dim)">'+esc(detail)+'</div>';if(a.url)h+='<a class="profile-link" href="'+esc(a.url)+'" target="_blank">Open &#8599;</a>';h+='</div></div>'});h+='</div>'}if(d.paste_sites&&d.paste_sites.length){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">&#128308; Leak Sites ('+d.paste_sites_count+')</div></div>';d.paste_sites.slice(0,8).forEach(function(p){h+='<div class="breach-card"><a href="'+esc(p.url)+'" target="_blank" style="color:var(--accent);font-size:0.75rem;word-break:break-all">'+esc(p.url).substring(0,80)+'</a></div>'});h+='</div>'}if(d.forum_mentions&&d.forum_mentions.length){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">&#128172; Forum Mentions ('+d.forum_mentions_count+')</div></div>';d.forum_mentions.slice(0,5).forEach(function(p){h+='<div class="kv-row"><span>'+esc(p.title||'').substring(0,60)+'</span><a href="'+esc(p.url)+'" target="_blank" style="color:var(--accent);font-size:0.75rem">Open</a></div>'});h+='</div>'}if(d.risk_assessment&&d.risk_assessment.length){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">&#9888; Risk Assessment</div></div>';d.risk_assessment.forEach(function(r){var c=r.level==='high'?'var(--red)':r.level==='medium'?'var(--yellow)':'var(--green)';h+='<div style="color:'+c+';padding:0.25rem 0;font-size:0.82rem">&#9888; '+esc(r.detail)+'</div>'});h+='</div>'}return h||'<div class="card">No results</div>'}

function renderLeaks(d){var h='';if(d.total_leak_hits>0){h+='<div class="card"><div class="stat-grid">';h+=buildStat('Hits',d.total_leak_hits||0,'danger');h+=buildStat('Psbdmp',d.psbdmp_count||0,'danger');h+=buildStat('Holehe',d.holehe_registered||0,'info');h+='</div></div>'}if(d.holehe_sites&&d.holehe_sites.length){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">Registered Accounts</div><span class="badge badge-success">'+d.holehe_sites.length+'</span></div>';d.holehe_sites.forEach(function(s){h+='<div class="kv-row"><span>'+esc(s.site)+'</span><span class="badge badge-success">Found</span></div>'});h+='</div>'}h+='<div class="card"><div class="result-card-header"><div class="result-card-title">Manual Search</div></div>';(d.leak_databases||[]).forEach(function(db){h+='<div class="kv-row"><span>'+esc(db.name)+'</span><a href="'+esc(db.url)+'" target="_blank" style="color:var(--accent);font-size:0.78rem">Search</a></div>'});h+='</div>';return h}

function renderPii(d){var h='<div class="card"><div class="stat-grid">';h+=buildStat('Type',d.pii_type||'?','info');h+=buildStat('Sources',d.sources_found||0,'info');h+=buildStat('Data Found',d.total_linked_data||0,d.total_linked_data>0?'danger':'info');h+='</div></div>';if(d.all_emails_found&&d.all_emails_found.length){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">Emails ('+d.all_emails_found.length+')</div></div>';d.all_emails_found.slice(0,15).forEach(function(e){h+='<div class="kv-row"><span style="font-family:monospace;font-size:0.78rem">'+esc(e)+'</span></div>'});h+='</div>'}if(d.all_phones_found&&d.all_phones_found.length){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">Phones ('+d.all_phones_found.length+')</div></div>';d.all_phones_found.slice(0,10).forEach(function(p){h+='<div class="kv-row">'+esc(p)+'</div>'});h+='</div>'}if(d.all_names_found&&d.all_names_found.length){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">Names ('+d.all_names_found.length+')</div></div>';d.all_names_found.slice(0,10).forEach(function(n){h+='<div class="kv-row">'+esc(n)+'</div>'});h+='</div>'}return h||'<div class="card">No linked data found</div>'}

function renderDocs(d){var h='<div class="card"><div class="stat-grid">';h+=buildStat('Documents',d.total_findings||0,'info');h+='</div></div>';if(d.findings&&d.findings.length){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">Found Documents</div></div>';d.findings.slice(0,20).forEach(function(f){h+='<div class="dork-result"><strong>['+esc(f.source)+']</strong> <a href="'+esc(f.url)+'" target="_blank">'+esc(f.url).substring(0,80)+'</a></div>'});h+='</div>'}return h}

function renderWeb(d){var h='';var tech=d.technologies||{};if(tech.technologies&&tech.technologies.length){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">Technologies</div><span class="badge badge-info">'+tech.technologies.length+'</span></div>'+tech.technologies.map(function(t){return'<span class="tag">'+esc(t)+'</span>'}).join(' ');h+='</div>'}if(d.wayback&&d.wayback.length){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">Wayback</div><span class="badge badge-info">'+d.wayback.length+'</span></div>';d.wayback.slice(0,10).forEach(function(w){h+='<div class="kv-row"><span>'+(w.timestamp||'').substring(0,10)+'</span><a href="'+(w.archive_url||'#')+'" target="_blank" style="color:var(--accent);font-size:0.75rem">View</a></div>'});h+='</div>'}return h||'<div class="card">No results</div>'}

function renderFace(d){var h='';if(d.faces_detected>0){h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">Faces Detected</div><span class=\"badge badge-success\">'+d.faces_detected+'</span></div>';var dd=d.detection_details||{};if(dd.demographics&&dd.demographics.length){h+='<div class=\"stat-grid\">';dd.demographics.forEach(function(dm){if(dm.age)h+=buildStat('Age','~'+Math.round(dm.age),'info');if(dm.gender)h+=buildStat('Gender',dm.gender,'info');if(dm.emotion)h+=buildStat('Emotion',dm.emotion,'info');if(dm.race)h+=buildStat('Race',dm.race,'info')});h+='</div>'}h+='</div>';if(d.reverse_search_yandex){var ys=d.reverse_search_yandex;if(ys.results_url)h+='<a class=\"map-link\" href=\"'+ys.results_url+'\" target=\"_blank\">Yandex Results</a>';if(ys.results&&ys.results.length){h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">Yandex Images ('+ys.results.length+')</div></div>';ys.results.slice(0,8).forEach(function(r){h+='<div class=\"kv-row\"><span>'+esc(r.source||'?')+'</span><a href=\"'+esc(r.url)+'\" target=\"_blank\" style=\"color:var(--accent);font-size:0.72rem\">Open</a></div>'});h+='</div>'}}if(d.reverse_search_google){var gs=d.reverse_search_google;if(gs.results_url)h+='<a class=\"map-link\" href=\"'+gs.results_url+'\" target=\"_blank\">Google Lens Results</a>'}}else h+='<div class=\"card\">No faces detected</div>';return h}

function renderDiscord(d){var h='<div class="card"><div class="stat-grid">';h+=buildStat('Sites',(d.sites||[]).length,'info');h+=buildStat('IDs',(d.possible_ids||[]).length,'info');h+=buildStat('Profiles',(d.profiles_found||[]).length,'info');h+='</div></div>';if(d.profiles_found&&d.profiles_found.length){d.profiles_found.forEach(function(p){var pr=p.profile||{};h+='<div class="card"><div class="result-card-header"><div class="result-card-title">'+esc(pr.username||'?')+'#'+esc(pr.discriminator||'0')+'</div></div>';if(pr.display_name)h+='<div class="kv-row"><span>Display</span><span>'+esc(pr.display_name)+'</span></div>';if(p.badges&&p.badges.length)h+='<div style="margin-top:0.3rem">'+p.badges.map(function(b){return'<span class="tag">'+esc(b)+'</span>'}).join(' ')+'</div>'});h+='</div>'}if(d.sites&&d.sites.length){d.sites.forEach(function(s){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">'+esc(s.name)+'</div>';h+=s.found?'<span class="badge badge-success">Found</span>':'<span class="badge badge-danger">Not Found</span>';h+='</div>';if(s.ids_found&&s.ids_found.length){s.ids_found.forEach(function(id){h+='<div class="kv-row"><span style="font-family:monospace">'+esc(id)+'</span><a href="https://discord.id/lookup/'+esc(id)+'" target="_blank" class="btn btn-sm btn-outline">View</a></div>'})}if(s.url)h+='<a class="map-link" href="'+esc(s.url)+'" target="_blank">Open</a>';h+='</div>'})}if(d.possible_ids&&d.possible_ids.length){h+='<div class="card"><div class="result-card-header"><div class="result-card-title">Discord User IDs</div></div>';d.possible_ids.forEach(function(id){h+='<div class="kv-row"><span style="font-family:monospace">'+esc(id)+'</span></div>'});h+='</div>'}return h||'<div class="card">No results</div>'}

function renderCompany(d){var h='';h+='<div class=\"card\"><div class=\"stat-grid\">';h+=buildStat('Mentions',(d.web_mentions||[]).length,'info');h+=buildStat('Social',(d.social_search_urls||[]).length,'info');h+=buildStat('Info Links',(d.info_links||[]).length,'info');h+='</div></div>';if(d.web_mentions&&d.web_mentions.length){h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">Web Results</div></div>';d.web_mentions.slice(0,8).forEach(function(w){h+='<div class=\"dork-result\"><strong>'+esc(w.title||'?')+'</strong>';if(w.url)h+='<a href=\"'+esc(w.url)+'\" target=\"_blank\">'+esc(w.url).substring(0,80)+'</a>';h+='</div>'});h+='</div>'}if(d.social_search_urls&&d.social_search_urls.length){h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">Social Search</div></div>';d.social_search_urls.forEach(function(s){h+='<div class=\"kv-row\"><span>'+esc(s.platform)+'</span><a href=\"'+esc(s.url)+'\" target=\"_blank\" style=\"color:var(--accent);font-size:0.78rem\">Open</a></div>'});h+='</div>'}if(d.info_links&&d.info_links.length){h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">Info & Tools</div></div>';d.info_links.forEach(function(s){h+='<div class=\"kv-row\"><span>'+esc(s.name)+'</span><a href=\"'+esc(s.url)+'\" target=\"_blank\" style=\"color:var(--accent);font-size:0.78rem\">Open</a></div>'});h+='</div>'}return h||'<div class=\"card\">No results</div>'}

function renderCrypto(d){var h='';h+='<div class=\"card\"><div class=\"stat-grid\">';h+=buildStat('Type',d.type||'?','info');var tx=d.transactions||{};if(tx.final_balance!==undefined)h+=buildStat('Balance',tx.final_balance+' BTC','success');if(tx.balance!==undefined)h+=buildStat('Balance',tx.balance+' ETH','success');if(tx.n_tx)h+=buildStat('Transactions',tx.n_tx,'info');h+='</div></div>';if(d.explorers&&d.explorers.length){d.explorers.forEach(function(e){h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">'+esc(e.name)+'</div></div>';h+='<a class=\"map-link\" href=\"'+esc(e.url)+'\" target=\"_blank\">Open Explorer</a>';h+='</div>'});h+='</div>'}if(d.sanctions_check)h+='<div class=\"card\"><a class=\"map-link\" href=\"'+esc(d.sanctions_check)+'\" target=\"_blank\">Check OFAC Sanctions</a></div>';return h}

function renderTwitterIntel(d){var h='';var p=d.profile||{};if(Object.keys(p).length){h+='<div class=\"card\"><div class=\"stat-grid\">';h+=buildStat('Followers',p.followers||0,'info');h+=buildStat('Following',p.following||0,'info');h+=buildStat('Tweets',p.tweets_count||0,'info');if(p.verified)h+=buildStat('Verified','Yes','success');h+='</div>';if(p.display_name)h+='<div class=\"kv-row\"><span>Name</span><span>'+esc(p.display_name)+'</span></div>';if(p.description)h+='<div class=\"kv-row\"><span>Bio</span><span>'+esc(p.description)+'</span></div>';if(p.location)h+='<div class=\"kv-row\"><span>Location</span><span>'+esc(p.location)+'</span></div>';if(p.created)h+='<div class=\"kv-row\"><span>Created</span><span>'+p.created+'</span></div>';h+='</div>'}if(d.recent_tweets&&d.recent_tweets.length){h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">Recent Tweets</div></div>';d.recent_tweets.forEach(function(t){h+='<div class=\"dork-result\"><strong>'+esc(t.date||'?')+'</strong><div style=\"font-size:0.82rem;margin-top:0.25rem\">'+esc(t.content||'').substring(0,200)+'</div>';if(t.url)h+='<a href=\"'+esc(t.url)+'\" target=\"_blank\">Open Tweet</a>';h+='</div>'});h+='</div>'}if(d.error)h+='<div class=\"card\"><span style=\"color:var(--text-dim)\">'+esc(d.error)+'</span></div>';return h||'<div class=\"card\">No results</div>'}

function renderTelegramIntel(d){var h='';var p=d.profile||{};if(d.found){h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">Profile Found</div><span class=\"badge badge-success\">Active</span></div>';if(p.display_name)h+='<div class=\"kv-row\"><span>Name</span><span>'+esc(p.display_name)+'</span></div>';if(p.bio)h+='<div class=\"kv-row\"><span>Bio</span><span>'+esc(p.bio).substring(0,200)+'</span></div>';if(p.members)h+='<div class=\"kv-row\"><span>Members</span><span>'+esc(p.members)+'</span></div>';if(p.avatar)h+='<div style=\"margin-top:0.5rem\"><img src=\"'+esc(p.avatar)+'\" style=\"width:80px;height:80px;border-radius:50%\"></div>';h+='</div>'}if(d.recent_messages&&d.recent_messages.length){h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">Recent Messages</div></div>';d.recent_messages.forEach(function(m){h+='<div class=\"dork-result\">'+esc(m)+'</div>'});h+='</div>'}return h||'<div class=\"card\">Not found</div>'}

function renderGeoIntel(d){var h='';h+='<div class=\"card\"><div class=\"stat-grid\">';if(d.city)h+=buildStat('City',d.city,'info');if(d.country)h+=buildStat('Country',d.country,'info');if(d.isp)h+=buildStat('ISP',d.isp,'info');h+='</div></div>';if(d.display_name)h+='<div class=\"card\"><div class=\"kv-row\"><span>Address</span><span>'+esc(d.display_name)+'</span></div></div>';if(d.address){h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">Address Details</div></div>';var a=d.address;if(a.road)h+='<div class=\"kv-row\"><span>Road</span><span>'+esc(a.road)+'</span></div>';if(a.city)h+='<div class=\"kv-row\"><span>City</span><span>'+esc(a.city)+'</span></div>';if(a.state)h+='<div class=\"kv-row\"><span>State</span><span>'+esc(a.state)+'</span></div>';if(a.country)h+='<div class=\"kv-row\"><span>Country</span><span>'+esc(a.country)+'</span></div>';h+='</div>'}if(d.maps_url)h+='<a class=\"map-link\" href=\"'+esc(d.maps_url)+'\" target=\"_blank\">&#128205; Open in Maps</a>';if(d.found!==undefined){if(d.found)h+='<div class=\"card\"><span class=\"badge badge-success\">WiFi BSSID Found on WiGLE</span></div>';if(d.coordinates)h+='<div class=\"kv-row\"><span>Location</span><span>Lat: '+d.coordinates.lat+', Lon: '+d.coordinates.lon+'</span></div>'}return h||'<div class=\"card\">No results</div>'}

function renderGraphView(d){var h='';
if(!d||!d.nodes||!d.nodes.length){
  h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">No Graph Data</div></div>';
  h+='<p style=\"color:var(--text-dim);margin-bottom:1rem\">The entity graph shows relationships between discovered data points (email \u2192 usernames \u2192 social profiles \u2192 locations...).</p>';
  h+='<p style=\"color:var(--text-dim);margin-bottom:1rem\">To generate a graph:</p>';
  h+='<ol style=\"color:var(--text-dim);margin-left:1.5rem;margin-bottom:1rem\">';
  h+='<li>Go to <b>Auto-Investigate</b> panel</li>';
  h+='<li>Enter any target (email, domain, phone, or name)</li>';
  h+='<li>Click Investigate</li>';
  h+='<li>Copy the <b>Case ID</b> from the results</li>';
  h+='<li>Come back here and paste the Case ID</li>';
  h+='</ol>';
  h+='<p style=\"color:var(--text-dim)\">Or go to <b>Cases</b> panel and click \"Load Graph\" on any saved case.</p>';
  h+='</div>';
  return h;
}
h+='<div class=\"card\"><div class=\"stat-grid\">';h+=buildStat('Entities',d.total_nodes||0,'info');h+=buildStat('Relationships',d.total_edges||0,'info');h+='</div></div>';
h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">&#128301; Interactive Entity Graph</div><span style=\"font-size:0.7rem;color:var(--text-dim)\">Drag nodes \u2022 Scroll to zoom \u2022 Colors = entity types</span></div>';
h+='<div id=\"graph-canvas\" style=\"width:100%;height:500px;background:var(--bg);border:1px solid var(--border);border-radius:8px\"></div>';
h+='<div id=\"graph-legend\" style=\"margin-top:0.5rem;display:flex;flex-wrap:wrap;gap:0.5rem\"></div>';
h+='</div>';

// Store graph data for vis.js
var nodesData=d.nodes.map(function(n){return{id:n.id,label:n.type.substring(0,10)+': '+n.value.substring(0,20),title:n.type+' | '+n.value,group:n.type}});
var edgesData=d.edges.map(function(e){return{from:e.source,to:e.target,label:e.relationship,arrows:'to',title:e.relationship+' (confidence: '+Math.round((e.confidence||0.5)*100)+'%)'}});

if(d.investigation_id)h+='<div class=\"card\"><span style=\"color:var(--text-dim)\">Case ID: </span><code>'+esc(d.investigation_id)+'</code></div>';

// Render graph after DOM update
setTimeout(function(){
  renderGraph(nodesData,edgesData,['Email','Person','Phone','Domain','IP','Username','SocialProfile','Breach','Location','Wallet','Company','Document','Discord']);
}, 400);

return h}

function renderGraph(nodesArr,edgesArr,types){
  var container=document.getElementById('graph-canvas');
  if(!container||!window.vis)return;
  var nodes=new vis.DataSet(nodesArr);
  var edges=new vis.DataSet(edgesArr);
  var colors={'Email':'#2ea043','Person':'#3b9eff','Phone':'#d29922','Domain':'#a371f7','IP':'#da3633','Username':'#e36209','SocialProfile':'#58a6ff','Breach':'#f85149','Location':'#7ee787','Wallet':'#d29922','Company':'#a371f7','Document':'#8b949e','Discord':'#5865F2'};
  var groups={};
  types.forEach(function(t){groups[t]={color:{background:colors[t]||'#64748b',border:'#30363d',highlight:{background:colors[t]||'#64748b',border:'#58a6ff'}},shape:'dot',size:25,font:{color:'#c9d1d9',size:12}}});
  var options={physics:{stabilization:{iterations:100},solver:'forceAtlas2Based'},groups:groups,edges:{smooth:{type:'continuous'},color:{color:'#484f58',highlight:'#58a6ff'}},interaction:{hover:true,tooltipDelay:200}};
  new vis.Network(container,{nodes:nodes,edges:edges},options);
  // Legend
  var leg=document.getElementById('graph-legend');
  if(leg){types.forEach(function(t){leg.innerHTML+='<span style=\"display:inline-flex;align-items:center;gap:4px;font-size:0.65rem;color:var(--text-dim)\"><span style=\"width:10px;height:10px;border-radius:50%;background:'+(colors[t]||'#64748b')+'\"></span>'+t+'</span>'});}
}

function renderInvestigate(d){var h='';
h+='<div class=\"card\"><div class=\"stat-grid\">';h+=buildStat('Type',d.target_type||'?','info');h+=buildStat('Entities',d.total_entities||0,'info');h+=buildStat('Relationships',d.total_edges||0,'info');h+=buildStat('Depth',d.depth||0,'info');h+='</div></div>';
if(d.graph&&d.graph.nodes&&d.graph.nodes.length){
  h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">&#128301; Entity Graph ('+d.graph.total_nodes+' nodes, '+d.graph.total_edges+' edges)</div></div>';
  h+='<div id=\"graph-canvas\" style=\"width:100%;height:400px;background:var(--bg);border:1px solid var(--border);border-radius:8px;margin-bottom:0.5rem\"></div>';
  h+='<div id=\"graph-legend\" style=\"margin-top:0.5rem;display:flex;flex-wrap:wrap;gap:0.5rem\"></div>';
  h+='</div>';
  var nArr=d.graph.nodes.map(function(n){return{id:n.id,label:n.type.substring(0,10)+': '+n.value.substring(0,20),title:n.type+' | '+n.value,group:n.type}});
  var eArr=d.graph.edges.map(function(e){return{from:e.source,to:e.target,label:e.relationship,arrows:'to',title:e.relationship+' (confidence: '+Math.round((e.confidence||0.5)*100)+'%)'}});
  setTimeout(function(){renderGraph(nArr,eArr,['Email','Person','Phone','Domain','IP','Username','SocialProfile','Breach','Location','Wallet','Company','Document','Discord']);},500);
}
if(d.investigation_id)h+='<div class=\"card\"><span style=\"color:var(--text-dim)\">Case saved: </span><code style=\"font-size:0.8rem\">'+esc(d.investigation_id)+'</code><br><button class=\"btn btn-sm btn-primary graph-load-btn\" data-caseid=\"'+esc(d.investigation_id)+'\" style=\"margin-top:0.5rem\">&#128301; Open in Graph View</button></div>';
return h||'<div class=\"card\">No results</div>'}

function renderCasesList(d){var h='';if(!d||!d.length)return'<div class=\"card\">No saved cases. Run <code>prosint investigate target</code> first.</div>';d.forEach(function(c){h+='<div class=\"card\"><div class=\"result-card-header\"><div class=\"result-card-title\">'+esc(c.name||c.id)+'</div><span class=\"badge badge-info\">'+esc(c.status||'active')+'</span></div>';h+='<div class=\"kv-row\"><span>Target</span><span>'+esc(c.target||'?')+'</span></div>';h+='<div class=\"kv-row\"><span>Entities</span><span>'+(c.entity_count||0)+'</span></div>';h+='<div class=\"kv-row\"><span>ID</span><span style=\"font-family:monospace;font-size:0.72rem\">'+esc(c.id)+'</span></div>';h+='<button class=\"btn btn-sm btn-primary graph-load-btn\" data-caseid=\"'+esc(c.id)+'\">Load Graph</button></div>'});return h}

document.addEventListener('click',function(e){
  if(e.target.classList.contains('graph-load-btn')){
    var caseId=e.target.getAttribute('data-caseid');
    document.getElementById('graph-target').value=caseId;
    switchPanel('graph');
    runModule('graph');
  }
});

function renderMetadata(d){if(d.error)return'<div class="card"><span style="color:var(--red)">'+esc(d.error)+'</span></div>';var h='<div class="card"><div class="stat-grid">';h+=buildStat('Type',d.type||'?','info');h+=buildStat('Size',fmtBytes(d.size_bytes||0),'info');h+='</div>';if(d.maps_link)h+='<a class="map-link" href="'+d.maps_link+'" target="_blank">GPS</a>';return h||renderRaw(d)}

function renderRaw(d){return'<div class="card"><pre style="font-size:0.78rem;overflow-x:auto;max-height:400px">'+JSON.stringify(d,null,2)+'</pre></div>'}
