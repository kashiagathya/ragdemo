export function chunkText(text:string,size=600):string[]{ const chunks:string[]=[]; for(let start=0;start<text.length;start+=size) chunks.push(text.slice(start,start+size)); return chunks; }
