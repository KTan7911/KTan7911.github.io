const sqlite3 = require('sqlite3');
const db = new sqlite3.Database('D:/DS_Harnees/MyWeb/.n8n/.n8n/database.sqlite');
db.get("SELECT id, name, nodes FROM workflow_entity", (err, row) => {
  if (err) { console.log('失败:', err.message); process.exit(1); }
  if (!row) { console.log('无工作流'); process.exit(0); }
  console.log('工作流:', row.id, row.name);
  const nodes = JSON.parse(row.nodes);
  console.log('节点数:', nodes.length);
  nodes.forEach(n => {
    console.log(`--- ${n.name} [${n.type} v${n.typeVersion}] ---`);
    if (n.name === '整理天气消息') {
      console.log(JSON.stringify(n.parameters, null, 2));
    }
  });
  db.close();
});
