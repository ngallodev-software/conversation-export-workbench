import fs from 'node:fs';

const plist = new URL('../ios/App/App/Info.plist', import.meta.url);
if (fs.existsSync(plist)) {
  let text = fs.readFileSync(plist, 'utf8');
  if (!text.includes('<key>NSFaceIDUsageDescription</key>')) {
    text = text.replace(
      '</dict>\n</plist>',
      '  <key>NSFaceIDUsageDescription</key>\n' +
      '  <string>Use Face ID to unlock your local conversation archive.</string>\n' +
      '</dict>\n</plist>'
    );
    fs.writeFileSync(plist, text);
  }
}
