# Dry‑Run Chart (Example)

This page renders a small bar chart from the `/dryrun.json` endpoint using Chart.js.

<div>
  <label>Date <input id="d" value="2025-08-21"/></label>
  <label>Rule <input id="r"/></label>
  <label>Action <input id="a"/></label>
  <button onclick="loadChart()">Load</button>
  <small>Requires internet access for Chart.js CDN or vendor locally.</small>
</div>
<canvas id="chart" width="720" height="320"></canvas>

<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
async function loadChart(){
  const day = document.getElementById('d').value;
  const rule = document.getElementById('r').value;
  const action = document.getElementById('a').value;
  const q = new URLSearchParams({date: day});
  if (rule) q.set('rule', rule);
  if (action) q.set('action', action);
  const res = await fetch('/dryrun.json?' + q.toString());
  const data = await res.json();
  const labels = Object.keys(data.rules);
  const actions = ['block','autocorrect','rpc_autocorrect_inplace','allow'];
  const colors = {
    block: 'rgba(220,53,69,.7)',
    autocorrect: 'rgba(13,110,253,.7)',
    rpc_autocorrect_inplace: 'rgba(32,201,151,.7)',
    allow: 'rgba(108,117,125,.6)'
  };
  const datasets = actions.map(a => ({label: a, data: labels.map(r => (data.rules[r][a]||0)), backgroundColor: colors[a]}));
  const ctx = document.getElementById('chart').getContext('2d');
  new Chart(ctx, {type:'bar', data:{labels, datasets}, options:{responsive:true, scales:{x:{stacked:true}, y:{stacked:true}}}});
}
loadChart();
</script>
