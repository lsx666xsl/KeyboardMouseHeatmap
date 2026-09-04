async function api(path, body) {
  const res = await fetch('http://127.0.0.1:7788' + path, {
    method: body ? 'POST' : 'GET',
    headers: { 'content-type': 'application/json' },
    body: body ? JSON.stringify(body) : undefined,
  });
  const text = await res.text();
  try { return JSON.parse(text); } catch { return { raw: text.slice(0, 80) }; }
}
(async () => {
  const reg = await api('/api/register', { name: '榜一测试', pass: '1234' });
  if (!reg.ok && !reg.token) {
    const login = await api('/api/login', { name: '榜一测试', pass: '1234' });
    console.log('reused existing account, login:', login.ok);
  }
  const token = reg.token || (await api('/api/login', { name: '榜一测试', pass: '1234' })).token;
  const days = ['2026-09-01', '2026-09-02', '2026-09-03'];
  for (const d of days) await api('/api/stats', { token, date: d, keys: 500, mouse: 100 });
  await api('/api/stats', { token, date: new Date().toISOString().slice(0, 10), keys: 999, mouse: 200 });
  const me = await api('/api/me?token=' + token);
  console.log('me:', JSON.stringify({ total: me.profile.totalKeys, today: me.profile.todayKeys, days: me.profile.activeDays, streak: me.profile.streak }));
  const board = await api('/api/leaderboard');
  console.log('board top:', JSON.stringify(board.list[0]));
  const byStreak = await api('/api/leaderboard?sort=streak');
  console.log('by-streak ok:', byStreak.ok === true && byStreak.list[0].name === '榜一测试');
  const byToday = await api('/api/leaderboard?sort=today');
  console.log('by-today ok:', byToday.ok === true);
  process.exit(0);
})();
