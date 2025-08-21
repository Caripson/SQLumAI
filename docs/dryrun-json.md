# Dry‑Run JSON API

Endpoint: `/dryrun.json`

Query params:
- `date`: ISO date `YYYY-MM-DD` (default: today UTC)
- `rule`: filter by rule id
- `action`: filter by action (`allow`, `autocorrect`, `block`, `rpc_autocorrect_inplace`, ...)

Response shape:
```json
{
  "date": "2025-08-21",
  "rules": {
    "rule-id": {"autocorrect": 12, "block": 3}
  }
}
```

## Example: Minimal chart embed

```html
<div>
  <label>Date <input id="d" value="2025-08-21"/></label>
  <button onclick="load()">Load</button>
  <small>Uses /dryrun.json</small>
  
</div>
<canvas id="chart" width="600" height="260"></canvas>
<script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
<script>
async function load() {
  const day = document.getElementById('d').value;
  const res = await fetch(`/dryrun.json?date=${day}`);
  const data = await res.json();
  const labels = Object.keys(data.rules);
  const blocks = labels.map(r => (data.rules[r].block||0));
  const acorr = labels.map(r => (data.rules[r].autocorrect||0));
  const ctx = document.getElementById('chart').getContext('2d');
  new Chart(ctx, {type: 'bar', data:{labels, datasets:[
    {label: 'block', data: blocks, backgroundColor: 'rgba(220,53,69,.6)'},
    {label: 'autocorrect', data: acorr, backgroundColor: 'rgba(13,110,253,.6)'}
  ]}});
}
load();
</script>
```
