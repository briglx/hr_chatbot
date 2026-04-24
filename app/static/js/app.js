// ── State ──
let state = {
    token: null,
    user: null,
    sessionId: null,
    messages: [],          // {role, content, ts, sources}
    isLoading: false
  };
  
  const API_BASE = '';   // same origin — FastAPI running alongside this page
                          // Change to e.g. 'https://api.yourcompany.com' for prod
  

  // ── Boot ──
  window.addEventListener('DOMContentLoaded', () => {
    const savedToken = sessionStorage.getItem('hr_token');
    const savedUser  = sessionStorage.getItem('hr_user');
    if (savedToken && savedUser) {
      state.token = savedToken;
      state.user  = JSON.parse(savedUser);
      enterChat();
    }
    const input = document.getElementById('user-input');
    input.addEventListener('input', () => {
      document.getElementById('send-btn').disabled = !input.value.trim();
    });
  });
  

  
  function enterChat() {
    document.getElementById('login-screen').style.display = 'none';
    const cs = document.getElementById('chat-screen');
    cs.style.display = 'flex';
  
    const name = state.user?.name || state.user?.email || 'there';
    const first = name.split(/[ @]/)[0];
    document.getElementById('user-first-name').textContent = first;
  
    // Header: show user pill + logout
    const hr = document.getElementById('header-right');
    const initials = first.slice(0,2).toUpperCase();
    hr.innerHTML = `
      <div class="user-pill">
        <div class="user-avatar">${initials}</div>
        ${state.user?.email || name}
      </div>
      <button class="btn btn-ghost" onclick="logout()">Sign out</button>
    `;
  
    state.sessionId = 'web-' + crypto.randomUUID().slice(0,8);
    document.getElementById('session-info').textContent = 'Session ' + state.sessionId;
  
    // Welcome bot message
    appendMessage('bot', 'Hello! I\'m your HR assistant, powered by your company\'s official HR documents. Ask me about policies, benefits, leave, onboarding, or anything else people-related.');
  }
  
  function logout() {
    sessionStorage.clear();
    state = { token: null, user: null, sessionId: null, messages: [], isLoading: false };
    document.getElementById('messages').innerHTML = `
      <div class="empty-state" id="empty-state">
        <svg width="48" height="48" viewBox="0 0 48 48" fill="none">
          <path d="M24 4L40 12v12c0 10-7 18-16 20C15 42 8 34 8 24V12L24 4z" stroke="currentColor" stroke-width="2"/>
          <circle cx="24" cy="22" r="4" stroke="currentColor" stroke-width="2"/>
          <path d="M17 34c1-4 4-6 7-6s6 2 7 6" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
        </svg>
        <p>Your conversation is private and grounded in your company's official HR documents.</p>
      </div>`;
    const hr = document.getElementById('header-right');
    hr.innerHTML = `<button class="btn btn-ghost">Sign in</button>`;
  }
  
  // ── Messaging ──
  function sendChip(el) {
    const text = el.textContent.trim();
    document.getElementById('chips').style.display = 'none';
    document.getElementById('user-input').value = text;
    sendMessage();
  }
  
  function handleKey(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  }
  
  function autoResize(el) {
    el.style.height = 'auto';
    el.style.height = Math.min(el.scrollHeight, 140) + 'px';
  }
  
  async function sendMessage() {
    const input = document.getElementById('user-input');
    const text  = input.value.trim();
    if (!text || state.isLoading) return;
  
    input.value = '';
    input.style.height = 'auto';
    document.getElementById('send-btn').disabled = true;
    document.getElementById('empty-state')?.remove();
    document.getElementById('chips').style.display = 'none';
  
    appendMessage('user', text);
    state.messages.push({ role: 'user', content: text });
  
    showTyping(true);
    state.isLoading = true;
  
    try {
      // ── Call FastAPI /messages endpoint (same contract as Teams Bot Framework)
      // POST /api/messages   — same route your bot adapter uses
      const res = await fetch(`${API_BASE}/api/messages`, {
        method: 'POST',
        headers: {
          'Content-Type':  'application/json',
          'Authorization': `Bearer ${state.token}`
        },
        body: JSON.stringify({
          type:        'message',
          id:           crypto.randomUUID(),
          timestamp:    new Date().toISOString(),
          channelId:    'webchat',
          coversationId: state.sessionId,
          from: {
            id:   state.user?.sub || 'web-user',
            name: state.user?.name || state.user?.email || 'Web User',
            role: 'user'
          },
          recipient: { id: 'hr-bot', name: 'HR Assistant', role: 'assistant' },
          content: {
              type: 'text',
              text: text
          },
          parentId: null,
          threadId: null,
          capabilities: {
            streaming: false,
            attachments: false,
            tools: false
          },
          locale:      navigator.language || 'en-US',
          metadata: { source: 'webchat', sessionId: state.sessionId, traceId: crypto.randomUUID(), latencyMs: 0}
        })
      });
  
      if (res.status === 401) { logout(); showToast('Session expired. Please sign in again.', true); return; }
      if (!res.ok) throw new Error(`API error ${res.status}`);
  
      const data = await res.json();
      showTyping(false);
  
      // Supports both direct response and Bot Framework Activity envelope
      const replyText    = data.text || data.reply || data.message || (data.activities && data.activities[0]?.text) || '';
      const sources      = data.sources || data.context_sources || [];
      const sessionId    = data.session_id || data.sessionId;
      if (sessionId) state.sessionId = sessionId;
  
      state.messages.push({ role: 'assistant', content: replyText, sources });
      appendMessage('bot', replyText, sources);
  
    } catch (err) {
      showTyping(false);
      if (err.message.includes('Failed to fetch') || err.message.includes('NetworkError')) {
        // Dev fallback — show a mock response so the UI is demoable without a running server
        const mock = getMockResponse(text);
        state.messages.push({ role: 'assistant', content: mock.text, sources: mock.sources });
        appendMessage('bot', mock.text, mock.sources);
      } else {
        appendMessage('bot', 'I encountered an error processing your request. Please try again or contact IT support.', []);
        showToast(err.message, true);
      }
    } finally {
      state.isLoading = false;
    }
  }
  
  function appendMessage(role, content, sources = []) {
    const messagesEl = document.getElementById('messages');
    const ts = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const isBot = role === 'bot';
  
    const row = document.createElement('div');
    row.className = `msg-row ${isBot ? 'bot' : 'user'}`;
  
    const initials = isBot ? 'HR' : (state.user?.name || 'Me').slice(0,2).toUpperCase();
    const avatarClass = isBot ? 'bot-avatar' : 'user-avatar-sm';
  
    let sourcesHTML = '';
    if (sources.length > 0) {
      sourcesHTML = `<div class="sources">${sources.map(s =>
        `<span class="source-pill">${escHtml(s.title || s.filename || s)}</span>`
      ).join('')}</div>`;
    }
  
    row.innerHTML = `
      <div class="msg-avatar ${avatarClass}">${initials}</div>
      <div>
        <div class="msg-bubble">${escHtml(content).replace(/\n/g,'<br>')}${sourcesHTML}</div>
        <div class="msg-meta">${ts}</div>
      </div>`;
  
    messagesEl.appendChild(row);
    row.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }
  
  function showTyping(visible) {
    document.getElementById('typing').className = 'typing-indicator' + (visible ? ' visible' : '');
    if (visible) document.getElementById('typing').scrollIntoView({ behavior: 'smooth', block: 'end' });
  }
  
  // ── UI helpers ──
  function showToast(msg, error = false) {
    const el = document.getElementById('toast');
    el.textContent = msg;
    el.className = 'toast' + (error ? ' error' : '') + ' show';
    setTimeout(() => { el.className = 'toast' + (error ? ' error' : ''); }, 4000);
  }
  
  function escHtml(str) {
    return String(str).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
  }
  
  // ── PKCE helpers ──
  function generateVerifier() {
    const arr = new Uint8Array(32);
    crypto.getRandomValues(arr);
    return btoa(String.fromCharCode(...arr)).replace(/\+/g,'-').replace(/\//g,'_').replace(/=/g,'');
  }
  async function pkceChallenge(verifier) {
    const buf = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(verifier));
    return btoa(String.fromCharCode(...new Uint8Array(buf))).replace(/\+/g,'-').replace(/\//g,'_').replace(/=/g,'');
  }
  
  function parseJwt(token) {
    try {
      return JSON.parse(atob(token.split('.')[1].replace(/-/g,'+').replace(/_/g,'/')));
    } catch { return {}; }
  }
  
  // ── Mock responses for UI demo when API isn't running ──
  function getMockResponse(query) {
    const q = query.toLowerCase();
    if (q.includes('parental') || q.includes('maternity') || q.includes('paternity')) {
      return {
        text: 'Our parental leave policy provides 16 weeks of fully paid leave for primary caregivers and 6 weeks for secondary caregivers, available after 6 months of employment. You may also request up to 4 additional weeks of unpaid leave. To initiate, notify HR at least 30 days in advance using the Leave Request form in Workday.',
        sources: [{ title: 'HR Policy Handbook — Section 4.2' }, { title: 'Benefits Guide 2024' }]
      };
    }
    if (q.includes('pto') || q.includes('vacation') || q.includes('time off')) {
      return {
        text: 'Full-time employees accrue 15 days of PTO annually during years 1–3, increasing to 20 days from year 4 onward. PTO requests should be submitted at least 2 weeks in advance through Workday. Unused PTO (up to 5 days) rolls over each calendar year.',
        sources: [{ title: 'HR Policy Handbook — Section 5.1' }]
      };
    }
    if (q.includes('401') || q.includes('retirement')) {
      return {
        text: 'The company matches 100% of your 401(k) contributions up to 4% of your salary, and 50% on the next 2% (for a maximum 5% match). You are eligible to enroll immediately upon hire; matching vests on a 3-year graded schedule.',
        sources: [{ title: 'Benefits Guide 2024 — Retirement' }, { title: 'Fidelity Plan Summary' }]
      };
    }
    return {
      text: 'I found relevant information in your HR knowledge base. Please note: this is a demo response — connect the page to your FastAPI backend at /api/messages to get live, document-grounded answers.',
      sources: [{ title: 'HR Policy Handbook' }]
    };
  }
