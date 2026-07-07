// Build script - Frontend is now built by Angular CLI
// This file is kept for compatibility but the actual build is done by Angular

const fs = require('fs');
const path = require('path');

// Ensure src/public exists
const publicDir = path.join(__dirname, 'src', 'public');
if (!fs.existsSync(publicDir)) {
  fs.mkdirSync(publicDir, { recursive: true });
}

console.log('Frontend build is now handled by Angular CLI (cd frontend && npm run build)');
console.log('Output is automatically placed in src/public for Worker deployment');
