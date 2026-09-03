import { documents } from "@/lib/data";
export async function GET(){ return Response.json({documents}); }
export async function POST(request:Request){ const body=await request.json(); if(typeof body.text!=="string"||!body.text.trim()) return Response.json({error:"Text is required"},{status:400}); const chunks=body.text.match(/.{1,600}(?:\\s|$)/g)||[body.text]; return Response.json({name:body.name||"Untitled.txt",characters:body.text.length,chunks:chunks.length,embeddings:chunks.length,status:"Ready"},{status:201}); }
