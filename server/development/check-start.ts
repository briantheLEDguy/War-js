import { checkDevelopment } from './check';
const report = await checkDevelopment(process.env);
console.info(JSON.stringify(report,null,2));
process.exitCode = report.issues.length ? 1 : 0;
